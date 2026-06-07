"""Step 1 — INGEST. Pull the source's metadata + transcript for ANALYSIS ONLY.

Legal posture: transient. We use yt-dlp to read metadata and (auto-)captions without
downloading the video, extract the signal, and keep nothing. The user chose this URL.
"""

from __future__ import annotations

import html
import json
import logging
import re
from dataclasses import dataclass, field

import httpx

log = logging.getLogger("omp")


@dataclass
class SourceVideo:
    url: str
    title: str = ""
    duration_s: float = 0.0
    transcript: str = ""
    uploader: str = ""
    metrics: dict = field(default_factory=dict)


def fetch_source(url: str | None) -> SourceVideo:
    if not url:
        raise ValueError("recreate mode requires a source_url")

    import yt_dlp  # lazy import

    opts = {"skip_download": True, "quiet": True, "noplaylist": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    transcript = _extract_transcript(info)
    if not transcript:
        log.warning("no captions found; analysis will rely on title/metadata only")

    return SourceVideo(
        url=url,
        title=info.get("title") or "",
        duration_s=float(info.get("duration") or 0),
        transcript=transcript,
        uploader=info.get("uploader") or "",
        metrics={
            "view_count": info.get("view_count"),
            "like_count": info.get("like_count"),
        },
    )


def _extract_transcript(info: dict) -> str:
    """Find an English caption track, fetch it, and reduce it to plain text.

    YouTube serves several caption formats; each needs its own parser. We prefer vtt
    (simplest), then json3 (common for auto-captions), then srv1 — and parse by the
    format we actually picked, never assuming vtt.
    """
    tracks = {**(info.get("subtitles") or {}), **(info.get("automatic_captions") or {})}
    lang = next((k for k in tracks if k.startswith("en")), None)
    if not lang:
        return ""
    fmts = tracks[lang]
    entry = None
    for ext in ("vtt", "json3", "srv1"):
        entry = next((f for f in fmts if f.get("ext") == ext), None)
        if entry:
            break
    entry = entry or (fmts[0] if fmts else None)
    if not entry or not entry.get("url"):
        return ""
    try:
        text = httpx.get(entry["url"], timeout=20, follow_redirects=True).text
    except httpx.HTTPError as exc:
        log.warning("caption fetch failed: %s", exc)
        return ""
    parser = {"json3": _json3_to_text, "srv1": _srv1_to_text}.get(entry.get("ext"), _vtt_to_text)
    return parser(text)


def _json3_to_text(raw: str) -> str:
    """Parse YouTube's json3 caption format (events[].segs[].utf8)."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    out: list[str] = []
    for ev in data.get("events", []):
        line = "".join(seg.get("utf8", "") for seg in (ev.get("segs") or [])).strip()
        line = re.sub(r"\s+", " ", line)
        if line and (not out or out[-1] != line):
            out.append(line)
    return " ".join(out).strip()


def _srv1_to_text(raw: str) -> str:
    """Parse the srv1 caption format (<text> XML nodes)."""
    out: list[str] = []
    for chunk in re.findall(r"<text[^>]*>(.*?)</text>", raw, flags=re.S):
        line = html.unescape(re.sub(r"<[^>]+>", "", chunk)).strip()
        line = re.sub(r"\s+", " ", line)
        if line and (not out or out[-1] != line):
            out.append(line)
    return " ".join(out).strip()


def _vtt_to_text(raw: str) -> str:
    """Strip WEBVTT/timestamps/cue-tags and collapse repeated auto-caption lines."""
    out: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line == "WEBVTT" or "-->" in line or line.isdigit():
            continue
        if line.startswith(("Kind:", "Language:", "NOTE")):
            continue
        line = re.sub(r"<[^>]+>", "", line)            # inline <c>/<00:00:00.000> tags
        line = re.sub(r"\s+", " ", line).strip()
        if line and (not out or out[-1] != line):       # dedupe consecutive duplicates
            out.append(line)
    return " ".join(out)
