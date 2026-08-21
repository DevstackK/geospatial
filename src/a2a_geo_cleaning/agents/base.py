from __future__ import annotations

from abc import ABC, abstractmethod

from a2a_geo_cleaning.contracts import AgentResult, WorkflowState


class Agent(ABC):
    @abstractmethod
    def run(self, state: WorkflowState) -> AgentResult:
        """Run the agent against the shared workflow state."""

