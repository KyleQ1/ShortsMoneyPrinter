"""LLM provider adapter. OpenAI-compatible client → OpenAI, Ollama, DeepSeek, etc.

Pluggable (inherited from MoneyPrinterTurbo's best trait): set provider/base_url/model
in config.toml. For Ollama, set base_url=http://localhost:11434/v1 (api_key can be blank).
"""

from __future__ import annotations

import json

from app.config import get_settings


def _client():
    from openai import OpenAI  # imported lazily so `omp version` doesn't need the dep

    cfg = get_settings().llm
    if not cfg.api_key and not cfg.base_url:
        raise RuntimeError(
            "No LLM configured. Set [llm] api_key (and model) in config.toml, "
            "or point base_url at a local Ollama (http://localhost:11434/v1)."
        )
    # Local servers (Ollama) often need no key; OpenAI's client requires a non-empty string.
    return OpenAI(api_key=cfg.api_key or "not-needed", base_url=cfg.base_url or None)


def complete(prompt: str, *, system: str | None = None, json_mode: bool = False) -> str:
    cfg = get_settings().llm
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs: dict = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    resp = _client().chat.completions.create(model=cfg.model, messages=messages, **kwargs)
    return (resp.choices[0].message.content or "").strip()


def complete_json(prompt: str, *, system: str | None = None) -> dict:
    """Completion that must return a JSON object. Tolerates models that wrap it in prose."""
    text = complete(prompt, system=system, json_mode=True)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some providers ignore json_mode; salvage the first {...} block.
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise
