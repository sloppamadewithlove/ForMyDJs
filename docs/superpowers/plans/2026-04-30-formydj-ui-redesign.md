# ForMyDJ UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace ForMyDJ's existing dark-mode UI with a single-page Hero Stack layout in the Iron & Neon palette — paste field, folder + format + download row, history list with cover art and metadata, and a pulsing errors tab on the right edge.

**Architecture:** Frontend-only redesign of `app/static/{index.html, styles.css, app.js}`. Backend (Python at `127.0.0.1:8765`), API contracts (`/api/jobs`, `/api/output/choose`, `/api/upload`, `/api/cache/clear`), and the yt-dlp/ffmpeg pipeline are untouched. The new `app.js` reorganizes around three concerns — state, rendering, I/O — with a single `state` object as the source of truth. All DOM updates use the safe DOM-creation API (`document.createElement`, `textContent`, `replaceChildren`) — no string-based HTML insertion.

**Tech Stack:** Vanilla HTML/CSS/JS. No framework, no build step, no package manager. System fonts only. No automated test framework — verification is manual smoke testing per the spec.

**Spec:** [`docs/superpowers/specs/2026-04-30-formydj-ui-redesign-design.md`](../specs/2026-04-30-formydj-ui-redesign-design.md)

---

## File Structure

| File | Responsibility | Approx. Size |
|------|----------------|--------------|
| `app/static/index.html` | Semantic structure: header, hero, divider, history, errors tab. No inline styles or scripts. | ~50 lines |
| `app/static/styles.css` | Design tokens at `:root`, then layout, then components. Single file. | ~350 lines |
| `app/static/app.js` | One `state` object, three concerns kept as separate function groups (state mutators, renderers, I/O). DOM-creation API only — no string interpolation into the DOM. | ~280 lines |

**Existing files to fully replace:** all three above. **No new files. No deletions of other files.**

**Files NOT touched:** `app/server.py`, `app/desktop.py`, `scripts/*`, `docs/SPEC.md` (the spec override is captured in the redesign spec, not edited inline).

---

## Development Loop

For every task that produces a visible/behavioral change:

1. Make the edit.
2. Restart the dev server: `./scripts/run-local.sh` (Ctrl-C the previous run first).
3. Open `http://127.0.0.1:8765` in any browser (Safari, Chrome, etc.).
4. Verify the acceptance criteria.
5. Commit.

You don't need to rebuild the macOS app between tasks — the static files are served live by the Python engine.

---

## Task 1: Replace HTML with Hero Stack scaffolding

**Files:**
- Modify: `app/static/index.html` (full replacement)

- [ ] **Step 1: Replace `index.html` with the new structure**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ForMyDJ</title>
    <link rel="stylesheet" href="/styles.css" />
  </head>
  <body>
    <main class="fm-wrap">
      <header class="fm-header">
        <div class="fm-spacer"></div>
        <h1 class="fm-title">ForMyDJ</h1>
        <div class="fm-keytoggle" role="group" aria-label="Key notation">
          <button type="button" class="opt active" data-key="std">Std</button>
          <button type="button" class="opt" data-key="cam">Cam</button>
        </div>
      </header>

      <section class="fm-hero" aria-label="Download controls">
        <form id="linkForm">
          <input
            id="linkInput"
            class="fm-paste"
            type="url"
            placeholder="paste a SoundCloud or YouTube link…"
            autocomplete="off"
          />
          <div class="fm-controls">
            <button id="chooseOutput" type="button" class="ctl">
              <span class="lbl">Folder:</span>
              <span id="outputName">Choose folder</span>
              <span class="caret">▾</span>
            </button>
            <label class="ctl" for="formatSelect">
              <span class="lbl">Format:</span>
              <select id="formatSelect" name="format">
                <option value="wav">WAV</option>
                <option value="aiff">AIFF</option>
                <option value="mp3">MP3 320</option>
              </select>
              <span class="caret">▾</span>
            </label>
            <button id="downloadBtn" type="submit" class="ctl download" disabled>Download</button>
          </div>
          <input id="outputDir" type="hidden" />
        </form>
      </section>

      <div class="fm-divider">
        <div class="line"></div>
        <span>Recent downloads</span>
        <div class="line"></div>
      </div>

      <section id="history" class="fm-history" aria-label="Recent downloads"></section>

      <button id="errorsTab" class="fm-tab" type="button" hidden aria-expanded="false">
        <span class="tablbl">errors</span>
        <span id="errorsBadge" class="badge">0</span>
      </button>

      <section id="errorsPanel" class="fm-errors-panel" hidden aria-label="Error log"></section>
    </main>

    <script src="/app.js"></script>
  </body>
</html>
```

- [ ] **Step 2: Restart the server and verify the page loads**

Run:
```bash
./scripts/run-local.sh
```
Open `http://127.0.0.1:8765`.
Expected: page loads with no console errors. Visuals are unstyled (default browser styles) because the new CSS isn't written yet. The title "ForMyDJ", the "Std/Cam" buttons, paste input, folder/format/download controls, and the "Recent downloads" divider should all be visible as plain HTML.

- [ ] **Step 3: Commit**

```bash
git add app/static/index.html
git commit -m "feat(ui): replace HTML scaffolding with Hero Stack structure"
```

---

## Task 2: Replace `styles.css` with design tokens and base layout

**Files:**
- Modify: `app/static/styles.css` (full replacement)

- [ ] **Step 1: Replace `styles.css` with tokens + base + wrap**

```css
/* ForMyDJ — Iron & Neon palette + Hero Stack layout */

:root {
  --p-bg:          #4a4f55;
  --p-surface:     #565b62;
  --p-surface-2:   #62686f;
  --p-edge:        #383d42;
  --p-text:        #ecedee;
  --p-muted:       #a9afb4;
  --p-muted-2:     #828990;
  --p-accent:      #6dd4d8;
  --p-accent-text: #102023;
  --p-accent-soft: rgba(109, 212, 216, 0.18);
  --p-success:     #8ec196;
  --p-warning:     #e0b370;
  --p-danger:      #d28080;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  min-height: 100vh;
  background: var(--p-bg);
  color: var(--p-text);
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
  font-size: 13px;
}

button, input, select {
  font: inherit;
  color: inherit;
}

.fm-wrap {
  position: relative;
  max-width: 720px;
  margin: 24px auto;
  background: var(--p-bg);
  border: 1px solid var(--p-edge);
  border-radius: 12px;
  overflow: visible;
}
```

- [ ] **Step 2: Verify in browser**

Reload `http://127.0.0.1:8765`.
Expected: page background is mid-tone industrial grey (`#4a4f55`). A bordered rounded rectangle is centered with `max-width: 720px`. The HTML elements inside still look mostly default (header, paste field, etc.) because component styles aren't written yet. No console errors.

- [ ] **Step 3: Commit**

```bash
git add app/static/styles.css
git commit -m "feat(ui): add Iron & Neon design tokens and page wrap"
```

---

## Task 3: Style the header (title + Std/Cam toggle)

**Files:**
- Modify: `app/static/styles.css` (append)

- [ ] **Step 1: Append header styles**

Add to the bottom of `app/static/styles.css`:

```css
/* Header */
.fm-header {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 18px 22px 14px;
  border-bottom: 1px solid var(--p-edge);
}

.fm-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.01em;
  text-align: center;
}

.fm-keytoggle {
  justify-self: end;
  display: inline-grid;
  grid-template-columns: 1fr 1fr;
  background: var(--p-surface);
  border: 1px solid var(--p-edge);
  border-radius: 7px;
  overflow: hidden;
  font-size: 11px;
}

.fm-keytoggle .opt {
  padding: 4px 10px;
  background: transparent;
  border: 0;
  color: var(--p-muted);
  cursor: pointer;
  text-align: center;
}

.fm-keytoggle .opt.active {
  background: var(--p-accent);
  color: var(--p-accent-text);
  font-weight: 600;
}
```

- [ ] **Step 2: Verify in browser**

Reload. Expected:
- "ForMyDJ" title is centered, 16px, white-ish on grey.
- "Std / Cam" segmented control sits in the top-right with `Std` filled cyan and `Cam` muted.
- A 1px edge line separates the header from the body.

- [ ] **Step 3: Commit**

```bash
git add app/static/styles.css
git commit -m "feat(ui): style header with title and Std/Cam toggle"
```

---

## Task 4: Style the hero (paste field + controls row)

**Files:**
- Modify: `app/static/styles.css` (append)

- [ ] **Step 1: Append hero styles**

Add to the bottom of `app/static/styles.css`:

```css
/* Hero */
.fm-hero { padding: 18px 22px 8px; }

.fm-paste {
  width: 100%;
  background: var(--p-surface);
  border: 1px solid var(--p-edge);
  border-radius: 10px;
  height: 44px;
  padding: 0 14px;
  color: var(--p-text);
  font-size: 13px;
  outline: none;
}

.fm-paste::placeholder { color: var(--p-muted); }
.fm-paste:focus { border-color: var(--p-accent); }

.fm-controls {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) auto;
  gap: 8px;
  margin-top: 10px;
}

.fm-controls .ctl {
  background: var(--p-surface);
  border: 1px solid var(--p-edge);
  border-radius: 8px;
  height: 38px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  font-size: 12.5px;
  color: var(--p-text);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  cursor: pointer;
}

.fm-controls .ctl .lbl {
  color: var(--p-muted);
  margin-right: 6px;
  font-size: 11.5px;
}

.fm-controls .ctl .caret {
  margin-left: auto;
  color: var(--p-muted);
}

.fm-controls .ctl select {
  background: transparent;
  border: 0;
  color: var(--p-text);
  font-size: 12.5px;
  cursor: pointer;
  padding: 0;
  margin-right: 6px;
  appearance: none;
  -webkit-appearance: none;
}

.fm-controls .download {
  background: var(--p-accent);
  color: var(--p-accent-text);
  border-color: transparent;
  font-weight: 600;
  padding: 0 18px;
  justify-content: center;
}

.fm-controls .download:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

- [ ] **Step 2: Verify in browser**

Reload. Expected:
- A 44px-tall paste field with cyan focus ring on click.
- A row below with three controls: `Folder: …▾`, `Format: WAV ▾`, and an accent-cyan `Download` button.
- Download button looks dimmed (disabled state) because no link entered yet.

- [ ] **Step 3: Commit**

```bash
git add app/static/styles.css
git commit -m "feat(ui): style paste field and controls row"
```

---

## Task 5: Style the divider, history rows, cover art, info, status, and progress bar

**Files:**
- Modify: `app/static/styles.css` (append)

- [ ] **Step 1: Append history-related styles**

Add to the bottom of `app/static/styles.css`:

```css
/* Divider */
.fm-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--p-muted);
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  padding: 18px 22px 6px;
}

.fm-divider .line { flex: 1; height: 1px; background: var(--p-edge); }

/* History */
.fm-history { padding: 0 14px 18px; }

.fm-empty {
  text-align: center;
  color: var(--p-muted);
  font-size: 12px;
  padding: 18px 0;
}

.fm-row {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  background: var(--p-surface);
  border: 1px solid var(--p-edge);
  border-radius: 10px;
  padding: 8px 12px 8px 8px;
  margin: 6px 0;
}

.fm-row.no-cover {
  grid-template-columns: minmax(0, 1fr) auto;
  padding-left: 12px;
}

.fm-cover {
  width: 44px;
  height: 44px;
  border-radius: 6px;
  background: var(--p-surface-2);
  overflow: hidden;
  position: relative;
}

.fm-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.fm-info { min-width: 0; }

.fm-info .fm-title-line {
  font-size: 13px;
  font-weight: 500;
  color: var(--p-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fm-info .fm-meta-line {
  font-size: 11px;
  color: var(--p-muted-2);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fm-info .fm-meta-line .sep {
  color: var(--p-muted-2);
  margin: 0 6px;
  opacity: 0.5;
}

.fm-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}

.fm-status .pill {
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid var(--p-edge);
  font-size: 10.5px;
  background: transparent;
  color: var(--p-muted);
}

.fm-status .pill.done { color: var(--p-success); border-color: var(--p-success); }
.fm-status .pill.run  { color: var(--p-accent);  border-color: var(--p-accent); }
.fm-status .pill.fail { color: var(--p-danger);  border-color: var(--p-danger); }

.fm-progress {
  width: 80px;
  height: 4px;
  background: var(--p-surface-2);
  border-radius: 999px;
  overflow: hidden;
}

.fm-progress > div {
  height: 100%;
  background: var(--p-accent);
}
```

- [ ] **Step 2: Verify in browser**

Reload. Expected:
- The "Recent downloads" label sits between two thin horizontal lines, uppercase + tracked.
- Below it: empty state will show once `app.js` is wired (currently the section is just empty).
- No errors in console.

- [ ] **Step 3: Commit**

```bash
git add app/static/styles.css
git commit -m "feat(ui): style divider, history rows, cover, status, progress"
```

---

## Task 6: Style the errors tab and pulse animation

**Files:**
- Modify: `app/static/styles.css` (append)

- [ ] **Step 1: Append errors tab + animation styles**

Add to the bottom of `app/static/styles.css`:

```css
/* Errors tab (right edge, pulsing nudge) */
.fm-tab {
  position: absolute;
  top: 100px;
  right: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 6px;
  min-width: 28px;
  background: var(--p-surface-2);
  border: 1px solid var(--p-edge);
  border-right: none;
  border-radius: 8px 0 0 8px;
  font-size: 10.5px;
  color: var(--p-muted);
  cursor: pointer;
  box-shadow: 0 0 0 0 var(--p-accent-soft);
  animation: fm-nudge 2.6s ease-in-out infinite;
}

.fm-tab[hidden] { display: none; }

.fm-tab .tablbl {
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 9.5px;
}

.fm-tab .badge {
  background: var(--p-accent);
  color: var(--p-accent-text);
  font-weight: 700;
  font-size: 10px;
  width: 18px;
  height: 18px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
}

@keyframes fm-nudge {
  0%, 100% { box-shadow: 0 0 0 0 var(--p-accent-soft); }
  50%      { box-shadow: -8px 0 22px 0 var(--p-accent-soft); }
}

/* Errors panel (inline expansion below history) */
.fm-errors-panel {
  margin: 0 14px 18px;
  padding: 12px 14px;
  background: var(--p-surface);
  border: 1px solid var(--p-edge);
  border-radius: 10px;
  font-size: 12px;
  color: var(--p-text);
}

.fm-errors-panel[hidden] { display: none; }

.fm-errors-panel h3 {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--p-danger);
}

.fm-errors-panel .err-item {
  padding: 6px 0;
  border-bottom: 1px solid var(--p-edge);
  color: var(--p-muted);
}

.fm-errors-panel .err-item:last-child { border-bottom: none; }
```

- [ ] **Step 2: Verify in browser**

Reload. Expected:
- The errors tab is hidden (no errors yet — `hidden` attribute set in HTML).
- No console errors.

To temporarily verify visuals, edit `index.html` to remove the `hidden` attribute on `#errorsTab`. Reload — the tab should appear on the right edge with a gently pulsing soft cyan glow expanding outward and fading. Re-add `hidden` after verifying.

- [ ] **Step 3: Commit**

```bash
git add app/static/styles.css
git commit -m "feat(ui): style errors tab with pulsing nudge animation"
```

---

## Task 7: Replace `app.js` with state object and I/O bootstrap

**Files:**
- Modify: `app/static/app.js` (full replacement)

- [ ] **Step 1: Replace `app.js` with the new core**

This bootstrap gets the state, element refs, I/O wrappers, and form wiring in place. Rendering uses the safe DOM-creation API (`createElement`, `textContent`, `replaceChildren`) — no string interpolation into the DOM. Render functions are stubs that get filled in by Tasks 8 and 10.

```javascript
/**
 * @typedef {Object} Job
 * @property {string} id
 * @property {string} status
 * @property {string} [title]
 * @property {string} [artist]
 * @property {string} [genre]
 * @property {number} [duration_seconds]
 * @property {string} [estimated_key]
 * @property {string} [cover_url]
 * @property {string} format
 * @property {string} progress
 * @property {string} [output_path]
 * @property {string} [input_value]
 * @property {string} [error]
 * @property {string[]} [warnings]
 */

const state = {
  /** @type {Job[]} */ history: [],
  /** @type {'std'|'cam'} */ keyNotation: 'std',
  /** @type {{ when: number, message: string }[]} */ errors: [],
  /** @type {string|null} */ outputFolder: null,
  /** @type {'wav'|'aiff'|'mp3'} */ format: 'wav',
  errorsPanelOpen: false,
};

const els = {
  linkForm:     document.getElementById('linkForm'),
  linkInput:    document.getElementById('linkInput'),
  formatSelect: document.getElementById('formatSelect'),
  downloadBtn:  document.getElementById('downloadBtn'),
  outputDir:    document.getElementById('outputDir'),
  chooseOutput: document.getElementById('chooseOutput'),
  outputName:   document.getElementById('outputName'),
  history:      document.getElementById('history'),
  keyToggle:    document.querySelectorAll('.fm-keytoggle .opt'),
  errorsTab:    document.getElementById('errorsTab'),
  errorsBadge:  document.getElementById('errorsBadge'),
  errorsPanel:  document.getElementById('errorsPanel'),
};

/* -------- I/O -------- */

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

async function refreshJobs() {
  try {
    const data = await fetchJson('/api/jobs');
    if (!state.outputFolder && data.default_output) {
      setOutputFolder(data.default_output);
    }
    state.history = data.jobs || [];
    renderHistory();
  } catch (err) {
    pushError(err.message);
  }
}

async function submitLink(link) {
  await fetchJson('/api/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      link,
      format: state.format,
      output_dir: state.outputFolder,
    }),
  });
  refreshJobs();
}

async function chooseOutputFolder() {
  els.chooseOutput.disabled = true;
  const previous = els.outputName.textContent;
  els.outputName.textContent = 'Choosing…';
  try {
    const data = await fetchJson('/api/output/choose', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_path: state.outputFolder }),
    });
    if (data.path) {
      setOutputFolder(data.path);
    } else {
      els.outputName.textContent = previous;
    }
  } catch (err) {
    els.outputName.textContent = previous;
    pushError(err.message);
  } finally {
    els.chooseOutput.disabled = false;
  }
}

/* -------- State mutators -------- */

function setOutputFolder(path) {
  state.outputFolder = path;
  els.outputDir.value = path;
  els.outputName.textContent = folderName(path);
  els.chooseOutput.title = path;
}

function setFormat(value) {
  state.format = /** @type {'wav'|'aiff'|'mp3'} */ (value);
}

function pushError(message) {
  state.errors.push({ when: Date.now(), message });
  renderErrors();
}

/* -------- Rendering (stubs — filled in Tasks 8 & 10) -------- */

function renderHistory() {
  els.history.replaceChildren();
  if (state.history.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'fm-empty';
    empty.textContent = 'Paste a link to start.';
    els.history.appendChild(empty);
  }
  // Real row rendering added in Task 8.
}

function renderErrors() {
  const count = state.errors.length;
  els.errorsBadge.textContent = String(count);
  els.errorsTab.hidden = count === 0;
  // Panel rendering added in Task 10.
}

/* -------- Helpers -------- */

function folderName(path) {
  return path.split('/').filter(Boolean).pop() || path;
}

/* -------- Wiring -------- */

els.linkInput.addEventListener('input', () => {
  els.downloadBtn.disabled = els.linkInput.value.trim().length === 0;
});

els.linkForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const link = els.linkInput.value.trim();
  if (!link) return;
  els.linkInput.value = '';
  els.downloadBtn.disabled = true;
  await submitLink(link);
});

els.formatSelect.addEventListener('change', (event) => {
  setFormat(/** @type {HTMLSelectElement} */ (event.target).value);
});

els.chooseOutput.addEventListener('click', chooseOutputFolder);

refreshJobs();
setInterval(refreshJobs, 1500);
```

- [ ] **Step 2: Verify in browser**

Reload `http://127.0.0.1:8765`. Expected:
- The folder button shows the default output folder name (from `/api/jobs`).
- "Paste a link to start." empty state visible in history area.
- Typing a URL into the paste field enables the Download button. Clearing it disables again.
- Clicking the folder button opens the native macOS folder picker (server handles this).
- Clicking Download with a real SC/YT URL fires `POST /api/jobs` and the empty state stays (rendering is a stub).
- No console errors.

- [ ] **Step 3: Commit**

```bash
git add app/static/app.js
git commit -m "feat(ui): rewrite app.js with state object and I/O bootstrap"
```

---

## Task 8: Render history rows with metadata, cover art, and key notation

**Files:**
- Modify: `app/static/app.js` (replace `renderHistory` body and add row builders)

- [ ] **Step 1: Replace the `renderHistory` stub and add helpers**

Find this block in `app/static/app.js`:

```javascript
function renderHistory() {
  els.history.replaceChildren();
  if (state.history.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'fm-empty';
    empty.textContent = 'Paste a link to start.';
    els.history.appendChild(empty);
  }
  // Real row rendering added in Task 8.
}
```

Replace it with:

```javascript
function renderHistory() {
  els.history.replaceChildren();
  if (state.history.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'fm-empty';
    empty.textContent = 'Paste a link to start.';
    els.history.appendChild(empty);
    return;
  }
  for (const job of state.history) {
    els.history.appendChild(buildRow(job));
  }
}

function buildRow(job) {
  const article = document.createElement('article');
  article.className = 'fm-row';

  const hasCover = Boolean(job.cover_url);
  if (hasCover) {
    const cover = document.createElement('div');
    cover.className = 'fm-cover';
    const img = document.createElement('img');
    img.src = job.cover_url;
    img.alt = '';
    cover.appendChild(img);
    article.appendChild(cover);
  } else {
    article.classList.add('no-cover');
  }

  const info = document.createElement('div');
  info.className = 'fm-info';

  const titleLine = document.createElement('div');
  titleLine.className = 'fm-title-line';
  titleLine.textContent = job.title || job.input_value || 'Untitled';
  info.appendChild(titleLine);

  const metaLine = document.createElement('div');
  metaLine.className = 'fm-meta-line';
  buildMetaParts(metaLine, job);
  info.appendChild(metaLine);

  article.appendChild(info);

  const status = document.createElement('div');
  status.className = 'fm-status';
  buildStatus(status, job);
  article.appendChild(status);

  return article;
}

function buildMetaParts(container, job) {
  const parts = [
    job.artist || '—',
    job.genre || null,
    formatDuration(job.duration_seconds),
    formatKey(job.estimated_key, state.keyNotation),
    (job.format || '').toUpperCase() || null,
  ].filter(Boolean);

  parts.forEach((part, index) => {
    const span = document.createElement('span');
    span.textContent = String(part);
    container.appendChild(span);
    if (index < parts.length - 1) {
      const sep = document.createElement('span');
      sep.className = 'sep';
      sep.textContent = '·';
      container.appendChild(sep);
    }
  });
}

function buildStatus(container, job) {
  if (job.status === 'finished') {
    container.appendChild(makePill('done', 'done'));
    return;
  }
  if (job.status === 'failed') {
    container.appendChild(makePill('fail', 'failed'));
    return;
  }
  const pct = parsePercent(job.progress);
  if (pct !== null) {
    const bar = document.createElement('div');
    bar.className = 'fm-progress';
    const fill = document.createElement('div');
    fill.style.width = `${pct}%`;
    bar.appendChild(fill);
    container.appendChild(bar);
    container.appendChild(makePill('run', `${pct}%`));
    return;
  }
  container.appendChild(makePill('', job.status || 'queued'));
}

function makePill(modifier, label) {
  const pill = document.createElement('span');
  pill.className = modifier ? `pill ${modifier}` : 'pill';
  pill.textContent = label;
  return pill;
}

function parsePercent(progress) {
  if (!progress) return null;
  const match = String(progress).match(/(\d+(?:\.\d+)?)\s*%/);
  return match ? Math.round(parseFloat(match[1])) : null;
}

function formatDuration(seconds) {
  if (!seconds || !Number.isFinite(seconds)) return null;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

const CAMELOT = {
  'C major': '8B',  'A minor':  '8A',
  'G major': '9B',  'E minor':  '9A',
  'D major': '10B', 'B minor':  '10A',
  'A major': '11B', 'F# minor': '11A', 'F♯ minor': '11A',
  'E major': '12B', 'C# minor': '12A', 'C♯ minor': '12A',
  'B major': '1B',  'G# minor': '1A',  'G♯ minor': '1A',
  'F# major': '2B', 'F♯ major': '2B',  'D# minor': '2A', 'D♯ minor': '2A', 'Eb minor': '2A',
  'Db major': '3B', 'C♯ major': '3B',  'Bb minor': '3A', 'A♯ minor': '3A',
  'Ab major': '4B', 'G♯ major': '4B',  'F minor':  '4A',
  'Eb major': '5B', 'D♯ major': '5B',  'C minor':  '5A',
  'Bb major': '6B', 'A♯ major': '6B',  'G minor':  '6A',
  'F major': '7B',  'D minor':  '7A',
};

function formatKey(estimatedKey, notation) {
  if (!estimatedKey) return '—';
  if (notation === 'std') return estimatedKey;
  return CAMELOT[estimatedKey] || estimatedKey;
}
```

- [ ] **Step 2: Verify in browser**

Submit a real SoundCloud or YouTube URL. Expected:
- Row appears with title, artist, genre, duration, key, and format separated by `·` dots.
- If the source has cover art metadata, a 44px thumbnail is on the left.
- If no cover art, the cover cell is omitted entirely (row uses 2 columns instead of 3).
- During download: progress bar + `<n>%` pill.
- On completion: `done` pill (green border).
- On failure: `failed` pill (red border).

- [ ] **Step 3: Commit**

```bash
git add app/static/app.js
git commit -m "feat(ui): render history rows with cover, metadata, status, key"
```

---

## Task 9: Wire Std↔Cam toggle (display-only, no reprocess)

**Files:**
- Modify: `app/static/app.js` (add toggle wiring)

- [ ] **Step 1: Add toggle handler before the `refreshJobs()` bootstrap call**

Find this near the bottom of `app/static/app.js`:

```javascript
els.chooseOutput.addEventListener('click', chooseOutputFolder);

refreshJobs();
```

Insert toggle wiring between them:

```javascript
els.chooseOutput.addEventListener('click', chooseOutputFolder);

els.keyToggle.forEach((opt) => {
  opt.addEventListener('click', () => {
    const next = opt.dataset.key;
    if (next !== 'std' && next !== 'cam') return;
    if (state.keyNotation === next) return;
    state.keyNotation = next;
    els.keyToggle.forEach((o) => o.classList.toggle('active', o.dataset.key === next));
    renderHistory();
  });
});

refreshJobs();
```

- [ ] **Step 2: Verify in browser**

With at least one completed download in history (run a real download first if needed):
- Click `Cam`. Key column updates immediately (e.g., `F minor` → `4A`).
- Click `Std`. Key column reverts.
- Toggle button styling: active option has cyan background, inactive is muted.
- Open Network tab in devtools — toggling fires zero requests.

- [ ] **Step 3: Commit**

```bash
git add app/static/app.js
git commit -m "feat(ui): wire Std/Cam toggle with display-only key conversion"
```

---

## Task 10: Wire errors tab open/close and error rendering

**Files:**
- Modify: `app/static/app.js` (replace `renderErrors` and wire tab click)

- [ ] **Step 1: Replace `renderErrors` with full panel rendering**

Find:

```javascript
function renderErrors() {
  const count = state.errors.length;
  els.errorsBadge.textContent = String(count);
  els.errorsTab.hidden = count === 0;
  // Panel rendering added in Task 10.
}
```

Replace with:

```javascript
function renderErrors() {
  const count = state.errors.length;
  els.errorsBadge.textContent = String(count);
  els.errorsTab.hidden = count === 0;

  if (count === 0) {
    state.errorsPanelOpen = false;
    els.errorsPanel.hidden = true;
    els.errorsTab.setAttribute('aria-expanded', 'false');
    els.errorsPanel.replaceChildren();
    return;
  }

  els.errorsPanel.hidden = !state.errorsPanelOpen;
  els.errorsTab.setAttribute('aria-expanded', String(state.errorsPanelOpen));

  els.errorsPanel.replaceChildren();
  const heading = document.createElement('h3');
  heading.textContent = `Errors (${count})`;
  els.errorsPanel.appendChild(heading);

  const reversed = state.errors.slice().reverse();
  for (const e of reversed) {
    const item = document.createElement('div');
    item.className = 'err-item';
    item.textContent = e.message;
    els.errorsPanel.appendChild(item);
  }
}
```

- [ ] **Step 2: Add tab click handler**

Find (near the bottom):

```javascript
els.keyToggle.forEach((opt) => {
  opt.addEventListener('click', () => {
    const next = opt.dataset.key;
    if (next !== 'std' && next !== 'cam') return;
    if (state.keyNotation === next) return;
    state.keyNotation = next;
    els.keyToggle.forEach((o) => o.classList.toggle('active', o.dataset.key === next));
    renderHistory();
  });
});

refreshJobs();
```

Add a click handler for the errors tab between them:

```javascript
els.keyToggle.forEach((opt) => {
  opt.addEventListener('click', () => {
    const next = opt.dataset.key;
    if (next !== 'std' && next !== 'cam') return;
    if (state.keyNotation === next) return;
    state.keyNotation = next;
    els.keyToggle.forEach((o) => o.classList.toggle('active', o.dataset.key === next));
    renderHistory();
  });
});

els.errorsTab.addEventListener('click', () => {
  state.errorsPanelOpen = !state.errorsPanelOpen;
  renderErrors();
});

refreshJobs();
```

- [ ] **Step 3: Verify in browser**

To trigger an error, paste an obviously invalid URL like `https://example.com/nope` and submit.
- A failed-status row appears in history.
- The errors tab appears on the right edge with badge `1` and a gentle pulsing cyan glow.
- Click the tab. Panel slides in below the history showing the error message.
- Click again. Panel collapses.
- Trigger another error. Badge becomes `2`. Panel re-renders with both messages, newest first.

- [ ] **Step 4: Commit**

```bash
git add app/static/app.js
git commit -m "feat(ui): wire errors tab with inline panel"
```

---

## Task 11: Wire silent window-wide drag-and-drop

**Files:**
- Modify: `app/static/app.js` (add upload helper and document-level drop handlers)

- [ ] **Step 1: Add `uploadFiles` near the I/O block**

Add this function just after `chooseOutputFolder` in `app/static/app.js`:

```javascript
async function uploadFiles(fileList) {
  for (const file of fileList) {
    const body = new FormData();
    body.append('file', file);
    body.append('format', state.format);
    body.append('output_dir', state.outputFolder || '');
    try {
      const response = await fetch('/api/upload', { method: 'POST', body });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || `Upload failed: ${response.status}`);
      }
    } catch (err) {
      pushError(`Upload failed for ${file.name}: ${err.message}`);
    }
  }
  refreshJobs();
}
```

- [ ] **Step 2: Add document-level drag-drop handlers**

Find the bottom of the file:

```javascript
els.errorsTab.addEventListener('click', () => {
  state.errorsPanelOpen = !state.errorsPanelOpen;
  renderErrors();
});

refreshJobs();
```

Insert the drop handlers between them:

```javascript
els.errorsTab.addEventListener('click', () => {
  state.errorsPanelOpen = !state.errorsPanelOpen;
  renderErrors();
});

document.addEventListener('dragover', (event) => {
  event.preventDefault();
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy';
});

document.addEventListener('drop', (event) => {
  event.preventDefault();
  const files = event.dataTransfer ? event.dataTransfer.files : null;
  if (!files || files.length === 0) return;
  uploadFiles(files);
});

refreshJobs();
```

- [ ] **Step 3: Verify in browser**

Drag a local audio file (any `.mp3`, `.wav`, etc.) onto any part of the window:
- No visual feedback during the drag (no border highlight, no overlay).
- After release, upload kicks off silently. Within 1.5s the row appears in history.
- Drop a non-audio file (e.g., a `.txt`). Server returns an error → errors tab appears with a message.

- [ ] **Step 4: Commit**

```bash
git add app/static/app.js
git commit -m "feat(ui): add silent window-wide drag-drop"
```

---

## Task 12: Manual smoke test pass and final commit

**Files:** none modified — verification only.

- [ ] **Step 1: Run all 8 spec smoke tests**

Open `http://127.0.0.1:8765` and walk through each:

1. Paste an SC URL, choose folder, select WAV, click Download → row appears, progress runs to 100%, `done` pill shows.
2. Paste a YT URL, repeat → same behavior.
3. Submit a known-bad URL → `failed` pill appears, errors badge increments, clicking the tab reveals the error.
4. Toggle Std ↔ Cam → key column updates instantly across all rows; no network calls fire (verify via devtools Network tab).
5. Drag a local audio file onto any part of the window → upload starts silently, row appears within 1.5s.
6. Restart the server (`Ctrl-C` and re-run `./scripts/run-local.sh`), reload page → history list is empty.
7. Resize window narrow (e.g., 360px wide) → column stays centered, no horizontal scroll. The controls row may wrap; that's acceptable.
8. View at full brightness in a bright room and at low brightness in a dark room → surface should feel comfortable in both. No glare, no muddy lows.

- [ ] **Step 2: Document any defects and fix inline**

If any check fails, address it in this section as a follow-up sub-task and re-verify. Common issues to watch for:
- Cover art URL from yt-dlp may be `null` for some sources — confirm the no-cover branch renders correctly.
- Camelot conversion misses uncommon enharmonic spellings — extend the `CAMELOT` map in `app.js` if any keys render verbatim instead of converting.
- Progress bar may be missing if `job.progress` doesn't include a `%` — confirm `parsePercent` returns `null` cleanly.

- [ ] **Step 3: Final review and push**

```bash
git status
git log --oneline -12
```

Expected: 11 new commits on the redesign, working tree clean.

If everything passes:

```bash
git push origin main
```

Or, to ship to a feature branch first:

```bash
git checkout -b feat/ui-redesign-iron-neon
git push -u origin feat/ui-redesign-iron-neon
```

---

## Out-of-band notes

- **The "Clear Cache" button is removed** from the UI. The backend endpoint `/api/cache/clear` still exists but is unreachable from the new UI. This is a deliberate UX simplification consistent with the spec's "no extra menus" rule.
- **The drop zone label** previously said `Drag audio files here or click to choose files`. That affordance is gone. There is no click-to-choose; only drag-drop is supported, and it's silent.
- **Format dropdown** uses native `<select>` styled flat inside the `.ctl` container. If the native arrow renders in some browsers, the inline caret `▾` is still visually present.
- **No automated tests** — per the spec, this is a UI-only change on top of an existing API. Add Playwright E2E later if/when test infrastructure is introduced; out of scope for this plan.
