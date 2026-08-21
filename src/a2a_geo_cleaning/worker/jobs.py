from __future__ import annotations

import json
import traceback
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from a2a_geo_cleaning.orchestrator import CleaningOrchestrator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobRecord:
    id: str
    status: str
    config: dict[str, Any]
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    events: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "events": self.events,
            "result": self.result,
            "error": self.error,
        }


class InMemoryJobStore:
    def __init__(self, output_root: Path = Path("runs/jobs"), max_workers: int = 2) -> None:
        self.output_root = output_root
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.jobs: dict[str, JobRecord] = {}
        self.lock = Lock()

    def submit(self, config: dict[str, Any], run_mode: str | None = None) -> JobRecord:
        job_id = str(uuid4())
        job_config = deepcopy(config)
        project = job_config.setdefault("project", {})
        if run_mode:
            project["run_mode"] = run_mode
        project.setdefault("name", f"geoflow-job-{job_id[:8]}")
        project["output_dir"] = str(self.output_root / job_id)

        job = JobRecord(id=job_id, status="queued", config=job_config)
        job.events.append(self._event("queued", "Job accepted by GeoFlow worker."))
        with self.lock:
            self.jobs[job_id] = job
        self.executor.submit(self._run_job, job_id)
        return job

    def get(self, job_id: str) -> JobRecord | None:
        with self.lock:
            return self.jobs.get(job_id)

    def list(self) -> list[JobRecord]:
        with self.lock:
            return sorted(self.jobs.values(), key=lambda job: job.created_at, reverse=True)

    def _run_job(self, job_id: str) -> None:
        self._update(job_id, "running", "Worker started cleansing workflow.")
        try:
            state = CleaningOrchestrator(self.jobs[job_id].config).run()
            output_dir = Path(self.jobs[job_id].config["project"]["output_dir"])
            audit_path = output_dir / "audit.json"
            audit = None
            if audit_path.exists():
                with audit_path.open("r", encoding="utf-8") as handle:
                    audit = json.load(handle)
            result = {
                "accepted_rule_count": len(state.accepted_rules),
                "execution_log": state.execution_log,
                "output_dir": str(output_dir),
                "audit": audit,
            }
            self._complete(job_id, result)
        except Exception as exc:  # noqa: BLE001
            self._fail(job_id, f"{exc}", traceback.format_exc())

    def _complete(self, job_id: str, result: dict[str, Any]) -> None:
        with self.lock:
            job = self.jobs[job_id]
            job.status = "completed"
            job.result = result
            job.updated_at = utc_now()
            job.events.append(self._event("completed", "Workflow completed."))

    def _fail(self, job_id: str, error: str, details: str) -> None:
        with self.lock:
            job = self.jobs[job_id]
            job.status = "failed"
            job.error = error
            job.updated_at = utc_now()
            job.events.append(self._event("failed", error, {"traceback": details}))

    def _update(self, job_id: str, status: str, message: str) -> None:
        with self.lock:
            job = self.jobs[job_id]
            job.status = status
            job.updated_at = utc_now()
            job.events.append(self._event(status, message))

    def _event(
        self, status: str, message: str, details: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return {
            "at": utc_now(),
            "status": status,
            "message": message,
            "details": details or {},
        }
