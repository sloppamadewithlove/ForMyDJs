# ForMyDJ Local Handoff

Read this before continuing product or implementation work. The public README should be updated later, after the app catches up to the direction below.

## Current State

- Repo: `https://github.com/sloppamadewithlove/ForMyDJs`
- Current runnable app: Python local server in `app/server.py` plus web UI in `app/static/`.
- Current macOS wrapper: `scripts/build-macos-app.sh` builds `dist/ForMyDJ.app`.
- Public README is intentionally conservative and should not be treated as the final product promise.
- Product source of truth: `docs/SPEC.md`.

## Locked Product Direction

- App name stays `ForMyDJ`.
- Product promise: `Listen to Music Globally`.
- Open-source project for reputation, not monetization.
- Target users: DJs, musicians, producers, A&R scouts, labels, and music curators.
- Priorities: audio quality clarity, organization, speed, cross-platform access.
- Public legal/use positioning belongs in GitHub docs, not intrusive in-app warnings.
- No Apple notarization requirement.
- No Windows code-signing requirement.
- No hosted backend or telemetry requirement.
- Public cross-platform support should wait until portable downloads exist.
- "Run from source" is for developers only, not the public user path.

## Platform Direction

- Use one shared app, then package differently per OS.
- Tauri is optional, not locked. It is one possible way to package one shared app for multiple operating systems.
- Core decision: each OS should get its own easiest downloadable package.
- macOS: portable `.zip` containing `ForMyDJ.app`.
- Windows: portable `.zip` containing `ForMyDJ.exe` plus bundled tools.
- Linux: AppImage or portable `.zip` later.
- Prefer portable packages before full installers.
- Current Python/WebKit implementation should keep working while migration happens.

## Tooling Direction

- Eventually bundle `ffmpeg`, `ffprobe`, and `yt-dlp`.
- Do not commit bundled binaries to source control.
- Build/release scripts should fetch pinned platform binaries and include license notices.
- Updates should be manual through one combined update area.
- Combined update area must show exactly what needs updating: app, `yt-dlp`, `ffmpeg`, `ffprobe`, or none.
- The app should update only the components that need updates.
- `yt-dlp` should use stable updates by default because stale extractors can break downloads.
- `ffmpeg`/`ffprobe` should stay pinned unless an update is needed for compatibility or security.

## App Update Direction

The easiest open-source update flow is not silent self-update.

Recommended v1:

1. User clicks combined update area.
2. App checks latest GitHub release and bundled tool versions.
3. App identifies OS/architecture.
4. App downloads the correct portable package directly into the user's Downloads folder when practical.
5. App reveals the downloaded file in the Downloads folder.
6. User unzips/replaces the app manually.

This avoids fragile unsigned self-replacement while still keeping updates easy.

Do not attempt automatic app replacement in v1.

## Output Direction

- Output files stay flat in the selected output folder.
- Filename format: `Song Title - Artist`.
- If artist is missing, use `Unknown Artist`.
- Do not fall back to uploader as artist.
- Do not create artist folders in the user's output folder.
- Duplicates are allowed; use suffixes like `Song Title - Artist 2.wav`.
- Internal metadata/history can organize by artist for search and past-download review.

## M3U Direction

- Use M3U instead of Rekordbox XML.
- Maintain one global playlist named `ForMyDJ Downloads.m3u`.
- Store the master M3U in app data.
- Make it easily accessible from the UI.
- Use absolute paths in the master M3U for compatibility.
- Update the M3U automatically after every successful job.

## Key Detection Direction

- Use `libkeyfinder`.
- Document GPLv3-or-later licensing impact.
- Current lightweight key detector is only a bridge/fallback.
- Default display is standard notation such as `C# minor`.
- UI should let user switch between standard notation and Camelot notation such as `12A`.
- Writing key tags into files is useful but not required in the next implementation pass.

## Error Report Direction

- Do not create success sidecar reports by default.
- Store compact history/report data in app data.
- Show report actions only when an error happens.
- Retry failed jobs 3 times in the backend.
- If the 4th attempt fails, show a popup with:
  - `Open GitHub Issue`
  - `Copy Report`
  - `Dismiss`
- `Open GitHub Issue` should prefill a browser issue where possible.
- `Copy Report` should copy structured text for users without GitHub accounts.
- No anonymous direct report submission unless a hosted backend is intentionally added later.

## UI Direction

- Claude Code should redesign the visual UI and button layout for best UI/UX.
- Keep it as a one-page app unless the UI becomes crowded.
- Include link input, format selector, output folder, download action, drag/drop, queue, history/artist search, M3U status, key notation choice, and combined update area.

## Next Implementation Priorities

1. Improve the current Python/WebKit app first while keeping cross-platform packaging in mind.
2. Add automatic app-data M3U writing.
3. Add retry policy and final-failure popup.
4. Add history/artist metadata index.
5. Add combined update area UI behavior.
6. Integrate `libkeyfinder`.
7. Have Claude Code redesign the visual UI and button layout.
8. Create portable package scripts for macOS and Windows.
9. Update the public README once implementation matches the new direction.
