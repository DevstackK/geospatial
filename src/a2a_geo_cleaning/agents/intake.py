from __future__ import annotations

from pathlib import Path

from a2a_geo_cleaning.agents.base import Agent
from a2a_geo_cleaning.contracts import AgentResult, AgentRole, WorkflowState


class IntakeAgent(Agent):
    def run(self, state: WorkflowState) -> AgentResult:
        dataset = state.config["dataset"]
        path = Path(dataset["path"])
        exists = path.exists()

        state.dataset_profile.update(
            {
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

