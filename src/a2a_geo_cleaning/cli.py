from __future__ import annotations

import argparse
import os
from copy import deepcopy
from pathlib import Path

import yaml

from a2a_geo_cleaning.orchestrator import CleaningOrchestrator

SUPPORTED_EXTENSIONS = {
    ".geojson",
    ".json",
    ".gpkg",
    ".shp",
    ".fgb",
}


def load_env_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'\"")
            if key:
                os.environ.setdefault(key, value)


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Config must be a YAML object.")
    return config


def find_latest_upload(uploads_dir: Path) -> Path:
    candidates = [
        path
        for path in uploads_dir.glob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if not candidates:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise FileNotFoundError(
            f"No supported geospatial files found in {uploads_dir}. "
            f"Supported extensions: {supported}."
        )
    return max(candidates, key=lambda path: path.stat().st_mtime)


def apply_cli_overrides(
    config: dict,
    input_path: Path | None,
    uploads_dir: Path,
    run_mode: str | None,
    output_dir: Path | None,
) -> dict:
    updated = deepcopy(config)
    project = updated.setdefault("project", {})
    dataset = updated.setdefault("dataset", {})
    is_postgis = dataset.get("source") == "postgis"

    selected_input = None
    if not is_postgis or input_path:
        selected_input = input_path or find_latest_upload(uploads_dir)
        selected_input = selected_input.expanduser().resolve()
        dataset["path"] = str(selected_input)
        if selected_input.suffix.lower() != ".gpkg":
            dataset["layer"] = dataset.get("layer") if input_path is None else None

    if run_mode:
        project["run_mode"] = run_mode
    elif project.get("run_mode") == "dry_run":
        project["run_mode"] = "execute"

    if output_dir:
        project["output_dir"] = str(output_dir.expanduser().resolve())
    elif is_postgis:
        table_name = str(dataset.get("table", "postgis-dataset")).split(".")[-1]
        project["output_dir"] = str(Path("runs") / f"{table_name}-cleaning")
    else:
        project["output_dir"] = str(
            Path("runs") / f"{selected_input.stem}-cleaning"
        )

    if selected_input:
        project["name"] = project.get("name") or f"{selected_input.stem}-cleaning"
    else:
        project["name"] = project.get("name") or f"{dataset.get('table')}-cleaning"
    return updated


def main() -> None:
    load_env_file()

    parser = argparse.ArgumentParser(
        description="Run an A2A geospatial data cleaning workflow."
    )
    parser.add_argument(
        "config",
        type=Path,
        nargs="?",
        default=Path("config/example.yaml"),
        help="Path to workflow YAML config. Defaults to config/example.yaml.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Uploaded geospatial file to clean. If omitted, the newest supported file in data/uploads is used.",
    )
    parser.add_argument(
        "--uploads-dir",
        type=Path,
        default=Path("data/uploads"),
        help="Folder to scan when --input is omitted.",
    )
    parser.add_argument(
        "--run-mode",
        choices=["dry_run", "execute"],
        help="Override project.run_mode from the config.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for cleaned output and audit.json.",
    )
    args = parser.parse_args()

    config = apply_cli_overrides(
        load_config(args.config),
        input_path=args.input,
        uploads_dir=args.uploads_dir,
        run_mode=args.run_mode,
        output_dir=args.output_dir,
    )

    state = CleaningOrchestrator(config).run()
    report_result = state.results[-1]
    print(report_result.summary)


if __name__ == "__main__":
    main()
