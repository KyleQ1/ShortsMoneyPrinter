"""Direct seedance2.ai provider for local smoke/live testing.

This uses the logged-in seedance2.ai web API shape captured in the smoke-test script.
It is intentionally cookie-based and BYO-session; never commit or log the cookie.
"""

from __future__ import annotations

import mimetypes
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from app.models import AspectRatio

BASE_URL = "https://seedance2.ai"

MODEL_VERSIONS = {
    "seedance-1.5-pro": "seedance-1-5-pro",
    "seedance-2.0": "seedance-2-0",
    "seedance-2.0-fast": "seedance-2-0-fast",
}


def generate_from_image(
    reference_image: str,
    prompt: str,
    out_path: str,
    aspect: AspectRatio = AspectRatio.VERTICAL,
    resolution: str = "480p",
    duration: str = "5",
    model_key: str = "seedance-2.0",
) -> str:
    cookie = temporary_cookie()
    if not cookie:
        raise RuntimeError(
            "Missing SEEDANCE2_COOKIE or SEEDANCE_API_TOKEN. Add it to .env and restart the app."
        )

    image_url = upload_image(cookie, Path(reference_image))
    payload = {
        "prompt": prompt,
        "type": "image-to-video",
        "imageUrls": [image_url],
        "resolution": resolution,
        "duration": int(duration) if str(duration).isdigit() else 5,
        "aspectRatio": aspect.value,
        "cameraFixed": False,
        "imageMode": "single",
        "modelVersion": MODEL_VERSIONS.get(model_key, model_key),
    }
    response = post_json(cookie, f"{BASE_URL}/api/video/byteplus/generate", payload)
    video_url = find_video_url(response)
    if not video_url:
        video_url = poll_for_video_url(cookie, response)
    if not video_url:
        raise RuntimeError(
            "Seedance2.ai accepted the request but did not return a downloadable video URL yet. "
            f"Response keys: {sorted(response) if isinstance(response, dict) else type(response).__name__}"
        )
    download(video_url, out_path)
    return out_path


def upload_image(cookie: str, path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"Seedance2 image upload file not found: {path}")
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    presign_payload = {
        "fileName": path.name,
        "path": f"images/{today}",
        "contentType": content_type,
        "fileSize": path.stat().st_size,
    }
    presign = post_json(cookie, f"{BASE_URL}/api/upload/image/presigned-url", presign_payload)
    upload_url = find_first_key(presign, {"uploadUrl", "presignedUrl", "signedUrl", "url"})
    if not upload_url:
        raise RuntimeError("Seedance2.ai did not return an image upload URL.")

    with httpx.Client(timeout=120, follow_redirects=True) as client:
        response = client.put(
            upload_url,
            content=path.read_bytes(),
            headers={
                "Content-Type": content_type,
                "Origin": BASE_URL,
                "Referer": f"{BASE_URL}/",
            },
        )
        response.raise_for_status()

    public_url = find_first_key(presign, {"publicUrl", "fileUrl", "cdnUrl", "imageUrl"})
    return public_url or derive_cdn_url(upload_url)


def temporary_cookie() -> str:
    # Prefer the auto-refreshing Supabase session when a seed is configured; the live
    # cookie is minted/refreshed on demand so it never goes stale mid-run.
    try:
        from app.services.providers import seedance2_auth

        cookie = seedance2_auth.cookie_header()
        if cookie:
            return cookie
    except Exception:
        pass
    return (os.environ.get("SEEDANCE2_COOKIE") or os.environ.get("SEEDANCE_API_TOKEN") or "").strip()


def post_json(cookie: str, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        response = client.post(
            url,
            json=payload,
            headers={
                "Accept": "*/*",
                "Content-Type": "application/json",
                "Cookie": cookie,
                "Origin": BASE_URL,
                "Referer": f"{BASE_URL}/",
                "User-Agent": "ShortsMoneyPrinter",
            },
        )
        response.raise_for_status()
        if not response.text.strip():
            return {}
        return response.json()


def poll_for_video_url(cookie: str, initial_response: dict[str, Any]) -> str | None:
    job_id = find_first_key(
        initial_response,
        {"taskId", "task_id", "jobId", "job_id", "generationId", "generation_id", "videoId"},
    )
    if not job_id:
        return None

    deadline = time.monotonic() + float(os.environ.get("SEEDANCE2_POLL_SECONDS", "600"))
    endpoints = [
        f"{BASE_URL}/api/video/byteplus/status",
        f"{BASE_URL}/api/video/byteplus/result",
        f"{BASE_URL}/api/video/status",
        f"{BASE_URL}/api/video/result",
    ]
    payloads = [{"id": job_id}, {"taskId": job_id}, {"jobId": job_id}]
    while time.monotonic() < deadline:
        time.sleep(5)
        for endpoint in endpoints:
            for payload in payloads:
                try:
                    response = post_json(cookie, endpoint, payload)
                except httpx.HTTPStatusError:
                    continue
                video_url = find_video_url(response)
                if video_url:
                    return video_url
                status = str(find_first_key(response, {"status", "state"}) or "").lower()
                if status in {"failed", "error", "cancelled", "canceled"}:
                    raise RuntimeError(f"Seedance2.ai generation failed: {response!r}")
    return None


def find_first_key(value: Any, keys: set[str]) -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys and isinstance(item, str):
                return item
        for item in value.values():
            found = find_first_key(item, keys)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_first_key(item, keys)
            if found:
                return found
    return None


def find_video_url(value: Any, parent_key: str = "") -> str | None:
    if isinstance(value, str):
        if value.startswith("http") and _looks_like_video_url(value, parent_key):
            return value
        return None
    if isinstance(value, dict):
        for key, item in value.items():
            found = find_video_url(item, key)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_video_url(item, parent_key)
            if found:
                return found
    return None


def _looks_like_video_url(value: str, key: str) -> bool:
    lower_value = value.lower()
    lower_key = key.lower()
    if any(lower_value.split("?", 1)[0].endswith(ext) for ext in (".mp4", ".mov", ".webm")):
        return True
    if "image" in lower_key or any(ext in lower_value for ext in (".jpg", ".jpeg", ".png", ".webp")):
        return False
    return "video" in lower_key or "result" in lower_key or "output" in lower_key


def derive_cdn_url(upload_url: str) -> str:
    parsed = urlparse(upload_url)
    path = parsed.path.lstrip("/")
    return f"https://cdn.seedance2.ai/{path}"


def download(url: str, dest: str) -> None:
    with httpx.stream("GET", url, timeout=180, follow_redirects=True) as response:
        response.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in response.iter_bytes(1 << 16):
                fh.write(chunk)
