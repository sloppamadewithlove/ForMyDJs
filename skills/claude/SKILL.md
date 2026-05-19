---
name: formydj
description: Use when the user wants to convert a SoundCloud/YouTube link or local audio file into a DJ-library-ready file (MP3, WAV, or AIFF). Bit-exact passthrough preserves quality when source already matches target format.
---

# ForMyDJ — Claude Code skill

This skill wraps the `formydj` CLI, a local audio downloader/converter that you (Claude) can invoke for the user. It never bypasses DRM, paywalls, or platform restrictions — only authorized public content.

## When to use this skill

Invoke when the user asks to:

- Download a SoundCloud or YouTube link as MP3/WAV/AIFF
- Convert a local `.mp3`, `.wav`, `.aiff`, `.flac`, `.m4a`, `.opus`, etc. file for DJ use
- Inspect a track's codec/bitrate/duration before downloading

Do NOT use this skill for streaming/playback or any non-DJ purpose.

## Prerequisites (one-time install)

If `formydj --version` errors with "command not found", install:

```bash
# macOS (Homebrew)
brew install ffmpeg yt-dlp
pip install "git+https://github.com/sloppamadewithlove/ForMyDJs.git"

# Linux (apt)
sudo apt-get install ffmpeg
pip install yt-dlp
pip install "git+https://github.com/sloppamadewithlove/ForMyDJs.git"

# Windows (Scoop)
scoop install ffmpeg yt-dlp
pip install "git+https://github.com/sloppamadewithlove/ForMyDJs.git"
```

## Commands

All commands print JSON when given `--json`, otherwise human-readable text.

### Download a URL

```bash
formydj url <link> [--format auto|mp3|wav|aiff] [--output DIR] [--json]
```

- `--format auto` (default): matches source codec. MP3 source → MP3 output (bit-exact), WAV source → WAV output, FLAC/ALAC → AIFF, lossy (Opus/AAC) → MP3.
- Output saved to the current working directory unless `--output DIR` overrides. ForMyDJ never auto-creates a folder for you.

### Convert a local file

```bash
formydj file <path> [--format auto|mp3|wav|aiff] [--output DIR] [--json]
```

Same smart-format default. If source extension matches target format, the file is bit-exact remuxed (no re-encode, no quality loss).

### Probe a URL

```bash
formydj probe <link> [--json]
```

Returns title, artist, codec, duration, lossy/lossless, and the suggested output format — without downloading. Use this when the user is unsure whether a link is worth downloading.

### Check for updates

```bash
formydj check-update [--force] [--json]
```

Hits `api.github.com/repos/sloppamadewithlove/ForMyDJs/releases/latest`. Cached 6 hours. If `update_available: true`, point the user to the `html_url` to download.

### Launch the web UI

```bash
formydj serve [--port 8765] [--no-browser]
```

Starts the same Python engine at `http://127.0.0.1:8765` for users who prefer the GUI.

## Quality rules to enforce

1. **Never auto-upgrade a lossy source to a lossless container without warning the user.** The CLI handles this defensively (lossy probe → MP3), but if the user explicitly asks for WAV from a SoundCloud Opus stream, tell them the file will be a lossless wrapper around lossy audio.
2. **MP3 → MP3 must remain bit-exact.** `--format auto` handles this. If the user overrides to `--format wav` on an MP3, warn them they'll get a lossless container of already-lossy audio.
3. **Respect platform terms of service.** Refuse to download from private/paywalled content. The underlying `yt-dlp` will fail on DRM-protected sources; pass the error through to the user.

## Output

Success prints `Saved: <path>` and any warnings. With `--json`, the full job record is emitted — useful for piping to other tools.

Failure prints the error to stderr and exits non-zero.
