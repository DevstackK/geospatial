from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any


IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class OracleIntrospectionError(ValueError):
    pass


@dataclass(frozen=True)
class OracleProfilePlan:
    table: str
    sql_steps: list[dict[str, str]]


class OracleIntrospector:
    def profile_table(self, request: dict[str, Any]) -> dict[str, Any]:
        table = self._quote_qualified(request["table"])
        geom_column = self._quote_identifier(request.get("geometry_column", "GEOM"))
        id_column = self._quote_identifier(request.get("id_column", "ASSET_ID"))
        status_column = self._quote_identifier(request.get("status_column", "STATUS"))
        srid = int(request.get("srid", 4326))
        plan = self.build_profile_plan(table, geom_column, id_column, status_column, srid)

        if request.get("dry_run", False):
            return {
                "status": "dry_run",
                "engine": "oracle",
                "table": table,
                "sql_steps": plan.sql_steps,
            }

        dsn = request.get("dsn") or os.environ.get(request.get("dsn_env", "GCOMM_ORACLE_DSN"))
        user = request.get("user") or os.environ.get(request.get("user_env", "GCOMM_ORACLE_USER"))
        password = request.get("password") or os.environ.get(
            request.get("password_env", "GCOMM_ORACLE_PASSWORD")
        )
        if not all([dsn, user, password]):
            raise OracleIntrospectionError(
                "Set dsn/user/password or GCOMM_ORACLE_DSN, GCOMM_ORACLE_USER, "
                "and GCOMM_ORACLE_PASSWORD for live Oracle profiling."
            )

        try:
            import oracledb
        except ImportError as exc:
            raise OracleIntrospectionError(
                "Install worker dependencies with `pip install -e .[worker,oracle]`."
            ) from exc

        results: list[dict[str, Any]] = []
        with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
            with conn.cursor() as cur:
                for step in plan.sql_steps:
                    cur.execute(step["sql"])
                    columns = [column[0].lower() for column in cur.description]
                    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
                    results.append({"name": step["name"], "rows": rows})

        return {
            "status": "profiled",
            "engine": "oracle",
            "table": table,
            "results": results,
        }

    def build_profile_plan(
        self,
        table: str,
        geom_column: str,
        id_column: str,
        status_column: str,
        srid: int,
    ) -> OracleProfilePlan:
        return OracleProfilePlan(
            table=table,
            sql_steps=[
                {
                    "name": "row_count",
                    "sql": f"SELECT COUNT(*) AS row_count FROM {table}",
                },
                {
                    "name": "null_id_and_geometry_counts",
                    "sql": (
                        "SELECT "
                        f"SUM(CASE WHEN {id_column} IS NULL THEN 1 ELSE 0 END) AS null_ids, "
                        f"SUM(CASE WHEN {geom_column} IS NULL THEN 1 ELSE 0 END) AS null_geometries "
                        f"FROM {table}"
                    ),
                },
                {
                    "name": "duplicate_ids",
                    "sql": (
                        f"SELECT {id_column}, COUNT(*) AS duplicate_count "
                        f"FROM {table} "
                        f"WHERE {id_column} IS NOT NULL "
                        f"GROUP BY {id_column} HAVING COUNT(*) > 1 "
                        "FETCH FIRST 100 ROWS ONLY"
                    ),
                },
                {
                    "name": "status_distribution",
                    "sql": (
                        f"SELECT {status_column}, COUNT(*) AS row_count "
                        f"FROM {table} GROUP BY {status_column} ORDER BY row_count DESC"
                    ),
                },
                {
                    "name": "srid_distribution",
                    "sql": (
                        f"SELECT {geom_column}.SDO_SRID AS srid, COUNT(*) AS row_count "
                        f"FROM {table} WHERE {geom_column} IS NOT NULL "
                        f"GROUP BY {geom_column}.SDO_SRID ORDER BY row_count DESC"
                    ),
                },
                {
                    "name": "srid_mismatches",
                    "sql": (
                        f"SELECT COUNT(*) AS mismatch_count FROM {table} "
                        f"WHERE {geom_column} IS NOT NULL "
                        f"AND NVL({geom_column}.SDO_SRID, -1) <> {srid}"
                    ),
                },
                {
                    "name": "invalid_geometries",
                    "sql": (
                        "SELECT validation_result, COUNT(*) AS row_count FROM ("
                        f"SELECT SDO_GEOM.VALIDATE_GEOMETRY_WITH_CONTEXT({geom_column}, 0.005) "
                        f"AS validation_result FROM {table} WHERE {geom_column} IS NOT NULL"
                        ") WHERE validation_result <> 'TRUE' "
                        "GROUP BY validation_result ORDER BY row_count DESC"
                    ),
                },
            ],
        )

    def _quote_qualified(self, value: str) -> str:
        parts = value.split(".")
        if len(parts) not in {1, 2}:
            raise OracleIntrospectionError("Oracle names must be `table` or `schema.table`.")
        return ".".join(self._quote_identifier(part) for part in parts)

    def _quote_identifier(self, value: str) -> str:
        if not IDENTIFIER_RE.match(value):
            raise OracleIntrospectionError(f"Unsafe Oracle identifier: {value!r}")
        return f'"{value.upper()}"'
