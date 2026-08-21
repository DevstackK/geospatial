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
