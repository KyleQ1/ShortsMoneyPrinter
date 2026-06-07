"""ShortsMoneyPrinter CLI.

    smp recreate <url> [--aspect 9:16] [--voice en-US-AriaNeural] [--out file.mp4]
    smp version

Phase-1 entry point (the desktop UI wraps this engine in Phase 2).
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys

from app import __version__, store
from app.models import AspectRatio, CreateRequest


def _recreate(args: argparse.Namespace) -> int:
    if shutil.which("ffmpeg") is None:
        print("error: ffmpeg not found on PATH. Install it first.", file=sys.stderr)
        return 2

    request = CreateRequest(
        source_url=args.url,
        aspect=AspectRatio(args.aspect),
        voice=args.voice,
    )
    job = store.create_job(request)
    print(f"job {job.id}: recreating {args.url}")

    from app.pipeline import run_pipeline  # deferred import keeps `smp version` cheap

    job = run_pipeline(job.id)
    if job.status.value == "done":
        out = args.out or job.output_path
        if args.out and job.output_path and args.out != job.output_path:
            shutil.copyfile(job.output_path, args.out)
        print(f"\n✅ done → {out}")
        return 0
    print(f"\n❌ failed: {job.error}", file=sys.stderr)
    return 1


def _test_seedance(args: argparse.Namespace) -> int:
    """De-risk Seedance: condition any video to its limits, then (with a key) run it."""
    import os
    from pathlib import Path

    from app.config import get_settings
    from app.models import AspectRatio
    from app.services import styles, video_conditioning

    work = Path("storage/work/seedance_test")
    work.mkdir(parents=True, exist_ok=True)
    cond = str(work / "conditioned.mp4")

    print(f"conditioning {args.video} → Seedance limits …")
    video_conditioning.condition(args.video, cond, max_seconds=args.seconds)
    iw, ih, dur = video_conditioning.probe(cond)
    mb = Path(cond).stat().st_size / 1e6
    ok = dur <= 15.0 and iw * ih <= 927_408 and mb < 50
    print(f"{'✅' if ok else '⚠️ '} conditioned → {cond}  ({iw}x{ih}, {dur:.1f}s, {mb:.1f} MB)")

    endpoint = (get_settings().video_gen.endpoint or "replicate").lower()
    have_key = bool(get_settings().video_gen.api_key) or (
        bool(os.environ.get("REPLICATE_API_TOKEN")) if endpoint == "replicate"
        else bool(os.environ.get("FAL_KEY"))
    )
    if not have_key:
        key_hint = "$REPLICATE_API_TOKEN" if endpoint == "replicate" else "$FAL_KEY"
        print(f"ℹ️  no {endpoint} key ([video_gen] api_key or {key_hint}) — skipping the live API call.")
        print("   Conditioning works; add a key to verify the Seedance round-trip end-to-end.")
        return 0

    # Feed the source's own audio (narration) instead of letting Seedance invent music.
    audio_paths = None
    if args.keep_audio:
        import subprocess
        src_audio = str(work / "source_audio.m4a")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", args.video,
             "-t", f"{min(args.seconds, 15.0):.3f}", "-vn", "-c:a", "aac", "-b:a", "128k", src_audio],
            check=True,
        )
        audio_paths = [src_audio]
        print(f"🔊 feeding source audio → {src_audio}")

    # Compose the animation style into the prompt (e.g. CoComelon-style 3D).
    style = styles.get(args.style)
    styled_prompt = styles.apply(args.prompt, args.style)
    # --different always loosens; otherwise the style's own preference wins.
    match_reference = (not args.different) and style.match_reference
    if style.key != "none":
        print(f"🎨 style: {style.label}")

    fast = not args.standard
    print(f"🚀 model: Seedance 2.0 {'Fast' if fast else 'Standard'}")

    from app.services.providers import seedance
    out = str(work / "seedance_out.mp4")
    print("calling Seedance (this costs credits) …")
    seedance.generate_from_video(
        cond, styled_prompt, out, AspectRatio(args.aspect), duration=str(args.duration),
        generate_audio=args.audio, match_reference=match_reference, audio_paths=audio_paths,
        fast=fast,
    )
    print(f"✅ seedance output → {out}")
    return 0


def _split(args: argparse.Namespace) -> int:
    """Scene-cut-aware split preview (ffmpeg only — no API, no spend)."""
    from app.services import video_conditioning as vc

    if shutil.which("ffmpeg") is None:
        print("error: ffmpeg not found on PATH.", file=sys.stderr)
        return 2

    _, _, dur = vc.probe(args.video)
    cuts = vc.detect_cuts(args.video, threshold=args.threshold)
    plan = vc.plan_segments(cuts, dur, min_seconds=args.min, max_seconds=args.max)
    print(f"{args.video}: {dur:.1f}s, {len(cuts)} scene cut(s), → {len(plan)} block(s)\n")
    for i, (start, length) in enumerate(plan):
        snap = any(abs(start - c) < 0.05 for c in cuts)
        mark = "cut" if (i > 0 and snap) else ("start" if i == 0 else "forced")
        print(f"  block {i:>2}  {start:6.2f}–{start + length:6.2f}s  ({length:4.1f}s)  [{mark}]")

    if args.write:
        out_dir = args.write
        paths = vc.smart_segments(
            args.video, out_dir, min_seconds=args.min, max_seconds=args.max,
            threshold=args.threshold,
        )
        print(f"\nwrote {len(paths)} conditioned block(s) → {out_dir}/")
    else:
        print("\n(preview only — pass --write <dir> to encode the conditioned blocks)")
    return 0


def _styles(_args: argparse.Namespace) -> int:
    from app.services import styles

    print("style presets (animation + live-action):\n")
    for key in styles.keys():
        st = styles.get(key)
        tag = " (kids/family)" if st.kids else ""
        print(f"  {key:<12} {st.label}{tag}")
    print("\nuse:  smp test-seedance <video> --style <key> [--keep-audio]")
    return 0


def _run(args: argparse.Namespace) -> int:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        print("error: ffmpeg/ffprobe not found on PATH. Install ffmpeg first.", file=sys.stderr)
        return 2
    if args.live and args.max_cost is None:
        print("error: --max-cost is required with --live", file=sys.stderr)
        return 2

    from app.remix_runner import RemixRequest, create_plan, run_live, user_error_message

    request = RemixRequest(
        source=args.source,
        style=args.style,
        prompt=args.prompt,
        quality=args.quality,
        max_cost=args.max_cost,
        captions=args.captions,
        max_total_seconds=args.max_total_seconds,
        wan_command=args.wan_command,
    )
    try:
        plan = create_plan(request)
        print(f"run {plan.run_id}")
        print(f"  source: {plan.source}")
        print(f"  duration: {plan.duration:.1f}s")
        print(f"  blocks: {plan.block_count}")
        print(f"  model: {plan.model_label} ({plan.resolution}, {plan.mode})")
        print(f"  estimated cost: ${plan.estimated_cost:.2f}")
        print(f"  plan: {plan.run_dir}/plan.json")
        if not args.live:
            return 0
        plan = run_live(plan.run_id, args.max_cost)
        print(f"\n✅ final → {plan.final_path}")
        return 0
    except Exception as exc:
        print(f"error: {user_error_message(exc)}", file=sys.stderr)
        return 1


def _serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print("error: smp serve needs FastAPI extras. Install project dependencies.", file=sys.stderr)
        return 2

    url = f"http://{args.host}:{args.port}"
    if args.open:
        import webbrowser

        webbrowser.open(url)
    print(f"serving ShortsMoneyPrinter at {url}")
    uvicorn.run("app.server:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def _runs(_args: argparse.Namespace) -> int:
    from app.remix_runner import list_runs

    runs = list_runs()
    if not runs:
        print("no runs yet")
        return 0
    for plan in runs:
        final = f" → {plan.final_path}" if plan.final_path else ""
        print(
            f"{plan.run_id}  {plan.status:<7}  {plan.quality:<8}  "
            f"{plan.duration:>5.1f}s  ${plan.estimated_cost:>5.2f}{final}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="smp", description="ShortsMoneyPrinter — recreate a winning short with AI.")
    parser.add_argument("--verbose", "-v", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="plan or run a remix from a URL/local video")
    run.add_argument("source", help="URL or local video path")
    run.add_argument("--style", default="nursery-3d", help="style preset; run 'smp styles' to list")
    run.add_argument("--prompt", default=None, help="optional direction to add to generated block prompts")
    run.add_argument(
        "--quality",
        default="standard",
        choices=["budget", "standard", "premium", "local"],
        help="budget=Seedance 1.5 image-to-video, standard=Seedance 2.0 Fast, "
        "premium=Seedance 2.0, local=Wan command",
    )
    run.add_argument("--live", action="store_true", help="spend credits and generate video")
    run.add_argument("--max-cost", type=float, default=None, help="required for --live")
    run.add_argument(
        "--captions",
        action="store_true",
        help="opt in to burned-in captions; off by default and adds transcription/render time",
    )
    run.add_argument("--max-total-seconds", type=float, default=None, help="cap source duration")
    run.add_argument(
        "--wan-command",
        default=None,
        help="local mode command with {input} {keyframe} {prompt} {output} {index}",
    )
    run.set_defaults(func=_run)

    serve = sub.add_parser("serve", help="serve the local browser UI")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    serve.add_argument("--open", action=argparse.BooleanOptionalAction, default=True)
    serve.add_argument("--reload", action="store_true", help="enable uvicorn autoreload")
    serve.set_defaults(func=_serve)

    sub.add_parser("runs", help="list recent local remix runs").set_defaults(func=_runs)

    r = sub.add_parser("recreate", help="recreate a video from a URL")
    r.add_argument("url", help="URL of the short to recreate")
    r.add_argument("--aspect", default="9:16", choices=["9:16", "16:9", "1:1"])
    r.add_argument("--voice", default=None, help="TTS voice (edge-tts), e.g. en-US-AriaNeural")
    r.add_argument("--out", default=None, help="copy the final mp4 to this path")
    r.set_defaults(func=_recreate)

    s = sub.add_parser("test-seedance", help="condition a video to Seedance limits, then test the API")
    s.add_argument("video", help="path to a local video file")
    s.add_argument("--prompt", default="Recreate this in a clean, modern style.")
    s.add_argument("--aspect", default="9:16", choices=["9:16", "16:9", "1:1"])
    s.add_argument("--seconds", type=float, default=12.0, help="max reference length (<=15)")
    s.add_argument("--duration", default="auto", help="output length: 'auto' or 4-15")
    s.add_argument("--audio", action="store_true", help="let Seedance generate a NEW audio track (random music/dialogue)")
    s.add_argument("--keep-audio", action="store_true",
                   help="feed the source video's own audio (narration) so the output carries it, not random music")
    s.add_argument("--different", action="store_true",
                   help="loosen reference matching so the prompt drives a different result")
    s.add_argument("--style", default="none",
                   help="animation style preset (e.g. nursery-3d, anime, claymation); "
                        "run 'smp styles' to list them")
    s.add_argument("--standard", action="store_true",
                   help="use Seedance 2.0 Standard (1080p-capable, higher fidelity); "
                        "default is the cheaper 720p Fast model")
    s.set_defaults(func=_test_seedance)

    sp = sub.add_parser("split", help="preview/encode scene-cut-aware blocks (no API spend)")
    sp.add_argument("video", help="path to a local video file")
    sp.add_argument("--max", type=float, default=12.0, help="max block length (≤15)")
    sp.add_argument("--min", type=float, default=4.0, help="min block length (avoid slivers)")
    sp.add_argument("--threshold", type=float, default=0.4, help="scene score 0–1; lower = more cuts")
    sp.add_argument("--write", default=None, metavar="DIR", help="encode conditioned blocks into DIR")
    sp.set_defaults(func=_split)

    sub.add_parser("styles", help="list animation style presets").set_defaults(func=_styles)

    v = sub.add_parser("version", help="print version")
    v.set_defaults(func=lambda _a: (print(__version__), 0)[1])

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
