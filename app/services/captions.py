"""Step 6 — CAPTIONS. Word-level pop-on captions (.ass) timed to the narration.

faster-whisper gives word timestamps; we render them in small pop-on groups — the native
TikTok/Reels caption look. Lighter and far more reliable than burning a drifting SRT.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import get_settings
from app.models import AspectRatio

log = logging.getLogger("omp")

WORDS_PER_CUE = 3  # pop-on group size

# ASS numpad alignment: 2=bottom-center, 5=middle-center, 8=top-center.
_ALIGNMENT = {"bottom": 2, "center": 5, "top": 8}


def align(
    audio_path: str,
    work_dir: Path,
    style: str,
    aspect: AspectRatio,
    position: str = "bottom",
) -> str:
    w, h = aspect.dimensions
    words = _transcribe(audio_path)
    ass = _build_ass(words, w, h, position)
    out = work_dir / "captions.ass"
    out.write_text(ass, encoding="utf-8")
    return str(out)


def _transcribe(audio_path: str) -> list[tuple[float, float, str]]:
    from faster_whisper import WhisperModel  # lazy import (heavy)

    size = get_settings().subtitles.model_size
    try:
        model = WhisperModel(size, device="auto", compute_type="int8")
    except Exception:  # noqa: BLE001 — fall back to plain CPU if auto/int8 unsupported
        model = WhisperModel(size, device="cpu", compute_type="int8")

    segments, _ = model.transcribe(audio_path, word_timestamps=True)
    words: list[tuple[float, float, str]] = []
    for seg in segments:
        for wd in seg.words or []:
            token = wd.word.strip()
            if token:
                words.append((wd.start, wd.end, token))
    return words


def _ts(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _build_ass(words: list[tuple[float, float, str]], w: int, h: int, position: str = "bottom") -> str:
    fontsize = max(36, h // 16)
    alignment = _ALIGNMENT.get(position, 2)
    # MarginV is the inset from the bottom (align 2) or top (align 8); ignored when centered.
    margin_v = 0 if alignment == 5 else int(h * (0.10 if alignment == 8 else 0.16))
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {w}\nPlayResY: {h}\n"
        "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Pop,Arial,{fontsize},&H00FFFFFF,&H000088FF,&H00000000,&H00000000,"
        f"-1,0,0,0,100,100,0,0,1,5,1,{alignment},40,40,{margin_v},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines: list[str] = []
    for i in range(0, len(words), WORDS_PER_CUE):
        group = words[i : i + WORDS_PER_CUE]
        start, end = group[0][0], group[-1][1]
        if end <= start:
            end = start + 0.4
        text = " ".join(g[2] for g in group).replace("{", "(").replace("}", ")")
        lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Pop,,0,0,0,,{text}")
    return header + "\n".join(lines) + "\n"
