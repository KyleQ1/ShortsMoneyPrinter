"""The recreate pipeline — runs in-process (desktop app; no queue/worker).

paste URL → ingest → analyze → script → assets → tts → captions → render → MP4.
Human-in-the-loop by design: one run = one video the user chose. No publishing,
no autonomy, and no hosted account system.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app import store
from app.config import get_settings
from app.models import CreateMode, Job, JobStatus
from app.services import analyze, assets, captions, ingest, render, script, tts

log = logging.getLogger("omp")


def run_pipeline(job_id: str) -> Job:
    """Execute a job to completion. Returns the final Job (status DONE or FAILED)."""
    job = store.get_job(job_id)
    if job is None:
        raise ValueError(f"No such job: {job_id}")

    settings = get_settings()
    work_dir = Path(settings.app.work_dir) / job_id
    work_dir.mkdir(parents=True, exist_ok=True)
    out_dir = Path(settings.app.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    aspect = job.request.aspect

    def step(status: JobStatus) -> None:
        log.info("[%s] %s", job_id, status.value)
        store.set_status(job_id, status)

    try:
        if job.request.mode is CreateMode.FORMULA:
            raise NotImplementedError("Formula/series mode is a hosted/cloud feature.")

        # 1. INGEST — transcript + metadata only; source media is transient, never re-hosted.
        step(JobStatus.INGESTING)
        source = ingest.fetch_source(job.request.source_url)

        # 2. ANALYZE — extract the winning formula (hook, structure, pacing, search terms).
        step(JobStatus.ANALYZING)
        job.blueprint = analyze.build_blueprint(source)

        # 3. SCRIPT — original narration in that shape (spin, don't copy).
        step(JobStatus.SCRIPTING)
        job.script = script.generate(job.blueprint)
        store.save_job(job)

        # 4. ASSETS — stock footage (Pexels→Pixabay fallback) sized to the script.
        step(JobStatus.SOURCING)
        clips = assets.gather(job.blueprint, job.script, work_dir, aspect)

        # 5. VOICE — edge-tts narration.
        step(JobStatus.VOICING)
        audio = tts.synthesize(job.script, job.request.voice, str(work_dir / "narration.mp3"))

        # 6. CAPTIONS — word-level karaoke (.ass) timed to the narration.
        step(JobStatus.CAPTIONING)
        caps = captions.align(audio, work_dir, job.blueprint.caption_style, aspect)

        # 7. RENDER — ffmpeg filter-graph compose → MP4.
        step(JobStatus.RENDERING)
        out_path = str(out_dir / f"{job_id}.mp4")
        render.compose(clips, audio, caps, out_path, aspect)
        job.output_path = out_path

        job.status = JobStatus.DONE
        store.save_job(job)
        log.info("[%s] done → %s", job_id, out_path)
        return job

    except Exception as exc:  # noqa: BLE001 — surface failure on the job
        job.error = f"{type(exc).__name__}: {exc}"
        job.status = JobStatus.FAILED
        store.save_job(job)
        log.error("[%s] failed: %s", job_id, job.error)
        return job
