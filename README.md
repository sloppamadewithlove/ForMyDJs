# ForMyDJ

ForMyDJ is a local, cross-platform tool for turning authorized music links and audio files into clean, DJ-library-ready files.

## Download ForMyDJ

### I just want to use the app

Use the latest macOS app release:

1. Open the [latest release](https://github.com/sloppamadewithlove/ForMyDJs/releases/latest).
2. Download `ForMyDJ-macOS-*.zip`.
3. Unzip it and move `ForMyDJ.app` to `/Applications`.
4. Open ForMyDJ.

The app checks GitHub for newer releases and shows an update banner when a
newer version is available.

Current public releases still need two local media tools installed once:

```bash
brew install ffmpeg yt-dlp
```

Those tools are what let ForMyDJ fetch authorized SoundCloud/YouTube media and
convert it into DJ-library-ready audio. The product goal is to bundle these
inside the macOS release so regular users only download ForMyDJ.

### I am a developer or source-code user

Use the repo source, CLI, or Docker paths below. Docker is only for people who
want an isolated development/source-code environment. Regular app users do not
need Docker.

The GitHub **Code -> Download ZIP** button downloads the source code, not the
ready-to-use Mac app. Most people should use the release ZIP above.

## What ForMyDJ Does

Paste a SoundCloud or YouTube link, choose WAV, AIFF, or MP3, pick an output folder, and ForMyDJ downloads, converts, tags, warns about common quality issues, and saves the finished track locally. Local audio files can also be converted and cleaned up.

This project is for music you are authorized to access. It does not bypass DRM, paywalls, private accounts, or platform restrictions.

- Downloads one SoundCloud or YouTube link at a time with `yt-dlp`.
- Processes up to 3 active jobs while keeping an unlimited queue.
- Converts output to WAV, AIFF, or 320 kbps MP3 with `ffmpeg`.
- Smart-matches the output format to the source: paste an MP3 link → MP3, drop a WAV file → WAV. Pre-download probe inspects the source codec and flips the format dropdown automatically; you can still override before pressing Download.
- Bit-exact passthrough when the source already matches the chosen format (no re-encode, no quality loss for MP3→MP3 or WAV→WAV).
- Standardizes converted WAV/AIFF output to 44.1 kHz, 16-bit, stereo. Passthrough copies keep the source rate and depth.
- Trims leading and trailing digital silence on conversions.
- Preserves useful metadata and writes clean filenames as `Song Title - Artist`.
- Warns when lossless output is created from a lossy source.
- Warns about long tracks, mono audio, low-bitrate sources, and incomplete metadata.
- Estimates musical key locally as helpful metadata, not guaranteed truth.
- Stores compact processing metadata under `~/Library/Application Support/ForMyDJ`.

## Requirements

For regular Mac users:

- macOS 12 or newer.
- `ForMyDJ.app` from the GitHub release page.
- `ffmpeg` and `yt-dlp`, installed once on the Mac for current releases.

For source-code installs:

- Python 3.9 through 3.12.
- Xcode Command Line Tools, only if you are building the desktop wrapper.
- Docker Desktop, only if you choose the optional Docker path.

## Security And Privacy

ForMyDJ does not need API keys, passwords, cloud credentials, or a hosted
backend for normal use. Do not put secrets in the repo, in issue reports, or in
example commands.

The repo has ignore rules for local secret files, generated app bundles,
downloads, caches, logs, and temporary conversion output. A Gitleaks security
workflow also scans pushes and pull requests for committed secrets.

If a secret is ever committed, revoke or rotate it immediately; deleting it in a
later commit does not remove it from git history. See [SECURITY.md](SECURITY.md)
for the full checklist.

## Why ForMyDJ Needs These Pieces

ForMyDJ uses three local pieces:

| Piece | Plain-English job |
|---|---|
| ForMyDJ | The app window, queue, format choices, filenames, metadata cleanup, update notice, and DJ-specific warnings |
| `yt-dlp` | Gets the authorized audio stream and metadata from SoundCloud or YouTube |
| `ffmpeg` / `ffprobe` | Reads audio details and converts the file to MP3, WAV, or AIFF |

The app does not use these tools to bypass private tracks, paywalls, DRM, or
platform restrictions. It only processes links and files you are allowed to use.

Docker is **not required** for normal users. Docker is only for developers,
testers, and people running the source-code ZIP who want one isolated
environment that already contains Python, `ffmpeg`, and `yt-dlp`.

## Public Release Strategy

ForMyDJ is meant to be easy for DJs and non-technical users. The intended
public download flow is the macOS release ZIP, not the source-code ZIP and not
Docker.

- Current release flow: users download `ForMyDJ.app` and install `ffmpeg` /
  `yt-dlp` once with Homebrew.
- Target release flow: users download only `ForMyDJ.app`; the app release
  bundles the tested media tools it needs.
- Developer flow: source-code users can run the Python CLI, browser mode, or
  Docker environment.

This keeps regular users on the simplest path while preserving source-code and
Docker workflows for contributors.

## Install For Regular Mac Users

1. Install Homebrew if your Mac does not have it yet:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Homebrew is the installer used here to install the two media tools below.

2. Install the media tools:

```bash
brew install ffmpeg yt-dlp
```

3. Download the app:

- Open the [latest release](https://github.com/sloppamadewithlove/ForMyDJs/releases/latest).
- Download `ForMyDJ-macOS-*.zip`.
- Unzip it and move `ForMyDJ.app` to `/Applications`.

4. Open the app:

- Right-click `ForMyDJ.app`.
- Click **Open**.
- macOS may ask once because the app is from GitHub.

5. Pick an output folder in the app, paste a SoundCloud or YouTube link, choose
MP3/WAV/AIFF, and click **Download**.

## Developer And Source Installs

### GitHub ZIP download

If you use GitHub's **Code → Download ZIP** button, that ZIP contains the
ForMyDJ source code, Docker setup, Python package metadata, scripts, tests, and
docs. It does **not** contain Python, Docker Desktop, `ffmpeg`, `yt-dlp`, or a
prebuilt macOS app.

Most regular users should not use the repo ZIP. They should download the
`ForMyDJ-macOS-*.zip` file from the release page instead.

If you do use the repo ZIP, choose one source-code path:

**Option A: run from source with Python**

```bash
brew install ffmpeg yt-dlp
python3 -m pip install .
formydj serve
```

Then open:

```text
http://127.0.0.1:8765
```

**Option B: run from source with Docker**

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. Download the repo ZIP from GitHub and unzip it.
3. Open a terminal in the unzipped `ForMyDJ` folder.
4. Run:

```bash
docker compose up --build
```

Then open:

```text
http://127.0.0.1:8765
```

Docker downloads a Python runtime, installs `ffmpeg`/`ffprobe`, installs
`yt-dlp`, installs ForMyDJ, and writes finished files to `./downloads` on your
computer. This keeps the media tools inside the container so users do not need
to install Homebrew packages just to try the browser UI, but it is more
technical than the normal app install.

### Cross-platform CLI

```bash
# macOS
brew install ffmpeg yt-dlp
pip install "git+https://github.com/sloppamadewithlove/ForMyDJs.git"

# Linux (Debian/Ubuntu)
sudo apt-get install ffmpeg
pip install yt-dlp
pip install "git+https://github.com/sloppamadewithlove/ForMyDJs.git"

# Windows (with Scoop)
scoop install ffmpeg yt-dlp
pip install "git+https://github.com/sloppamadewithlove/ForMyDJs.git"
```

Then:

```bash
formydj url 'https://soundcloud.com/artist/track'
formydj file ~/Downloads/track.mp3
formydj --help
```

If you downloaded the repo as a ZIP instead of installing from Git, unzip it,
open a terminal in the `ForMyDJ` folder, install the system tools above, then
run:

```bash
pip install .
formydj version
```

### Build the macOS app yourself

The release ZIP is different from the repo ZIP. The release ZIP contains a
prebuilt `ForMyDJ.app`. The repo ZIP contains source code. If you want to build
the app yourself from source:

```bash
git clone https://github.com/sloppamadewithlove/ForMyDJs.git
cd ForMyDJ
brew install ffmpeg yt-dlp
./scripts/build-macos-app.sh
open dist/ForMyDJ.app
```

The app starts a local engine at `http://127.0.0.1:8765` inside its own window. Finished files are saved to the folder you choose on first launch — ForMyDJ does not pick one for you.

### Ask your AI assistant to install it for you

Source-code users can paste this into any AI assistant with shell access
(Claude Code, Codex, Gemini CLI, Cursor, etc.):

> Install ForMyDJ for me. The install instructions are at https://github.com/sloppamadewithlove/ForMyDJs — use the cross-platform CLI path appropriate for my OS, then verify with `formydj version`.

Skill manifests for the major AI agents are in `skills/` (see [skills/README.md](skills/README.md)).

## CLI Quick Reference

| Command | What it does |
|---|---|
| `formydj url <link>` | Download + convert a SoundCloud/YouTube link |
| `formydj file <path>` | Convert a local audio file |
| `formydj probe <link>` | Inspect metadata + codec without downloading |
| `formydj serve` | Launch the local web UI on port 8765 |
| `formydj version` | Print installed version |
| `formydj check-update` | Check GitHub for a newer release |

Common flags: `--format auto\|mp3\|wav\|aiff` (default `auto` matches source), `--output DIR` (default is the current working directory), `--json` for machine-readable output.

## Auto-Update

ForMyDJ checks GitHub on launch for new releases (cached 6 hours, no telemetry — just one anonymous request to `api.github.com/repos/sloppamadewithlove/ForMyDJs/releases/latest`).

When an update is available:

- **macOS app**: a banner appears at the top of the window with a download link straight to the GitHub release zip.
- **CLI**: run `formydj check-update` to see the latest version and release URL.

To install the update:

```bash
# CLI users
pip install -U "git+https://github.com/sloppamadewithlove/ForMyDJs.git"

# macOS app users
# Download ForMyDJ-macOS-*.zip from the release page, unzip, drag into /Applications.
```

Every tagged release on GitHub is built automatically by a workflow: it produces a `ForMyDJ-macOS-X.Y.Z.zip` (signed-friendly `ditto` archive that preserves macOS metadata) plus a Python wheel + sdist, all attached to the release.

## Browser Mode

You can also run the same local app in a browser without building the macOS wrapper:

```bash
./scripts/run-local.sh
# or
formydj serve
```

Then open:

```text
http://127.0.0.1:8765
```

## Docker

Docker is optional. It is useful for developers, testers, and source-code ZIP
users who want a known-good environment without changing their Mac's installed
media tools.

The Docker image includes Python 3.12, `ffmpeg`, `ffprobe`, and `yt-dlp`.
Finished files are written to `./downloads` on the host:

```bash
docker compose up --build
```

Then open:

```text
http://127.0.0.1:8765
```

In Docker, the app uses `/downloads` as the selected output folder because a
container cannot open the native macOS folder picker.

## What Gets Downloaded And Why

| Path | What the user downloads | Why it is needed |
|---|---|---|
| macOS app install | `ForMyDJ-macOS-*.zip`, `ffmpeg`, and `yt-dlp` | Smallest normal user setup: app plus the two media tools it calls |
| Repo ZIP | Source code, Dockerfile, Compose file, Python package metadata, scripts, docs, tests | Lets developers or advanced users run ForMyDJ from source |
| Docker | `python:3.12-slim`, Debian `ffmpeg`/`ffprobe`, Python `yt-dlp`, ForMyDJ package | Optional source-code environment that avoids local media-tool setup |
| CLI install | ForMyDJ Python package plus OS-installed `ffmpeg` and `yt-dlp` | Runs `formydj` directly on macOS, Linux, or Windows |
| macOS release ZIP | Prebuilt `ForMyDJ.app` wrapper | Gives Mac users a double-clickable UI; media tools still need to exist on the Mac |

`ffmpeg` does the actual audio conversion/probing. `yt-dlp` fetches authorized
SoundCloud/YouTube media and metadata. ForMyDJ is the workflow layer around
those tools: queueing, format choice, metadata cleanup, warnings, and the UI.

## How To Use

1. Click the **Folder** chip and choose where finished files should land. ForMyDJ does not pick a default — you designate the folder, and the Download button stays disabled until one is chosen.
2. Pick an output format: WAV, AIFF, or MP3. The dropdown auto-flips to match the source after you paste a link or drop a file — adjust manually only if you want a different target.
3. Paste a SoundCloud or YouTube link and press Download.
4. Or drag local audio files into the drop zone (still requires a chosen output folder).
5. Watch the queue for progress, warnings, errors, and finished file paths. The pulsing tab on the right edge appears whenever an error is logged — click to see what happened.

ForMyDJ saves completed audio directly in the folder you chose. It keeps temporary working files out of the repo and removes temporary download files after conversion.

## Quality Notes

ForMyDJ can convert a lossy source such as YouTube Opus/AAC or MP3 into WAV or AIFF, but that does not restore lost audio detail. It only places the already-lossy audio into a lossless container. The app warns when this happens so you can decide whether the file is good enough for your DJ workflow.

The best available path is:

1. Use the original WAV/AIFF if the platform officially exposes it.
2. Otherwise use the best available audio stream.
3. Convert only when the chosen output format requires it.

## Project Structure

```text
app/
  server.py          Local Python download/conversion engine
  cli.py             `formydj` CLI entry point
  desktop.py         Python desktop helper
  static/            Browser UI used by both browser mode and the macOS wrapper
scripts/
  build-macos-app.sh Build the WebKit-based macOS app wrapper
  run-local.sh       Run the local browser app
skills/
  README.md          Universal install guide for AI agents
  claude/SKILL.md    Claude Code skill manifest
  codex/AGENTS.md    Codex / generic agent guidance
  gemini/skill.toml  Gemini CLI skill manifest
Sources/ForMyDJ/     Experimental native SwiftUI implementation
pyproject.toml       Installable Python package (exposes `formydj` CLI)
docs/SPEC.md         Product and technical spec
```

The supported runnable surfaces today are the `formydj` CLI (cross-platform) and the macOS WebKit app. The SwiftUI source is kept in the repo as an experimental native direction.

## Development

Run locally:

```bash
./scripts/run-local.sh
```

Check Python syntax:

```bash
python3 -m py_compile app/server.py app/desktop.py
```

Build the macOS wrapper:

```bash
./scripts/build-macos-app.sh
```

Generated files such as `dist/`, `.build/`, `DerivedData/`, `__pycache__/`, logs, and `.DS_Store` are ignored by Git.

## Contributing

Issues and pull requests are welcome. Useful contributions include:

- More reliable source adapters.
- Better metadata extraction and tagging.
- Clearer quality warnings.
- UI improvements that keep the workflow fast.
- Tests around filename cleanup, warning generation, metadata reports, and job behavior.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow.

## License

ForMyDJ is open source under the [MIT License](LICENSE).
