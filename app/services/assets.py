"""Step 4 — ASSETS. Stock footage sized to the script, with cross-source fallback.

Free by default (Pexels → Pixabay). A job NEVER returns zero clips if any source has a
hit. (AI hero shots via Seedance are a Phase-5 / cloud feature.)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from itertools import cycle
from pathlib import Path

import httpx

from app.config import get_settings
from app.models import AspectRatio, VideoBlueprint

log = logging.getLogger("omp")

MAX_CLIPS = 12


@dataclass
class Clip:
    path: str
    source: str       # "pexels" | "pixabay"
    seconds: float


def gather(blueprint: VideoBlueprint, script: str, work_dir: Path, aspect: AspectRatio) -> list[Clip]:
    cfg = get_settings().stock
    if not cfg.pexels_api_key and not cfg.pixabay_api_key:
        raise RuntimeError(
            "No stock-footage key. Set [stock] pexels_api_key (free at pexels.com/api) "
            "or pixabay_api_key in config.toml."
        )

    slice_s = max(1.5, blueprint.pacing_seconds)
    n = min(MAX_CLIPS, max(1, math.ceil(blueprint.total_seconds / slice_s)))
    terms = blueprint.search_terms or [blueprint.topic or "abstract background"]

    clips: list[Clip] = []
    seen_urls: set[str] = set()
    for i, term in zip(range(n), cycle(terms)):
        hit = _search(term, aspect, cfg, seen_urls)
        if hit is None:
            continue
        url, source = hit
        seen_urls.add(url)
        dest = work_dir / f"clip_{i:02d}.mp4"
        if _download(url, dest):
            clips.append(Clip(path=str(dest), source=source, seconds=slice_s))

    if not clips:
        raise RuntimeError("No stock footage found for any search term. Try a broader topic.")
    log.info("sourced %d clips (%d requested)", len(clips), n)
    return clips


def _search(term: str, aspect: AspectRatio, cfg, seen: set[str]) -> tuple[str, str] | None:
    if cfg.pexels_api_key:
        if url := _pexels(term, aspect, cfg.pexels_api_key, seen):
            return url, "pexels"
    if cfg.pixabay_api_key:
        if url := _pixabay(term, cfg.pixabay_api_key, seen):
            return url, "pixabay"
    return None


def _pexels(term: str, aspect: AspectRatio, key: str, seen: set[str]) -> str | None:
    try:
        r = httpx.get(
            "https://api.pexels.com/videos/search",
            params={"query": term, "orientation": aspect.pexels_orientation, "per_page": 10},
            headers={"Authorization": key},
            timeout=30,
        )
        r.raise_for_status()
        for video in r.json().get("videos", []):
            files = sorted(video.get("video_files", []), key=lambda f: f.get("height") or 0, reverse=True)
            for f in files:
                link = f.get("link")
                if link and link not in seen:
                    return link
    except httpx.HTTPError as exc:
        log.warning("pexels search failed for %r: %s", term, exc)
    return None


def _pixabay(term: str, key: str, seen: set[str]) -> str | None:
    try:
        r = httpx.get(
            "https://pixabay.com/api/videos/",
            params={"key": key, "q": term, "per_page": 10},
            timeout=30,
        )
        r.raise_for_status()
        for hit in r.json().get("hits", []):
            videos = hit.get("videos", {})
            for quality in ("large", "medium", "small"):
                link = videos.get(quality, {}).get("url")
                if link and link not in seen:
                    return link
    except httpx.HTTPError as exc:
        log.warning("pixabay search failed for %r: %s", term, exc)
    return None


def _download(url: str, dest: Path) -> bool:
    try:
        with httpx.stream("GET", url, timeout=60, follow_redirects=True) as r:
            r.raise_for_status()
            with dest.open("wb") as fh:
                for chunk in r.iter_bytes(1 << 16):
                    fh.write(chunk)
        return dest.stat().st_size > 0
    except (httpx.HTTPError, OSError) as exc:
        log.warning("download failed %s: %s", url, exc)
        return False
