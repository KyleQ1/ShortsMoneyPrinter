"""Light unit tests for pure logic (no network, no heavy models, no ffmpeg)."""

from app.models import AspectRatio
from app.services import captions, render, video_conditioning as vc


def test_aspect_dimensions():
    assert AspectRatio.VERTICAL.dimensions == (1080, 1920)
    assert AspectRatio.HORIZONTAL.dimensions == (1920, 1080)
    assert AspectRatio.VERTICAL.pexels_orientation == "portrait"


def test_ass_timestamp():
    assert captions._ts(0) == "0:00:00.00"
    assert captions._ts(65.5) == "0:01:05.50"


def test_build_ass_emits_dialogue():
    words = [(0.0, 0.4, "hello"), (0.4, 0.9, "there"), (0.9, 1.5, "world"), (1.5, 2.0, "again")]
    ass = captions._build_ass(words, 1080, 1920)
    assert "[V4+ Styles]" in ass
    assert ass.count("Dialogue:") == 2  # 4 words / 3-per-cue → 2 cues
    assert "PlayResX: 1080" in ass


def test_subtitles_path_escaping():
    assert render._escape_path("/a/b/captions.ass") == "/a/b/captions.ass"
    assert render._escape_path("C:/x/captions.ass") == "C\\:/x/captions.ass"


def test_seedance_target_dims_within_limits():
    # Any aspect must land within Seedance's pixel ceiling, with even dims.
    for iw, ih in [(1920, 1080), (1080, 1920), (1080, 1080), (2520, 1080), (3840, 2160)]:
        w, h = vc.target_dims(iw, ih)
        assert w % 2 == 0 and h % 2 == 0
        assert w * h <= vc.MAX_PIXELS
        assert min(w, h) >= 2
    assert vc.target_dims(1920, 1080) == (1280, 720)
    assert vc.target_dims(1080, 1920) == (720, 1280)
