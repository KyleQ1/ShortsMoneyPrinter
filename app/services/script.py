"""Step 3 — SCRIPT. Generate an ORIGINAL narration in the blueprint's proven shape.

Spin, don't copy: new words, same winning structure/pacing/length.
"""

from __future__ import annotations

from app.models import VideoBlueprint
from app.services.providers import llm

WORDS_PER_SECOND = 2.5  # ~150 wpm narration

_SYSTEM = (
    "You are a short-form scriptwriter. Write punchy, original spoken narration for a "
    "vertical short. Output ONLY the words to be spoken — no scene directions, no labels."
)


def generate(blueprint: VideoBlueprint) -> str:
    target_words = max(20, int(blueprint.total_seconds * WORDS_PER_SECOND))
    prompt = (
        f"Topic: {blueprint.topic}\n"
        f"Hook style: {blueprint.hook}\n"
        f"Structure: {' → '.join(blueprint.structure)}\n"
        f"Target length: about {blueprint.total_seconds:.0f}s (~{target_words} words).\n\n"
        "Write a fresh, original script that follows this structure and nails the hook in "
        "the first line. Do not copy any existing video's wording. Spoken words only."
    )
    return llm.complete(prompt, system=_SYSTEM).strip()
