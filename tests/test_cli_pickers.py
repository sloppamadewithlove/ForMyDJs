"""Tests for the CLI's smart-format pickers and argument resolution.

The CLI re-implements small picker functions that mirror the UI-side logic in
app/static/app.js. These tests pin the codec-to-format and extension-to-format
mappings so a future change can't silently route MP3 sources through a WAV
re-encode (the bug the smart-flip feature exists to prevent).
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.cli import (
    VALID_FORMATS,
    _autopick_file,
    _autopick_url,
    _resolve_format,
    build_parser,
)


class TestAutopickFile:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("track.mp3", "mp3"),
            ("track.MP3", "mp3"),
            ("track.wav", "wav"),
            ("track.wave", "wav"),
            ("track.aiff", "aiff"),
            ("track.aif", "aiff"),
            ("track.aifc", "aiff"),
            ("track.flac", "aiff"),
            ("track.alac", "aiff"),
            ("track.m4a", "aiff"),
            ("track.opus", "mp3"),
            ("track.aac", "mp3"),
            ("track", "mp3"),
            ("track.unknown", "mp3"),
        ],
    )
    def test_picks_expected_format(self, name, expected):
        assert _autopick_file(Path(name)) == expected


class TestAutopickUrl:
    def test_mp3_codec_picks_mp3(self):
        with patch("app.cli.server.probe_url", return_value={"codec": "mp3"}):
            assert _autopick_url("https://example.com/x") == "mp3"

    def test_pcm_le_picks_wav(self):
        with patch("app.cli.server.probe_url", return_value={"codec": "pcm_s16le"}):
            assert _autopick_url("https://example.com/x") == "wav"

    def test_pcm_be_picks_aiff(self):
        with patch("app.cli.server.probe_url", return_value={"codec": "pcm_s24be"}):
            assert _autopick_url("https://example.com/x") == "aiff"

    def test_flac_picks_aiff(self):
        with patch("app.cli.server.probe_url", return_value={"codec": "flac"}):
            assert _autopick_url("https://example.com/x") == "aiff"

    def test_opus_picks_mp3(self):
        with patch("app.cli.server.probe_url", return_value={"codec": "opus"}):
            assert _autopick_url("https://example.com/x") == "mp3"

    def test_probe_failure_defaults_to_mp3(self):
        with patch("app.cli.server.probe_url", side_effect=RuntimeError("offline")):
            assert _autopick_url("https://example.com/x") == "mp3"

    def test_missing_codec_defaults_to_mp3(self):
        with patch("app.cli.server.probe_url", return_value={}):
            assert _autopick_url("https://example.com/x") == "mp3"


class TestResolveFormat:
    def test_explicit_format_passthrough(self):
        assert _resolve_format("mp3", kind="url", value="x") == "mp3"

    def test_explicit_format_case_insensitive(self):
        assert _resolve_format("AIFF", kind="url", value="x") == "aiff"

    def test_invalid_format_raises(self):
        with pytest.raises(SystemExit):
            _resolve_format("ogg", kind="url", value="x")

    def test_auto_uses_url_picker(self):
        with patch("app.cli._autopick_url", return_value="wav") as mock_pick:
            result = _resolve_format("auto", kind="url", value="https://x")
        mock_pick.assert_called_once_with("https://x")
        assert result == "wav"

    def test_auto_uses_file_picker(self):
        result = _resolve_format("auto", kind="file", value=Path("track.mp3"))
        assert result == "mp3"

    def test_valid_formats_set(self):
        assert VALID_FORMATS == {"mp3", "wav", "aiff"}


class TestParser:
    def test_parses_url_command(self):
        parser = build_parser()
        args = parser.parse_args(["url", "https://example.com/x", "--format", "mp3"])
        assert args.command == "url"
        assert args.url == "https://example.com/x"
        assert args.format == "mp3"

    def test_parses_file_command(self):
        parser = build_parser()
        args = parser.parse_args(["file", "/tmp/track.wav", "--output", "/tmp/out"])
        assert args.command == "file"
        assert args.path == "/tmp/track.wav"
        assert args.output == "/tmp/out"

    def test_parses_check_update(self):
        parser = build_parser()
        args = parser.parse_args(["check-update", "--force", "--json"])
        assert args.command == "check-update"
        assert args.force is True
        assert args.json is True

    def test_missing_subcommand_raises(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])
