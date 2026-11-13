const $ = s => document.querySelector(s);
const hex = v => v == null ? '–' : v.toString(16);
const S = {
  maps: [], map: null, atlas: {}, show: [true, true, true], alpha: [1, 1, 1],
  tool: 'view', block: null, pending: new Map(), undo: [], redo: [], stroke: null,
  markerMoves: new Map(),  // marker index -> {x, z, restore}, unsaved
  scenes: [], allScenes: null, tableEdits: new Map(), entranceCache: {},
  names: null, legend: {}, spriteImg: {},
  clip: null, stampMode: 'copy', sel: null, hoverCell: null, pixelCache: {},
};

function save(k, v) { try { localStorage.setItem('gsmap.' + k, JSON.stringify(v)); } catch (e) {} }
function load(k, d) { try { const v = localStorage.getItem('gsmap.' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } }

async function api(path, body) {
  const opt = body === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-GSMap': '1' }, body: JSON.stringify(body) };
  const busy = body === undefined ? null : setTimeout(() => document.body.classList.add('busy'), 200);
  let j;
  try {
    const r = await fetch(path, opt);
    try { j = await r.json(); } catch (e) { j = { error: `HTTP ${r.status}` }; }
  } catch (e) { j = { error: T('The editor stopped answering. Is it still running?') }; }
  if (busy) { clearTimeout(busy); document.body.classList.remove('busy'); if (!path.includes('history')) refreshUndoSave(); }
  return j;
}

// ---- map list -----------------------------------------------------------
async function init() {
  refreshUndoSave();
  S.names = await api('/api/names');
  S.names.itemById = Object.fromEntries(S.names.items.map(i => [i.id, i]));
  S.names.spriteById = Object.fromEntries(S.names.sprites.map(i => [i.id, i]));
  S.names.sceneById = Object.fromEntries(S.names.scenes.map(i => [i.id, i]));
  S.advanced = load('advanced', false); $('#advanced').checked = S.advanced;
  $('#ovStand').checked = load('ovStand', false);
  document.body.classList.toggle('advanced', S.advanced);
  buildBrushes();
  S.maps = await api('/api/maps');
  $('#zoom').value = load('zoom', '2');
  renderList();
  // Links like ?map=003&tool=collision&table=points open straight to a place.
  const q = new URLSearchParams(location.search);
  const want = q.get('map') || load('map', null);
  if (want && S.maps.some(m => m.number === want)) {
    await openMap(want);
    if (q.get('tool')) setTool(q.get('tool'));
    if (q.get('kind')) {
      const t = scene()?.tables.find(t => t.kind === q.get('kind'));
      if (t) { $('#tableSel').value = t.symbol; renderTable(); drawAll(); revealPoints(); }
    }
  }
}

function renderList() {
  const q = $('#filter').value.trim().toLowerCase();
  $('#maps').innerHTML = q && !('world map overworld ' + T('World map').toLowerCase()).includes(q) ? '' : '<a class="map" href="/world.html" style="text-decoration:none;color:inherit"><span class="t">🌍 ' + T('World map') + '</span><span class="d" style="grid-column:1/3">' + T('the overworld: towns, regions, ground') + '</span></a>';
  for (const m of S.maps) {
    const text = `${m.number} ${m.folder} ${m.tileset || ''} ${m.label || ''}`.toLowerCase();
    if (q && !text.includes(q)) continue;
    const el = document.createElement('div');
    el.className = 'map' + (S.map && S.map.number === m.number ? ' sel' : '');
    el.innerHTML = `<span class="t">${esc(m.label || m.folder)}</span>
      <span class="d" style="grid-column:1/3">${T('map {n}', { n: m.number })}${S.advanced ? ` · ${esc(m.folder)} · ${esc(m.tileset || '?')}` : ''} · ${m.size[0]}×${m.size[1]}</span>`;
    el.onclick = () => openMap(m.number);
    $('#maps').appendChild(el);
  }
  $('#maps a.map')?.addEventListener('click', async e => {
    e.preventDefault();
    if (await saveFirst()) location.href = '/world.html';
  });
}

function loadImage(src) {
  return new Promise(res => { const i = new Image(); i.onload = () => res(i); i.onerror = () => res(null); i.src = src; });
}

async function openMap(n) {
  for (const k in PEOPLE_LINES) delete PEOPLE_LINES[k];  // what people say may have changed
  if (S.map && S.map.number !== n) EV.stage = null;  // a story stage belongs to one map's tables
  if (!await saveFirst()) return;
  // The place asked for last wins: an earlier request still loading stops at its next step.
  const ticket = S.opening = {}, stale = () => S.opening !== ticket;
  $('#status').textContent = T('Loading map {n}…', { n });
  const map = await api(`/api/map/${n}`);
  if (stale()) return;
  if (map.error) {
    S.failed = map.damaged ? n : null;  // Reset place can still put it back
    if (map.damaged) failDialog(T("This place can't be opened"), map.error, map.detail);
    status(`<span class="err">${esc(map.error)}</span>`);
    return;
  }
  if (!S.map || S.map.number !== n) forgetPlace();
  S.failed = null;
  S.map = map; save('map', n);
  map.shapesSaved = map.shapes.length;  // heights past this are new, added on Save
  if (S.block != null && (S.block >= map.metatile_count || map.retired?.includes(S.block))) S.block = null;
  S.pending.clear(); S.markerMoves.clear(); S.tableEdits.clear(); S.undo = []; S.redo = [];
  const bases = [...new Set(map.layers.filter(l => l.priority).map(l => l.char_base))];
  const atlas = S.atlas = {};
  S.pixelCache = {};  // keyed by atlas URL, which changes on every load
  await Promise.all(bases.map(async b => { atlas[b] = await loadImage(`/api/map/${n}/atlas/${b}.png?t=${Date.now()}`); }));
  if (stale()) return;
  buildLayerControls();
  renderList(); drawAll(); drawPalette(); updateButtons();
  await loadScenes();
  if (stale()) return;
  fillPlayFrom();
  if (S.tool === 'stamp') setStampMode(S.stampMode);
  api(`/api/map/${n}/legend`).then(l => { if (S.map !== map) return; S.legend = l.error ? {} : l; drawAll(); });
  loadChests(); loadDoors();
  if (S.tool === 'events') await loadEvents();
  if (stale()) return;
  if (S.tool === 'shape') buildHeightPanel();
  WK.key = null; loadStand();
  status(S.advanced ? `${T('Map {n}', { n: `<b>${n}</b>` })} · ${esc(map.folder)} · ${esc(map.tileset)}${map.palette ? ' ' + T('(palette {p})', { p: esc(map.palette) }) : ''} · ${map.size[0]}×${map.size[1]} · ${T('{n} blocks', { n: map.metatile_count })}` : `<b>${esc(S.maps.find(m => m.number === n)?.label || T('Place {n}', { n }))}</b>`);
  $('#welcome').style.display = 'none';
  if (map.shares_grid?.length) status(`<span class="warn">${map.shares_grid.length > 1
    ? T("This place's map is shared with {n} others: painting here changes them too.", { n: map.shares_grid.length })
    : T("This place's map is shared with 1 other: painting here changes it too.")}</span>`);
}

// What was picked or half filled in belongs to the place you were on.
function forgetPlace() {
  Object.assign(EV, { data: null, sel: null, filter: null, spot: null, region: null, newPerson: null });
  Object.assign(WK, { cells: null, key: null });
  $('#evSpot').style.display = 'none';
  importData = null; $('#importBox').style.display = 'none';
  S.chestAt = null; $('#chestForm').style.display = 'none';
  S.doorAt = null; $('#doorForm').style.display = 'none'; S.arrivalMark = S.cellMark = null;
  S.legend = {}; S.chests = null; S.doors = null;  // until the new place's arrive
  if (S.tool === 'stamp') S.sel = null;
}

const LAYER_NAMES = [T('Ground'), T('Middle'), T('Overhead')];
function visibleLayers() { return S.map.layers.filter(l => l.priority).sort((a, b) => b.priority - a.priority); }

function buildLayerControls() {
  const box = $('#layers'); box.innerHTML = '';
  for (const l of visibleLayers()) {
    const i = l.index, el = document.createElement('span'); el.className = 'layer';
    el.innerHTML = `<label title="${T('Show or hide this layer')}"><input type="checkbox" ${S.show[i] ? 'checked' : ''}> ${LAYER_NAMES[i] || 'L' + i}</label>
      <input class="adv" type="range" min="0" max="100" value="${Math.round(S.alpha[i] * 100)}" title="${T('See-through')}">`;
    const [cb, rng] = el.querySelectorAll('input');
    cb.onchange = () => { S.show[i] = cb.checked; drawAll(); };
    rng.oninput = () => { S.alpha[i] = rng.value / 100; drawAll(); };
    box.appendChild(el);
  }
  const sel = $('#editLayer'), prev = sel.value; sel.innerHTML = '';
  for (const l of S.map.layers.filter(l => l.priority))
    sel.insertAdjacentHTML('beforeend', `<option value="${l.index}">${LAYER_NAMES[l.index] || 'L' + l.index}</option>`);
  if ([...sel.options].some(o => o.value === prev)) sel.value = prev;
}

// ---- coordinates ---------------------------------------------------------
function layer() { return S.map.layers[+$('#editLayer').value] || S.map.layers[0]; }
// Grid cell behind window cell (x, y) on layer l; windows wrap at 128 like the game.
function gridXY(l, x, y) {
  const m = S.map;
  return [(l.origin[0] + m.bounds[0] / 2 + x) % 128, (l.origin[1] + m.bounds[1] / 2 + y) % 128];
}
function at(grid, l, x, y) { const [gx, gy] = gridXY(l, x, y); return grid?.[gy]?.[gx]; }

// ---- drawing ---------------------------------------------------------------
function collisionRange(v) { return S.names?.collision.find(r => r.lo <= v && v <= r.hi); }
function collisionName(v) {
  if (v == null) return '–';
  const legend = S.legend[String(v)], r = collisionRange(v);
  const base = legend ? legend.join('; ') : (r ? r.name : T('unknown'));
  return S.advanced ? `${base} [${hex(v)}]` : base;
}
function collisionColor(v) {
  if (!v) return null;
  const r = collisionRange(v);
  if (r && r.color && r.lo === r.hi) {
    const c = r.color;  // #rrggbb or #rrggbbaa
    return c.length === 9 ? c : c + '88';
  }
  if (v >= 1 && v <= 239) return S.legend[String(v)] ? 'rgba(255,170,0,0.6)' : 'rgba(255,204,0,0.35)';
  return `hsla(${(v * 47) % 360},80%,55%,0.45)`;
}

// ---- height: square types, levels and stairs ----------------------------------
// A square's height is a row of the place's shape table: a kind (the pattern)
// and up to three samples, each a level (8 pixels, the game's unit and the most
// the party can step up). The panel builds a square type from a pattern,
// a direction and levels; painting finds that row in the table or makes it,
// and Save adds the rows made here (project.apply_edits). ⌥-click copies a
// square's exact row. The list below the builder is only a tally.
const HB_ROWS = {  // pattern -> direction -> [kind, which sample is low first]
  ramp: { right: [1, true], left: [1, false], down: [2, true], up: [2, false] },
  steps: { right: [8, true], left: [8, false], down: [9, true], up: [9, false] },
  diagonal: { se: [3, true], nw: [3, false], sw: [4, true], ne: [4, false] },
};
const HB_FLAT = new Set([0, 14, 15]);
const lvSigned = v => (v > 127 ? v - 256 : v);
function hbRow(hb, lift = 0) {
  const lo = hb.low + lift, hi = hb.high + lift;
  if (hb.pattern === 'flat') return [0, lo, 0, 0];
  const [kind, lowFirst] = HB_ROWS[hb.pattern][hb.dir];
  return lowFirst ? [kind, lo, hi, 0] : [kind, hi, lo, 0];
}
// The builder's reading of a table row, or 'copied' for patterns it can't make.
function hbFromRow(r) {
  const k = r[0] & 15, a = lvSigned(r[1]), b = lvSigned(r[2]);
  if (HB_FLAT.has(k)) return { pattern: 'flat', dir: 'right', low: a, high: a + 2 };
  for (const [pattern, dirs] of Object.entries(HB_ROWS))
    for (const [dir, [kind, lowFirst]] of Object.entries(dirs))
      if (kind === k && (lowFirst ? a <= b : a > b)) return { pattern, dir, low: Math.min(a, b), high: Math.max(a, b) };
  const ls = (k === 7 ? r.slice(1, 3) : r.slice(1, 4)).map(lvSigned);  // as describeShape reads them
  return { pattern: 'copied', dir: 'right', low: Math.min(...ls), high: Math.max(...ls) };
}
// The table row for a square type: the first identical one, else a new one
// kept with the place until Save adds it (or until the place is reloaded).
const sameShape = (r, row) => !!r && !!row && r[0] === row[0] && r[1] === row[1] && r[2] === row[2] && (r[3] ?? 0) === (row[3] ?? 0);
function findShape(row) { return S.map.shapes.findIndex(r => sameShape(r, row)); }
function shapeIndex(row) {
  const m = S.map, i = findShape(row);
  if (i >= 0) return i;
  const free = unusedShape();  // trying levels out leaves rows behind: reuse one
  if (free != null) { m.shapes[free] = row.slice(); return free; }
  if (m.shapes.length >= 256) return null;  // the game reads one byte per square
  m.shapes.push(row.slice());
  return m.shapes.length - 1;
}
// A row made here that nothing uses any more: no square, Undo or Redo step
// or brush names it (stamps carry rows by content, so they don't count).
function unusedShape() {
  const m = S.map, saved = m.shapesSaved ?? m.shapes.length;
  if (saved >= m.shapes.length) return null;
  const inUse = new Set();
  for (const line of m.grids.shape || []) for (const v of line) if (v >= saved) inUse.add(v);
  for (const step of [...S.undo || [], ...S.redo || [], S.stroke || []])
    for (const c of step) if (c.plane === 'shape') { inUse.add(c.before); inUse.add(c.after); }
  inUse.add(parseInt(S.tool === 'shape' ? $('#value').value : S.values?.shape, 16));
  for (let v = saved; v < m.shapes.length; v++) if (!inUse.has(v)) return v;
  return null;
}
function pendingShapes() { const m = S.map; return m ? m.shapes.slice(m.shapesSaved) : []; }
function describeShape(r) {
  if (!r) return T('Unknown height');
  const k = r[0] & 15, a = lvSigned(r[1]), b = lvSigned(r[2]);
  if (HB_FLAT.has(k)) return T('Level {n}', { n: a });
  if (k === 1) return T('Ramp, level {a} to {b}, left to right', { a, b });
  if (k === 2) return T('Ramp, level {a} to {b}, top to bottom', { a, b });
  if (k === 8) return T('Steps, left half level {a}, right half level {b}', { a, b });
  if (k === 9) return T('Steps, top half level {a}, bottom half level {b}', { a, b });
  if (k === 3) return T('Diagonal, top-left level {a}, bottom-right level {b}', { a, b });
  if (k === 4) return T('Diagonal, top-right level {a}, bottom-left level {b}', { a, b });
  const ls = (k === 7 ? r.slice(1, 3) : r.slice(1, 4)).map(lvSigned);
  return T('Shaped, levels {a} to {b}', { a: Math.min(...ls), b: Math.max(...ls) });
}
// Height in levels at pixel (x, y) of a square, for the builder's picture
// (walk.py's height_at for the kinds the builder makes; others read flat).
function shapeLevelAt(r, x, y) {
  const k = r[0] & 15, a = lvSigned(r[1]), b = lvSigned(r[2]);
  if (k === 1) return a + (b - a) * x / 15;
  if (k === 2) return a + (b - a) * y / 15;
  if (k === 8) return x < 8 ? a : b;
  if (k === 9) return y < 8 ? a : b;
  if (k === 3) return x + y === 15 ? Math.max(a, b) : x + y < 15 ? a : b;
  if (k === 4) return y - x === 0 ? Math.max(a, b) : y < x ? a : b;
  return HB_FLAT.has(k) ? a : Math.max(a, b);
}
// Whether the party can cross a square of this type: one level a step, and
// the game looks a step (half a square) ahead, so a ramp climbs two a square.
function hbWalkable(hb) {
  const d = Math.abs(hb.high - hb.low);
  return hb.pattern === 'flat' || (hb.pattern === 'ramp' ? d <= 2 : d <= 1);
}
// Levels one square of stairs climbs: a ramp's whole rise, steps' two halves.
function hbClimb(hb) { return hb.pattern === 'ramp' ? hb.high - hb.low : 2 * (hb.high - hb.low); }

// The brush's row for square (gx, gy): with Stairs on, each square further
// along the rising direction from where the stroke began is a flight higher.
function shapeBrushAt(gx, gy) {
  const hb = S.hb;
  if (!hb || !hb.stairs || !['ramp', 'steps'].includes(hb.pattern) || hb.exact != null) return parseInt($('#value').value, 16);
  if (!S.climbFrom) S.climbFrom = [gx, gy];
  const dx = gx - S.climbFrom[0], dy = gy - S.climbFrom[1];
  const k = { right: dx, left: -dx, down: dy, up: -dy }[hb.dir], lift = k * hbClimb(hb);
  if (Math.max(hb.low, hb.high) + lift > 127 || Math.min(hb.low, hb.high) + lift < -128) return undefined;  // past the game's levels
  return shapeIndex(hbRow(hb, lift));
}

function setHeightBrush(change) {
  const hb = S.hb, m = S.map;
  Object.assign(hb, change, { exact: null });
  if (hb.pattern === 'copied') hb.pattern = 'flat';
  if (hb.pattern === 'diagonal' && !HB_ROWS.diagonal[hb.dir]) hb.dir = 'se';
  if (hb.pattern !== 'diagonal' && hb.pattern !== 'flat' && !HB_ROWS.ramp[hb.dir]) hb.dir = 'right';
  hb.low = Math.max(-128, Math.min(127, Math.round(hb.low) || 0));
  hb.high = Math.max(-128, Math.min(127, Math.round(hb.high) || 0));
  const v = shapeIndex(hbRow(hb));
  if (v == null) { status(`<span class="err">${T('This place already has {n} heights, the most the game can hold. Reuse one of them.', { n: 256 })}</span>`); return; }
  $('#value').value = hex(v);
  buildHeightPanel();
}

function buildHeightPanel() {
  const box = $('#heightPanel'), m = S.map; if (!m) return;
  let current = parseInt($('#value').value, 16);
  // The table was replaced (another place, a reload, a save): the brush is its
  // row's content, so find (or make) that row in this one.
  if (S.hbTable && S.hbTable !== m.shapes && current === S.hbValue && S.hbContent) {
    const v = shapeIndex(S.hbContent);
    current = v ?? NaN; $('#value').value = v == null ? '' : hex(v);
    if (S.hb && S.hb.exact != null) S.hb.exact = v;
  }
  if (!(current < m.shapes.length)) { $('#value').value = ''; current = NaN; }  // another place's height
  const used = new Map();
  for (const row of m.grids.shape || []) for (const v of row) used.set(v, (used.get(v) || 0) + 1);
  if (isNaN(current)) {  // start from this place's commonest flat ground
    const flat = [...used].filter(([v]) => m.shapes[v] && HB_FLAT.has(m.shapes[v][0] & 15)).sort((a, b) => b[1] - a[1])[0];
    if (flat) { current = flat[0]; $('#value').value = hex(current); }
  }
  S.hb ||= { pattern: 'flat', dir: 'right', low: 0, high: 2, stairs: false, exact: null };
  const hb = S.hb;
  // A value set from outside the builder (⌥-click, Advanced) is read back exactly.
  if (!isNaN(current) && hb.exact !== current) {
    const same = hb.exact == null && findShape(hbRow(hb)) === current;
    if (!same) Object.assign(hb, hbFromRow(m.shapes[current]), { exact: current });
  }
  const shade = heightShade(m);
  const choice = (group, value, label, title) =>
    `<button data-${group}="${value}" title="${esc(title || '')}" class="${hb[group] === value ? 'on' : ''}">${label}</button>`;
  const PATTERNS = [['flat', T('Flat')], ['ramp', T('Ramp')], ['steps', T('Steps')], ['diagonal', T('Diagonal')]];
  const DIRS = hb.pattern === 'diagonal'
    ? [['se', '↘', T('High corner bottom-right')], ['sw', '↙', T('High corner bottom-left')], ['ne', '↗', T('High corner top-right')], ['nw', '↖', T('High corner top-left')]]
    : [['right', '→', T('Rising to the right')], ['left', '←', T('Rising to the left')], ['down', '↓', T('Rising downwards')], ['up', '↑', T('Rising upwards')]];
  const num = (key, value) => `<input type="number" data-level="${key}" value="${value}" min="-128" max="127" step="1">`;
  const levels = hb.pattern === 'flat' || hb.pattern === 'copied'
    ? `<label>${T('Level')} ${num('low', hb.low)}</label>`
    : `<label>${T('From level')} ${num('low', hb.low)}</label> <label>${T('to')} ${num('high', hb.high)}</label>`;
  const row = isNaN(current) ? null : m.shapes[current];
  Object.assign(S, { hbTable: m.shapes, hbValue: current, hbContent: row && row.slice() });
  const isNew = !isNaN(current) && current >= m.shapesSaved;
  const walkable = hbWalkable(hb);
  const canStairs = ['ramp', 'steps'].includes(hb.pattern) && hb.exact == null;
  const html = [
    `<div class="note">${T('Pick a square type, then paint, or ⌥-click the map to copy one. The party can walk up or down one level at a time; two levels or more is a wall. Ramps join levels: one square of ramp can climb two.')} ${T('On the map, darker blue is higher ground; the lowest ground here has none.')}</div>`,
    `<div class="hb-row">${PATTERNS.map(([v, t]) => choice('pattern', v, esc(t))).join('')}</div>`,
    hb.pattern === 'flat' || hb.pattern === 'copied' ? '' : `<div class="hb-row">${DIRS.map(([v, a, t]) => choice('dir', v, a, t)).join('')}</div>`,
    hb.pattern === 'copied' ? `<div class="note">${esc(T('Copied from the map: {what}', { what: describeShape(row) }))}</div>` : `<div class="hb-row">${levels}</div>`,
    `<div class="hb-row"><canvas id="hbPreview" width="48" height="48"></canvas><div>
       <div>${esc(row ? describeShape(row) : T('Pick a square type'))}${S.advanced && row ? ` [${hex(current)}]` : ''}</div>
       <div class="${walkable ? 'ok' : 'warn'}">${walkable ? T('The party can walk across it.') : T('Too steep to walk: it works as a wall.')}</div>
       ${isNew ? `<div class="muted">${T('New height: added to this place when you save.')}</div>` : ''}
     </div></div>`,
    canStairs ? `<label class="hb-row" title="${esc(T('Drag in the rising direction: each square climbs on from the last, so one drag paints a whole staircase.'))}"><input type="checkbox" id="hbStairs" ${hb.stairs ? 'checked' : ''}><span style="flex:1;min-width:0">${T('Stairs: keep climbing as I drag ({n} levels a square)', { n: hbClimb(hb) })}</span></label>` : '',
  ];
  // The tally: squares per level, flat ground only; everything else in one line.
  const tally = new Map(); let shaped = 0;
  for (const [v, n] of used) {
    const r = m.shapes[v];
    if (r && HB_FLAT.has(r[0] & 15)) { const l = lvSigned(r[1]); const t = tally.get(l) || { n: 0, v }; t.n += n; tally.set(l, t); }
    else shaped += n;
  }
  const lines = [...tally].sort((a, b) => b[0] - a[0]).map(([l, t]) =>
    `<div class="hb-tally"><i style="background:${shade(t.v) || 'transparent'}"></i>${esc(T('Level {n}', { n: l }))}<span>${t.n === 1 ? T('1 square') : T('{n} squares', { n: t.n })}</span></div>`);
  if (shaped) lines.push(`<div class="hb-tally"><i></i>${esc(T('Ramps, steps and other shapes'))}<span>${shaped === 1 ? T('1 square') : T('{n} squares', { n: shaped })}</span></div>`);
  html.push(`<h3>${T('Levels in this place')}</h3><div class="hb-list">${lines.join('')}</div>`);
  if (S.advanced) {
    const all = [...m.shapes.keys()].map(v => `<button data-row="${v}" class="${v === current ? 'on' : ''}" title="${esc(T('{n} squares here use this height.', { n: used.get(v) || 0 }))}">[${hex(v)}] ${esc(describeShape(m.shapes[v]))}</button>`);
    html.push(`<details id="hbAll" ${S.heightMoreOpen ? 'open' : ''}><summary>${T('Every height in the table ({n})', { n: m.shapes.length })}</summary><div class="hb-list">${all.join('')}</div></details>`);
  }
  box.innerHTML = localWords(html.join(''));
  box.querySelectorAll('[data-pattern]').forEach(b => b.onclick = () => {
    const p = b.dataset.pattern, base = hb.pattern === 'flat' || hb.pattern === 'copied' ? hb.low : Math.min(hb.low, hb.high);
    setHeightBrush({ pattern: p, low: base, high: base + (p === 'ramp' ? 2 : 1) });
  });
  box.querySelectorAll('[data-dir]').forEach(b => b.onclick = () => setHeightBrush({ dir: b.dataset.dir }));
  box.querySelectorAll('[data-level]').forEach(inp => inp.onchange = () => {
    const v = +inp.value, ch = { [inp.dataset.level]: v };
    if (inp.dataset.level === 'low') ch.high = hb.pattern === 'flat' || hb.pattern === 'copied' ? v + 2 : hb.high + (v - hb.low);  // keep the rise
    setHeightBrush(ch);
  });
  box.querySelectorAll('[data-row]').forEach(b => b.onclick = () => { $('#value').value = hex(+b.dataset.row); buildHeightPanel(); });
  const st = $('#hbStairs'); if (st) st.onchange = () => { hb.stairs = st.checked; };
  const all = $('#hbAll'); if (all) all.ontoggle = () => { S.heightMoreOpen = all.open; };
  // The picture: the square seen from above, lighter where it's lower.
  const cv = $('#hbPreview'), g = cv.getContext('2d');
  g.fillStyle = '#000'; g.fillRect(0, 0, 48, 48);
  if (row) {
    const ls = [...Array(256).keys()].map(i => shapeLevelAt(row, i % 16, i >> 4));
    // Shaded on the same scale as the map: the place's lowest ground to its highest, stretched to take in this square.
    const placed = [...new Set((m.grids.shape || []).flat())].map(v => cellHeightPx(m.shapes[v]) / 8);
    const lo = Math.min(...placed, ...ls), span = Math.max(...placed, ...ls) - lo || 1;
    ls.forEach((l, i) => { g.fillStyle = `rgba(80,160,255,${(0.1 + 0.65 * (l - lo) / span).toFixed(2)})`; g.fillRect((i % 16) * 3, (i >> 4) * 3, 3, 3); });
  }
}
// Height's blue grows with the ground's real height, from this place's lowest
// ground (no blue) to its highest; the height numbers themselves are only table rows.
function heightShade(m) {
  const hs = (m.shapes || []).map(cellHeightPx), inUse = new Set((m.grids.shape || []).flat());
  const used = [...inUse].map(v => hs[v] ?? 0), lo = used.length ? Math.min(...used) : 0, span = Math.max(...used) - lo || 1;
  return v => { const f = ((hs[v] ?? lo) - lo) / span; return f > 0 ? `rgba(80,160,255,${(0.1 + 0.65 * f).toFixed(2)})` : null; };
}
// Pixels to levels (8 px each), to a half-level where a ramp's middle falls between.
function levelOf(px) { return Math.round(px / 4) / 2; }
// Pixels at a square's middle: flat kinds their level, ramps halfway, other
// kinds their highest sample (only bends, folds and picked kinds read the third).
const SHAPE_THREE = new Set([5, 6, 10, 11, 12, 13]);
function cellHeightPx(r) {
  if (!r) return 0;
  const k = r[0] & 15, a = lvSigned(r[1]), b = lvSigned(r[2]);
  if (HB_FLAT.has(k)) return 8 * a;
  if (k === 1 || k === 2) return 4 * (a + b);
  return 8 * (SHAPE_THREE.has(k) ? Math.max(a, b, lvSigned(r[3] ?? 0)) : Math.max(a, b));
}

function buildBrushes() {
  const box = $('#brushes'); box.innerHTML = '';
  const order = ['walk', 'block', 'move', 'search'];
  const brushes = S.names.collision.filter(r => r.lo === r.hi && /brush/.test(r.editor) && !/advanced/.test(r.editor))
    .sort((a, b) => order.indexOf(a.category) - order.indexOf(b.category));
  for (const r of brushes) {
    const b = document.createElement('button');
    b.innerHTML = `<i style="background:${r.color && r.color !== '#00000000' ? r.color : 'transparent'}"></i>${esc(r.name)}`;
    b.title = r.meaning;
    b.dataset.value = r.lo;
    b.onclick = () => { $('#value').value = hex(r.lo); for (const o of box.children) o.classList.toggle('on', o === b); };
    box.appendChild(b);
  }
}

// Draws window cells (x, y): their blocks, layer by layer, and the grid. What
// that needs is worked out once per redraw, not once per square.
function cellPainter() {
  const m = S.map, z = +$('#zoom').value, s = 16 * z, grid = $('#ovGrid').checked;
  const ls = visibleLayers().filter(l => S.show[l.index] && S.atlas[l.char_base]).map(l => ({
    img: S.atlas[l.char_base], alpha: S.alpha[l.index], ox: l.origin[0] + m.bounds[0] / 2, oy: l.origin[1] + m.bounds[1] / 2 }));
  return (ctx, x, y) => {
    ctx.fillStyle = '#000'; ctx.fillRect(x * s, y * s, s, s);
    for (const L of ls) {  // as at(m.blocks, l, x, y)
      const b = m.blocks?.[(L.oy + y) % 128]?.[(L.ox + x) % 128]; if (b == null) continue;
      const id = b & 0xfff; if (id >= m.metatile_count) continue;
      ctx.globalAlpha = L.alpha;
      ctx.drawImage(L.img, (id % 32) * 16, Math.floor(id / 32) * 16, 16, 16, x * s, y * s, s, s);
    }
    ctx.globalAlpha = 1;
    if (grid) { ctx.strokeStyle = 'rgba(255,255,255,0.12)'; ctx.strokeRect(x * s + .5, y * s + .5, s, s); }
  };
}

// Walkability and height, each square drawn where the game shows its ground:
// lower ground first, so raised squares sit on top.
function drawGroundOverlays(ctx) {
  const m = S.map, col = $('#ovCollision').checked, sh = $('#ovShape').checked;
  if (!col && !sh) return;
  const z = +$('#zoom').value, s = 16 * z, l = layer(), cells = [];
  const shade = heightShade(m);
  const ox = l.origin[0] + m.bounds[0] / 2, oy = l.origin[1] + m.bounds[1] / 2;  // as gridXY
  for (let y = 0; y < m.size[1]; y++) for (let x = 0; x < m.size[0]; x++) {
    const gx = (ox + x) % 128, gy = (oy + y) % 128, h = heightPx(l, gx, gy);
    cells.push([h, x, y - h / 16, gx, gy]);
  }
  cells.sort((a, b) => a[0] - b[0]);
  // A colour per value, worked out once per redraw.
  const colours = new Map(), shades = new Map();
  const colourOf = v => { if (!colours.has(v)) colours.set(v, collisionColor(v)); return colours.get(v); };
  const shadeOf = v => { if (!shades.has(v)) shades.set(v, shade(v)); return shades.get(v); };
  for (const [, x, y, gx, gy] of cells) {
    if (col) { const c = colourOf(m.grids.collision?.[gy]?.[gx]); if (c) { ctx.fillStyle = c; ctx.fillRect(x * s, y * s, s, s); } }
    if (sh) {
      const v = m.grids.shape?.[gy]?.[gx], c = shadeOf(v);
      if (c) {
        ctx.fillStyle = c; ctx.fillRect(x * s, y * s, s, s);
        if (z >= 2 && S.advanced) { ctx.fillStyle = '#fff'; ctx.fillText(hex(v), x * s + s / 2, y * s + s / 2); }
      }
    }
  }
}

function ctxSetup(ctx) {
  const z = +$('#zoom').value;
  ctx.imageSmoothingEnabled = false;
  ctx.font = `${Math.max(8, 5 * z)}px monospace`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.lineWidth = 1;
}

function drawAll() {
  const m = S.map; if (!m) return;
  const z = +$('#zoom').value, [w, h] = m.size, cv = $('#cv'), ctx = cv.getContext('2d');
  const ov = $('#ov'), W = w * 16 * z, H = h * 16 * z;
  if (cv.width !== W || cv.height !== H) {
    cv.width = W; cv.height = H; ov.width = W; ov.height = H;
  } else {
    // Same size: clear rather than reallocate, and start from a fresh state as a resize would.
    for (const c of [ctx, ov.getContext('2d')]) {
      c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = 1; c.globalCompositeOperation = 'source-over';
      c.setLineDash([]); c.clearRect(0, 0, W, H);
    }
  }
  ctxSetup(ctx);
  const paint = cellPainter();
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) paint(ctx, x, y);
  drawGroundOverlays(ctx); drawStand(ctx);
  markPending(ctx); drawMarkers(ctx); drawDoors(ctx); drawEvents(ctx); drawPoints(ctx); drawCellMark(ctx);
}

// A whole redraw at most once a frame: dragging a brush with an overlay on
// would otherwise redraw the map for every square it crosses.
let redrawQueued = false;
function drawAllSoon() {
  if (redrawQueued) return;
  redrawQueued = true;
  requestAnimationFrame(() => { redrawQueued = false; drawAll(); });
}
function redrawCells(cells) {
  if ($('#ovCollision').checked || $('#ovShape').checked || $('#ovStand').checked) return drawAllSoon();  // raised squares overlap other cells
  const ctx = $('#cv').getContext('2d'); ctxSetup(ctx);
  const paint = cellPainter();
  for (const [x, y] of cells) paint(ctx, x, y);
  markPending(ctx); drawMarkers(ctx); drawDoors(ctx); drawEvents(ctx); drawPoints(ctx); drawCellMark(ctx);
}

// Window cell of grid cell (gx, gy) on layer l, or null when outside the window.
function windowXY(l, gx, gy) {
  const m = S.map;
  const x = ((gx - l.origin[0] - m.bounds[0] / 2) % 128 + 128) % 128;
  const y = ((gy - l.origin[1] - m.bounds[1] / 2) % 128 + 128) % 128;
  return x < m.size[0] && y < m.size[1] ? [x, y] : null;
}

// The game stores collision, height, doors, chests and people at their ground
// position and draws them raised by the ground's height (field/terrain.c: a
// cell's shape row holds a kind and samples in 8-px units). These convert.
function heightPx(l, gx, gy) {
  return cellHeightPx(S.map.shapes?.[S.map.grids.shape?.[gy]?.[gx]]);
}
// Window position (cells, possibly fractional) where ground cell (gx, gy) shows.
function groundXY(l, gx, gy) {
  const w = windowXY(l, gx, gy); if (!w) return null;
  return [w[0], w[1] - heightPx(l, gx, gy) / 16];
}
// Ground cell drawn under window pixel (px, py) (unzoomed): the one whose raised
// square covers it, the highest when terrain overlaps.
function groundAt(l, px, py) {
  const m = S.map, wx = Math.floor(px / 16), row = Math.floor(py / 16);
  if (wx < 0 || wx >= m.size[0]) return null;
  let best = null;
  for (let wy = Math.max(0, row - 16); wy < m.size[1] && wy <= row + 72; wy++) {
    const [gx, gy] = gridXY(l, wx, wy), h = heightPx(l, gx, gy), top = wy * 16 - h;
    if (py >= top && py < top + 16 && (!best || h > best.h)) best = { gx, gy, h };
  }
  return best ? [best.gx, best.gy] : (row >= 0 && row < m.size[1] ? gridXY(l, wx, row) : null);
}
// Window pixels of a thing at map pixels (x, z) on the ground, as drawn.
function entityXY(x, z) {
  const m = S.map, l = m.layers[0], wx = x - m.bounds[0] * 8, wz = z - m.bounds[1] * 8;
  const [gx, gy] = gridXY(l, Math.floor(wx / 16), Math.floor(wz / 16));
  return [wx, wz - heightPx(l, gx, gy)];
}
// Map pixels on the ground for window pixel (px, py): the inverse of entityXY.
function groundPx(px, py) {
  const m = S.map, l = m.layers[0], g = groundAt(l, px, py);
  const h = g ? heightPx(l, g[0], g[1]) : 0;
  return [Math.round(px) + m.bounds[0] * 8, Math.round(py + h) + m.bounds[1] * 8];
}
function mousePx(e) { const z = +$('#zoom').value, r = $('#cv').getBoundingClientRect(); return [(e.clientX - r.left) / z, (e.clientY - r.top) / z]; }

// Actions that reload a place save what you've painted first, rather than ask to lose it.
async function saveFirst() {
  if (dirtyCount()) await doSave();
  if (!dirtyCount()) return true;
  if (!confirm(T("Your changes couldn't be saved:\n\n{error}\n\nThrow them away and carry on?", { error: S.saveError || T('The save was refused.') }))) return false;
  S.pending.clear(); S.markerMoves.clear(); S.tableEdits.clear(); S.undo = []; S.redo = [];
  updateButtons();
  return true;
}

function dirtyCount() { return S.pending.size + S.markerMoves.size + S.tableEdits.size; }

function drawMarkers(ctx) {
  const m = S.map, z = +$('#zoom').value, s = 16 * z, l = layer();
  for (const mk of m.markers || []) {
    const w = groundXY(l, mk.x, mk.z); if (!w) continue;
    const moved = S.markerMoves.has(mk.index);
    ctx.lineWidth = S.tool === 'chest' ? 2 : 1;
    ctx.strokeStyle = moved ? '#7ee787' : '#e0b84a';
    ctx.strokeRect(w[0] * s + 2, w[1] * s + 2, s - 4, s - 4);
    const c = S.chests?.find(c => c.code === mk.id);  // by its code: a moved chest keeps its picture
    if (c?.chest && c.value >> 20 === 1 && S.icons[c.value & 0xffff]?.complete) ctx.drawImage(S.icons[c.value & 0xffff], w[0] * s + 2, w[1] * s + 2, s - 4, s - 4);
    else if (z >= 2 && S.advanced) { ctx.fillStyle = moved ? '#7ee787' : '#e0b84a'; ctx.fillText(hex(mk.id), w[0] * s + s / 2, w[1] * s + s / 2); }
  }
  if (S.tool === 'chest' && S.chestAt) {
    const w = groundXY(l, S.chestAt.x, S.chestAt.z);
    if (w) { ctx.lineWidth = 2; ctx.setLineDash([4, 3]); ctx.strokeStyle = '#58a6ff'; ctx.strokeRect(w[0] * s + 1, w[1] * s + 1, s - 2, s - 2); ctx.setLineDash([]); }
  }
  ctx.lineWidth = 1;
}

// Outline unsaved cells that fall inside the edit layer's window.
function markPending(ctx) {
  const z = +$('#zoom').value, s = 16 * z, l = layer();
  ctx.strokeStyle = 'rgba(224,184,74,0.9)';
  for (const key of S.pending.keys()) {
    const parts = key.split(':'), w = parts[0] === 'block' ? windowXY(l, +parts[1], +parts[2]) : groundXY(l, +parts[1], +parts[2]);
    if (w) ctx.strokeRect(w[0] * s + .5, w[1] * s + .5, s - 1, s - 1);
  }
}

function drawPalette() {
  const m = S.map, img = S.atlas[layer().char_base], cv = $('#palette');
  if (!img) { cv.width = cv.height = 0; return; }
  const sc = 2, cols = 8, n = m.metatile_count, rows = Math.ceil(n / cols);
  cv.width = cols * 16 * sc; cv.height = rows * 16 * sc;
  const ctx = cv.getContext('2d'); ctx.imageSmoothingEnabled = false;
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, cv.width, cv.height);
  for (let i = 0; i < n; i++)
    ctx.drawImage(img, (i % 32) * 16, Math.floor(i / 32) * 16, 16, 16, (i % cols) * 16 * sc, Math.floor(i / cols) * 16 * sc, 16 * sc, 16 * sc);
  for (const r of (m.retired || [])) {  // retired to make room for custom tiles
    if (r >= n) continue;
    ctx.fillStyle = 'rgba(0,0,0,0.75)'; ctx.fillRect((r % cols) * 16 * sc, Math.floor(r / cols) * 16 * sc, 16 * sc, 16 * sc);
  }
  if (S.block != null && S.block < n) {
    ctx.strokeStyle = '#e0b84a'; ctx.lineWidth = 2;
    ctx.strokeRect((S.block % cols) * 16 * sc + 1, Math.floor(S.block / cols) * 16 * sc + 1, 16 * sc - 2, 16 * sc - 2);
  }
  drawPick();
}

function drawPick() {
  const img = S.atlas[layer().char_base], ctx = $('#pickCv').getContext('2d');
  ctx.imageSmoothingEnabled = false; ctx.clearRect(0, 0, 16, 16);
  if (S.block == null || !img) { $('#pickText').textContent = localWords(T('Pick a block below, or ⌥-click the map')); return; }
  ctx.drawImage(img, (S.block % 32) * 16, Math.floor(S.block / 32) * 16, 16, 16, 0, 0, 16, 16);
  $('#pickText').innerHTML = T('block {b} on L{l}', { b: `<b>${hex(S.block)}</b>`, l: layer().index });
}

$('#palette').addEventListener('click', e => {
  const r = e.target.getBoundingClientRect(), cols = 8, s = 32;
  const i = Math.floor((e.clientY - r.top) / s) * cols + Math.floor((e.clientX - r.left) / s);
  if (i < S.map.metatile_count) {
    if ((S.map.retired || []).includes(i)) return status(`<span class="warn">${T('That block was retired to make room for custom tiles.')}</span>`);
    S.block = i; setTool('block'); drawPalette();
  }
});

// ---- editing ----------------------------------------------------------------
function gridOf(plane) { return plane === 'block' ? S.map.blocks : S.map.grids[plane]; }

function setValue(plane, gx, gy, value) {
  const g = gridOf(plane), before = g[gy][gx];
  if (before === value) return;
  g[gy][gx] = value;
  S.stroke.push({ plane, gx, gy, before, after: value });
  trackPending(`${plane}:${gx}:${gy}`, before, value);
}

// An edit undone back to the file's value has nothing left to save.
function trackPending(key, before, value) {
  if (!S.pending.size) S.saved = new Map();  // what the files hold now
  if (!S.saved.has(key)) S.saved.set(key, before);
  if (S.saved.get(key) === value) S.pending.delete(key); else S.pending.set(key, value);
}

// The grid square a paint stroke touches at window cell (x, y): blocks are drawn
// where they are; walkability and height belong to the ground under the cursor.
function strokeCell(x, y) {
  const l = layer();
  return S.tool === 'block' || !S.mouse ? gridXY(l, x, y) : (groundAt(l, S.mouse[0], S.mouse[1]) || gridXY(l, x, y));
}
// Grid squares from a to b, both included, in a line (no gaps when the mouse moves fast).
function cellsBetween(a, b) {
  const out = [], dx = Math.abs(b[0] - a[0]), dy = Math.abs(b[1] - a[1]), sx = Math.sign(b[0] - a[0]), sy = Math.sign(b[1] - a[1]);
  if (dx > 32 || dy > 32) return [b];  // a jump across the place (or the grid's wrap): just the square
  let [x, y] = a, err = dx - dy;
  for (;;) {
    out.push([x, y]);
    if (x === b[0] && y === b[1]) return out;
    const e2 = 2 * err;
    if (e2 > -dy) { err -= dy; x += sx; }
    if (e2 < dx) { err += dx; y += sy; }
  }
}
function stairsStroke() {
  const hb = S.hb;
  return S.tool === 'shape' && hb && hb.stairs && ['ramp', 'steps'].includes(hb.pattern) && hb.exact == null;
}
// A drag moved to window cell (x, y): paint every square since the last one.
// Stairs stay on the line they started on and climb one square at a time, so
// raised steps hiding the ground behind them can't make the stroke jump ahead.
function paintTo(x, y) {
  const m = S.map;
  if (x < 0 || y < 0 || x >= m.size[0] || y >= m.size[1]) return;
  const g = strokeCell(x, y), from = S.strokeAt;
  let path;
  if (stairsStroke() && S.climbFrom) {
    const [cx, cy] = S.climbFrom, d = S.hb.dir, along = d === 'left' || d === 'right';
    const sign = d === 'right' || d === 'down' ? 1 : -1;
    const k = sign * (along ? g[0] - cx : g[1] - cy), last = S.climbK || 0;
    if (k <= last) return;
    const next = last + 1, cell = along ? [cx + sign * next, cy] : [cx, cy + sign * next];
    if (cell[0] < 0 || cell[1] < 0 || cell[0] > 127 || cell[1] > 127) return;  // the grid's edge
    S.climbK = next;
    path = [cell];
  } else {
    path = from ? cellsBetween(from, g).slice(1) : [g];
  }
  if (!path.length) return;
  for (const [gx, gy] of path) paintGround(gx, gy);
  S.strokeAt = path[path.length - 1];
  if (path.length === 1 && path[0][0] === g[0] && path[0][1] === g[1]) redrawCells([[x, y]]); else drawAllSoon();
}

function paintAt(x, y) {
  const m = S.map;
  if (x < 0 || y < 0 || x >= m.size[0] || y >= m.size[1]) return;
  const [gx, gy] = strokeCell(x, y);
  S.strokeAt = [gx, gy]; S.climbK = 0;
  paintGround(gx, gy);
  redrawCells([[x, y]]);
}

function paintGround(gx, gy) {
  const m = S.map;
  if (S.tool === 'block') {
    if (S.block == null) return status(`<span class="warn">${T('Pick a block first.')}</span>`);
    setValue('block', gx, gy, (m.blocks[gy][gx] & 0xf000) | S.block);  // keep the cell's flags
  } else if (S.tool === 'collision' || S.tool === 'shape') {
    const v = parseInt($('#value').value, 16);
    if ($('#value').value.trim() === '') return status(`<span class="warn">${S.tool === 'shape' ? T('Pick a height on the right first.') : T('Pick a brush on the right first.')}</span>`);
    if (isNaN(v) || v < 0 || v > 0xff) return status(`<span class="err">${T('That value should be 0 to ff.')}</span>`);
    if (S.tool === 'collision' && m.markers?.some(k => k.x === gx && k.z === gy)) return status(`<span class="warn">${T('That square holds a chest or stone. Move or remove it first.')}</span>`);
    const value = S.tool === 'shape' ? shapeBrushAt(gx, gy) : v;
    if (value === undefined) return status(`<span class="warn">${T('The stairs have reached the highest or lowest level the game can hold.')}</span>`);
    if (value == null) return status(`<span class="err">${T('This place already has {n} heights, the most the game can hold. Reuse one of them.', { n: 256 })}</span>`);
    setValue(S.tool, gx, gy, value);
  }
}

// Fill: every square connected to the one clicked (sideways, not diagonally)
// that has the same block on this layer, or the same walkability or height,
// takes the brush. Only squares this place shows are filled. One undo step.
function fillAt(x, y) {
  const m = S.map, l = layer(), tool = S.tool;
  if (x < 0 || y < 0 || x >= m.size[0] || y >= m.size[1]) return;
  let value, read, write;
  if (tool === 'block') {
    if (S.block == null) return status(`<span class="warn">${T('Pick a block first.')}</span>`);
    read = (gx, gy) => m.blocks[gy][gx] & 0xfff;
    write = (gx, gy) => setValue('block', gx, gy, (m.blocks[gy][gx] & 0xf000) | S.block);
    value = S.block;
  } else {
    if ($('#value').value.trim() === '') return status(`<span class="warn">${tool === 'shape' ? T('Pick a height on the right first.') : T('Pick a brush on the right first.')}</span>`);
    value = parseInt($('#value').value, 16);
    if (isNaN(value) || value < 0 || value > 0xff) return status(`<span class="err">${T('That value should be 0 to ff.')}</span>`);
    const g = m.grids[tool];
    read = (gx, gy) => g[gy][gx];
    write = (gx, gy) => { if (!(tool === 'collision' && m.markers?.some(k => k.x === gx && k.z === gy))) setValue(tool, gx, gy, value); };
  }
  // The grid cells this place shows (at most 128 by 128: windows wrap), so the fill is bounded.
  const shown = new Set();
  for (let wy = 0; wy < m.size[1]; wy++) for (let wx = 0; wx < m.size[0]; wx++) shown.add(gridXY(l, wx, wy).join(','));
  const [sx, sy] = tool === 'block' || !S.mouse ? gridXY(l, x, y) : (groundAt(l, S.mouse[0], S.mouse[1]) || gridXY(l, x, y));
  const from = read(sx, sy);
  if (from === value) return;
  const seen = new Set([`${sx},${sy}`]), queue = [[sx, sy]];
  for (let i = 0; i < queue.length; i++) {
    const [gx, gy] = queue[i];
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = (gx + dx + 128) % 128, ny = (gy + dy + 128) % 128, k = `${nx},${ny}`;
      if (seen.has(k) || !shown.has(k) || read(nx, ny) !== from) continue;
      seen.add(k); queue.push([nx, ny]);
    }
  }
  for (const [gx, gy] of queue) write(gx, gy);
  drawAll();
  const n = S.stroke.length;  // squares holding a chest or stone keep their walkability
  status(!n ? T('Nothing changed.') : n === 1 ? T('Filled 1 square. Save to keep it.') : T('Filled {n} squares. Save to keep them.', { n }));
}

function eyedrop(x, y) {
  const l = layer(), m = S.map;
  if (S.tool === 'collision' || S.tool === 'shape') {
    const g = S.mouse && groundAt(l, S.mouse[0], S.mouse[1]) || gridXY(l, x, y);
    $('#value').value = hex(m.grids[S.tool]?.[g[1]]?.[g[0]] ?? 0);
    if (S.tool === 'shape') buildHeightPanel();
  }
  else { S.block = at(m.blocks, l, x, y) & 0xfff; setTool('block'); drawPalette(); }
}

function applyChanges(list, which) {
  for (const c of list) {
    if (c.plane === 'marker') { setMarker(c.index, c[which]); continue; }
    if (c.plane === 'table') { setTableRows(c.table, clone(c[which]), c.base); continue; }
    const g = gridOf(c.plane), now = g[c.gy][c.gx];
    g[c.gy][c.gx] = c[which];
    trackPending(`${c.plane}:${c.gx}:${c.gy}`, now, c[which]);
  }
  drawAll(); updateButtons(); renderTable(); staleStand();
  // What the status line said (and its buttons, like "Move to the nearest good spot") was about the change just undone or redone.
  status(which === 'before' ? T('Undone. Save to keep it that way.') : T('Redone. Save to keep it.'));
}

// Marker state is {x, z, restore, oldCol, newCol}; collision codes of the two
// cells are shown locally, and the server rewrites them itself on save.
function setMarker(index, st) {
  const mk = S.map.markers.find(m => m.index === index), col = S.map.grids.collision;
  const cur = S.markerMoves.get(index);
  // undo the current local collision change, if any
  if (cur) { col[cur.z][cur.x] = cur.newCol; col[mk.orig[1]][mk.orig[0]] = mk.id; }
  if (st.x === mk.orig[0] && st.z === mk.orig[1]) { S.markerMoves.delete(index); mk.x = st.x; mk.z = st.z; return; }
  const newCol = col[st.z][st.x];
  col[mk.orig[1]][mk.orig[0]] = st.restore; col[st.z][st.x] = mk.id;
  mk.x = st.x; mk.z = st.z;
  S.markerMoves.set(index, { x: st.x, z: st.z, restore: st.restore, newCol });
}

function restoreCode(gx, gy, id) {
  // most common neighbouring collision code that isn't the marker's own
  const col = S.map.grids.collision, count = new Map();
  for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
    const v = col[gy + dy]?.[gx + dx];
    if (v != null && v !== id && !(v >= 100 && v <= 239)) count.set(v, (count.get(v) || 0) + 1);
  }
  return [...count].sort((a, b) => b[1] - a[1])[0]?.[0] ?? 0;
}

function finishStroke() {
  if (S.stroke && S.stroke.length) { S.undo.push(S.stroke); S.redo = []; staleStand(); }
  S.stroke = null; updateButtons();
}

function updateButtons() {
  const serverRedo = !S.redo.length && HIST.next && !dirtyCount();
  $('#undo').disabled = !S.undo.length && !HIST.last;
  $('#undo').title = localWords(S.undo.length ? T('Undo your last unsaved change (⌘Z)') : historyTitle(false) + (HIST.last ? ' (⌘Z)' : ''));
  $('#redo').disabled = !S.redo.length && !serverRedo;
  $('#redo').title = localWords(S.redo.length ? T('Redo (⇧⌘Z)') : !HIST.next ? T('Nothing to redo')
    : dirtyCount() ? T('Save your changes first, or undo them') : historyTitle(true) + ' (⇧⌘Z)');
  $('#save').disabled = !dirtyCount();
  $('#save').textContent = dirtyCount() ? T('Save ({n})', { n: dirtyCount() }) : T('Saved');
}

// The scene's data tables are for Advanced, and for Move people, which drags their rows.
function showScenePanel() {
  const full = S.advanced || S.tool === 'points';
  const many = $('#sceneSel').options.length > 1;
  $('#sceneTitle').style.display = $('#scenePanel').style.display = full || many ? '' : 'none';
  $('#tableSel').style.display = $('#tableView').style.display = full ? '' : 'none';
}

function setTool(t) {
  // Walkability and height each keep their own brush.
  S.values = S.values || {};
  if (S.tool === 'collision' || S.tool === 'shape') S.values[S.tool] = $('#value').value;
  if (t === 'collision' || t === 'shape') $('#value').value = S.values[t] ?? '';
  if (t === 'collision') for (const o of $('#brushes').children) o.classList.toggle('on', parseInt($('#value').value, 16) === +o.dataset.value);
  S.tool = t;
  $('#heightPanel').style.display = $('#heightTitle').style.display = t === 'shape' ? '' : 'none';
  if (t === 'shape' && S.map) buildHeightPanel();
  const painting = t === 'block' || t === 'stamp' || S.advanced;
  for (const id of ['#blocksTitle', '#pick', '#paletteWrap']) $(id).style.display = painting ? '' : 'none';
  showScenePanel();
  for (const b of document.querySelectorAll('#tools button')) b.classList.toggle('on', b.dataset.tool === t);
  $('#valueBox').style.display = (t === 'collision' || t === 'shape') ? '' : 'none';
  $('#fillBox').style.display = (t === 'block' || t === 'collision' || t === 'shape') ? '' : 'none';
  $('#brushes').style.display = $('#brushTitle').style.display = t === 'collision' ? '' : 'none';
  $('#stampPanel').style.display = $('#stampTitle').style.display = t === 'stamp' ? 'block' : 'none';
  if (t === 'stamp') setStampMode(S.clip ? 'paste' : 'copy');
  $('#chestPanel').style.display = $('#chestTitle').style.display = t === 'chest' ? 'block' : 'none';
  if (t !== 'chest') chestDeselect();
  $('#doorPanel').style.display = $('#doorTitle').style.display = t === 'doors' ? 'block' : 'none';
  $('#evPanel').style.display = $('#evTitle').style.display = t === 'events' ? 'block' : 'none';
  if (t === 'events' && S.map) loadEvents();
  if (t !== 'doors') doorDeselect();
  clearOverlay();
  if (t === 'collision') $('#ovCollision').checked = true;
  if (t === 'shape') $('#ovShape').checked = true;
  if (S.map) drawAll();
}

function cellFromEvent(e) {
  const z = +$('#zoom').value, r = $('#cv').getBoundingClientRect();
  return [Math.floor((e.clientX - r.left) / (16 * z)), Math.floor((e.clientY - r.top) / (16 * z))];
}

let painting = false, lastCell = null;
$('#cv').addEventListener('mousedown', e => {
  if (!S.map || S.saving) return;  // see doSave
  const [x, y] = cellFromEvent(e);
  S.mouse = mousePx(e);
  if (e.altKey) { eyedrop(x, y); return; }
  if (S.tool === 'view') return;
  if (S.tool === 'points') { startPointDrag(e); return; }
  if (S.tool === 'stamp') { stampDown(x, y); return; }
  if (S.tool === 'doors') { const g = groundAt(S.map.layers[0], S.mouse[0], S.mouse[1]); if (g) doorSelect(g[0], g[1]); return; }
  if (S.tool === 'events') { evClick(e, x, y); return; }
  if (S.tool === 'chest') {
    const [gx, gy] = groundAt(layer(), S.mouse[0], S.mouse[1]) || gridXY(layer(), x, y);
    const mk = S.map.markers.find(mk => mk.x === gx && mk.z === gy);
    if (mk && S.map.markers_editable) S.drag = mk;  // a click without moving selects it
    else chestSelect(gx, gy, mk || null);
    return;
  }
  if ($('#fill').checked && ['block', 'collision', 'shape'].includes(S.tool)) { S.stroke = []; fillAt(x, y); finishStroke(); return; }
  painting = true; S.stroke = []; S.climbFrom = null; lastCell = `${x},${y}`; paintAt(x, y);
});
window.addEventListener('mouseup', e => {
  if (painting) { painting = false; finishStroke(); }
  if (S.tool === 'stamp' && S.sel && S.sel.dragging) stampUp();
  if (S.pointDrag) endPointDrag(e);
  if (S.drag) {
    const mk = S.drag; S.drag = null;
    const [x, y] = cellFromEvent(e), m = S.map;
    if (x < 0 || y < 0 || x >= m.size[0] || y >= m.size[1]) return;
    const [mx, my] = mousePx(e), [gx, gy] = groundAt(layer(), mx, my) || gridXY(layer(), x, y);
    if (gx === mk.x && gy === mk.z) return chestSelect(gx, gy, mk);
    if (m.markers.some(o => o !== mk && o.x === gx && o.z === gy)) return status(`<span class="err">${T("There's already a chest there.")}</span>`);
    const under = m.grids.collision?.[gy]?.[gx];
    if (under >= 1 && under <= 239) return status(`<span class="err">${T('That square already does something, like a door or a sign. Pick another for the chest.')}</span>`);
    mk.orig = mk.orig || [mk.x, mk.z];
    const before = { x: mk.x, z: mk.z, restore: S.markerMoves.get(mk.index)?.restore ?? 0 };
    const after = { x: gx, z: gy, restore: restoreCode(mk.orig[0], mk.orig[1], mk.id) };
    setMarker(mk.index, after);
    S.undo.push([{ plane: 'marker', index: mk.index, before, after }]); S.redo = [];
    drawAll(); updateButtons();
    status(S.advanced ? T("Marker {id} → {x},{y}; old cell's collision becomes {code}. Save to apply.", { id: `<b>${hex(mk.id)}</b>`, x: gx, y: gy, code: `<b>${hex(after.restore)}</b>` }) : T('Moved. Save to keep it.'));
  }
});
$('#cv').addEventListener('mousemove', e => {
  const m = S.map; if (!m) return;
  const [x, y] = cellFromEvent(e);
  S.mouse = mousePx(e);
  const g0 = groundAt(layer(), S.mouse[0], S.mouse[1]);
  const key = S.tool === 'block' || !g0 ? `${x},${y}` : `${g0[0]},${g0[1]}`;
  if (painting && key !== lastCell && !S.saving) { lastCell = key; paintTo(x, y); }
  if (S.tool === 'stamp') stampMove(x, y);
  if (x < 0 || y < 0 || x >= m.size[0] || y >= m.size[1]) return;
  const parts = visibleLayers().map(l => {
    const raw = at(m.grids.metatile, l, x, y), v = at(m.blocks, l, x, y);
    if (v == null) return `L${l.index} –`;
    return `L${l.index} <b>${hex(v & 0xfff)}</b>${(raw & 0xfff) === 0xfff ? '*' : ''}${v >> 12 ? '/' + hex(v >> 12) : ''}`;
  });
  // what the ground under the cursor does (raised ground is stored further down the grid)
  const l = layer(), [gx, gy] = g0 || gridXY(l, x, y);
  const col = m.grids.collision?.[gy]?.[gx], mk = (m.markers || []).find(k => k.x === gx && k.z === gy);
  const what = mk ? `<b>${esc((S.legend[String(mk.id)] || [T('Chest')])[0])}</b>` : `<b>${esc(collisionName(col))}</b>`;
  // Over a person in Move people: who it is and, once their lines are loaded, what they say.
  if (S.tool === 'points') {
    const t = table();
    if (t && t.kind === 'placements') {
      const rows = rowsOf(t);
      const near = rows.map((r, i) => { if (r.sprite < 0) return null; const [x, y] = pointPx(t, r); return [Math.hypot(x - S.mouse[0], y - S.mouse[1]), i]; })
        .filter(Boolean).sort((a, b) => a[0] - b[0])[0];
      if (near && near[0] < 10) {
        const i = near[1], actor = actorNumber(rows, i), who = `<b>${esc(S.names.spriteById?.[rows[i].sprite]?.name || T('This person'))}</b>`;
        const lines = peopleLines(t);
        if (lines) {
          const line = lines.find(e => e.actor === actor && e.kind === 'talk' && e.text);
          return status(line ? T('{who} says: “{text}”', { who, text: esc(shortText(line.text)) }) : T("{who} doesn't say anything here yet.", { who }));
        }
        return status(who);
      }
    }
  }
  // Over a person in Events: who it is and what they say.
  if (S.tool === 'events' && EV.data) {
    const p = personAt(S.mouse[0], S.mouse[1]);
    if (p) {
      const line = EV.data.events.find(e => e.actor === p.actor && e.kind === 'talk' && e.text);
      const who = `<b>${esc(p.name || T('This person'))}</b>`;
      return status(line ? T('{who} says: “{text}”', { who, text: esc(shortText(line.text)) }) : T("{who} doesn't say anything here yet.", { who }));
    }
  }
  status(S.advanced
    ? T('cell {cell} (ground {ground}) · blocks {blocks} · {what} · height {height} ({px} px) on L{layer}', {
      cell: `<b>${x},${y}</b>`, ground: `${gx},${gy}`, blocks: parts.join(' '), what,
      height: `<b>${hex(m.grids.shape?.[gy]?.[gx])}</b>`, px: heightPx(l, gx, gy), layer: l.index })
    // The ground square: what doors, chests and Check name, even on raised ground.
    : T('{what} · level {n} · cell {cell}', { what, n: levelOf(heightPx(l, gx, gy)), cell: `${gx},${gy}` }));
});

// ---- scenes and their tables ---------------------------------------------------
function clone(v) { return JSON.parse(JSON.stringify(v)); }
const KIND_ORDER = ['entrances', 'placements', 'exits', 'events', 'regions'];
const KIND_LABEL = { entrances: T('Arrival points'), placements: T('People'), exits: T('Exits'), events: T('Events'), regions: T('Areas') };
// A table's kind as its note above the rows names it.
const KIND_WORD = { entrances: T('entrances'), placements: T('placements'), exits: T('exits'), events: T('events'), regions: T('regions') };
// gValeHome_ActorPlacementsAfterKalay -> "After Kalay"; plain table -> "normal"
function variantName(sym) {
  const kinds = /_?(Entrances|Exits|ActorPlacements|Placements|Triggers|Regions)(.*)$/, m = sym.match(kinds);
  // The stage is named after the table's kind (gVale_TriggersAfterKalay) or before
  // it, following the place's name (gValePlaza_StormTriggers).
  const before = m ? sym.slice(0, m.index).replace(/^g/, '') : '', lead = before.includes('_') ? before.split('_').pop() : '';
  const v = ((m && m[2]) || lead).replace(/^_/, '').replace(/([a-z])([A-Z])/g, '$1 $2');
  return (v || T('normal')) + (S.advanced ? ` [${sym}]` : '');
}

async function loadScenes(keepSelection) {
  const prevScene = $('#sceneSel').value, prevTable = $('#tableSel').value;
  const map = S.map;
  if (!S.allScenes) S.allScenes = await api('/api/scenes');
  const r = await api(`/api/map/${map.number}/scenes`);
  if (S.map !== map) return;  // another place opened meanwhile
  S.scenes = Array.isArray(r) ? r : [];
  const sel = $('#sceneSel'); sel.innerHTML = '';
  if (!S.scenes.length) { $('#tableSel').innerHTML = ''; $('#tableView').innerHTML = `<div class="note">${esc(r.error || T('No scene uses this map.'))}</div>`; return; }
  for (const sc of S.scenes) sel.insertAdjacentHTML('beforeend', `<option value="${sc.id}">${esc(S.names.sceneById[sc.id]?.label || sc.name || T('scene {n}', { n: sc.id }))}${S.advanced ? ' [' + sc.id + ']' : ''}</option>`);
  if (keepSelection && [...sel.options].some(o => o.value === prevScene)) sel.value = prevScene;
  fillTables(keepSelection ? prevTable : null);
}

function scene() { return S.scenes.find(s => String(s.id) === $('#sceneSel').value); }

function fillTables(prefer) {
  const sc = scene(), sel = $('#tableSel'); sel.innerHTML = '';
  if (!sc) return;
  const tables = [...sc.tables].sort((a, b) => KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind));
  for (const t of tables)
    sel.insertAdjacentHTML('beforeend', `<option value="${esc(t.symbol)}">${KIND_LABEL[t.kind]}: ${esc(variantName(t.symbol))}${t.overridden ? ' ✎' : ''}${t.editable ? '' : ' ' + T('(read-only)')}</option>`);
  const def = tables.find(t => t.kind === 'entrances') || tables[0];
  sel.value = prefer && tables.some(t => t.symbol === prefer) ? prefer : (def ? def.symbol : '');
  renderTable(); drawAll();
}

function table() { const sc = scene(); return sc && sc.tables.find(t => t.symbol === $('#tableSel').value); }
function rowsOf(t) { return S.tableEdits.has(t.symbol) ? S.tableEdits.get(t.symbol).rows : t.rows; }

// Replace a table's rows (undoable through applyChanges); base = rows before any edit.
function setTableRows(t, rows, base) {
  if (JSON.stringify(rows) === JSON.stringify(base)) S.tableEdits.delete(t.symbol);
  else S.tableEdits.set(t.symbol, { overlay: scene().overlay, kind: t.kind, rows });
}

function editTable(t, mutate) {
  const before = clone(rowsOf(t)), after = clone(before);
  mutate(after);
  if (JSON.stringify(after) === JSON.stringify(before)) return;
  setTableRows(t, after, t.rows);
  S.undo.push([{ plane: 'table', table: t, before, after, base: t.rows }]); S.redo = [];
  updateButtons(); renderTable(); drawAll();
}

// As the game numbers people: the party's own sprites (0 to 7) are their own
// actors and take no slot; everyone else takes the next one from 8.
function actorNumber(rows, i) {
  if (rows[i].sprite <= 7) return rows[i].sprite;
  return 8 + rows.slice(0, i).filter(r => r.sprite > 7).length;
}

function pointPx(t, r) {  // map pixels on the ground -> window pixels, as drawn
  const sh = t.kind === 'placements' ? 16 : 0;
  return entityXY(r.x >> sh, r.z >> sh);
}

function drawPoints(ctx) {
  const t = S.map && table(); if (!t || !['entrances', 'placements'].includes(t.kind)) return;
  const z = +$('#zoom').value;
  // People kept at 0,0 wait off the map: one picture and a count, not a pile.
  let waiting = 0, corner = null;
  rowsOf(t).forEach((r, i) => {
    if ((t.kind === 'entrances' ? r.entrance : r.sprite) < 0) return;
    const [x, y] = pointPx(t, r), cx = x * z, cy = y * z, rad = 5 * z;
    const off = t.kind === 'placements' && r.x === 0 && r.z === 0;
    if (off) { if (waiting++) return; corner = [cx, cy, 0]; }
    ctx.lineWidth = 2;
    if (t.kind === 'entrances') {
      ctx.strokeStyle = '#3ddc84'; ctx.strokeRect(cx - rad, cy - rad, rad * 2, rad * 2);
      ctx.fillStyle = '#3ddc84'; ctx.fillText(r.entrance, cx, cy - rad - 6);
    } else {
      const img = spriteImage(r.sprite);
      if (img && img.complete && img.naturalWidth) {
        const w = img.naturalWidth * z, h = img.naturalHeight * z;
        // Feet at the point; one waiting at 0,0 is pulled down onto the canvas so it shows whole.
        const top = off ? Math.max(cy - h + 4 * z, 0) : cy - h + 4 * z, left = off ? Math.max(cx - w / 2, 0) : cx - w / 2;
        ctx.drawImage(img, left, top, w, h);
        if (off) corner = [left + w, top + 14, 1];
      } else {
        ctx.strokeStyle = r.x === 0 && r.z === 0 ? '#888' : '#ff5cf0';
        ctx.beginPath(); ctx.arc(cx, cy, rad, 0, 7); ctx.stroke();
      }
      if (S.advanced) { ctx.fillStyle = '#ff5cf0'; ctx.fillText(actorNumber(rowsOf(t), i), cx, cy - rad - 6); }
    }
  });
  if (waiting > 1) {
    // Beside the picture, inside the canvas (corner holds where the picture ended).
    const text = `×${waiting}`, tw = ctx.measureText(text).width;
    const bx = corner[2] ? corner[0] + 2 : Math.max(corner[0] + 4 * z, 2), by = corner[2] ? corner[1] : Math.max(corner[1] - 4 * z, 14);
    ctx.save(); ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
    ctx.fillStyle = '#000b'; ctx.fillRect(bx, by - 11, tw + 6, 14);
    ctx.fillStyle = '#fff'; ctx.fillText(text, bx + 3, by);
    ctx.restore();
  }
  ctx.lineWidth = 1;
}

// What the people of a placements table say, for hovering in Move people: the
// events of the story stage that goes with the table, fetched once per table.
// null until loaded, or when no stage pairs with it.
const PEOPLE_LINES = {};
function peopleLines(t) {
  const sc = scene(), key = `${S.map.number}:${sc.id}:${t.symbol}`;
  if (key in PEOPLE_LINES) return PEOPLE_LINES[key];
  PEOPLE_LINES[key] = null;
  (async () => {
    for (const guess of [t.symbol.replace('ActorPlacements', 'Triggers'), null]) {
      const r = await api(`/api/map/${S.map.number}/events?scene=${sc.id}` + (guess ? `&table=${encodeURIComponent(guess)}` : ''));
      if (!r.error && r.people_table === t.symbol) { PEOPLE_LINES[key] = r.events; return; }
    }
  })();
  return null;
}

// A line of game text for one status line: its markup dropped, at most 120 characters.
function shortText(text) {
  const plain = showNames(String(text).replace(/\{(?!protagonist_name|actor_name:)[^}]*\}/g, ' ')).replace(/\s+/g, ' ').trim();
  return plain.length > 120 ? plain.slice(0, 119) + '…' : plain;
}

function spriteImage(id) {
  if (!(id in S.spriteImg)) {
    const img = new Image(); img.onload = drawAllSoon; img.src = `/api/asset/sprite/${id}.png`;  // once a frame however many arrive
    S.spriteImg[id] = img;
  }
  return S.spriteImg[id];
}

// Scroll the map so the selected table's first point is in view.
function revealPoints() {
  const t = table(); if (!t || !['entrances', 'placements'].includes(t.kind)) return;
  const r = rowsOf(t).find(r => (t.kind === 'entrances' ? r.entrance : r.sprite) >= 0 && (r.x || r.z));
  if (!r) return;
  const z = +$('#zoom').value, [x, y] = pointPx(t, r), view = $('#view');
  const vx = x * z, vy = y * z;
  if (vx < view.scrollLeft || vx > view.scrollLeft + view.clientWidth || vy < view.scrollTop || vy > view.scrollTop + view.clientHeight)
    view.scrollTo({ left: vx - view.clientWidth / 2, top: vy - view.clientHeight / 2 });
}

function startPointDrag(e) {
  const t = table(); if (!t || !['entrances', 'placements'].includes(t.kind)) return status(`<span class="warn">${T('Pick an entrances or placements table in the Scene panel.')}</span>`);
  if (!t.editable) return status(`<span class="warn">${T('This table is read-only.')}</span>`);
  const z = +$('#zoom').value, rc = $('#cv').getBoundingClientRect();
  const mx = (e.clientX - rc.left) / z, my = (e.clientY - rc.top) / z;
  let best = null, bd = 10;
  rowsOf(t).forEach((r, i) => {
    if ((t.kind === 'entrances' ? r.entrance : r.sprite) < 0) return;
    const [x, y] = pointPx(t, r), d = Math.hypot(x - mx, y - my);
    if (d < bd) { bd = d; best = i; }
  });
  if (best != null) S.pointDrag = { t, i: best, x: e.clientX, y: e.clientY };
}

function endPointDrag(e) {
  const { t, i, x: startX, y: startY } = S.pointDrag; S.pointDrag = null;
  if (Math.hypot(e.clientX - startX, e.clientY - startY) < 3) return;  // a click, not a drag
  let [x, y] = groundPx(...mousePx(e));  // the ground under the drop point
  if (e.shiftKey) { x = Math.round(x / 8) * 8; y = Math.round(y / 8) * 8; }
  editTable(t, rows => {
    if (t.kind === 'entrances') { rows[i].x = x; rows[i].z = y; }
    else { rows[i].x = x * 65536; rows[i].z = y * 65536; }
  });
  const who = t.kind === 'entrances' ? T('Entrance {n}', { n: rowsOf(t)[i].entrance })
    : (S.advanced ? T('Actor {n}', { n: actorNumber(rowsOf(t), i) }) : T('Person'));
  status(T('{who} moved to {x},{y} px. Save, then press ▶ Play to try it.', { who, x, y }));
  if (t.kind === 'placements') checkMovedPerson(t, i, x, y);
  else staleStand();  // an arrival point moved
}

async function entrancesOf(sceneId) {
  const sc = S.allScenes.find(s => s.id === sceneId); if (!sc) return [];
  const k = sc.overlay.toString(16);
  // The request itself is kept, so a table with many exits to one scene asks once.
  if (!S.entranceCache[k]) S.entranceCache[k] = api(`/api/scene-overlay/${k}/entrances`);
  const list = await S.entranceCache[k];
  return Array.isArray(list) ? list : [];
}

const hexIn = v => v == null ? '' : '0x' + v.toString(16);
function sceneOptions(cur) {
  return S.allScenes.map(s => `<option value="${s.id}" ${s.id === cur ? 'selected' : ''}>${esc(S.names.sceneById[s.id]?.label || s.name || T('scene {n}', { n: s.id }))}${S.advanced ? ' [' + s.id + ']' : ''}</option>`).join('');
}

function renderTable() {
  const view = $('#tableView'), t = S.map && table();
  if (!t) { view.innerHTML = ''; return; }
  const rows = rowsOf(t), edited = S.tableEdits.has(t.symbol);
  let html = `<div class="note">${KIND_WORD[t.kind] || t.kind} · ${rows.length === 1 ? T('1 row') : T('{n} rows', { n: rows.length })}${t.overridden ? ` · <b>${T('overridden in mod')}</b>` : ''}${edited ? ' · ' + T('unsaved') : ''}
    ${t.overridden ? ` <button id="revertTable">${T('Revert to original')}</button>` : ''}</div>`;
  if (!t.editable) html += `<div class="note">${T('This can’t be edited yet: its bytes are not a plain table of this kind.')}</div>`;
  if (t.kind === 'exits') {
    rows.forEach((seg, si) => {
      if (seg.raw !== undefined || seg.scene === 0x1ff) return;
      const name = S.names.sceneById[seg.scene]?.label || T('scene {n}', { n: seg.scene });
      html += `<div class="note">${T('Exits from {place}', { place: `<b>${esc(name)}</b>` })}</div><table><tr><th title="${T('what triggers it')}">${T('kind')}</th><th>${T('leads to')}</th><th title="${T('arrival point')}">${T('arrive at')}</th><th class="adv">${T('flag')}</th><th></th></tr>`;
      seg.exits.forEach((ex, ei) => {
        html += `<tr data-s="${si}" data-e="${ei}"><td><input data-f="kind" value="${ex.kind}"></td>
          <td><select data-f="scene">${sceneOptions(ex.scene)}</select></td>
          <td><input data-f="entrance" value="${ex.entrance}"><span class="chk" data-scene="${ex.scene}" data-entr="${ex.entrance}"></span></td>
          <td class="adv"><input data-f="flag" value="${hexIn(ex.flag)}" placeholder="${T('none')}"></td>
          <td><button data-del="1" title="${T('remove exit')}">×</button></td></tr>`;
      });
      html += `</table><button data-add="${si}">${T('+ exit')}</button>`;
    });
    html += `<div class="note">${T('Kind is what a collision code, script or region asks for; kind 255 matches any.')}</div>`;
  } else if (t.kind === 'entrances' || t.kind === 'placements') {
    const pl = t.kind === 'placements';
    html += `<table><tr><th>${pl ? T('who') : T('arrival #')}</th><th class="adv">${pl ? T('actor') : T('flag')}</th><th>x</th><th>z</th><th class="adv">${T('facing')}</th></tr>`;
    rows.forEach((r, i) => {
      if ((pl ? r.sprite : r.entrance) < 0) return;
      const who = pl ? (S.names.spriteById[r.sprite]?.name || T('sprite {n}', { n: r.sprite })) : '';
      html += `<tr><td>${pl ? `<img src="/api/asset/sprite/${r.sprite}.png" style="height:20px;vertical-align:middle" data-hide-broken> ${esc(who)}` : r.entrance}</td>
        <td class="adv">${pl ? actorNumber(rows, i) : hexIn(r.requiredFlag < 0 ? null : r.requiredFlag) || '–'}</td>
        <td>${pl ? r.x >> 16 : r.x}</td><td>${pl ? r.z >> 16 : r.z}</td><td class="adv">${hexIn(r.facing)}</td></tr>`;
    });
    html += `</table><div class="note">${T('Drag them with Move people (P); hold ⇧ to snap to 8 px. Grey people are placed by the story, so they can’t be dragged.')}</div>`;
  } else {
    html += '<table>' + rows.slice(0, 200).map(r => '<tr>' + Object.values(r).map(v => `<td>${hexIn(v >>> 0)}</td>`).join('') + '</tr>').join('') + '</table>';
    html += `<div class="note">${T('Shown read-only for now.')}</div>`;
  }
  view.innerHTML = html;
  $('#revertTable')?.addEventListener('click', () => { S.tableEdits.set(t.symbol, { overlay: scene().overlay, kind: t.kind, rows: t.rows, revert: true }); updateButtons(); status(T('Revert queued; Save to apply.')); });
  if (t.kind !== 'exits' || !t.editable) return;
  view.querySelectorAll('tr[data-s]').forEach(tr => {
    const si = +tr.dataset.s, ei = +tr.dataset.e;
    tr.querySelectorAll('[data-f]').forEach(inp => inp.addEventListener('change', () => editTable(t, rows => {
      const ex = rows[si].exits[ei], f = inp.dataset.f, v = inp.value.trim();
      if (f === 'flag') ex.flag = v === '' ? null : parseInt(v, 16);
      else ex[f] = parseInt(v, 10) || 0;
    })));
    tr.querySelector('[data-del]').addEventListener('click', () => editTable(t, rows => rows[si].exits.splice(ei, 1)));
  });
  view.querySelectorAll('[data-add]').forEach(b => b.addEventListener('click', () => editTable(t, rows => {
    rows[+b.dataset.add].exits.push({ kind: 1, entrance: 0, scene: rows[+b.dataset.add].scene, flag: null, extra: 0 });
  })));
  // mark exits whose entrance doesn't exist in the target scene's overlay
  view.querySelectorAll('.chk').forEach(async el => {
    const list = await entrancesOf(+el.dataset.scene);
    if (list.length && !list.includes(+el.dataset.entr)) { el.className = 'chk bad'; el.textContent = ' ✗'; el.title = T('no such entrance in that scene'); }
  });
}

$('#sceneSel').onchange = () => { EV.stage = null; fillTables(); if (S.doorAt) doorSelect(S.doorAt.x, S.doorAt.z); if (S.tool === 'events') { EV.stage = null; loadEvents(); } };
$('#advanced').onchange = () => {
  S.advanced = $('#advanced').checked; save('advanced', S.advanced);
  setTimeout(() => { setTool(S.tool); }, 0);
  document.body.classList.toggle('advanced', S.advanced);
  renderList(); if (S.map) { loadScenes(true); drawAll(); }
};
$('#tableSel').onchange = () => { renderTable(); drawAll(); revealPoints(); };

// ---- stamp: copy an area (all layers, walkability, height) and paste it --------
function clearOverlay() { const ov = $('#ov'); ov.getContext('2d').clearRect(0, 0, ov.width, ov.height); }

function setStampMode(mode) {
  if (mode === 'paste' && !S.clip) mode = 'copy';
  S.stampMode = mode; S.sel = null; clearOverlay();
  $('#stampCopy').classList.toggle('on', mode === 'copy');
  $('#stampPaste').classList.toggle('on', mode === 'paste');
  $('#stampPaste').disabled = !S.clip;
  updateStampInfo();
}

function updateStampInfo() {
  const c = S.clip;
  $('#stampInfo').innerHTML = !c ? T('Drag on the map to copy an area.')
    : `${S.stampMode === 'paste' ? T('Click to paste') : T('Drag to copy a new area')} · ${T('clipboard {w}×{h} from {place}', { w: c.w, h: c.h, place: `<b>${esc(c.from)}</b>` })}` +
      (S.map && !stampFits(c) ? `<br><span class="err">${T('This map uses a different block set; the stamp can only be pasted into maps sharing its blocks.')}</span>` : '');
}

// A stamp fits a map of its block family. Blocks past the shared part are the
// source map's own additions, so those paste only back into that map.
function stampFits(c) {
  const m = S.map; if (!m || !c) return false;
  if (c.family !== m.family) return false;
  if (c.map === m.number) return true;
  return c.maxBlock < Math.min(c.familySize, m.family_size, m.metatile_count);
}
function retiredSet() { return new Set(S.map.retired || []); }

// Pixels of one 16x16 block of an atlas image, via an offscreen canvas.
function blockPixels(img, b) {
  const key = img.src;
  if (!S.pixelCache[key]) {
    const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
    const g = c.getContext('2d'); g.drawImage(img, 0, 0);
    S.pixelCache[key] = g.getImageData(0, 0, img.width, img.height);
  }
  const d = S.pixelCache[key], out = [], bx = (b % 32) * 16, by = Math.floor(b / 32) * 16;
  for (let y = 0; y < 16; y++) for (let x = 0; x < 16; x++) {
    const i = ((by + y) * d.width + bx + x) * 4;
    if (d.data[i + 3]) out.push([d.data[i], d.data[i + 1], d.data[i + 2]]);
  }
  return out;
}

// "Object" blocks on an upper layer: a good share of pixels unlike the
// layer's commonest block (its background), as tools/forest_scene.py does.
function objectTester(l) {
  const m = S.map, img = S.atlas[l.char_base], count = new Map();
  for (let y = 0; y < m.size[1]; y++) for (let x = 0; x < m.size[0]; x++) {
    const b = at(m.blocks, l, x, y) & 0xfff; count.set(b, (count.get(b) || 0) + 1);
  }
  const bg = [...count].sort((a, b) => b[1] - a[1])[0][0];
  const bp = img ? blockPixels(img, bg) : [];
  const mean = [0, 1, 2].map(i => bp.reduce((s, c) => s + c[i], 0) / Math.max(bp.length, 1));
  const cache = new Map();
  return b => {
    b &= 0xfff;
    if (b === bg || !img) return false;
    if (!cache.has(b)) {
      const px = blockPixels(img, b);
      const far = px.filter(c => (c[0] - mean[0]) ** 2 + (c[1] - mean[1]) ** 2 + (c[2] - mean[2]) ** 2 > 4900).length;
      cache.set(b, px.length > 0 && far / px.length > 0.3);
    }
    return cache.get(b);
  };
}

function stampDown(x, y) {
  const m = S.map;
  if (x < 0 || y < 0 || x >= m.size[0] || y >= m.size[1]) return;
  if (S.stampMode === 'copy') { S.sel = { x0: x, y0: y, x1: x, y1: y, dragging: true }; drawStampOverlay(); }
  else pasteStamp(x, y);
}

function stampMove(x, y) {
  const m = S.map;
  x = Math.max(0, Math.min(m.size[0] - 1, x)); y = Math.max(0, Math.min(m.size[1] - 1, y));
  if (S.sel && S.sel.dragging) { S.sel.x1 = x; S.sel.y1 = y; }
  S.hoverCell = [x, y];
  drawStampOverlay();
}

function stampUp() {
  const m = S.map, s = S.sel; s.dragging = false;
  const x0 = Math.min(s.x0, s.x1), y0 = Math.min(s.y0, s.y1), w = Math.abs(s.x1 - s.x0) + 1, h = Math.abs(s.y1 - s.y0) + 1;
  const layers = m.layers.map(l => l.priority ? l : null);
  const testers = layers.map((l, i) => l && i > 0 ? objectTester(l) : null);
  const clip = { w, h, from: (S.maps.find(o => o.number === m.number) || {}).label || T('map {n}', { n: m.number }), map: m.number,
    hash: m.metatiles_hash, family: m.family, familySize: m.family_size, layers: [], object: [], shapeRows: m.shapes.slice() };
  for (let li = 0; li < layers.length; li++) {
    const l = layers[li];
    clip.layers.push(l ? { block: [], collision: [], shape: [] } : null);
  }
  for (let j = 0; j < h; j++) {
    const objRow = [];
    for (let i = 0; i < w; i++) {
      let obj = false;
      layers.forEach((l, li) => {
        if (!l) return;
        const L = clip.layers[li];
        (L.block[j] = L.block[j] || []).push(at(m.blocks, l, x0 + i, y0 + j));
        (L.collision[j] = L.collision[j] || []).push(at(m.grids.collision, l, x0 + i, y0 + j));
        (L.shape[j] = L.shape[j] || []).push(at(m.grids.shape, l, x0 + i, y0 + j));
        if (testers[li] && testers[li](at(m.blocks, l, x0 + i, y0 + j))) obj = true;
      });
      objRow.push(obj);
    }
    clip.object.push(objRow);
  }
  clip.maxBlock = Math.max(...clip.layers.filter(Boolean).flatMap(L => L.block.flat().map(v => v & 0xfff)));
  S.clip = clip;
  try { localStorage.setItem('gsmap.clip', JSON.stringify(clip)); } catch (e) {}
  drawStampThumb(x0, y0, w, h);
  setStampMode('paste');
  status(T('Copied {w}×{h}. Click to paste (here or in another map with the same block set); Esc to copy again.', { w, h }));
}

function drawStampThumb(x0, y0, w, h) {
  const t = $('#stampThumb'), src = $('#cv'), z = +$('#zoom').value, s = 16 * z;
  const sc = Math.min(1, 270 / (w * 16));
  t.width = Math.round(w * 16 * sc); t.height = Math.round(h * 16 * sc);
  const g = t.getContext('2d'); g.imageSmoothingEnabled = false;
  g.drawImage(src, x0 * s, y0 * s, w * s, h * s, 0, 0, t.width, t.height);
}

function drawStampOverlay() {
  const ov = $('#ov'), g = ov.getContext('2d'), z = +$('#zoom').value, s = 16 * z;
  g.clearRect(0, 0, ov.width, ov.height);
  if (S.stampMode === 'copy' && S.sel) {
    const x0 = Math.min(S.sel.x0, S.sel.x1), y0 = Math.min(S.sel.y0, S.sel.y1);
    const w = Math.abs(S.sel.x1 - S.sel.x0) + 1, h = Math.abs(S.sel.y1 - S.sel.y0) + 1;
    g.fillStyle = 'rgba(224,184,74,0.18)'; g.fillRect(x0 * s, y0 * s, w * s, h * s);
    g.strokeStyle = '#e0b84a'; g.lineWidth = 2; g.strokeRect(x0 * s + 1, y0 * s + 1, w * s - 2, h * s - 2);
  } else if (S.stampMode === 'paste' && S.clip && S.hoverCell) {
    const [hx, hy] = S.hoverCell, c = S.clip, objOnly = $('#stampObjects').checked;
    const ok = stampFits(c);
    g.globalAlpha = 0.75;
    if (ok) c.layers.forEach((L, li) => {
      if (!L) return;
      const l = S.map.layers[li], img = S.atlas[l.char_base]; if (!img) return;
      for (let j = 0; j < c.h; j++) for (let i = 0; i < c.w; i++) {
        if (objOnly && !c.object[j][i]) continue;
        if (L.block[j][i] == null) continue;
        const b = L.block[j][i] & 0xfff;
        g.drawImage(img, (b % 32) * 16, Math.floor(b / 32) * 16, 16, 16, (hx + i) * s, (hy + j) * s, s, s);
      }
    });
    g.globalAlpha = 1;
    g.strokeStyle = ok ? '#7ee787' : '#ff7b72'; g.lineWidth = 2;
    g.strokeRect(hx * s + 1, hy * s + 1, c.w * s - 2, c.h * s - 2);
  }
}

function pasteStamp(x, y) {
  const m = S.map, c = S.clip;
  if (!stampFits(c)) return status(`<span class="err">${T('This map uses a different block set, so the stamp would draw the wrong tiles. Paste it into a place that shares its blocks.')}</span>`);
  const retired = retiredSet();
  const bad = c.layers.filter(Boolean).some(L => L.block.flat().some(v => v != null && retired.has(v & 0xfff)));
  if (bad) return status(`<span class="err">${T('This stamp uses blocks this map retired to make room for custom tiles, so they would draw the wrong art here.')}</span>`);
  const objOnly = $('#stampObjects').checked, walk = $('#stampWalk').checked;
  // A height is a row number in each place's own table, and unsaved rows are
  // renumbered by Save: unless the number still means the same row, find or make it.
  const heightHere = v => { const r = c.shapeRows?.[v]; return !r || sameShape(m.shapes[v], r) ? v : shapeIndex(r); };
  S.stroke = [];
  const cells = [];
  for (let j = 0; j < c.h; j++) for (let i = 0; i < c.w; i++) {
    const tx = x + i, ty = y + j;
    if (tx >= m.size[0] || ty >= m.size[1]) continue;
    if (objOnly && !c.object[j][i]) continue;
    c.layers.forEach((L, li) => {
      if (!L || !m.layers[li] || !m.layers[li].priority) return;
      if (L.block[j][i] == null) return;
      const [gx, gy] = gridXY(m.layers[li], tx, ty);
      setValue('block', gx, gy, L.block[j][i]);
      if (walk && L.collision) { setValue('collision', gx, gy, L.collision[j][i]); const h = heightHere(L.shape[j][i]); if (h != null) setValue('shape', gx, gy, h); }
    });
    cells.push([tx, ty]);
  }
  finishStroke();
  redrawCells(cells); drawStampOverlay();
  status(localWords(objOnly ? T('Pasted {w}×{h} (objects only). Save to keep it; ⌘Z to undo.', { w: c.w, h: c.h })
    : T('Pasted {w}×{h}. Save to keep it; ⌘Z to undo.', { w: c.w, h: c.h })));
}

// ---- chests: add, change what's inside, remove (one server action each) ----------
S.icons = {};
async function loadChests() {
  const n = S.map.number, r = await api(`/api/map/${n}/chests`);
  if (S.map.number !== n) return;
  S.chests = r.error ? [] : r;
  if (r.error) status(`<span class="err">${esc(r.error)}</span>`);
  for (const c of S.chests) if (c.chest && c.value >> 20 === 1) chestIcon(c.value & 0xffff);
  drawAll();
}
function chestIcon(id) {
  if (!S.icons[id]) { S.icons[id] = new Image(); S.icons[id].onload = drawAllSoon; S.icons[id].src = `/api/asset/item/${id}.png`; }
  return S.icons[id];
}
function itemByName(name) {
  const t = name.trim().toLowerCase();
  return t ? S.names.items.find(i => i.name && !i.unused && i.name.toLowerCase() === t) : null;
}
function chestDeselect() { S.chestAt = null; $('#chestForm').style.display = 'none'; }
function chestSelect(x, z, mk) {
  if (!$('#itemList').options.length)
    $('#itemList').innerHTML = S.names.items.filter(i => !i.unused && i.id && i.name).map(i => `<option value="${esc(i.name)}">`).join('');
  const c = mk && S.chests?.find(c => c.x === x && c.z === z);
  if (mk && !c?.chest) {
    chestDeselect(); drawAll();
    return status(T('This is {what}; it can be moved but not changed here.', { what: esc(S.legend[String(mk.id)]?.[0] || T('a Psynergy Stone or scripted find')) }));
  }
  S.chestAt = { x, z, chest: c || null };
  $('#chestForm').style.display = 'block';
  $('#chestOk').textContent = c ? T('Change contents') : T('Add chest');
  $('#chestRemove').style.display = c ? '' : 'none';
  const kind = c && c.value >> 20 === 2 ? 'coins' : 'item';
  document.querySelector(`input[name=chestKind][value=${kind}]`).checked = true;
  if (c && kind === 'coins') $('#chestCoins').value = c.value & 0xffff;
  if (c && kind === 'item') $('#chestItem').value = S.names.itemById[c.value & 0xffff]?.name || '';
  updateChestIcon();
  $('#chestInfo').innerHTML = c ? T('Chest holding {what}.', { what: `<b>${esc(c.contents)}</b>` }) + (S.advanced ? ' ' + T('Code {code}, opened flag {flag}.', { code: hex(c.code), flag: hex(c.flag) }) : '')
    : T('New chest here. Pick what it holds:');
  drawAll();
}
function updateChestIcon() {
  const it = itemByName($('#chestItem').value);
  $('#chestIcon').src = it ? chestIcon(it.id).src : '';
  $('#chestIcon').style.visibility = it ? 'visible' : 'hidden';
}
$('#chestItem').oninput = () => { document.querySelector('input[name=chestKind][value=item]').checked = true; updateChestIcon(); };
$('#chestCoins').oninput = () => { document.querySelector('input[name=chestKind][value=coins]').checked = true; };
$('#chestCancel').onclick = () => { chestDeselect(); drawAll(); };
async function chestAction(action) {
  const at = S.chestAt; if (!at) return;
  let contents = {};
  if (action !== 'remove') {
    if (document.querySelector('input[name=chestKind]:checked').value === 'coins') contents = { coins: +$('#chestCoins').value };
    else {
      const it = itemByName($('#chestItem').value);
      if (!it) return status(`<span class="err">${T('Pick an item from the list (start typing its name).')}</span>`);
      contents = { item: it.id };
    }
  }
  if (!await saveFirst()) return;
  const n = S.map.number;
  const r = await api(`/api/map/${n}/chest`, { action, x: at.x, z: at.z, contents });
  if (r.error) return status(`<span class="err">${esc(r.error)}</span>`);
  S.pending.clear(); S.markerMoves.clear(); S.tableEdits.clear();
  await openMap(n);
  chestDeselect();
  const what = `<b>${esc(r.contents)}</b>`;
  status(`<span class="ok">${action === 'add' ? T('Added a chest with {what}.', { what }) : action === 'remove' ? T('Removed the chest.') : T('The chest now holds {what}.', { what })}</span> ${T('Press ▶ Play to try it.')}`);
}
$('#chestOk').onclick = () => chestAction(S.chestAt?.chest ? 'contents' : 'add');
$('#chestRemove').onclick = () => confirm(T('Remove this chest?')) && chestAction('remove');

// ---- events: what people say, signs and step messages, in words -----------------------
const EV = { data: null, sel: null, stage: null, spot: null };
const KIND_ICON = { talk: '🗨', 'talk-stopped': '🗨', touch: '👣', search: '🔎', item: '🎒', psynergy: '✨', exit: '🚪', raised: '🎬' };
function gameToPlain(t) {
  return (t || '').replace(/\{end_wait\}/g, '').replace(/\{page_break\}/g, '\n\n').replace(/([^\n])\n(?!\n)/g, '$1 ').trim();
}
function showNames(t) {
  return (t || '').replace(/\{protagonist_name\}/g, S.names.characters[0] || T('the hero')).replace(/\{actor_name:(\d+)\}/g, (m, n) => S.names.characters[n - 1] || T('someone'))
    .replace(/\{end_wait\}|\{end_now\}|\{pause_\w+\}/g, '').replace(/\{[^}]*\}/g, '');
}
async function loadEvents() {
  const sc = scene(); if (!sc) { $('#evList').innerHTML = `<div class="note">${T('No scene uses this map.')}</div>`; return; }
  const q = `scene=${sc.id}` + (EV.stage ? `&table=${encodeURIComponent(EV.stage)}` : ''), map = S.map, ask = EV.ask = {};
  const r = await api(`/api/map/${map.number}/events?${q}`);
  if (EV.ask !== ask || S.map !== map) return;  // asked again, or another place opened, meanwhile
  if (r.error) { $('#evList').innerHTML = `<div class="err">${esc(r.error)}</div>`; return; }
  EV.data = r; EV.stage = r.symbol; staleStand();
  $('#evStage').innerHTML = r.tables.map(t => `<option value="${esc(t)}" ${t === r.symbol ? 'selected' : ''}>${esc(variantName(t))}</option>`).join('');
  $('#evShared').style.display = r.shared_with.length ? '' : 'none';
  $('#evShared').textContent = r.shared_with.length ? T('This scene shares its people and events with {places}: changes show there too.', { places: r.shared_with.slice(0, 3).join(', ') + (r.shared_with.length > 3 ? '…' : '') }) : '';
  if (!S.flags) {  // a failed answer is asked again next time, not kept
    const f = await api('/api/flags');
    if (!f.error) { S.flags = f; $('#flagList').innerHTML = f.flags.map(f => `<option value="${esc(f.label)}">`).join(''); }
  }
  renderEvents(); drawAll();
}
$('#evStage').onchange = () => { EV.stage = $('#evStage').value; EV.sel = null; loadEvents(); };
function evTitle(e) {
  const icon = KIND_ICON[e.kind] || '•';
  if (e.kind === 'talk' || e.kind === 'talk-stopped') return `${icon} ${e.who}`;
  if (e.kind === 'psynergy') return `${icon} ${e.who ? T('{what} on {who}', { what: e.what, who: e.who }) : e.what}`;
  if (e.kind === 'item') return `${icon} ${e.who ? T('Using {what} on {who}', { what: e.what, who: e.who }) : T('Using {what} here', { what: e.what })}`;
  if (e.kind === 'search') return `${icon} ${T('Searching {what}', { what: e.what })}`;
  if (e.kind === 'touch') return `${icon} ${T('Stepping here')}`;
  if (e.kind === 'exit') return `${icon} ${T('Door')}`;
  return `${icon} ${T('Story event')}`;
}
const EV_GROUP_LABEL = { People: T('People'), Spots: T('Spots'), 'Doors and story': T('Doors and story') };
function renderEvents() {
  const r = EV.data; if (!r) return;
  const filt = EV.filter;
  const groups = { People: [], Spots: [], 'Doors and story': [] };
  for (const e of r.events) {
    if (filt && !(filt.actor != null ? e.actor === filt.actor : e.cells.some(c => c[0] === filt.x && c[1] === filt.z))) continue;
    (e.actor != null ? groups.People : ['touch', 'search', 'item'].includes(e.kind) ? groups.Spots : groups['Doors and story']).push(e);
  }
  let html = filt ? `<div class="row"><span class="note">${esc(filt.label)}</span><button id="evAll">${T('Show all')}</button></div>` : '';
  for (const [g, list] of Object.entries(groups)) {
    if (!list.length) continue;
    html += `<h3>${EV_GROUP_LABEL[g]}</h3>`;
    for (const e of list) {
      const words = e.text != null ? '“' + showNames(gameToPlain(e.text)) + '”' : (S.advanced && e.detail ? e.detail : e.does) + (e.script && S.advanced ? ` [${e.script}]` : '');
      html += `<div class="ev ${EV.sel === e.index ? 'on' : ''}" data-i="${e.index}"><div class="h"><b>${esc(evTitle(e))}</b>${e.condition !== -1 ? `<span class="w">${esc(e.when)}</span>` : ''}</div>
        <div class="t">${esc(words.slice(0, 220))}</div>
        <div class="act">${e.editable_text ? `<button data-a="edit">${T('Change words')}</button>` : ''}<button data-a="when">${T('When…')}</button>
          ${e.kind !== 'exit' ? `<button data-a="remove">${T('Remove')}</button>` : `<button data-a="doors">${T('Open in Doors')}</button>`}</div></div>`;
    }
  }
  const waiting = r.people.filter(offMap).length;
  if (!filt && waiting) html += `<div class="note" style="padding:6px 0">${waiting === 1 ? T('1 person waits off the map until the story brings them in. Move people can place them.') : T('{n} people wait off the map until the story brings them in. Move people can place them.', { n: waiting })}</div>`;
  if (!filt && r.regions.length) {
    html += `<h3>${T('Exit areas')}</h3>` + r.regions.map((g, i) => `<div class="ev" data-region="${i}"><div class="h"><b>▭ ${T('Area')}</b></div><div class="t">${g.label ? T('Leads to {place}, arrival point {n}', { place: esc(g.label), n: g.entrance }) : T('Leads nowhere')}</div>
      <div class="act"><button data-r="link">${T('Change where it leads…')}</button><button data-r="remove">${T('Remove')}</button></div></div>`).join('');
  }
  $('#evList').innerHTML = html || `<div class="note">${T('Nothing happens here yet.')}</div>`;
  $('#evAll')?.addEventListener('click', () => { EV.filter = null; $('#evSpot').style.display = 'none'; renderEvents(); drawAll(); });
}
$('#evList').onclick = async e => {
  const reg = e.target.closest('[data-region]');
  if (reg) {
    const g = EV.data.regions[+reg.dataset.region], a = e.target.dataset.r;
    for (const el of document.querySelectorAll('#evList .ev')) el.classList.toggle('on', el === reg);
    EV.region = g; drawAll();
    if (a === 'remove' && confirm(T('Remove this exit area?'))) evAction({ action: 'region', region_table: g.table, index: g.index, remove: true }, T('Removed the exit area.'));
    if (a === 'link') { S.regionPick = g; openPicker({ scene: null }); }
    return;
  }
  const card = e.target.closest('.ev'); if (!card) return;
  const ev = EV.data.events.find(x => x.index === +card.dataset.i);
  EV.sel = ev.index; EV.region = null;
  const a = e.target.dataset.a;
  if (a === 'edit') return openEventEditor({ mode: 'text', ev });
  if (a === 'when') return openEventEditor({ mode: 'when', ev });
  if (a === 'remove') { if (confirm(T('Remove this event?'))) evAction({ action: 'remove', index: ev.index }, T('Removed.')); return; }
  if (a === 'doors') { setTool('doors'); if (ev.cells[0]) doorSelect(ev.cells[0][0], ev.cells[0][1]); return; }
  renderEvents(); drawAll(); evReveal(ev);
};
function evReveal(ev) {
  const z0 = +$('#zoom').value * 16, m = S.map;
  let w = null;
  if (ev.at) w = entityXY(ev.at[0], ev.at[1]).map(v => v / 16);
  else if (ev.cells[0]) w = groundXY(S.map.layers[0], ev.cells[0][0], ev.cells[0][1]);
  if (w) $('#view').scrollTo(w[0] * z0 - $('#view').clientWidth / 2, w[1] * z0 - $('#view').clientHeight / 2);
}
function drawEvents(ctx) {
  if (S.tool !== 'events' || !EV.data || !S.map) return;
  const z = +$('#zoom').value, s = 16 * z, l0 = S.map.layers[0], m = S.map;
  ctx.save(); ctx.font = `${4 * z + 3}px sans-serif`; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  const sel = EV.data.events.find(e => e.index === EV.sel);
  // spots
  for (const e of EV.data.events) {
    if (!['touch', 'search', 'item'].includes(e.kind)) continue;
    for (const [gx, gz] of e.cells) {
      const w = groundXY(l0, gx, gz); if (!w) continue;
      ctx.fillStyle = e === sel ? 'rgba(224,184,74,.45)' : 'rgba(126,231,135,.28)'; ctx.fillRect(w[0] * s, w[1] * s, s, s);
      ctx.strokeStyle = e === sel ? '#e0b84a' : '#7ee787'; ctx.lineWidth = 2; ctx.strokeRect(w[0] * s + 1, w[1] * s + 1, s - 2, s - 2);
    }
  }
  // people
  for (const p of EV.data.people) {
    if (offMap(p)) continue;  // the panel counts them instead of stacking them in the corner
    const [ex, ey] = entityXY(p.x, p.z), x = ex * z, y = ey * z;
    const on = sel && sel.actor === p.actor, talks = EV.data.events.some(e => e.actor === p.actor && e.kind === 'talk');
    const img = spriteImage(p.sprite);
    if (img && img.complete && img.naturalWidth) {
      const w = img.naturalWidth * z, h = img.naturalHeight * z;
      ctx.drawImage(img, x - w / 2, y - h + 4 * z, w, h);  // feet at the point, as Move people draws them
    }
    ctx.beginPath(); ctx.arc(x, y, 7 * z, 0, Math.PI * 2);
    ctx.lineWidth = 2; ctx.strokeStyle = on ? '#e0b84a' : talks ? '#58a6ff' : '#8b93a3'; ctx.stroke();
    if (z >= 2) { const t = p.name || T('person'); const tw = ctx.measureText(t).width; ctx.fillStyle = '#000b'; ctx.fillRect(x - tw / 2 - 3, y + 8 * z, tw + 6, 4 * z + 6); ctx.fillStyle = '#fff'; ctx.fillText(t, x, y + 8 * z + 2); }
  }
  // exit areas
  for (const g of EV.data.regions) {
    const x0 = (g.minX - m.bounds[0] * 8) * z, y0 = (g.minZ - g.minY - m.bounds[1] * 8) * z;  // raised by its height
    ctx.strokeStyle = g === EV.region ? '#e0b84a' : '#c297ff'; ctx.lineWidth = 2; ctx.setLineDash([5, 3]);
    ctx.strokeRect(x0, y0, (g.maxX - g.minX) * z, (g.maxZ - g.minZ) * z); ctx.setLineDash([]);
  }
  if (EV.spot && !EV.newPerson) { const w = groundXY(l0, EV.spot.x, EV.spot.z); if (w) { ctx.setLineDash([4, 3]); ctx.strokeStyle = '#e0b84a'; ctx.strokeRect(w[0] * s + 1, w[1] * s + 1, s - 2, s - 2); ctx.setLineDash([]); } }
  if (EV.newPerson) {  // the person about to be added
    const [ex, ey] = entityXY(EV.newPerson.x, EV.newPerson.z);
    ctx.setLineDash([4, 3]); ctx.lineWidth = 2; ctx.strokeStyle = EV.newPerson.ok ? '#7ee787' : '#e0b84a';
    ctx.beginPath(); ctx.arc(ex * z, ey * z, 7 * z, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
  }
  ctx.restore();
}
// The person at window pixel (sx, sy) in Events: under the cursor's picture of
// them (drawn feet at their point, as drawEvents does), or within 10 pixels of
// their feet; the nearest when several overlap. null when nobody's there.
// A person the scene keeps at 0,0 waits off the map until a script brings them in.
const offMap = p => p.x === 0 && p.z === 0;
function personAt(sx, sy) {
  let best = null;
  for (const p of EV.data.people) {
    if (offMap(p)) continue;
    const [ex, ey] = entityXY(p.x, p.z), img = spriteImage(p.sprite);
    const d = Math.hypot(ex - sx, ey - sy);
    const w = img?.naturalWidth || 0, h = img?.naturalHeight || 0;
    const onPicture = w && sx >= ex - w / 2 && sx <= ex + w / 2 && sy >= ey - h + 4 && sy <= ey + 4;
    if ((onPicture || d < 10) && (!best || d < best[0])) best = [d, p];
  }
  return best && best[1];
}
function evClick(e, x, y) {
  if (!EV.data) return;
  const [sx, sy] = mousePx(e), [px, pz] = groundPx(sx, sy);
  const p = personAt(sx, sy);
  $('#evSpot').style.display = 'flex';
  if (p) {
    const talks = EV.data.events.some(ev => ev.actor === p.actor && ev.kind === 'talk');
    EV.filter = { actor: p.actor, label: `${p.name || T('This person')}` }; EV.spot = null; EV.newPerson = null;
    $('#evSpot').innerHTML = `<button id="evTalk" class="primary">${talks ? T('Add a line for a story moment…') : T('Make them say something…')}</button>`
      + (p.added ? `<button id="evRemovePerson">${T('Remove this person')}</button>` : '');
    $('#evTalk').onclick = () => openEventEditor({ mode: 'talk', actor: p.actor, who: p.name, conditional: talks });
    if (p.added) $('#evRemovePerson').onclick = () => {
      if (!confirm(T('Remove {who} and everything they say?', { who: p.name || T('this person') }))) return;
      EV.filter = null; $('#evSpot').style.display = 'none';
      evAction({ action: 'remove-person', actor: p.actor }, T('Removed.'));
    };
  } else {
    const [gx, gz] = groundAt(S.map.layers[0], sx, sy) || gridXY(S.map.layers[0], x, y);
    EV.filter = { x: gx, z: gz, label: T('Spot {x},{z}', { x: gx, z: gz }) }; EV.spot = { x: gx, z: gz }; EV.newPerson = null;
    $('#evSpot').innerHTML = `<button id="evSign">${T('Add a sign (read with A)…')}</button><button id="evStep">${T('Add a step message…')}</button><button id="evPerson">${T('Add a person here…')}</button>`;
    $('#evSign').onclick = () => openEventEditor({ mode: 'spot', how: 'search', x: gx, z: gz });
    $('#evStep').onclick = () => openEventEditor({ mode: 'spot', how: 'touch', x: gx, z: gz });
    $('#evPerson').onclick = () => startAddPerson(Math.round(px), Math.round(pz));
  }
  renderEvents(); drawAll();
}
// ---- where people can stand (gsmap/walk.py: the game's walking rules) ---------------
// The server follows the party from every arrival point and says, per square,
// what a person standing there would mean. Unsaved painting is sent along, so
// the answer matches what you see.
const WK = { cells: null, size: null, key: null, timer: null };
const STAND = {
  good: ['rgba(80,200,120,0.38)', T('The party can walk up and talk')],
  talk: ['rgba(230,200,60,0.40)', T('Can be talked to from nearby (behind a counter, on a ledge)')],
  slide: ['rgba(70,140,255,0.50)', T('Ice the party slides across: keep people off it')],
  trigger: ['rgba(255,140,40,0.55)', T('A door, exit or step spot: keep it clear')],
  cut: ['rgba(230,70,70,0.40)', T("The party can't get near by walking")],
};
function walkEdits() {
  return [...S.pending].filter(([k]) => /^(shape|collision):/.test(k))
    .map(([k, value]) => { const [plane, x, y] = k.split(':'); return { plane, x: +x, y: +y, value }; });
}
function staleStand() {
  if (!$('#ovStand')?.checked) return;
  clearTimeout(WK.timer); WK.timer = setTimeout(loadStand, 300);
}
async function loadStand() {
  const sc = scene();
  $('#standLegend').style.display = $('#ovStand').checked ? '' : 'none';
  if (!S.map || !sc || !$('#ovStand').checked) { WK.cells = null; return; }
  const edits = walkEdits(), shapes = pendingShapes(), key = `${S.map.number}:${sc.id}:${EV.stage}:${JSON.stringify(edits)}:${JSON.stringify(shapes)}`;
  if (key === WK.key && WK.cells) return;
  WK.key = key;
  const r = await api(`/api/map/${S.map.number}/walk`, { scene: sc.id, table: EV.stage, edits, shapes });
  if (WK.key !== key) return;
  if (r.error) { WK.cells = null; status(`<span class="err">${esc(r.error)}</span>`); drawAll(); return; }
  WK.cells = r.cells; WK.size = r.size;
  $('#standLegend').innerHTML = Object.entries(STAND).filter(([k]) => k !== 'slide' || r.slide)
    .map(([, [c, t]]) => `<div style="display:flex;gap:6px;align-items:center"><span style="width:12px;height:12px;flex:none;background:${c};border:1px solid #0004"></span>${esc(t)}</div>`).join('')
    + (r.arrivals ? `<div style="margin-top:4px">${r.arrivals > 1
      ? T("Worked out from the game's walking rules, starting at this place's {n} arrival points. Places opened by Psynergy or the story can show as red.", { n: r.arrivals })
      : T("Worked out from the game's walking rules, starting at this place's 1 arrival point. Places opened by Psynergy or the story can show as red.")}</div>`
                  : `<div style="margin-top:4px">${T("This place has no arrival points, so the editor can't tell where the party walks.")}</div>`);
  drawAll();
}
function drawStand(ctx) {
  if (!$('#ovStand').checked || !WK.cells || !S.map) return;
  const z = +$('#zoom').value, s = 16 * z, l0 = S.map.layers[0], w = WK.size[0], cells = [];
  WK.cells.forEach((c, k) => {
    if (!STAND[c]) return;
    const [gx, gy] = gridXY(l0, k % w, Math.floor(k / w)), p = groundXY(l0, gx, gy);
    if (p) cells.push([heightPx(l0, gx, gy), p, STAND[c][0]]);
  });
  cells.sort((a, b) => a[0] - b[0]);
  for (const [, p, c] of cells) { ctx.fillStyle = c; ctx.fillRect(p[0] * s, p[1] * s, s, s); }
}
function checkSpot(x, z, actor) {
  return api(`/api/map/${S.map.number}/walk/check`, { scene: scene().id, table: EV.stage, x, z, actor, edits: walkEdits(), shapes: pendingShapes() });
}
function problemList(r) {
  return `<ul style="margin:4px 0 6px 18px;padding:0">${r.problems.map(p => `<li>${esc(p.text)}</li>`).join('')}</ul>`;
}
// Level the squares the server picked to the path's height: unsaved painting,
// so Undo takes it back and Save keeps it.
function applyLevel(level) {
  S.stroke = [];
  for (const e of level.cells) setValue(e.plane, e.x, e.y, e.value);
  finishStroke(); drawAll();
  WK.key = null; loadStand();
}
const LEVEL_NOTE = T("The picture doesn't change: use Paint if it should look like a path.");
function levelLabel(level) {
  return level.count > 1 ? T("Level {n} squares to the path's height (level {h})", { n: level.count, h: levelOf(level.height) })
    : T("Level 1 square to the path's height (level {h})", { h: levelOf(level.height) });
}
function levelledText(level) { return level.count > 1 ? T('Levelled {n} squares.', { n: level.count }) : T('Levelled 1 square.'); }

// Adding a person: check the spot first, and offer a way round what's wrong.
async function startAddPerson(x, z) {
  EV.newPerson = { x, z };
  if (!$('#ovStand').checked) { $('#ovStand').checked = true; save('ovStand', true); }
  WK.key = null; loadStand();
  await showPersonCheck();
}
async function showPersonCheck(note) {
  const p = EV.newPerson; if (!p) return;
  const box = $('#evSpot'); box.style.display = 'flex'; box.style.flexDirection = 'column'; box.style.alignItems = 'stretch';
  box.innerHTML = `<div class="note">${T('Checking this spot…')}</div>`; drawAll();
  const r = await checkSpot(p.x, p.z);
  if (EV.newPerson !== p) return;
  const lead = note ? `<div class="ok">${esc(note)}</div>` : '';
  if (r.error) {
    box.innerHTML = `${lead}<div class="warn">${esc(r.error)}</div><button id="evPersonGo">${T('Add a person here…')}</button>`;
  } else if (!r.problems.length) {
    p.ok = true;
    const fine = r.notes?.length ? T('Fine: {notes}', { notes: r.notes.map(n => n.text).join(' ') }) : T('Good spot: the party can walk up and talk to them.');
    box.innerHTML = `${lead}<div class="ok">${esc(fine)}</div><button id="evPersonGo" class="primary">${T('Add a person here…')}</button>`;
  } else {
    p.ok = false;
    box.innerHTML = `${lead}<div class="warn">${T('This spot has a problem:')}</div>${problemList(r)}`
      + (r.nearest ? `<button id="evPersonNear" class="primary">${T('Move to the nearest good spot')}</button>` : '')
      + (r.level ? `<button id="evPersonLevel" title="${esc(LEVEL_NOTE)}">${esc(levelLabel(r.level))}</button>` : '')
      + `<button id="evPersonGo">${T('Add here anyway…')}</button><button id="evPersonCancel">${T('Cancel')}</button>`;
  }
  drawAll();
  $('#evPersonGo').onclick = () => openEventEditor({ mode: 'person', x: p.x, z: p.z });
  if ($('#evPersonCancel')) $('#evPersonCancel').onclick = () => { EV.newPerson = null; box.style.display = 'none'; drawAll(); };
  if ($('#evPersonNear')) $('#evPersonNear').onclick = () => {
    const from = { ...p }; EV.newPerson = { x: r.nearest.x, z: r.nearest.z };
    const cells = Math.round(Math.hypot(r.nearest.x - from.x, r.nearest.z - from.z) / 16);
    showPersonCheck(!cells ? T('Moved less than one square.') : cells === 1 ? T('Moved 1 square.') : T('Moved {n} squares.', { n: cells }));
  };
  if ($('#evPersonLevel')) $('#evPersonLevel').onclick = () => {
    applyLevel(r.level);
    showPersonCheck(`${levelledText(r.level)} ${LEVEL_NOTE} ${T('Save to keep it; Undo takes it back.')}`);
  };
}

// Moving a person with the Points tool: the same check, after the drop.
async function checkMovedPerson(t, i, x, z) {
  const map = S.map, actor = actorNumber(rowsOf(t), i), r = await checkSpot(x, z, actor);
  if (S.map !== map || table() !== t) return;  // its buttons would change a table no longer shown
  if (r.error || !r.problems.length) return;
  status(`<span class="warn">${T('Moved, but:')}</span> ${r.problems.map(p => esc(p.text)).join(' ')} `
    + (r.nearest ? `<button id="stNear">${T('Move to the nearest good spot')}</button> ` : '')
    + (r.level ? `<button id="stLevel" title="${esc(LEVEL_NOTE)}">${esc(levelLabel(r.level))}</button>` : ''));
  if ($('#stNear')) $('#stNear').onclick = () => {
    editTable(t, rows => { rows[i].x = r.nearest.x * 65536; rows[i].z = r.nearest.z * 65536; });
    status(`<span class="ok">${T('Moved to a good spot.')}</span> ${T('Save, then press ▶ Play to try it.')}`);
  };
  if ($('#stLevel')) $('#stLevel').onclick = () => {
    applyLevel(r.level); status(`<span class="ok">${levelledText(r.level)}</span> ${LEVEL_NOTE} ${T('Save to keep it; Undo takes it back.')}`);
  };
}

// the edit dialog
let EE = null;
function openEventEditor(o) {
  EE = o;
  const ev = o.ev;
  $('#eeTitle').textContent = { text: T('Change the words'), when: T('When does it happen?'), talk: o.who ? T('What should {who} say?', { who: o.who }) : T('What should they say?'),
    spot: o.how === 'search' ? T('A sign or something to examine') : T('A message when you step here'), person: T('Add a person') }[o.mode];
  $('#eeSub').textContent = ev ? evTitle(ev) : o.mode === 'spot' ? (o.how === 'search' ? T('At spot {x},{z}. Pressing A facing it shows the text.', { x: o.x, z: o.z })
    : T('At spot {x},{z}. Stepping on it shows the text.', { x: o.x, z: o.z })) : '';
  $('#eeTextBox').style.display = o.mode === 'when' ? 'none' : '';
  $('#eePerson').style.display = o.mode === 'person' ? '' : 'none';
  $('#eeTarget').style.display = o.mode === 'spot' && o.how === 'search' ? '' : 'none';
  if (o.mode === 'spot' && !$('#eeTargetSel').options.length) $('#eeTargetSel').innerHTML = S.flags.search_targets.map((t, i) => `<option value="${i}">${esc(t)}</option>`).join('');
  if (o.mode === 'person' && !$('#eeSprite').options.length) {
    $('#eeSprite').innerHTML = S.names.sprites.filter(sp => sp.has_image && sp.name && sp.id > 7).map(sp => `<option value="${sp.id}">${esc(sp.name)}</option>`).join('');
    $('#eeSprite').onchange = () => { $('#eeSpriteImg').src = `/api/asset/sprite/${$('#eeSprite').value}.png`; };
  }
  if (o.mode === 'person') $('#eeSprite').onchange();
  $('#eeRaw').checked = false;
  $('#eeText').value = ev && ev.text != null ? gameToPlain(ev.text) : '';
  const c = ev ? ev.condition : (o.conditional ? null : -1);
  $('#eeWhen').value = c === -1 ? 'always' : (c === null || c & 0x1000 ? 'set' : 'clear');
  $('#eeFlag').value = c === -1 || c === null ? '' : (S.flags.flags.find(f => f.flag === (c & 0xfff))?.label || '0x' + (c & 0xfff).toString(16));
  $('#eeWhen').onchange(); $('#eeMsg').textContent = ''; preview();
  $('#evEdit').style.display = 'flex'; $('#eeText').focus();
}
$('#eeWhen').onchange = () => { $('#eeFlag').style.display = $('#eeWhen').value === 'always' ? 'none' : ''; };
$('#eeCancel').onclick = () => { $('#evEdit').style.display = 'none'; };
$('#eeName').onclick = () => { const t = $('#eeText'); t.setRangeText('{protagonist_name}', t.selectionStart, t.selectionEnd, 'end'); t.focus(); preview(); };
$('#eeRaw').onchange = () => {
  const ev = EE?.ev;
  $('#eeText').value = $('#eeRaw').checked ? (ev?.text ?? compose($('#eeText').value)) : gameToPlain($('#eeText').value);
  preview();
};
$('#eeText').oninput = preview;
function compose(text) {  // as gsmap/messages.py compose: 22 wide, 3 lines a box
  const len = s => s.replace(/\{[^}]*\}/g, 'xxxxx').length, boxes = [];
  for (const para of text.trim().split(/\n\s*\n/)) {
    const lines = [];
    for (const forced of para.split('\n')) {
      let cur = '';
      for (const w of forced.split(/\s+/).filter(Boolean)) {
        if (cur && len(cur) + 1 + len(w) > 22) { lines.push(cur); cur = w; } else cur = cur ? cur + ' ' + w : w;
      }
      if (cur) lines.push(cur);
    }
    for (let i = 0; i < lines.length; i += 3) boxes.push(lines.slice(i, i + 3).join('\n'));
  }
  return boxes.join('{page_break}') + '{end_wait}';
}
function preview() {
  const raw = $('#eeRaw').checked, t = raw ? $('#eeText').value : compose($('#eeText').value);
  const boxes = t.replace(/\{end_wait\}/g, '').split('{page_break}').filter(b => b.trim());
  $('#evPreview').innerHTML = boxes.map(b => { const shown = showNames(b), long = shown.split('\n').some(l => l.length > 26) || shown.split('\n').length > 3;
    return `<div class="gbabox${long ? ' long' : ''}" title="${long ? T('This box may not fit') : ''}">${esc(shown)}</div>`; }).join('');
}
function whenValue() {
  const w = $('#eeWhen').value; if (w === 'always') return { always: true };
  const label = $('#eeFlag').value.trim(), f = S.flags.flags.find(x => x.label === label);
  const flag = f ? f.flag : /^0x[0-9a-f]{1,3}$/i.test(label) ? parseInt(label, 16) : NaN;
  if (Number.isNaN(flag)) throw new Error(T('Pick a story flag from the list (start typing).'));
  return { flag, set: w === 'set' };
}
$('#eeSave').onclick = async () => {
  let when; try { when = whenValue(); } catch (err) { $('#eeMsg').innerHTML = `<span class="err">${esc(err.message)}</span>`; return; }
  const text = $('#eeText').value, raw = $('#eeRaw').checked, o = EE;
  if (o.mode !== 'when' && o.mode !== 'person' && !text.trim()) { $('#eeMsg').innerHTML = `<span class="err">${T('Write what it says.')}</span>`; return; }
  const body = { text: { action: 'text', index: o.ev?.index, text, raw, when }, when: { action: 'when', index: o.ev?.index, when },
    talk: { action: 'talk', actor: o.actor, text, when }, spot: { action: 'spot', x: o.x, z: o.z, how: o.how, text, target: +$('#eeTargetSel').value || 0, when },
    person: { action: 'person', sprite: +$('#eeSprite').value, x: o.x, z: o.z, text: text.trim() || null, wander: $('#eeWander').checked, when } }[o.mode];
  const ok = await evAction(body, T('Saved.'));
  if (ok) $('#evEdit').style.display = 'none';
};
async function evAction(body, done) {
  if (!await saveFirst()) return false;
  const sc = scene(), n = S.map.number;
  const r = await api(`/api/map/${n}/event`, { scene: sc.id, table: EV.stage, ...body });
  if (r.error) { $('#eeMsg').innerHTML = `<span class="err">${esc(r.error)}</span>`; status(`<span class="err">${esc(r.error)}</span>`); return false; }
  const keepStage = EV.stage, keepScene = sc.id;
  S.pending.clear(); S.markerMoves.clear(); S.tableEdits.clear();
  await openMap(n);
  if ([...$('#sceneSel').options].some(o => +o.value === keepScene)) { $('#sceneSel').value = String(keepScene); fillTables(); }
  EV.stage = keepStage;
  // A new person stands apart from the spot clicked: show everyone, so their line can be seen.
  if (body.action === 'person') { EV.filter = null; EV.newPerson = null; $('#evSpot').style.display = 'none'; }
  await loadEvents();
  status(`<span class="ok">${done}</span> ${T('Press ▶ Play to try it.')}`);
  return true;
}

// ---- doors: where each leads; link anywhere, make, remove (one server action each)
async function loadDoors() {
  const n = S.map.number, r = await api(`/api/map/${n}/doors`);
  if (S.map.number !== n) return;
  S.doors = r.error ? {} : r;
  if (r.error) status(`<span class="err">${esc(r.error)}</span>`);
  if (S.doorAt) doorSelect(S.doorAt.x, S.doorAt.z); else drawAll();
}
function sceneDoors() { const sc = scene(); return (sc && S.doors?.[sc.id]) || []; }
function doorAtCell(gx, gz) { return sceneDoors().find(d => d.cells.some(c => c[0] === gx && c[1] === gz)); }
function shortLabel(label) { return (label || '').split(' · ').pop(); }
// The square Check's Show points at, for a few seconds whatever the tool.
function drawCellMark(ctx) {
  const c = S.cellMark; if (!c || !S.map || Date.now() >= c.until) return;
  const s = 16 * +$('#zoom').value, w = c.block ? [c.x, c.z] : groundXY(S.map.layers[0], c.x, c.z);
  if (!w) return;
  ctx.save();
  ctx.lineWidth = 3; ctx.setLineDash([]); ctx.strokeStyle = '#e0b84a';
  ctx.strokeRect(w[0] * s - 2, w[1] * s - 2, s + 4, s + 4);
  ctx.beginPath(); ctx.arc((w[0] + 0.5) * s, (w[1] + 0.5) * s, s * 1.2, 0, Math.PI * 2); ctx.stroke();
  ctx.restore();
}
function drawDoors(ctx) {
  if (S.tool !== 'doors' || !S.map) return;
  const z = +$('#zoom').value, s = 16 * z, l0 = S.map.layers[0];
  ctx.save();
  for (const d of sceneDoors()) for (const [gx, gz] of d.cells) {
    const w = groundXY(l0, gx, gz); if (!w) continue;
    const bad = d.scene == null;
    ctx.fillStyle = bad ? 'rgba(255,123,114,.35)' : 'rgba(88,166,255,.3)'; ctx.fillRect(w[0] * s, w[1] * s, s, s);
    ctx.strokeStyle = bad ? '#ff7b72' : '#58a6ff'; ctx.lineWidth = 2; ctx.strokeRect(w[0] * s + 1, w[1] * s + 1, s - 2, s - 2);
  }
  if (z >= 2) {
    ctx.font = `${4 * z + 3}px sans-serif`; ctx.textAlign = 'left'; ctx.textBaseline = 'bottom';
    for (const d of sceneDoors()) {
      const w = d.cells.map(c => groundXY(l0, c[0], c[1])).find(Boolean); if (!w) continue;
      const text = d.scene == null ? T('leads nowhere') : '→ ' + shortLabel(d.label) + (d.fallback ? ' ' + T('(default)') : ''), tw = ctx.measureText(text).width;
      ctx.fillStyle = '#000b'; ctx.fillRect(w[0] * s, w[1] * s - 4 * z - 6, tw + 6, 4 * z + 6);
      ctx.fillStyle = d.scene == null ? '#ff7b72' : '#fff'; ctx.fillText(text, w[0] * s + 3, w[1] * s - 1);
    }
  }
  if (S.arrivalMark && Date.now() < S.arrivalMark.until) {  // where Go there arrived
    const [ex, ey] = entityXY(S.arrivalMark.x, S.arrivalMark.z);
    ctx.lineWidth = 3; ctx.strokeStyle = '#e0b84a';
    for (const r of [7, 12]) { ctx.beginPath(); ctx.arc(ex * z, ey * z, r * z, 0, Math.PI * 2); ctx.stroke(); }
  }
  if (S.doorAt) {
    const w = groundXY(l0, S.doorAt.x, S.doorAt.z);
    if (w) { ctx.lineWidth = 2; ctx.setLineDash([4, 3]); ctx.strokeStyle = '#e0b84a'; ctx.strokeRect(w[0] * s + 1, w[1] * s + 1, s - 2, s - 2); }
  }
  ctx.restore();
}
function doorDeselect() { S.doorAt = null; $('#doorForm').style.display = 'none'; }
function doorSelect(gx, gz) {
  const d = doorAtCell(gx, gz), adv = d && S.advanced ? ` <span style="color:var(--muted)">${T('(code {code}, exit kind {kind})', { code: hex(d.code), kind: d.kind })}</span>` : '';
  S.doorAt = { x: gx, z: gz, door: d || null };
  const place = d && `<b>${esc(d.label)}</b>`;
  $('#doorInfo').innerHTML = !d ? T('Not a door. Make one here, leading anywhere in the game.')
    : d.scene == null ? `<span style="color:var(--bad)">${T('This scene has no exits at all, so this door does nothing.')}</span> ${T('Link it to a place, or remove it.')}${adv}`
    : d.fallback ? `${T("Has no exit of its own, so the game sends it to {place}, arrival point 0 (the scene's first exit). Give it a destination of its own if you like.", { place })}${adv}`
    : `${T('Leads to {place}, arrival point {n}.', { place, n: d.entrance })}${d.shared_kind ? ` <i>${T("(the scene's catch-all exit)")}</i>` : ''}${d.scripted ? `<br><span style="color:var(--muted)">${T('Opened by a scene script; its destination can change, the script stays.')}</span>` : ''}${adv}`;
  $('#doorLink').textContent = d ? T('Change where it leads…') : T('Make a door here…');
  $('#doorRemove').style.display = d && !d.scripted ? '' : 'none';
  $('#doorGo').style.display = d && d.scene != null ? '' : 'none';
  $('#doorForm').style.display = 'block';
  drawAll();
}
async function doorAction(action, extra) {
  const at = S.doorAt, sc = scene(); if (!at || !sc) return;
  if (!await saveFirst()) return false;
  const n = S.map.number;
  const r = await api(`/api/map/${n}/door`, { action, scene: sc.id, code: at.door?.code, x: at.x, z: at.z, ...extra });
  if (r.error) return status(`<span class="err">${esc(r.error)}</span>`);
  S.pending.clear(); S.markerMoves.clear(); S.tableEdits.clear();
  await openMap(n);
  const place = `<b>${esc(r.label)}</b>`;
  const done = action === 'remove' ? (r.cells === 1 ? T('Removed the door (1 cell).') : T('Removed the door ({n} cells).', { n: r.cells }))
    : action === 'add' ? T('New door now leads to {place}.', { place }) : T('The door now leads to {place}.', { place });
  status(`<span class="ok">${done}</span> ${T('Press ▶ Play to try it.')}`);
}
$('#doorRemove').onclick = () => confirm(T('Remove this door? Its cells become ground again.')) && doorAction('remove', {});

// Following a door: open where it leads, at its arrival point, and offer the way back.
async function followDoor(sceneId, entrance, back) {
  if (sceneId === WORLD_SCENE) { if (await saveFirst()) location.href = '/world.html'; return; }
  const r = await api(`/api/scene/${sceneId}/arrivals`);
  if (r.error || r.map == null) return status(`<span class="err">${T("That place has no map to open.")}</span>`);
  if (!S.map || S.map.number !== r.map) await openMap(r.map);
  if (!S.map || S.map.number !== r.map) return;  // the place didn't open (unsaved changes kept, or an error)
  doorDeselect();  // the door followed belongs to where you came from
  pickScene(sceneId);
  setTool('doors');
  const a = r.arrivals.find(x => x.entrance === entrance) || r.arrivals[0];
  S.arrivalMark = a ? { x: a.x, z: a.z, until: Date.now() + 4000 } : null;
  if (a) setTimeout(drawAllSoon, 4100);
  S.doorBack = back;
  $('#doorBack').style.display = back ? '' : 'none';
  if (back) $('#doorBack').textContent = T('← Back to {place}', { place: back.label });
  if (a) {
    const [ex, ey] = entityXY(a.x, a.z), z0 = +$('#zoom').value;
    $('#view').scrollTo(ex * z0 - $('#view').clientWidth / 2, ey * z0 - $('#view').clientHeight / 2);
  }
  drawAll();
  status(T('Arrived at {place}, arrival point {n}.', { place: `<b>${esc(r.label)}</b>`, n: a ? a.entrance : 0 }));
}
// Show scene `id` of this place, as picking it from the menu does.
function pickScene(id) {
  const sel = $('#sceneSel');
  if (sel.value === String(id) || ![...sel.options].some(o => +o.value === id)) return;
  sel.value = String(id); sel.dispatchEvent(new Event('change'));
}
$('#doorGo').onclick = () => {
  const d = S.doorAt?.door, sc = scene(); if (!d || d.scene == null || !sc) return;
  const label = S.names.sceneById[sc.id]?.label || S.maps.find(m => m.number === S.map.number)?.label || T('Place {n}', { n: S.map.number });
  followDoor(d.scene, d.entrance ?? 0, { map: S.map.number, scene: sc.id, x: S.doorAt.x, z: S.doorAt.z, label });
};
$('#doorBack').onclick = async () => {
  const b = S.doorBack; if (!b) return;
  if (S.map?.number !== b.map) await openMap(b.map);
  if (S.map?.number !== b.map) return;
  pickScene(b.scene);
  setTool('doors'); S.doorBack = null; $('#doorBack').style.display = 'none';
  doorSelect(b.x, b.z);
  const w = groundXY(S.map.layers[0], b.x, b.z), z0 = +$('#zoom').value * 16;
  if (w) $('#view').scrollTo(w[0] * z0 - $('#view').clientWidth / 2, w[1] * z0 - $('#view').clientHeight / 2);
};
$('#doorLink').onclick = () => openPicker(S.doorAt?.door);

// The destination picker: a place, then an arrival point on its map.
const PK = {};
function openPicker(door) {
  PK.scene = door?.scene ?? null; PK.entrance = door?.entrance ?? null;
  $('#pkTitle').textContent = S.regionPick ? T('Where should this exit area lead?') : door ? T('Where should this door lead?') : T('Where should the new door lead?');
  $('#pkFilter').value = ''; pkList(); $('#picker').style.display = 'flex'; $('#pkFilter').focus();
  if (PK.scene != null) pkScene(PK.scene, PK.entrance); else pkClear();
}
function pkClear() { $('#pkImg').removeAttribute('src'); $('#pkDots').innerHTML = $('#pkArrivals').innerHTML = ''; $('#pkHint').style.display = ''; pkUpdate(); }
function pkList() {
  const q = $('#pkFilter').value.trim().toLowerCase();
  $('#pkList').innerHTML = S.allScenes.filter(sc => sc.map != null)
    .map(sc => ({ id: sc.id, label: S.names.sceneById[sc.id]?.label || sc.name || T('scene {n}', { n: sc.id }) }))
    .filter(sc => !q || sc.label.toLowerCase().includes(q) || String(sc.id) === q)
    .map(sc => `<div data-id="${sc.id}" class="${sc.id === PK.scene ? 'on' : ''}">${esc(sc.label)}${S.advanced ? ` <span style="color:var(--muted)">[${sc.id}]</span>` : ''}</div>`).join('');
}
$('#pkFilter').oninput = pkList;
$('#pkList').onclick = e => { const id = e.target.closest('[data-id]')?.dataset.id; if (id != null) pkScene(+id, null); };
async function pkScene(id, entrance) {
  PK.scene = id; PK.entrance = entrance; pkList(); $('#pkMapWrap').scrollTo(0, 0);
  const r = await api(`/api/scene/${id}/arrivals`);
  if (PK.scene !== id) return;
  if (r.error) {
    $('#pkImg').removeAttribute('src'); $('#pkDots').innerHTML = '';
    $('#pkArrivals').innerHTML = `<div class="err" style="padding:12px">${esc(r.error)}</div>`; pkUpdate(); return;
  }
  PK.info = r; $('#pkHint').style.display = 'none';
  const dots = $('#pkDots'); dots.innerHTML = '';
  $('#pkArrivals').innerHTML = r.arrivals.length ? '' : `<div class="note" style="padding:12px">${T('This place lists no arrival points; the party arrives at its default spot (0).')}</div>`;
  if (!r.arrivals.length) PK.entrance = 0;
  if (r.map) {
    $('#pkImg').src = `/api/map/${r.map}/render.png`;
    const [bx, bz] = [r.bounds[0] * 8, r.bounds[1] * 8];
    for (const a of r.arrivals) {
      const b = document.createElement('button');
      b.textContent = a.entrance; b.dataset.e = a.entrance; b.title = T('Arrival point {n}', { n: a.entrance });
      b.style.left = (a.x - bx) + 'px'; b.style.top = ((a.sz ?? a.z) - bz) + 'px';
      b.onclick = () => { PK.entrance = a.entrance; pkUpdate(); };
      dots.appendChild(b);
    }
    $('#pkImg').onload = () => { const first = dots.querySelector(PK.entrance != null ? `[data-e="${PK.entrance}"]` : 'button');
      if (first) first.scrollIntoView({ block: 'center', inline: 'center' }); };
  } else { $('#pkImg').removeAttribute('src'); }
  pkUpdate();
}
function pkUpdate() {
  for (const b of $('#pkDots').children) b.classList.toggle('on', +b.dataset.e === PK.entrance);
  const label = PK.scene != null ? (S.names.sceneById[PK.scene]?.label || T('scene {n}', { n: PK.scene })) : null;
  $('#pkSel').innerHTML = label ? (PK.entrance != null ? T('{place}, arrival point {n}', { place: `<b>${esc(label)}</b>`, n: PK.entrance })
    : `<b>${esc(label)}</b> · ${T('click an arrival point on the map')}`) : '';
  $('#pkOk').disabled = PK.scene == null || PK.entrance == null;
}
$('#pkCancel').onclick = () => { $('#picker').style.display = 'none'; S.regionPick = null; };
$('#pkOk').onclick = () => {
  $('#picker').style.display = 'none';
  if (S.regionPick) {
    const g = S.regionPick; S.regionPick = null;
    return evAction({ action: 'region', region_table: g.table, index: g.index, target: { scene: PK.scene, entrance: PK.entrance } }, T('The exit area now leads there.'));
  }
  doorAction(S.doorAt?.door ? 'relink' : 'add', { target_scene: PK.scene, target_entrance: PK.entrance });
};

// ---- import an image into this map's own tile set ------------------------------
let importData = null;
// Names some places that can take a picture, so the refusal says where to go.
async function explainNoImport() {
  const r = await api('/api/maps/own-tileset'), own = Array.isArray(r) ? r : [];  // api() answers {error}, never throws
  const names = [...new Set(S.maps.filter(m => own.includes(m.number)).map(m => m.label || m.folder))];
  const some = names.length ? ' ' + T('You can import into {n} places, such as {places}.', { n: own.length, places: names.slice(0, 3).map(esc).join(', ') }) : '';
  status(`<span class="warn">${T('This place shares its art with other places, so a picture here would change them too.')}${some}</span>`);
}
$('#importBtn').onclick = () => {
  if (!S.map) return status(`<span class="warn">${T('Pick a place first.')}</span>`);
  if (!S.map.own_tileset) return explainNoImport();
  $('#importFile').value = ''; $('#importFile').click();
};
$('#importFile').onchange = async () => {
  const f = $('#importFile').files[0]; if (!f) return;
  importData = await new Promise(r => { const fr = new FileReader(); fr.onload = () => r(fr.result); fr.readAsDataURL(f); });
  await importPreview();
};
$('#importLayer').onchange = () => { if (importData) importPreview(); };
async function importPreview() {
  status(T('Fitting the image to this map’s colours…'));
  const r = await api(`/api/map/${S.map.number}/import-image`, { png: importData, layer: +$('#importLayer').value });
  if (r.error) { $('#importBox').style.display = 'none'; return status(`<span class="err">${esc(r.error)}</span>`); }
  $('#importBox').style.display = 'block';
  $('#importPreview').src = r.preview; $('#importPreview').style.width = (r.cells[0] * 16 * 3) + 'px';
  $('#importInfo').innerHTML = T('{w}×{h} blocks · {added} new tiles, {reused} reused', { w: r.cells[0], h: r.cells[1], added: r.new_tiles, reused: r.reused_tiles }) +
    ' · ' + (r.palette_row != null ? T('colours from palette row {n}', { n: r.palette_row }) : T('colours per tile')) +
    (r.retired_blocks ? `<br><span class="warn">${T('Makes room by retiring {n} unused block(s).', { n: r.retired_blocks })}</span>` : '') +
    `<br>${T('Room left afterwards: about {n} tiles. This is how it will look in game.', { n: r.free_tiles_left })}`;
  status(T('Preview ready. “Add to tile set” saves the tiles and blocks, then puts them on the Stamp clipboard.'));
}
$('#importCancel').onclick = () => { importData = null; $('#importBox').style.display = 'none'; };
$('#importApply').onclick = async () => {
  if (!await saveFirst()) return;
  const layer = +$('#importLayer').value, n = S.map.number;
  const r = await api(`/api/map/${n}/import-image`, { png: importData, layer, apply: true });
  if (r.error) return status(`<span class="err">${esc(r.error)}</span>`);
  importData = null; $('#importBox').style.display = 'none';
  S.pending.clear(); S.markerMoves.clear(); S.tableEdits.clear();
  await openMap(n);
  // the new blocks become the stamp: one layer, no walkability, empty cells skipped
  const m = S.map, h = r.blocks.length, w = r.blocks[0].length;
  const layers = m.layers.map((l, li) => li === layer ? { block: r.blocks, collision: null, shape: null } : null);
  S.clip = { w, h, from: T('imported image'), map: n, hash: m.metatiles_hash, family: m.family, familySize: m.family_size,
    layers, object: r.blocks.map(row => row.map(v => v != null)),
    maxBlock: Math.max(...r.blocks.flat().filter(v => v != null)) };
  try { localStorage.setItem('gsmap.clip', JSON.stringify(S.clip)); } catch (e) {}
  const t = $('#stampThumb'); t.width = w * 16; t.height = h * 16;
  const g = t.getContext('2d'); g.clearRect(0, 0, t.width, t.height); g.imageSmoothingEnabled = false;
  const img = S.atlas[m.layers[layer].char_base];
  r.blocks.forEach((row, y) => row.forEach((b, x) => { if (b != null) g.drawImage(img, (b % 32) * 16, Math.floor(b / 32) * 16, 16, 16, x * 16, y * 16, 16, 16); }));
  setTool('stamp'); setStampMode('paste');
  status(T('Added {tiles} tiles and {blocks} block(s). Click the map to place your image, then Save.', { tiles: r.new_tiles, blocks: w * h }));
};

$('#stampCopy').onclick = () => setStampMode('copy');
$('#stampPaste').onclick = () => setStampMode('paste');
$('#stampObjects').onchange = drawStampOverlay;
$('#cv').addEventListener('mouseleave', () => { S.hoverCell = null; if (S.tool === 'stamp' && !(S.sel && S.sel.dragging)) drawStampOverlay(); });
try { S.clip = JSON.parse(localStorage.getItem('gsmap.clip')); } catch (e) { S.clip = null; }

// ---- save / build / play -------------------------------------------------------
// One save at a time: ⌘S pressed again, or an action that saves first, waits for
// the save already running. Meanwhile clicks on the map and Undo/Redo are ignored
// (S.saving): what is sent must be what the bookkeeping clears after it.
async function doSave() {
  if (!S.saving) S.saving = saveNow().finally(() => { S.saving = null; });
  return S.saving;
}
async function saveNow() {
  const edits = [...S.pending].map(([k, value]) => {
    const [plane, gx, gy] = k.split(':'); return { plane, x: +gx, y: +gy, value };
  });
  $('#save').disabled = true;
  const markers = [...S.markerMoves].map(([index, st]) => ({ index, x: st.x, z: st.z, restore: st.restore }));
  // collision cells the server rewrites for marker moves are not sent as edits
  const auto = new Set([...S.markerMoves].flatMap(([i, st]) => {
    const mk = S.map.markers.find(m => m.index === i); return [`${mk.orig[0]}:${mk.orig[1]}`, `${st.x}:${st.z}`];
  }));
  const sent = edits.filter(e => !(e.plane === 'collision' && auto.has(`${e.x}:${e.y}`)));
  for (const [sym, te] of S.tableEdits) {
    const tr = await api(te.revert ? '/api/scene-table/revert' : '/api/scene-table',
      { overlay: te.overlay, symbol: sym, rows: te.rows, map: S.map.number });
    if (tr.error) { S.saveError = tr.error; status(`<span class="err">${T('Table {name} not saved: {error}', { name: esc(sym), error: esc(tr.error) })}</span>`); updateButtons(); return; }
  }
  const savedTables = S.tableEdits.size; S.tableEdits.clear();
  if (savedTables) {  // saved: Undo now takes these back from the saved history
    const notTables = list => list.map(s => s.filter(c => c.plane !== 'table')).filter(s => s.length);
    S.undo = notTables(S.undo); S.redo = notTables(S.redo);
    await loadScenes(true);
  }
  if (!sent.length && !markers.length) {
    S.undo = []; S.redo = [];  // all saved: Undo now steps through the saved history
    updateButtons(); drawAll();
    status(`<span class="ok">${T('Saved.')}</span> ${T('Press ▶ Play to try it.')}`); refreshUndoSave(); return;
  }
  const newShapes = pendingShapes();
  const r = await api(`/api/map/${S.map.number}/edits`, newShapes.length ? { edits: sent, markers, shapes: newShapes, shapes_base: S.map.shapesSaved } : { edits: sent, markers });
  if (r.error) { S.saveError = r.error; status(`<span class="err">${T('Not saved: {error}', { error: esc(r.error) })}</span>`); updateButtons(); return; }
  if (r.shapes) settleShapes(r.shapes, r.remap || {});
  const movedChests = S.markerMoves.size;
  S.pending.clear(); S.markerMoves.clear();
  for (const mk of S.map.markers) delete mk.orig;
  // All saved: Undo now steps through the saved history, this save first.
  S.undo = []; S.redo = [];
  if (movedChests) await loadChests();
  updateButtons(); drawAll();
  if (S.advanced) log(T('Saved {files}', { files: r.saved.join(', ') }));
  refreshUndoSave();
  status(`<span class="ok">${T('Saved.')}</span> ${T('Press ▶ Play to try it.')}`);
}

// After a save that added heights: the table as the file now holds it, and
// squares painted with an unsaved height renumbered to its saved row. The
// height brush finds its row again by content (buildHeightPanel).
function settleShapes(rows, remap) {
  const m = S.map, saved = m.shapesSaved ?? m.shapes.length, old = m.shapes;
  const to = v => remap[v] ?? rows.findIndex(r => sameShape(r, old[v]));
  for (const line of m.grids.shape) for (let x = 0; x < line.length; x++) {
    if (line[x] < saved) continue;
    const v = to(line[x]); if (v >= 0) line[x] = v;
  }
  m.shapes = rows; m.shapesSaved = rows.length;
  if (S.tool === 'shape') buildHeightPanel();
}

// ---- connections: one place in the middle, what leads in and where it leads -----
const CN = { scene: null }, WORLD_SCENE = 2;
function cnPlaces() {
  return S.allScenes.filter(sc => sc.map != null).map(sc => {
    const n = S.names.sceneById[sc.id] || {};
    return { id: sc.id, label: n.label || sc.name || T('scene {n}', { n: sc.id }), area: n.area || n.label || T('Other') };
  });
}
function cnList() {
  const q = $('#cnFilter').value.trim().toLowerCase(), groups = new Map();
  for (const p of cnPlaces()) {
    if (q && !p.label.toLowerCase().includes(q)) continue;
    if (!groups.has(p.area)) groups.set(p.area, []); groups.get(p.area).push(p);
  }
  $('#cnList').innerHTML = [...groups].map(([a, ps]) => `<h4>${esc(a)}</h4>` + ps.map(p =>
    `<div data-id="${p.id}" class="${p.id === CN.scene ? 'on' : ''}">${esc(p.label.split(' · ').pop())}</div>`).join('')).join('');
}
$('#cnFilter').oninput = cnList;
$('#cnList').onclick = e => { const id = e.target.closest('[data-id]')?.dataset.id; if (id != null) cnShow(+id); };
async function openConnections() {
  if (!S.allScenes) S.allScenes = await api('/api/scenes');
  $('#conn').style.display = 'flex';
  const sc = S.map && scene();
  await cnShow(CN.scene ?? sc?.id ?? 4);
}
async function cnShow(id) {
  CN.scene = id; cnList();
  const sel = $('#cnList .on'); if (sel) sel.scrollIntoView({ block: 'nearest' });
  $('#cnView').innerHTML = `<div class="note">${T('Loading…')}</div>`;
  const r = await api(`/api/connections/${id}`);
  if (CN.scene !== id) return;
  if (r.error) { $('#cnView').innerHTML = `<div class="err">${esc(r.error)}</div>`; return; }
  CN.data = r;
  const card = (l, dir, i) => `<div class="lk" data-dir="${dir}" data-i="${i}" title="${T('Show its connections')}">
      ${dir === 'in' ? '' : '<span class="ar">→</span>'}<div class="t">${esc(l.label)}<div class="s">${dir === 'in'
        ? T('arrives at point {n}', { n: l.entrance }) : `${esc(l.how)} · ${T('arrives at point {n}', { n: l.entrance })}`}${S.advanced ? ' · ' + T('kind {n}', { n: l.kind }) : ''}</div></div>
      ${dir === 'in' ? '<span class="ar">→</span>' : ''}<button data-open="${dir}:${i}" title="${T('Open in the editor')}">${T('Open')}</button></div>`;
  $('#cnView').innerHTML = `
    <div class="col"><h3>${T('Reached from ({n})', { n: r.in.length })}</h3>${r.in.map((l, i) => card(l, 'in', i)).join('') || `<div class="note">${T('Nothing leads here.')}</div>`}</div>
    <div class="center"><h2 style="margin:0">${esc(r.label)}</h2>${r.area && r.area !== r.label ? `<div class="note">${esc(r.area)}</div>` : ''}
      ${r.map ? `<img src="/api/map/${r.map}/render.png" alt="">` : ''}
      <button data-open="me" class="primary">${T('Open this place in the editor')}</button></div>
    <div class="col"><h3>${T('Leads to ({n})', { n: r.out.length })}</h3>${r.out.map((l, i) => card(l, 'out', i)).join('') || `<div class="note">${T('No exits.')}</div>`}</div>`;
}
$('#cnView').onclick = async e => {
  const open = e.target.closest('[data-open]')?.dataset.open;
  if (open) {
    const r = CN.data; let mapN = r.map, sid = r.scene, cell = null, tool = 'doors';
    if (open !== 'me') {
      const [dir, i] = open.split(':'), l = r[dir][+i];
      // an exit opens here with its door selected; an entry opens the place it comes from
      if (dir === 'out') cell = l.cell; else { mapN = l.map; sid = l.scene; }
    }
    if (sid === WORLD_SCENE) { if (await saveFirst()) location.href = '/world.html'; return; }
    $('#conn').style.display = 'none';
    if (!S.map || S.map.number !== mapN) await openMap(mapN);
    if ([...$('#sceneSel').options].some(o => +o.value === sid)) { $('#sceneSel').value = String(sid); fillTables(); }
    setTool(tool);
    if (cell) {
      doorSelect(cell[0], cell[1]);
      const w = groundXY(S.map.layers[0], cell[0], cell[1]), z0 = +$('#zoom').value * 16;
      if (w) $('#view').scrollTo(w[0] * z0 - $('#view').clientWidth / 2, w[1] * z0 - $('#view').clientHeight / 2);
    }
    return;
  }
  const lk = e.target.closest('.lk'); if (!lk) return;
  cnShow(CN.data[lk.dataset.dir][+lk.dataset.i].scene);
};
$('#connBtn').onclick = openConnections;
$('#atlasBtn').onclick = async () => { if (await saveFirst()) location.href = '/atlas.html'; };

// The place's random battles (gsmap/encounters.py, gScene_EncounterRules), in a dialog.
const BT = { ask: null };
async function openBattles() {
  const sc = scene(); if (!S.map || !sc) return status(`<span class="warn">${T('Open a place first.')}</span>`);
  const label = S.names.sceneById[sc.id]?.label || T('scene {n}', { n: sc.id });
  $('#btTitle').textContent = T('Battles in {place}', { place: label });
  $('#battles').style.display = 'flex'; $('#btPane').innerHTML = `<div class="note">${T('Loading…')}</div>`;
  const ask = BT.ask = {};
  const r = await api(`/api/scene/${sc.id}/battles`);
  if (BT.ask !== ask) return;  // opened again, for this or another place, meanwhile
  if (r.error) return $('#btPane').innerHTML = `<div class="err">${esc(r.error)}</div>`;
  if (!r.battles.length) return $('#btPane').innerHTML = `<div class="note" style="padding:12px 0">${T('No random battles in {place}.', { place: esc(label) })}</div>`;
  battleBoxes($('#btPane'), r.battles, r.formations, S.advanced, async (zone, rate, groups) => {
    const s = await api('/api/battles', { zone, rate, groups, map: S.map.number });  // api() refreshes Undo
    if (s.error) return status(`<span class="err">${esc(s.error)}</span>`);
    if ($('#battles').style.display !== 'none') await openBattles();
    status(s.changed ? `<span class="ok">${T("Saved this place's battles.")}</span> ${T('Press ▶ Play to try it.')}` : T('Nothing changed.'));
  });
}
$('#battlesBtn').onclick = openBattles;
$('#btClose').onclick = () => { $('#battles').style.display = 'none'; };
$('#cnClose').onclick = () => { $('#conn').style.display = 'none'; };

// ---- export: the mod as a patch file ----------------------------------------------------
let exResult = null;
$('#exportBtn').onclick = () => {
  $('#exp').style.display = 'flex'; $('#exName').value ||= load('modName', ''); $('#exAuthor').value ||= load('modAuthor', '');
  $('#exName').focus();
};
$('#exClose').onclick = () => { $('#exp').style.display = 'none'; };
$('#exReveal').onclick = () => exResult && api('/api/reveal', { path: exResult.patch });
$('#exGo').onclick = async () => {
  const name = $('#exName').value.trim();
  if (!name) return $('#exMsg').innerHTML = `<span class="err">${T('Give your mod a name.')}</span>`;
  if (!await saveFirst()) return;
  save('modName', name); save('modAuthor', $('#exAuthor').value.trim());
  const found = await runChecks(), mine = (found || []).filter(i => !i.original);
  if (!found && !confirm(T("Check couldn't finish, so your changes haven't been checked. Export anyway?"))) { $('#exp').style.display = 'none'; openChecks(false); return; }
  if (mine.length && !confirm(T('Check found {n} problem(s) in your changes. Export anyway?', { n: mine.length }))) { $('#exp').style.display = 'none'; openChecks(false); return; }
  const ask = { name, author: $('#exAuthor').value.trim(), description: $('#exDesc').value.trim(), ips: $('#exIps').checked };
  let r = await api('/api/export', ask);
  if (r.exists) {
    // OK replaces the earlier patch; Cancel keeps it and saves this one under the next free number.
    const replace = confirm(T('You already exported a patch called {file}. Replace it? OK replaces it; Cancel keeps it and saves this one as {instead}.', { file: r.exists, instead: r.instead }));
    r = await api('/api/export', { ...ask, keep: !replace });
  }
  if (r.error) return $('#exMsg').innerHTML = `<span class="err">${esc(r.error)}</span>`;
  $('#exGo').disabled = true; $('#exReveal').style.display = 'none'; exResult = null;
  $('#exLog').style.display = 'block'; $('#exLog').textContent = '';
  let since = 0;
  for (;;) {
    const s = await api(`/api/export/status?since=${since}`);
    // No answer at all (api()'s own {error}): the app went away, so stop asking.
    if (s.done === undefined) { $('#exGo').disabled = false; $('#exMsg').innerHTML = `<span class="err">${esc(s.error)}</span>`; break; }
    if (s.log?.length) { $('#exLog').textContent += s.log.join('\n') + '\n'; $('#exLog').scrollTop = $('#exLog').scrollHeight; }
    since = s.next ?? since;
    $('#exMsg').textContent = s.done ? '' : T('Working… the first export also builds the unmodified game once, which takes a few minutes.');
    if (s.done) {
      $('#exGo').disabled = false;
      if (s.ok) {
        exResult = s.result; $('#exReveal').style.display = '';
        const file = `<b>${esc(s.result.patch.split('/').pop())}</b>`, size = (s.result.size / 1024).toFixed(1);
        $('#exMsg').innerHTML = `<span class="ok">${s.result.ips_size
          ? T('Saved {file} ({size} KB) and an .ips ({ips} MB) with a readme for players.', { file, size, ips: (s.result.ips_size / 1048576).toFixed(1) })
          : T('Saved {file} ({size} KB) with a readme for players.', { file, size })}</span>`;
      } else $('#exMsg').innerHTML = `<span class="err">${esc(s.error)}</span>`;
      break;
    }
    await new Promise(r => setTimeout(r, 800));
  }
};

// The patcher: someone's mod onto the unmodified game (built here) or the player's own ROM.
const PT = {};
const readFile = f => new Promise(r => { const fr = new FileReader(); fr.onload = () => r(fr.result); fr.readAsDataURL(f); });
$('#patcherBtn').onclick = () => { $('#ptc').style.display = 'flex'; };
$('#ptClose').onclick = () => { $('#ptc').style.display = 'none'; };
$('#ptPick').onclick = () => { $('#ptFile').value = ''; $('#ptFile').click(); };
$('#ptFile').onchange = async () => {
  const f = $('#ptFile').files[0]; if (!f) return;
  PT.patch = await readFile(f); PT.name = f.name; $('#ptName').textContent = f.name; $('#ptGo').disabled = false;
};
$('#ptRomPick').onclick = e => { e.preventDefault(); $('#ptRom').value = ''; $('#ptRom').click(); };
$('#ptRom').onchange = async () => {
  const f = $('#ptRom').files[0]; if (!f) return;
  PT.rom = await readFile(f); $('#ptRomName').textContent = f.name;
  document.querySelector('input[name=ptBase][value=file]').checked = true;
};
$('#ptPlay').onclick = async () => { const r = await api('/api/play-file', { path: PT.result.game }); if (r.error) $('#ptMsg').innerHTML = `<span class="err">${esc(r.error)}</span>`; };
$('#ptReveal').onclick = () => api('/api/reveal', { path: PT.result.game });
$('#ptGo').onclick = async () => {
  const own = document.querySelector('input[name=ptBase]:checked').value === 'file';
  if (own && !PT.rom) return $('#ptMsg').innerHTML = `<span class="err">${T('Choose your ROM file, or use the unmodified game built here.')}</span>`;
  const r = await api('/api/patcher', { patch: PT.patch, name: PT.name, rom: own ? PT.rom : null });
  if (r.error) return $('#ptMsg').innerHTML = `<span class="err">${esc(r.error)}</span>`;
  $('#ptGo').disabled = true; $('#ptPlay').style.display = $('#ptReveal').style.display = 'none';
  $('#ptLog').style.display = 'block'; $('#ptLog').textContent = '';
  let since = 0;
  for (;;) {
    const s = await api(`/api/export/status?since=${since}`);
    if (s.done === undefined) { $('#ptGo').disabled = false; $('#ptMsg').innerHTML = `<span class="err">${esc(s.error)}</span>`; break; }  // as in Export
    if (s.log?.length) { $('#ptLog').textContent += s.log.join('\n') + '\n'; $('#ptLog').scrollTop = $('#ptLog').scrollHeight; }
    since = s.next ?? since;
    $('#ptMsg').textContent = s.done ? '' : (own ? T('Patching…') : T('Patching… the first time also builds the unmodified game, a few minutes.'));
    if (s.done) {
      $('#ptGo').disabled = false;
      if (s.ok) {
        PT.result = s.result;
        // The patch's own notes (name: …, author: …), with the editor's words for the ones it writes.
        const aboutLabel = { name: T('Name'), author: T('Author'), description: T('Description'), for: T('For') };
        const about = (s.result.about || '').split('\n').filter(Boolean).map(l => esc(l).replace(/^(\w+): /, (m, k) => `<b>${({}).hasOwnProperty.call(aboutLabel, k) ? aboutLabel[k] : k[0].toUpperCase() + k.slice(1)}:</b> `)).join('<br>');
        const pv = { base: esc(s.result.base), format: esc(s.result.format.toUpperCase()), file: esc(s.result.game.split('/').pop()) };
        $('#ptMsg').innerHTML = `<span class="ok">${s.result.format === 'ips' ? T('Patched {base} with an {format} patch: saved {file}.', pv) : T('Patched {base} with a {format} patch: saved {file}.', pv)}</span>` +
          (about ? `<div class="note" style="margin-top:6px">${about}</div>` : '') +
          s.result.notes.map(n => `<div class="warn" style="margin-top:6px">${esc(n)}</div>`).join('');
        $('#ptPlay').style.display = $('#ptReveal').style.display = '';
      } else $('#ptMsg').innerHTML = `<span class="err">${esc(s.error)}</span>`;
      break;
    }
    await new Promise(res => setTimeout(res, 700));
  }
};

// ---- checks: what your changes would break, in plain words ------------------------
let checkResult = null, checkFailed = null;
async function runChecks() {
  $('#check').disabled = true; status(T('Checking every map…'));
  const answer = await api('/api/check');
  $('#check').disabled = false;
  checkFailed = answer.issues ? null : (answer.error || T('The check stopped part way.'));
  if (checkFailed) { checkResult = null; status(`<span class="err">${T("Check couldn't finish: {error}", { error: esc(checkFailed) })}</span>`); return null; }
  const r = checkResult = answer.issues;
  const mine = r.filter(i => !i.original);
  $('#checkBadge').style.display = mine.length ? '' : 'none'; $('#checkBadge').textContent = mine.length;
  status(mine.length ? `<span class="warn">${T('{n} problem(s) in your changes.', { n: mine.length })}</span>` : `<span class="ok">${T('No problems found in your changes.')}</span>`);
  return r;
}
function renderChecks() {
  if (checkFailed) {
    $('#ckTitle').textContent = T("Check couldn't finish");
    $('#ckOrigN').textContent = '';
    $('#ckList').innerHTML = `<div class="note" style="padding:16px 0">${T("Nothing has been checked, so there may be problems it didn't get to see.")} ${esc(checkFailed)}</div>`;
    return;
  }
  const r = checkResult || [], mine = r.filter(i => !i.original), orig = r.filter(i => i.original);
  $('#ckTitle').innerHTML = mine.length ? (mine.length === 1 ? T('1 problem in your changes') : T('{n} problems in your changes', { n: mine.length })) : T('No problems in your changes ✓');
  $('#ckOrigN').textContent = `(${orig.length})`;
  const shown = $('#ckOrig').checked ? r : mine, groups = new Map();
  for (const i of shown) { const k = i.place || T('Everywhere'); if (!groups.has(k)) groups.set(k, []); groups.get(k).push(i); }
  let html = shown.length ? '' : `<div class="note" style="padding:16px 0">${T('Nothing to fix. Your doors lead somewhere, your chests open, and every block exists.')}</div>`;
  for (const [place, list] of groups) {
    html += `<h3>${esc(place)}</h3>`;
    for (const i of list) {
      const idx = r.indexOf(i);
      html += `<div class="issue${i.original ? ' orig' : ''}"><span class="ico">${i.severity === 'error' ? '⛔' : '⚠️'}</span>
        <div>${esc(i.message)}${i.original ? ` <i style="color:var(--muted)">${T('(in the original game)')}</i>` : ''}<div class="fix">${esc(i.fix)}</div></div>
        ${i.map || i.tool === 'world' ? `<button data-i="${idx}">${T('Show')}</button>` : '<span></span>'}</div>`;
    }
  }
  $('#ckList').innerHTML = html;
}
async function openChecks(rerun) {
  $('#checks').style.display = 'flex';
  if (rerun || (!checkResult && !checkFailed)) { $('#ckTitle').textContent = T('Checking every map…'); $('#ckList').innerHTML = ''; await runChecks(); }
  renderChecks();
}
$('#check').onclick = () => openChecks(true);
$('#ckRerun').onclick = () => openChecks(true);
$('#ckClose').onclick = () => { $('#checks').style.display = 'none'; };
$('#ckOrig').onchange = renderChecks;
$('#ckList').onclick = async e => {
  const b = e.target.closest('[data-i]'); if (!b) return;
  const i = checkResult[+b.dataset.i];
  if (i.tool === 'world') { if (await saveFirst()) location.href = '/world.html'; return; }
  $('#checks').style.display = 'none';
  if (!S.map || S.map.number !== i.map) await openMap(i.map);
  if (!S.map || S.map.number !== i.map) return;
  if (i.scene != null && [...$('#sceneSel').options].some(o => +o.value === i.scene)) { $('#sceneSel').value = String(i.scene); fillTables(); }
  setTool(i.tool);
  if (i.cell) {
    const [x, z] = i.cell, z0 = +$('#zoom').value * 16;
    if (i.tool === 'doors') doorSelect(x, z);
    if (i.tool === 'chest') chestSelect(x, z, S.map.markers.find(m => m.x === x && m.z === z) || null);
    const w = i.tool === 'block' ? [x, z] : groundXY(S.map.layers[0], x, z);
    if (w) $('#view').scrollTo(w[0] * z0 - $('#view').clientWidth / 2, w[1] * z0 - $('#view').clientHeight / 2);
    S.cellMark = { x, z, block: i.tool === 'block', until: Date.now() + 4000 };
    drawAll(); setTimeout(drawAllSoon, 4100);
  }
  status(`${esc(i.message)} <span style="color:var(--muted)">${esc(i.fix)}</span>`);
};

// Problems your changes would cause: true to carry on.
// `anyway` is the closing question: "Build anyway?" or "Play anyway?".
async function checkFirst(anyway) {
  const found = await runChecks();
  if (!found && !confirm(T("Check couldn't finish, so your changes haven't been checked.") + '\n\n' + anyway)) { openChecks(false); return false; }
  const mine = (found || []).filter(i => !i.original);
  if (mine.length && !confirm(T('Found {n} problem(s) in your changes:', { n: mine.length }) + '\n\n' +
      mine.slice(0, 6).map(i => '• ' + (i.place ? i.place + ': ' : '') + i.message).join('\n') +
      (mine.length > 6 ? '\n' + T('…and {n} more', { n: mine.length - 6 }) : '') + '\n\n' + anyway)) { openChecks(false); return false; }
  return true;
}

async function doBuild() {
  if (!await saveFirst() || !await checkFirst(T('Build anyway?'))) return;
  $('#build').disabled = true; status(T('Building your game…'));
  const r = await api('/api/build', { target: 'tbs-en' });
  $('#build').disabled = false;
  if (r.error) return status(`<span class="err">${esc(r.error)}</span>`);
  log(r.tail.join('\n'));
  if (r.exit === 0) return status(`<span class="ok">${T('Your game is built.')}</span>`);
  failDialog(T("Your changes couldn't be turned into a game"), r.why || T('Your files are safe. Use Undo to step back, then try again.'), r.tail.join('\n'));
}

async function doPlay() {
  if (!await saveFirst()) return;
  refreshUndoSave();
  if (!await checkFirst(T('Play anyway?'))) return;
  const from = $('#playFrom').value;
  await buildAndPlay($('#play'), S.map ? scene()?.id : undefined, from === '' ? undefined : +from);
}

// Files just went back: what was picked may be gone. The same place and scene again.
async function reopenPlace() {
  const n = S.failed ?? S.map?.number, keep = $('#sceneSel').value;
  if (n == null) return;
  forgetPlace();
  await openMap(n);
  if ([...$('#sceneSel').options].some(o => o.value === keep)) { $('#sceneSel').value = keep; fillTables(); fillPlayFrom(); if (S.tool === 'events') { EV.stage = null; await loadEvents(); } }
}

async function resetPlace() {
  const n = S.failed ?? S.map?.number;
  if (n == null) return;
  const sharing = !S.failed && S.map.shares_grid?.length ? '\n\n' + T("This place's map is shared with {n} other place(s), and they go back too.", { n: S.map.shares_grid.length }) : '';
  if (!confirm(T('Put this place back as the original game has it?\n\nYour painting, chests, doors, pictures and events here go. You can bring them back with Undo.') + sharing)) return;
  S.pending.clear(); S.markerMoves.clear(); S.tableEdits.clear();
  const r = await api(`/api/map/${n}/reset`, {});
  if (r.error) return status(`<span class="err">${esc(r.error)}</span>`);
  if (r.shared_tables && confirm(T('{n} table(s) of people and events here are shared with other places, so they were left as they are.\n\nPut those back too? Those places lose your edits to them as well.', { n: r.shared_tables }))) {
    const again = await api(`/api/map/${n}/reset`, { shared: true });
    if (again.error) return status(`<span class="err">${esc(again.error)}</span>`);
    r.tables += again.tables; r.text = r.text || again.text; r.shared_tables = 0;
  }
  await reopenPlace();
  refreshUndoSave();
  const nothing = !r.files && !r.tables && !r.text;
  status((nothing ? T('This place already matches the original.') : `<span class="ok">${T('Back to the original.')}</span>`) + (r.shared_tables ? ` <span class="warn">${T('Some people and events here are shared with other places, so those stay as they are.')}</span>` : ''));
}

// The arrival points Play can start at, for the scene being edited.
async function fillPlayFrom() {
  const sc = scene(), box = $('#playFrom'), want = box.dataset.scene === String(sc?.id) ? box.value : '';
  box.dataset.scene = sc?.id ?? '';
  box.innerHTML = `<option value="">${T('best guess')}</option>`;
  if (!sc) return;
  const r = await api(`/api/scene/${sc.id}/arrivals`);
  if (box.dataset.scene !== String(sc.id)) return;
  for (const a of r.arrivals || []) box.insertAdjacentHTML('beforeend', `<option value="${a.entrance}">${T('arrival {n}', { n: a.entrance })}</option>`);
  if ([...box.options].some(o => o.value === want)) box.value = want;
}
$('#sceneSel').addEventListener('change', fillPlayFrom);

function log(text) { const el = $('#log'); el.style.display = 'block'; el.textContent = text; }
function status(html) { $('#status').innerHTML = html; }

// Undo takes back unsaved changes first, then saved actions newest first, from
// any tool and any place; Redo does them again until something new is saved.
$('#undo').onclick = async () => {
  if (S.saving) return;  // see doSave
  const s = S.undo.pop();
  if (s) { applyChanges([...s].reverse(), 'before'); S.redo.push(s); updateButtons(); return; }
  if (!HIST.last) return;
  if (dirtyCount() && !confirm(T("You have changes you haven't saved. Undoing your last saved change throws those away too.\n\nGo ahead?"))) return;
  S.pending.clear(); S.markerMoves.clear(); S.tableEdits.clear();
  await historyStep(false, afterHistory);
};
$('#redo').onclick = async () => {
  if (S.saving) return;
  const s = S.redo.pop();
  if (s) { applyChanges(s, 'after'); S.undo.push(s); updateButtons(); return; }
  if (!HIST.next || dirtyCount()) return;
  await historyStep(true, afterHistory);
};
// Files went back or forward: show the place that changed.
async function afterHistory(r) {
  const n = r.where;
  if (n && n !== 'world' && S.maps.some(m => m.number === n) && n !== S.map?.number && S.failed == null) {
    forgetPlace(); await openMap(n);
  } else {
    await reopenPlace();
  }
}
function placeLabel(n) { const m = S.maps?.find(x => x.number === n); return m ? (m.label || m.folder) : null; }
$('#save').onclick = doSave;
$('#resetMap').onclick = resetPlace;
$('#build').onclick = doBuild;
$('#play').onclick = doPlay;
for (const b of document.querySelectorAll('#tools button')) b.onclick = () => setTool(b.dataset.tool);
$('#editLayer').onchange = () => { drawPalette(); drawAll(); };
$('#filter').oninput = renderList;
$('#zoom').onchange = () => { save('zoom', $('#zoom').value); drawAll(); };
for (const id of ['#ovCollision', '#ovShape', '#ovGrid']) $(id).onchange = drawAll;
$('#ovStand').onchange = () => { save('ovStand', $('#ovStand').checked); WK.key = null; loadStand(); drawAll(); };
window.addEventListener('keydown', e => {
  const dialog = openDialog();
  if (dialog) {
    if (e.key === 'Escape') { dialog.style.display = 'none'; if (dialog.id === 'picker') S.regionPick = null; }
    return;
  }
  if (isTyping(e.target)) return;  // typing isn't a shortcut
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'z') { e.preventDefault(); (e.shiftKey ? $('#redo') : $('#undo')).click(); return; }
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 's') { e.preventDefault(); if (dirtyCount()) doSave(); return; }
  if (e.key === 'Escape' && S.tool === 'stamp') { setStampMode('copy'); return; }
  if (e.key.toLowerCase() === 'f' && !e.metaKey && !e.ctrlKey && $('#fillBox').style.display !== 'none') { $('#fill').checked = !$('#fill').checked; return; }
  const t = { v: 'view', b: 'block', c: 'collision', h: 'shape', k: 'chest', e: 'events', d: 'doors', p: 'points', s: 'stamp' }[e.key.toLowerCase()];
  if (t && !e.metaKey && !e.ctrlKey) setTool(t);
});
window.addEventListener('beforeunload', e => { if (dirtyCount()) { e.preventDefault(); e.returnValue = ''; } });
init().then(() => {
  const practice = S.maps?.find(m => /Sandbox/.test(m.label || ''));
  if (practice) { $('#welcomeGo').style.display = ''; $('#welcomeGo').onclick = () => openMap(practice.number); }
  if (S.map) $('#welcome').style.display = 'none';
});
