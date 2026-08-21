from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from a2a_geo_cleaning.cli import load_config, load_env_file
from a2a_geo_cleaning.worker.jobs import InMemoryJobStore
from a2a_geo_cleaning.worker.oracle_introspection import OracleIntrospector


def json_error(message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status_code)


class GeoFlowWorkerAPI:
    def __init__(self, default_config: Path, output_root: Path) -> None:
        self.default_config = default_config
        self.jobs = InMemoryJobStore(output_root=output_root)
        self.oracle = OracleIntrospector()

    async def health(self, request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "geoflow-worker"})

    async def create_job(self, request: Request) -> JSONResponse:
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                return json_error("Job payload must be a JSON object.")
            config = self._config_from_payload(payload)
            job = self.jobs.submit(config, run_mode=payload.get("run_mode"))
            return JSONResponse(job.snapshot(), status_code=202)
        except Exception as exc:  # noqa: BLE001
            return json_error(str(exc))

    async def list_jobs(self, request: Request) -> JSONResponse:
        return JSONResponse({"jobs": [job.snapshot() for job in self.jobs.list()]})

    async def get_job(self, request: Request) -> JSONResponse:
        job = self.jobs.get(request.path_params["job_id"])
        if job is None:
            return json_error("Job not found.", status_code=404)
        return JSONResponse(job.snapshot())

    async def get_job_events(self, request: Request) -> JSONResponse:
        job = self.jobs.get(request.path_params["job_id"])
        if job is None:
            return json_error("Job not found.", status_code=404)
        return JSONResponse({"job_id": job.id, "events": job.events})

    async def profile_oracle(self, request: Request) -> JSONResponse:
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                return json_error("Profile payload must be a JSON object.")
            return JSONResponse(self.oracle.profile_table(payload))
        except Exception as exc:  # noqa: BLE001
            return json_error(str(exc))

    def _config_from_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "config" in payload:
            config = payload["config"]
            if not isinstance(config, dict):
                raise ValueError("payload.config must be a JSON object.")
            return config
        if "config_path" in payload:
            return load_config(Path(payload["config_path"]))
        return load_config(self.default_config)


def build_app(
    default_config: Path = Path("config/gcomm-iqgeo.oracle.yaml"),
    output_root: Path = Path("runs/jobs"),
) -> Starlette:
    api = GeoFlowWorkerAPI(default_config=default_config, output_root=output_root)
    routes = [
        Route("/health", api.health, methods=["GET"]),
        Route("/api/jobs", api.create_job, methods=["POST"]),
        Route("/api/jobs", api.list_jobs, methods=["GET"]),
        Route("/api/jobs/{job_id}", api.get_job, methods=["GET"]),
        Route("/api/jobs/{job_id}/events", api.get_job_events, methods=["GET"]),
        Route("/api/oracle/profile", api.profile_oracle, methods=["POST"]),
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
    parser = argparse.ArgumentParser(description="Run the GeoFlow IQ worker API.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--config", type=Path, default=Path("config/gcomm-iqgeo.oracle.yaml"))
    parser.add_argument("--output-root", type=Path, default=Path("runs/jobs"))
    args = parser.parse_args()

    load_env_file()

    import uvicorn

    uvicorn.run(
        build_app(default_config=args.config, output_root=args.output_root),
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    main()
