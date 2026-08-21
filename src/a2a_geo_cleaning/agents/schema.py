from __future__ import annotations

from a2a_geo_cleaning.agents.base import Agent
from a2a_geo_cleaning.contracts import (
    AgentResult,
    AgentRole,
    CleaningRule,
    RuleType,
    WorkflowState,
)


class SchemaAgent(Agent):
    def run(self, state: WorkflowState) -> AgentResult:
        required_columns = state.config["dataset"].get("required_columns", [])
        rules = [
            CleaningRule(
                rule_type=RuleType.REQUIRE_COLUMN,
                target=column,
                parameters={"column": column},
                confidence=1.0,
                reason="Column is declared as required by workflow config.",
            )
            for column in required_columns
        ]

        return AgentResult(
            agent=AgentRole.SCHEMA,
            summary=f"Prepared {len(rules)} required-column checks.",
            proposed_rules=rules,
            metrics={"required_column_count": len(required_columns)},
        )

