from __future__ import annotations

from a2a_geo_cleaning.contracts import WorkflowState
from a2a_geo_cleaning.sinks.oracle import OracleSink


def publish_outputs(state: WorkflowState) -> None:
    output = state.config.get("output", {})
    if not output:
        return

    if output.get("sink") == "oracle":
        OracleSink(state).publish()
        return

    state.execution_log.append(
        {
            "status": "skipped",
            "sink": output.get("sink"),
            "message": "Unsupported output sink.",
        }
    )
