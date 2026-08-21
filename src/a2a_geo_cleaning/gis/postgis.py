from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from a2a_geo_cleaning.contracts import CleaningRule, RuleType, WorkflowState


IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class PostGISConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class SQLStep:
    name: str
    sql: str
    transactional: bool = True


class PostGISExecutor:
    def __init__(self, state: WorkflowState) -> None:
        self.state = state
        dataset = state.config["dataset"]
        self.schema, self.table = self._split_table(dataset["table"])
        self.geom_column = self._quote_identifier(
            dataset.get("geometry_column", "geom")
        )
        self.id_column = dataset.get("id_column")
        self.audit_table = self._quote_qualified(
            state.config.get("execution", {}).get(
                "audit_table", f"{self.schema}.cleaning_audit"
            )
        )

    def execute(self) -> None:
        steps = self.build_plan()
        run_mode = self.state.config["project"].get("run_mode", "dry_run")

        if run_mode == "dry_run":
            self.state.execution_log.append(
                {
                    "status": "dry_run",
                    "engine": "postgis",
                    "message": "PostGIS SQL plan was generated but not executed.",
                    "table": self.qualified_table,
                    "rule_count": len(self.state.accepted_rules),
                    "sql_steps": [step.__dict__ for step in steps],
                }
            )
            return

        database_url = (
            self.state.config.get("execution", {}).get("database_url")
            or os.environ.get("DATABASE_URL")
            or os.environ.get("POSTGIS_DATABASE_URL")
        )
        if not database_url:
            raise PostGISConfigurationError(
                "Set execution.database_url, DATABASE_URL, or POSTGIS_DATABASE_URL "
                "to execute PostGIS cleaning."
            )

        try:
            import psycopg
        except ImportError as exc:
            raise PostGISConfigurationError(
                "Install PostGIS dependencies with `pip install -e .[postgis]`."
            ) from exc

        executed: list[dict[str, Any]] = []
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                for step in steps:
                    cur.execute(step.sql)
                    executed.append(
                        {
                            "name": step.name,
                            "rowcount": cur.rowcount,
                            "transactional": step.transactional,
                        }
                    )
            conn.commit()

        self.state.execution_log.append(
            {
                "status": "executed",
                "engine": "postgis",
                "table": self.qualified_table,
                "rule_count": len(self.state.accepted_rules),
                "executed_steps": executed,
            }
        )

    def build_plan(self) -> list[SQLStep]:
        steps = [
            SQLStep(
                "create_audit_table",
                (
                    f"CREATE TABLE IF NOT EXISTS {self.audit_table} ("
                    "id bigserial PRIMARY KEY, "
                    "run_name text NOT NULL, "
                    "rule_type text NOT NULL, "
                    "target text NOT NULL, "
                    "affected_count bigint, "
                    "details jsonb DEFAULT '{}'::jsonb, "
                    "created_at timestamptz NOT NULL DEFAULT now()"
                    ");"
                ),
            )
        ]
        for rule in self.state.accepted_rules:
            steps.extend(self._steps_for_rule(rule))
        steps.extend(self._validation_steps())
        return steps

    @property
    def qualified_table(self) -> str:
        return f"{self._quote_identifier(self.schema)}.{self._quote_identifier(self.table)}"

    def _steps_for_rule(self, rule: CleaningRule) -> list[SQLStep]:
        run_name = self._literal(self.state.config["project"].get("name", "cleaning"))
        rule_type = rule.rule_type.value
        target = self._literal(rule.target)

        if rule.rule_type == RuleType.REQUIRE_COLUMN:
            column = self._literal(rule.parameters["column"])
            return [
                SQLStep(
                    f"check_required_column_{rule.parameters['column']}",
                    (
                        f"INSERT INTO {self.audit_table} "
                        "(run_name, rule_type, target, affected_count, details) "
                        f"SELECT {run_name}, 'require_column', {target}, "
                        "CASE WHEN EXISTS ("
                        "SELECT 1 FROM information_schema.columns "
                        f"WHERE table_schema = {self._literal(self.schema)} "
                        f"AND table_name = {self._literal(self.table)} "
                        f"AND column_name = {column}"
                        ") THEN 0 ELSE 1 END, "
                        f"jsonb_build_object('column', {column});"
                    ),
                )
            ]

        if rule.rule_type == RuleType.NORMALIZE_CRS:
            target_srid = self._srid(rule.parameters["target_crs"])
            return [
                SQLStep(
                    "normalize_crs",
                    (
                        f"UPDATE {self.qualified_table} "
                        f"SET {self.geom_column} = ST_Transform({self.geom_column}, {target_srid}) "
                        f"WHERE {self.geom_column} IS NOT NULL "
                        f"AND ST_SRID({self.geom_column}) NOT IN (0, {target_srid});"
                    ),
                )
            ]

        if rule.rule_type == RuleType.DROP_EMPTY_GEOMETRY:
            return [
                SQLStep(
                    "audit_empty_geometries",
                    self._insert_count_sql(
                        "drop_empty_geometry",
                        target,
                        f"{self.geom_column} IS NULL OR ST_IsEmpty({self.geom_column})",
                    ),
                ),
                SQLStep(
                    "drop_empty_geometries",
                    (
                        f"DELETE FROM {self.qualified_table} "
                        f"WHERE {self.geom_column} IS NULL OR ST_IsEmpty({self.geom_column});"
                    ),
                ),
            ]

        if rule.rule_type == RuleType.MAKE_VALID:
            return [
                SQLStep(
                    "make_valid",
                    (
                        f"UPDATE {self.qualified_table} "
                        f"SET {self.geom_column} = ST_MakeValid({self.geom_column}) "
                        f"WHERE {self.geom_column} IS NOT NULL "
                        f"AND NOT ST_IsValid({self.geom_column});"
                    ),
                )
            ]

        if rule.rule_type == RuleType.CHECK_BOUNDS:
            params = rule.parameters
            condition = (
                f"{self.geom_column} IS NOT NULL AND ("
                f"ST_XMin(Box2D({self.geom_column})) < {float(params['minx'])} OR "
                f"ST_YMin(Box2D({self.geom_column})) < {float(params['miny'])} OR "
                f"ST_XMax(Box2D({self.geom_column})) > {float(params['maxx'])} OR "
                f"ST_YMax(Box2D({self.geom_column})) > {float(params['maxy'])})"
            )
            return [
                SQLStep(
                    "audit_out_of_bounds_geometries",
                    self._insert_count_sql("check_bounds", target, condition),
                )
            ]

        if rule.rule_type == RuleType.TRIM_STRING:
            column = self._quote_identifier(rule.parameters["column"])
            return [
                SQLStep(
                    f"trim_{rule.parameters['column']}",
                    (
                        f"UPDATE {self.qualified_table} "
                        f"SET {column} = btrim({column}) "
                        f"WHERE {column} IS NOT NULL AND {column} <> btrim({column});"
                    ),
                )
            ]

        if rule.rule_type == RuleType.NORMALIZE_CATEGORY:
            column = self._quote_identifier(rule.parameters["column"])
            cases = []
            values = []
            for raw, normalized in rule.parameters["mapping"].items():
                cases.append(
                    f"WHEN lower(btrim({column})) = {self._literal(str(raw).lower())} "
                    f"THEN {self._literal(str(normalized))}"
                )
                values.append(self._literal(str(raw).lower()))
            return [
                SQLStep(
                    f"normalize_{rule.parameters['column']}",
                    (
                        f"UPDATE {self.qualified_table} "
                        f"SET {column} = CASE {' '.join(cases)} ELSE {column} END "
                        f"WHERE lower(btrim({column})) IN ({', '.join(values)});"
                    ),
                )
            ]

        if rule.rule_type == RuleType.FLAG_DUPLICATES and self.id_column:
            column = self._quote_identifier(rule.parameters["column"])
            return [
                SQLStep(
                    f"audit_duplicate_{rule.parameters['column']}",
                    (
                        f"INSERT INTO {self.audit_table} "
                        "(run_name, rule_type, target, affected_count, details) "
                        f"SELECT {run_name}, 'flag_duplicates', {target}, COUNT(*), "
                        f"jsonb_build_object('column', {self._literal(rule.parameters['column'])}) "
                        f"FROM {self.qualified_table} "
                        f"WHERE {column} IN ("
                        f"SELECT {column} FROM {self.qualified_table} "
                        f"GROUP BY {column} HAVING COUNT(*) > 1"
                        ");"
                    ),
                )
            ]

        return []

    def _validation_steps(self) -> list[SQLStep]:
        return [
            SQLStep(
                "analyze_cleaned_table",
                f"ANALYZE {self.qualified_table};",
                transactional=False,
            )
        ]

    def _insert_count_sql(self, rule_type: str, target: str, condition: str) -> str:
        run_name = self._literal(self.state.config["project"].get("name", "cleaning"))
        return (
            f"INSERT INTO {self.audit_table} "
            "(run_name, rule_type, target, affected_count) "
            f"SELECT {run_name}, {self._literal(rule_type)}, {target}, COUNT(*) "
            f"FROM {self.qualified_table} WHERE {condition};"
        )

    def _split_table(self, table: str) -> tuple[str, str]:
        parts = table.split(".")
        if len(parts) == 1:
            schema, name = "public", parts[0]
        elif len(parts) == 2:
            schema, name = parts
        else:
            raise PostGISConfigurationError("dataset.table must be `table` or `schema.table`.")
        self._quote_identifier(schema)
        self._quote_identifier(name)
        return schema, name

    def _quote_qualified(self, value: str) -> str:
        parts = value.split(".")
        if len(parts) != 2:
            raise PostGISConfigurationError("Qualified names must be `schema.table`.")
        return ".".join(self._quote_identifier(part) for part in parts)

    def _quote_identifier(self, value: str) -> str:
        if not IDENTIFIER_RE.match(value):
            raise PostGISConfigurationError(f"Unsafe SQL identifier: {value!r}")
        return f'"{value}"'

    def _literal(self, value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    def _srid(self, crs: str) -> int:
        if not crs.upper().startswith("EPSG:"):
            raise PostGISConfigurationError("PostGIS CRS normalization requires EPSG:<srid>.")
        return int(crs.split(":", 1)[1])
