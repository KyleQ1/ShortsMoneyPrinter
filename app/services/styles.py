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

import json
import re
from dataclasses import dataclass
from pathlib import Path

# User overrides + custom styles live here (gitignored). Built-ins are the defaults.
STYLES_FILE = Path("storage/styles.json")


@dataclass(frozen=True)
class Style:
    key: str
    label: str
    prompt: str            # style fragment, prepended to the user's prompt
    match_reference: bool  # keep source motion/pacing/framing?
    kids: bool             # is this a young-kids / family look?


# Ordered registry. First match wins; `none` is the passthrough.
BUILTIN_STYLES: dict[str, Style] = {
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


# --- persistence overlay -----------------------------------------------------


def _read_overlay() -> dict:
    try:
        data = json.loads(STYLES_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("styles", {})
    data.setdefault("hidden", [])
    return data


def _write_overlay(overlay: dict) -> None:
    STYLES_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STYLES_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(overlay, indent=2), encoding="utf-8")
    tmp.replace(STYLES_FILE)


def _registry() -> dict[str, Style]:
    """Built-in styles overlaid with the user's saved edits/customs, minus hidden keys."""
    overlay = _read_overlay()
    registry: dict[str, Style] = dict(BUILTIN_STYLES)
    for key, item in overlay["styles"].items():
        if not isinstance(item, dict):
            continue
        registry[key] = Style(
            key=key,
            label=str(item.get("label") or key),
            prompt=str(item.get("prompt") or ""),
            match_reference=bool(item.get("match_reference", True)),
            kids=bool(item.get("kids", False)),
        )
    for key in overlay["hidden"]:
        registry.pop(key, None)
    return registry


# --- read API ----------------------------------------------------------------


def get(key: str) -> Style:
    registry = _registry()
    try:
        return registry[key]
    except KeyError:
        raise ValueError(f"unknown style {key!r}; choices: {', '.join(registry)}") from None


def keys() -> list[str]:
    return list(_registry())


def all_styles() -> list[Style]:
    return list(_registry().values())


def is_builtin(key: str) -> bool:
    return key in BUILTIN_STYLES


def is_overridden(key: str) -> bool:
    return key in _read_overlay()["styles"]


def to_dict(style: Style) -> dict:
    return {
        "key": style.key,
        "label": style.label,
        "prompt": style.prompt,
        "match_reference": style.match_reference,
        "kids": style.kids,
        "builtin": is_builtin(style.key),
        "custom": not is_builtin(style.key),
        "overridden": is_overridden(style.key),
    }


def apply(base_prompt: str, key: str) -> str:
    """Prepend the style fragment to the user's prompt (passthrough for an empty fragment)."""
    style = get(key)
    base = (base_prompt or "").strip()
    if not style.prompt:
        return base
    return f"{style.prompt} {base}".strip()


# --- write API (save / edit / create / delete / reset) -----------------------


_KEY_RE = re.compile(r"[^a-z0-9-]+")


def slugify(label: str) -> str:
    slug = _KEY_RE.sub("-", (label or "").strip().lower()).strip("-")
    return slug or "style"


def save_style(label: str, prompt: str, *, key: str | None = None,
               match_reference: bool = True, kids: bool = False) -> Style:
    label = (label or "").strip()
    if not label:
        raise ValueError("Style label is required.")
    key = (key or slugify(label)).strip()
    if not key:
        raise ValueError("Style key is required.")
    overlay = _read_overlay()
    overlay["styles"][key] = {
        "label": label,
        "prompt": (prompt or "").strip(),
        "match_reference": bool(match_reference),
        "kids": bool(kids),
    }
    if key in overlay["hidden"]:
        overlay["hidden"].remove(key)
    _write_overlay(overlay)
    return get(key)


def delete_style(key: str) -> None:
    if key == DEFAULT_STYLE:
        raise ValueError("Cannot delete the default style.")
    overlay = _read_overlay()
    removed = overlay["styles"].pop(key, None)
    if key in BUILTIN_STYLES:
        if key not in overlay["hidden"]:
            overlay["hidden"].append(key)  # built-ins are hidden, not erased
    elif removed is None:
        raise ValueError(f"unknown style {key!r}")
    _write_overlay(overlay)


def reset_style(key: str) -> Style:
    """Drop a single built-in's override/hide, restoring its shipped default."""
    overlay = _read_overlay()
    overlay["styles"].pop(key, None)
    if key in overlay["hidden"]:
        overlay["hidden"].remove(key)
    _write_overlay(overlay)
    return get(key)


def reset_all() -> None:
    STYLES_FILE.unlink(missing_ok=True)
