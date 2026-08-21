from __future__ import annotations

from a2a_geo_cleaning.agents.attribute import AttributeAgent
from a2a_geo_cleaning.agents.crs import CRSAgent
from a2a_geo_cleaning.agents.geometry import GeometryAgent
from a2a_geo_cleaning.agents.intake import IntakeAgent
from a2a_geo_cleaning.agents.llm_planner import LLMRulePlannerAgent
from a2a_geo_cleaning.agents.report import ReportAgent
from a2a_geo_cleaning.agents.schema import SchemaAgent
from a2a_geo_cleaning.agents.validation import ValidationAgent
from a2a_geo_cleaning.contracts import WorkflowState
from a2a_geo_cleaning.gis.executor import GeoExecutor


class CleaningOrchestrator:
    def __init__(self, config: dict) -> None:
        self.state = WorkflowState(config=config)
        self.agents = [
            IntakeAgent(),
            SchemaAgent(),
            CRSAgent(),
            GeometryAgent(),
            AttributeAgent(),
            LLMRulePlannerAgent(),
            ValidationAgent(),
        ]

    def run(self) -> WorkflowState:
        for agent in self.agents:
            self.state.add_result(agent.run(self.state))

        GeoExecutor(self.state).execute()

        report = ReportAgent().run(self.state)
        self.state.add_result(report)
        return self.state
