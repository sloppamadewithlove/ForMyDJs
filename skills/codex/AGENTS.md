# AGENTS.md — ForMyDJ

Codex / generic-agent guidance for using the `formydj` CLI.

## What this tool does

Converts authorized SoundCloud/YouTube links and local audio files into DJ-library-ready outputs (MP3/WAV/AIFF) with smart source-matching and bit-exact passthrough.

## Activation

If `formydj --version` works, the tool is installed. Otherwise install it:

```bash
pip install "git+https://github.com/sloppamadewithlove/ForMyDJs.git"
# System tools (required):
#   macOS:   brew install ffmpeg yt-dlp
#   Linux:   apt-get install ffmpeg && pip install yt-dlp
#   Windows: scoop install ffmpeg yt-dlp
```

## Subcommand reference

| Command | Purpose |
|---|---|
| `formydj url <link>` | Download + convert a link |
| `formydj file <path>` | Convert a local audio file |
| `formydj probe <link>` | Inspect URL metadata + codec without downloading |
| `formydj serve` | Launch the local web UI on port 8765 |
| `formydj version` | Print version |
| `formydj check-update` | Check GitHub for newer releases (6h cache) |

### Common flags

- `--format auto|mp3|wav|aiff` — default `auto` matches source codec
- `--output DIR` — default is the current working directory (ForMyDJ never auto-creates a folder)
- `--json` — machine-readable result (use this when chaining)

## Decision logic

- **Source codec MP3** → emit MP3 (bit-exact, no re-encode)
- **Source codec WAV/PCM-LE** → emit WAV
- **Source codec AIFF/PCM-BE** → emit AIFF
- **Source codec FLAC/ALAC/APE/TTA/WV** → emit AIFF (lossless container)
- **Source codec Opus/AAC/M4A (lossy)** → emit MP3
- **Probe failure or unknown** → emit MP3 (defensive)

## Error semantics

- Exit `0`: file saved successfully (path printed to stdout)
- Exit `1`: job failed (reason on stderr)
- DRM/paywall/private content → `yt-dlp` error propagated; do not retry
