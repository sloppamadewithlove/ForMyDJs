# Contributing To ForMyDJ

ForMyDJ is a small local-first macOS app. Keep changes focused, easy to run locally, and respectful of platform rules.

## Development Setup

Install the external tools:

```bash
xcode-select --install
brew install ffmpeg yt-dlp
```

Run the app:

```bash
./scripts/run-local.sh
```

Build the desktop wrapper:

```bash
./scripts/build-macos-app.sh
```

## Before Opening A Pull Request

Run:

```bash
python3 -m py_compile app/server.py app/desktop.py
./scripts/build-macos-app.sh
gitleaks git --no-banner --redact --log-opts="--all" .
gitleaks dir --no-banner --redact .
```

Then verify the app opens:

```bash
open dist/ForMyDJ.app
```

## Contribution Guidelines

- Do not add behavior that bypasses DRM, paywalls, account restrictions, or private content controls.
- Do not commit API keys, passwords, tokens, private keys, signing files, `.env` files, downloaded tracks, or personal machine credentials.
- Prefer small pull requests with a clear user-facing purpose.
- Keep generated files out of Git. The repo intentionally ignores `dist/`, `.build/`, `DerivedData/`, caches, logs, and macOS metadata files.
- Preserve the local-first design. ForMyDJ should not require a hosted backend for normal use.
- Add tests or focused verification notes when changing conversion, metadata, warning, or queue behavior.

## Good First Areas

- Metadata parsing and embedding improvements.
- Tests for filename sanitization and warning generation.
- Better error messages for missing tools or unsupported links.
- Rekordbox-friendly export helpers.
- UI polish that keeps the intake workflow fast.
