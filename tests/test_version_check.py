"""Tests for VERSION, version_is_newer, and check_for_update.

These pin the update-check contract so a future refactor can't silently
break the in-app banner or `formydj check-update` CLI command.
"""

from unittest.mock import patch

import pytest

from app.server import (
    VERSION,
    _parse_version,
    check_for_update,
    version_is_newer,
)


class TestParseVersion:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("0.2.0", (0, 2, 0)),
            ("v0.2.0", (0, 2, 0)),
            ("V1.10.3", (1, 10, 3)),
            ("1.0", (1, 0, 0)),
            ("2", (2, 0, 0)),
            ("0.2.0-beta", (0, 2, 0)),
            ("0.2.0+build.7", (0, 2, 0)),
            ("v1.2.3-rc.1", (1, 2, 3)),
            ("", (0, 0, 0)),
            (None, (0, 0, 0)),
            ("garbage", (0, 0, 0)),
        ],
    )
    def test_parses(self, value, expected):
        assert _parse_version(value) == expected


class TestVersionIsNewer:
    def test_strictly_newer_patch(self):
        assert version_is_newer("0.2.1", "0.2.0") is True

    def test_strictly_newer_minor(self):
        assert version_is_newer("0.3.0", "0.2.9") is True

    def test_strictly_newer_major(self):
        assert version_is_newer("1.0.0", "0.99.99") is True

    def test_same_version_is_not_newer(self):
        assert version_is_newer("0.2.0", "0.2.0") is False

    def test_older_is_not_newer(self):
        assert version_is_newer("0.1.9", "0.2.0") is False

    def test_v_prefix_does_not_affect_comparison(self):
        assert version_is_newer("v0.2.1", "0.2.0") is True
        assert version_is_newer("0.2.0", "v0.2.0") is False

    def test_prerelease_suffix_ignored(self):
        # We intentionally treat "0.2.0-beta" as equivalent to "0.2.0" for the
        # update check. Releases are tagged without prerelease suffix; if a
        # prerelease IS published, we'd rather not nag users to install it.
        assert version_is_newer("0.2.0-beta", "0.2.0") is False


class TestCheckForUpdate:
    def test_network_failure_returns_payload_with_error(self, tmp_path, monkeypatch):
        from app import server

        monkeypatch.setattr(server, "UPDATE_CACHE", tmp_path / "no-cache.json")

        def fail(*_args, **_kwargs):
            raise OSError("no network")

        with patch("app.server.urllib.request.urlopen", side_effect=fail):
            result = check_for_update(force=True)

        assert result["current"] == VERSION
        assert result["update_available"] is False
        assert "error" in result

    def test_cache_round_trip(self, tmp_path, monkeypatch):
        from app import server

        monkeypatch.setattr(server, "UPDATE_CACHE", tmp_path / "cache.json")
        # First, force a network call that will fail; that still writes a cache.
        with patch("app.server.urllib.request.urlopen", side_effect=OSError("boom")):
            first = check_for_update(force=True)
        # Now call without force; we should read from cache, not re-hit network.
        with patch("app.server.urllib.request.urlopen") as mocked:
            second = check_for_update(force=False)
            mocked.assert_not_called()

        assert second["current"] == first["current"]
        assert second["source"] == "cache"

    def test_version_constant_is_set(self):
        assert isinstance(VERSION, str)
        assert _parse_version(VERSION) > (0, 0, 0)
