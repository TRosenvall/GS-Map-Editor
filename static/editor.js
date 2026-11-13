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
  const r = await fetch(path, opt);
  let j; try { j = await r.json(); } catch (e) { j = { error: `HTTP ${r.status}` }; }
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
  if (S.map && S.map.number !== n) EV.stage = null;  // a story stage belongs to one map's tables
  if (!await saveFirst()) return;
  $('#status').textContent = T('Loading map {n}…', { n });
  const map = await api(`/api/map/${n}`);
  if (map.error) {
    S.failed = map.damaged ? n : null;  // Reset place can still put it back
    if (map.damaged) failDialog(T("This place can't be opened"), map.error, map.detail);
    status(`<span class="err">${esc(map.error)}</span>`);
    return;
  }
  if (!S.map || S.map.number !== n) forgetPlace();
  S.failed = null;
  S.map = map; save('map', n);
  if (S.block != null && (S.block >= map.metatile_count || map.retired?.includes(S.block))) S.block = null;
  S.pending.clear(); S.markerMoves.clear(); S.tableEdits.clear(); S.undo = []; S.redo = [];
  const bases = [...new Set(map.layers.filter(l => l.priority).map(l => l.char_base))];
  S.atlas = {};
  await Promise.all(bases.map(async b => { S.atlas[b] = await loadImage(`/api/map/${n}/atlas/${b}.png?t=${Date.now()}`); }));
  buildLayerControls();
  renderList(); drawAll(); drawPalette(); updateButtons();
  await loadScenes();
  fillPlayFrom();
  if (S.tool === 'stamp') setStampMode(S.stampMode);
  api(`/api/map/${n}/legend`).then(l => { S.legend = l.error ? {} : l; drawAll(); });
  loadChests(); loadDoors();
  if (S.tool === 'events') await loadEvents();
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
  S.doorAt = null; $('#doorForm').style.display = 'none';
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

// Heights as the map uses them, tallest first; ⌥-click copies one from the map.
function buildHeightPanel() {
  const box = $('#heightPanel'), m = S.map; if (!m) return;
  const used = new Map();
  for (const row of m.grids.shape || []) for (const v of row) used.set(v, (used.get(v) || 0) + 1);
  const describe = v => {
    const r = m.shapes?.[v]; if (!r) return T('Height {v}', { v });
    const px = Math.round(cellHeightPx(r));
    return r[0] & 15 ? T('Slope or step, {px} px', { px }) : T('Flat, {px} px', { px });
  };
  const rows = [...used.keys()].sort((a, b) => cellHeightPx(m.shapes?.[b]) - cellHeightPx(m.shapes?.[a]));
  let current = parseInt($('#value').value, 16);
  if (current >= (m.shapes?.length ?? Infinity)) { $('#value').value = ''; current = NaN; }  // another place's height
  box.innerHTML = localWords(`<div class="note" style="padding:0 10px 6px;color:var(--muted);font-size:12px">${T('Pick a height, then paint. Things stand at the height of the ground they’re on, and you can only step up a little at a time. Or ⌥-click the map to copy a height from it.')}</div>`);
  const list = document.createElement('div'); list.style.cssText = 'display:flex;flex-direction:column;gap:3px;padding:0 10px 8px;max-height:240px;overflow:auto';
  for (const v of rows) {
    const b = document.createElement('button');
    b.textContent = describe(v) + (S.advanced ? ` [${hex(v)}]` : '');
    b.style.textAlign = 'left';
    if (v === current) b.style.borderColor = 'var(--accent)';
    b.onclick = () => { $('#value').value = hex(v); buildHeightPanel(); };
    list.appendChild(b);
  }
  box.appendChild(list);
}
function cellHeightPx(r) {
  if (!r) return 0;
  const k = r[0] & 15, a = r[1], b = r[2], c = r[3];
  return (k === 0 ? a : k === 1 || k === 2 ? (a + b) / 2 : Math.max(a, b, c)) * 8;
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

function drawCell(ctx, x, y) {
  const m = S.map, z = +$('#zoom').value, s = 16 * z;
  ctx.fillStyle = '#000'; ctx.fillRect(x * s, y * s, s, s);
  for (const l of visibleLayers()) {
    if (!S.show[l.index]) continue;
    const img = S.atlas[l.char_base]; if (!img) continue;
    const b = at(m.blocks, l, x, y); if (b == null) continue;
    const id = b & 0xfff; if (id >= m.metatile_count) continue;
    ctx.globalAlpha = S.alpha[l.index];
    ctx.drawImage(img, (id % 32) * 16, Math.floor(id / 32) * 16, 16, 16, x * s, y * s, s, s);
  }
  ctx.globalAlpha = 1;
  if ($('#ovGrid').checked) { ctx.strokeStyle = 'rgba(255,255,255,0.12)'; ctx.strokeRect(x * s + .5, y * s + .5, s, s); }
}

// Walkability and height, each square drawn where the game shows its ground:
// lower ground first, so raised squares sit on top.
function drawGroundOverlays(ctx) {
  const m = S.map, col = $('#ovCollision').checked, sh = $('#ovShape').checked;
  if (!col && !sh) return;
  const z = +$('#zoom').value, s = 16 * z, l = layer(), cells = [];
  for (let y = 0; y < m.size[1]; y++) for (let x = 0; x < m.size[0]; x++) {
    const [gx, gy] = gridXY(l, x, y);
    cells.push([heightPx(l, gx, gy), x, y - heightPx(l, gx, gy) / 16, gx, gy]);
  }
  cells.sort((a, b) => a[0] - b[0]);
  for (const [, x, y, gx, gy] of cells) {
    if (col) { const c = collisionColor(m.grids.collision?.[gy]?.[gx]); if (c) { ctx.fillStyle = c; ctx.fillRect(x * s, y * s, s, s); } }
    if (sh) {
      const v = m.grids.shape?.[gy]?.[gx];
      if (v) {
        ctx.fillStyle = `rgba(80,160,255,${Math.min(0.15 + v * 0.06, 0.7)})`; ctx.fillRect(x * s, y * s, s, s);
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
  cv.width = w * 16 * z; cv.height = h * 16 * z; ctxSetup(ctx);
  const ov = $('#ov'); ov.width = cv.width; ov.height = cv.height;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) drawCell(ctx, x, y);
  drawGroundOverlays(ctx); drawStand(ctx);
  markPending(ctx); drawMarkers(ctx); drawDoors(ctx); drawEvents(ctx); drawPoints(ctx);
}

function redrawCells(cells) {
  if ($('#ovCollision').checked || $('#ovShape').checked || $('#ovStand').checked) return drawAll();  // raised squares overlap other cells
  const ctx = $('#cv').getContext('2d'); ctxSetup(ctx);
  for (const [x, y] of cells) drawCell(ctx, x, y);
  markPending(ctx); drawMarkers(ctx); drawDoors(ctx); drawEvents(ctx); drawPoints(ctx);
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
  const v = S.map.grids.shape?.[gy]?.[gx], row = S.map.shapes?.[v];
  if (!row) return 0;
  const k = row[0] & 15, a = row[1], b = row[2], c = row[3];
  return 8 * (k === 0 ? a : (k === 1 || k === 2) ? (a + b) / 2 : Math.max(a, b, c));
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
    const c = S.chests?.find(c => c.x === mk.x && c.z === mk.z);
    if (c?.chest && c.value >> 20 === 1 && S.icons[c.value & 0xffff]?.complete) ctx.drawImage(S.icons[c.value & 0xffff], w[0] * s + 2, w[1] * s + 2, s - 4, s - 4);
    else if (z >= 2) { ctx.fillStyle = moved ? '#7ee787' : '#e0b84a'; ctx.fillText(hex(mk.id), w[0] * s + s / 2, w[1] * s + s / 2); }
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

function paintAt(x, y) {
  const m = S.map, l = layer();
  if (x < 0 || y < 0 || x >= m.size[0] || y >= m.size[1]) return;
  // Blocks are drawn where they are; walkability and height belong to the ground under the cursor.
  const [gx, gy] = S.tool === 'block' || !S.mouse ? gridXY(l, x, y) : (groundAt(l, S.mouse[0], S.mouse[1]) || gridXY(l, x, y));
  if (S.tool === 'block') {
    if (S.block == null) return status(`<span class="warn">${T('Pick a block first.')}</span>`);
    setValue('block', gx, gy, (m.blocks[gy][gx] & 0xf000) | S.block);  // keep the cell's flags
  } else if (S.tool === 'collision' || S.tool === 'shape') {
    const v = parseInt($('#value').value, 16);
    if ($('#value').value.trim() === '') return status(`<span class="warn">${S.tool === 'shape' ? T('Pick a height on the right first.') : T('Pick a brush on the right first.')}</span>`);
    if (isNaN(v) || v < 0 || v > 0xff) return status(`<span class="err">${T('That value should be 0 to ff.')}</span>`);
    if (S.tool === 'collision' && m.markers?.some(k => k.x === gx && k.z === gy)) return status(`<span class="warn">${T('That square holds a chest or stone. Move or remove it first.')}</span>`);
    setValue(S.tool, gx, gy, v);
  }
  redrawCells([[x, y]]);
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
  if (!S.map) return;
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
  painting = true; S.stroke = []; lastCell = `${x},${y}`; paintAt(x, y);
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
  if (painting && key !== lastCell) { lastCell = key; paintAt(x, y); }
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
  const what = mk ? `<b>${(S.legend[String(mk.id)] || [T('Chest')])[0]}</b>` : `<b>${collisionName(col)}</b>`;
  status(S.advanced
    ? T('cell {cell} (ground {ground}) · blocks {blocks} · {what} · height {height} ({px} px) on L{layer}', {
      cell: `<b>${x},${y}</b>`, ground: `${gx},${gy}`, blocks: parts.join(' '), what,
      height: `<b>${hex(m.grids.shape?.[gy]?.[gx])}</b>`, px: heightPx(l, gx, gy), layer: l.index })
    : T('{what} · height {px} px · cell {cell}', { what, px: heightPx(l, gx, gy), cell: `${x},${y}` }));
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
  if (!S.allScenes) S.allScenes = await api('/api/scenes');
  const r = await api(`/api/map/${S.map.number}/scenes`);
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
  rowsOf(t).forEach((r, i) => {
    if ((t.kind === 'entrances' ? r.entrance : r.sprite) < 0) return;
    const [x, y] = pointPx(t, r), cx = x * z, cy = y * z, rad = 5 * z;
    ctx.lineWidth = 2;
    if (t.kind === 'entrances') {
      ctx.strokeStyle = '#3ddc84'; ctx.strokeRect(cx - rad, cy - rad, rad * 2, rad * 2);
      ctx.fillStyle = '#3ddc84'; ctx.fillText(r.entrance, cx, cy - rad - 6);
    } else {
      const img = spriteImage(r.sprite);
      if (img && img.complete && img.naturalWidth) {
        const w = img.naturalWidth * z, h = img.naturalHeight * z;
        ctx.drawImage(img, cx - w / 2, cy - h + 4 * z, w, h);  // feet at the point
      } else {
        ctx.strokeStyle = r.x === 0 && r.z === 0 ? '#888' : '#ff5cf0';
        ctx.beginPath(); ctx.arc(cx, cy, rad, 0, 7); ctx.stroke();
      }
      if (S.advanced) { ctx.fillStyle = '#ff5cf0'; ctx.fillText(actorNumber(rowsOf(t), i), cx, cy - rad - 6); }
    }
  });
  ctx.lineWidth = 1;
}

function spriteImage(id) {
  if (!(id in S.spriteImg)) {
    const img = new Image(); img.onload = () => drawAll(); img.src = `/api/asset/sprite/${id}.png`;
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
  if (!S.entranceCache[k]) S.entranceCache[k] = await api(`/api/scene-overlay/${k}/entrances`);
  return S.entranceCache[k];
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
    hash: m.metatiles_hash, family: m.family, familySize: m.family_size, layers: [], object: [] };
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
      if (walk && L.collision) { setValue('collision', gx, gy, L.collision[j][i]); setValue('shape', gx, gy, L.shape[j][i]); }
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
  if (!S.icons[id]) { S.icons[id] = new Image(); S.icons[id].onload = () => S.map && drawAll(); S.icons[id].src = `/api/asset/item/${id}.png`; }
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
    return status(T('This is {what}; it can be moved but not changed here.', { what: S.legend[String(mk.id)]?.[0] || T('a Psynergy Stone or scripted find') }));
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
  const q = `scene=${sc.id}` + (EV.stage ? `&table=${EV.stage}` : '');
  const r = await api(`/api/map/${S.map.number}/events?${q}`);
  if (r.error) { $('#evList').innerHTML = `<div class="err">${esc(r.error)}</div>`; return; }
  EV.data = r; EV.stage = r.symbol; staleStand();
  $('#evStage').innerHTML = r.tables.map(t => `<option value="${esc(t)}" ${t === r.symbol ? 'selected' : ''}>${esc(variantName(t))}</option>`).join('');
  $('#evShared').style.display = r.shared_with.length ? '' : 'none';
  $('#evShared').textContent = r.shared_with.length ? T('This scene shares its people and events with {places}: changes show there too.', { places: r.shared_with.slice(0, 3).join(', ') + (r.shared_with.length > 3 ? '…' : '') }) : '';
  if (!S.flags) { S.flags = await api('/api/flags'); $('#flagList').innerHTML = S.flags.flags.map(f => `<option value="${esc(f.label)}">`).join(''); }
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
      const words = e.text != null ? '“' + showNames(gameToPlain(e.text)) + '”' : e.does + (e.script && S.advanced ? ` [${e.script}]` : '');
      html += `<div class="ev ${EV.sel === e.index ? 'on' : ''}" data-i="${e.index}"><div class="h"><b>${esc(evTitle(e))}</b>${e.condition !== -1 ? `<span class="w">${esc(e.when)}</span>` : ''}</div>
        <div class="t">${esc(words.slice(0, 220))}</div>
        <div class="act">${e.editable_text ? `<button data-a="edit">${T('Change words')}</button>` : ''}<button data-a="when">${T('When…')}</button>
          ${e.kind !== 'exit' ? `<button data-a="remove">${T('Remove')}</button>` : `<button data-a="doors">${T('Open in Doors')}</button>`}</div></div>`;
    }
  }
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
    const [ex, ey] = entityXY(p.x, p.z), x = ex * z, y = ey * z;
    const on = sel && sel.actor === p.actor, talks = EV.data.events.some(e => e.actor === p.actor && e.kind === 'talk');
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
function evClick(e, x, y) {
  if (!EV.data) return;
  const [sx, sy] = mousePx(e), [px, pz] = groundPx(sx, sy);
  const near = EV.data.people.map(p => { const [ex, ey] = entityXY(p.x, p.z); return [Math.hypot(ex - sx, ey - sy), p]; }).sort((a, b) => a[0] - b[0])[0];
  $('#evSpot').style.display = 'flex';
  if (near && near[0] < 10) {
    const p = near[1], talks = EV.data.events.some(ev => ev.actor === p.actor && ev.kind === 'talk');
    EV.filter = { actor: p.actor, label: `${p.name || T('This person')}` }; EV.spot = null;
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
  const edits = walkEdits(), key = `${S.map.number}:${sc.id}:${EV.stage}:${JSON.stringify(edits)}`;
  if (key === WK.key && WK.cells) return;
  WK.key = key;
  const r = await api(`/api/map/${S.map.number}/walk`, { scene: sc.id, table: EV.stage, edits });
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
  return api(`/api/map/${S.map.number}/walk/check`, { scene: scene().id, table: EV.stage, x, z, actor, edits: walkEdits() });
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
  return level.count > 1 ? T("Level {n} squares to the path's height ({px} px)", { n: level.count, px: level.height })
    : T("Level 1 square to the path's height ({px} px)", { px: level.height });
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
  const actor = actorNumber(rowsOf(t), i), r = await checkSpot(x, z, actor);
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
  PK.scene = id; PK.entrance = entrance; pkList();
  const r = await api(`/api/scene/${id}/arrivals`);
  if (PK.scene !== id) return;
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
  const own = await api('/api/maps/own-tileset').catch(() => []);
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
async function doSave() {
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
  const r = await api(`/api/map/${S.map.number}/edits`, { edits: sent, markers });
  if (r.error) { S.saveError = r.error; status(`<span class="err">${T('Not saved: {error}', { error: esc(r.error) })}</span>`); updateButtons(); return; }
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
    html += `<h3>${place}</h3>`;
    for (const i of list) {
      const idx = r.indexOf(i);
      html += `<div class="issue${i.original ? ' orig' : ''}"><span class="ico">${i.severity === 'error' ? '⛔' : '⚠️'}</span>
        <div>${esc(i.message)}${i.original ? ` <i style="color:var(--muted)">${T('(in the original game)')}</i>` : ''}<div class="fix">${esc(i.fix)}</div></div>
        ${i.map ? `<button data-i="${idx}">${T('Show')}</button>` : '<span></span>'}</div>`;
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
  const s = S.undo.pop();
  if (s) { applyChanges([...s].reverse(), 'before'); S.redo.push(s); updateButtons(); return; }
  if (!HIST.last) return;
  if (dirtyCount() && !confirm(T("You have changes you haven't saved. Undoing your last saved change throws those away too.\n\nGo ahead?"))) return;
  S.pending.clear(); S.markerMoves.clear(); S.tableEdits.clear();
  await historyStep(false, afterHistory);
};
$('#redo').onclick = async () => {
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
  const t = { v: 'view', b: 'block', c: 'collision', h: 'shape', k: 'chest', e: 'events', d: 'doors', p: 'points', s: 'stamp' }[e.key.toLowerCase()];
  if (t && !e.metaKey && !e.ctrlKey) setTool(t);
});
window.addEventListener('beforeunload', e => { if (dirtyCount()) { e.preventDefault(); e.returnValue = ''; } });
init().then(() => {
  const practice = S.maps?.find(m => /Sandbox/.test(m.label || ''));
  if (practice) { $('#welcomeGo').style.display = ''; $('#welcomeGo').onclick = () => openMap(practice.number); }
  if (S.map) $('#welcome').style.display = 'none';
});
