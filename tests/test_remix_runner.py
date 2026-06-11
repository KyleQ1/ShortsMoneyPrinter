from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.server as server
import app.remix_runner as remix_runner
from app.remix_runner import (
    QUALITY_PROFILES,
    RemixProvider,
    RemixRequest,
    create_plan,
    generate_prompt,
    list_runs,
    load_plan,
    run_live,
)


pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe required for remix runner integration tests",
)


def _tiny_mp4(path: Path, seconds: float = 1.0) -> Path:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"testsrc=size=180x320:rate=30:duration={seconds}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={seconds}",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(path),
        ],
        check=True,
    )
    return path


class CopyProvider(RemixProvider):
    def __init__(self) -> None:
        self.calls: list[int] = []

    def generate_block(self, plan, block) -> str:
        self.calls.append(block.index)
        shutil.copyfile(block.ref_video, block.generated_path)
        return block.generated_path


class FailingProvider(RemixProvider):
    def generate_block(self, plan, block) -> str:
        raise AssertionError("provider should not be called")


def test_quality_profiles_match_mvp_modes():
    assert QUALITY_PROFILES["budget"].model_label == "Replicate Seedance 1.5 Pro"
    assert QUALITY_PROFILES["budget"].mode == "image-to-video"
    assert QUALITY_PROFILES["budget"].resolution == "480p"
    assert QUALITY_PROFILES["budget"].estimated_cost_per_second == 0.013
    assert QUALITY_PROFILES["standard"].model_label == "Replicate Seedance 2.0 Fast"
    assert QUALITY_PROFILES["standard"].mode == "video-to-video"
    assert QUALITY_PROFILES["standard"].resolution == "480p"
    assert QUALITY_PROFILES["standard"].estimated_cost_per_second == 0.08
    assert QUALITY_PROFILES["premium"].model_label == "Replicate Seedance 2.0"
    assert QUALITY_PROFILES["premium"].mode == "video-to-video"
    assert QUALITY_PROFILES["premium"].resolution == "720p"
    assert QUALITY_PROFILES["premium"].estimated_cost_per_second == 0.22
    assert QUALITY_PROFILES["local"].model_label == "Wan 2.2 TI2V-5B"


def test_prompt_generation_is_deterministic():
    one = generate_prompt(0, 0.0, 3.25, "nursery-3d")
    two = generate_prompt(0, 0.0, 3.25, "nursery-3d")
    assert one == two
    assert "Recreate block 000" in one

    custom = generate_prompt(0, 0.0, 3.25, "nursery-3d", "make it playful")
    assert "User direction: make it playful" in custom

    directed = generate_prompt(
        0,
        0.0,
        3.25,
        "nursery-3d",
        subject_prompt="money facts for teenagers",
        script_prompt="fast Hindi narration",
        language="hi",
    )
    assert "Target language" in directed
    assert "Video subject: money facts for teenagers" in directed
    assert "Script/narration direction: fast Hindi narration" in directed


def test_dry_run_writes_plan_and_never_calls_provider(tmp_path):
    source = _tiny_mp4(tmp_path / "source.mp4")
    plan = create_plan(
        RemixRequest(source=str(source), prompt="use toy-like characters", max_total_seconds=1),
        runs_dir=tmp_path / "runs",
    )

    saved = load_plan(plan.run_id, tmp_path / "runs")
    assert saved.status == "planned"
    assert saved.user_prompt == "use toy-like characters"
    assert saved.source_platform == "local"
    assert saved.source_title == "source.mp4"
    assert saved.quality == "local"
    assert saved.audio_mode == "source"
    assert saved.original_duration > 0
    assert saved.aspect_ratio == "9:16"
    assert saved.block_count == 1
    assert Path(saved.blocks[0].ref_video).exists()
    assert Path(saved.blocks[0].keyframe).exists()
    assert saved.blocks[0].estimated_cost == 0
    assert "use toy-like characters" in saved.blocks[0].prompt
    assert not Path(saved.blocks[0].generated_path).exists()


def test_plan_requires_source(tmp_path):
    with pytest.raises(ValueError, match="Enter a YouTube"):
        create_plan(RemixRequest(source="  "), runs_dir=tmp_path / "runs")


def test_plan_missing_local_file_has_actionable_error(tmp_path):
    missing = tmp_path / "missing.mp4"
    with pytest.raises(FileNotFoundError, match="Source file not found"):
        create_plan(RemixRequest(source=str(missing)), runs_dir=tmp_path / "runs")


def test_live_requires_max_cost_and_enforces_estimate_before_provider(tmp_path):
    source = _tiny_mp4(tmp_path / "source.mp4")
    plan = create_plan(
        RemixRequest(source=str(source), quality="standard", max_total_seconds=1),
        runs_dir=tmp_path / "runs",
    )

    with pytest.raises(ValueError, match="max_cost is required"):
        run_live(plan.run_id, None, provider=FailingProvider(), runs_dir=tmp_path / "runs")

    with pytest.raises(ValueError, match="greater than 0"):
        run_live(plan.run_id, 0.0, provider=FailingProvider(), runs_dir=tmp_path / "runs")

    with pytest.raises(ValueError, match="exceeds max cost"):
        run_live(plan.run_id, 0.01, provider=FailingProvider(), runs_dir=tmp_path / "runs")


def test_local_live_requires_wan_command_without_gpu_probe(tmp_path):
    source = _tiny_mp4(tmp_path / "source.mp4")
    plan = create_plan(
        RemixRequest(source=str(source), quality="local", max_total_seconds=1),
        runs_dir=tmp_path / "runs",
    )

    with pytest.raises(RuntimeError, match="Local quality requires a Wan command"):
        run_live(plan.run_id, 1.0, runs_dir=tmp_path / "runs")
    failed = load_plan(plan.run_id, tmp_path / "runs")
    assert failed.status == "failed"
    assert failed.error is not None
    assert "Wan command" in failed.error


def test_tts_audio_mode_requires_script_and_sets_audio_path(tmp_path, monkeypatch):
    source = _tiny_mp4(tmp_path / "source.mp4")

    with pytest.raises(RuntimeError, match="TTS audio requires"):
        create_plan(
            RemixRequest(source=str(source), audio_mode="tts", max_total_seconds=1),
            runs_dir=tmp_path / "runs-missing-script",
        )

    def fake_synthesize(script: str, voice: str | None, out_path: str) -> str:
        Path(out_path).write_bytes(b"fake audio")
        assert script == "Narrate this in Hindi."
        assert voice == "hi-IN-SwaraNeural"
        return out_path

    monkeypatch.setattr("app.services.tts.synthesize", fake_synthesize)
    plan = create_plan(
        RemixRequest(
            source=str(source),
            audio_mode="tts",
            video_script_prompt="Narrate this in Hindi.",
            language="hi",
            tts_voice="hi-IN-SwaraNeural",
            max_total_seconds=1,
        ),
        runs_dir=tmp_path / "runs",
    )

    assert plan.audio_mode == "tts"
    assert plan.language == "hi"
    assert plan.video_script_prompt == "Narrate this in Hindi."
    assert plan.tts_voice == "hi-IN-SwaraNeural"
    assert plan.audio_path is not None
    assert Path(plan.audio_path).exists()


def test_mocked_live_run_stitches_playable_final_and_resume_skips(tmp_path):
    source = _tiny_mp4(tmp_path / "source.mp4")
    plan = create_plan(RemixRequest(source=str(source), max_total_seconds=1), runs_dir=tmp_path / "runs")

    provider = CopyProvider()
    finished = run_live(plan.run_id, 10.0, provider=provider, runs_dir=tmp_path / "runs")
    assert provider.calls == [0]
    assert finished.status == "done"
    assert finished.final_path is not None
    assert Path(finished.final_path).exists()

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            finished.final_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert float(probe.stdout.strip()) > 0

    provider_again = CopyProvider()
    resumed = run_live(plan.run_id, 10.0, provider=provider_again, runs_dir=tmp_path / "runs")
    assert provider_again.calls == []
    assert resumed.blocks[0].status == "skipped"


def test_captions_are_opt_in_and_write_caption_artifact(tmp_path, monkeypatch):
    source = _tiny_mp4(tmp_path / "source.mp4")
    plan = create_plan(
        RemixRequest(source=str(source), captions=True, max_total_seconds=1),
        runs_dir=tmp_path / "runs",
    )

    def fake_captions(saved_plan):
        path = Path(saved_plan.run_dir) / "captions.ass"
        path.write_text("[Script Info]\n", encoding="utf-8")
        return str(path)

    monkeypatch.setattr(remix_runner, "_make_captions", fake_captions)
    monkeypatch.setattr(remix_runner, "_has_subtitles_filter", lambda: False)

    finished = run_live(plan.run_id, 10.0, provider=CopyProvider(), runs_dir=tmp_path / "runs")
    assert finished.captions is True
    assert finished.captions_path is not None
    assert Path(finished.captions_path).exists()
    assert finished.final_path is not None
    assert Path(finished.final_path).exists()


def test_api_plan_start_status_and_final_download(tmp_path, monkeypatch):
    source = _tiny_mp4(tmp_path / "source.mp4")
    runs_dir = tmp_path / "runs"

    monkeypatch.setattr(
        server,
        "create_plan",
        lambda request: create_plan(request, runs_dir=runs_dir),
    )
    monkeypatch.setattr(server, "load_plan", lambda run_id: load_plan(run_id, runs_dir))
    monkeypatch.setattr(server, "list_runs", lambda: list_runs(runs_dir))
    monkeypatch.setattr(
        server,
        "run_live",
        lambda run_id, max_cost: run_live(
            run_id,
            max_cost,
            provider=CopyProvider(),
            runs_dir=runs_dir,
        ),
    )

    client = TestClient(server.app)
    planned = client.post(
        "/api/runs/plan",
        json={"source": str(source), "quality": "standard", "max_total_seconds": 1},
    )
    assert planned.status_code == 200
    run_id = planned.json()["run_id"]

    started = client.post(f"/api/runs/{run_id}/start", json={"max_cost": 10})
    assert started.status_code == 200

    for _ in range(20):
        status = client.get(f"/api/runs/{run_id}").json()
        if status["status"] == "done":
            break
        time.sleep(0.1)
    assert status["status"] == "done"

    final = client.get(f"/api/runs/{run_id}/final.mp4")
    assert final.status_code == 200
    assert final.headers["content-type"].startswith("video/mp4")
