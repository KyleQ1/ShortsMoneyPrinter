"""Step 7 — RENDER. Compose the final MP4 with ffmpeg filter graphs (NOT moviepy).

Each clip is scaled+cropped to the target frame, trimmed to its slice, concatenated to
cover the narration length, captions are burned in, narration is muxed, and the whole
thing is encoded h264/aac. Short clips are looped (-stream_loop) so a slice never runs dry.
"""

from __future__ import annotations

import logging
import subprocess
from functools import lru_cache

from app.models import AspectRatio
from app.services.assets import Clip

log = logging.getLogger("omp")


def compose(clips: list[Clip], audio_path: str, captions_path: str | None, out_path: str,
            aspect: AspectRatio = AspectRatio.VERTICAL) -> str:
    if not clips:
        raise ValueError("no clips to render")
    w, h = aspect.dimensions
    audio_dur = _probe_duration(audio_path)
    n = len(clips)
    slice_s = audio_dur / n

    cmd = ["ffmpeg", "-y"]
    for clip in clips:
        cmd += ["-stream_loop", "-1", "-i", clip.path]  # loop short clips
    cmd += ["-i", audio_path]
    audio_idx = n

    parts = []
    for i in range(n):
        parts.append(
            f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},setsar=1,fps=30,"
            f"trim=duration={slice_s:.3f},setpts=PTS-STARTPTS[v{i}]"
        )
    concat_inputs = "".join(f"[v{i}]" for i in range(n))
    parts.append(f"{concat_inputs}concat=n={n}:v=1:a=0[vcat]")

    burn_captions = bool(captions_path) and _has_subtitles_filter()
    if captions_path and not burn_captions:
        log.warning("ffmpeg lacks the 'subtitles' filter (libass) — rendering without burned-in captions")
    if burn_captions:
        parts.append(f"[vcat]subtitles={_escape_path(captions_path)}[v]")
        vmap = "[v]"
    else:
        vmap = "[vcat]"

    cmd += [
        "-filter_complex", ";".join(parts),
        "-map", vmap,
        "-map", f"{audio_idx}:a",
        "-t", f"{audio_dur:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        out_path,
    ]

    log.debug("ffmpeg: %s", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        raise RuntimeError(f"ffmpeg render failed:\n{tail}")
    return out_path


@lru_cache(maxsize=1)
def _has_subtitles_filter() -> bool:
    """True if this ffmpeg was built with libass (the subtitles filter). Bundled builds must be."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
    return any(line.split()[1:2] == ["subtitles"] for line in out.stdout.splitlines() if line.strip())


def _probe_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"could not probe duration of {path}: {out.stderr}") from exc


def _escape_path(path: str) -> str:
    """Escape a path for the ffmpeg subtitles filter value (filtergraph-level, no shell).

    The graph is passed via argv, so we escape the chars special to filtergraph parsing
    (\\, :, ') rather than wrapping in shell quotes (which ffmpeg would take literally).
    """
    return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
