"""Conform ANY input video to Seedance's reference-video limits.

Seedance 2.0 reference-to-video requires each reference video to be:
  - 2–15s (we target ≤12s to stay safely under the combined-15s cap)
  - ~480p–720p  (pixel count roughly 409,600–927,408)
  - mp4/mov, < 50 MB

Real winning Shorts are often 30–60s, 1080p, and >50 MB — so we MUST condition them
first. For sources longer than the cap, callers segment first and condition each segment.
"""

from __future__ import annotations

import logging
import math
import re
import subprocess
from pathlib import Path

log = logging.getLogger("omp")

MAX_SECONDS = 12.0
MIN_SECONDS = 4.0           # Seedance output floor; avoid sub-4s sliver blocks
MAX_PIXELS = 921_600        # 1280×720, just under Seedance's ~927,408 ceiling
MAX_BYTES = 50 * 1024 * 1024
SCENE_THRESHOLD = 0.4       # ffmpeg scene score [0–1]; lower = more cuts detected


def probe(path: str) -> tuple[int, int, float]:
    """Return (width, height, duration_seconds)."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True,
    ).stdout.split()
    try:
        return int(out[0]), int(out[1]), float(out[2])
    except (IndexError, ValueError) as exc:
        raise RuntimeError(f"could not probe {path}") from exc


def target_dims(iw: int, ih: int) -> tuple[int, int]:
    """Scale so the short side ~720, clamped to the pixel band; return even dimensions."""
    s = 720 / min(iw, ih)
    if iw * ih * s * s > MAX_PIXELS:
        s = math.sqrt(MAX_PIXELS / (iw * ih))
    w = max(2, int(round(iw * s)) & ~1)   # force even
    h = max(2, int(round(ih * s)) & ~1)
    return w, h


def condition(src: str, dst: str, max_seconds: float = MAX_SECONDS) -> str:
    """Trim + downscale + transcode `src` so it satisfies Seedance limits. Returns `dst`."""
    iw, ih, dur = probe(src)
    w, h = target_dims(iw, ih)
    t = min(dur, max_seconds)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)

    for crf in (23, 28, 32):  # bump compression if we blow the 50 MB cap
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error", "-i", src,
            "-t", f"{t:.3f}", "-an",                      # drop audio (reference = visual/motion)
            "-vf", f"scale={w}:{h}", "-r", "30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", dst,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            tail = "\n".join(proc.stderr.strip().splitlines()[-10:])
            raise RuntimeError(f"conditioning failed:\n{tail}")
        if Path(dst).stat().st_size <= MAX_BYTES:
            break
        log.warning("conditioned clip > 50MB at crf=%d; recompressing", crf)

    log.info("conditioned %s → %dx%d, %.1fs, %d bytes", src, w, h, t, Path(dst).stat().st_size)
    return dst


def _encode_segment(src: str, dst: str, start: float, length: float, w: int, h: int) -> None:
    """Cut [start, start+length) from src, downscale to w×h, transcode to Seedance limits."""
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-i", src,
        "-t", f"{length:.3f}", "-an",
        "-vf", f"scale={w}:{h}", "-r", "30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", dst,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-10:])
        raise RuntimeError(f"segment encode failed ({start:.1f}s +{length:.1f}s):\n{tail}")


def condition_segments(
    src: str,
    out_dir: str,
    segment_seconds: float = MAX_SECONDS,
    max_total_seconds: float | None = None,
) -> list[str]:
    """Split a long source into fixed ≤`segment_seconds` blocks, each conditioned.

    Naive fixed-interval split (cuts mid-shot). For cleaner joins, prefer
    `smart_segments`, which snaps boundaries to scene cuts.

    Seedance 2.0 caps output at ~15s, so anything longer must be generated in blocks
    and concatenated afterward. Returns the conditioned segment paths in order.

    NOTE: splitting does NOT reduce cost — billing is per output second (and on 2.0
    video→video the input reference is re-billed per block). It only works around the
    duration cap. Expect minor identity/lighting drift and audio seams at the joins.
    """
    if segment_seconds > 15.0:
        raise ValueError("segment_seconds must be ≤ 15 (Seedance output cap)")

    _, _, dur = probe(src)
    if max_total_seconds is not None:
        dur = min(dur, max_total_seconds)

    n = max(1, math.ceil(dur / segment_seconds))
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    iw, ih, _ = probe(src)
    w, h = target_dims(iw, ih)

    paths: list[str] = []
    for i in range(n):
        start = i * segment_seconds
        length = min(segment_seconds, dur - start)
        if length <= 0.05:
            break
        dst = str(Path(out_dir) / f"seg_{i:03d}.mp4")
        _encode_segment(src, dst, start, length, w, h)
        paths.append(dst)
        log.info("segment %d/%d → %s (%.1fs, %dx%d)", i + 1, n, dst, length, w, h)

    return paths


def detect_cuts(src: str, threshold: float = SCENE_THRESHOLD) -> list[float]:
    """Return sorted scene-cut timestamps (seconds) via ffmpeg scene detection.

    Uses the `select='gt(scene,threshold)'` filter + showinfo, parsing each selected
    frame's pts_time. Empty list means no hard cuts (single continuous shot).
    """
    proc = subprocess.run(
        ["ffmpeg", "-nostats", "-i", src,
         "-filter:v", f"select='gt(scene,{threshold})',showinfo",
         "-an", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    # showinfo writes to stderr: "...Parsed_showinfo... pts_time:12.345 ..."
    cuts = sorted(
        float(m.group(1))
        for line in proc.stderr.splitlines()
        if "showinfo" in line and (m := re.search(r"pts_time:([0-9.]+)", line))
    )
    log.info("detected %d scene cut(s) in %s (threshold=%.2f)", len(cuts), src, threshold)
    return cuts


def plan_segments(
    cuts: list[float],
    total: float,
    min_seconds: float = MIN_SECONDS,
    max_seconds: float = MAX_SECONDS,
) -> list[tuple[float, float]]:
    """Greedily plan (start, length) blocks that snap to scene cuts.

    Each block is made as LONG as possible (≤ max_seconds) to minimize the number of
    splits, but ends on the latest scene cut that lands in the [min_seconds, max_seconds]
    window from the block's start. If no cut falls in that window, it falls back to a
    hard split at max_seconds (an unavoidable mid-shot cut). A trailing sub-min sliver is
    pulled back into a clean min_seconds tail.
    """
    interior = sorted(c for c in cuts if 0.0 < c < total)
    boundaries = [0.0]
    pos = 0.0
    while total - pos > max_seconds + 1e-3:
        lo, hi = pos + min_seconds, pos + max_seconds
        candidate = max((c for c in interior if lo <= c <= hi), default=None)
        nxt = candidate if candidate is not None else hi
        # Avoid leaving a sub-min final sliver: don't cut so late that <min remains.
        if 0.0 < total - nxt < min_seconds:
            nxt = total - min_seconds
        if nxt <= pos + 1e-3:        # safety: never stall
            nxt = hi
        boundaries.append(round(nxt, 3))
        pos = nxt
    boundaries.append(round(total, 3))
    return [(boundaries[i], boundaries[i + 1] - boundaries[i]) for i in range(len(boundaries) - 1)]


def smart_segments(
    src: str,
    out_dir: str,
    min_seconds: float = MIN_SECONDS,
    max_seconds: float = MAX_SECONDS,
    max_total_seconds: float | None = None,
    threshold: float = SCENE_THRESHOLD,
) -> list[str]:
    """Scene-cut-aware split: detect cuts, plan fewest blocks snapped to cuts, condition each.

    Like `condition_segments` but boundaries land on real scene cuts where possible, so
    each generated block is a whole shot (or run of shots) — much cleaner Seedance joins.
    Returns the conditioned segment paths in order. Same cost caveat: billing is per
    output second; splitting only works around the 15s cap.
    """
    if max_seconds > 15.0:
        raise ValueError("max_seconds must be ≤ 15 (Seedance output cap)")

    iw, ih, dur = probe(src)
    if max_total_seconds is not None:
        dur = min(dur, max_total_seconds)
    w, h = target_dims(iw, ih)

    cuts = detect_cuts(src, threshold)
    plan = plan_segments(cuts, dur, min_seconds, max_seconds)
    snapped = sum(1 for (s, _) in plan[1:] if any(abs(s - c) < 0.05 for c in cuts))
    log.info("planned %d block(s); %d boundary(ies) snapped to cuts", len(plan), snapped)

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for i, (start, length) in enumerate(plan):
        if length <= 0.05:
            continue
        dst = str(Path(out_dir) / f"seg_{i:03d}.mp4")
        _encode_segment(src, dst, start, length, w, h)
        paths.append(dst)
        log.info("block %d/%d → %s (%.1f–%.1fs, %.1fs)", i + 1, len(plan), dst,
                 start, start + length, length)

    return paths
