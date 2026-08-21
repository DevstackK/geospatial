from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from a2a_geo_cleaning.contracts import CleaningRule, RuleType, WorkflowState


IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class OracleSpatialConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class OracleSpatialSQLStep:
    name: str
    sql: str
    transactional: bool = True


class OracleSpatialExecutor:
    def __init__(self, state: WorkflowState) -> None:
        self.state = state
        dataset = state.config["dataset"]
        self.schema, self.table = self._split_table(dataset["table"])
        self.geom_column = self._quote_identifier(
            dataset.get("geometry_column", "GEOM")
        )
        self.id_column = dataset.get("id_column")
        self.audit_table = self._quote_qualified(
            state.config.get("execution", {}).get(
                "audit_table", f"{self.schema}.CLEANSING_AUDIT"
            )
        )
        pipeline = state.config.get("oracle_pipeline", {})
        self.clean_table = self._optional_qualified(pipeline.get("clean_table"))
        self.reject_table = self._optional_qualified(pipeline.get("reject_table"))
        self.quarantine_table = self._optional_qualified(pipeline.get("quarantine_table"))
        self.redundant_table = self._optional_qualified(pipeline.get("redundant_table"))
        validation = state.config.get("validation", {})
        self.allowed_statuses = [
            str(value).upper() for value in validation.get("allowed_statuses", [])
        ]
        self.redundant_statuses = [
            str(value).upper() for value in validation.get("redundant_statuses", [])
        ]
        self.status_column = self._quote_identifier(
            validation.get("status_column", "STATUS")
        )

    def execute(self) -> None:
        steps = self.build_plan()
        run_mode = self.state.config["project"].get("run_mode", "dry_run")

        if run_mode == "dry_run":
            self.state.execution_log.append(
                {
                    "status": "dry_run",
                    "engine": "oracle_spatial",
                    "message": "Oracle Spatial SQL plan was generated but not executed.",
                    "table": self.qualified_table,
                    "rule_count": len(self.state.accepted_rules),
                    "sql_steps": [step.__dict__ for step in steps],
                }
            )
            return

        dsn = (
            self.state.config.get("execution", {}).get("dsn")
            or os.environ.get("ORACLE_DSN")
            or os.environ.get("GCOMM_ORACLE_DSN")
        )
        user = (
            self.state.config.get("execution", {}).get("user")
            or os.environ.get("ORACLE_USER")
            or os.environ.get("GCOMM_ORACLE_USER")
        )
        password = (
            self.state.config.get("execution", {}).get("password")
            or os.environ.get("ORACLE_PASSWORD")
            or os.environ.get("GCOMM_ORACLE_PASSWORD")
        )
        if not all([dsn, user, password]):
            raise OracleSpatialConfigurationError(
                "Set execution.dsn/user/password or ORACLE_DSN, ORACLE_USER, "
                "and ORACLE_PASSWORD to execute Oracle Spatial validation."
            )

        try:
            import oracledb
        except ImportError as exc:
            raise OracleSpatialConfigurationError(
                "Install Oracle dependencies with `pip install -e .[oracle]`."
            ) from exc

        executed: list[dict[str, Any]] = []
        with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
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
                "engine": "oracle_spatial",
                "table": self.qualified_table,
                "rule_count": len(self.state.accepted_rules),
                "executed_steps": executed,
            }
        )

    def build_plan(self) -> list[OracleSpatialSQLStep]:
        steps = [self._create_audit_table_step()]
        for rule in self.state.accepted_rules:
            steps.extend(self._steps_for_rule(rule))
        steps.extend(self._classification_steps())
        steps.extend(self._validation_steps())
        return steps

    @property
    def qualified_table(self) -> str:
        return f"{self._quote_identifier(self.schema)}.{self._quote_identifier(self.table)}"

    def _create_audit_table_step(self) -> OracleSpatialSQLStep:
        return OracleSpatialSQLStep(
            "create_oracle_validation_audit_table",
            (
                "BEGIN "
                "EXECUTE IMMEDIATE "
                f"{self._literal(self._create_audit_table_sql())}; "
                "EXCEPTION WHEN OTHERS THEN "
                "IF SQLCODE != -955 THEN RAISE; END IF; "
                "END;"
            ),
        )

    def _steps_for_rule(self, rule: CleaningRule) -> list[OracleSpatialSQLStep]:
        target = self._literal(rule.target)

        if rule.rule_type == RuleType.REQUIRE_COLUMN:
            column = rule.parameters["column"]
            return [
                OracleSpatialSQLStep(
                    f"check_required_column_{column}",
                    (
                        f"INSERT INTO {self.audit_table} "
                        "(RUN_NAME, RULE_TYPE, TARGET, AFFECTED_COUNT, DETAILS) "
                        f"SELECT {self.run_name}, 'require_column', {target}, "
                        "CASE WHEN EXISTS ("
                        "SELECT 1 FROM ALL_TAB_COLUMNS "
                        f"WHERE OWNER = {self._literal(self.schema.upper())} "
                        f"AND TABLE_NAME = {self._literal(self.table.upper())} "
                        f"AND COLUMN_NAME = {self._literal(column.upper())}"
                        ") THEN 0 ELSE 1 END, "
                        f"{self._literal('column=' + column)} FROM DUAL"
                    ),
                )
            ]

        if rule.rule_type == RuleType.NORMALIZE_CRS:
            target_srid = self._srid(rule.parameters["target_crs"])
            return [
                OracleSpatialSQLStep(
                    "audit_srid_mismatch",
                    self._insert_count_sql(
                        "normalize_crs",
                        target,
                        (
                            f"{self.geom_column} IS NOT NULL AND "
                            f"NVL({self.geom_column}.SDO_SRID, -1) <> {target_srid}"
                        ),
                    ),
                )
            ]

        if rule.rule_type == RuleType.DROP_EMPTY_GEOMETRY:
            return [
                OracleSpatialSQLStep(
                    "audit_null_geometries",
                    self._insert_count_sql(
                        "drop_empty_geometry",
                        target,
                        f"{self.geom_column} IS NULL",
                    ),
                )
            ]

        if rule.rule_type == RuleType.MAKE_VALID:
            return [
                OracleSpatialSQLStep(
                    "audit_invalid_geometries",
                    self._insert_count_sql(
                        "make_valid",
                        target,
                        (
                            f"{self.geom_column} IS NOT NULL AND "
                            f"SDO_GEOM.VALIDATE_GEOMETRY_WITH_CONTEXT({self.geom_column}, 0.005) <> 'TRUE'"
                        ),
                    ),
                )
            ]

        if rule.rule_type == RuleType.CHECK_BOUNDS:
            return [
                OracleSpatialSQLStep(
                    "audit_bounds_review_required",
                    (
                        f"INSERT INTO {self.audit_table} "
                        "(RUN_NAME, RULE_TYPE, TARGET, AFFECTED_COUNT, DETAILS) "
                        f"SELECT {self.run_name}, 'check_bounds', {target}, NULL, "
                        f"{self._literal('Review layer extent using Oracle Spatial metadata or SDO_AGGR_MBR.')} "
                        "FROM DUAL"
                    ),
                )
            ]

        if rule.rule_type == RuleType.TRIM_STRING:
            column = self._quote_identifier(rule.parameters["column"])
            return [
                OracleSpatialSQLStep(
                    f"trim_{rule.parameters['column']}",
                    (
                        f"UPDATE {self.qualified_table} "
                        f"SET {column} = TRIM({column}) "
                        f"WHERE {column} IS NOT NULL AND {column} <> TRIM({column})"
                    ),
                )
            ]

        if rule.rule_type == RuleType.NORMALIZE_CATEGORY:
            column = self._quote_identifier(rule.parameters["column"])
            cases = []
            values = []
            for raw, normalized in rule.parameters["mapping"].items():
                cases.append(
                    f"WHEN LOWER(TRIM({column})) = {self._literal(str(raw).lower())} "
                    f"THEN {self._literal(str(normalized))}"
                )
                values.append(self._literal(str(raw).lower()))
            return [
                OracleSpatialSQLStep(
                    f"normalize_{rule.parameters['column']}",
                    (
                        f"UPDATE {self.qualified_table} "
                        f"SET {column} = CASE {' '.join(cases)} ELSE {column} END "
                        f"WHERE LOWER(TRIM({column})) IN ({', '.join(values)})"
                    ),
                )
            ]

        if rule.rule_type == RuleType.FLAG_DUPLICATES and self.id_column:
            column = self._quote_identifier(rule.parameters["column"])
            return [
                OracleSpatialSQLStep(
                    f"audit_duplicate_{rule.parameters['column']}",
                    (
                        f"INSERT INTO {self.audit_table} "
                        "(RUN_NAME, RULE_TYPE, TARGET, AFFECTED_COUNT, DETAILS) "
                        f"SELECT {self.run_name}, 'flag_duplicates', {target}, COUNT(*), "
                        f"{self._literal('column=' + rule.parameters['column'])} "
                        f"FROM {self.qualified_table} "
                        f"WHERE {column} IN ("
                        f"SELECT {column} FROM {self.qualified_table} "
                        f"GROUP BY {column} HAVING COUNT(*) > 1)"
                    ),
                )
            ]

        if rule.rule_type == RuleType.VALIDATE_PARALLEL_ASSOCIATION:
            return self._parallel_association_steps(rule)

        return []

    def _parallel_association_steps(
        self, rule: CleaningRule
    ) -> list[OracleSpatialSQLStep]:
        params = rule.parameters
        span_table = self._quote_qualified(params["span_table"])
        duct_table = self._quote_qualified(params["duct_table"])
        result_table = self._quote_qualified(params.get("result_table", "IQGEO_STAGE.SPAN_DUCT_MATCH_AUDIT"))
        span_id = self._quote_identifier(params.get("span_id_column", "SPAN_ID"))
        span_geom = self._quote_identifier(params.get("span_geometry_column", "GEOM"))
        duct_id = self._quote_identifier(params.get("duct_id_column", "DUCT_ID"))
        duct_geom = self._quote_identifier(params.get("duct_geometry_column", "GEOM"))
        current_match = self._quote_identifier(params.get("current_match_column", "MATCHED_DUCT_ID"))
        max_distance = float(params.get("max_distance", 25))
        angle_tolerance = float(params.get("angle_tolerance_degrees", 25))
        perpendicular_penalty = float(params.get("perpendicular_penalty", 1000))
        candidate_count = int(params.get("candidate_count", 8))
        bearing_function = self._quote_function_name(
            params.get("bearing_function", "GEOM_BEARING_DEGREES")
        )
        bearing_delta = (
            "LEAST("
            f"ABS({bearing_function}(s.{span_geom}) - {bearing_function}(d.{duct_geom})), "
            f"180 - ABS({bearing_function}(s.{span_geom}) - {bearing_function}(d.{duct_geom}))"
            ")"
        )

        scoring_sql = (
            f"CREATE TABLE {result_table} AS "
            "WITH candidates AS ("
            f"SELECT s.{span_id} AS SPAN_ID, s.{current_match} AS CURRENT_DUCT_ID, "
            f"d.{duct_id} AS CANDIDATE_DUCT_ID, "
            f"SDO_GEOM.SDO_DISTANCE(s.{span_geom}, d.{duct_geom}, 0.005) AS DISTANCE_M, "
            f"{bearing_delta} AS ALIGNMENT_DELTA "
            f"FROM {span_table} s JOIN {duct_table} d "
            f"ON SDO_NN(d.{duct_geom}, s.{span_geom}, "
            f"'sdo_num_res={candidate_count} distance={max_distance}', 1) = 'TRUE'"
            "), scored AS ("
            "SELECT candidates.*, "
            "DISTANCE_M + CASE "
            f"WHEN ALIGNMENT_DELTA > {angle_tolerance} THEN {perpendicular_penalty} "
            "ELSE ALIGNMENT_DELTA END AS MATCH_SCORE "
            "FROM candidates"
            "), ranked AS ("
            "SELECT scored.*, ROW_NUMBER() OVER (PARTITION BY SPAN_ID ORDER BY MATCH_SCORE) AS RN "
            "FROM scored"
            ") "
            "SELECT SPAN_ID, CURRENT_DUCT_ID, CANDIDATE_DUCT_ID AS RECOMMENDED_DUCT_ID, "
            "DISTANCE_M, ALIGNMENT_DELTA, MATCH_SCORE, "
            "CASE WHEN CURRENT_DUCT_ID = CANDIDATE_DUCT_ID THEN 'MATCHED' "
            "ELSE 'INCORRECT_ASSOCIATION' END AS ASSOCIATION_STATUS "
            "FROM ranked WHERE RN = 1"
        )

        return [
            OracleSpatialSQLStep(
                "drop_parallel_association_audit",
                (
                    "BEGIN EXECUTE IMMEDIATE "
                    f"{self._literal(f'DROP TABLE {result_table} PURGE')}; "
                    "EXCEPTION WHEN OTHERS THEN IF SQLCODE != -942 THEN RAISE; END IF; END;"
                ),
            ),
            OracleSpatialSQLStep("score_parallel_duct_associations", scoring_sql),
            OracleSpatialSQLStep(
                "audit_parallel_association_mismatches",
                (
                    f"INSERT INTO {self.audit_table} "
                    "(RUN_NAME, RULE_TYPE, TARGET, AFFECTED_COUNT, DETAILS) "
                    f"SELECT {self.run_name}, 'validate_parallel_association', "
                    f"{self._literal(params.get('span_table', 'spans'))}, COUNT(*), "
                    f"{self._literal('nearest match replaced by parallel-alignment scoring')} "
                    f"FROM {result_table} WHERE ASSOCIATION_STATUS = 'INCORRECT_ASSOCIATION'"
                ),
            ),
        ]

    def _classification_steps(self) -> list[OracleSpatialSQLStep]:
        if not any(
            [self.clean_table, self.reject_table, self.quarantine_table, self.redundant_table]
        ):
            return []

        invalid_geometry = (
            f"{self.geom_column} IS NULL OR "
            f"SDO_GEOM.VALIDATE_GEOMETRY_WITH_CONTEXT({self.geom_column}, 0.005) <> 'TRUE'"
        )
        redundant_status = self._in_list_condition(
            f"UPPER(TRIM({self.status_column}))", self.redundant_statuses
        )
        invalid_status = ""
        if self.allowed_statuses:
            accepted = self.allowed_statuses + self.redundant_statuses
            invalid_status = (
                f"{self.status_column} IS NOT NULL AND NOT "
                f"{self._in_list_condition(f'UPPER(TRIM({self.status_column}))', accepted)}"
            )

        steps: list[OracleSpatialSQLStep] = []
        if self.reject_table:
            steps.extend(
                self._replace_table_as_select(
                    "build_reject_table",
                    self.reject_table,
                    f"{invalid_geometry}",
                )
            )
        if self.redundant_table and self.redundant_statuses:
            steps.extend(
                self._replace_table_as_select(
                    "build_redundant_table",
                    self.redundant_table,
                    redundant_status,
                )
            )
        if self.quarantine_table and invalid_status:
            steps.extend(
                self._replace_table_as_select(
                    "build_quarantine_table",
                    self.quarantine_table,
                    invalid_status,
                )
            )
        if self.clean_table:
            blocked_conditions = [f"NOT ({invalid_geometry})"]
            if self.redundant_statuses:
                blocked_conditions.append(f"NOT ({redundant_status})")
            if invalid_status:
                blocked_conditions.append(f"NOT ({invalid_status})")
            steps.extend(
                self._replace_table_as_select(
                    "build_clean_table",
                    self.clean_table,
                    " AND ".join(blocked_conditions),
                )
            )
        return steps

    def _replace_table_as_select(
        self, name: str, table: str, condition: str
    ) -> list[OracleSpatialSQLStep]:
        return [
            OracleSpatialSQLStep(
                f"drop_{name}",
                (
                    "BEGIN EXECUTE IMMEDIATE "
                    f"{self._literal(f'DROP TABLE {table} PURGE')}; "
                    "EXCEPTION WHEN OTHERS THEN IF SQLCODE != -942 THEN RAISE; END IF; END;"
                ),
            ),
            OracleSpatialSQLStep(
                name,
                f"CREATE TABLE {table} AS SELECT * FROM {self.qualified_table} WHERE {condition}",
            ),
            OracleSpatialSQLStep(
                f"audit_{name}",
                self._insert_count_sql(name, self._literal(table), condition),
            ),
        ]

    def _create_audit_table_sql(self) -> str:
        return (
            f"CREATE TABLE {self.audit_table} ("
            "ID NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, "
            "RUN_NAME VARCHAR2(255) NOT NULL, "
            "RULE_TYPE VARCHAR2(100) NOT NULL, "
            "TARGET VARCHAR2(255) NOT NULL, "
            "AFFECTED_COUNT NUMBER, "
            "DETAILS CLOB, "
            "CREATED_AT TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL"
            ")"
        )

    def _validation_steps(self) -> list[OracleSpatialSQLStep]:
        return [
            OracleSpatialSQLStep(
                "gather_oracle_table_stats",
                (
                    "BEGIN DBMS_STATS.GATHER_TABLE_STATS("
                    f"ownname => {self._literal(self.schema.upper())}, "
                    f"tabname => {self._literal(self.table.upper())}); END;"
                ),
                transactional=False,
            )
        ]

    @property
    def run_name(self) -> str:
        return self._literal(self.state.config["project"].get("name", "cleaning"))

    def _insert_count_sql(self, rule_type: str, target: str, condition: str) -> str:
        return (
            f"INSERT INTO {self.audit_table} "
            "(RUN_NAME, RULE_TYPE, TARGET, AFFECTED_COUNT) "
            f"SELECT {self.run_name}, {self._literal(rule_type)}, {target}, COUNT(*) "
            f"FROM {self.qualified_table} WHERE {condition}"
        )

    def _split_table(self, table: str) -> tuple[str, str]:
        parts = table.split(".")
        if len(parts) == 1:
            schema, name = "GIS", parts[0]
        elif len(parts) == 2:
            schema, name = parts
        else:
            raise OracleSpatialConfigurationError(
                "dataset.table must be `table` or `schema.table`."
            )
        self._quote_identifier(schema)
        self._quote_identifier(name)
        return schema, name

    def _quote_qualified(self, value: str) -> str:
        parts = value.split(".")
        if len(parts) != 2:
            raise OracleSpatialConfigurationError("Qualified names must be `schema.table`.")
        return ".".join(self._quote_identifier(part) for part in parts)

    def _optional_qualified(self, value: str | None) -> str:
        return self._quote_qualified(value) if value else ""

    def _quote_identifier(self, value: str) -> str:
        if not IDENTIFIER_RE.match(value):
            raise OracleSpatialConfigurationError(f"Unsafe Oracle identifier: {value!r}")
        return f'"{value.upper()}"'

    def _quote_function_name(self, value: str) -> str:
        parts = value.split(".")
        if len(parts) not in {1, 2}:
            raise OracleSpatialConfigurationError("Function names must be `name` or `schema.name`.")
        return ".".join(self._quote_identifier(part) for part in parts)

    def _literal(self, value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    def _in_list_condition(self, expression: str, values: list[str]) -> str:
        if not values:
            return "1 = 0"
        return f"{expression} IN ({', '.join(self._literal(value) for value in values)})"

    def _srid(self, crs: str) -> int:
        if not crs.upper().startswith("EPSG:"):
            raise OracleSpatialConfigurationError(
                "Oracle Spatial CRS normalization requires EPSG:<srid>."
            )
        return int(crs.split(":", 1)[1])
