"""Job persistence — local SQLite (desktop app; no server DB).

Stores each job as a JSON blob keyed by id. Enough for job history + resuming a run;
the local UI reads from here. A hosted/cloud version should use a real database.
"""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

from app.config import get_settings
from app.models import CreateRequest, Job, JobStatus


def _db_path() -> Path:
    p = Path(get_settings().app.work_dir) / "omp.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
    return conn


def create_job(request: CreateRequest) -> Job:
    job = Job(id=uuid.uuid4().hex[:12], request=request)
    save_job(job)
    return job


def get_job(job_id: str) -> Job | None:
    with _conn() as conn:
        row = conn.execute("SELECT data FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return Job.model_validate_json(row[0]) if row else None


def save_job(job: Job) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO jobs (id, data) VALUES (?, ?) "
            "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (job.id, job.model_dump_json()),
        )


def set_status(job_id: str, status: JobStatus) -> None:
    if job := get_job(job_id):
        job.status = status
        save_job(job)
