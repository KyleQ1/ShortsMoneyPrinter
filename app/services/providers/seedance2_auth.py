"""Auto-refreshing Supabase session for the seedance2.ai web API.

seedance2.ai is a Next.js app backed by Supabase auth. Its backend authenticates
requests via the `sb-<ref>-auth-token` cookie (the @supabase/ssr format). A raw
browser cookie expires within the hour, which is why the direct path keeps 401'ing.

This module mints and silently refreshes that session using the project's public
anon key plus a one-time seed credential, then serializes it back into the exact
cookie format seedance2.ai expects. Configure via .env:

    SEEDANCE2_ANON_KEY=<public anon key>          # required
    # then ONE seed:
    SEEDANCE2_EMAIL=...  SEEDANCE2_PASSWORD=...    # preferred (email auth is enabled)
    # or
    SEEDANCE2_REFRESH_TOKEN=<one-time refresh token from a browser session>

The session is cached on disk (gitignored) and refreshed ~1 min before expiry, so a
configured seed means the cookie effectively never goes stale.
"""

from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CACHE_PATH = _PROJECT_ROOT / "storage" / ".seedance2_session.json"
_CHUNK_SIZE = 3180  # @supabase/ssr default
_EXPIRY_SKEW = 60  # refresh this many seconds before the token actually expires


def cookie_header() -> str:
    """Return a ready-to-send Cookie header, or '' if auto-refresh isn't configured."""
    session = current_session()
    if not session:
        return ""
    return _session_to_cookie(session)


def access_token() -> str:
    session = current_session()
    return str(session.get("access_token", "")) if session else ""


def is_configured() -> bool:
    """True if a seed is available to mint/refresh a session (no network call)."""
    if not _anon_key():
        return False
    has_password = bool(os.environ.get("SEEDANCE2_EMAIL") and os.environ.get("SEEDANCE2_PASSWORD"))
    has_refresh = bool(os.environ.get("SEEDANCE2_REFRESH_TOKEN", "").strip())
    return has_password or has_refresh or _load_cache() is not None


def current_session(force_refresh: bool = False) -> dict[str, Any] | None:
    """Return a valid session, refreshing or logging in as needed. None if no seed."""
    anon = _anon_key()
    if not anon:
        return None

    session = _load_cache()
    if session and not force_refresh and not _is_expired(session):
        return session

    # Try refreshing an existing/seed refresh token first (cheap, no password needed).
    refresh_token = (session or {}).get("refresh_token") or os.environ.get("SEEDANCE2_REFRESH_TOKEN", "").strip()
    if refresh_token:
        refreshed = _grant("refresh_token", {"refresh_token": refresh_token})
        if refreshed:
            _save_cache(refreshed)
            return refreshed

    # Fall back to a full password login if credentials are configured.
    email = os.environ.get("SEEDANCE2_EMAIL", "").strip()
    password = os.environ.get("SEEDANCE2_PASSWORD", "").strip()
    if email and password:
        logged_in = _grant("password", {"email": email, "password": password})
        if logged_in:
            _save_cache(logged_in)
            return logged_in

    return None


# --- Supabase auth -----------------------------------------------------------


def _grant(grant_type: str, body: dict[str, Any]) -> dict[str, Any] | None:
    anon = _anon_key()
    url = f"{_base_url()}/auth/v1/token?grant_type={grant_type}"
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                url,
                json=body,
                headers={
                    "apikey": anon,
                    "Authorization": f"Bearer {anon}",
                    "Content-Type": "application/json",
                },
            )
        if response.status_code >= 400:
            return None
        data = response.json()
        if "access_token" not in data:
            return None
        # Normalize expires_at (some grants only return expires_in).
        if "expires_at" not in data and "expires_in" in data:
            data["expires_at"] = int(time.time()) + int(data["expires_in"])
        return data
    except (httpx.HTTPError, ValueError):
        return None


def _is_expired(session: dict[str, Any]) -> bool:
    expires_at = session.get("expires_at")
    if not expires_at:
        return True
    return time.time() >= float(expires_at) - _EXPIRY_SKEW


# --- cookie serialization (@supabase/ssr format) -----------------------------


def _session_to_cookie(session: dict[str, Any]) -> str:
    name = f"sb-{_project_ref()}-auth-token"
    raw = json.dumps(session, separators=(",", ":")).encode("utf-8")
    value = "base64-" + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    if len(value) <= _CHUNK_SIZE:
        return f"{name}={value}"
    chunks = [value[i : i + _CHUNK_SIZE] for i in range(0, len(value), _CHUNK_SIZE)]
    return "; ".join(f"{name}.{i}={chunk}" for i, chunk in enumerate(chunks))


# --- config / cache ----------------------------------------------------------


def _anon_key() -> str:
    return os.environ.get("SEEDANCE2_ANON_KEY", "").strip()


def _project_ref() -> str:
    ref = os.environ.get("SEEDANCE2_SUPABASE_REF", "").strip()
    if ref:
        return ref
    # Decode the ref claim from the anon JWT payload.
    try:
        payload_b64 = _anon_key().split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return str(payload.get("ref", ""))
    except (IndexError, ValueError):
        return ""


def _base_url() -> str:
    override = os.environ.get("SEEDANCE2_SUPABASE_URL", "").strip()
    return override.rstrip("/") if override else f"https://{_project_ref()}.supabase.co"


def _load_cache() -> dict[str, Any] | None:
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def _save_cache(session: dict[str, Any]) -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps(session), encoding="utf-8")
        _CACHE_PATH.chmod(0o600)
    except OSError:
        pass


if __name__ == "__main__":  # quick status check: python -m app.services.providers.seedance2_auth
    try:
        from app import config

        config._load_dotenv()
    except Exception:
        pass
    ref = _project_ref()
    print(f"project ref : {ref or '(unknown)'}")
    print(f"base url    : {_base_url()}")
    print(f"anon key    : {'set' if _anon_key() else 'MISSING'}")
    seed = (
        "email+password"
        if os.environ.get("SEEDANCE2_EMAIL") and os.environ.get("SEEDANCE2_PASSWORD")
        else "refresh_token"
        if os.environ.get("SEEDANCE2_REFRESH_TOKEN")
        else "(none configured)"
    )
    print(f"seed        : {seed}")
    session = current_session(force_refresh=True)
    if session:
        print(f"session     : OK  expires_at={session.get('expires_at')}")
        print("cookie      : ready")
    else:
        print("session     : FAILED — add a seed (SEEDANCE2_EMAIL/PASSWORD or SEEDANCE2_REFRESH_TOKEN) to .env")
