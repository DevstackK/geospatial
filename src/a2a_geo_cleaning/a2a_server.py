from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from a2a.helpers.proto_helpers import (
    new_data_part,
    new_task_from_user_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentProvider,
    AgentSkill,
    TaskState,
)
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from a2a_geo_cleaning.cli import apply_cli_overrides, load_config, load_env_file
from a2a_geo_cleaning.orchestrator import CleaningOrchestrator


class GeospatialCleaningExecutor(AgentExecutor):
    def __init__(self, default_config: Path, uploads_dir: Path) -> None:
        self.default_config = default_config
        self.uploads_dir = uploads_dir

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        if context.current_task is None and context.message is not None:
            await event_queue.enqueue_event(new_task_from_user_message(context.message))
        await updater.start_work(
            updater.new_agent_message(
                [new_text_part("Running geospatial data cleaning workflow.")]
            )
        )

        try:
            request_payload = self._parse_request(context.get_user_input())
            config = self._build_config(request_payload)
            state = CleaningOrchestrator(config).run()
            audit = self._read_json(Path(config["project"]["output_dir"]) / "audit.json")
            cleaned = self._read_cleaned_dataset(config)
        except Exception as exc:  # noqa: BLE001
            await updater.failed(
                updater.new_agent_message([new_text_part(f"Cleaning failed: {exc}")])
            )
            return

        summary = {
            "status": "completed",
            "acceptedRuleCount": len(state.accepted_rules),
            "resultCount": len(state.results),
            "executionLog": state.execution_log,
            "outputDir": config["project"]["output_dir"],
        }
        await updater.add_artifact(
            [new_data_part(audit, media_type="application/json")],
            name="audit.json",
            metadata={"kind": "audit"},
        )
        if cleaned is not None:
            await updater.add_artifact(
                [new_data_part(cleaned, media_type="application/geo+json")],
                name="cleaned.geojson",
                metadata={"kind": "cleaned_dataset"},
            )
        await updater.complete(
            updater.new_agent_message(
                [
                    new_text_part(
                        "Geospatial cleaning completed. See task artifacts for audit and cleaned dataset."
                    ),
                    new_data_part(summary, media_type="application/json"),
                ]
            )
        )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.cancel(
            updater.new_agent_message([new_text_part("Cleaning task canceled.")])
        )

    def _parse_request(self, text: str) -> dict[str, Any]:
        if not text.strip():
            return {}
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return {"input": text.strip()}
        if not isinstance(payload, dict):
            raise ValueError("A2A request content must be a JSON object or input path.")
        return payload

    def _build_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        config_path = Path(payload.get("config", self.default_config))
        input_path = payload.get("input")
        output_dir = payload.get("output_dir")
        run_mode = payload.get("run_mode", "execute")
        config = load_config(config_path)

        inline_geojson = payload.get("geojson")
        if inline_geojson is not None:
            input_path = self._write_inline_geojson(inline_geojson)

        return apply_cli_overrides(
            config,
            input_path=Path(input_path) if input_path else None,
            uploads_dir=self.uploads_dir,
            run_mode=run_mode,
            output_dir=Path(output_dir) if output_dir else None,
        )

    def _write_inline_geojson(self, geojson: Any) -> Path:
        upload_dir = self.uploads_dir.resolve()
        upload_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".geojson",
            prefix="a2a-upload-",
            dir=upload_dir,
            delete=False,
        ) as handle:
            json.dump(geojson, handle)
            handle.write("\n")
            return Path(handle.name)

    def _read_json(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"{path} did not contain a JSON object.")
        return data

    def _read_cleaned_dataset(self, config: dict[str, Any]) -> dict[str, Any] | None:
        if not config.get("execution", {}).get("write_cleaned_dataset", True):
            return None

        output_dir = Path(config["project"]["output_dir"])
        input_stem = Path(config["dataset"]["path"]).stem
        candidates = [
            output_dir / f"{input_stem}-cleaned.geojson",
            output_dir / "cleaned.geojson",
        ]
        for path in candidates:
            if path.exists():
                return self._read_json(path)
        return None


def build_agent_card(base_url: str) -> AgentCard:
    return AgentCard(
        name="Geospatial A2A Cleaning Agent",
        description=(
            "Runs a deterministic geospatial data cleaning workflow and returns "
            "audit and cleaned GeoJSON artifacts."
        ),
        version="0.1.0",
        supported_interfaces=[
            AgentInterface(
                url=base_url.rstrip("/") + "/",
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        provider=AgentProvider(organization="DevstackK"),
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=["application/json", "text/plain"],
        default_output_modes=["application/json", "application/geo+json"],
        skills=[
            AgentSkill(
                id="clean-geospatial-dataset",
                name="Clean geospatial dataset",
                description=(
                    "Accepts a local input path or inline GeoJSON, runs schema, "
                    "CRS, geometry, attribute, validation, and optional Claude "
                    "planning agents, then returns audit and cleaned dataset artifacts."
                ),
                tags=["geospatial", "data-cleaning", "geojson", "a2a"],
                examples=[
                    '{"input":"examples/sample-issues.geojson","run_mode":"execute"}',
                    '{"geojson":{"type":"FeatureCollection","features":[]},"run_mode":"dry_run"}',
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "application/geo+json"],
            )
        ],
    )


def build_app(
    host: str,
    port: int,
    config: Path,
    uploads_dir: Path,
    public_url: str | None = None,
) -> Starlette:
    advertised_host = "localhost" if host == "0.0.0.0" else host
    base_url = public_url or f"http://{advertised_host}:{port}"
    agent_card = build_agent_card(base_url)
    request_handler = DefaultRequestHandler(
        agent_executor=GeospatialCleaningExecutor(config, uploads_dir),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )
    routes = [
        *create_agent_card_routes(agent_card),
        *create_jsonrpc_routes(
            request_handler,
            rpc_url="/",
            enable_v0_3_compat=True,
        ),
    ]
    return Starlette(
        routes=routes,
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_methods=["*"],
                allow_headers=["*"],
            )
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the official A2A JSON-RPC server for geospatial cleaning."
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--config", type=Path, default=Path("config/example.yaml"))
    parser.add_argument("--uploads-dir", type=Path, default=Path("data/uploads"))
    parser.add_argument("--public-url", help="Public base URL to advertise in the agent card.")
    args = parser.parse_args()

    load_env_file()

    import uvicorn

    uvicorn.run(
        build_app(
            host=args.host,
            port=args.port,
            config=args.config,
            uploads_dir=args.uploads_dir,
            public_url=args.public_url,
        ),
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    main()
