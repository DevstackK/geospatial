from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any
from urllib import request

from a2a_geo_cleaning.agents.base import Agent
from a2a_geo_cleaning.contracts import AgentResult, AgentRole, WorkflowState


class LLMRulePlannerAgent(Agent):
    def run(self, state: WorkflowState) -> AgentResult:
        llm_config = state.config.get("llm", {})
        if not llm_config.get("enabled", False):
            return AgentResult(
                agent=AgentRole.LLM_PLANNER,
                summary="LLM planner skipped because it is disabled.",
            )

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return AgentResult(
                agent=AgentRole.LLM_PLANNER,
                summary="Claude planner skipped because ANTHROPIC_API_KEY is not set.",
                observations=[
                    {
                        "type": "llm_setup",
                        "status": "missing_api_key",
                        "fix": "Set ANTHROPIC_API_KEY and rerun with llm.enabled: true.",
                    }
                ],
            )

        model = llm_config.get("model", "claude-sonnet-4-20250514")
        payload = {
            "model": model,
            "max_tokens": int(llm_config.get("max_tokens", 1200)),
            "messages": [
                {
                    "role": "user",
                    "content": self._build_prompt(state),
                }
            ],
        }

        try:
            response = self._messages_create(api_key, payload)
            text = self._extract_output_text(response)
            recommendations = self._parse_recommendations(text)
        except Exception as exc:  # noqa: BLE001
            return AgentResult(
                agent=AgentRole.LLM_PLANNER,
                summary="LLM planner failed; deterministic rules are still available.",
                observations=[
                    {
                        "type": "llm_error",
                        "status": "failed",
                        "message": str(exc),
                    }
                ],
            )

        return AgentResult(
            agent=AgentRole.LLM_PLANNER,
            summary=f"Claude planner returned {len(recommendations)} recommendations.",
            observations=[
                {
                    "type": "llm_recommendations",
                    "model": model,
                    "recommendations": recommendations,
                }
            ],
            metrics={"recommendation_count": len(recommendations), "model": model},
        )

    def _build_prompt(self, state: WorkflowState) -> str:
        context = {
            "dataset_profile": state.dataset_profile,
            "configured_dataset": state.config.get("dataset", {}),
            "configured_rules": state.config.get("rules", {}),
            "deterministic_rules": [asdict(rule) for rule in state.accepted_rules],
            "agent_summaries": [
                {
                    "agent": result.agent.value,
                    "summary": result.summary,
                    "metrics": result.metrics,
                    "observations": result.observations[:8],
                }
                for result in state.results
            ],
        }
        return (
            "You are reviewing a geospatial data cleaning workflow. "
            "Return only JSON with this shape: "
            '{"recommendations":[{"issue":"...","recommended_fix":"...",'
            '"risk":"low|medium|high","requires_human_review":true|false}]}. '
            "Do not suggest direct edits to geometry coordinates unless they are "
            "deterministic GIS operations such as make_valid, drop empty geometry, "
            "reproject CRS, trim strings, normalize categories, or flag duplicates.\n\n"
            f"Workflow context:\n{json.dumps(context, default=str)}"
        )

    def _messages_create(self, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=60) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))

    def _extract_output_text(self, response: dict[str, Any]) -> str:
        chunks: list[str] = []
        for content in response.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
        if not chunks:
            raise ValueError("Claude response did not include text output.")
        return "\n".join(chunks)

    def _parse_recommendations(self, text: str) -> list[dict[str, Any]]:
        parsed = json.loads(text)
        recommendations = parsed.get("recommendations", [])
        if not isinstance(recommendations, list):
            raise ValueError("LLM output field recommendations must be a list.")
        return recommendations
