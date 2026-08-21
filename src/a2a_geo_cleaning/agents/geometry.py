from __future__ import annotations

from a2a_geo_cleaning.agents.base import Agent
from a2a_geo_cleaning.contracts import (
    AgentResult,
    AgentRole,
    CleaningRule,
    RuleType,
    WorkflowState,
)


class GeometryAgent(Agent):
    def run(self, state: WorkflowState) -> AgentResult:
        rules = [
            CleaningRule(
                rule_type=RuleType.DROP_EMPTY_GEOMETRY,
                target="geometry",
                parameters={},
                confidence=0.98,
                reason="Empty geometries cannot support spatial validation.",
            ),
            CleaningRule(
                rule_type=RuleType.MAKE_VALID,
                target="geometry",
                parameters={},
                confidence=0.9,
                reason="Invalid geometries should be repaired before topology checks.",
            ),
        ]

        bounds = state.config.get("rules", {}).get("bounds")
        if bounds:
            rules.append(
                CleaningRule(
                    rule_type=RuleType.CHECK_BOUNDS,
                    target="geometry",
                    parameters=bounds,
                    confidence=0.9,
                    reason="Configured coordinate bounds guard against CRS and data errors.",
                )
            )

        association = state.config.get("rules", {}).get("parallel_association") or state.config.get(
            "validation", {}
        ).get("parallel_association")
        if association:
            rules.append(
                CleaningRule(
                    rule_type=RuleType.VALIDATE_PARALLEL_ASSOCIATION,
                    target=association.get("span_table", "spans"),
                    parameters=association,
                    confidence=0.92,
                    review_required=True,
                    reason=(
                        "Duct-span matching must consider parallel alignment, "
                        "not only nearest distance."
                    ),
                )
            )

        return AgentResult(
            agent=AgentRole.GEOMETRY,
            summary=f"Prepared {len(rules)} geometry cleaning and validation rules.",
            proposed_rules=rules,
        )
