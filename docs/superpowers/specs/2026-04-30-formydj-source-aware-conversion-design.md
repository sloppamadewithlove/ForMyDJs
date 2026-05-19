# ForMyDJ Source-Aware Conversion Design

**Goal:** Show users what kind of audio the URL actually contains (codec, bitrate, cover thumbnail, title) before they download, auto-pick a sensible output format based on whether the source is lossy or lossless, and embed cover art into the output file when the format supports it.

**Architecture:** Add a `GET /api/probe` endpoint that runs `yt-dlp -j` against the URL and returns codec/bitrate/duration/thumbnail. Frontend fires the probe on URL paste (debounced), populates a new "source card" UI element above the controls, and silently flips the format dropdown to MP3 320 when the source is lossy (stays at AIFF when lossless). Backend `convert_audio` is restructured to embed cover art per output format.

**Tech stack:** Python 3 stdlib HTTP server (existing), vanilla JS frontend, ffmpeg, yt-dlp. No new dependencies.

---

## 1. Default format change: WAV → AIFF

The app currently opens with WAV selected. Change to AIFF.

- `app/static/app.js` — initial `state.format` from `'wav'` → `'aiff'`.
- `app/static/index.html` — add `selected` attribute to the AIFF `<option>`. Keep current option order. Change the visible `<span class="value" id="formatValue">WAV</span>` to `AIFF`.
- `app/server.py` — both `do_POST` defaults (`payload.get("format") or "wav"` in `/api/jobs` and `/api/upload`) change from `"wav"` to `"aiff"`. This way the server's fallback matches the frontend default if a request omits the field.

## 2. New endpoint: `GET /api/probe?url=...`

Runs `yt-dlp -j` on the URL with a 10-second timeout. Returns:

```json
{
  "title": "Hold On Tight",
  "artist": "Hidde van Wee",
  "duration": 287.4,
  "codec": "opus",
  "bitrate": 128000,
  "thumbnail": "https://...jpg",
  "lossy": true,
  "ext": "opus"
}
```

`lossy` is computed server-side from a known codec set (`mp3`, `aac`, `opus`, `vorbis`, `m4a`). If `codec` is missing or unknown, `lossy` defaults to `true` — better to flip to MP3 320 than silently upcode to AIFF.

On failure (timeout, geo-block, private link, rate limit), return HTTP 502 with the yt-dlp error message in the body. The endpoint never blocks the existing `/api/jobs` flow — Download still works without a probe.

## 3. Cover art: pass thumbnail through the pipeline

Currently `download_source` writes a thumbnail next to the audio file via `--write-thumbnail`, but never returns its path, and `convert_audio` strips all video streams via `-vn`. Cover art is being downloaded and discarded.

Changes:

- `download_source` returns a 3-tuple: `(audio_path, info_path, thumbnail_path)`. Find the thumbnail by extension scan in the workdir. Add `--convert-thumbnails jpg` to the yt-dlp args so YouTube's WebP thumbnails come out as JPG (universally embeddable).
- `convert_audio` accepts a `thumbnail_path` arg. Drops the unconditional `-vn`. Branches on output format:
  - **MP3:** dual-input ffmpeg, embed via ID3v2 APIC. Args include `-i thumbnail`, `-map 0:a -map 1:v`, `-id3v2_version 3`, `-metadata:s:v title="Album cover"`.
  - **AIFF:** dual-input ffmpeg, embed via ID3 chunk. Args include `-i thumbnail`, `-map 0:a -map 1:v`, `-write_id3v2 1`, `-c:a pcm_s16be -f aiff`.
  - **WAV:** unchanged. Re-apply `-vn`. No cover art (RIFF has no portable standard, sidecar JPG explicitly declined).
- `process_job` threads `thumbnail_path` from `download_source` into the conversion call. For uploaded files (`input_kind == "file"`), `thumbnail_path` is `None`.
- If `thumbnail_path` is `None` for any reason (probe didn't fire, yt-dlp failed to fetch the thumb, upload flow), the convert function falls back to audio-only output for that format. No error — just no cover.

## 4. New format option: "Original"

Adds a 4th option to the format dropdown. When picked, the source file's container and codec are preserved — no re-encode, no quality change.

- Frontend: `<option value="original">Original</option>` added last. `FORMAT_LABELS.original = 'Original'`.
- Backend: new `copy_original(source_path, metadata, output_dir, thumbnail_path)` function. Uses `ffmpeg -c:a copy` to remux (audio is bit-identical) and embeds cover art via `attached_pic` disposition for containers that support it (Opus/Ogg, MP3, M4A, FLAC). Output extension matches source. `process_job` routes to `copy_original` when `output_format == "original"`, otherwise to `convert_audio`.
- For SoundCloud/YouTube sources this typically produces a `.opus` file. Rekordbox may reject `.opus` — that's the user's call. The source card's codec pill is the warning. No additional UI guard.

## 5. Frontend: source card

A new section between the paste form and the "Recent downloads" divider. Hidden by default; shown when probe returns successfully.

```html
<section class="fm-source-card" id="sourceCard" hidden aria-label="Source preview">
  <div class="fm-source-cover"><img id="sourceCover" alt="" /></div>
  <div class="fm-source-info">
    <div class="fm-source-title" id="sourceTitle">—</div>
    <div class="fm-source-meta" id="sourceMeta">—</div>
  </div>
  <div class="fm-source-pill" id="sourcePill">—</div>
</section>
```

Layout: `grid-template-columns: 56px minmax(0, 1fr) auto`, matching the existing palette and row card style. Title and meta truncate with ellipsis. The codec pill on the right gets a color modifier — `lossy` (warning amber) or `lossless` (success green).

Pill format: `${CODEC} ${KBPS}` (e.g., `OPUS 128`, `FLAC 1411`). Falls back to just codec if bitrate is missing, or `—` if both are.

## 6. Frontend: probe pipeline

The existing `linkInput` `'input'` listener already toggles the Download button. Extend it to:

1. Cancel any in-flight probe request (via `AbortController`).
2. Cancel any pending debounce timer.
3. If the input is empty or doesn't start with `http`, hide the source card.
4. Otherwise, schedule a probe request 350ms in the future.

Probe handler:

```js
async function probeUrl(url) {
  probeAbort = new AbortController();
  try {
    const data = await fetchJson(`/api/probe?url=${encodeURIComponent(url)}`, { signal: probeAbort.signal });
    populateSourceCard(data);
    applySmartFormat(data);
  } catch (err) {
    if (err.name !== 'AbortError') hideSourceCard();
  }
}

function applySmartFormat(data) {
  const next = data.lossy ? 'mp3' : 'aiff';
  if (state.format === next) return;
  setFormat(next);
  els.formatSelect.value = next;
  els.formatValue.textContent = FORMAT_LABELS[next];
}
```

Smart-flip is silent — no extra text on the card explaining the change. The codec pill and the dropdown's new value are the only signals.

On form submit, hide the card after clearing the input. The card reappears on the next paste.

## 7. Format / cover art matrix

| Output | Audio quality | Cover art | Mechanism |
|--------|---------------|-----------|-----------|
| MP3 320 | Re-encoded lossy | Embedded | ID3v2 APIC, dual-input ffmpeg |
| AIFF | Re-encoded lossless PCM | Embedded | ID3 chunk via `-write_id3v2 1`, dual-input ffmpeg |
| WAV | Re-encoded lossless PCM | None | RIFF has no portable cover standard |
| Original | Bit-identical to source | Embedded if container supports | `ffmpeg -c:a copy` remux with `attached_pic` |

## 8. Edge cases

- **Probe times out / fails**: backend returns HTTP 502, frontend hides the card. Download still works with whatever format is selected.
- **Probe returns no codec**: `lossy=true` (defensive — flip to MP3 320 rather than silently AIFF-upcode).
- **User pastes faster than debounce**: `AbortController` cancels in-flight request, only the latest probe completes.
- **Thumbnail fetch fails inside yt-dlp**: `download_source` returns `thumbnail_path=None`, conversion proceeds without cover art.
- **Form submit during in-flight probe**: probe is left to complete (or fail silently), card is hidden by the submit handler regardless.
- **Uploaded local file**: `input_kind == "file"` skips the probe entirely. Smart-flip doesn't fire. No cover art (uploads don't carry thumbnails through this flow).
- **Lossy source warning** (server.py `warnings_for`): preserved as-is. With smart-flip it now only triggers when the user manually overrides AIFF/WAV after a lossy probe — that's the intended signal.

## 9. Out of scope

- Sidecar JPG for WAV outputs (explicitly declined).
- Toggle to disable smart-flip ("never auto-change my format").
- Probe result caching across pastes.
- Re-probing when the dropdown changes.
- Confirmation dialog for lossy → lossless conversions.
- "Original" badge or icon in the dropdown (just plain text).
- Rekordbox/Serato/Traktor-specific compatibility hints in the UI.

## 10. Files touched

- `app/server.py` — `probe_url`, `LOSSY_CODECS`, `/api/probe` route, refactored `download_source`/`convert_audio`/`process_job`, new `copy_original`. ~80 lines.
- `app/static/index.html` — source card markup, Original option, AIFF default. ~15 lines.
- `app/static/styles.css` — source card styles. ~50 lines.
- `app/static/app.js` — probe pipeline, card population, smart-flip, format default. ~70 lines.

Roughly 215 lines across four files.

## 11. Manual smoke test (post-implementation)

1. Open app — dropdown shows AIFF.
2. Paste `https://soundcloud.com/hiddevanwee/hold-on-tight` — card appears with cover, title, artist; pill says `OPUS 128` (amber); dropdown silently flips to MP3 320.
3. Click Download — output is MP3 320 with embedded cover. Verify in Finder Get Info preview and Rekordbox import.
4. Manually pick AIFF, paste same URL again, Download — output is AIFF with embedded cover. Verify cover in Rekordbox.
5. Manually pick WAV, Download — WAV file, no cover, no sidecar JPG.
6. Manually pick Original, Download — `.opus` file with embedded cover. Rekordbox may reject; that's expected.
7. Paste a Bandcamp link with FLAC source — pill says `FLAC ...` (green), dropdown stays AIFF.
8. Paste a malformed or private URL — card disappears, Download still works.
9. Drag-drop a local file — uploads as AIFF, no cover.
