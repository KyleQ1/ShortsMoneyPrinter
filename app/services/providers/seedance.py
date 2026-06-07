"""Seedance 2.0 reference-to-video provider. BYO key — optional/Phase-5 feature.

Takes a CONDITIONED reference video (see video_conditioning) + a prompt, and generates a
new short clip guided by it. Seedance is reference-based (subject/motion/style), not a
1:1 frame transform — and inputs must already meet the limits before they get here.

Default backend: Replicate (model `bytedance/seedance-2.0`), token from REPLICATE_API_TOKEN.
Routed by [video_gen] endpoint in config.toml: "replicate" (default) | "fal".
"""

from __future__ import annotations

import logging
import os

import httpx

from app.config import get_settings
from app.models import AspectRatio

log = logging.getLogger("omp")

REPLICATE_MODEL = "bytedance/seedance-2.0"
REPLICATE_MODEL_FAST = "bytedance/seedance-2.0-fast"
REPLICATE_MODEL_15_PRO = "bytedance/seedance-1.5-pro"
FAL_ENDPOINT = "bytedance/seedance-2.0/reference-to-video"
FAL_ENDPOINT_FAST = "bytedance/seedance-2.0/fast/reference-to-video"


def generate_from_video(
    reference_video: str,
    prompt: str,
    out_path: str,
    aspect: AspectRatio = AspectRatio.VERTICAL,
    resolution: str = "720p",
    duration: str = "auto",
    generate_audio: bool = False,
    match_reference: bool = True,
    audio_paths: list[str] | None = None,
    fast: bool = False,
) -> str:
    """Run Seedance reference-to-video; download the result to out_path.

    generate_audio: let Seedance synthesize a NEW audio track (dialogue/music)
        for the output. Mutually exclusive in practice with audio_paths — if you
        pass real audio, leave this off or the model may add its own on top.
    match_reference: when True, the prompt is steered to copy the reference's
        motion/pacing/framing (a near-recreation). Set False to use the
        reference only as loose inspiration and let `prompt` drive a different
        result.
    audio_paths: real audio file(s) to feed as `reference_audios` (≤3, ≤15s
        total). The output is driven by / carries this audio instead of random
        generated music — e.g. pass the source clip's own narration.
    fast: use the Seedance 2.0 *Fast* model — cheaper, slightly quicker, 720p
        cap (no 1080p). Quality gap is mostly in human fidelity/fine detail,
        which stylized/animation output hides — good default for the 720p
        animation pipeline; prefer standard for photoreal/live-action at 1080p.
    """
    endpoint = (get_settings().video_gen.endpoint or "replicate").lower()
    if endpoint == "replicate":
        return _via_replicate(
            reference_video, prompt, out_path, aspect, resolution, duration,
            generate_audio, match_reference, audio_paths, fast,
        )
    if endpoint == "fal":
        return _via_fal(
            reference_video, prompt, out_path, aspect, resolution, duration,
            generate_audio, match_reference, audio_paths, fast,
        )
    raise RuntimeError(f"Unknown [video_gen] endpoint {endpoint!r} (use 'replicate' or 'fal').")


def generate_from_image(
    reference_image: str,
    prompt: str,
    out_path: str,
    aspect: AspectRatio = AspectRatio.VERTICAL,
    resolution: str = "480p",
    duration: str = "4",
) -> str:
    """Run the budget Seedance image-to-video path via Replicate.

    The MVP keeps Replicate as the stable remote provider. This wrapper is intentionally
    small because tests and local development usually mock provider calls; real users only
    hit it when they choose the budget live mode with ``REPLICATE_API_TOKEN`` set.
    """
    endpoint = (get_settings().video_gen.endpoint or "replicate").lower()
    if endpoint != "replicate":
        raise RuntimeError("budget Seedance image-to-video is only wired for Replicate")

    cfg = get_settings().video_gen
    token = cfg.api_key or os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError(
            "No Replicate token. Set REPLICATE_API_TOKEN in .env (or [video_gen] api_key)."
        )
    os.environ["REPLICATE_API_TOKEN"] = token

    try:
        import replicate  # lazy; optional dependency
    except ImportError as exc:
        raise RuntimeError("Seedance via Replicate needs: pip install replicate") from exc

    dur = -1 if str(duration) == "auto" else int(duration)
    log.info("calling Seedance on Replicate (%s) …", REPLICATE_MODEL_15_PRO)
    with open(reference_image, "rb") as image_fh:
        output = replicate.run(
            REPLICATE_MODEL_15_PRO,
            input={
                "prompt": prompt,
                "reference_image": image_fh,
                "resolution": resolution,
                "duration": dur,
                "aspect_ratio": aspect.value,
                "generate_audio": False,
            },
        )
    url = _replicate_output_url(output)
    if not url:
        raise RuntimeError(f"Seedance/Replicate returned no video URL: {output!r}")
    _download(url, out_path)
    log.info("seedance clip → %s", out_path)
    return out_path


def _build_prompt(prompt: str, ref_token: str, match_reference: bool) -> str:
    """Compose the full multimodal prompt around the reference-video token."""
    if match_reference:
        return f"{prompt} Match the motion, pacing, and framing of {ref_token}.".strip()
    # Looser steer: keep the reference as inspiration but let `prompt` lead.
    return (
        f"{prompt} Use {ref_token} only as loose visual reference; "
        "you may reinterpret the subject, setting, and style as a new scene."
    ).strip()


# ---------------------------------------------------------------- Replicate (default)

def _via_replicate(
    reference_video, prompt, out_path, aspect, resolution, duration,
    generate_audio=False, match_reference=True, audio_paths=None, fast=False,
) -> str:
    cfg = get_settings().video_gen
    token = cfg.api_key or os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError(
            "No Replicate token. Set REPLICATE_API_TOKEN in .env (or [video_gen] api_key)."
        )
    os.environ["REPLICATE_API_TOKEN"] = token

    try:
        import replicate  # lazy; optional dependency
    except ImportError as exc:
        raise RuntimeError("Seedance via Replicate needs: pip install replicate") from exc

    model = REPLICATE_MODEL_FAST if fast else REPLICATE_MODEL
    if fast and resolution == "1080p":
        log.warning("Seedance 2.0 Fast caps at 720p; downgrading 1080p → 720p")
        resolution = "720p"

    dur = -1 if str(duration) == "auto" else int(duration)
    # Reference the uploaded clip via [Video1] per Seedance's multimodal prompt syntax.
    full_prompt = _build_prompt(prompt, "[Video1]", match_reference)

    log.info("calling Seedance on Replicate (%s) …", model)
    import contextlib

    with contextlib.ExitStack() as stack:
        payload = {
            "prompt": full_prompt,
            "reference_videos": [stack.enter_context(open(reference_video, "rb"))],
            "resolution": resolution,
            "duration": dur,
            "aspect_ratio": aspect.value,
            "generate_audio": generate_audio,
        }
        if audio_paths:
            # Feed real audio (e.g. the source narration) so the output carries it
            # instead of random generated music.
            payload["reference_audios"] = [
                stack.enter_context(open(p, "rb")) for p in audio_paths
            ]
            log.info("  + %d reference audio file(s)", len(audio_paths))
        output = replicate.run(model, input=payload)

    url = _replicate_output_url(output)
    if not url:
        raise RuntimeError(f"Seedance/Replicate returned no video URL: {output!r}")
    _download(url, out_path)
    log.info("seedance clip → %s", out_path)
    return out_path


def _replicate_output_url(output) -> str | None:
    """replicate>=1.0 returns a FileOutput (URL-like) or a list of them."""
    if isinstance(output, (list, tuple)):
        output = output[0] if output else None
    if output is None:
        return None
    return getattr(output, "url", None) or str(output)


# ---------------------------------------------------------------- fal (non-default)

def _via_fal(
    reference_video, prompt, out_path, aspect, resolution, duration,
    generate_audio=False, match_reference=True, audio_paths=None, fast=False,
) -> str:
    if audio_paths:
        log.warning("audio_paths is only wired for the Replicate endpoint; ignoring on fal.")
    endpoint_id = FAL_ENDPOINT_FAST if fast else FAL_ENDPOINT
    if fast and resolution == "1080p":
        log.warning("Seedance 2.0 Fast caps at 720p; downgrading 1080p → 720p")
        resolution = "720p"
    cfg = get_settings().video_gen
    key = cfg.api_key or os.environ.get("FAL_KEY")
    if not key:
        raise RuntimeError("No fal key. Set FAL_KEY or switch [video_gen] endpoint to 'replicate'.")
    os.environ["FAL_KEY"] = key

    try:
        import fal_client  # lazy; optional dependency
    except ImportError as exc:
        raise RuntimeError('fal endpoint needs fal-client: pip install fal-client') from exc

    log.info("uploading reference video to fal …")
    video_url = fal_client.upload_file(reference_video)
    full_prompt = _build_prompt(prompt, "@Video1", match_reference)
    args = {
        "prompt": full_prompt,
        "video_urls": [video_url],
        "resolution": resolution,
        "duration": duration,
        "aspect_ratio": aspect.value,
        "generate_audio": generate_audio,
    }
    log.info("calling Seedance (%s) …", endpoint_id)
    result = fal_client.subscribe(endpoint_id, arguments=args, with_logs=False)
    url = _fal_result_url(result)
    if not url:
        raise RuntimeError(f"Seedance returned no video URL: {result!r}")
    _download(url, out_path)
    log.info("seedance clip → %s", out_path)
    return out_path


def _fal_result_url(result: dict) -> str | None:
    video = result.get("video")
    if isinstance(video, dict):
        return video.get("url")
    if isinstance(result.get("videos"), list) and result["videos"]:
        return result["videos"][0].get("url")
    return result.get("url")


def _download(url: str, dest: str) -> None:
    with httpx.stream("GET", url, timeout=180, follow_redirects=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_bytes(1 << 16):
                fh.write(chunk)
