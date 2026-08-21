from __future__ import annotations

from pathlib import Path
from typing import Any

from a2a_geo_cleaning.contracts import CleaningRule, RuleType, WorkflowState
from a2a_geo_cleaning.gis.postgis import PostGISExecutor


class GeoDependencyError(RuntimeError):
    pass


class GeoExecutor:
    def __init__(self, state: WorkflowState) -> None:
        self.state = state

    def execute(self) -> None:
        if self.state.config["dataset"].get("source") == "postgis":
            PostGISExecutor(self.state).execute()
            return

        run_mode = self.state.config["project"].get("run_mode", "dry_run")
        if run_mode == "dry_run":
            self.state.execution_log.append(
                {
                    "status": "dry_run",
                    "message": "Rules were planned but not applied.",
                    "rule_count": len(self.state.accepted_rules),
                }
            )
            return

        try:
            import geopandas as gpd
        except ImportError as exc:
            raise GeoDependencyError(
                "Install geospatial dependencies with `pip install -e .[geo]`."
            ) from exc

        dataset = self.state.config["dataset"]
        input_path = Path(dataset["path"])
        layer = dataset.get("layer")
        gdf = gpd.read_file(input_path, layer=layer) if layer else gpd.read_file(input_path)

        before_count = len(gdf)
        for rule in self.state.accepted_rules:
            gdf = self._apply_rule(gdf, rule)

        output_dir = Path(self.state.config["project"]["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{input_path.stem}.cleaned.geojson"

        if self.state.config.get("execution", {}).get("write_cleaned_dataset", True):
            gdf.to_file(output_path, driver="GeoJSON")

        self.state.execution_log.append(
            {
                "status": "executed",
                "input_path": str(input_path),
                "output_path": str(output_path),
                "before_count": before_count,
                "after_count": len(gdf),
                "rule_count": len(self.state.accepted_rules),
            }
        )

    def _apply_rule(self, gdf: Any, rule: CleaningRule) -> Any:
        if rule.rule_type == RuleType.NORMALIZE_CRS:
            target_crs = rule.parameters["target_crs"]
            if gdf.crs is None:
                self.state.execution_log.append(
                    {
                        "status": "skipped",
                        "rule": rule.rule_type.value,
                        "reason": "Input CRS is missing; assign CRS manually before reprojection.",
                    }
                )
                return gdf
            return gdf.to_crs(target_crs)

        if rule.rule_type == RuleType.DROP_EMPTY_GEOMETRY:
            return gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].copy()

        if rule.rule_type == RuleType.MAKE_VALID:
            gdf = gdf.copy()
            gdf.geometry = gdf.geometry.make_valid()
            return gdf

        if rule.rule_type == RuleType.TRIM_STRING:
            column = rule.parameters["column"]
            if column in gdf.columns:
                gdf[column] = gdf[column].astype("string").str.strip()
            return gdf

        if rule.rule_type == RuleType.NORMALIZE_CATEGORY:
            column = rule.parameters["column"]
            mapping = {str(k).lower(): v for k, v in rule.parameters["mapping"].items()}
            if column in gdf.columns:
                normalized = gdf[column].astype("string").str.strip().str.lower()
                gdf[column] = normalized.map(mapping).fillna(gdf[column])
            return gdf

        if rule.rule_type == RuleType.FLAG_DUPLICATES:
            column = rule.parameters["column"]
            if column in gdf.columns:
                duplicate_count = int(gdf[column].duplicated(keep=False).sum())
                self.state.execution_log.append(
                    {
                        "status": "flagged",
                        "rule": rule.rule_type.value,
                        "column": column,
                        "duplicate_count": duplicate_count,
                    }
                )
            return gdf

        if rule.rule_type == RuleType.REQUIRE_COLUMN:
            column = rule.parameters["column"]
            if column not in gdf.columns:
                self.state.execution_log.append(
                    {
                        "status": "failed_check",
                        "rule": rule.rule_type.value,
                        "column": column,
                        "message": "Required column is missing.",
                    }
                )
            return gdf

        if rule.rule_type == RuleType.CHECK_BOUNDS:
            minx, miny, maxx, maxy = gdf.total_bounds
            expected = rule.parameters
            out_of_bounds = (
                minx < expected["minx"]
                or miny < expected["miny"]
                or maxx > expected["maxx"]
                or maxy > expected["maxy"]
            )
            self.state.execution_log.append(
                {
                    "status": "checked",
                    "rule": rule.rule_type.value,
                    "out_of_bounds": bool(out_of_bounds),
                    "bounds": [float(minx), float(miny), float(maxx), float(maxy)],
                }
            )
            return gdf

        return gdf
