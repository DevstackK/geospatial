from __future__ import annotations

import json
import sqlite3
import traceback
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

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
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    progress: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None
    approved_at: str | None = None

    @property
    def requires_approval(self) -> bool:
        return self.config.get("project", {}).get("run_mode") == "execute" and not self.approved_at

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "progress": self.progress,
            "events": self.events,
            "checkpoints": self.checkpoints,
            "result": self.result,
            "error": self.error,
            "approved_at": self.approved_at,
            "requires_approval": self.requires_approval,
        }

    def persisted_snapshot(self) -> dict[str, Any]:
        snapshot = self.snapshot()
        snapshot["config"] = self.config
        return snapshot


class SQLiteJobStore:
    def __init__(self, output_root: Path = Path("runs/jobs"), max_workers: int = 2) -> None:
        self.output_root = output_root
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.database_path = self.output_root / "jobs.sqlite3"
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.jobs: dict[str, JobRecord] = {}
        self.lock = Lock()
        self._init_database()
        self._load_jobs()

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
        if job.requires_approval:
            job.status = "awaiting_approval"
            job.events.append(
                self._event(
                    "awaiting_approval",
                    "Execute job is waiting for operator approval.",
                )
            )

        with self.lock:
            self.jobs[job_id] = job
            self._save_job(job)
        if job.status == "queued":
            self.executor.submit(self._run_job, job_id)
        return job

    def approve(self, job_id: str, operator: str = "operator") -> JobRecord | None:
        with self.lock:
            job = self.jobs.get(job_id)
            if job is None:
                return None
            job.approved_at = utc_now()
            job.status = "queued"
            job.updated_at = utc_now()
            job.events.append(self._event("approved", f"Execute approved by {operator}."))
            self._save_job(job)
        self.executor.submit(self._run_job, job_id)
        return job

    def resume(self, job_id: str) -> JobRecord | None:
        with self.lock:
            job = self.jobs.get(job_id)
            if job is None or job.status not in {"failed", "interrupted"}:
                return job
            job.status = "queued"
            job.error = None
            job.updated_at = utc_now()
            job.events.append(self._event("queued", "Job queued for resume."))
            self._save_job(job)
        self.executor.submit(self._run_job, job_id)
        return job

    def get(self, job_id: str) -> JobRecord | None:
        with self.lock:
            return self.jobs.get(job_id)

    def list(self) -> list[JobRecord]:
        with self.lock:
            return sorted(self.jobs.values(), key=lambda job: job.created_at, reverse=True)

    def _run_job(self, job_id: str) -> None:
        self._update(job_id, "running", "Worker started cleansing workflow.", progress=5)
        self._checkpoint(job_id, "job_started", "Worker picked up the job.", progress=10)
        try:
            with self.lock:
                config = deepcopy(self.jobs[job_id].config)
            self._checkpoint(job_id, "rules_planned", "Preparing validation and import plan.", progress=30)
            state = CleaningOrchestrator(config).run()
            self._checkpoint(job_id, "workflow_executed", "Backend workflow returned.", progress=80)
            output_dir = Path(config["project"]["output_dir"])
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
            job.progress = 100
            job.result = result
            job.updated_at = utc_now()
            job.events.append(self._event("completed", "Workflow completed."))
            job.checkpoints.append(self._checkpoint_payload("completed", "Workflow completed.", 100))
            self._save_job(job)

    def _fail(self, job_id: str, error: str, details: str) -> None:
        with self.lock:
            job = self.jobs[job_id]
            job.status = "failed"
            job.error = error
            job.updated_at = utc_now()
            job.events.append(self._event("failed", error, {"traceback": details}))
            self._save_job(job)

    def _update(
        self, job_id: str, status: str, message: str, progress: int | None = None
    ) -> None:
        with self.lock:
            job = self.jobs[job_id]
            job.status = status
            if progress is not None:
                job.progress = max(job.progress, progress)
            job.updated_at = utc_now()
            job.events.append(self._event(status, message, {"progress": job.progress}))
            self._save_job(job)

    def _checkpoint(
        self, job_id: str, name: str, message: str, progress: int | None = None
    ) -> None:
        with self.lock:
            job = self.jobs[job_id]
            if progress is not None:
                job.progress = max(job.progress, progress)
            payload = self._checkpoint_payload(name, message, job.progress)
            job.checkpoints.append(payload)
            job.events.append(self._event("checkpoint", message, payload))
            job.updated_at = utc_now()
            self._save_job(job)

    def _checkpoint_payload(self, name: str, message: str, progress: int) -> dict[str, Any]:
        return {"name": name, "message": message, "progress": progress, "at": utc_now()}

    def _event(
        self, status: str, message: str, details: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return {
            "at": utc_now(),
            "status": status,
            "message": message,
            "details": details or {},
        }

    def _init_database(self) -> None:
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    snapshot TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def _load_jobs(self) -> None:
        with sqlite3.connect(self.database_path) as conn:
            rows = conn.execute("SELECT snapshot FROM jobs").fetchall()
        for (snapshot_json,) in rows:
            snapshot = json.loads(snapshot_json)
            job = JobRecord(
                id=snapshot["id"],
                status=snapshot["status"],
                config=snapshot.get("config", {}),
                created_at=snapshot["created_at"],
                updated_at=snapshot["updated_at"],
                events=snapshot.get("events", []),
                checkpoints=snapshot.get("checkpoints", []),
                progress=int(snapshot.get("progress", 0)),
                result=snapshot.get("result"),
                error=snapshot.get("error"),
                approved_at=snapshot.get("approved_at"),
            )
            if job.status in {"queued", "running"}:
                job.status = "interrupted"
                job.events.append(
                    self._event(
                        "interrupted",
                        "Worker restarted before job completed; resume is available.",
                    )
                )
            self.jobs[job.id] = job
            self._save_job(job)

    def _save_job(self, job: JobRecord) -> None:
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO jobs (id, snapshot, updated_at) VALUES (?, ?, ?)",
                (job.id, json.dumps(job.persisted_snapshot()), job.updated_at),
            )


InMemoryJobStore = SQLiteJobStore
