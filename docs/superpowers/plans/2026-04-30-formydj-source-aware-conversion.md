# ForMyDJ Source-Aware Conversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Probe pasted URLs to show codec/cover/title before download, auto-flip the format dropdown to MP3 320 for lossy sources, embed cover art into MP3/AIFF/Original outputs, and add an "Original" remux option.

**Architecture:** Backend gains a `GET /api/probe` endpoint (yt-dlp -j wrapper) and a refactored conversion pipeline that threads cover-art paths from `download_source` into `convert_audio` (and a new `copy_original`). Frontend adds a debounced probe, a "source card" UI element above the controls, and a silent smart-flip of the format dropdown.

**Tech Stack:** Python 3 stdlib HTTP server, vanilla JS, ffmpeg, yt-dlp, pytest (newly introduced for backend logic).

**Branch context:** This plan extends `feat/ui-redesign-iron-neon` (17 commits, UI redesign already in place). Continue on the same branch — the source card uses the redesign's palette and row card aesthetic, and a single PR can ship redesign + this feature together.

---

## File Structure

| File | Responsibility | Touch |
|------|----------------|-------|
| `app/__init__.py` | Make `app` an importable package for tests | Create (empty) |
| `app/server.py` | Backend logic, all changes | Modify (~80 lines added/changed) |
| `app/static/index.html` | Source card markup, Original option, AIFF default | Modify (~15 lines) |
| `app/static/styles.css` | Source card styles | Modify (~50 lines added) |
| `app/static/app.js` | Probe pipeline, source card population, smart-flip, format default | Modify (~70 lines added) |
| `pytest.ini` | pytest config (pythonpath, testpaths) | Create |
| `tests/__init__.py` | Empty marker | Create |
| `tests/test_codec_classification.py` | Unit tests for `LOSSY_CODECS` | Create |
| `tests/test_probe_response.py` | Unit tests for `build_probe_response` parser | Create |
| `tests/test_cover_embedding.py` | Integration tests for `convert_audio` and `copy_original` cover art | Create |

Frontend changes (HTML/CSS/JS) are verified via the manual smoke test in Task 11; a JS test harness would be disproportionate for a vanilla-JS file with three new functions.

---

## Task 0: Confirm working tree before starting

**Files:** none

- [ ] **Step 1: Verify working branch and clean state**

```bash
cd /Users/slava/Downloads/vibework/ForMyDJ
git status
git branch --show-current
```

Expected: branch is `feat/ui-redesign-iron-neon`. The only untracked file should be `docs/superpowers/specs/2026-04-30-formydj-source-aware-conversion-design.md`. README.md may have a small unrelated diff — leave it alone.

If the branch is something else, stop and ask the user how to proceed. The source card depends on the Iron & Neon palette (`--p-warning`, `--p-success`, `--p-surface`, etc.) which only exists on this branch.

- [ ] **Step 2: Verify dependencies are present**

```bash
which yt-dlp ffmpeg ffprobe
yt-dlp --version
ffmpeg -version | head -1
```

Expected: all three resolve to `/opt/homebrew/bin/...` (or `/usr/local/bin/...`). If any are missing, install via `brew install yt-dlp ffmpeg`.

- [ ] **Step 3: Verify pytest is installable**

```bash
python3 -m pip show pytest >/dev/null 2>&1 || python3 -m pip install --user pytest
python3 -m pytest --version
```

Expected: `pytest 7.x` or newer.

---

## Task 1: pytest scaffolding + extract `LOSSY_CODECS` to module level

**Files:**
- Create: `app/__init__.py`
- Create: `pytest.ini`
- Create: `tests/__init__.py`
- Create: `tests/test_codec_classification.py`
- Modify: `app/server.py:117-145` (move `lossy_codecs` set out of function body)

- [ ] **Step 1: Create empty package marker for `app`**

```bash
touch app/__init__.py
```

- [ ] **Step 2: Create empty marker for `tests`**

```bash
mkdir -p tests
touch tests/__init__.py
```

- [ ] **Step 3: Create `pytest.ini`**

Write `pytest.ini` at project root:

```ini
[pytest]
pythonpath = .
testpaths = tests
addopts = -v
```

- [ ] **Step 4: Write the failing test**

Write `tests/test_codec_classification.py`:

```python
from app.server import LOSSY_CODECS


def test_lossy_codecs_is_frozenset():
    assert isinstance(LOSSY_CODECS, frozenset)


def test_lossy_codecs_contents():
    assert LOSSY_CODECS == frozenset({"mp3", "aac", "opus", "vorbis", "m4a"})


def test_mp3_is_lossy():
    assert "mp3" in LOSSY_CODECS


def test_flac_is_not_lossy():
    assert "flac" not in LOSSY_CODECS


def test_wav_is_not_lossy():
    assert "wav" not in LOSSY_CODECS
```

- [ ] **Step 5: Run test to verify it fails**

```bash
python3 -m pytest tests/test_codec_classification.py
```

Expected: ImportError — `cannot import name 'LOSSY_CODECS' from 'app.server'`.

- [ ] **Step 6: Add `LOSSY_CODECS` constant to `app/server.py`**

In `app/server.py`, locate the existing `metadata_from_info` function (around line 117). Above it (at module level, just after the `tool()` definitions and `FFMPEG/FFPROBE/YTDLP/GZIP` declarations near line 51), add:

```python
LOSSY_CODECS = frozenset({"mp3", "aac", "opus", "vorbis", "m4a"})
```

Then in `metadata_from_info` (currently lines 117-145), replace the local `lossy_codecs = {"mp3", "aac", "opus", "vorbis", "m4a"}` declaration with a reference to the module constant. The relevant lines (124-125 in the current file) become:

```python
    codec = (probe.get("codec") or "").lower()
    # (no local lossy_codecs assignment — uses module-level LOSSY_CODECS)
```

And the line that uses it (line 144 currently) becomes:

```python
        "is_lossy": codec in LOSSY_CODECS,
```

- [ ] **Step 7: Run test to verify it passes**

```bash
python3 -m pytest tests/test_codec_classification.py
```

Expected: 5 passed.

- [ ] **Step 8: Verify the existing app still runs**

```bash
python3 -c "from app.server import metadata_from_info, LOSSY_CODECS; print(LOSSY_CODECS)"
```

Expected: `frozenset({'mp3', 'aac', 'opus', 'vorbis', 'm4a'})` (order may vary).

- [ ] **Step 9: Commit**

```bash
git add app/__init__.py pytest.ini tests/__init__.py tests/test_codec_classification.py app/server.py
git commit -m "test: add pytest scaffolding and extract LOSSY_CODECS constant"
```

---

## Task 2: `build_probe_response` pure parser function

**Files:**
- Modify: `app/server.py` (add new function after `LOSSY_CODECS` constant)
- Create: `tests/test_probe_response.py`

The probe endpoint will run `yt-dlp -j` and parse a JSON dict. The parsing logic is pure and easy to test in isolation; the subprocess wrapper comes in Task 3.

- [ ] **Step 1: Write the failing tests**

Write `tests/test_probe_response.py`:

```python
from app.server import build_probe_response


def test_lossy_opus_source():
    info = {
        "title": "Hold On Tight",
        "artist": "Hidde van Wee",
        "duration": 287.4,
        "acodec": "opus",
        "abr": 128.0,
        "thumbnail": "https://example.com/cover.jpg",
        "ext": "opus",
    }
    result = build_probe_response(info)
    assert result["title"] == "Hold On Tight"
    assert result["artist"] == "Hidde van Wee"
    assert result["duration"] == 287.4
    assert result["codec"] == "opus"
    assert result["bitrate"] == 128000
    assert result["thumbnail"] == "https://example.com/cover.jpg"
    assert result["ext"] == "opus"
    assert result["lossy"] is True


def test_lossless_flac_source():
    info = {
        "title": "Symphony No. 9",
        "uploader": "Berlin Philharmonic",
        "duration": 4200.0,
        "acodec": "flac",
        "abr": 1411.0,
        "thumbnail": "https://example.com/symphony.jpg",
        "ext": "flac",
    }
    result = build_probe_response(info)
    assert result["codec"] == "flac"
    assert result["bitrate"] == 1411000
    assert result["lossy"] is False
    assert result["artist"] == "Berlin Philharmonic"


def test_uploader_falls_back_to_artist():
    info = {"title": "X", "uploader": "Some Channel", "acodec": "mp3", "abr": 320}
    result = build_probe_response(info)
    assert result["artist"] == "Some Channel"


def test_creator_preferred_over_uploader():
    info = {"title": "X", "creator": "True Artist", "uploader": "Channel", "acodec": "mp3", "abr": 320}
    result = build_probe_response(info)
    assert result["artist"] == "True Artist"


def test_artist_field_preferred_when_present():
    info = {"title": "X", "artist": "Tagged Artist", "uploader": "Channel", "acodec": "mp3"}
    result = build_probe_response(info)
    assert result["artist"] == "Tagged Artist"


def test_missing_codec_defaults_to_lossy():
    info = {"title": "X", "uploader": "Y"}
    result = build_probe_response(info)
    assert result["codec"] is None
    assert result["lossy"] is True


def test_unknown_codec_defaults_to_lossy():
    info = {"title": "X", "uploader": "Y", "acodec": "unknownformat"}
    result = build_probe_response(info)
    assert result["codec"] == "unknownformat"
    assert result["lossy"] is True


def test_bitrate_missing_returns_none():
    info = {"title": "X", "uploader": "Y", "acodec": "flac"}
    result = build_probe_response(info)
    assert result["bitrate"] is None


def test_uppercase_codec_normalised():
    info = {"title": "X", "uploader": "Y", "acodec": "MP3", "abr": 320}
    result = build_probe_response(info)
    assert result["codec"] == "mp3"
    assert result["lossy"] is True


def test_thumbnail_falls_back_to_thumbnails_list():
    info = {
        "title": "X",
        "uploader": "Y",
        "acodec": "opus",
        "thumbnails": [
            {"url": "https://example.com/small.jpg", "width": 100},
            {"url": "https://example.com/large.jpg", "width": 1000},
        ],
    }
    result = build_probe_response(info)
    assert result["thumbnail"] == "https://example.com/large.jpg"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_probe_response.py
```

Expected: ImportError — `cannot import name 'build_probe_response' from 'app.server'`.

- [ ] **Step 3: Implement `build_probe_response` in `app/server.py`**

Add the following two definitions to `app/server.py` immediately after the `LOSSY_CODECS = frozenset(...)` line. `LOSSLESS_CODECS` is a positive-list of codecs we explicitly trust as lossless; everything else (including unknown) defaults to lossy.

```python
LOSSLESS_CODECS = frozenset({
    "flac", "alac", "wav",
    "pcm_s16le", "pcm_s16be", "pcm_s24le", "pcm_s24be", "pcm_f32le",
    "ape", "tta", "wv",
})


def _is_lossy_for_probe(codec):
    """Defensive lossy classifier for pre-download probes.

    Known lossless → False. Known lossy or unknown or missing → True (defensive,
    so we never silently upcode an unknown source to AIFF).
    """
    if not codec:
        return True
    return codec not in LOSSLESS_CODECS


def build_probe_response(info):
    """Convert a yt-dlp -j info dict into a probe API response."""
    raw_codec = info.get("acodec") or info.get("codec")
    codec = raw_codec.lower() if isinstance(raw_codec, str) and raw_codec else None

    raw_bitrate = info.get("abr") or info.get("tbr")
    bitrate = int(round(float(raw_bitrate) * 1000)) if raw_bitrate else None

    artist = info.get("artist") or info.get("creator") or info.get("uploader")

    thumbnail = info.get("thumbnail")
    if not thumbnail:
        candidates = info.get("thumbnails") or []
        if candidates:
            best = max(candidates, key=lambda item: item.get("width") or 0)
            thumbnail = best.get("url")

    duration = info.get("duration")
    if duration is not None:
        try:
            duration = float(duration)
        except (TypeError, ValueError):
            duration = None

    return {
        "title": info.get("title"),
        "artist": artist,
        "duration": duration,
        "codec": codec,
        "bitrate": bitrate,
        "thumbnail": thumbnail,
        "ext": info.get("ext"),
        "lossy": _is_lossy_for_probe(codec),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_probe_response.py
```

Expected: 10 passed.

- [ ] **Step 5: Re-run the codec-classification tests to confirm no regression**

```bash
python3 -m pytest
```

Expected: 15 passed (5 from Task 1 + 10 from Task 2).

- [ ] **Step 6: Commit**

```bash
git add tests/test_probe_response.py app/server.py
git commit -m "feat(probe): add build_probe_response parser with lossy/lossless heuristics"
```

---

## Task 3: `probe_url` subprocess wrapper + `/api/probe` endpoint

**Files:**
- Modify: `app/server.py` (add `probe_url`, add `/api/probe` branch in `Handler.do_GET`)

The endpoint runs `yt-dlp -j` with a 10-second timeout and returns the parsed dict. Failures (timeout, geo-block, private link) become HTTP 502 with the yt-dlp error in the body. This task is verified manually with `curl` rather than mocked, because mocking subprocess against yt-dlp's real CLI surface is fragile and the value of testing it is mostly that yt-dlp is invoked with the right arguments — which a manual test covers cheaply.

- [ ] **Step 1: Add `probe_url` function to `app/server.py`**

Add this function just below `build_probe_response` (created in Task 2):

```python
def probe_url(url):
    """Run `yt-dlp -j` against URL and return a probe response dict.

    Raises RuntimeError with the yt-dlp error message on any failure.
    """
    try:
        result = subprocess.run(
            [YTDLP, "-j", "--no-playlist", "--ignore-config", "--skip-download", url],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Probe timed out after 10 seconds")
    if result.returncode != 0:
        message = result.stderr.strip().splitlines()[-1] if result.stderr else "yt-dlp failed"
        raise RuntimeError(message)
    info = json.loads(result.stdout)
    return build_probe_response(info)
```

- [ ] **Step 2: Add `/api/probe` route to the GET handler**

In `app/server.py`, modify `Handler.do_GET` (currently lines 434-439). Replace it with:

```python
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/jobs":
            self.send_json({"jobs": public_jobs(), "default_output": str(DEFAULT_OUTPUT)})
            return
        if parsed.path == "/api/probe":
            params = parse_qs(parsed.query)
            url = (params.get("url") or [""])[0].strip()
            if not url:
                self.send_json({"error": "Missing url"}, 400)
                return
            try:
                self.send_json(probe_url(url))
            except Exception as exc:
                self.send_json({"error": str(exc)}, 502)
            return
        return super().do_GET()
```

- [ ] **Step 3: Restart the server and probe a real URL**

In a separate terminal:

```bash
python3 -m app.server
```

(Or however the user normally launches; `python3 app/server.py` is fine too. The server prints `ForMyDJ running at http://127.0.0.1:8765` and may open the browser — close that.)

- [ ] **Step 4: Manual test against a real SoundCloud URL**

```bash
curl -s 'http://127.0.0.1:8765/api/probe?url=https%3A%2F%2Fsoundcloud.com%2Fhiddevanwee%2Fhold-on-tight' | python3 -m json.tool
```

Expected: a JSON object with `title`, `artist`, `duration`, `codec`, `bitrate`, `thumbnail`, `ext`, `lossy` fields. Exact values vary, but `codec` should be `"opus"` and `lossy` should be `true` for this SoundCloud URL.

- [ ] **Step 5: Manual test the empty-URL error path**

```bash
curl -i -s 'http://127.0.0.1:8765/api/probe'
```

Expected: HTTP 400, body `{"error": "Missing url"}`.

- [ ] **Step 6: Manual test the bad-URL error path**

```bash
curl -i -s 'http://127.0.0.1:8765/api/probe?url=https%3A%2F%2Fexample.com%2Fnotreal'
```

Expected: HTTP 502, body containing an error message from yt-dlp.

- [ ] **Step 7: Stop the server and commit**

Stop the server (Ctrl-C), then:

```bash
git add app/server.py
git commit -m "feat(probe): add /api/probe endpoint with 10s timeout and 502 on failure"
```

---

## Task 4: Backend default format WAV → AIFF

**Files:**
- Modify: `app/server.py:447,460` (POST handlers fall back to `"aiff"` instead of `"wav"`)

This is mechanical but worth its own commit so the change is easy to revert if the user wants to change defaults later.

- [ ] **Step 1: Update `/api/jobs` POST default**

In `app/server.py`, locate line 447 (in `do_POST`, the `/api/jobs` branch):

```python
            output_format = (payload.get("format") or "wav").lower()
```

Change `"wav"` to `"aiff"`:

```python
            output_format = (payload.get("format") or "aiff").lower()
```

- [ ] **Step 2: Update `/api/upload` POST default**

In `app/server.py`, locate line 460 (in `do_POST`, the `/api/upload` branch):

```python
            output_format = (form.getfirst("format") or "wav").lower()
```

Change `"wav"` to `"aiff"`:

```python
            output_format = (form.getfirst("format") or "aiff").lower()
```

- [ ] **Step 3: Verify both call sites changed**

```bash
grep -n '"wav"' app/server.py | grep -v wav.lower
```

Expected: no lines printed (the only remaining `"wav"` references should be inside `convert_audio` for branching on output format and in `warnings_for`).

```bash
grep -n '"aiff"' app/server.py
```

Expected: at least four hits — the two new defaults plus the `warnings_for` set member and the `convert_audio` branch.

- [ ] **Step 4: Commit**

```bash
git add app/server.py
git commit -m "feat: default output format to AIFF instead of WAV (server fallback)"
```

---

## Task 5: `download_source` returns 3-tuple with thumbnail path

**Files:**
- Modify: `app/server.py:164-183` (refactor `download_source`)
- Modify: `app/server.py:316-371` (update `process_job` to receive thumbnail)

Currently `--write-thumbnail` downloads cover art into the workdir but it's never returned to the caller. We add `--convert-thumbnails jpg` so YouTube WebPs come out as universally-embeddable JPGs, then scan the workdir for the thumbnail and return it as a third tuple element.

- [ ] **Step 1: Replace `download_source`**

In `app/server.py`, replace the entire `download_source` function (currently lines 164-183) with:

```python
def download_source(url, workdir):
    output_template = str(workdir / "source.%(ext)s")
    run([
        YTDLP,
        "--no-playlist",
        "--ignore-config",
        "-f", "ba/best",
        "--write-info-json",
        "--write-thumbnail",
        "--convert-thumbnails", "jpg",
        "-o", output_template,
        url,
    ])
    audio_extensions_excluded = {"json", "jpg", "jpeg", "png", "webp", "part"}
    audio_candidates = [
        path for path in workdir.iterdir()
        if path.suffix.lower().lstrip(".") not in audio_extensions_excluded
    ]
    if not audio_candidates:
        raise RuntimeError("No downloadable audio file was produced.")
    info_path = next((path for path in workdir.iterdir() if path.name.endswith(".info.json")), None)
    thumbnail_extensions = {".jpg", ".jpeg", ".png"}
    thumbnail_path = next(
        (path for path in workdir.iterdir() if path.suffix.lower() in thumbnail_extensions),
        None,
    )
    return audio_candidates[0], info_path, thumbnail_path
```

- [ ] **Step 2: Update `process_job` call site to unpack three values**

In `app/server.py`, find the section in `process_job` (around lines 326-333) that looks like:

```python
        update_job(job_id, status="downloading", progress="Preparing source")
        if input_kind == "url":
            source_path, info_path = download_source(input_value, workdir)
            source_url = input_value
        else:
            source_path = Path(input_value)
            info_path = None
            source_url = None
```

Replace with:

```python
        update_job(job_id, status="downloading", progress="Preparing source")
        if input_kind == "url":
            source_path, info_path, thumbnail_path = download_source(input_value, workdir)
            source_url = input_value
        else:
            source_path = Path(input_value)
            info_path = None
            thumbnail_path = None
            source_url = None
```

(`thumbnail_path` will be wired into the convert call in Task 6 — it's defined here so the next task can use it without re-touching `process_job`'s download branch.)

- [ ] **Step 3: Smoke-test the change with a quick interactive run**

```bash
python3 -c "
import tempfile
from pathlib import Path
from app.server import download_source
with tempfile.TemporaryDirectory() as d:
    workdir = Path(d)
    audio, info, thumb = download_source('https://soundcloud.com/hiddevanwee/hold-on-tight', workdir)
    print('audio:', audio)
    print('info:', info)
    print('thumb:', thumb)
    print('exists:', thumb.exists() if thumb else None)
"
```

Expected: prints three paths (audio, info JSON, jpg thumbnail), and `exists: True` for the thumbnail. The audio file's extension will be `.opus` for SoundCloud.

- [ ] **Step 4: Commit**

```bash
git add app/server.py
git commit -m "feat(download): return thumbnail path from download_source as 3-tuple"
```

---

## Task 6: `convert_audio` embeds cover art per output format

**Files:**
- Modify: `app/server.py:186-217` (refactor `convert_audio`)
- Modify: `app/server.py:316-371` (thread `thumbnail_path` into `convert_audio` call)
- Create: `tests/test_cover_embedding.py`

The current `convert_audio` strips all video streams via `-vn`. We branch by format: MP3 and AIFF embed via dual-input ffmpeg; WAV stays audio-only (RIFF has no portable cover standard). When `thumbnail_path` is `None` (uploaded files, or download failed to fetch a thumb), every format falls back to audio-only.

- [ ] **Step 1: Write the failing integration test**

This test exercises the real ffmpeg pipeline against a synthetic input, then probes the output for embedded cover art. We use a tiny generated WAV + a tiny generated JPG, call `convert_audio`, and verify ffprobe sees the attached image.

Write `tests/test_cover_embedding.py`:

```python
import json
import shutil
import subprocess
from pathlib import Path

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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_cover_embedding.py
```

Expected: TypeError — `convert_audio() got an unexpected keyword argument 'thumbnail_path'`.

- [ ] **Step 3: Replace `convert_audio`**

In `app/server.py`, replace the entire `convert_audio` function (currently lines 186-217) with:

```python
def convert_audio(source_path, metadata, output_dir, output_format, thumbnail_path=None):
    artist = sanitize(metadata.get("artist") or metadata.get("uploader"), "Unknown Artist")
    title = sanitize(metadata.get("title") or Path(source_path).stem, "Unknown Title")
    output_folder = Path(output_dir).expanduser()
    output_folder.mkdir(parents=True, exist_ok=True)
    output_path = unique_path(output_folder, sanitize(f"{title} - {artist}"), output_format)

    has_cover = thumbnail_path is not None and Path(thumbnail_path).exists() and output_format != "wav"

    args = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source_path)]
    if has_cover:
        args += ["-i", str(thumbnail_path)]

    if has_cover:
        args += ["-map", "0:a", "-map", "1:v"]
    else:
        args += ["-vn"]

    args += [
        "-map_metadata", "0",
        "-ar", "44100",
        "-ac", "2",
        "-af", "silenceremove=start_periods=1:start_threshold=-90dB:stop_periods=1:stop_threshold=-90dB",
        "-metadata", f"title={title}",
        "-metadata", f"artist={artist}",
    ]

    if output_format == "wav":
        args += ["-sample_fmt", "s16", "-c:a", "pcm_s16le"]
    elif output_format == "aiff":
        args += ["-sample_fmt", "s16", "-c:a", "pcm_s16be"]
        if has_cover:
            args += ["-c:v", "mjpeg", "-write_id3v2", "1"]
        args += ["-f", "aiff"]
    else:  # mp3
        args += ["-c:a", "libmp3lame", "-b:a", "320k"]
        if has_cover:
            args += [
                "-c:v", "mjpeg",
                "-id3v2_version", "3",
                "-metadata:s:v", "title=Album cover",
                "-metadata:s:v", "comment=Cover (front)",
            ]

    args.append(str(output_path))
    run(args)
    return output_path
```

- [ ] **Step 4: Update `process_job` to pass `thumbnail_path` into `convert_audio`**

In `app/server.py`, locate the `process_job` call to `convert_audio` (around line 354):

```python
        output_path = convert_audio(source_path, metadata, output_dir, output_format)
```

Replace with:

```python
        output_path = convert_audio(source_path, metadata, output_dir, output_format, thumbnail_path=thumbnail_path)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_cover_embedding.py
```

Expected: 4 passed. (Tests run actual ffmpeg, so each takes ~1-2 seconds.)

- [ ] **Step 6: Run full test suite**

```bash
python3 -m pytest
```

Expected: 19 passed (5 codec + 10 probe + 4 cover).

- [ ] **Step 7: Commit**

```bash
git add app/server.py tests/test_cover_embedding.py
git commit -m "feat(convert): embed cover art into MP3 (APIC) and AIFF (ID3) outputs"
```

---

## Task 7: `copy_original` function and "original" format routing

**Files:**
- Modify: `app/server.py` (add `copy_original` function below `convert_audio`)
- Modify: `app/server.py:316-371` (route `output_format == "original"` to `copy_original`)
- Modify: `tests/test_cover_embedding.py` (add tests for `copy_original`)

The "Original" format does an `ffmpeg -c:a copy` remux — the audio bytes are bit-identical to the source. For containers that support `attached_pic` disposition (Opus/Ogg, MP3, M4A, FLAC), we embed the cover; for others, audio-only.

- [ ] **Step 1: Add tests for `copy_original`**

Append to `tests/test_cover_embedding.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_cover_embedding.py
```

Expected: ImportError for `copy_original`.

- [ ] **Step 3: Add `copy_original` to `app/server.py`**

Add this function in `app/server.py` immediately below `convert_audio`:

```python
ATTACHED_PIC_CONTAINERS = frozenset({".mp3", ".m4a", ".mp4", ".ogg", ".opus", ".flac"})


def copy_original(source_path, metadata, output_dir, thumbnail_path=None):
    artist = sanitize(metadata.get("artist") or metadata.get("uploader"), "Unknown Artist")
    title = sanitize(metadata.get("title") or Path(source_path).stem, "Unknown Title")
    output_folder = Path(output_dir).expanduser()
    output_folder.mkdir(parents=True, exist_ok=True)
    suffix = Path(source_path).suffix.lstrip(".") or "audio"
    output_path = unique_path(output_folder, sanitize(f"{title} - {artist}"), suffix)

    container = Path(source_path).suffix.lower()
    has_cover = (
        thumbnail_path is not None
        and Path(thumbnail_path).exists()
        and container in ATTACHED_PIC_CONTAINERS
    )

    args = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source_path)]
    if has_cover:
        args += ["-i", str(thumbnail_path)]
        args += ["-map", "0:a", "-map", "1:v"]
        args += ["-c:a", "copy", "-c:v", "mjpeg"]
        args += ["-disposition:v:0", "attached_pic"]
    else:
        args += ["-vn", "-c:a", "copy"]

    args += [
        "-map_metadata", "0",
        "-metadata", f"title={title}",
        "-metadata", f"artist={artist}",
    ]
    args.append(str(output_path))
    run(args)
    return output_path
```

- [ ] **Step 4: Route `process_job` to `copy_original` for `output_format == "original"`**

In `app/server.py`, locate the line in `process_job` (around line 354 after Task 6):

```python
        output_path = convert_audio(source_path, metadata, output_dir, output_format, thumbnail_path=thumbnail_path)
```

Replace with:

```python
        if output_format == "original":
            output_path = copy_original(source_path, metadata, output_dir, thumbnail_path=thumbnail_path)
        else:
            output_path = convert_audio(source_path, metadata, output_dir, output_format, thumbnail_path=thumbnail_path)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_cover_embedding.py
```

Expected: 7 passed (4 from Task 6 + 3 new).

- [ ] **Step 6: Run full test suite**

```bash
python3 -m pytest
```

Expected: 22 passed.

- [ ] **Step 7: Commit**

```bash
git add app/server.py tests/test_cover_embedding.py
git commit -m "feat(convert): add copy_original remux with attached_pic cover embedding"
```

---

## Task 8: Frontend default format AIFF + add "Original" option

**Files:**
- Modify: `app/static/index.html:37,39-43`
- Modify: `app/static/app.js:24,338`

This is mechanical and verified visually in the browser. No JS test harness exists.

- [ ] **Step 1: Update `index.html` format controls**

In `app/static/index.html`, replace lines 35-44 (the `format-ctl` div and its `<select>`) with:

```html
            <div class="ctl format-ctl">
              <span class="lbl">Format:</span>
              <span class="value" id="formatValue">AIFF</span>
              <span class="caret">▾</span>
              <select id="formatSelect" name="format" aria-label="Output format">
                <option value="wav">WAV</option>
                <option value="aiff" selected>AIFF</option>
                <option value="mp3">MP3 320</option>
                <option value="original">Original</option>
              </select>
            </div>
```

The diff: visible label `WAV` → `AIFF`, `selected` attribute on AIFF option, new `original` option.

- [ ] **Step 2: Update `app.js` initial state**

In `app/static/app.js`, locate line 24:

```javascript
  /** @type {'wav'|'aiff'|'mp3'} */ format: 'wav',
```

Replace with:

```javascript
  /** @type {'wav'|'aiff'|'mp3'|'original'} */ format: 'aiff',
```

- [ ] **Step 3: Update the `setFormat` JSDoc cast**

In `app/static/app.js`, locate the `setFormat` function (around line 136-138):

```javascript
function setFormat(value) {
  state.format = /** @type {'wav'|'aiff'|'mp3'} */ (value);
}
```

Replace with:

```javascript
function setFormat(value) {
  state.format = /** @type {'wav'|'aiff'|'mp3'|'original'} */ (value);
}
```

- [ ] **Step 4: Update `FORMAT_LABELS`**

In `app/static/app.js`, locate line 338:

```javascript
const FORMAT_LABELS = { wav: 'WAV', aiff: 'AIFF', mp3: 'MP3 320' };
```

Replace with:

```javascript
const FORMAT_LABELS = { wav: 'WAV', aiff: 'AIFF', mp3: 'MP3 320', original: 'Original' };
```

- [ ] **Step 5: Manual verification**

Start the server:

```bash
python3 -m app.server
```

Open `http://127.0.0.1:8765` in a browser.

Expected:
- The format control reads `AIFF` on first load (not `WAV`).
- Clicking the format control opens a native dropdown with four options in order: `WAV`, `AIFF`, `MP3 320`, `Original`.
- `AIFF` is highlighted as the current selection.
- Picking `Original` updates the visible label to `Original`.
- Picking `WAV` updates the label to `WAV`. The label for each option matches what's in `FORMAT_LABELS`.

Stop the server (Ctrl-C).

- [ ] **Step 6: Commit**

```bash
git add app/static/index.html app/static/app.js
git commit -m "feat(ui): default format to AIFF and add Original option"
```

---

## Task 9: Source card markup + CSS

**Files:**
- Modify: `app/static/index.html` (insert source card section between hero and divider)
- Modify: `app/static/styles.css` (append source card styles)

The card sits between the paste form and the "Recent downloads" divider, hidden until `populateSourceCard` (Task 10) makes it visible. The grid layout is `56px minmax(0, 1fr) auto` — cover, info, pill — matching the existing row card style at a slightly larger thumbnail size.

- [ ] **Step 1: Add source card HTML**

In `app/static/index.html`, find the closing `</section>` of `fm-hero` (line 49). Insert the source card immediately after it, before the `fm-divider` (line 51):

```html
      </section>

      <section class="fm-source-card" id="sourceCard" hidden aria-label="Source preview">
        <div class="fm-source-cover">
          <img id="sourceCover" alt="" />
        </div>
        <div class="fm-source-info">
          <div class="fm-source-title" id="sourceTitle">—</div>
          <div class="fm-source-meta" id="sourceMeta">—</div>
        </div>
        <div class="fm-source-pill" id="sourcePill">—</div>
      </section>

      <div class="fm-divider">
```

- [ ] **Step 2: Append source card CSS**

In `app/static/styles.css`, append at the bottom:

```css
/* Source preview card */
.fm-source-card {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  margin: 8px 22px 0;
  padding: 8px 12px 8px 8px;
  background: var(--p-surface);
  border: 1px solid var(--p-edge);
  border-radius: 10px;
}

.fm-source-card[hidden] { display: none; }

.fm-source-cover {
  width: 56px;
  height: 56px;
  border-radius: 6px;
  background: var(--p-surface-2);
  overflow: hidden;
}

.fm-source-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.fm-source-info { min-width: 0; }

.fm-source-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--p-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fm-source-meta {
  font-size: 11px;
  color: var(--p-muted-2);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fm-source-pill {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.04em;
  border: 1px solid var(--p-edge);
  background: transparent;
  color: var(--p-muted);
  white-space: nowrap;
}

.fm-source-pill.lossy {
  color: var(--p-warning);
  border-color: var(--p-warning);
}

.fm-source-pill.lossless {
  color: var(--p-success);
  border-color: var(--p-success);
}
```

- [ ] **Step 3: Manual verification (markup-only — card stays hidden)**

Start the server:

```bash
python3 -m app.server
```

Open `http://127.0.0.1:8765`. The card should NOT appear yet — it's `hidden` until JS unhides it in Task 10.

In the browser dev tools, run:

```javascript
document.getElementById('sourceCard').hidden = false;
```

Expected: a card appears between the paste form and the `Recent downloads` divider, with a 56×56 placeholder cover area, two `—` text lines, and a `—` pill on the right. The card uses the same surface color and border as the row cards below.

Re-hide it:

```javascript
document.getElementById('sourceCard').hidden = true;
```

Stop the server (Ctrl-C).

- [ ] **Step 4: Commit**

```bash
git add app/static/index.html app/static/styles.css
git commit -m "feat(ui): add source preview card markup and styles"
```

---

## Task 10: Frontend probe pipeline (debounce + AbortController + smart-flip)

**Files:**
- Modify: `app/static/app.js` (multiple sections)

This adds JS-side wiring: element refs, three new functions (`probeUrl`, `populateSourceCard`, `applySmartFormat`, `hideSourceCard`, `formatSourcePill`), debounce + abort logic on the input listener, and a card hide on form submit.

- [ ] **Step 1: Add element refs to `els`**

In `app/static/app.js`, locate the `els` object (lines 28-42). Replace it with:

```javascript
const els = {
  linkForm:     document.getElementById('linkForm'),
  linkInput:    document.getElementById('linkInput'),
  formatSelect: document.getElementById('formatSelect'),
  formatValue:  document.getElementById('formatValue'),
  downloadBtn:  document.getElementById('downloadBtn'),
  outputDir:    document.getElementById('outputDir'),
  chooseOutput: document.getElementById('chooseOutput'),
  outputName:   document.getElementById('outputName'),
  history:      document.getElementById('history'),
  keyToggle:    document.querySelectorAll('.fm-keytoggle .opt'),
  errorsTab:    document.getElementById('errorsTab'),
  errorsBadge:  document.getElementById('errorsBadge'),
  errorsPanel:  document.getElementById('errorsPanel'),
  sourceCard:   document.getElementById('sourceCard'),
  sourceCover:  document.getElementById('sourceCover'),
  sourceTitle:  document.getElementById('sourceTitle'),
  sourceMeta:   document.getElementById('sourceMeta'),
  sourcePill:   document.getElementById('sourcePill'),
};
```

- [ ] **Step 2: Add probe state and helpers**

In `app/static/app.js`, just below the `els` definition, add:

```javascript
const PROBE_DEBOUNCE_MS = 350;
let probeAbort = null;
let probeTimer = null;
```

- [ ] **Step 3: Add `probeUrl`, `populateSourceCard`, `formatSourcePill`, `applySmartFormat`, `hideSourceCard` functions**

In `app/static/app.js`, immediately after `chooseOutputFolder` (ends around line 106) and before `uploadFiles`, insert:

```javascript
async function probeUrl(url) {
  if (probeAbort) probeAbort.abort();
  probeAbort = new AbortController();
  try {
    const data = await fetchJson(`/api/probe?url=${encodeURIComponent(url)}`, { signal: probeAbort.signal });
    populateSourceCard(data);
    applySmartFormat(data);
  } catch (err) {
    if (err.name === 'AbortError') return;
    hideSourceCard();
  }
}

function populateSourceCard(data) {
  const titleText = data.title || '—';
  const metaParts = [];
  if (data.artist) metaParts.push(data.artist);
  const duration = formatDuration(data.duration);
  if (duration) metaParts.push(duration);
  els.sourceTitle.textContent = titleText;
  els.sourceMeta.textContent = metaParts.length ? metaParts.join(' · ') : '—';

  if (data.thumbnail) {
    els.sourceCover.src = data.thumbnail;
    els.sourceCover.alt = titleText;
  } else {
    els.sourceCover.removeAttribute('src');
    els.sourceCover.alt = '';
  }

  const pill = formatSourcePill(data);
  els.sourcePill.textContent = pill.label;
  els.sourcePill.className = `fm-source-pill ${pill.modifier}`;

  els.sourceCard.hidden = false;
}

function formatSourcePill(data) {
  const codec = data.codec ? String(data.codec).toUpperCase() : null;
  const kbps = data.bitrate ? Math.round(data.bitrate / 1000) : null;
  let label = '—';
  if (codec && kbps) label = `${codec} ${kbps}`;
  else if (codec) label = codec;
  const modifier = data.lossy ? 'lossy' : 'lossless';
  return { label, modifier };
}

function applySmartFormat(data) {
  const next = data.lossy ? 'mp3' : 'aiff';
  if (state.format === next) return;
  setFormat(next);
  els.formatSelect.value = next;
  els.formatValue.textContent = FORMAT_LABELS[next];
}

function hideSourceCard() {
  if (probeAbort) probeAbort.abort();
  if (probeTimer) clearTimeout(probeTimer);
  probeAbort = null;
  probeTimer = null;
  els.sourceCard.hidden = true;
  els.sourceCover.removeAttribute('src');
  els.sourceCover.alt = '';
  els.sourceTitle.textContent = '—';
  els.sourceMeta.textContent = '—';
  els.sourcePill.textContent = '—';
  els.sourcePill.className = 'fm-source-pill';
}
```

- [ ] **Step 4: Wire the input listener to schedule probes**

In `app/static/app.js`, locate the existing input listener (around line 325):

```javascript
els.linkInput.addEventListener('input', () => {
  els.downloadBtn.disabled = els.linkInput.value.trim().length === 0;
});
```

Replace with:

```javascript
els.linkInput.addEventListener('input', () => {
  const value = els.linkInput.value.trim();
  els.downloadBtn.disabled = value.length === 0;

  if (probeAbort) probeAbort.abort();
  if (probeTimer) clearTimeout(probeTimer);

  if (!value.toLowerCase().startsWith('http')) {
    hideSourceCard();
    return;
  }

  probeTimer = setTimeout(() => {
    probeTimer = null;
    probeUrl(value);
  }, PROBE_DEBOUNCE_MS);
});
```

- [ ] **Step 5: Hide the card on form submit**

In `app/static/app.js`, locate the existing submit handler (around line 329):

```javascript
els.linkForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const link = els.linkInput.value.trim();
  if (!link) return;
  els.linkInput.value = '';
  els.downloadBtn.disabled = true;
  await submitLink(link);
});
```

Replace with:

```javascript
els.linkForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const link = els.linkInput.value.trim();
  if (!link) return;
  els.linkInput.value = '';
  els.downloadBtn.disabled = true;
  hideSourceCard();
  await submitLink(link);
});
```

- [ ] **Step 6: Manual verification — happy path**

Start the server:

```bash
python3 -m app.server
```

Open `http://127.0.0.1:8765`. Paste a SoundCloud URL into the link input — for example:
`https://soundcloud.com/hiddevanwee/hold-on-tight`

Wait ~1 second.

Expected:
- The source card appears below the controls.
- The cover image loads.
- Title shows "Hold On Tight".
- Meta line shows "Hidde van Wee · 4:47" (or similar duration).
- The pill on the right reads "OPUS 128" in amber.
- The format control silently flips from `AIFF` to `MP3 320`.

- [ ] **Step 7: Manual verification — clearing input hides card**

Clear the input.

Expected: card disappears immediately (hidden state). Format control stays at `MP3 320` (smart-flip is one-way; user can manually reset).

- [ ] **Step 8: Manual verification — invalid URL does not show card**

Type `notaurl` into the input.

Expected: card stays hidden. No probe request fires. (Watch the Network tab to confirm.)

- [ ] **Step 9: Manual verification — fast-paste cancels prior probe**

In rapid succession (within 350ms): clear input, paste URL A, immediately paste URL B over it.

Expected: only one probe request completes (for B). The Network tab may show A's request as `(canceled)`.

- [ ] **Step 10: Manual verification — submit hides card**

Paste a URL, wait for the card to appear, click `Download`.

Expected: the card disappears as the row is added to the history below.

Stop the server (Ctrl-C).

- [ ] **Step 11: Commit**

```bash
git add app/static/app.js
git commit -m "feat(ui): probe pipeline with debounced fetch, source card, and smart-flip"
```

---

## Task 11: Manual end-to-end smoke test

**Files:** none (verification only)

This walks the full feature end-to-end against real SoundCloud/YouTube/Bandcamp URLs and confirms the cover-art chain works in Finder/Rekordbox. No code changes.

- [ ] **Step 1: Launch the app fresh**

```bash
python3 -m app.server
```

Open `http://127.0.0.1:8765`. Confirm the format control reads `AIFF` on first load.

- [ ] **Step 2: Lossy smart-flip + MP3 cover art**

Paste `https://soundcloud.com/hiddevanwee/hold-on-tight`.

Verify: source card appears with cover, title `Hold On Tight`, artist `Hidde van Wee`, pill `OPUS 128` (amber). Format control flips to `MP3 320`.

Click `Download`. Wait for the row to show `done`.

```bash
ls -lh "$HOME/Downloads/ForMyDJ" | tail -3
```

Verify: an `.mp3` file exists. Right-click it in Finder → `Get Info` → expect a thumbnail preview that matches the SoundCloud cover.

Drag the file into Rekordbox. Expect the cover art to display in the track list.

- [ ] **Step 3: AIFF cover art (manual override)**

Clear the input, then click the format control and select `AIFF`. Confirm the visible label updates to `AIFF`.

Paste the same SoundCloud URL again. Expect the source card to reappear, but the format control to stay at `AIFF` (smart-flip is a one-shot triggered by the probe, but since we just selected AIFF, a re-probe will flip back to MP3 — this is expected behavior; user must select AIFF *after* the probe). To test the AIFF cover path: select AIFF, paste URL, wait for card, manually re-select AIFF, click `Download`.

```bash
ls -lh "$HOME/Downloads/ForMyDJ" | grep aiff | tail -1
```

Verify: an `.aiff` file exists. Drag into Rekordbox — cover should display.

- [ ] **Step 4: WAV has no cover art**

Clear the input. Select `WAV`. Paste the same SoundCloud URL. Card appears, format control auto-flips to MP3 — manually re-select `WAV` after the card appears. Click `Download`.

```bash
ls -lh "$HOME/Downloads/ForMyDJ" | grep -i wav | tail -1
```

Verify: a `.wav` file exists. Right-click → `Get Info`. No cover art is expected. There should be NO sidecar `.jpg` next to the WAV file.

- [ ] **Step 5: Original format (Opus passthrough)**

Clear the input. Select `Original`. Paste the same SoundCloud URL. Card appears, format control auto-flips — re-select `Original` after the card. Click `Download`.

```bash
ls -lh "$HOME/Downloads/ForMyDJ" | grep opus | tail -1
```

Verify: an `.opus` file exists. Drag into Rekordbox — Rekordbox may reject `.opus` (it does not officially support Opus); that's expected and documented in the spec. Cover art should be embedded — verify with:

```bash
ffprobe -v error -show_streams "$HOME/Downloads/ForMyDJ/$(ls -t "$HOME/Downloads/ForMyDJ" | head -1)" | grep codec_type
```

Expect both `audio` and `video` codec types listed.

- [ ] **Step 6: Lossless source stays at AIFF**

Find or use a Bandcamp URL with a FLAC source (Bandcamp downloads are lossless when the artist enables it). Or use any YouTube URL where yt-dlp probes a non-lossy codec — most YouTube audio is `opus` or `m4a`, both lossy. If no FLAC URL is at hand, manually test by mocking: in browser dev tools console, after a probe:

```javascript
applySmartFormat({ lossy: false });
```

Verify: format control reads `AIFF` (no flip happened).

For a real test: paste a SoundCloud URL where the artist uploaded WAV (rare but exists), or use a known FLAC source. The pill should read `FLAC 1411` (green) and the format control should stay at `AIFF`.

- [ ] **Step 7: Probe failure path**

Paste `https://soundcloud.com/this-user-does-not-exist/some-track`.

Verify: after ~1 second, the card stays hidden (or disappears). The `Download` button is still enabled. Clicking it submits the job and the existing failure path takes over (red `failed` pill in history).

- [ ] **Step 8: Drag-drop upload**

Drag a local `.wav` or `.mp3` from Finder onto the browser window.

Verify: a job appears in history with format `AIFF` (the new default). No source card appears for uploads (probe is URL-only). The output AIFF should embed cover art if the source had ID3 cover art (existing `-map_metadata 0` behavior).

- [ ] **Step 9: Run the test suite one more time**

```bash
python3 -m pytest
```

Expected: 22 passed.

- [ ] **Step 10: Stop the server**

Ctrl-C in the server terminal.

If all nine smoke steps passed, the feature is complete. If any failed, file the failure as a follow-up commit fix; don't merge until they're all green.

---

## Self-Review (run before handoff to executor)

This plan was checked against the spec at `docs/superpowers/specs/2026-04-30-formydj-source-aware-conversion-design.md` for:

1. **Spec coverage:**
   - §1 Default WAV→AIFF: Tasks 4 (backend) + 8 (frontend) ✓
   - §2 `/api/probe` endpoint: Tasks 2 (parser) + 3 (subprocess wrapper + endpoint) ✓
   - §3 Cover art passthrough: Tasks 5 (download_source 3-tuple) + 6 (convert_audio embed) ✓
   - §4 "Original" format: Task 7 ✓
   - §5 Source card UI: Task 9 ✓
   - §6 Probe pipeline: Task 10 ✓
   - §7 Format/cover matrix: covered across Tasks 6 (MP3/AIFF/WAV) + 7 (Original) ✓
   - §8 Edge cases: probe timeout (Task 3), missing codec (Task 2), AbortController (Task 10), missing thumbnail (Task 6 test), uploaded files (Task 5: thumbnail_path = None branch) ✓
   - §9 Out of scope: nothing to implement, naturally covered by absence ✓
   - §10 Files touched: matches plan's File Structure section ✓
   - §11 Manual smoke test: Task 11 ✓

2. **Placeholder scan:** No "TBD"/"TODO"/"add appropriate error handling"/"similar to Task N" patterns. All code blocks contain complete, runnable code.

3. **Type consistency:**
   - `convert_audio(source_path, metadata, output_dir, output_format, thumbnail_path=None)` — same signature in Tasks 6 and 7.
   - `copy_original(source_path, metadata, output_dir, thumbnail_path=None)` — same signature in Task 7 definition and Task 7 routing.
   - `build_probe_response(info)` returns dict with keys `{title, artist, duration, codec, bitrate, thumbnail, ext, lossy}` — used consistently in Tasks 2 (parser), 3 (endpoint), 10 (frontend `populateSourceCard` reads these exact keys).
   - Frontend `state.format` type union in Tasks 8 includes `'original'` and matches `FORMAT_LABELS` keys.

No issues found. Plan is ready for execution.
