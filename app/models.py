"""Core data models for a recreate job. (OSS engine: recreate → render → export.)"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CreateMode(str, Enum):
    RECREATE = "recreate"   # 1:1 — "make my version of this video"
    FORMULA = "formula"     # niche series — cloud/roadmap


class JobStatus(str, Enum):
    QUEUED = "queued"
    INGESTING = "ingesting"
    ANALYZING = "analyzing"
    SCRIPTING = "scripting"
    SOURCING = "sourcing"
    VOICING = "voicing"
    CAPTIONING = "captioning"
    RENDERING = "rendering"
    DONE = "done"
    FAILED = "failed"


class AspectRatio(str, Enum):
    VERTICAL = "9:16"
    HORIZONTAL = "16:9"
    SQUARE = "1:1"

    @property
    def dimensions(self) -> tuple[int, int]:
        return {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}[self.value]

    @property
    def pexels_orientation(self) -> str:
        return {"9:16": "portrait", "16:9": "landscape", "1:1": "square"}[self.value]


class CreateRequest(BaseModel):
    """What the user submits to kick off a job."""
    mode: CreateMode = CreateMode.RECREATE
    source_url: str | None = None          # the winning short to recreate
    niche: str | None = None               # for FORMULA mode (cloud)
    aspect: AspectRatio = AspectRatio.VERTICAL
    voice: str | None = None               # override config default


class VideoBlueprint(BaseModel):
    """The analysis of the source — the 'winning formula' we recreate from."""
    hook: str                                          # the first-2-seconds hook, described
    structure: list[str] = Field(default_factory=list)  # beat-by-beat outline
    pacing_seconds: float = 2.5                         # avg shot length
    total_seconds: float = 30.0
    caption_style: str = "word-level karaoke, bold, centered"
    topic: str = ""
    audio_style: str = "upbeat"
    search_terms: list[str] = Field(default_factory=list)  # visual stock-footage queries


class Job(BaseModel):
    id: str
    status: JobStatus = JobStatus.QUEUED
    request: CreateRequest
    blueprint: VideoBlueprint | None = None
    script: str | None = None
    output_path: str | None = None
    error: str | None = None
