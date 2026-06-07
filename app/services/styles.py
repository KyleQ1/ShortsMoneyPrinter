"""Animation style presets for Seedance reference-to-video.

ShortsMoneyPrinter's edge is a *consistent, recognizable look* — that's what keeps
faceless channels monetized (YouTube demonetizes anonymous "AI slop"; a steady style
reads as a show). Each preset is a strong visual-style prompt fragment we prepend to
the user's prompt, plus whether to keep the reference's motion/framing.

Seedance is reference-to-video (style transfer), so a vivid style description + the
source's real motion = "this clip, but as <style>". match_reference stays True for
most presets to preserve pacing/framing while only the look changes.

Kids/family animation is the default lane (high volume, contextual ads). Presets here
target a bright, simple, toddler-friendly look à la CoComelon, plus a few general
animation styles for broader 13+ content.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Style:
    key: str
    label: str
    prompt: str            # style fragment, prepended to the user's prompt
    match_reference: bool  # keep source motion/pacing/framing?
    kids: bool             # is this a young-kids / family look?


# Ordered registry. First match wins; `none` is the passthrough.
STYLES: dict[str, Style] = {
    "none": Style(
        "none", "No style (passthrough)",
        "", True, False,
    ),
    "nursery-3d": Style(
        "nursery-3d", "Nursery 3D (CoComelon-style)",
        "Render as a bright, glossy 3D cartoon for toddlers in the style of "
        "CoComelon: big round friendly characters with large expressive eyes, "
        "soft rounded shapes, smooth simple surfaces, cheerful saturated primary "
        "colors, clean uncluttered backgrounds, soft even lighting, gentle "
        "wholesome mood.",
        True, True,
    ),
    "storybook": Style(
        "storybook", "Soft storybook (watercolor)",
        "Render as a soft hand-painted children's storybook illustration: warm "
        "watercolor textures, gentle pastel palette, rounded cozy shapes, soft "
        "edges, calm dreamy picture-book mood.",
        True, True,
    ),
    "claymation": Style(
        "claymation", "Claymation (stop-motion)",
        "Render as charming stop-motion claymation: soft modeling-clay textures "
        "with subtle fingerprints, rounded handmade shapes, warm tactile "
        "lighting, playful toy-like world.",
        True, True,
    ),
    "pixar": Style(
        "pixar", "Pixar-style 3D film",
        "Render as a polished cinematic 3D animated film in the style of a Pixar "
        "short: appealing stylized characters, rich detailed lighting, soft "
        "depth of field, warm expressive mood.",
        True, True,
    ),
    "anime": Style(
        "anime", "2D anime",
        "Render as vibrant 2D Japanese anime: clean bold linework, cel shading, "
        "expressive large eyes, dynamic saturated colors, crisp animation look.",
        True, False,
    ),
    "cartoon-2d": Style(
        "cartoon-2d", "Flat 2D cartoon",
        "Render as a flat modern 2D cartoon: bold clean outlines, simple flat "
        "color fills, snappy expressive shapes, bright punchy palette.",
        True, False,
    ),
    # --- live-action (keep it real) ---
    "realistic": Style(
        "realistic", "Realistic (clean live-action)",
        "Keep it photorealistic live-action: real people and real materials, "
        "natural skin and textures, true-to-life lighting and color, no "
        "cartoon or stylization — just a clean, polished real-world look.",
        True, False,
    ),
    "cinematic": Style(
        "cinematic", "Cinematic film",
        "Render as a cinematic live-action film: photorealistic, shot on a "
        "professional camera with shallow depth of field, soft motivated "
        "lighting, rich filmic color grade, crisp detail.",
        True, False,
    ),
    "vlog": Style(
        "vlog", "Authentic vlog / UGC",
        "Render as authentic real-life handheld vlog footage: natural daylight, "
        "realistic everyday setting, candid unpolished phone-camera look, "
        "true-to-life people and skin tones.",
        True, False,
    ),
}

DEFAULT_STYLE = "nursery-3d"


def get(key: str) -> Style:
    try:
        return STYLES[key]
    except KeyError:
        raise ValueError(
            f"unknown style {key!r}; choices: {', '.join(STYLES)}"
        ) from None


def keys() -> list[str]:
    return list(STYLES)


def apply(base_prompt: str, key: str) -> str:
    """Prepend the style fragment to the user's prompt (passthrough for 'none')."""
    style = get(key)
    base = (base_prompt or "").strip()
    if not style.prompt:
        return base
    return f"{style.prompt} {base}".strip()
