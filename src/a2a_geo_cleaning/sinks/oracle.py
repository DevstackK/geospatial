from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from a2a_geo_cleaning.contracts import WorkflowState


IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class OracleConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class OracleSQLStep:
    name: str
    sql: str


class OracleSink:
    def __init__(self, state: WorkflowState) -> None:
        self.state = state
        self.config = state.config.get("output", {})
        if self.config.get("sink") != "oracle":
            raise OracleConfigurationError("output.sink must be `oracle`.")

        self.mode = self.config.get("mode", "staging")
        if self.mode not in {"staging", "merge"}:
            raise OracleConfigurationError("output.mode must be `staging` or `merge`.")

        self.stage_table = self._quote_qualified(self.config["stage_table"])
        self.target_table = self._quote_qualified(self.config.get("target_table", ""))
        self.source_table = self._quote_qualified(self.config.get("source_table", ""))
        self.key_columns = [self._quote_identifier(col) for col in self.config["key_columns"]]
        self.columns = [self._quote_identifier(col) for col in self.config["columns"]]
        self.geometry = self.config.get("geometry")

    def publish(self) -> None:
        steps = self.build_plan()
        run_mode = self.state.config["project"].get("run_mode", "dry_run")

        if run_mode == "dry_run":
            self.state.execution_log.append(
                {
                    "status": "dry_run",
                    "sink": "oracle",
                    "mode": self.mode,
                    "message": "Oracle write-back SQL plan was generated but not executed.",
                    "sql_steps": [step.__dict__ for step in steps],
                }
            )
            return

        dsn = self.config.get("dsn") or os.environ.get("ORACLE_DSN")
        user = self.config.get("user") or os.environ.get("ORACLE_USER")
        password = self.config.get("password") or os.environ.get("ORACLE_PASSWORD")
        if not all([dsn, user, password]):
            raise OracleConfigurationError(
                "Set output.dsn/user/password or ORACLE_DSN, ORACLE_USER, "
                "and ORACLE_PASSWORD to execute Oracle write-back."
            )

        try:
            import oracledb
        except ImportError as exc:
            raise OracleConfigurationError(
                "Install Oracle dependencies with `pip install -e .[oracle]`."
            ) from exc

        executed: list[dict[str, Any]] = []
        with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
            with conn.cursor() as cur:
                for step in steps:
                    cur.execute(step.sql)
                    executed.append({"name": step.name, "rowcount": cur.rowcount})
            conn.commit()

        self.state.execution_log.append(
            {
                "status": "executed",
                "sink": "oracle",
                "mode": self.mode,
                "executed_steps": executed,
            }
        )

    def build_plan(self) -> list[OracleSQLStep]:
        steps = [self._create_stage_step(), self._load_stage_step()]
        if self.mode == "merge":
            if not self.target_table:
                raise OracleConfigurationError("output.target_table is required for merge mode.")
            steps.append(self._merge_step())
        return steps

    def _create_stage_step(self) -> OracleSQLStep:
        column_defs = []
        for column in self.columns:
            if self.geometry and column == self._quote_identifier(self.geometry["column"]):
                column_defs.append(f"{column} SDO_GEOMETRY")
            else:
                column_defs.append(f"{column} VARCHAR2(4000)")
        return OracleSQLStep(
            "create_oracle_stage_table",
            (
                f"CREATE TABLE {self.stage_table} ("
                + ", ".join(column_defs)
                + ")"
            ),
        )

    def _load_stage_step(self) -> OracleSQLStep:
        if not self.source_table:
            return OracleSQLStep(
                "load_oracle_stage_table",
                (
                    "-- Load cleaned rows into "
                    f"{self.stage_table} using your ETL tool, SQL*Loader, or "
                    "the application row loader before running merge mode."
                ),
            )

        return OracleSQLStep(
            "load_oracle_stage_table",
            (
                f"INSERT INTO {self.stage_table} ({self.column_list}) "
                f"SELECT {self.select_list_from_source()} FROM {self.source_table}"
            ),
        )

    def _merge_step(self) -> OracleSQLStep:
        non_key_columns = [col for col in self.columns if col not in self.key_columns]
        on_clause = " AND ".join(
            f"target.{col} = source.{col}" for col in self.key_columns
        )
        updates = ", ".join(f"target.{col} = source.{col}" for col in non_key_columns)
        insert_values = ", ".join(f"source.{col}" for col in self.columns)

        return OracleSQLStep(
            "merge_stage_into_oracle_target",
            (
                f"MERGE INTO {self.target_table} target "
                f"USING {self.stage_table} source "
                f"ON ({on_clause}) "
                f"WHEN MATCHED THEN UPDATE SET {updates} "
                f"WHEN NOT MATCHED THEN INSERT ({self.column_list}) "
                f"VALUES ({insert_values})"
            ),
        )

    @property
    def column_list(self) -> str:
        return ", ".join(self.columns)

    def select_list_from_source(self) -> str:
        selected = []
        for column in self.columns:
            if self.geometry and column == self._quote_identifier(self.geometry["column"]):
                selected.append(self._geometry_expression(column))
            else:
                selected.append(column)
        return ", ".join(selected)

    def _geometry_expression(self, column: str) -> str:
        srid = int(self.geometry.get("srid", 4326))
        source_format = self.geometry.get("source_format", "wkt")
        if source_format == "wkt":
            return f"SDO_UTIL.FROM_WKTGEOMETRY({column})"
        if source_format == "wkb":
            return f"SDO_UTIL.FROM_WKBGEOMETRY({column})"
        if source_format == "sdo_geometry":
            return column
        if source_format == "lon_lat":
            lon = self._quote_identifier(self.geometry["longitude_column"])
            lat = self._quote_identifier(self.geometry["latitude_column"])
            return (
                "SDO_GEOMETRY(2001, "
                f"{srid}, SDO_POINT_TYPE({lon}, {lat}, NULL), NULL, NULL)"
            )
        raise OracleConfigurationError(
            "output.geometry.source_format must be wkt, wkb, sdo_geometry, or lon_lat."
        )

    def _quote_qualified(self, value: str) -> str:
        if not value:
            return ""
        parts = value.split(".")
        if len(parts) == 1:
            return self._quote_identifier(parts[0])
        if len(parts) == 2:
            return ".".join(self._quote_identifier(part) for part in parts)
        raise OracleConfigurationError("Oracle names must be `table` or `schema.table`.")

    def _quote_identifier(self, value: str) -> str:
        if not IDENTIFIER_RE.match(value):
            raise OracleConfigurationError(f"Unsafe Oracle identifier: {value!r}")
        return f'"{value.upper()}"'
