# ForMyDJ UI Redesign — Design Spec

**Date:** 2026-04-30
**Status:** Approved (pending user review of this document)
**Scope:** Frontend only — `app/static/{index.html,styles.css,app.js}`. No backend, API, or pipeline changes.

## Goal

Replace the current dark-mode UI with a single-page, mid-tone, focused download surface. The user's core flow — paste a link, pick folder + format, hit download, watch history — should be the entire app. No tabs, no modals, no nested screens.

## Overrides to `docs/SPEC.md`

These supersede the existing spec where they conflict:

1. **M3U playlist support is removed.** No playlist export, no M3U list, no playlist UI. Users save flat files to a folder; that is the entire output model. The CLI/backend M3U code path may remain dormant but is unreachable from the UI.
2. **Cover art + song metadata are first-class in the history row.** Each completed/active job shows a 44px cover art thumb (when available from the source), title, artist, genre, duration, key, and format. If cover art is unavailable, the thumb slot is omitted (no placeholder block).
3. **Drag-and-drop is silent and window-wide.** The visible drop zone is removed. The entire window accepts file drops; there is no visible affordance for it.

All other items in `docs/SPEC.md` (output naming, formats, concurrency, retry policy, key detection, etc.) remain authoritative.

## Architecture

**Stack (unchanged):** Python backend at `127.0.0.1:8765` serving `app/static/` and exposing `/api/jobs`, `/api/output/choose`, `/api/upload`, `/api/cache/clear`. Frontend is plain HTML/CSS/JS — no framework, no build step.

**What changes:** the three files in `app/static/`. The polling cadence (`refreshJobs()` every 1500ms), the API contract, and the job model stay as-is.

**File-level boundaries:**
- `index.html` — semantic structure only. One `<main>` containing header, hero, divider, history list, errors tab. No inline styles, no inline scripts.
- `styles.css` — design tokens at `:root`, then layout, then components. Single file is fine; expected ~300–400 lines.
- `app.js` — three concerns kept as separate functions: state (in-memory session history + key-notation preference), rendering (DOM updates from state), I/O (fetch wrappers + drag-drop). No global mutation outside the state object.

## Visual Design

### Layout — Hero Stack

Centered single column, `max-width: 720px`, with an edge tab on the right side for errors.

```
┌─────────────────────────────────────────┐
│              ForMyDJ          [Std|Cam]│  ← header (title + key toggle)
├─────────────────────────────────────────┤
│                                         │
│   [paste a SoundCloud or YouTube link…] │  ← 44px paste field
│                                         │
│   [Folder ▾]  [Format ▾]  [Download]    │  ← controls row
│                                         │
│   ────── Recent downloads ──────        │  ← divider
│                                         │
│   [▦] Title          Artist · …  [done] │  ← history rows
│   [▦] Title          Artist · …  [64%]  │   (cover · meta · status)
│   [▦] Title          Artist · …  [done] │
│   [ ] Title          Artist · …  [fail] │   (no cover when unavailable)
│                                         │
└─────────────────────────────────────────┘  [errors▌1] ← pulsing tab
```

The errors tab is positioned `position: absolute; right: 0; top: ~100px;` relative to the column, with vertical "ERRORS" label and a circular badge showing count.

### Palette — Iron & Neon

Cool industrial grey base, electric cyan accent. Mid-tone (L*≈40–50% on the surface), comfortable in both bright and dim environments.

```css
:root {
  --p-bg:          #4a4f55;   /* page background */
  --p-surface:     #565b62;   /* cards, controls */
  --p-surface-2:   #62686f;   /* nested surfaces, cover placeholder */
  --p-edge:        #383d42;   /* borders */
  --p-text:        #ecedee;   /* primary text */
  --p-muted:       #a9afb4;   /* secondary text */
  --p-muted-2:     #828990;   /* tertiary / metadata */
  --p-accent:      #6dd4d8;   /* cyan — active, primary action */
  --p-accent-text: #102023;   /* on-accent text */
  --p-accent-soft: rgba(109, 212, 216, 0.18);  /* glow for nudge */
  --p-success:     #8ec196;   /* done pill */
  --p-warning:     #e0b370;   /* quality warnings */
  --p-danger:      #d28080;   /* failed pill, errors badge */
}
```

### Typography

System stack: `-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif`. No web fonts. Weights: 500 for titles, 600 for the key toggle's active state and the Download CTA, 400 elsewhere.

## Components

### Header
- Three-column grid: spacer · title · key-toggle.
- Title: "ForMyDJ", 16px, weight 600, centered.
- Key toggle: segmented control, two options `Std` / `Cam`, active state filled with accent. Persists across session (in-memory only). Toggling re-renders the displayed key in history rows; **does not reprocess any audio.**

### Paste field
- 44px tall, full width of column, single line.
- Placeholder: `paste a SoundCloud or YouTube link…`
- On paste of a valid SC/YT URL → focus stays, user clicks Download (or presses Enter) to start.

### Controls row
- Three-cell grid: `Folder ▾` (1.4fr) · `Format ▾` (1fr) · `Download` (auto).
- Folder button calls existing `/api/output/choose` to pick a directory; selected folder name displays in the button.
- Format dropdown: WAV (default), AIFF, MP3 320.
- Download is the accent-filled primary action.
- The `▾` glyph is unicode (U+25BE), not an emoji asset.

### Divider
- Thin horizontal lines flanking the label `RECENT DOWNLOADS` (uppercase, 10.5px, letter-spacing 0.16em, muted color).

### History row
- Grid: `44px cover · 1fr info · auto status`, gap 12px.
- **Cover:** 44×44 rounded square, source-provided cover art. **Omit the cover cell entirely when no cover is available.** Grid template falls back to `1fr auto` for that row.
- **Info column:**
  - Line 1: title, 13px, weight 500, ellipsis on overflow.
  - Line 2: `Artist · Genre · Duration · Key · Format`, 11px, muted-2 color, separator dots between fields. Missing fields render as `—`.
- **Status column:**
  - `done` pill (success color border + text)
  - `<n>%` pill with progress bar above (accent color)
  - `failed` pill (danger color border + text)
- Background: `--p-surface`, border `--p-edge`, radius 10px.

### Errors tab (subtle nudge)
- Position: `position: absolute; right: 0; top: 100px;` relative to the column wrap.
- Vertical "ERRORS" label (writing-mode: vertical-rl) + circular badge with count.
- Subtle pulsing glow: `box-shadow` animates `0` → `-8px 0 22px var(--p-accent-soft)` → `0` over 2.6s, infinite. The pulse is gentle — not a distracting flash.
- Click opens an inline error log (slides over from the right or expands below — implementation detail; default: expands inline below the history list).
- Hidden entirely when error count is 0.

### Drag-drop (invisible, window-wide)
- Whole `<body>` is the drop target.
- No visible drop zone, no hover state, no border highlight.
- On drop: existing `/api/upload` flow runs silently. If the dropped file isn't a valid audio source, the error appears in the errors tab (no inline alert).

## State & Data Flow

### Client state (in-memory, session-only)
```js
const state = {
  history: [],          // array of job records, oldest-first
  keyNotation: 'std',   // 'std' | 'cam'
  errors: [],           // array of error records
  outputFolder: null,   // string path
  format: 'wav',        // 'wav' | 'aiff' | 'mp3'
};
```

History is **never persisted.** On page reload / app restart, `state.history` starts empty. This is by design (user decision 3b).

### Polling
- `setInterval(refreshJobs, 1500)` — unchanged.
- `refreshJobs()` calls `/api/jobs`, merges results into `state.history` by job ID, re-renders.

### Camelot conversion
- A `keyToCamelot(stdKey)` map handles conversion at render time.
- Example: `F minor` → `4A`, `F♯ minor` → `11A`, `C major` → `8B`.
- When a key is missing or unparseable, render `—` (em dash) regardless of toggle.

## Error Handling

- Network/API errors → push to `state.errors`, increment errors badge, log to console.
- Job failures → row shows `failed` pill, error detail viewable via errors tab.
- Invalid drag-drop → error tab only, no UI alert.
- All user-visible error messages: short, plain language, no stack traces. Detailed traces stay in the errors tab.

## Testing

Manual smoke test (no automated tests required for this redesign — pure UI on existing API):

1. Paste an SC URL, choose folder, select WAV, click Download → row appears, progress runs to 100%, `done` pill shows.
2. Paste a YT URL, repeat → same behavior.
3. Trigger a known-bad URL → `failed` pill, errors badge increments, clicking the tab reveals the error.
4. Toggle Std ↔ Cam → key column updates instantly across all rows; no network calls fire.
5. Drag a local audio file onto the window → upload starts silently, row appears.
6. Restart the app → history list is empty.
7. Resize window narrow → column stays centered, no horizontal scroll, controls reflow if needed.
8. Visual: in bright daylight and in a dark room, the surface should feel comfortable in both. No glare, no muddy lows.

## Input Validation

Existing validation in `app.js` is preserved:
- Download button is disabled when no URL is entered.
- Invalid URL formats route to the errors tab on submit.
- Folder selection has no client-side validation; backend rejects unwritable paths and the error surfaces in the errors tab.

## Out of Scope

- Backend changes (Python, yt-dlp invocation, ffmpeg conversion, key detection)
- API contract changes
- Native macOS / SwiftUI work
- Light/dark mode toggle (intentionally absent — mid-tone is the only mode)
- M3U playlist UI (removed entirely)
- User preferences persistence (session-only by design)
- Authentication, multi-user, sync — none of these exist in this app

## Open Questions

None. All decisions captured above.
