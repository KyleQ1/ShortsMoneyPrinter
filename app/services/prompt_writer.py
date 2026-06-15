"""Optional LLM-backed prompt refinement.

The default remix planner is deterministic and does not require an LLM key. This module
is only used when the user explicitly enables the AI prompt writer.
"""

from __future__ import annotations

import httpx

from app.config import get_settings


class PromptWriterError(RuntimeError):
    """Prompt writer failure safe to show to a local app user."""


def configured() -> bool:
    return bool(get_settings().prompts.api_key)


def refine_prompt(
    base_prompt: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    endpoint: str | None = None,
) -> str:
    settings = get_settings().prompts
    key = (api_key or settings.api_key).strip()
    if not key:
        raise PromptWriterError("AI prompt writer needs PROMPT_API_KEY or a prompt API key in the form.")

    model_name = (model or settings.model).strip() or settings.model
    base_url = (endpoint or settings.endpoint).strip().rstrip("/")
    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_name,
                "temperature": 0.4,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Rewrite video generation prompts for short-form AI video. "
                            "Keep the same intent, source-motion instructions, style, duration, "
                            "and safety constraints. Return one concise production prompt only."
                        ),
                    },
                    {"role": "user", "content": base_prompt},
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = _response_detail(exc.response)
        raise PromptWriterError(f"AI prompt writer failed: {detail}") from exc
    except httpx.HTTPError as exc:
        raise PromptWriterError(f"AI prompt writer failed: {exc}") from exc

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise PromptWriterError("AI prompt writer returned an unexpected response.") from exc

    prompt = str(content).strip()
    if not prompt:
        raise PromptWriterError("AI prompt writer returned an empty prompt.")
    return prompt


def _response_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text.strip() or response.reason_phrase
    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if data.get("detail"):
            return str(data["detail"])
    return response.reason_phrase
