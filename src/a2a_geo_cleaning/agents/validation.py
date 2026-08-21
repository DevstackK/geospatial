from __future__ import annotations

from a2a_geo_cleaning.agents.base import Agent
from a2a_geo_cleaning.contracts import AgentResult, AgentRole, WorkflowState


class ValidationAgent(Agent):
    def run(self, state: WorkflowState) -> AgentResult:
        review_threshold = state.config.get("execution", {}).get(
            "review_confidence_threshold", 0.85
        )
        needs_review = [
            rule
            for rule in state.accepted_rules
            if rule.review_required or rule.confidence < review_threshold
        ]

        return AgentResult(
            agent=AgentRole.VALIDATION,
            summary=f"Validation prepared with {len(needs_review)} rules requiring review.",
            observations=[
                {
                    "type": "review_rule",
                    "rule_type": rule.rule_type.value,
                    "target": rule.target,
                    "confidence": rule.confidence,
                    "reason": rule.reason,
                }
                for rule in needs_review
            ],
            metrics={
                "rule_count": len(state.accepted_rules),
                "review_required_count": len(needs_review),
            },
        )

