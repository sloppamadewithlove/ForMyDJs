"""Regression tests for the 'no auto-folder' behavior.

ForMyDJ used to silently fall back to ~/Downloads/ForMyDJ when no output_dir
was sent. That created surprise folders for users and undermined the rule that
the user picks where their music lands. These tests pin the corrected behavior:

  - The API rejects job submissions and uploads with no output_dir.
  - The /api/jobs GET response returns default_output: None (UI must prompt).
  - server.main() does not create ~/Downloads/ForMyDJ on launch.
"""

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from app import server


class _FakeHeaders(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def _make_handler(body: bytes, *, content_type: str = "application/json"):
    """Build a minimal Handler instance suitable for direct method calls."""
    handler = server.Handler.__new__(server.Handler)
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()
    handler.headers = _FakeHeaders({
        "Content-Length": str(len(body)),
        "Content-Type": content_type,
    })
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.responses = []

    def _capture(payload, status=200):
        handler.responses.append((status, payload))

    handler.send_json = _capture
    return handler


class TestJobsRejectsEmptyOutputDir:
    def test_post_jobs_without_output_dir_returns_400(self):
        body = json.dumps({"link": "https://example.com/track", "format": "mp3"}).encode()
        handler = _make_handler(body)
        handler.path = "/api/jobs"

        handler.do_POST()

        assert handler.responses, "Handler did not send a response"
        status, payload = handler.responses[-1]
        assert status == 400
        assert "output folder" in payload["error"].lower()

    def test_post_jobs_with_blank_output_dir_returns_400(self):
        body = json.dumps({
            "link": "https://example.com/track",
            "format": "mp3",
            "output_dir": "   ",
        }).encode()
        handler = _make_handler(body)
        handler.path = "/api/jobs"

        handler.do_POST()

        status, payload = handler.responses[-1]
        assert status == 400
        assert "output folder" in payload["error"].lower()

    def test_post_jobs_still_rejects_missing_link_first(self):
        body = json.dumps({"format": "mp3", "output_dir": "/tmp/elsewhere"}).encode()
        handler = _make_handler(body)
        handler.path = "/api/jobs"

        handler.do_POST()

        status, payload = handler.responses[-1]
        assert status == 400
        assert "link" in payload["error"].lower()


class TestJobsListSignalsNoDefault:
    def test_get_jobs_returns_null_default_output(self):
        handler = server.Handler.__new__(server.Handler)
        handler.path = "/api/jobs"
        handler.responses = []

        def _capture(payload, status=200):
            handler.responses.append((status, payload))

        handler.send_json = _capture
        with patch("app.server.public_jobs", return_value=[]):
            handler.do_GET()

        status, payload = handler.responses[-1]
        assert status == 200
        assert payload["default_output"] is None, (
            "Server must NOT suggest a default folder; UI must prompt the user."
        )

    def test_get_jobs_returns_configured_default_output(self, monkeypatch):
        monkeypatch.setenv("FORMYDJ_OUTPUT_DIR", "/downloads")
        handler = server.Handler.__new__(server.Handler)
        handler.path = "/api/jobs"
        handler.responses = []

        def _capture(payload, status=200):
            handler.responses.append((status, payload))

        handler.send_json = _capture
        with patch("app.server.public_jobs", return_value=[]):
            handler.do_GET()

        status, payload = handler.responses[-1]
        assert status == 200
        assert payload["default_output"] == "/downloads"


class TestMainDoesNotAutoCreateFolder:
    def test_default_output_not_created_at_startup(self, tmp_path, monkeypatch):
        """The bug we're guarding against: ~/Downloads/ForMyDJ used to be
        unconditionally mkdir'd at launch. We replace DEFAULT_OUTPUT with a
        path under tmp_path, then stop main() before it serves, and assert
        the path was never created.
        """
        sentinel = tmp_path / "should-not-exist"
        monkeypatch.setattr(server, "DEFAULT_OUTPUT", sentinel)

        # Stub serve_forever so main() exits immediately after setup.
        class _StubServer:
            def __init__(self, *_a, **_kw): pass
            def serve_forever(self): pass

        monkeypatch.setattr(server, "ThreadingHTTPServer", _StubServer)
        monkeypatch.setattr(server, "webbrowser", MagicMock())
        monkeypatch.setattr(server.threading, "Timer", lambda *a, **kw: MagicMock())

        server.main()

        assert not sentinel.exists(), (
            "DEFAULT_OUTPUT must not be created at server startup — the user picks."
        )
