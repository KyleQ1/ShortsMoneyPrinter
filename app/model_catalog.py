"""Model catalog loaded from the repo-level models.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ProviderMode = Literal["local", "remote"]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODELS_TOML = PROJECT_ROOT / "models.toml"


@dataclass(frozen=True)
class QualityProfile:
    key: str
    provider_mode: ProviderMode
    provider: str
    model_id: str
    model_label: str
    mode: str
    resolution: str
    input_kind: str
    estimated_cost_per_second: float
    detail: str = ""
    cost_note: str = ""
    cost_per_second_image: float | None = None
    cost_per_second_video: float | None = None
    default_for_mode: bool = False
    recommended: bool = False
    aliases: tuple[str, ...] = ()

    def cost_per_second(self) -> float:
        if self.input_kind == "video" and self.cost_per_second_video is not None:
            return self.cost_per_second_video
        if self.input_kind == "image" and self.cost_per_second_image is not None:
            return self.cost_per_second_image
        return self.estimated_cost_per_second

    def to_api(self) -> dict[str, object]:
        return {
            "key": self.key,
            "quality": self.key,
            "provider_mode": self.provider_mode,
            "provider": self.provider,
            "model_id": self.model_id,
            "label": self.model_label,
            "title": self.model_label,
            "mode": self.mode,
            "resolution": self.resolution,
            "input_kind": self.input_kind,
            "default_for_mode": self.default_for_mode,
            "recommended": self.recommended,
            "estimated_cost_per_second": self.estimated_cost_per_second,
            "cost_per_second_image": self.cost_per_second_image,
            "cost_per_second_video": self.cost_per_second_video,
            "detail": self.detail,
            "cost": self.cost_note,
            "aliases": list(self.aliases),
        }


def load_quality_profiles(path: Path = MODELS_TOML) -> dict[str, QualityProfile]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    models = data.get("models")
    if not isinstance(models, list) or not models:
        raise RuntimeError(f"{path} must define at least one [[models]] entry")

    profiles: dict[str, QualityProfile] = {}
    canonical_keys: list[str] = []
    for item in models:
        if not isinstance(item, dict):
            raise RuntimeError(f"{path} contains an invalid model entry")
        profile = _profile_from_item(item, path)
        if profile.key in profiles:
            raise RuntimeError(f"{path} defines duplicate model key: {profile.key}")
        profiles[profile.key] = profile
        canonical_keys.append(profile.key)
        for alias in profile.aliases:
            if alias in profiles:
                raise RuntimeError(f"{path} defines duplicate model key or alias: {alias}")
            profiles[alias] = profile
    globals()["MODEL_CHOICES"] = tuple(canonical_keys)
    return profiles


def _profile_from_item(item: dict[str, object], path: Path) -> QualityProfile:
    key = _required_str(item, "key", path)
    provider_mode = _required_str(item, "provider_mode", path)
    if provider_mode not in {"local", "remote"}:
        raise RuntimeError(f"{path}: model {key!r} provider_mode must be local or remote")

    return QualityProfile(
        key=key,
        provider_mode=provider_mode,  # type: ignore[arg-type]
        provider=_required_str(item, "provider", path),
        model_id=_required_str(item, "model_id", path),
        model_label=_required_str(item, "label", path),
        mode=_required_str(item, "mode", path),
        resolution=_required_str(item, "resolution", path),
        input_kind=str(item.get("input_kind") or "video"),
        estimated_cost_per_second=_float(item.get("estimated_cost_per_second"), 0.0),
        detail=str(item.get("detail") or ""),
        cost_note=str(item.get("cost_note") or ""),
        cost_per_second_image=_optional_float(item.get("cost_per_second_image")),
        cost_per_second_video=_optional_float(item.get("cost_per_second_video")),
        default_for_mode=bool(item.get("default_for_mode", False)),
        recommended=bool(item.get("recommended", False)),
        aliases=_str_tuple(item.get("aliases")),
    )


def _required_str(item: dict[str, object], key: str, path: Path) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{path}: model entry missing required string field {key!r}")
    return value.strip()


def _float(value: object, default: float) -> float:
    if value is None:
        return default
    return float(value)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _str_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise RuntimeError("aliases must be a list of strings")
    aliases: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RuntimeError("aliases must be a list of strings")
        aliases.append(item.strip())
    return tuple(aliases)


MODEL_CHOICES: tuple[str, ...] = ()
QUALITY_PROFILES = load_quality_profiles()
