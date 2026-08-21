from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class AgentRole(str, Enum):
    INTAKE = "intake"
    SCHEMA = "schema"
    CRS = "crs"
    GEOMETRY = "geometry"
    ATTRIBUTE = "attribute"
    LLM_PLANNER = "llm_planner"
    VALIDATION = "validation"
    REPORT = "report"


class RuleType(str, Enum):
    NORMALIZE_CRS = "normalize_crs"
    MAKE_VALID = "make_valid"
    DROP_EMPTY_GEOMETRY = "drop_empty_geometry"
    FLAG_DUPLICATES = "flag_duplicates"
    TRIM_STRING = "trim_string"
    NORMALIZE_CATEGORY = "normalize_category"
    REQUIRE_COLUMN = "require_column"
    CHECK_BOUNDS = "check_bounds"
    VALIDATE_PARALLEL_ASSOCIATION = "validate_parallel_association"


@dataclass(frozen=True)
class AgentMessage:
    sender: AgentRole
    recipient: AgentRole
    message_type: str
    payload: dict[str, Any]
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass(frozen=True)
class CleaningRule:
    rule_type: RuleType
    target: str
    parameters: dict[str, Any]
    confidence: float
    reason: str
    review_required: bool = False


@dataclass(frozen=True)
class AgentResult:
    agent: AgentRole
    summary: str
    observations: list[dict[str, Any]] = field(default_factory=list)
    proposed_rules: list[CleaningRule] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowState:
    config: dict[str, Any]
    dataset_profile: dict[str, Any] = field(default_factory=dict)
    results: list[AgentResult] = field(default_factory=list)
    accepted_rules: list[CleaningRule] = field(default_factory=list)
    execution_log: list[dict[str, Any]] = field(default_factory=list)

    def add_result(self, result: AgentResult) -> None:
        self.results.append(result)
        self.accepted_rules.extend(result.proposed_rules)
