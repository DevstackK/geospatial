from __future__ import annotations

import os
from pathlib import Path

from a2a_geo_cleaning.cli import apply_cli_overrides, find_latest_upload
from a2a_geo_cleaning.orchestrator import CleaningOrchestrator


def test_dry_run_creates_rules_and_audit(tmp_path: Path) -> None:
    config = {
        "project": {
            "name": "test",
            "run_mode": "dry_run",
            "output_dir": str(tmp_path),
        },
        "dataset": {
            "path": str(tmp_path / "missing.geojson"),
            "id_column": "id",
            "target_crs": "EPSG:4326",
            "required_columns": ["id", "name"],
        },
        "rules": {
            "string_trim_columns": ["name"],
            "category_maps": {"kind": {"a": "alpha"}},
            "bounds": {"minx": -180, "miny": -90, "maxx": 180, "maxy": 90},
        },
        "execution": {"review_confidence_threshold": 0.85},
    }

    state = CleaningOrchestrator(config).run()

    assert len(state.accepted_rules) == 9
    assert state.execution_log[0]["status"] == "dry_run"
    assert (tmp_path / "audit.json").exists()
    assert any(result.agent.value == "llm_planner" for result in state.results)


def test_cli_selects_latest_upload_and_overrides_output(tmp_path: Path) -> None:
    older = tmp_path / "older.geojson"
    newer = tmp_path / "newer.geojson"
    older.write_text("{}\n")
    newer.write_text("{}\n")
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))

    selected = find_latest_upload(tmp_path)
    config = {
        "project": {"name": "test", "run_mode": "dry_run", "output_dir": "unused"},
        "dataset": {"path": "unused", "layer": "old-layer"},
    }

    updated = apply_cli_overrides(
        config,
        input_path=selected,
        uploads_dir=tmp_path,
        run_mode="dry_run",
        output_dir=tmp_path / "out",
    )

    assert updated["dataset"]["path"] == str(selected.resolve())
    assert updated["dataset"]["layer"] is None
    assert updated["project"]["run_mode"] == "dry_run"
    assert updated["project"]["output_dir"] == str((tmp_path / "out").resolve())


def test_postgis_dry_run_generates_sql_plan(tmp_path: Path) -> None:
    config = {
        "project": {
            "name": "postgis-test",
            "run_mode": "dry_run",
            "output_dir": str(tmp_path),
        },
        "dataset": {
            "source": "postgis",
            "table": "public.parcels",
            "geometry_column": "geom",
            "id_column": "parcel_id",
            "target_crs": "EPSG:4326",
            "required_columns": ["parcel_id", "owner_name"],
        },
        "rules": {
            "string_trim_columns": ["owner_name"],
            "category_maps": {"land_use": {"res": "residential"}},
            "bounds": {"minx": -180, "miny": -90, "maxx": 180, "maxy": 90},
        },
        "execution": {
            "engine": "postgis",
            "audit_table": "public.cleaning_audit",
            "review_confidence_threshold": 0.85,
        },
    }

    state = CleaningOrchestrator(config).run()

    postgis_log = state.execution_log[0]
    sql = "\n".join(step["sql"] for step in postgis_log["sql_steps"])
    assert postgis_log["status"] == "dry_run"
    assert postgis_log["engine"] == "postgis"
    assert postgis_log["table"] == '"public"."parcels"'
    assert "ST_MakeValid" in sql
    assert "ST_Transform" in sql
    assert 'UPDATE "public"."parcels" SET "owner_name" = btrim("owner_name")' in sql
    assert "cleaning_audit" in sql
    assert (tmp_path / "audit.json").exists()


def test_cli_does_not_require_upload_for_postgis_config(tmp_path: Path) -> None:
    config = {
        "project": {"name": "postgis-test", "run_mode": "dry_run"},
        "dataset": {
            "source": "postgis",
            "table": "public.parcels",
            "geometry_column": "geom",
        },
    }

    updated = apply_cli_overrides(
        config,
        input_path=None,
        uploads_dir=tmp_path,
        run_mode="dry_run",
        output_dir=None,
    )

    assert updated["dataset"]["source"] == "postgis"
    assert "path" not in updated["dataset"]
    assert updated["project"]["output_dir"] == "runs/parcels-cleaning"
