from pathlib import Path

from app import server


def test_ytdlp_ffmpeg_args_points_at_resolved_ffmpeg_dir():
    assert server.ytdlp_ffmpeg_args() == [
        "--ffmpeg-location",
        str(Path(server.FFMPEG).parent),
    ]


def test_download_source_passes_ffmpeg_location(monkeypatch, tmp_path):
    commands = []

    def fake_run(cmd):
        commands.append(cmd)
        (tmp_path / "source.m4a").write_bytes(b"audio")
        (tmp_path / "source.info.json").write_text("{}")
        return None

    monkeypatch.setattr(server, "run", fake_run)

    audio_path, info_path, thumbnail_path = server.download_source("https://example.com/track", tmp_path)

    assert audio_path == tmp_path / "source.m4a"
    assert info_path == tmp_path / "source.info.json"
    assert thumbnail_path is None
    assert "--ffmpeg-location" in commands[0]
    assert str(Path(server.FFMPEG).parent) in commands[0]
