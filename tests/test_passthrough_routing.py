"""Tests for can_passthrough + normalize_suffix routing logic.

Smart-flip on the UI side picks an output format from {wav, aiff, mp3} based on
source codec. When the source file already matches that format, process_job
routes to copy_original (bit-exact remux) instead of convert_audio (re-encode).
These tests pin the routing decision so a future refactor can't silently
re-encode MP3-to-MP3 or WAV-to-WAV.
"""

from pathlib import Path

import pytest

from app.server import can_passthrough, normalize_suffix


class TestNormalizeSuffix:
    def test_lowercases(self):
        assert normalize_suffix("WAV") == "wav"

    def test_wave_alias_collapses_to_wav(self):
        assert normalize_suffix("wave") == "wav"

    def test_aif_alias_collapses_to_aiff(self):
        assert normalize_suffix("aif") == "aiff"

    def test_aifc_alias_collapses_to_aiff(self):
        assert normalize_suffix("aifc") == "aiff"

    def test_mp3_passthrough(self):
        assert normalize_suffix("mp3") == "mp3"

    def test_empty(self):
        assert normalize_suffix("") == ""


class TestCanPassthrough:
    @pytest.mark.parametrize(
        "source_name,output_format",
        [
            ("track.mp3", "mp3"),
            ("track.MP3", "mp3"),
            ("track.wav", "wav"),
            ("track.WAV", "wav"),
            ("track.wave", "wav"),
            ("track.aiff", "aiff"),
            ("track.aif", "aiff"),
            ("track.aifc", "aiff"),
        ],
    )
    def test_matching_extension_passes_through(self, source_name, output_format):
        assert can_passthrough(Path(source_name), output_format) is True

    @pytest.mark.parametrize(
        "source_name,output_format",
        [
            ("track.mp3", "wav"),
            ("track.mp3", "aiff"),
            ("track.wav", "mp3"),
            ("track.wav", "aiff"),
            ("track.aiff", "wav"),
            ("track.aiff", "mp3"),
            ("track.flac", "wav"),
            ("track.flac", "aiff"),
            ("track.opus", "mp3"),
            ("track.m4a", "mp3"),
        ],
    )
    def test_mismatched_format_requires_convert(self, source_name, output_format):
        assert can_passthrough(Path(source_name), output_format) is False

    def test_no_extension_does_not_passthrough(self):
        assert can_passthrough(Path("track"), "mp3") is False

    def test_empty_output_format_is_safe(self):
        assert can_passthrough(Path("track.mp3"), "") is False

    def test_original_pseudo_format_does_not_short_circuit(self):
        # The process_job branch handles "original" explicitly before calling
        # can_passthrough, so can_passthrough itself should not say yes here.
        assert can_passthrough(Path("track.mp3"), "original") is False
