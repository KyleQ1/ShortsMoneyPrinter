"""Step 2 — ANALYZE. Turn the source into a VideoBlueprint: the 'winning formula'.

The core differentiator vs. keyword generators. An LLM reads the transcript + metadata
and articulates WHY it worked — hook, beat structure, pacing, caption style, topic — plus
a set of visual search terms. We recreate from this shape; we never copy the words.
"""

from __future__ import annotations

from app.models import VideoBlueprint
from app.services.ingest import SourceVideo
from app.services.providers import llm

_SYSTEM = (
    "You are a short-form video strategist. Given a video's transcript and metadata, "
    "explain the reusable formula behind it so a creator can make an ORIGINAL video in "
    "the same proven shape. Never reproduce the original script."
)


def build_blueprint(source: SourceVideo) -> VideoBlueprint:
    duration = source.duration_s or 30.0
    prompt = (
        f"Title: {source.title}\n"
        f"Duration: {duration:.0f}s\n"
        f"Transcript (may be empty): {source.transcript[:4000]}\n\n"
        "Return a JSON object with keys:\n"
        '  "hook": string (describe the first-2-seconds hook pattern),\n'
        '  "structure": array of strings (beat-by-beat outline),\n'
        '  "pacing_seconds": number (avg shot length),\n'
        '  "total_seconds": number,\n'
        '  "caption_style": string,\n'
        '  "topic": string,\n'
        '  "audio_style": string,\n'
        '  "search_terms": array of 5-8 short stock-footage search queries for the visuals.'
    )
    data = llm.complete_json(prompt, system=_SYSTEM)

    def _f(key: str, default: float) -> float:
        try:
            return float(data.get(key, default))
        except (TypeError, ValueError):
            return default

    return VideoBlueprint(
        hook=str(data.get("hook") or "pattern-interrupt opening"),
        structure=[str(s) for s in (data.get("structure") or [])] or ["hook", "body", "payoff"],
        pacing_seconds=_f("pacing_seconds", 2.5),
        total_seconds=_f("total_seconds", duration),
        caption_style=str(data.get("caption_style") or "word-level karaoke, bold, centered"),
        topic=str(data.get("topic") or source.title),
        audio_style=str(data.get("audio_style") or "upbeat"),
        search_terms=[str(t) for t in (data.get("search_terms") or [])] or [source.title or "abstract background"],
    )
