"""Load config.toml into typed settings. Provider-pluggable; blank section = disabled."""

from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

CONFIG_PATH = Path("config.toml")
ENV_PATH = Path(".env")


def _load_dotenv() -> None:
    """Load KEY=VALUE pairs from .env into os.environ (no override of real env vars).

    Keeps secrets (REPLICATE_API_TOKEN, FAL_KEY, etc.) out of config.toml and out of git.
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


class LLMConfig(BaseModel):
    provider: str = "openai"
    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-4o-mini"


class VideoGenConfig(BaseModel):
    provider: str = "none"
    api_key: str = ""
    endpoint: str = "replicate"
    max_ai_seconds: int = 6  # cap AI-gen seconds/video to protect COGS; rest = stock


class StockConfig(BaseModel):
    pexels_api_key: str = ""
    pixabay_api_key: str = ""


class TTSConfig(BaseModel):
    provider: str = "edge"
    api_key: str = ""
    voice: str = "en-US-AriaNeural"


class SubtitleConfig(BaseModel):
    provider: str = "whisper"
    model_size: str = "large-v3"


class DiscoveryConfig(BaseModel):
    enabled: bool = False
    niches: list[str] = []


class AppConfig(BaseModel):
    output_dir: str = "./storage/output"
    work_dir: str = "./storage/work"
    watermark: bool = True


class Settings(BaseModel):
    app: AppConfig = AppConfig()
    llm: LLMConfig = LLMConfig()
    video_gen: VideoGenConfig = VideoGenConfig()
    stock: StockConfig = StockConfig()
    tts: TTSConfig = TTSConfig()
    subtitles: SubtitleConfig = SubtitleConfig()
    discovery: DiscoveryConfig = DiscoveryConfig()


@lru_cache
def get_settings() -> Settings:
    _load_dotenv()
    if not CONFIG_PATH.exists():
        # Fall back to defaults so the skeleton boots; real runs need config.toml.
        return Settings()
    with CONFIG_PATH.open("rb") as fh:
        data = tomllib.load(fh)
    return Settings(**data)
