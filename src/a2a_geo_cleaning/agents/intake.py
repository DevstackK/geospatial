from __future__ import annotations

from pathlib import Path

from a2a_geo_cleaning.agents.base import Agent
from a2a_geo_cleaning.contracts import AgentResult, AgentRole, WorkflowState


class IntakeAgent(Agent):
    def run(self, state: WorkflowState) -> AgentResult:
        dataset = state.config["dataset"]
        source = dataset.get("source", "file")

        if source in {"postgis", "oracle"}:
            table = dataset.get("table")
            geom_column = dataset.get("geometry_column", "geom")
            state.dataset_profile.update(
                {
                    "source": source,
                    "table": table,
                    "geometry_column": geom_column,
                    "id_column": dataset.get("id_column"),
                    "target_crs": dataset.get("target_crs"),
                }
            )

            return AgentResult(
                agent=AgentRole.INTAKE,
                summary=f"{source.title()} dataset intake metadata captured.",
                observations=[
                    {
                        "type": f"{source}_table",
                        "table": table,
                        "geometry_column": geom_column,
                    }
                ],
            )

        path = Path(dataset["path"])
        exists = path.exists()

        state.dataset_profile.update(
            {
                "source": "file",
                "path": str(path),
                "path_exists": exists,
                "layer": dataset.get("layer"),
                "id_column": dataset.get("id_column"),
                "target_crs": dataset.get("target_crs"),
            }
        )

        return AgentResult(
            agent=AgentRole.INTAKE,
            summary="Dataset intake metadata captured.",
            observations=[
                {
                    "type": "dataset_path",
                    "path": str(path),
                    "exists": exists,
                }
            ],
        )
