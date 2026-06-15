#!/usr/bin/env python3
"""Smoke-test seedance2.ai's logged-in generation endpoint.

This is intentionally a developer utility, not the OSS provider path. It depends on
a logged-in seedance2.ai browser session and may spend credits.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

BASE_URL = "https://seedance2.ai"

MODEL_VERSIONS = {
    "seedance-1.5-pro": "seedance-1-5-pro",
    "seedance-2.0": "seedance-2-0",
    "seedance-2.0-fast": "seedance-2-0-fast",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test seedance2.ai generation")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--image-url", action="append", default=[], help="already-uploaded image URL")
    parser.add_argument("--image", action="append", default=[], help="local image to upload first")
    parser.add_argument(
        "--model",
        action="append",
        choices=sorted(MODEL_VERSIONS),
        help="model to test; repeat to compare. Defaults to seedance-1.5-pro and seedance-2.0",
    )
    parser.add_argument("--model-version", help="raw seedance2.ai modelVersion override")
    parser.add_argument("--resolution", default="480p", choices=["480p", "720p", "1080p"])
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--aspect-ratio", default="9:16")
    parser.add_argument("--output", default=None, help="write JSON response(s) to this path")
    parser.add_argument("--dry-run", action="store_true", help="print request payloads without calling generate")
    args = parser.parse_args()

    cookie = os.environ.get("SEEDANCE2_COOKIE")
    if not cookie:
        print(
            "error: set SEEDANCE2_COOKIE to your seedance2.ai Cookie header value. "
            "Do not commit it.",
            file=sys.stderr,
        )
        return 2

    image_urls = list(args.image_url)
    for image in args.image:
        image_urls.append(upload_image(cookie, Path(image)))
    if not image_urls:
        print("error: pass --image-url or --image", file=sys.stderr)
        return 2

    models = args.model or ["seedance-1.5-pro", "seedance-2.0"]
    responses: list[dict[str, Any]] = []
    for model in models:
        model_version = args.model_version or MODEL_VERSIONS[model]
        payload = {
            "prompt": args.prompt,
            "type": "image-to-video",
            "imageUrls": image_urls,
            "resolution": args.resolution,
            "duration": args.duration,
            "aspectRatio": args.aspect_ratio,
            "cameraFixed": False,
            "imageMode": "single" if len(image_urls) == 1 else "multi",
            "modelVersion": model_version,
        }
        if args.dry_run:
            responses.append({"model": model, "payload": payload})
            continue
        response = post_json(cookie, f"{BASE_URL}/api/video/byteplus/generate", payload)
        responses.append({"model": model, "modelVersion": model_version, "response": response})
        print(json.dumps(responses[-1], indent=2))

    if args.output:
        Path(args.output).write_text(json.dumps(responses, indent=2) + "\n", encoding="utf-8")
    elif args.dry_run:
        print(json.dumps(responses, indent=2))
    return 0


def upload_image(cookie: str, path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"image not found: {path}")
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
        raise SystemExit(f"could not find upload URL in presign response: {presign!r}")

    data = path.read_bytes()
    request = Request(
        upload_url,
        data=data,
        method="PUT",
        headers={
            "Content-Type": content_type,
            "Content-Length": str(len(data)),
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/",
        },
    )
    with urlopen(request) as response:
        if response.status >= 400:
            raise SystemExit(f"upload failed: HTTP {response.status}")

    public_url = find_first_key(presign, {"publicUrl", "fileUrl", "cdnUrl", "imageUrl"})
    if public_url:
        return public_url
    return derive_cdn_url(upload_url)


def post_json(cookie: str, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Cookie": cookie,
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/",
            "User-Agent": "ShortsMoneyPrinter smoke-test",
        },
    )
    try:
        with urlopen(request) as response:
            body = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}:\n{body}") from exc
    if not body.strip():
        return {}
    return json.loads(body)


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


def derive_cdn_url(upload_url: str) -> str:
    parsed = urlparse(upload_url)
    path = parsed.path.lstrip("/")
    return f"https://cdn.seedance2.ai/{path}"


if __name__ == "__main__":
    raise SystemExit(main())
