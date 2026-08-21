from __future__ import annotations

from a2a_geo_cleaning.agents.base import Agent
from a2a_geo_cleaning.contracts import (
    AgentResult,
    AgentRole,
    CleaningRule,
    RuleType,
    WorkflowState,
)


class AttributeAgent(Agent):
    def run(self, state: WorkflowState) -> AgentResult:
        rule_config = state.config.get("rules", {})
        rules: list[CleaningRule] = []

        for column in rule_config.get("string_trim_columns", []):
            rules.append(
                CleaningRule(
                    rule_type=RuleType.TRIM_STRING,
                    target=column,
                    parameters={"column": column},
                    confidence=0.99,
                    reason="Configured string column should be whitespace-normalized.",
                )
            )

        for column, mapping in rule_config.get("category_maps", {}).items():
            rules.append(
                CleaningRule(
                    rule_type=RuleType.NORMALIZE_CATEGORY,
                    target=column,
                    parameters={"column": column, "mapping": mapping},
                    confidence=0.92,
                    reason="Configured category map standardizes known variants.",
                )
            )

        id_column = state.config["dataset"].get("id_column")
        if id_column:
            rules.append(
                CleaningRule(
                    rule_type=RuleType.FLAG_DUPLICATES,
                    target=id_column,
                    parameters={"column": id_column},
                    confidence=0.95,
                    reason="Identifier duplicates should be visible in the audit report.",
                    review_required=True,
                )
            )

        return AgentResult(
            agent=AgentRole.ATTRIBUTE,
            summary=f"Prepared {len(rules)} attribute cleaning rules.",
            proposed_rules=rules,
        )

