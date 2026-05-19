# ForMyDJ Spec

## Product Intent

ForMyDJ is an open-source desktop app for DJs, musicians, A&R scouts, producers, labels, and music curators who want a fast local workflow for authorized music intake.

The product promise is: **Listen to Music Globally**.

ForMyDJ should let a user open the app, paste an authorized SoundCloud, YouTube, or future supported music link, choose an output format, and download a clean local audio file without needing to understand command-line tools.

The product priorities are:

1. Audio quality clarity.
2. Clean organization.
3. Speed.
4. Cross-platform access.

ForMyDJ is not intended to bypass DRM, paywalls, account restrictions, or private content controls. This legal/use-positioning belongs in the GitHub README and docs, not as intrusive in-app warnings.

## Public Release Direction

- Open source project.
- Public GitHub repo remains the primary home.
- Distribution should be easy for normal users but does not require professional app-store style polish.
- No Apple notarization requirement.
- No Windows code-signing requirement.
- No hosted backend requirement.
- No telemetry requirement.
- No paid/proprietary edition planned.
- Releases are built manually by the maintainer.
- GitHub Releases can store downloadable builds, but the app and README should expose obvious download/update paths so users are not forced to understand the Releases page.
- Public cross-platform support should wait until portable downloads exist. "Run from source" can remain a developer path, but it should not be presented as the public user experience.

## Cross-Platform Direction

The long-term app should use one shared product/UI codebase with platform-specific packages:

- macOS: portable `.zip` containing `ForMyDJ.app`.
- Windows: portable `.zip` containing `ForMyDJ.exe` plus bundled tools.
- Linux: AppImage or portable `.zip` later.

Tauri is a possible packaging/runtime option, not a locked requirement. It is useful because it can produce macOS/Windows/Linux desktop builds from one shared app with smaller size than Electron, but the core product decision is simpler: each operating system should get its own easiest downloadable package.

Each operating system may use the easiest package format for that platform. The app should not become three separate product implementations unless there is a strong technical reason, because that would increase maintenance and make features drift across platforms.

Use portable packages before full installers. Portable packages fit the open-source direction better because they do not need admin permissions, app-store distribution, notarization, or Windows installer signing. Full installers can be considered later only if users need shortcuts, file associations, or smoother replacement flows.

The current runnable implementation remains:

- Local Python server in `app/server.py`.
- Browser/WebKit UI in `app/static/`.
- macOS wrapper built by `scripts/build-macos-app.sh`.

The migration path should be incremental: keep the current app working while moving packaging/runtime toward the cross-platform direction.

## Bundled Tools

ForMyDJ should eventually bundle the tools needed to run:

- `ffmpeg`
- `ffprobe`
- `yt-dlp`

Reason: users should be able to download the app and use it without installing Homebrew, Python packages, or command-line dependencies manually.

The GitHub repo should explain why these tools are included:

- `yt-dlp` handles supported music/video source extraction.
- `ffmpeg` and `ffprobe` handle audio inspection, conversion, metadata, and encoding.
- Bundling avoids setup friction and makes behavior more consistent across operating systems.

Bundled tools should not be committed directly into source control. Release/build scripts should fetch pinned versions for each platform, verify checksums where practical, and include license notices.

Tool updates should be manual and stable-first:

- User clicks a combined update area/button.
- App checks for app updates and tool updates.
- App shows exactly what needs updating: app, `yt-dlp`, `ffmpeg`, `ffprobe`, or none.
- User confirms.
- App updates only the specific components that need updates.
- `yt-dlp` updates should use stable releases by default because extractor changes can break downloads if the tool gets stale.
- `ffmpeg` and `ffprobe` should update less often and stay pinned unless a release is needed for compatibility or security.

The app should not silently update tools in the background.

## App Update Direction

The app should expose a clear update path:

- A visible "Check for Updates" or "Download Latest Version" action.
- It checks the latest GitHub release.
- It tells the user if their app is current or outdated.
- It opens or downloads the correct platform build.

Because the project does not require code signing/notarization, fully automatic self-replacement should be treated as optional and lower priority. The reliable open-source default is to open the browser directly to the correct latest build or download it into the user's Downloads folder, then guide the user to replace the old app.

The easiest v1 option is:

1. App checks the latest GitHub release.
2. App identifies the current operating system and CPU architecture.
3. App offers to download the correct portable package directly into the user's Downloads folder.
4. App reveals the downloaded file in the Downloads folder.
5. User unzips/replaces the app manually.

This avoids fragile unsigned self-update behavior while still making updates easy.

## Locked Workflow Requirements

- Easy desktop workflow.
- One link submitted at a time.
- Multiple submitted links can process concurrently.
- Current processing policy: 3 active jobs with unlimited queued jobs.
- Local audio files can be dragged and dropped for metadata cleanup/conversion.
- Download starts immediately after submission.
- User chooses output format per job: WAV, AIFF, or MP3.
- MP3 output defaults to 320 kbps CBR.
- Prefer original platform-provided WAV/AIFF if exposed.
- Fall back to best available stream when original file is not exposed.
- WAV/AIFF output: 44.1 kHz, 16-bit, stereo.
- No loudness normalization.
- No EQ, compression, or creative processing.
- Trim only leading/trailing digital silence.
- Extract title, artist, album/release info when available, genre, mood, upload date, source platform, source URL, duration, cover art, and key if detected.
- If artist metadata is missing, use `Unknown Artist`. Do not fall back to uploader as artist.
- Exclude follower count, likes, plays, comments, and user comment metadata.
- Save output files directly in the selected output folder.
- Save filenames as `Song Title - Artist`.
- Do not create artist folders in the user's output folder.
- Clean unsafe filename characters.
- Embed metadata where supported.
- Download cover art when available.
- Keep completed files available offline.
- Delete temporary source files after successful conversion.
- Warn on likely quality issues without modifying extra audio characteristics.
- Warn on tracks over 20 minutes, but still allow download.
- Remember default output folder and output format between launches.
- Do not require a separate settings page unless the one-page UI becomes too crowded.

## Output Organization

User-facing downloads stay flat:

```text
Selected Output Folder/
  Song Title - Artist.wav
  Other Song - Unknown Artist.mp3
```

Artist organization should happen inside app metadata/history, not by adding extra folders to the user's downloads. The app can maintain an internal artist index so users can search or filter past downloads by artist.

Duplicates are allowed. If a duplicate filename exists, the app should create a unique filename such as:

```text
Song Title - Artist 2.wav
```

The app does not need to warn that a source URL was downloaded before.

## M3U Playlist Support

ForMyDJ should prioritize M3U over Rekordbox XML because M3U is simpler and broadly compatible with DJ/music software.

Requirements:

- Maintain one global playlist named `ForMyDJ Downloads.m3u`.
- Update the M3U automatically whenever a track finishes successfully.
- Store the master M3U in the app data directory.
- Make the master M3U easily accessible from the UI with an "Open Playlist" or "Reveal Playlist" action.
- Use absolute file paths in the master M3U for maximum compatibility when audio files stay in a flat user-selected output folder.
- Optionally allow later export/copy of the M3U into the selected output folder.
- Keep output useful for Rekordbox, Serato, Traktor, VirtualDJ, Engine DJ, Ableton, and general music players.

Rekordbox XML is not a v1 requirement.

## Audio Truths

Converting MP3 or another lossy source to WAV/AIFF does not improve audio quality. It only creates a lossless container around audio that has already lost information. WAV/AIFF can still be useful for DJ playback compatibility, editing workflows, and avoiding further generation loss, but it will not restore detail removed by MP3, Opus, AAC, or a platform transcode.

Best quality behavior:

1. Download original WAV/AIFF if officially exposed.
2. Otherwise download the highest-quality available stream.
3. Warn when a WAV/AIFF output is sourced from lossy audio.
4. Avoid re-encoding unless the user-selected format requires it.

## Platform Handling

### SoundCloud

Use `yt-dlp` initially. It supports SoundCloud extraction and can obtain available audio streams and metadata for many public SoundCloud links. If a track has an official downloadable original file exposed by SoundCloud and accessible to the user, the app should prefer that original.

The app should not attempt to bypass SoundCloud Go+, paywalls, DRM, or account-gated access. Private/link-only access can be considered later only when it uses normal user-authorized access.

### YouTube

Use `yt-dlp` initially for YouTube videos, YouTube Music links, Shorts when accepted as regular videos, and unlisted videos when accessible.

YouTube does not usually expose original uploaded WAV/AIFF files. Most YouTube downloads will be best-available streamed audio converted to the selected output format. The app should warn when lossless output is created from a lossy YouTube stream.

### Future Sources

Future adapters can support Bandcamp, Dropbox, direct audio links, Audiomack, Instagram, TikTok, and other sources. Each source should declare whether it can provide original files or only streamed/transcoded audio.

## Key Detection

Key detection is an important feature because users may rely on it in Rekordbox and other DJ software.

Requirements:

- Include key detection.
- Treat detected key as strong app metadata, while still recognizing no automatic key detector is perfect.
- Embed detected key where supported by the output format and tagging library.
- Display detected key in the job row/history.
- Prefer an open-source engine rather than copying Rekordbox behavior.

Chosen efficient path:

1. Use `libkeyfinder` for stronger open-source key detection.
2. Accept and document the `libkeyfinder` GPLv3-or-later licensing implications.
3. Keep the current lightweight in-house detector only as a fallback or temporary bridge until `libkeyfinder` is integrated.

The project should document whichever key detection engine is selected, including license and binary/source availability.

The default key display should be standard notation such as `C# minor`. The UI should let users switch between standard notation and Camelot notation such as `12A`. Writing key tags into output files is useful but not required for the next implementation pass.

## Reports And Error Handling

Success reports should not clutter the output folder by default.

Optimized report behavior:

- Store compact job metadata in app data.
- Maintain artist/source/history indexes for search and duplicate awareness.
- Only show report actions when an error happens.
- Provide a user-facing error popup after final failure.

On failure:

1. Retry automatically in the backend up to 3 times.
2. If the 4th attempt fails, stop retrying.
3. Show a clear popup explaining what failed and why, using the best human-readable reason available.
4. Offer:
   - `Open GitHub Issue`
   - `Copy Report`
   - `Dismiss`

`Open GitHub Issue` should open a browser with a prefilled GitHub issue when possible. Users without a GitHub account may not be able to submit the issue, so `Copy Report` is required as a fallback.

`Copy Report` copies a structured text report to the clipboard. The user can paste it into a GitHub issue, email, chat, or any support thread.

The report should include:

- App version
- Operating system
- Source URL or input filename
- Platform/extractor
- Output format
- Tool versions
- Error message
- Retry history
- Source codec/bitrate if known
- Output path if created
- Relevant warnings

No anonymous direct report submission is planned because that would require a hosted backend or embedded GitHub credentials.

## Quality Report Data

Each completed job may store compact internal report data:

- Source URL
- Platform
- Extracted title
- Extracted artist
- Output filename
- Output format
- Source codec
- Source bitrate when available
- Output sample rate
- Output bit depth
- Channel layout
- Duration
- Leading/trailing silence trimmed
- Whether output is original file or converted fallback
- Whether source appears lossy
- Detected key
- Warnings

Future UI can expose this data in an advanced detail panel if needed.

## UI Direction

The app should remain a one-page workflow:

- Link input
- Format selector
- Output folder selector
- Download action
- Combined update area showing app/tool update status and exact pending updates
- Drag/drop audio input
- Job queue
- History/artist search area
- Automatic M3U status
- Key notation choice: standard or Camelot

The UI should be nicer and easier to understand than a raw developer tool, but it does not need enterprise-level polish.

Claude Code will redesign the app's look and feel for the best UI/UX experience before the public polished release.

## Architecture Direction

Near term:

- Keep the current Python/WebKit app functional.
- Add automatic M3U writing.
- Add retry policy.
- Add better error popups/report actions.
- Add artist/history metadata.
- Add a combined update area for app/tool updates.
- Integrate `libkeyfinder` for stronger key detection.

Cross-platform packaging:

- Evaluate Tauri as one practical option for shared UI and platform-specific builds, but do not treat it as mandatory.
- Bundle platform-specific sidecar binaries for `yt-dlp`, `ffmpeg`, and `ffprobe`.
- Keep release build scripts manual and reproducible.
- Include license notices for bundled tools and key detection dependencies.
- Optimize for one shared implementation with per-OS portable packages.
- Keep Python as the engine short term if it keeps momentum; replace it only if cross-platform packaging proves painful or unreliable.

Storage:

- Compact local metadata store under each OS app-data directory.
- Track jobs, artists, source URLs, output files, warnings, and errors.
- Do not require cloud sync.

GPU acceleration is not materially useful for this workflow. Audio download, demuxing, resampling, silence trim, key estimation, and WAV/AIFF encoding are CPU-bound but manageable. Battery life is best protected by avoiding unnecessary video downloads, avoiding needless re-encodes, limiting background analysis, and using efficient native process execution.

## Open Questions

1. Should the first portable release target macOS only, or macOS and Windows together?
2. Should Linux be included in the first portable release, or wait until Mac/Windows are solid?
3. Should the app show release notes after downloading a new portable build?
