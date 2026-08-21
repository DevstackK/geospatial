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


def test_cli_does_not_require_upload_for_oracle_config(tmp_path: Path) -> None:
    config = {
        "project": {"name": "oracle-test", "run_mode": "dry_run"},
        "dataset": {
            "source": "oracle",
            "table": "GCOMM.ASSETS",
            "geometry_column": "GEOM",
        },
    }

    updated = apply_cli_overrides(
        config,
        input_path=None,
        uploads_dir=tmp_path,
        run_mode="dry_run",
        output_dir=None,
    )

    assert updated["dataset"]["source"] == "oracle"
    assert "path" not in updated["dataset"]
    assert updated["project"]["output_dir"] == "runs/ASSETS-cleaning"


def test_oracle_spatial_dry_run_generates_validation_plan(tmp_path: Path) -> None:
    config = {
        "project": {
            "name": "gcomm-to-iqgeo-test",
            "run_mode": "dry_run",
            "output_dir": str(tmp_path),
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
            "category_maps": {"STATUS": {"active ": "ACTIVE", "retired": "RETIRED"}},
            "bounds": {"minx": -180, "miny": -90, "maxx": 180, "maxy": 90},
            "parallel_association": {
                "span_table": "GCOMM.SPANS",
                "duct_table": "GCOMM.DUCTS",
                "span_id_column": "SPAN_ID",
                "span_geometry_column": "GEOM",
                "duct_id_column": "DUCT_ID",
                "duct_geometry_column": "GEOM",
                "current_match_column": "MATCHED_DUCT_ID",
                "result_table": "IQGEO_STAGE.SPAN_DUCT_MATCH_AUDIT",
                "bearing_function": "GEOM_BEARING_DEGREES",
                "max_distance": 25,
                "angle_tolerance_degrees": 25,
                "perpendicular_penalty": 1000,
                "candidate_count": 8,
            },
        },
        "execution": {
            "engine": "oracle_spatial",
            "audit_table": "IQGEO_STAGE.CLEANSING_AUDIT",
            "review_confidence_threshold": 0.85,
        },
        "oracle_pipeline": {
            "clean_table": "IQGEO_STAGE.GCOMM_ASSETS_CLEAN",
            "reject_table": "IQGEO_STAGE.GCOMM_ASSETS_REJECT",
            "quarantine_table": "IQGEO_STAGE.GCOMM_ASSETS_QUARANTINE",
            "redundant_table": "IQGEO_STAGE.GCOMM_ASSETS_REDUNDANT",
        },
        "validation": {
            "status_column": "STATUS",
            "allowed_statuses": ["ACTIVE", "PLANNED"],
            "redundant_statuses": ["RETIRED"],
        },
    }

    state = CleaningOrchestrator(config).run()

    oracle_log = state.execution_log[0]
    sql = "\n".join(step["sql"] for step in oracle_log["sql_steps"])
    assert oracle_log["status"] == "dry_run"
    assert oracle_log["engine"] == "oracle_spatial"
    assert oracle_log["table"] == '"GCOMM"."ASSETS"'
    assert "SDO_GEOM.VALIDATE_GEOMETRY_WITH_CONTEXT" in sql
    assert "ALL_TAB_COLUMNS" in sql
    assert 'UPDATE "GCOMM"."ASSETS" SET "STATUS" = TRIM("STATUS")' in sql
    assert 'CREATE TABLE "IQGEO_STAGE"."GCOMM_ASSETS_CLEAN" AS SELECT *' in sql
    assert 'CREATE TABLE "IQGEO_STAGE"."GCOMM_ASSETS_REJECT" AS SELECT *' in sql
    assert 'CREATE TABLE "IQGEO_STAGE"."GCOMM_ASSETS_QUARANTINE" AS SELECT *' in sql
    assert 'CREATE TABLE "IQGEO_STAGE"."GCOMM_ASSETS_REDUNDANT" AS SELECT *' in sql
    assert 'CREATE TABLE "IQGEO_STAGE"."SPAN_DUCT_MATCH_AUDIT" AS' in sql
    assert "SDO_NN" in sql
    assert '"GEOM_BEARING_DEGREES"' in sql
    assert "INCORRECT_ASSOCIATION" in sql
    assert "DBMS_STATS.GATHER_TABLE_STATS" in sql
    assert (tmp_path / "audit.json").exists()


def test_oracle_sink_dry_run_generates_merge_plan(tmp_path: Path) -> None:
    config = {
        "project": {
            "name": "oracle-test",
            "run_mode": "dry_run",
            "output_dir": str(tmp_path),
        },
        "dataset": {
            "source": "postgis",
            "table": "public.parcels_cleaned",
            "geometry_column": "geom",
            "id_column": "parcel_id",
            "target_crs": "EPSG:4326",
            "required_columns": ["parcel_id"],
        },
        "rules": {"string_trim_columns": [], "category_maps": {}},
        "execution": {
            "engine": "postgis",
            "audit_table": "public.cleaning_audit",
        },
        "output": {
            "sink": "oracle",
            "mode": "merge",
            "stage_table": "GIS.PARCELS_CLEANED_STAGE",
            "batch_table": "GIS.PARCELS_CLEANED_STAGE_BATCHES",
            "target_table": "GIS.PARCELS",
            "source_table": "PUBLIC.PARCELS_CLEANED_EXPORT",
            "key_columns": ["PARCEL_ID"],
            "columns": ["PARCEL_ID", "OWNER_NAME", "LAND_USE", "GEOM"],
            "field_mappings": {
                "PARCEL_ID": "SRC_PARCEL_ID",
                "OWNER_NAME": "SRC_OWNER",
            },
            "batch_size": 50000,
            "geometry": {"column": "GEOM", "source_format": "wkt", "srid": 4326},
        },
    }

    state = CleaningOrchestrator(config).run()

    oracle_log = next(log for log in state.execution_log if log.get("sink") == "oracle")
    sql = "\n".join(step["sql"] for step in oracle_log["sql_steps"])
    assert oracle_log["status"] == "dry_run"
    assert oracle_log["mode"] == "merge"
    assert 'CREATE TABLE "GIS"."PARCELS_CLEANED_STAGE"' in sql
    assert '"SRC_PARCEL_ID" AS "PARCEL_ID"' in sql
    assert '"SRC_OWNER" AS "OWNER_NAME"' in sql
    assert 'CREATE TABLE "GIS"."PARCELS_CLEANED_STAGE_BATCHES" AS' in sql
    assert "BATCH_NO" in sql
    assert "Batch window size: 50000" in sql
    assert 'MERGE INTO "GIS"."PARCELS" target' in sql
    assert 'USING "GIS"."PARCELS_CLEANED_STAGE" source' in sql
    assert "SDO_UTIL.FROM_WKTGEOMETRY" in sql
    assert (tmp_path / "audit.json").exists()
