from __future__ import annotations

from a2a_geo_cleaning.agents.base import Agent
from a2a_geo_cleaning.contracts import (
    AgentResult,
    AgentRole,
    CleaningRule,
    RuleType,
    WorkflowState,
)


class CRSAgent(Agent):
    def run(self, state: WorkflowState) -> AgentResult:
        target_crs = state.config["dataset"].get("target_crs")
        rules = []
        if target_crs:
            rules.append(
                CleaningRule(
                    rule_type=RuleType.NORMALIZE_CRS,
                    target="geometry",
                    parameters={"target_crs": target_crs},
                    confidence=0.95,
                    reason="Target CRS is configured for normalized output.",
                )
            )

        return AgentResult(
            agent=AgentRole.CRS,
            summary="Prepared CRS normalization rule." if rules else "No CRS target set.",
            proposed_rules=rules,
        )

