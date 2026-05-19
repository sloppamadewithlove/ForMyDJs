import json
import subprocess

import pytest

from app.server import FFMPEG, FFPROBE, convert_audio


@pytest.fixture
def workspace(tmp_path):
    src = tmp_path / "source.wav"
    subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
         "-ac", "2", "-ar", "44100", str(src)],
        check=True,
    )
    cover = tmp_path / "cover.jpg"
    subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", "color=red:size=64x64:duration=0.04",
         "-frames:v", "1", str(cover)],
        check=True,
    )
    out = tmp_path / "out"
    out.mkdir()
    return src, cover, out


def video_streams(audio_path):
    result = subprocess.run(
        [FFPROBE, "-v", "error", "-print_format", "json", "-show_streams", str(audio_path)],
        check=True, text=True, stdout=subprocess.PIPE,
    )
    streams = json.loads(result.stdout).get("streams", [])
    return [s for s in streams if s.get("codec_type") == "video"]


def test_mp3_embeds_cover_when_thumbnail_present(workspace):
    src, cover, out = workspace
    metadata = {"title": "Test", "artist": "Tester"}
    output = convert_audio(src, metadata, out, "mp3", thumbnail_path=cover)
    assert output.exists()
    assert output.suffix == ".mp3"
    streams = video_streams(output)
    assert len(streams) == 1, f"Expected 1 attached image stream, got {len(streams)}"


def test_mp3_no_cover_when_thumbnail_missing(workspace):
    src, _, out = workspace
    metadata = {"title": "Test", "artist": "Tester"}
    output = convert_audio(src, metadata, out, "mp3", thumbnail_path=None)
    assert output.exists()
    assert video_streams(output) == []


def test_aiff_embeds_cover_when_thumbnail_present(workspace):
    src, cover, out = workspace
    metadata = {"title": "Test", "artist": "Tester"}
    output = convert_audio(src, metadata, out, "aiff", thumbnail_path=cover)
    assert output.exists()
    assert output.suffix == ".aiff"
    streams = video_streams(output)
    assert len(streams) == 1, f"Expected 1 attached image stream, got {len(streams)}"


def test_wav_never_embeds_cover(workspace):
    src, cover, out = workspace
    metadata = {"title": "Test", "artist": "Tester"}
    output = convert_audio(src, metadata, out, "wav", thumbnail_path=cover)
    assert output.exists()
    assert output.suffix == ".wav"
    assert video_streams(output) == []


from app.server import copy_original


def test_copy_original_preserves_audio_codec(workspace):
    src, cover, out = workspace
    # Source is WAV (PCM s16le) — copy will preserve it.
    metadata = {"title": "Test", "artist": "Tester"}
    output = copy_original(src, metadata, out, thumbnail_path=cover)
    assert output.exists()
    assert output.suffix == ".wav"
    # WAV doesn't support attached_pic — no video stream expected.
    assert video_streams(output) == []


def test_copy_original_opus_embeds_cover(workspace):
    src, cover, out = workspace
    # Re-encode the synthetic WAV to opus first so we have an attached_pic-capable container.
    opus_src = src.with_suffix(".opus")
    subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(src), "-c:a", "libopus", "-b:a", "128k", str(opus_src)],
        check=True,
    )
    metadata = {"title": "Test", "artist": "Tester"}
    output = copy_original(opus_src, metadata, out, thumbnail_path=cover)
    assert output.exists()
    assert output.suffix == ".opus"
    streams = video_streams(output)
    assert len(streams) == 1, f"Expected 1 attached image stream, got {len(streams)}"


def test_copy_original_no_thumbnail_audio_only(workspace):
    src, _, out = workspace
    metadata = {"title": "Test", "artist": "Tester"}
    output = copy_original(src, metadata, out, thumbnail_path=None)
    assert output.exists()
    assert video_streams(output) == []
