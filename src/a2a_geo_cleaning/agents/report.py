from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from a2a_geo_cleaning.agents.base import Agent
from a2a_geo_cleaning.contracts import AgentResult, AgentRole, WorkflowState


class ReportAgent(Agent):
    def run(self, state: WorkflowState) -> AgentResult:
        output_dir = Path(state.config["project"]["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        audit_path = output_dir / "audit.json"

        audit = {
            "project": state.config["project"],
            "dataset_profile": state.dataset_profile,
            "agent_results": [asdict(result) for result in state.results],
            "accepted_rules": [asdict(rule) for rule in state.accepted_rules],
            "execution_log": state.execution_log,
        }
        audit_path.write_text(json.dumps(audit, indent=2, default=str) + "\n")

        return AgentResult(
            agent=AgentRole.REPORT,
            summary=f"Audit report written to {audit_path}.",
            observations=[{"type": "audit_path", "path": str(audit_path)}],
        )

