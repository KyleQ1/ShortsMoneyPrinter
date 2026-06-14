"""Core data models for the remix engine."""

from __future__ import annotations

from enum import Enum


class AspectRatio(str, Enum):
    VERTICAL = "9:16"
    HORIZONTAL = "16:9"
    SQUARE = "1:1"

    @property
    def dimensions(self) -> tuple[int, int]:
        return {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}[self.value]

    @property
    def pexels_orientation(self) -> str:
        return {"9:16": "portrait", "16:9": "landscape", "1:1": "square"}[self.value]
