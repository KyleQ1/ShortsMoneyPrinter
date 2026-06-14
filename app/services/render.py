"""ffmpeg caption helpers shared by the remix engine."""

from __future__ import annotations

import subprocess
from functools import lru_cache


@lru_cache(maxsize=1)
def _has_subtitles_filter() -> bool:
    """True if this ffmpeg was built with libass (the subtitles filter). Bundled builds must be."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
    return any(line.split()[1:2] == ["subtitles"] for line in out.stdout.splitlines() if line.strip())


def _escape_path(path: str) -> str:
    """Escape a path for the ffmpeg subtitles filter value (filtergraph-level, no shell).

    The graph is passed via argv, so we escape the chars special to filtergraph parsing
    (\\, :, ') rather than wrapping in shell quotes (which ffmpeg would take literally).
    """
    return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
