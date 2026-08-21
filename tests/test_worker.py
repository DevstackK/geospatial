from __future__ import annotations

import time
from pathlib import Path

from a2a_geo_cleaning.worker.jobs import InMemoryJobStore
from a2a_geo_cleaning.worker.oracle_introspection import OracleIntrospector


def test_oracle_profile_dry_run_generates_introspection_sql() -> None:
    profile = OracleIntrospector().profile_table(
        {
            "dry_run": True,
            "table": "GCOMM.ASSETS",
            "geometry_column": "GEOM",
            "id_column": "ASSET_ID",
            "status_column": "STATUS",
            "srid": 4326,
        }
    )

    sql = "\n".join(step["sql"] for step in profile["sql_steps"])
    assert profile["status"] == "dry_run"
    assert profile["table"] == '"GCOMM"."ASSETS"'
    assert "COUNT(*) AS row_count" in sql
    assert "SDO_GEOM.VALIDATE_GEOMETRY_WITH_CONTEXT" in sql
    assert '"GEOM".SDO_SRID' in sql
    assert "FETCH FIRST 100 ROWS ONLY" in sql


def test_worker_job_store_runs_oracle_dry_run(tmp_path: Path) -> None:
    config = {
        "project": {
            "name": "worker-test",
            "run_mode": "dry_run",
        },
        "dataset": {
            "source": "oracle",
            "table": "GCOMM.ASSETS",
            "geometry_column": "GEOM",
            "id_column": "ASSET_ID",
            "target_crs": "EPSG:4326",
            "required_columns": ["ASSET_ID", "STATUS"],
        },
        "rules": {
            "string_trim_columns": ["STATUS"],
            "category_maps": {},
            "bounds": {"minx": -180, "miny": -90, "maxx": 180, "maxy": 90},
        },
        "execution": {
            "engine": "oracle_spatial",
            "audit_table": "IQGEO_STAGE.CLEANSING_AUDIT",
        },
    }
    jobs = InMemoryJobStore(output_root=tmp_path, max_workers=1)
    job = jobs.submit(config)

    deadline = time.time() + 2
    while time.time() < deadline:
        current = jobs.get(job.id)
        if current and current.status in {"completed", "failed"}:
            break
        time.sleep(0.01)

    current = jobs.get(job.id)
    assert current is not None
    assert current.status == "completed"
    assert current.result is not None
    assert current.result["accepted_rule_count"] > 0
    assert current.result["execution_log"][0]["engine"] == "oracle_spatial"
    assert (tmp_path / job.id / "audit.json").exists()
