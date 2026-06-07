"""Step 5 — TTS. Synthesize narration. Default edge-tts (free, no key)."""

from __future__ import annotations

import asyncio

from app.config import get_settings


def synthesize(script: str, voice: str | None, out_path: str) -> str:
    cfg = get_settings().tts
    if cfg.provider != "edge":
        raise NotImplementedError(
            f"TTS provider {cfg.provider!r} not implemented in OSS v1 (edge-tts only)."
        )

    chosen = voice or cfg.voice
    text = " ".join(script.split())  # collapse whitespace; edge-tts wants clean text
    if not text:
        raise ValueError("empty script — nothing to voice")

    import edge_tts  # lazy import

    async def _run() -> None:
        await edge_tts.Communicate(text, chosen).save(out_path)

    asyncio.run(_run())
    return out_path
