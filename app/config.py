"""Runtime settings, sourced from environment variables (and .env) with sensible defaults.

There is no config file: models live in models.toml, and the few runtime knobs below come
from the environment. To add a setting, add a field to the matching model and read one env
var for it in get_settings(). Secrets (REPLICATE_API_TOKEN, FAL_KEY, …) stay in .env.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

ENV_PATH = Path(".env")


def _load_dotenv() -> None:
    """Load KEY=VALUE pairs from .env into os.environ (without overriding real env vars).

    Minimal on purpose — no python-dotenv dependency.
    """
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class VideoGenConfig(BaseModel):
    api_key: str = ""
    endpoint: str = "replicate"  # "replicate" or "fal"


class TTSConfig(BaseModel):
    provider: str = "edge"
    api_key: str = ""
    voice: str = "en-US-AriaNeural"


class SubtitleConfig(BaseModel):
    provider: str = "whisper"
    model_size: str = "large-v3"


class Settings(BaseModel):
    video_gen: VideoGenConfig = VideoGenConfig()
    tts: TTSConfig = TTSConfig()
    subtitles: SubtitleConfig = SubtitleConfig()


@lru_cache
def get_settings() -> Settings:
    _load_dotenv()
    return Settings(
        video_gen=VideoGenConfig(
            api_key=os.environ.get("VIDEO_GEN_API_KEY", ""),
            endpoint=os.environ.get("VIDEO_ENDPOINT", "replicate"),
        ),
        tts=TTSConfig(voice=os.environ.get("TTS_VOICE", "en-US-AriaNeural")),
        subtitles=SubtitleConfig(model_size=os.environ.get("WHISPER_MODEL", "large-v3")),
    )
