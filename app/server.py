#!/usr/bin/env python3
import base64
import cgi
import gzip
import json
import math
import os
import queue
import re
import shutil
import struct
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

VERSION = "0.2.0"
GITHUB_REPO = "sloppamadewithlove/ForMyDJs"
UPDATE_CHECK_TIMEOUT_SECONDS = 4

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DEFAULT_OUTPUT = Path.home() / "Downloads" / "ForMyDJ"
CACHE_DIR = Path.home() / "Library" / "Application Support" / "ForMyDJ"
ACTIVE_METADATA = CACHE_DIR / "metadata-active.jsonl"
MAX_ACTIVE_JOBS = 3
MAX_KEY_SECONDS = 300
KEY_SAMPLE_RATE = 11025
PROBE_TIMEOUT_SECONDS = 10
UPDATE_CACHE = CACHE_DIR / "update-check.json"
UPDATE_CHECK_MAX_AGE_SECONDS = 6 * 60 * 60  # 6 hours

jobs_lock = threading.Lock()
jobs = {}
executor = ThreadPoolExecutor(max_workers=MAX_ACTIVE_JOBS)


def tool(name):
    for candidate in (
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
        f"/usr/bin/{name}",
        f"/bin/{name}",
    ):
        if os.path.exists(candidate) and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError(f"{name} was not found. Install it with Homebrew.")


FFMPEG = tool("ffmpeg")
FFPROBE = tool("ffprobe")
YTDLP = tool("yt-dlp")
GZIP = tool("gzip")

# Used by metadata_from_info (post-download): explicit lossy membership test.
# After ffprobe identifies the codec on disk, anything in this set triggers a
# lossy-source warning. Keep this list narrow.
LOSSY_CODECS = frozenset({"mp3", "aac", "opus", "vorbis", "m4a"})

# Used by _is_lossy_for_probe (pre-download): defensive — codecs NOT in this
# set are classified lossy. Includes uncommon-but-known lossless formats so
# that a flac/alac/wav probe never accidentally flips the dropdown to MP3 320.
# Do not assume LOSSY_CODECS and LOSSLESS_CODECS are complementary; they cover
# different call sites and different sets of codec names.
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


SUFFIX_ALIASES = {
    "wave": "wav",
    "aif": "aiff",
    "aifc": "aiff",
}


def _parse_version(value):
    """Parse a semver-ish string into a comparable tuple, ignoring 'v' prefix and pre-release suffix."""
    if not value:
        return (0, 0, 0)
    cleaned = value.strip().lstrip("vV")
    base = re.split(r"[-+]", cleaned, maxsplit=1)[0]
    parts = []
    for chunk in base.split("."):
        match = re.match(r"^(\d+)", chunk)
        parts.append(int(match.group(1)) if match else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def version_is_newer(candidate, current):
    """True iff `candidate` represents a strictly newer version than `current`."""
    return _parse_version(candidate) > _parse_version(current)


def _read_update_cache():
    try:
        if not UPDATE_CACHE.exists():
            return None
        age = time.time() - UPDATE_CACHE.stat().st_mtime
        if age > UPDATE_CHECK_MAX_AGE_SECONDS:
            return None
        return json.loads(UPDATE_CACHE.read_text())
    except (OSError, ValueError):
        return None


def _write_update_cache(payload):
    try:
        UPDATE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        UPDATE_CACHE.write_text(json.dumps(payload))
    except OSError:
        pass


def check_for_update(force=False, timeout=UPDATE_CHECK_TIMEOUT_SECONDS):
    """Check GitHub Releases for a newer ForMyDJ version.

    Returns dict: {current, latest, update_available, html_url, checked_at, source}
    On network failure, returns a payload with update_available=False and an error field.
    Caches results for UPDATE_CACHE_MAX_AGE_SECONDS to avoid hammering the API.
    """
    if not force:
        cached = _read_update_cache()
        if cached:
            cached["source"] = "cache"
            return cached

    payload = {
        "current": VERSION,
        "latest": None,
        "update_available": False,
        "html_url": None,
        "checked_at": int(time.time()),
        "source": "network",
    }
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"ForMyDJ/{VERSION}",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        latest = data.get("tag_name") or data.get("name") or ""
        payload["latest"] = latest
        payload["html_url"] = data.get("html_url")
        payload["update_available"] = bool(latest) and version_is_newer(latest, VERSION)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError) as exc:
        payload["error"] = str(exc)

    _write_update_cache(payload)
    return payload


def configured_default_output():
    """Optional explicit output folder for non-native environments such as Docker."""
    value = os.environ.get("FORMYDJ_OUTPUT_DIR")
    if not value:
        return None
    return Path(value).expanduser()


def normalize_suffix(suffix):
    """Lowercase a file suffix and collapse common aliases (wave→wav, aif→aiff)."""
    if not suffix:
        return ""
    return SUFFIX_ALIASES.get(suffix.lower(), suffix.lower())


def can_passthrough(source_path, output_format):
    """True when the source file is already in the requested output format
    and can be remuxed bit-exact instead of re-encoded.

    Compares normalized file extensions only — codec-vs-container quirks fall
    back to convert_audio, which is the safe path.
    """
    if not output_format:
        return False
    suffix = Path(source_path).suffix.lstrip(".")
    return normalize_suffix(suffix) == output_format.lower()


def build_probe_response(info):
    """Convert a yt-dlp -j info dict into a probe API response."""
    raw_codec = info.get("acodec") or info.get("codec")
    if isinstance(raw_codec, str) and raw_codec.lower() == "none":
        raw_codec = info.get("codec")
        if isinstance(raw_codec, str) and raw_codec.lower() == "none":
            raw_codec = None
    codec = raw_codec.lower() if isinstance(raw_codec, str) and raw_codec else None

    raw_bitrate = info.get("abr")
    if raw_bitrate is None:
        raw_bitrate = info.get("tbr")
    bitrate = int(round(float(raw_bitrate) * 1000)) if raw_bitrate is not None else None

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
            timeout=PROBE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Probe timed out after {PROBE_TIMEOUT_SECONDS} seconds")
    if result.returncode != 0:
        stripped = result.stderr.strip()
        message = stripped.splitlines()[-1] if stripped else "yt-dlp failed"
        raise RuntimeError(message)
    info = json.loads(result.stdout)
    return build_probe_response(info)


def ytdlp_ffmpeg_args():
    """Tell yt-dlp where ffmpeg lives when app launchers provide a minimal PATH."""
    return ["--ffmpeg-location", str(Path(FFMPEG).parent)]


def run(cmd):
    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"{cmd[0]} failed")
    return result


def update_job(job_id, **changes):
    with jobs_lock:
        jobs[job_id].update(changes)
        jobs[job_id]["updated_at"] = time.time()


def public_jobs():
    with jobs_lock:
        return sorted(jobs.values(), key=lambda item: item["created_at"], reverse=True)


def sanitize(value, fallback="Unknown"):
    value = re.sub(r'[\/\\?%*|"<>:]', "", value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value or fallback


def unique_path(folder, stem, suffix):
    candidate = folder / f"{stem}.{suffix}"
    index = 2
    while candidate.exists():
        candidate = folder / f"{stem} {index}.{suffix}"
        index += 1
    return candidate


def parse_title_artist(name):
    for sep in (" - ", " – ", " — "):
        if sep in name:
            left, right = name.split(sep, 1)
            return left.strip(), right.strip()
    return name.strip(), None


def ffprobe(path):
    result = run([
        FFPROBE,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ])
    data = json.loads(result.stdout or "{}")
    streams = data.get("streams", [])
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
    fmt = data.get("format", {})
    return {
        "duration": float(fmt["duration"]) if fmt.get("duration") else None,
        "codec": audio.get("codec_name"),
        "bitrate": int(audio.get("bit_rate") or fmt.get("bit_rate") or 0) or None,
        "channel_layout": audio.get("channel_layout"),
        "sample_rate": int(audio.get("sample_rate") or 0) or None,
    }


def metadata_from_info(info_path, audio_path, source_url=None):
    info = {}
    if info_path and Path(info_path).exists():
        info = json.loads(Path(info_path).read_text())

    probe = ffprobe(audio_path)
    filename_title, filename_artist = parse_title_artist(Path(audio_path).stem)
    codec = (probe.get("codec") or "").lower()

    artist = info.get("artist") or info.get("creator") or info.get("uploader") or filename_artist
    return {
        "title": info.get("title") or filename_title,
        "artist": artist,
        "album": info.get("album"),
        "genre": info.get("genre"),
        "mood": info.get("mood"),
        "uploader": info.get("uploader"),
        "upload_date": info.get("upload_date"),
        "source_url": info.get("webpage_url") or info.get("original_url") or source_url,
        "platform": info.get("extractor_key") or (urlparse(source_url).netloc if source_url else "Local"),
        "duration": probe.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "source_codec": probe.get("codec"),
        "source_bitrate": probe.get("bitrate"),
        "channel_layout": probe.get("channel_layout"),
        "sample_rate": probe.get("sample_rate"),
        "is_lossy": codec in LOSSY_CODECS,
    }


def warnings_for(metadata, output_format):
    warnings = []
    if metadata.get("duration") and metadata["duration"] > 20 * 60:
        warnings.append("Track is over 20 minutes")
    if metadata.get("is_lossy") and output_format in {"wav", "aiff"}:
        warnings.append(f"{output_format.upper()} output is converted from a lossy source")
    if "mono" in (metadata.get("channel_layout") or "").lower():
        warnings.append("Source appears mono")
    if not metadata.get("title") or not metadata.get("artist"):
        warnings.append("Metadata is incomplete")
    bitrate = metadata.get("source_bitrate")
    if metadata.get("is_lossy") and bitrate and bitrate < 192000:
        warnings.append("Lossy source bitrate appears low")
    return warnings


def download_source(url, workdir):
    output_template = str(workdir / "source.%(ext)s")
    run([
        YTDLP,
        "--no-playlist",
        "--ignore-config",
        *ytdlp_ffmpeg_args(),
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


_ATTACHED_PIC_CONTAINERS = frozenset({".mp3", ".m4a", ".mp4", ".ogg", ".opus", ".flac"})

# Ogg/Opus containers use METADATA_BLOCK_PICTURE (Vorbis comment) rather than a muxed
# video stream. These containers reject -map 1:v with any codec ffmpeg supports.
_VORBIS_COMMENT_CONTAINERS = frozenset({".ogg", ".opus"})


def _metadata_block_picture_b64(thumbnail_path):
    """Return a base64-encoded FLAC/Vorbis METADATA_BLOCK_PICTURE blob for the given image."""
    img_data = Path(thumbnail_path).read_bytes()
    suffix = Path(thumbnail_path).suffix.lower()
    mime = b"image/jpeg" if suffix in {".jpg", ".jpeg"} else b"image/png"
    desc = b""
    pic_type = 3  # Cover (front)
    width = height = depth = colors = 0
    bloc = struct.pack(">I", pic_type)
    bloc += struct.pack(">I", len(mime)) + mime
    bloc += struct.pack(">I", len(desc)) + desc
    bloc += struct.pack(">IIII", width, height, depth, colors)
    bloc += struct.pack(">I", len(img_data)) + img_data
    return base64.b64encode(bloc).decode()


def copy_original(source_path, metadata, output_dir, thumbnail_path=None, suffix_override=None):
    artist = sanitize(metadata.get("artist") or metadata.get("uploader"), "Unknown Artist")
    title = sanitize(metadata.get("title") or Path(source_path).stem, "Unknown Title")
    output_folder = Path(output_dir).expanduser()
    output_folder.mkdir(parents=True, exist_ok=True)
    raw_suffix = suffix_override or Path(source_path).suffix.lstrip(".") or "audio"
    suffix = normalize_suffix(raw_suffix) or raw_suffix.lower()
    output_path = unique_path(output_folder, sanitize(f"{title} - {artist}"), suffix)

    container = Path(source_path).suffix.lower()
    has_cover = (
        thumbnail_path is not None
        and Path(thumbnail_path).exists()
        and container in _ATTACHED_PIC_CONTAINERS
    )

    args = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source_path)]

    if has_cover and container not in _VORBIS_COMMENT_CONTAINERS:
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

    if has_cover and container in _VORBIS_COMMENT_CONTAINERS:
        args += ["-metadata", f"METADATA_BLOCK_PICTURE={_metadata_block_picture_b64(thumbnail_path)}"]

    args.append(str(output_path))
    run(args)
    return output_path


def estimate_key(audio_path, workdir):
    raw_path = workdir / "keydetect.f32"
    run([
        FFMPEG,
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(audio_path),
        "-t", str(MAX_KEY_SECONDS),
        "-ac", "1",
        "-ar", str(KEY_SAMPLE_RATE),
        "-f", "f32le",
        str(raw_path),
    ])
    data = raw_path.read_bytes()
    sample_count = len(data) // 4
    if sample_count < 4096:
        return None

    import array
    samples = array.array("f")
    samples.frombytes(data)
    if os.sys.byteorder != "little":
        samples.byteswap()

    frame_size = 4096
    hop = 4096
    chroma = [0.0] * 12
    for start in range(0, len(samples) - frame_size, hop):
        frame = samples[start:start + frame_size]
        rms = math.sqrt(sum(value * value for value in frame) / frame_size)
        if rms <= 0.01:
            continue
        for octave in range(2, 7):
            for note in range(12):
                midi = octave * 12 + note
                freq = 440.0 * (2.0 ** ((midi - 69) / 12.0))
                chroma[note] += goertzel(frame, freq)

    max_value = max(chroma) if chroma else 0
    if max_value <= 0:
        return None
    chroma = [value / max_value for value in chroma]
    return best_key(chroma)


def goertzel(frame, freq):
    omega = 2.0 * math.pi * freq / KEY_SAMPLE_RATE
    coeff = 2.0 * math.cos(omega)
    q0 = q1 = q2 = 0.0
    count = len(frame)
    for index, value in enumerate(frame):
        window = 0.5 - 0.5 * math.cos(2.0 * math.pi * index / (count - 1))
        q0 = coeff * q1 - q2 + value * window
        q2 = q1
        q1 = q0
    return math.sqrt(max(q1 * q1 + q2 * q2 - coeff * q1 * q2, 0.0))


def best_key(chroma):
    note_names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    major = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    minor = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
    best = (-999.0, "Unknown")
    for root in range(12):
        for label, profile in (("major", major), ("minor", minor)):
            rotated = [profile[(i - root) % 12] for i in range(12)]
            score = correlation(chroma, rotated)
            if score > best[0]:
                best = (score, f"{note_names[root]} {label}")
    return best[1]


def correlation(left, right):
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    left_power = sum((a - left_mean) ** 2 for a in left)
    right_power = sum((b - right_mean) ** 2 for b in right)
    return numerator / max(math.sqrt(left_power * right_power), 0.000001)


def append_metadata(report):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with ACTIVE_METADATA.open("a") as handle:
        handle.write(json.dumps(report, sort_keys=True) + "\n")
    with ACTIVE_METADATA.open() as handle:
        lines = sum(1 for _ in handle)
    if lines >= 50:
        archive = CACHE_DIR / f"metadata-{int(time.time())}.jsonl"
        ACTIVE_METADATA.rename(archive)
        with archive.open("rb") as source, gzip.open(f"{archive}.gz", "wb") as dest:
            shutil.copyfileobj(source, dest)
        archive.unlink(missing_ok=True)


def process_job(job_id):
    with jobs_lock:
        job = jobs[job_id]
        input_kind = job["input_kind"]
        input_value = job["input_value"]
        output_format = job["format"]
        output_dir = Path(job["output_dir"]).expanduser()

    workdir = Path(tempfile.mkdtemp(prefix=f"formydj-{job_id}-"))
    try:
        update_job(job_id, status="downloading", progress="Preparing source")
        if input_kind == "url":
            source_path, info_path, thumbnail_path = download_source(input_value, workdir)
            source_url = input_value
        else:
            source_path = Path(input_value)
            info_path = None
            thumbnail_path = None
            source_url = None

        update_job(job_id, status="analyzing", progress="Reading metadata")
        metadata = metadata_from_info(info_path, source_path, source_url)
        update_job(
            job_id,
            title=metadata.get("title"),
            artist=metadata.get("artist") or metadata.get("uploader"),
            genre=metadata.get("genre"),
            duration_seconds=metadata.get("duration"),
            cover_url=metadata.get("thumbnail"),
            warnings=warnings_for(metadata, output_format),
        )

        key = None
        try:
            key = estimate_key(source_path, workdir)
        except Exception as exc:
            update_job(job_id, warnings=jobs[job_id].get("warnings", []) + [f"Key estimate failed: {exc}"])

        update_job(job_id, estimated_key=key, status="converting", progress=f"Writing {output_format.upper()}")
        if output_format == "original":
            output_path = copy_original(source_path, metadata, output_dir, thumbnail_path=thumbnail_path)
        elif can_passthrough(source_path, output_format):
            output_path = copy_original(
                source_path,
                metadata,
                output_dir,
                thumbnail_path=thumbnail_path,
                suffix_override=output_format,
            )
        else:
            output_path = convert_audio(source_path, metadata, output_dir, output_format, thumbnail_path=thumbnail_path)
        report = {
            "id": job_id,
            "created_at": job["created_at"],
            "input_kind": input_kind,
            "input_value": input_value,
            "output_path": str(output_path),
            "output_format": output_format,
            "metadata": metadata,
            "estimated_key": key,
            "warnings": jobs[job_id].get("warnings", []),
        }
        append_metadata(report)
        update_job(job_id, status="finished", progress="Done", output_path=str(output_path), report=report)
    except Exception as exc:
        update_job(job_id, status="failed", progress="Failed", error=str(exc))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def enqueue(input_kind, input_value, output_format, output_dir):
    job_id = uuid.uuid4().hex
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "created_at": time.time(),
            "created_at_display": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": time.time(),
            "input_kind": input_kind,
            "input_value": input_value,
            "format": output_format,
            "output_dir": output_dir,
            "status": "queued",
            "progress": "Waiting",
            "warnings": [],
        }
    executor.submit(process_job, job_id)
    return jobs[job_id]


def choose_output_folder(current_path):
    configured_output = configured_default_output()
    if configured_output:
        return str(configured_output)

    default_path = Path(current_path or DEFAULT_OUTPUT).expanduser()
    if not default_path.exists():
        default_path = default_path.parent if default_path.parent.exists() else Path.home()

    script = """
on run argv
  set defaultPath to POSIX file (item 1 of argv)
  set selectedFolder to choose folder with prompt "Choose ForMyDJ output folder" default location defaultPath
  return POSIX path of selectedFolder
end run
"""
    result = subprocess.run(
        ["osascript", "-e", script, str(default_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        if "User canceled" in result.stderr:
            return None
        raise RuntimeError(result.stderr.strip() or "Could not open folder picker")
    return result.stdout.strip().rstrip("/") or None


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        parsed = urlparse(path)
        if parsed.path == "/":
            return str(STATIC / "index.html")
        return str(STATIC / parsed.path.lstrip("/"))

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/jobs":
            default_output = configured_default_output()
            self.send_json({
                "jobs": public_jobs(),
                "default_output": str(default_output) if default_output else None,
            })
            return
        if parsed.path == "/api/version":
            force = parse_qs(parsed.query).get("refresh") == ["1"]
            self.send_json(check_for_update(force=force))
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

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/jobs":
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            link = (payload.get("link") or "").strip()
            output_format = (payload.get("format") or "aiff").lower()
            output_dir = (payload.get("output_dir") or "").strip()
            if not link:
                self.send_json({"error": "Missing link"}, 400)
                return
            if not output_dir:
                self.send_json({"error": "Choose an output folder before downloading."}, 400)
                return
            self.send_json({"job": enqueue("url", link, output_format, output_dir)})
            return

        if parsed.path == "/api/upload":
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type"),
            })
            output_format = (form.getfirst("format") or "aiff").lower()
            output_dir = (form.getfirst("output_dir") or "").strip()
            file_item = form["file"] if "file" in form else None
            if file_item is None or not file_item.filename:
                self.send_json({"error": "Missing file"}, 400)
                return
            if not output_dir:
                self.send_json({"error": "Choose an output folder before converting."}, 400)
                return
            upload_dir = CACHE_DIR / "uploads" / uuid.uuid4().hex
            upload_dir.mkdir(parents=True, exist_ok=True)
            upload_path = upload_dir / sanitize(file_item.filename)
            with upload_path.open("wb") as handle:
                shutil.copyfileobj(file_item.file, handle)
            self.send_json({"job": enqueue("file", str(upload_path), output_format, output_dir)})
            return

        if parsed.path == "/api/cache/clear":
            shutil.rmtree(CACHE_DIR, ignore_errors=True)
            self.send_json({"ok": True})
            return

        if parsed.path == "/api/output/choose":
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            try:
                path = choose_output_folder(payload.get("current_path") or str(Path.home() / "Downloads"))
            except Exception as exc:
                self.send_json({"error": str(exc)}, 500)
                return
            self.send_json({"path": path, "cancelled": path is None})
            return

        self.send_json({"error": "Not found"}, 404)


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    port = int(os.environ.get("FORMYDJ_PORT", "8765"))
    host = os.environ.get("FORMYDJ_HOST", "127.0.0.1")
    server = ThreadingHTTPServer((host, port), Handler)
    display_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    url = f"http://{display_host}:{port}"
    print(f"ForMyDJ running at {url}")
    if os.environ.get("FORMYDJ_NO_BROWSER") != "1":
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
