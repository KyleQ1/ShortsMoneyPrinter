"""Shared remix runner for the CLI and local FastAPI app.

The runner is deliberately file-backed: every run owns a folder under ``runs/`` with
``plan.json`` as the source of truth. That keeps the OSS app easy to inspect, resume,
and debug without a database or queue.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import shlex
import shutil
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic import BaseModel, Field

from app.config import get_settings
from app.model_catalog import QUALITY_PROFILES, QualityProfile
from app.models import AspectRatio
from app.services import prompt_writer, styles, video_conditioning as vc

Quality = str
Language = Literal["auto", "en", "zh", "hi", "es", "fr", "de", "ja", "ko", "pt"]
AudioMode = Literal["source", "tts", "none", "upload"]
CaptionPosition = Literal["bottom", "center", "top"]
BlockStatus = Literal["planned", "generating", "done", "failed", "skipped"]
RunStatus = Literal["planned", "running", "done", "failed"]

RUNS_DIR = Path("runs")
MAX_BLOCK_SECONDS = 15.0
DEFAULT_TEST_SECONDS = 10.0


class UserFacingError(RuntimeError):
    """An error message that is safe to show directly in the CLI and UI."""


class CommandError(RuntimeError):
    def __init__(self, label: str, stdout: str, stderr: str) -> None:
        self.label = label
        self.stdout = stdout
        self.stderr = stderr
        output = _tail(stderr) or stdout.strip() or "command failed"
        super().__init__(f"{label}:\n{output}")

    @property
    def output(self) -> str:
        return f"{self.stderr}\n{self.stdout}".strip()


class RemixRequest(BaseModel):
    source: str = ""
    style: str = styles.DEFAULT_STYLE
    prompt: str | None = None
    video_subject_prompt: str | None = None
    video_script_prompt: str | None = None
    language: Language = "auto"
    audio_mode: AudioMode = "source"
    tts_voice: str | None = None
    quality: Quality = "local"
    max_cost: float | None = None
    captions: bool = False
    caption_position: CaptionPosition = "bottom"
    max_total_seconds: float | None = None
    local_command: str | None = None
    # Advanced overrides / inputs
    resolution: str | None = None          # "480p" | "720p" | "1080p"; None = model default
    aspect_ratio: str | None = None        # "9:16" | "16:9" | "1:1"; None = from source
    image_path: str | None = None          # uploaded still -> image-to-video (single block)
    audio_upload: str | None = None        # uploaded soundtrack (audio_mode = "upload")
    prompt_enhance: bool = False           # opt-in LLM rewrite for block prompts
    prompt_api_key: str | None = None      # request-scoped; never stored in plan.json
    prompt_model: str | None = None


class BlockPlan(BaseModel):
    index: int
    start: float
    end: float
    duration: float
    mode: str
    status: BlockStatus = "planned"
    ref_video: str
    keyframe: str
    prompt_path: str
    prompt: str
    generated_path: str
    estimated_cost: float = 0.0
    error: str | None = None


class SourceMetadata(BaseModel):
    platform: str = "local"
    title: str | None = None
    original_duration: float | None = None
    aspect_ratio: str | None = None


class RunPlan(BaseModel):
    run_id: str
    created_at: str
    status: RunStatus = "planned"
    source: str
    source_platform: str = "local"
    source_title: str | None = None
    source_path: str
    audio_path: str | None = None
    run_dir: str
    style: str
    user_prompt: str | None = None
    video_subject_prompt: str | None = None
    video_script_prompt: str | None = None
    language: Language = "auto"
    audio_mode: AudioMode = "source"
    tts_voice: str | None = None
    quality: Quality
    provider: str
    model_id: str
    model_label: str
    mode: str
    resolution: str
    width: int
    height: int
    original_duration: float = 0.0
    duration: float
    aspect_ratio: str = "9:16"
    has_audio: bool
    is_image_to_video: bool = False
    captions: bool = False
    caption_position: CaptionPosition = "bottom"
    captions_path: str | None = None
    max_cost: float | None = None
    local_command: str | None = None
    estimated_cost: float
    block_count: int
    blocks: list[BlockPlan] = Field(default_factory=list)
    final_path: str | None = None
    error: str | None = None


class RemixProvider:
    """Provider interface used by live runs and tests."""

    def generate_block(self, plan: RunPlan, block: BlockPlan) -> str:
        raise NotImplementedError


class SeedanceProvider(RemixProvider):
    def generate_block(self, plan: RunPlan, block: BlockPlan) -> str:
        profile = _quality_profile(plan.quality)
        out_path = block.generated_path
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        if profile.provider == "local":
            return _run_local_model(plan, block)

        resolution = plan.resolution or profile.resolution
        aspect = _aspect_enum(plan.aspect_ratio)
        duration = str(max(4, min(15, math.ceil(block.duration))))
        from_image = plan.is_image_to_video or profile.input_kind == "image"

        if _remote_endpoint() == "seedance2":
            from app.services.providers import seedance2

            return seedance2.generate_from_image(
                block.keyframe,
                block.prompt,
                out_path,
                aspect,
                resolution=resolution,
                duration=duration,
                model_key=plan.quality,
            )

        from app.services.providers import seedance

        if from_image:
            return seedance.generate_from_image(
                block.keyframe,
                block.prompt,
                out_path,
                aspect,
                resolution=resolution,
                duration=duration,
            )

        style = styles.get(plan.style)
        return seedance.generate_from_video(
            block.ref_video,
            block.prompt,
            out_path,
            aspect,
            resolution=resolution,
            duration=duration,
            generate_audio=False,
            match_reference=style.match_reference,
            fast="fast" in profile.model_id,
        )


def preflight_status() -> dict[str, object]:
    """Return local capability hints for UI and diagnostics."""
    cfg = get_settings().video_gen
    endpoint = _remote_endpoint()
    return {
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "ffprobe": bool(shutil.which("ffprobe")),
        "yt_dlp": bool(
            shutil.which("yt-dlp")
            or shutil.which("yt_dlp")
            or importlib.util.find_spec("yt_dlp")
        ),
        "endpoint": endpoint,
        "seedance2_cookie": bool(_temporary_seedance2_cookie()),
        "replicate_token": bool(cfg.api_key or os.environ.get("REPLICATE_API_TOKEN")),
        "replicate_package": bool(importlib.util.find_spec("replicate")),
        "fal_token": bool(cfg.api_key or os.environ.get("FAL_KEY")),
        "fal_package": bool(importlib.util.find_spec("fal_client")),
        "prompt_api_key": prompt_writer.configured(),
    }


def user_error_message(exc: Exception) -> str:
    """Collapse internal exceptions into one useful message for local users."""
    if isinstance(exc, UserFacingError):
        return str(exc)
    if isinstance(exc, FileNotFoundError):
        return str(exc)
    if isinstance(exc, ValueError):
        return str(exc)
    if isinstance(exc, CommandError):
        return str(exc)
    message = str(exc).strip()
    return message or f"{type(exc).__name__}: failed"


def _quality_profile(quality: str) -> QualityProfile:
    try:
        return QUALITY_PROFILES[quality]
    except KeyError as exc:
        available = ", ".join(QUALITY_PROFILES)
        raise ValueError(f"Unknown model {quality!r}. Choose one of: {available}") from exc


def create_plan(request: RemixRequest, runs_dir: Path = RUNS_DIR) -> RunPlan:
    """Create a dry-run plan and stop before provider calls."""
    _require_media_tools()
    if request.image_path:
        return _create_image_plan(request, runs_dir)
    if not request.source.strip():
        raise ValueError("Enter a YouTube, Instagram, TikTok URL or local video path.")
    if request.max_total_seconds is not None and request.max_total_seconds <= 0:
        raise ValueError("max_total_seconds must be greater than 0.")
    styles.get(request.style)
    profile = _quality_profile(request.quality)
    resolution = request.resolution or profile.resolution
    override_dims = _ASPECT_DIMS.get(request.aspect_ratio or "")
    run_id = _new_run_id()
    run_dir = runs_dir / run_id
    source_dir = run_dir / "source"
    audio_dir = run_dir / "audio"
    blocks_dir = run_dir / "blocks"
    prompts_dir = run_dir / "prompts"
    generated_dir = run_dir / "generated"
    for directory in (source_dir, audio_dir, blocks_dir, prompts_dir, generated_dir):
        directory.mkdir(parents=True, exist_ok=True)

    source_path = str(source_dir / "source.mp4")
    metadata = _materialize_source(request.source, source_path)
    try:
        width, height, original_duration = vc.probe(source_path)
    except Exception as exc:
        raise UserFacingError(
            "Could not read the source video. Use a public YouTube, Instagram, or TikTok "
            "URL, or a local MP4/MOV file that ffmpeg can read."
        ) from exc
    duration = original_duration
    if request.max_total_seconds is not None:
        duration = min(duration, request.max_total_seconds)
    metadata.original_duration = round(original_duration, 3)
    metadata.aspect_ratio = _aspect_label(width, height)

    has_audio = _has_audio(source_path)
    source_audio_path = str(audio_dir / "source.m4a") if has_audio else None
    if has_audio and source_audio_path:
        try:
            _extract_audio(source_path, source_audio_path, duration)
        except CommandError as exc:
            raise UserFacingError(
                "Could not extract source audio. Try another video, or rerun with a shorter "
                "max seconds value."
            ) from exc
    audio_path = _prepare_audio(request, audio_dir, source_audio_path)

    segment_plan = _plan_blocks(source_path, duration)
    block_models: list[BlockPlan] = []
    for index, (start, length) in enumerate(segment_plan):
        end = start + length
        ref_video = str(blocks_dir / f"block_{index:03d}_ref.mp4")
        keyframe = str(blocks_dir / f"block_{index:03d}_keyframe.jpg")
        prompt_path = str(prompts_dir / f"block_{index:03d}.txt")
        generated_path = str(generated_dir / f"block_{index:03d}.mp4")
        try:
            _encode_reference_block(source_path, ref_video, start, length, dims=override_dims)
            _extract_keyframe(source_path, keyframe, start + (length / 2.0))
        except CommandError as exc:
            raise UserFacingError(
                "Could not prepare a remix block from the source video. Try a shorter max "
                "seconds value or a different MP4/MOV source."
            ) from exc
        prompt = generate_prompt(
            index,
            start,
            end,
            request.style,
            request.prompt,
            request.video_subject_prompt,
            request.video_script_prompt,
            request.language,
            enhance=request.prompt_enhance,
            prompt_api_key=request.prompt_api_key,
            prompt_model=request.prompt_model,
        )
        Path(prompt_path).write_text(prompt + "\n", encoding="utf-8")
        block_models.append(
            BlockPlan(
                index=index,
                start=round(start, 3),
                end=round(end, 3),
                duration=round(length, 3),
                mode=profile.mode,
                ref_video=ref_video,
                keyframe=keyframe,
                prompt_path=prompt_path,
                prompt=prompt,
                generated_path=generated_path,
                estimated_cost=round(length * profile.cost_per_second(), 2),
            )
        )

    estimated_cost = round(duration * profile.cost_per_second(), 2)
    plan = RunPlan(
        run_id=run_id,
        created_at=datetime.now(UTC).isoformat(),
        source=request.source,
        source_platform=metadata.platform,
        source_title=metadata.title,
        source_path=source_path,
        audio_path=audio_path,
        run_dir=str(run_dir),
        style=request.style,
        user_prompt=request.prompt.strip() if request.prompt else None,
        video_subject_prompt=request.video_subject_prompt.strip() if request.video_subject_prompt else None,
        video_script_prompt=request.video_script_prompt.strip() if request.video_script_prompt else None,
        language=request.language,
        audio_mode=request.audio_mode,
        tts_voice=request.tts_voice.strip() if request.tts_voice else None,
        quality=request.quality,
        provider=profile.provider,
        model_id=profile.model_id,
        model_label=profile.model_label,
        mode=profile.mode,
        resolution=resolution,
        width=override_dims[0] if override_dims else width,
        height=override_dims[1] if override_dims else height,
        original_duration=round(original_duration, 3),
        duration=round(duration, 3),
        aspect_ratio=request.aspect_ratio or metadata.aspect_ratio or _aspect_label(width, height),
        has_audio=has_audio,
        captions=request.captions,
        caption_position=request.caption_position,
        max_cost=request.max_cost,
        local_command=_local_command_from_request(request),
        estimated_cost=estimated_cost,
        block_count=len(block_models),
        blocks=block_models,
    )
    save_plan(plan)
    return plan


def _create_image_plan(request: RemixRequest, runs_dir: Path) -> RunPlan:
    """Single-block image-to-video plan built from an uploaded still image."""
    image_path = (request.image_path or "").strip()
    if not image_path or not Path(image_path).is_file():
        raise UserFacingError("Upload an image to use image-to-video mode.")
    if request.max_total_seconds is not None and request.max_total_seconds <= 0:
        raise ValueError("max_total_seconds must be greater than 0.")
    styles.get(request.style)
    profile = _quality_profile(request.quality)
    resolution = request.resolution or profile.resolution

    run_id = _new_run_id()
    run_dir = runs_dir / run_id
    source_dir = run_dir / "source"
    audio_dir = run_dir / "audio"
    blocks_dir = run_dir / "blocks"
    prompts_dir = run_dir / "prompts"
    generated_dir = run_dir / "generated"
    for directory in (source_dir, audio_dir, blocks_dir, prompts_dir, generated_dir):
        directory.mkdir(parents=True, exist_ok=True)

    ext = Path(image_path).suffix.lower() or ".jpg"
    keyframe = str(blocks_dir / f"block_000_keyframe{ext}")
    source_copy = str(source_dir / f"image{ext}")
    shutil.copyfile(image_path, keyframe)
    shutil.copyfile(image_path, source_copy)

    if request.aspect_ratio in _ASPECT_DIMS:
        width, height = _ASPECT_DIMS[request.aspect_ratio]
        aspect = request.aspect_ratio
    else:
        iw, ih = _probe_dims(keyframe)
        width, height = vc.target_dims(iw, ih)
        aspect = _aspect_label(width, height)

    duration = float(request.max_total_seconds or DEFAULT_IMAGE_SECONDS)
    duration = max(1.0, min(float(MAX_BLOCK_SECONDS), duration))

    audio_path = _prepare_audio(request, audio_dir, None)

    prompt = generate_prompt(
        0,
        0.0,
        duration,
        request.style,
        request.prompt,
        request.video_subject_prompt,
        request.video_script_prompt,
        request.language,
        enhance=request.prompt_enhance,
        prompt_api_key=request.prompt_api_key,
        prompt_model=request.prompt_model,
    )
    prompt_path = str(prompts_dir / "block_000.txt")
    Path(prompt_path).write_text(prompt + "\n", encoding="utf-8")
    generated_path = str(generated_dir / "block_000.mp4")
    block = BlockPlan(
        index=0,
        start=0.0,
        end=round(duration, 3),
        duration=round(duration, 3),
        mode=profile.mode,
        ref_video="",
        keyframe=keyframe,
        prompt_path=prompt_path,
        prompt=prompt,
        generated_path=generated_path,
        estimated_cost=round(duration * profile.cost_per_second(), 2),
    )
    plan = RunPlan(
        run_id=run_id,
        created_at=datetime.now(UTC).isoformat(),
        source=image_path,
        source_platform="image",
        source_title=Path(image_path).name,
        source_path=source_copy,
        audio_path=audio_path,
        run_dir=str(run_dir),
        style=request.style,
        user_prompt=request.prompt.strip() if request.prompt else None,
        video_subject_prompt=request.video_subject_prompt.strip() if request.video_subject_prompt else None,
        video_script_prompt=request.video_script_prompt.strip() if request.video_script_prompt else None,
        language=request.language,
        audio_mode=request.audio_mode,
        tts_voice=request.tts_voice.strip() if request.tts_voice else None,
        quality=request.quality,
        provider=profile.provider,
        model_id=profile.model_id,
        model_label=profile.model_label,
        mode=profile.mode,
        resolution=resolution,
        width=width,
        height=height,
        original_duration=round(duration, 3),
        duration=round(duration, 3),
        aspect_ratio=aspect,
        has_audio=bool(audio_path),
        is_image_to_video=True,
        captions=request.captions,
        caption_position=request.caption_position,
        max_cost=request.max_cost,
        local_command=_local_command_from_request(request),
        estimated_cost=round(duration * profile.cost_per_second(), 2),
        block_count=1,
        blocks=[block],
    )
    save_plan(plan)
    return plan


def run_live(
    run_id: str,
    max_cost: float | None,
    provider: RemixProvider | None = None,
    runs_dir: Path = RUNS_DIR,
) -> RunPlan:
    """Generate missing blocks, then concatenate and mux source audio."""
    plan = load_plan(run_id, runs_dir)
    if max_cost is None:
        raise ValueError("max_cost is required for live runs")
    if max_cost <= 0:
        raise ValueError("max_cost must be greater than 0")
    if plan.estimated_cost > max_cost:
        raise ValueError(
            f"estimated cost ${plan.estimated_cost:.2f} exceeds max cost ${max_cost:.2f}"
        )
    plan.max_cost = max_cost
    plan.status = "running"
    plan.error = None
    save_plan(plan)

    try:
        if provider is None:
            _validate_live_preflight(plan)
            provider = SeedanceProvider()
        for block in plan.blocks:
            if Path(block.generated_path).exists() and block.status == "done":
                block.status = "skipped"
                save_plan(plan)
                continue
            block.status = "generating"
            block.error = None
            save_plan(plan)
            provider.generate_block(plan, block)
            if not Path(block.generated_path).exists():
                raise UserFacingError(
                    "The video provider finished without returning a generated block. "
                    "Check your provider dashboard and retry the run."
                )
            block.status = "done"
            save_plan(plan)

        plan.final_path = _stitch_final(plan)
        plan.status = "done"
        save_plan(plan)
        return plan
    except Exception as exc:
        message = user_error_message(exc)
        plan.status = "failed"
        plan.error = message
        for block in plan.blocks:
            if block.status == "generating":
                block.status = "failed"
                block.error = message
                break
        save_plan(plan)
        raise


def load_plan(run_id: str, runs_dir: Path = RUNS_DIR) -> RunPlan:
    path = runs_dir / run_id / "plan.json"
    if not path.exists():
        raise FileNotFoundError(f"unknown run {run_id}")
    return RunPlan.model_validate_json(path.read_text(encoding="utf-8"))


def save_plan(plan: RunPlan) -> None:
    path = Path(plan.run_dir) / "plan.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(path)


def list_runs(runs_dir: Path = RUNS_DIR) -> list[RunPlan]:
    plans: list[RunPlan] = []
    if not runs_dir.exists():
        return plans
    for path in runs_dir.glob("*/plan.json"):
        try:
            plans.append(RunPlan.model_validate_json(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return sorted(plans, key=lambda plan: plan.created_at, reverse=True)


def generate_prompt(
    index: int,
    start: float,
    end: float,
    style: str,
    user_prompt: str | None = None,
    subject_prompt: str | None = None,
    script_prompt: str | None = None,
    language: Language = "auto",
    enhance: bool = False,
    prompt_api_key: str | None = None,
    prompt_model: str | None = None,
) -> str:
    """Deterministic prompt; no LLM key is required for the MVP."""
    base = (
        f"Recreate block {index:03d} as an original short-form video scene. "
        f"Preserve the source pacing, camera motion, composition, and action from "
        f"{start:.2f}s to {end:.2f}s. Keep continuity with adjacent blocks. "
        "Do not add text overlays unless text is visible in the source."
    )
    if language != "auto":
        base = f"{base} Target language for any narration or visible text is {language}."
    if subject_prompt and subject_prompt.strip():
        base = f"{base} Video subject: {subject_prompt.strip()}"
    if script_prompt and script_prompt.strip():
        base = f"{base} Script/narration direction: {script_prompt.strip()}"
    if user_prompt and user_prompt.strip():
        base = f"{base} User direction: {user_prompt.strip()}"
    prompt = styles.apply(base, style)
    if not enhance:
        return prompt
    try:
        return prompt_writer.refine_prompt(
            prompt,
            api_key=prompt_api_key,
            model=prompt_model,
        )
    except prompt_writer.PromptWriterError as exc:
        raise UserFacingError(str(exc)) from exc


def _prepare_audio(request: RemixRequest, audio_dir: Path, source_audio_path: str | None) -> str | None:
    if request.audio_mode == "none":
        return None
    if request.audio_mode == "source":
        return source_audio_path
    if request.audio_mode == "tts":
        if not request.video_script_prompt or not request.video_script_prompt.strip():
            raise UserFacingError("TTS audio requires a video script prompt.")
        from app.services import tts

        tts_path = str(audio_dir / "tts.mp3")
        return tts.synthesize(request.video_script_prompt, request.tts_voice, tts_path)
    if request.audio_mode == "upload":
        upload = (request.audio_upload or "").strip()
        if not upload or not Path(upload).is_file():
            raise UserFacingError("Upload-audio mode requires an uploaded audio file.")
        return upload
    raise ValueError(f"unknown audio mode: {request.audio_mode}")


def _new_run_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def _require_media_tools() -> None:
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise RuntimeError(
            f"Missing required media tool(s): {', '.join(missing)}. Install ffmpeg first."
        )


def _validate_live_preflight(plan: RunPlan) -> None:
    profile = _quality_profile(plan.quality)
    if profile.provider == "local":
        if not _local_command_from_plan(plan):
            raise RuntimeError(
                f"{profile.model_label} requires a local command. Add one in the local command field "
                "using {input}, {keyframe}, {prompt}, and {output} placeholders."
            )
        return

    cfg = get_settings().video_gen
    endpoint = _remote_endpoint()
    if endpoint == "seedance2":
        if not _temporary_seedance2_cookie():
            raise UserFacingError(
                "Missing temporary Seedance2 cookie. Set SEEDANCE2_COOKIE or SEEDANCE_API_TOKEN "
                "in .env before clicking Run Live."
            )
        return
    if endpoint == "fal":
        if not (cfg.api_key or os.environ.get("FAL_KEY")):
            raise UserFacingError("Missing fal key. Set FAL_KEY in .env before clicking Run Live.")
        if not importlib.util.find_spec("fal_client"):
            raise UserFacingError("Missing fal-client package. Install with: pip install -e '.[seedance]'")
        return
    if endpoint != "replicate":
        raise UserFacingError(
            "Unknown video_gen endpoint. Use replicate or fal. The direct Seedance2 path "
            "is a temporary local test override when SEEDANCE2_COOKIE is set."
        )
    if not (cfg.api_key or os.environ.get("REPLICATE_API_TOKEN")):
        raise UserFacingError(
            "Missing Replicate token. Set REPLICATE_API_TOKEN in .env before clicking Run Live."
        )
    if not importlib.util.find_spec("replicate"):
        raise UserFacingError("Missing Replicate package. Install with: pip install -e '.[seedance]'")


def _remote_endpoint() -> str:
    endpoint = (get_settings().video_gen.endpoint or "replicate").lower()
    # Temporary local test path for seedance2.ai. Keep the public config/catalog on
    # Replicate until the direct API is stable enough to support.
    if endpoint == "replicate" and _temporary_seedance2_cookie():
        return "seedance2"
    return endpoint


def _temporary_seedance2_cookie() -> str:
    legacy = (os.environ.get("SEEDANCE2_COOKIE") or os.environ.get("SEEDANCE_API_TOKEN") or "").strip()
    if legacy:
        return legacy
    # Auto-refresh path: route to seedance2 when an anon key + seed are configured.
    try:
        from app.services.providers import seedance2_auth

        if seedance2_auth.is_configured():
            return "auto"
    except Exception:
        pass
    return ""


def _materialize_source(source: str, dest: str) -> SourceMetadata:
    source = source.strip()
    if _is_url(source):
        try:
            _download_url(source, dest)
        except CommandError as exc:
            raise UserFacingError(_download_error_message(source, exc.output)) from exc
        return _metadata_from_info_json(dest) or SourceMetadata(platform=_platform_from_url(source))
    src = Path(source).expanduser()
    if not src.exists():
        raise FileNotFoundError(
            f"Source file not found: {source}. Enter a public video URL or a local file path "
            "that exists on this machine."
        )
    if not src.is_file():
        raise UserFacingError(f"Source path is not a file: {source}")
    shutil.copyfile(src, dest)
    return SourceMetadata(platform="local", title=src.name)


def _download_url(url: str, dest: str) -> None:
    last_error: CommandError | None = None
    for candidate in _download_candidates(url):
        try:
            _run(_yt_dlp_command(candidate, dest), "yt-dlp download failed")
            return
        except CommandError as exc:
            last_error = exc
    if last_error:
        raise last_error


def _yt_dlp_command(url: str, dest: str) -> list[str]:
    exe = shutil.which("yt-dlp") or shutil.which("yt_dlp")
    if exe:
        cmd = [exe]
    else:
        cmd = [
            "python",
            "-m",
            "yt_dlp",
        ]
    cmd.extend(
        [
            "--no-playlist",
            "-f",
            "bv*+ba/b",
            "--merge-output-format",
            "mp4",
            "--write-info-json",
            "-o",
            dest,
        ]
    )
    cookies_file = os.environ.get("YTDLP_COOKIES_FILE", "").strip()
    if cookies_file:
        cmd.extend(["--cookies", str(Path(cookies_file).expanduser())])
    cmd.append(url)
    return cmd


def _download_candidates(url: str) -> list[str]:
    candidates = [url]
    normalized = _normalize_youtube_video_url(url)
    if normalized and normalized not in candidates:
        candidates.append(normalized)
    return candidates


def _normalize_youtube_video_url(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    video_id: str | None = None
    if "youtube.com" in host:
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "shorts":
            video_id = parts[1]
        elif parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
    elif host == "youtu.be" and parsed.path.strip("/"):
        video_id = parsed.path.strip("/").split("/")[0]
    if not video_id:
        return None
    query = urlencode({"v": video_id})
    return urlunparse(("https", "www.youtube.com", "/watch", "", query, ""))


def _download_error_message(url: str, output: str) -> str:
    lower = output.lower()
    platform = _platform_from_url(url)
    if "unsupported url" in lower:
        return (
            f"Could not download this {platform} URL because yt-dlp does not support it. "
            "Try a public YouTube, TikTok, or Instagram video URL, or use a local MP4 path."
        )
    if platform == "youtube" and any(
        token in lower
        for token in (
            "this video is not available",
            "video unavailable",
            "not available",
            "playability status: unplayable",
            "remote components challenge",
            "po token",
        )
    ):
        return (
            "Could not download this YouTube video with yt-dlp. YouTube can block "
            "automated extraction even when the video page still embeds. Try another "
            "public Short, update yt-dlp, set YTDLP_COOKIES_FILE to a Netscape cookies.txt "
            "export, or download the video locally and use the file path."
        )
    if any(token in lower for token in ("private video", "sign in", "login", "cookies")):
        return (
            f"Could not download this {platform} video because it looks private, age-gated, "
            "or login-protected. Use a public video or download it locally first."
        )
    if any(token in lower for token in ("video unavailable", "not available", "removed")):
        return f"Could not download this {platform} video because it is unavailable or removed."
    if any(token in lower for token in ("403", "forbidden", "429", "too many requests")):
        return (
            f"Could not download this {platform} video because the platform blocked the request. "
            "Try a different public URL or download the video locally and use the file path."
        )
    if any(token in lower for token in ("requested format is not available", "no video formats")):
        return (
            f"Could not download a usable MP4 stream from this {platform} URL. Try another URL "
            "or use a local MP4/MOV file."
        )
    return (
        f"Could not download the source video from {platform}. Make sure the URL is public and "
        "supported by yt-dlp, or use a local MP4 path."
    )


def _metadata_from_info_json(dest: str) -> SourceMetadata | None:
    path = Path(dest)
    candidates = [path.with_suffix(".info.json"), path.with_name(f"{path.stem}.info.json")]
    candidates.extend(path.parent.glob("*.info.json"))
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
        return SourceMetadata(
            platform=str(data.get("extractor_key") or data.get("extractor") or "url"),
            title=data.get("title"),
            original_duration=float(data["duration"]) if data.get("duration") else None,
        )
    return None


def _is_url(source: str) -> bool:
    parsed = urlparse(source)
    return parsed.scheme in {"http", "https"}


def _platform_from_url(source: str) -> str:
    host = (urlparse(source).hostname or "url").lower()
    if "youtube" in host or "youtu.be" in host:
        return "youtube"
    if "tiktok" in host:
        return "tiktok"
    if "instagram" in host:
        return "instagram"
    return host


def _aspect_label(width: int, height: int) -> str:
    if width == height:
        return "1:1"
    return "9:16" if height > width else "16:9"


DEFAULT_IMAGE_SECONDS = 5.0
# Target frame for an explicit aspect override (kept under the provider pixel ceiling).
_ASPECT_DIMS = {"9:16": (720, 1280), "16:9": (1280, 720), "1:1": (960, 960)}


def _aspect_enum(aspect: str | None) -> AspectRatio:
    return {
        "9:16": AspectRatio.VERTICAL,
        "16:9": AspectRatio.HORIZONTAL,
        "1:1": AspectRatio.SQUARE,
    }.get(aspect or "", AspectRatio.VERTICAL)


def _has_audio(path: str) -> bool:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            path,
        ],
        capture_output=True,
        text=True,
    )
    # Only trust a clean probe; a non-zero exit means we couldn't tell, not "no audio".
    return proc.returncode == 0 and "audio" in proc.stdout


def _probe_dims(path: str) -> tuple[int, int]:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", path],
        capture_output=True,
        text=True,
    )
    try:
        width, height = proc.stdout.strip().split("x")
        return int(width), int(height)
    except (ValueError, AttributeError):
        return 720, 1280


def _probe_fps(path: str) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", path],
        capture_output=True,
        text=True,
    )
    raw = proc.stdout.strip()
    if proc.returncode != 0 or not raw:
        return 30.0
    try:
        if "/" in raw:
            num, den = raw.split("/", 1)
            value = float(num) / float(den) if float(den) else 0.0
        else:
            value = float(raw)
    except ValueError:
        return 30.0
    return value if 1.0 <= value <= 120.0 else 30.0


def _normalize_for_concat(src: str, dest: str, width: int, height: int, fps: float) -> None:
    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"setsar=1,fps={fps:.5f},format=yuv420p"
    )
    _run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", src,
            "-vf", video_filter,
            "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-video_track_timescale", "90000",
            dest,
        ],
        "block normalization failed",
    )


def _extract_audio(source: str, dest: str, duration: float) -> None:
    _run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            source,
            "-t",
            f"{duration:.3f}",
            "-vn",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            dest,
        ],
        "audio extraction failed",
    )


def _plan_blocks(source: str, duration: float) -> list[tuple[float, float]]:
    cuts = vc.detect_cuts(source)
    return vc.plan_segments(cuts, duration, min_seconds=vc.MIN_SECONDS, max_seconds=MAX_BLOCK_SECONDS)


def _encode_reference_block(
    source: str, dest: str, start: float, length: float, dims: tuple[int, int] | None = None
) -> None:
    if dims is not None:
        width, height = dims
        # Fit-and-pad into the chosen aspect so the reference matches the requested frame.
        scale_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
        )
    else:
        iw, ih, _ = vc.probe(source)
        width, height = vc.target_dims(iw, ih)
        scale_filter = f"scale={width}:{height}"
    _run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-ss",
            f"{start:.3f}",
            "-i",
            source,
            "-t",
            f"{length:.3f}",
            "-an",
            "-vf",
            scale_filter,
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            dest,
        ],
        "reference block encode failed",
    )


def _extract_keyframe(source: str, dest: str, timestamp: float) -> None:
    _run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            source,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            dest,
        ],
        "keyframe extraction failed",
    )


def _local_command_from_request(request: RemixRequest) -> str | None:
    command = request.local_command
    return command.strip() if command and command.strip() else None


def _local_command_from_plan(plan: RunPlan) -> str | None:
    command = plan.local_command
    return command.strip() if command and command.strip() else None


def _run_local_model(plan: RunPlan, block: BlockPlan) -> str:
    command = _local_command_from_plan(plan)
    if not command:
        raise RuntimeError("local generation requires local_command")
    profile = _quality_profile(plan.quality)
    formatted = command.format(
        input=block.ref_video,
        keyframe=block.keyframe,
        prompt=block.prompt_path,
        output=block.generated_path,
        index=block.index,
    )
    _run(shlex.split(formatted), f"{profile.model_label} command failed")
    return block.generated_path


def _stitch_final(plan: RunPlan) -> str:
    generated = [Path(block.generated_path) for block in plan.blocks]
    missing = [str(path) for path in generated if not path.exists()]
    if missing:
        raise RuntimeError(f"missing generated block(s): {', '.join(missing)}")

    run_dir = Path(plan.run_dir)
    gen_dir = run_dir / "generated"
    concat_list = gen_dir / "concat.txt"
    concat_video = gen_dir / "concat_video.mp4"
    muxed = gen_dir / "muxed.mp4"
    final = run_dir / "final.mp4"

    # Generated blocks can come back from different models at different resolutions, frame
    # rates, or pixel aspect ratios. The concat demuxer assumes uniform parameters and will
    # corrupt or abort otherwise, so normalize every block to one target spec first.
    target_w, target_h = plan.width, plan.height
    if target_w <= 0 or target_h <= 0:
        target_w, target_h = _probe_dims(str(generated[0]))
    fps = _probe_fps(str(generated[0]))
    normalized: list[Path] = []
    for index, src in enumerate(generated):
        dest = gen_dir / f"norm_{index:03d}.mp4"
        _normalize_for_concat(str(src), str(dest), target_w, target_h, fps)
        normalized.append(dest)

    concat_list.write_text(
        "".join(f"file '{path.resolve().as_posix()}'\n" for path in normalized),
        encoding="utf-8",
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(concat_video),
        ],
        "final concat failed",
    )
    if plan.audio_path and Path(plan.audio_path).exists():
        _run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(concat_video),
                "-i",
                plan.audio_path,
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-shortest",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                str(muxed),
            ],
            "audio mux failed",
        )
    else:
        shutil.copyfile(concat_video, muxed)

    if plan.captions:
        if not plan.audio_path or not Path(plan.audio_path).exists():
            shutil.copyfile(muxed, final)
            return str(final)
        captions_path = _make_captions(plan)
        plan.captions_path = captions_path
        if _has_subtitles_filter():
            _burn_captions(str(muxed), captions_path, str(final))
        else:
            shutil.copyfile(muxed, final)
        return str(final)

    shutil.copyfile(muxed, final)
    return str(final)


def _make_captions(plan: RunPlan) -> str:
    from app.services import captions as captions_service

    return captions_service.align(
        plan.audio_path or "",
        Path(plan.run_dir),
        "word-level karaoke, bold, centered",
        AspectRatio.VERTICAL,
        position=plan.caption_position,
    )


def _has_subtitles_filter() -> bool:
    from app.services import render

    return render._has_subtitles_filter()


def _burn_captions(src: str, captions_path: str, dest: str) -> None:
    from app.services import render

    _run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            src,
            "-vf",
            f"subtitles={render._escape_path(captions_path)}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            dest,
        ],
        "caption burn-in failed",
    )


def _run(cmd: list[str], label: str) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise CommandError(label, proc.stdout, proc.stderr)


def _tail(text: str, lines: int = 12) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])
