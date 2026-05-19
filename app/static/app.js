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
  /** @type {'wav'|'aiff'|'mp3'} */ format: 'aiff',
  errorsPanelOpen: false,
};

const els = {
  linkForm:     document.getElementById('linkForm'),
  linkInput:    document.getElementById('linkInput'),
  formatSelect: document.getElementById('formatSelect'),
  formatValue:  document.getElementById('formatValue'),
  downloadBtn:  document.getElementById('downloadBtn'),
  outputDir:    document.getElementById('outputDir'),
  chooseOutput: document.getElementById('chooseOutput'),
  outputName:   document.getElementById('outputName'),
  history:      document.getElementById('history'),
  keyToggle:    document.querySelectorAll('.fm-keytoggle .opt'),
  errorsTab:    document.getElementById('errorsTab'),
  errorsBadge:  document.getElementById('errorsBadge'),
  errorsPanel:  document.getElementById('errorsPanel'),
  sourceCard:   document.getElementById('sourceCard'),
  sourceCover:  document.getElementById('sourceCover'),
  sourceTitle:  document.getElementById('sourceTitle'),
  sourceMeta:   document.getElementById('sourceMeta'),
  sourcePill:   document.getElementById('sourcePill'),
};

const PROBE_DEBOUNCE_MS = 350;
let probeAbort = null;
let probeTimer = null;

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
  if (!state.outputFolder) {
    pushError('Choose an output folder before downloading.');
    return;
  }
  try {
    await fetchJson('/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        link,
        format: state.format,
        output_dir: state.outputFolder,
      }),
    });
  } catch (err) {
    pushError(err.message);
  }
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

async function probeUrl(url) {
  if (probeAbort) probeAbort.abort();
  const controller = new AbortController();
  probeAbort = controller;
  try {
    const data = await fetchJson(`/api/probe?url=${encodeURIComponent(url)}`, { signal: controller.signal });
    if (probeAbort !== controller) return;
    populateSourceCard(data);
    applySmartFormat(data);
  } catch (err) {
    if (err.name === 'AbortError') return;
    if (probeAbort !== controller) return;
    hideSourceCard();
  }
}

function populateSourceCard(data) {
  const titleText = data.title || '—';
  const metaParts = [];
  if (data.artist) metaParts.push(data.artist);
  const duration = formatDuration(data.duration);
  if (duration) metaParts.push(duration);
  els.sourceTitle.textContent = titleText;
  els.sourceMeta.textContent = metaParts.length ? metaParts.join(' · ') : '—';

  if (data.thumbnail) {
    els.sourceCover.src = data.thumbnail;
    els.sourceCover.alt = titleText;
  } else {
    els.sourceCover.removeAttribute('src');
    els.sourceCover.alt = '';
  }

  const pill = formatSourcePill(data);
  els.sourcePill.textContent = pill.label;
  els.sourcePill.className = `fm-source-pill ${pill.modifier}`;

  els.sourceCard.hidden = false;
}

function formatSourcePill(data) {
  const codec = data.codec ? String(data.codec).toUpperCase() : null;
  const kbps = data.bitrate ? Math.round(data.bitrate / 1000) : null;
  let label = '—';
  if (codec && kbps) label = `${codec} ${kbps}`;
  else if (codec) label = codec;
  const modifier = data.lossy ? 'lossy' : 'lossless';
  return { label, modifier };
}

function applySmartFormat(data) {
  const next = pickFormatForCodec(data.codec);
  if (state.format === next) return;
  setFormat(next);
  els.formatSelect.value = next;
  els.formatValue.textContent = FORMAT_LABELS[next];
}

/**
 * Pick the best output format for a given source codec.
 * MP3 source → MP3, WAV/little-endian-PCM → WAV, AIFF/big-endian-PCM → AIFF,
 * other lossless (FLAC/ALAC) → AIFF, lossy non-MP3 (opus/aac) → MP3,
 * unknown → MP3 (defensive: never silently upcode an unknown source).
 * @param {string|undefined|null} codec
 * @returns {'wav'|'aiff'|'mp3'}
 */
function pickFormatForCodec(codec) {
  if (!codec) return 'mp3';
  const c = String(codec).toLowerCase();
  if (c === 'mp3') return 'mp3';
  if (c === 'aiff' || c === 'pcm_s16be' || c === 'pcm_s24be') return 'aiff';
  if (c === 'wav' || c.startsWith('pcm_')) return 'wav';
  if (c === 'flac' || c === 'alac' || c === 'ape' || c === 'tta' || c === 'wv') return 'aiff';
  return 'mp3';
}

/**
 * Pick output format for a local file based on its extension.
 * Returns null when the extension is unrecognized, so callers can fall back
 * to the dropdown choice.
 * @param {string} filename
 * @returns {'wav'|'aiff'|'mp3'|null}
 */
function pickFormatForFile(filename) {
  const dot = filename.lastIndexOf('.');
  if (dot < 0) return null;
  const ext = filename.slice(dot + 1).toLowerCase();
  if (ext === 'mp3') return 'mp3';
  if (ext === 'wav' || ext === 'wave') return 'wav';
  if (ext === 'aiff' || ext === 'aif' || ext === 'aifc') return 'aiff';
  if (ext === 'flac' || ext === 'alac' || ext === 'm4a' || ext === 'ape' || ext === 'tta' || ext === 'wv') return 'aiff';
  return null;
}

function hideSourceCard() {
  if (probeAbort) probeAbort.abort();
  if (probeTimer) clearTimeout(probeTimer);
  probeAbort = null;
  probeTimer = null;
  els.sourceCard.hidden = true;
  els.sourceCover.removeAttribute('src');
  els.sourceCover.alt = '';
  els.sourceTitle.textContent = '—';
  els.sourceMeta.textContent = '—';
  els.sourcePill.textContent = '—';
  els.sourcePill.className = 'fm-source-pill';
}

async function uploadFiles(fileList) {
  if (!state.outputFolder) {
    pushError('Choose an output folder before converting.');
    return;
  }
  for (const file of fileList) {
    const body = new FormData();
    body.append('file', file);
    body.append('format', pickFormatForFile(file.name) || state.format);
    body.append('output_dir', state.outputFolder);
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

/* -------- State mutators -------- */

function setOutputFolder(path) {
  if (!path) {
    state.outputFolder = null;
    els.outputDir.value = '';
    els.outputName.textContent = 'Choose folder';
    els.chooseOutput.removeAttribute('title');
    updateDownloadButton();
    return;
  }
  state.outputFolder = path;
  els.outputDir.value = path;
  els.outputName.textContent = folderName(path);
  els.chooseOutput.title = path;
  updateDownloadButton();
}

function updateDownloadButton() {
  const hasLink = els.linkInput.value.trim().length > 0;
  els.downloadBtn.disabled = !hasLink || !state.outputFolder;
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

/* -------- Helpers -------- */

function folderName(path) {
  return path.split('/').filter(Boolean).pop() || path;
}

/* -------- Wiring -------- */

els.linkInput.addEventListener('input', () => {
  const value = els.linkInput.value.trim();
  updateDownloadButton();

  if (probeAbort) probeAbort.abort();
  if (probeTimer) clearTimeout(probeTimer);

  if (!value.toLowerCase().startsWith('http')) {
    hideSourceCard();
    return;
  }

  probeTimer = setTimeout(() => {
    probeTimer = null;
    probeUrl(value);
  }, PROBE_DEBOUNCE_MS);
});

els.linkForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const link = els.linkInput.value.trim();
  if (!link) return;
  els.linkInput.value = '';
  els.downloadBtn.disabled = true;
  hideSourceCard();
  await submitLink(link);
});

const FORMAT_LABELS = { wav: 'WAV', aiff: 'AIFF', mp3: 'MP3 320' };

els.formatSelect.addEventListener('change', (event) => {
  const value = /** @type {HTMLSelectElement} */ (event.target).value;
  setFormat(value);
  els.formatValue.textContent = FORMAT_LABELS[value] || value;
});

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
setInterval(refreshJobs, 1500);

async function checkForUpdate() {
  try {
    const banner = document.getElementById('updateBanner');
    if (!banner) return;
    const text = banner.querySelector('.fm-update-text');
    const link = document.getElementById('updateLink');
    const dismiss = document.getElementById('updateDismiss');
    if (!text || !link || !dismiss) return;
    if (sessionStorage.getItem('fm-update-dismissed') === '1') return;
    const response = await fetch('/api/version');
    if (!response.ok) return;
    const data = await response.json();
    if (!data || !data.update_available) return;
    text.textContent = `Update available: v${data.latest} (you have v${data.current}).`;
    if (data.html_url) link.href = data.html_url;
    banner.hidden = false;
    dismiss.addEventListener('click', () => {
      banner.hidden = true;
      sessionStorage.setItem('fm-update-dismissed', '1');
    }, { once: true });
  } catch (_) {
    // Update check is best-effort; silently ignore network errors.
  }
}

checkForUpdate();
