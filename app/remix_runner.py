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
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.config import get_settings
from app.models import AspectRatio
from app.services import styles, video_conditioning as vc

Quality = Literal["budget", "standard", "premium", "local"]
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


@dataclass(frozen=True)
class QualityProfile:
    key: Quality
    provider: str
    model_id: str
    model_label: str
    mode: str
    resolution: str
    estimated_cost_per_second: float


QUALITY_PROFILES: dict[Quality, QualityProfile] = {
    "budget": QualityProfile(
        key="budget",
        provider="replicate",
        model_id="bytedance/seedance-1.5-pro",
        model_label="Replicate Seedance 1.5 Pro",
        mode="image-to-video",
        resolution="480p",
        estimated_cost_per_second=0.013,
    ),
    "standard": QualityProfile(
        key="standard",
        provider="replicate",
        model_id="bytedance/seedance-2.0-fast",
        model_label="Replicate Seedance 2.0 Fast",
        mode="video-to-video",
        resolution="480p",
        estimated_cost_per_second=0.08,
    ),
    "premium": QualityProfile(
        key="premium",
        provider="replicate",
        model_id="bytedance/seedance-2.0",
        model_label="Replicate Seedance 2.0",
        mode="video-to-video",
        resolution="720p",
        estimated_cost_per_second=0.22,
    ),
    "local": QualityProfile(
        key="local",
        provider="local",
        model_id="wan-2.2-ti2v-5b",
        model_label="Wan 2.2 TI2V-5B",
        mode="local-ti2v",
        resolution="local",
        estimated_cost_per_second=0.0,
    ),
}


class RemixRequest(BaseModel):
    source: str
    style: str = styles.DEFAULT_STYLE
    prompt: str | None = None
    quality: Quality = "standard"
    max_cost: float | None = None
    captions: bool = False
    max_total_seconds: float | None = None
    wan_command: str | None = None


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
    captions: bool = False
    captions_path: str | None = None
    max_cost: float | None = None
    wan_command: str | None = None
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
        profile = QUALITY_PROFILES[plan.quality]
        out_path = block.generated_path
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        if plan.quality == "local":
            return _run_local_wan(plan, block)

        from app.services.providers import seedance

        style = styles.get(plan.style)
        duration = str(max(4, min(15, math.ceil(block.duration))))
        if plan.quality == "budget":
            return seedance.generate_from_image(
                block.keyframe,
                block.prompt,
                out_path,
                AspectRatio.VERTICAL,
                resolution=profile.resolution,
                duration=duration,
            )

        return seedance.generate_from_video(
            block.ref_video,
            block.prompt,
            out_path,
            AspectRatio.VERTICAL,
            resolution=profile.resolution,
            duration=duration,
            generate_audio=False,
            match_reference=style.match_reference,
            fast=plan.quality == "standard",
        )


def preflight_status() -> dict[str, object]:
    """Return local capability hints for UI and diagnostics."""
    cfg = get_settings().video_gen
    endpoint = (cfg.endpoint or "replicate").lower()
    return {
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "ffprobe": bool(shutil.which("ffprobe")),
        "yt_dlp": bool(
            shutil.which("yt-dlp")
            or shutil.which("yt_dlp")
            or importlib.util.find_spec("yt_dlp")
        ),
        "endpoint": endpoint,
        "replicate_token": bool(cfg.api_key or os.environ.get("REPLICATE_API_TOKEN")),
        "replicate_package": bool(importlib.util.find_spec("replicate")),
        "fal_token": bool(cfg.api_key or os.environ.get("FAL_KEY")),
        "fal_package": bool(importlib.util.find_spec("fal_client")),
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


def create_plan(request: RemixRequest, runs_dir: Path = RUNS_DIR) -> RunPlan:
    """Create a dry-run plan and stop before provider calls."""
    _require_media_tools()
    if not request.source.strip():
        raise ValueError("Enter a YouTube, Instagram, TikTok URL or local video path.")
    if request.max_total_seconds is not None and request.max_total_seconds <= 0:
        raise ValueError("max_total_seconds must be greater than 0.")
    styles.get(request.style)
    profile = QUALITY_PROFILES[request.quality]
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
    audio_path = str(audio_dir / "source.m4a") if has_audio else None
    if has_audio and audio_path:
        try:
            _extract_audio(source_path, audio_path, duration)
        except CommandError as exc:
            raise UserFacingError(
                "Could not extract source audio. Try another video, or rerun with a shorter "
                "max seconds value."
            ) from exc

    segment_plan = _plan_blocks(source_path, duration)
    block_models: list[BlockPlan] = []
    for index, (start, length) in enumerate(segment_plan):
        end = start + length
        ref_video = str(blocks_dir / f"block_{index:03d}_ref.mp4")
        keyframe = str(blocks_dir / f"block_{index:03d}_keyframe.jpg")
        prompt_path = str(prompts_dir / f"block_{index:03d}.txt")
        generated_path = str(generated_dir / f"block_{index:03d}.mp4")
        try:
            _encode_reference_block(source_path, ref_video, start, length)
            _extract_keyframe(source_path, keyframe, start + (length / 2.0))
        except CommandError as exc:
            raise UserFacingError(
                "Could not prepare a remix block from the source video. Try a shorter max "
                "seconds value or a different MP4/MOV source."
            ) from exc
        prompt = generate_prompt(index, start, end, request.style, request.prompt)
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
                estimated_cost=round(length * profile.estimated_cost_per_second, 2),
            )
        )

    estimated_cost = round(duration * profile.estimated_cost_per_second, 2)
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
        quality=request.quality,
        provider=profile.provider,
        model_id=profile.model_id,
        model_label=profile.model_label,
        mode=profile.mode,
        resolution=profile.resolution,
        width=width,
        height=height,
        original_duration=round(original_duration, 3),
        duration=round(duration, 3),
        aspect_ratio=metadata.aspect_ratio or _aspect_label(width, height),
        has_audio=has_audio,
        captions=request.captions,
        max_cost=request.max_cost,
        wan_command=request.wan_command,
        estimated_cost=estimated_cost,
        block_count=len(block_models),
        blocks=block_models,
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
) -> str:
    """Deterministic prompt; no LLM key is required for the MVP."""
    base = (
        f"Recreate block {index:03d} as an original short-form video scene. "
        f"Preserve the source pacing, camera motion, composition, and action from "
        f"{start:.2f}s to {end:.2f}s. Keep continuity with adjacent blocks. "
        "Do not add text overlays unless text is visible in the source."
    )
    if user_prompt and user_prompt.strip():
        base = f"{base} User direction: {user_prompt.strip()}"
    return styles.apply(base, style)


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
    if plan.quality == "local":
        if not plan.wan_command:
            raise RuntimeError(
                "Local quality requires a Wan command. Add one in the Wan command field "
                "using {input}, {keyframe}, {prompt}, and {output} placeholders."
            )
        return

    cfg = get_settings().video_gen
    endpoint = (cfg.endpoint or "replicate").lower()
    if endpoint != "replicate":
        raise UserFacingError("Live remix generation is currently supported through Replicate only.")
    if not (cfg.api_key or os.environ.get("REPLICATE_API_TOKEN")):
        raise UserFacingError(
            "Missing Replicate token. Set REPLICATE_API_TOKEN in .env before clicking Run Live."
        )
    if not importlib.util.find_spec("replicate"):
        raise UserFacingError("Missing Replicate package. Install with: pip install -e '.[seedance]'")


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
    exe = shutil.which("yt-dlp") or shutil.which("yt_dlp")
    if exe:
        cmd = [
            exe,
            "-f",
            "bv*+ba/b",
            "--merge-output-format",
            "mp4",
            "--write-info-json",
            "-o",
            dest,
            url,
        ]
    else:
        cmd = [
            "python",
            "-m",
            "yt_dlp",
            "-f",
            "bv*+ba/b",
            "--merge-output-format",
            "mp4",
            "--write-info-json",
            "-o",
            dest,
            url,
        ]
    _run(cmd, "yt-dlp download failed")


def _download_error_message(url: str, output: str) -> str:
    lower = output.lower()
    platform = _platform_from_url(url)
    if "unsupported url" in lower:
        return (
            f"Could not download this {platform} URL because yt-dlp does not support it. "
            "Try a public YouTube, TikTok, or Instagram video URL, or use a local MP4 path."
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
    return "audio" in proc.stdout


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


def _encode_reference_block(source: str, dest: str, start: float, length: float) -> None:
    iw, ih, _ = vc.probe(source)
    width, height = vc.target_dims(iw, ih)
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
            f"scale={width}:{height}",
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


def _run_local_wan(plan: RunPlan, block: BlockPlan) -> str:
    if not plan.wan_command:
        raise RuntimeError("local quality requires wan_command")
    formatted = plan.wan_command.format(
        input=block.ref_video,
        keyframe=block.keyframe,
        prompt=block.prompt_path,
        output=block.generated_path,
        index=block.index,
    )
    _run(shlex.split(formatted), "local Wan command failed")
    return block.generated_path


def _stitch_final(plan: RunPlan) -> str:
    generated = [Path(block.generated_path) for block in plan.blocks]
    missing = [str(path) for path in generated if not path.exists()]
    if missing:
        raise RuntimeError(f"missing generated block(s): {', '.join(missing)}")

    run_dir = Path(plan.run_dir)
    concat_list = run_dir / "generated" / "concat.txt"
    concat_video = run_dir / "generated" / "concat_video.mp4"
    muxed = run_dir / "generated" / "muxed.mp4"
    final = run_dir / "final.mp4"
    concat_list.write_text(
        "".join(f"file '{path.resolve().as_posix()}'\n" for path in generated),
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
