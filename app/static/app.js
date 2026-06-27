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
  /** @type {boolean} Once the DJ picks a format by hand, stop auto-flipping it. */
  userOverrodeFormat: false,
  /** @type {'wav'|'aiff'|'mp3'} The format the dropdown held before the last auto-flip. */
  formatBeforeAuto: 'aiff',
  /** @type {boolean} */ soundEnabled: true,
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
  rendering:    document.getElementById('rendering'),
  renderingList: document.getElementById('renderingList'),
  keyToggle:    document.querySelectorAll('.fm-keytoggle .opt'),
  errorsTab:    document.getElementById('errorsTab'),
  errorsBadge:  document.getElementById('errorsBadge'),
  errorsPanel:  document.getElementById('errorsPanel'),
  sourceCard:   document.getElementById('sourceCard'),
  sourceCover:  document.getElementById('sourceCover'),
  sourceTitle:  document.getElementById('sourceTitle'),
  sourceMeta:   document.getElementById('sourceMeta'),
  sourcePill:   document.getElementById('sourcePill'),
  soundToggle:  document.getElementById('soundToggle'),
  formatNote:        document.getElementById('formatNote'),
  formatNoteText:    document.querySelector('#formatNote .fm-format-note-text'),
  formatNoteOverride: document.getElementById('formatNoteOverride'),
};

const PROBE_DEBOUNCE_MS = 350;
let probeAbort = null;
let probeTimer = null;

/* Completion tracking — diff job statuses across polls so a freshly-landed
   track gets its payoff exactly once, and old history never re-celebrates. */
const prevStatusById = new Map();
let celebrateIds = new Set();
let seededStatuses = false;

/* -------- Sound + haptics (synthesized — no audio asset files) -------- */

const SOUND_KEY = 'fm-sound';
let audioCtx = null;

function loadSoundPref() {
  state.soundEnabled = localStorage.getItem(SOUND_KEY) !== '0';
}

function ensureAudio() {
  if (!state.soundEnabled) return null;
  if (!audioCtx) {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    audioCtx = new Ctx();
  }
  if (audioCtx.state === 'suspended') audioCtx.resume().catch(() => {});
  return audioCtx;
}

/**
 * Play one short synthesized blip. Kept quiet and brief so it reads as tactile
 * feedback, not noise that competes with the music a DJ is monitoring.
 */
function blip({ freq = 440, type = 'sine', duration = 0.06, gain = 0.05, slideTo = null } = {}) {
  const ctx = ensureAudio();
  if (!ctx) return;
  const now = ctx.currentTime;
  const osc = ctx.createOscillator();
  const amp = ctx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, now);
  if (slideTo) osc.frequency.exponentialRampToValueAtTime(slideTo, now + duration);
  amp.gain.setValueAtTime(0.0001, now);
  amp.gain.exponentialRampToValueAtTime(gain, now + 0.008);
  amp.gain.exponentialRampToValueAtTime(0.0001, now + duration);
  osc.connect(amp).connect(ctx.destination);
  osc.start(now);
  osc.stop(now + duration + 0.02);
}

const sound = {
  tick:   () => blip({ freq: 520, type: 'triangle', duration: 0.04, gain: 0.04 }),
  toggle: () => blip({ freq: 660, type: 'sine', duration: 0.05, gain: 0.05 }),
  drop:   () => blip({ freq: 300, type: 'sine', duration: 0.09, gain: 0.05, slideTo: 180 }),
  launch: () => blip({ freq: 420, type: 'triangle', duration: 0.12, gain: 0.05, slideTo: 720 }),
  done:   () => {
    blip({ freq: 660, type: 'sine', duration: 0.10, gain: 0.05 });
    setTimeout(() => blip({ freq: 990, type: 'sine', duration: 0.14, gain: 0.05 }), 90);
  },
};

function haptic(pattern) {
  try { if (navigator.vibrate) navigator.vibrate(pattern); } catch (_) { /* unsupported */ }
}

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
    const jobs = data.jobs || [];
    detectCompletions(jobs);
    state.history = jobs;
    renderHistory();
  } catch (err) {
    pushError(err.message);
  }
}

/**
 * Flag jobs that just transitioned into `finished` so renderHistory can play
 * the payoff once. The first poll only seeds statuses (so existing history on
 * launch doesn't all celebrate at once).
 */
function detectCompletions(jobs) {
  const fresh = new Set();
  for (const job of jobs) {
    const prev = prevStatusById.get(job.id);
    if (seededStatuses && job.status === 'finished' && prev && prev !== 'finished') {
      fresh.add(job.id);
    }
    prevStatusById.set(job.id, job.status);
  }
  celebrateIds = fresh;
  seededStatuses = true;
  if (fresh.size > 0) {
    sound.done();
    haptic([10, 40, 16]);
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
  sound.tick();
  haptic(8);
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
  if (state.userOverrodeFormat) return;        // the DJ chose by hand — don't fight them
  const next = pickFormatForCodec(data.codec);
  if (state.format === next) { hideFormatNote(); return; }

  state.formatBeforeAuto = state.format;
  setFormat(next);
  els.formatSelect.value = next;
  els.formatValue.textContent = FORMAT_LABELS[next];
  showFormatNote(data, next, state.formatBeforeAuto);
}

/**
 * Surface *why* the format dropdown just changed, with a one-tap escape hatch
 * back to whatever the DJ had selected before. No more silent switches.
 */
function showFormatNote(data, picked, previous) {
  const codec = data.codec ? String(data.codec).toUpperCase() : 'this source';
  const kbps = data.bitrate ? `${Math.round(data.bitrate / 1000)} kbps` : '';
  const quality = data.lossy ? 'lossy' : 'lossless';
  const sourceDesc = [codec, kbps].filter(Boolean).join(' ');

  els.formatNoteText.replaceChildren();
  els.formatNoteText.append('Auto-set to ');
  const strong = document.createElement('strong');
  strong.textContent = FORMAT_LABELS[picked];
  els.formatNoteText.append(strong, ` — source is ${quality} ${sourceDesc}.`);

  els.formatNoteOverride.textContent = `Keep ${FORMAT_LABELS[previous]}`;
  els.formatNoteOverride.dataset.target = previous;
  els.formatNote.hidden = false;
}

function hideFormatNote() {
  els.formatNote.hidden = true;
  delete els.formatNoteOverride.dataset.target;
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
  const active = [];
  const done = [];
  for (const job of state.history) {
    if (job.status === 'finished' || job.status === 'failed') done.push(job);
    else active.push(job);
  }
  renderRendering(active);
  renderCrate(done);
}

/* Keep one DOM node per active job alive across polls. Wiping and rebuilding
   the list every 1.5s restarted the CSS swipe/pulse animations mid-cycle, which
   read as a stutter ("goes a little, snaps back, then completes"). Reconciling
   in place — touching a card only when its visible fields actually change —
   lets the loading swipe run as one clean, uninterrupted sweep. */
const activeCards = new Map(); // jobId -> { sig, el }

function heroSignature(job) {
  return JSON.stringify([
    job.status,
    job.cover_url || '',
    job.title || job.input_value || '',
    job.artist || '',
    job.genre || '',
    job.estimated_bpm || '',
    job.estimated_key || '',
    state.keyNotation,
    job.format || '',
    job.duration_seconds || '',
    Array.isArray(job.waveform) ? job.waveform.length : 0,
  ]);
}

function renderRendering(active) {
  els.rendering.hidden = active.length === 0;
  const list = els.renderingList;
  const seen = new Set();
  let prev = null;

  for (const job of active) {
    seen.add(job.id);
    const sig = heroSignature(job);
    let entry = activeCards.get(job.id);
    if (!entry) {
      entry = { sig, el: buildRenderHero(job) };
      activeCards.set(job.id, entry);
    } else if (entry.sig !== sig) {
      const fresh = buildRenderHero(job); // one rebuild per real change, not per poll
      entry.el.replaceWith(fresh);
      entry.el = fresh;
      entry.sig = sig;
    }
    // Place after `prev` without disturbing already-correct nodes (moving an
    // attached node doesn't restart its animations; removing + re-adding would).
    const anchor = prev ? prev.nextSibling : list.firstChild;
    if (anchor !== entry.el) list.insertBefore(entry.el, anchor);
    prev = entry.el;
  }

  for (const [id, entry] of activeCards) {
    if (!seen.has(id)) {
      entry.el.remove();
      activeCards.delete(id);
    }
  }
}

function renderCrate(done) {
  els.history.replaceChildren();
  if (done.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'fm-empty';
    empty.textContent = "Crate's empty — paste a link and let's dig.";
    els.history.appendChild(empty);
    return;
  }
  for (const job of done) {
    els.history.appendChild(buildCrateRow(job));
  }
}

const STAGE_RAIL = [
  { key: 'downloading', label: 'digging' },
  { key: 'analyzing',   label: 'reading the groove' },
  { key: 'converting',  label: 'bouncing' },
  { key: 'finished',    label: 'completed' },
];

/* ----- Rendering hero (active jobs) ----- */

function buildRenderHero(job) {
  const card = document.createElement('article');
  card.className = 'fm-hero-card';

  const art = document.createElement('div');
  art.className = 'fm-hero-art';
  if (job.cover_url) {
    const img = document.createElement('img');
    img.src = job.cover_url;
    img.alt = '';
    art.appendChild(img);
  } else {
    art.classList.add('placeholder');
    art.textContent = '♪';
  }
  card.appendChild(art);

  const mid = document.createElement('div');
  mid.className = 'fm-hero-mid';

  const title = document.createElement('div');
  title.className = 'fm-hero-title';
  title.textContent = job.title || job.input_value || 'Untitled';
  mid.appendChild(title);

  const artist = document.createElement('div');
  artist.className = 'fm-hero-artist';
  artist.textContent = [job.artist, job.genre].filter(Boolean).join(' · ') || '—';
  mid.appendChild(artist);

  mid.appendChild(buildBadges(job));
  mid.appendChild(buildWaveform(job.waveform));
  card.appendChild(mid);

  card.appendChild(buildStageRail(job));
  return card;
}

function buildBadges(job) {
  const wrap = document.createElement('div');
  wrap.className = 'fm-badges';
  wrap.appendChild(makeBadge('bpm', job.estimated_bpm ? String(job.estimated_bpm) : '—', 'BPM'));
  wrap.appendChild(makeBadge('key', formatKey(job.estimated_key, state.keyNotation), 'key'));
  wrap.appendChild(makeBadge('fmt', (job.format || '').toUpperCase() || '—', 'format'));
  wrap.appendChild(makeBadge('len', formatDuration(job.duration_seconds) || '—', 'length'));
  return wrap;
}

function makeBadge(modifier, value, label) {
  const badge = document.createElement('div');
  badge.className = `fm-badge ${modifier}`;
  const v = document.createElement('span');
  v.className = 'v';
  v.textContent = value;
  const l = document.createElement('span');
  l.className = 'l';
  l.textContent = label;
  badge.append(v, l);
  return badge;
}

/**
 * Render the real waveform (peaks 0..1 from the decoded audio). Real silence in
 * the track surfaces as near-flat bars. Before analysis finishes there are no
 * peaks yet, so we show a pending shimmer rather than fake a shape.
 */
function buildWaveform(waveform) {
  const wrap = document.createElement('div');
  wrap.className = 'fm-wave';
  if (!Array.isArray(waveform) || waveform.length === 0) {
    wrap.classList.add('pending');
    return wrap;
  }
  for (const peak of waveform) {
    const bar = document.createElement('i');
    const value = Math.max(0, Math.min(1, Number(peak) || 0));
    bar.style.height = `${Math.max(3, Math.round(value * 100))}%`;
    wrap.appendChild(bar);
  }
  return wrap;
}

function buildStageRail(job) {
  const rail = document.createElement('div');
  rail.className = 'fm-rail';
  const order = STAGE_RAIL.map((s) => s.key);
  let current = order.indexOf(job.status);
  if (job.status === 'queued') current = -1;

  STAGE_RAIL.forEach((stage, i) => {
    const step = document.createElement('div');
    step.className = 'fm-step';
    if (i < current) step.classList.add('done');
    else if (i === current) step.classList.add('cur');
    const dot = document.createElement('span');
    dot.className = 'dot';
    step.append(dot, document.createTextNode(stage.label));
    rail.appendChild(step);
    if (i < STAGE_RAIL.length - 1) {
      const link = document.createElement('div');
      link.className = i < current ? 'fm-link' : 'fm-link dim';
      rail.appendChild(link);
    }
  });
  return rail;
}

/* ----- Crate rows (completed / failed jobs) ----- */

function buildCrateRow(job) {
  const article = document.createElement('article');
  article.className = 'fm-row';
  if (celebrateIds.has(job.id)) article.classList.add('celebrate');

  if (job.cover_url) {
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
  metaLine.textContent = [job.artist, job.genre].filter(Boolean).join(' · ') || '—';
  info.appendChild(metaLine);
  article.appendChild(info);

  const chips = document.createElement('div');
  chips.className = 'fm-chips';
  if (job.status === 'finished') {
    if (job.estimated_bpm) chips.appendChild(makeChip('bpm', String(job.estimated_bpm)));
    const key = formatKey(job.estimated_key, state.keyNotation);
    if (key && key !== '—') chips.appendChild(makeChip('key', key));
    if (job.format) chips.appendChild(makeChip('fmt', job.format.toUpperCase()));
    chips.appendChild(makePill('done', 'completed'));
  } else {
    chips.appendChild(makePill('fail', 'failed'));
  }
  article.appendChild(chips);
  return article;
}

function makeChip(modifier, text) {
  const chip = document.createElement('span');
  chip.className = `fm-chip ${modifier}`;
  chip.textContent = text;
  return chip;
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
    state.userOverrodeFormat = false;   // fresh field → let the next link auto-pick again
    hideFormatNote();
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
  sound.launch();
  haptic(14);
  els.linkInput.value = '';
  els.downloadBtn.disabled = true;
  hideSourceCard();
  state.userOverrodeFormat = false;   // next link starts with a clean auto-pick
  hideFormatNote();
  await submitLink(link);
});

const FORMAT_LABELS = { wav: 'WAV', aiff: 'AIFF', mp3: 'MP3 320' };

els.formatSelect.addEventListener('change', (event) => {
  const value = /** @type {HTMLSelectElement} */ (event.target).value;
  setFormat(value);
  els.formatValue.textContent = FORMAT_LABELS[value] || value;
  state.userOverrodeFormat = true;   // hand-picked → stop auto-flipping
  hideFormatNote();
  sound.tick();
  haptic(8);
});

els.formatNoteOverride.addEventListener('click', () => {
  const target = els.formatNoteOverride.dataset.target;
  if (target !== 'wav' && target !== 'aiff' && target !== 'mp3') return;
  setFormat(target);
  els.formatSelect.value = target;
  els.formatValue.textContent = FORMAT_LABELS[target];
  state.userOverrodeFormat = true;
  hideFormatNote();
  sound.tick();
  haptic(8);
});

els.chooseOutput.addEventListener('click', chooseOutputFolder);

els.soundToggle.addEventListener('click', () => {
  state.soundEnabled = !state.soundEnabled;
  localStorage.setItem(SOUND_KEY, state.soundEnabled ? '1' : '0');
  applySoundUi();
  if (state.soundEnabled) { sound.toggle(); haptic(8); }
});

function applySoundUi() {
  els.soundToggle.setAttribute('aria-pressed', String(state.soundEnabled));
  els.soundToggle.setAttribute('aria-label', state.soundEnabled ? 'Mute sound' : 'Unmute sound');
  els.soundToggle.title = state.soundEnabled ? 'Sound on' : 'Sound off';
}

els.keyToggle.forEach((opt) => {
  opt.addEventListener('click', () => {
    const next = opt.dataset.key;
    if (next !== 'std' && next !== 'cam') return;
    if (state.keyNotation === next) return;
    state.keyNotation = next;
    els.keyToggle.forEach((o) => o.classList.toggle('active', o.dataset.key === next));
    renderHistory();
    sound.tick();
    haptic(6);
  });
});

els.errorsTab.addEventListener('click', () => {
  state.errorsPanelOpen = !state.errorsPanelOpen;
  renderErrors();
  sound.tick();
});

document.addEventListener('dragover', (event) => {
  event.preventDefault();
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy';
});

document.addEventListener('drop', (event) => {
  event.preventDefault();
  const files = event.dataTransfer ? event.dataTransfer.files : null;
  if (!files || files.length === 0) return;
  sound.drop();
  haptic([8, 30, 8]);
  uploadFiles(files);
});

loadSoundPref();
applySoundUi();
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
