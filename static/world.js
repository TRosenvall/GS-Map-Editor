const $ = s => document.querySelector(s);
const W = { tool: 'view', block: { 0: null, 1: null }, recent: { 0: [], 1: [] }, kind: 1, cells: {}, sel: null, ver: 0 };
const KIND_COLOURS = { 0: 'transparent', 1: 'rgb(255,214,10)', 2: 'rgb(255,120,40)', 3: 'rgb(80,200,255)', 4: 'rgb(190,90,255)',
  5: 'rgb(60,230,120)', 6: 'rgb(255,80,160)', 21: 'rgb(240,240,255)', 31: 'rgb(255,50,50)' };
const HELP = {
  view: [T('Look around'), T('Hover to see a spot\'s region and what it does. Click a town, dungeon or blue step spot to see where it leads.')],
  ground: [T('Paint ground'), localWords(T('Pick a block, then click or drag on the map. ⌥-click the map to pick up the block under the cursor. Changes save as you paint; Undo takes the last stroke back and Redo puts it back. The pause-screen map is a separate picture: it won\'t follow coastline changes.'))],
  overlay: [T('Paint overlay'), T('Mountains, trees and coastline sit on the overlay, drawn over the ground. Walking is decided by both layers\' tiles.')],
  region: [T('Encounter regions'), T('Each region has its own random battles. Pick one and paint; the region overlay turns on so you can see them.')],
  icons: [T('Towns and dungeons'), T('Drag a town to move it. Click one to change where it leads.')],
  steps: [T('Step spots'), T('Blue squares lead somewhere when the party steps on them. Click one to change where it leads or remove it, or click any other square to make a new one.')],
};
function status(h) { $('#status').innerHTML = h; }
async function api(path, body) {
  const opt = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-GSMap': '1' }, body: JSON.stringify(body) };
  const busy = body === undefined ? null : setTimeout(() => document.body.classList.add('busy'), 200);
  const r = await fetch(path, opt);
  try { return await r.json(); } catch (e) { return { error: `HTTP ${r.status}` }; }
  finally { if (busy) { clearTimeout(busy); document.body.classList.remove('busy'); if (!path.includes('history')) refreshUndoSave(); } }
}
const zoom = () => +$('#zoom').value;

// ---- the world: 16x16 chunks of 256 px, loaded as you scroll ---------------------
function buildTiles() {
  const z = zoom(), s = 256 * z;
  $('#world').style.width = $('#world').style.height = (4096 * z) + 'px';
  for (const [id, kind, cls] of [['#tiles', 'chunk', 'ch'], ['#walkL', 'walk', 'ov'], ['#kindL', 'kind', 'ov']]) {
    const box = $(id); box.innerHTML = '';
    if (kind === 'walk' && !$('#ovWalk').checked) continue;
    if (kind === 'kind' && !$('#ovKind').checked) continue;
    for (let cy = 0; cy < 16; cy++) for (let cx = 0; cx < 16; cx++) {
      const img = document.createElement('img');
      img.className = cls; img.loading = 'lazy'; img.dataset.k = `${cx},${cy}`; img.alt = '';
      img.src = `/api/world/${kind}/${cx}/${cy}.png?v=${W.ver}`;
      Object.assign(img.style, { left: cx * s + 'px', top: cy * s + 'px', width: s + 'px', height: s + 'px' });
      box.appendChild(img);
    }
  }
  drawMarks(); drawPending();
}
function reloadChunks(keys) {
  W.ver++;
  for (const img of document.querySelectorAll('#world img')) {
    if (!keys.has(img.dataset.k)) continue;
    img.src = img.src.replace(/\?v=\d+/, `?v=${W.ver}`);
  }
  for (const k of keys) delete W.cells[k];
}

// ---- places: town icons, step spots, arrival points --------------------------------
function short(l) { return (l || '').split(' · ')[0]; }
function drawMarks() {
  const box = $('#marks'), z = zoom(); box.innerHTML = '';
  $('#world').classList.toggle('far', z < 1);
  if (!W.data || !$('#ovPlaces').checked) return;
  for (const ic of W.data.places.icons) {
    if (!ic.x && !ic.z) continue;
    const el = document.createElement('div'), lead = ic.lead;
    el.className = 'icon' + (W.sel && W.sel.actor === ic.actor ? ' sel' : '') + (lead && lead.scene == null ? ' nowhere' : '');
    el.style.left = (ic.x / 2 * z) + 'px'; el.style.top = (ic.z / 2 * z) + 'px';
    const name = lead ? (lead.scene == null ? T('leads nowhere') : short(lead.label)) : '';
    el.innerHTML = `<img src="/api/asset/sprite/${ic.sprite}.png" data-hide-broken style="height:${Math.max(16, 24 * z)}px">` +
      (name || W.adv ? `<span>${esc(name)}${W.adv ? ` [${ic.actor}]` : ''}</span>` : '');
    el.title = lead && lead.label ? T('{place}, arrival point {n}', { place: lead.label, n: lead.entrance }) : T('Runs a scene script (where it leads depends on the story)');
    el.onmousedown = e => iconDown(e, ic);
    box.appendChild(el);
  }
  for (const st of W.data.places.steps) {
    if (!st.lead) continue;
    const el = document.createElement('div');
    el.className = 'step' + (st.lead.scene == null ? ' nowhere' : '') + (W.sel?.step && W.sel.step.gx === st.gx && W.sel.step.gy === st.gy ? ' sel' : '');
    Object.assign(el.style, { left: st.gx * 16 * z + 'px', top: st.gy * 16 * z + 'px', width: 16 * z + 'px', height: 16 * z + 'px' });
    el.title = st.lead.scene == null ? T('Leads nowhere') : T('{place}, arrival point {n}', { place: st.lead.label, n: st.lead.entrance });
    el.onmousedown = e => { e.preventDefault(); if (W.tool === 'view' || W.tool === 'icons' || W.tool === 'steps') { e.stopPropagation(); selectStep(st); } };
    box.appendChild(el);
  }
  if (W.sel?.newStep) {  // the square a new step spot would go on
    const el = document.createElement('div'), { gx, gy } = W.sel.newStep;
    el.className = 'step sel';
    Object.assign(el.style, { left: gx * 16 * z + 'px', top: gy * 16 * z + 'px', width: 16 * z + 'px', height: 16 * z + 'px', borderStyle: 'dashed' });
    box.appendChild(el);
  }
  if (W.adv) for (const a of W.data.places.arrivals) {
    const el = document.createElement('div'); el.className = 'arr'; el.textContent = a.entrance;
    el.style.left = (a.x / 2 * z) + 'px'; el.style.top = (a.z / 2 * z) + 'px'; box.appendChild(el);
  }
}
function selectIcon(ic) {
  W.sel = { actor: ic.actor, trigger: 100 + ic.actor };
  const lead = ic.lead;
  $('#iconInfo').innerHTML = !lead ? T('This one runs a scene script, so where it leads can\'t be changed here.')
    : lead.scene == null ? `<span class="err">${T('Leads nowhere.')}</span> ${T('Link it to a place.')}`
    : T('Leads to <b>{place}</b>, arrival point {n}.', { place: esc(lead.label), n: lead.entrance })
      + (W.adv ? ` <span class="note">${T('(trigger {trigger}, exit kind {kind})', { trigger: 100 + ic.actor, kind: lead.kind })}</span>` : '');
  $('#iconLink').style.display = lead ? '' : 'none';
  $('#iconLink').textContent = T('Change where it leads…'); $('#stepRemove').style.display = 'none'; $('#stepWiden').style.display = 'none';
  $('#iconRemove').style.display = ic.added && W.tool === 'icons' ? '' : 'none';
  showPane('icon'); drawMarks();
}
function selectStep(st) {
  W.sel = { step: st, trigger: st.code };
  $('#iconInfo').innerHTML = st.lead.scene == null ? `<span class="err">${T('This spot leads nowhere.')}</span>`
    : T('Stepping here leads to <b>{place}</b>, arrival point {n}.', { place: esc(st.lead.label), n: st.lead.entrance })
      + (W.adv ? ` <span class="note">${T('(code {code})', { code: st.code })}</span>` : '');
  $('#iconLink').style.display = st.lead.scripted ? 'none' : '';
  $('#iconLink').textContent = T('Change where it leads…');
  $('#stepRemove').style.display = W.tool === 'steps' && !st.lead.scripted ? '' : 'none';
  $('#stepWiden').style.display = W.tool === 'steps' && st.code < 100 ? '' : 'none';
  $('#iconRemove').style.display = 'none';
  showPane('icon'); drawMarks();
}
// A square that isn't a step spot yet, in the Step spots tool.
function selectNewStep(gx, gy) {
  W.sel = { newStep: { gx, gy } };
  $('#iconInfo').innerHTML = T('Not a step spot. Make one here, leading anywhere in the game.');
  $('#iconLink').style.display = ''; $('#iconLink').textContent = T('Make a step spot here…');
  $('#stepRemove').style.display = 'none'; $('#iconRemove').style.display = 'none'; $('#stepWiden').style.display = 'none';
  showPane('icon'); drawMarks();
}
// Widening a spot: each square clicked next joins it, until another tool or Esc.
$('#stepWiden').onclick = () => {
  const st = W.sel?.step; if (!st) return;
  W.widen = st.code;
  status(T('Click squares to add them to this spot. Press Esc when you\'re done.'));
};
$('#stepRemove').onclick = async () => {
  const st = W.sel?.step; if (!st || !confirm(T('Remove this step spot?'))) return;
  const r = await api('/api/world/step', { action: 'remove', gx: st.gx, gy: st.gy });
  if (r.error) return status(`<span class="err">${esc(r.error)}</span>`);
  W.cells = {}; await loadPlaces(); showPane(null);
  status(`<span class="ok">${T('Removed the step spot.')}</span> ${T('Press ▶ Play to try it.')}`);
};
let drag = null;
function iconDown(e, ic) {
  if (W.tool !== 'view' && W.tool !== 'icons') return;
  e.stopPropagation(); e.preventDefault();
  if (W.tool === 'view') return selectIcon(ic);
  drag = { ic, el: e.currentTarget, x0: e.clientX, y0: e.clientY, moved: false };
}
window.addEventListener('mousemove', e => {
  if (!drag) return;
  const dx = e.clientX - drag.x0, dy = e.clientY - drag.y0;
  if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
  const z = zoom();
  drag.el.style.left = (drag.ic.x / 2 * z + dx) + 'px'; drag.el.style.top = (drag.ic.z / 2 * z + dy) + 'px';
});
window.addEventListener('mouseup', async e => {
  if (!drag) return;
  const d = drag; drag = null;
  if (!d.moved) return selectIcon(d.ic);
  const z = zoom(), x = Math.round(d.ic.x + (e.clientX - d.x0) * 2 / z), zz = Math.round(d.ic.z + (e.clientY - d.y0) * 2 / z);
  const name = esc(short(d.ic.lead?.label));
  status(name ? T('Moving {name}…', { name }) : T('Moving the icon…'));
  const r = await api('/api/world/icon', { action: 'move', actor: d.ic.actor, x, z: zz, move_arrivals: $('#moveArrivals').checked });
  if (r.error) { status(`<span class="err">${esc(r.error)}</span>`); drawMarks(); return; }
  await loadPlaces();
  const n = r.arrivals_moved.length;
  const moved = name
    ? (n ? T('<span class="ok">Moved {name}</span>, with {n} arrival point(s).', { name, n }) : T('<span class="ok">Moved {name}</span>.', { name }))
    : (n ? T('<span class="ok">Moved the icon</span>, with {n} arrival point(s).', { n }) : T('<span class="ok">Moved the icon</span>.'));
  status(`${moved} ${T('Press ▶ Play to try it.')}`);
});
async function loadPlaces() {
  W.data = await api('/api/world');
  if (W.data.error) { status(`<span class="err">${W.data.error}</span>`); return; }
  drawMarks(); buildKinds();
  if (W.sel?.actor) { const ic = W.data.places.icons.find(i => i.actor === W.sel.actor); if (ic) selectIcon(ic); }
}

// ---- painting ------------------------------------------------------------------------
function cellAt(e) {
  const r = $('#world').getBoundingClientRect(), z = zoom();
  return [Math.floor((e.clientX - r.left) / (16 * z)), Math.floor((e.clientY - r.top) / (16 * z))];
}
async function cells(gx, gy) {
  const k = `${gx >> 4},${gy >> 4}`;
  if (!W.cells[k]) W.cells[k] = api(`/api/world/cells/${gx >> 4}/${gy >> 4}`);
  return (await W.cells[k])[gy & 15][gx & 15];
}
let stroke = null;
$('#world').addEventListener('mousedown', async e => {
  if (e.button !== 0) return;
  const [gx, gy] = cellAt(e);
  if (e.altKey && (W.tool === 'ground' || W.tool === 'overlay' || W.tool === 'region')) {
    const c = await cells(gx, gy);
    if (W.tool === 'region') { W.kind = (c[0] >>> 24) & 0x7f; buildKinds(); }
    else pickBlock(c[W.tool === 'ground' ? 0 : 1] & 0xffff);
    return;
  }
  if (W.tool === 'icons' && W.placing != null) {
    const r = $('#world').getBoundingClientRect(), z = zoom();
    const x = Math.round((e.clientX - r.left) * 2 / z), zz = Math.round((e.clientY - r.top) * 2 / z);
    W.sel = { newIcon: { x, z: zz, sprite: W.placing } }; W.placing = null;
    return openPicker();
  }
  if (W.tool === 'steps') {
    if (gx < 0 || gy < 0 || gx > 255 || gy > 255) return;
    const code = ((await cells(gx, gy))[0] >>> 16) & 0xff;
    if (W.widen != null && !code) {
      const r = await api('/api/world/step', { action: 'extend', gx, gy, code: W.widen });
      if (r.error) return status(`<span class="err">${esc(r.error)}</span>`);
      W.cells = {}; await loadPlaces();
      return status(`<span class="ok">${T('The spot now covers {n} squares.', { n: r.cells })}</span> ${T('Press Esc when you\'re done.')}`);
    }
    if (!code) return selectNewStep(gx, gy);
    const st = W.data.places.steps.find(s => s.gx === gx && s.gy === gy);
    if (st) return selectStep(st);
    return status(`<span class="warn">${T('Something already happens on that square. Pick another, or change that spot.')}</span>`);
  }
  if (W.tool === 'ground' || W.tool === 'overlay') {
    if (W.block[layerOf()] == null) return status(`<span class="warn">${T('Pick a block first.')}</span>`);
  } else if (W.tool !== 'region') return;
  e.preventDefault();
  stroke = new Map(); paintCell(gx, gy);
});
$('#world').addEventListener('mousemove', async e => {
  const [gx, gy] = cellAt(e);
  if (stroke) { paintCell(gx, gy); return; }
  if (gx < 0 || gy < 0 || gx > 255 || gy > 255) return;
  hover(gx, gy);
});
window.addEventListener('mouseup', async () => {
  if (!stroke) return;
  const edits = [...stroke.values()]; stroke = null;
  if (!edits.length) return;
  const r = await api('/api/world/edits', { edits });
  if (r.error) { status(`<span class="err">${esc(r.error)}</span>`); $('#pend').innerHTML = ''; return; }
  reloadChunks(new Set(edits.map(e => `${e.gx >> 4},${e.gy >> 4}`)));
  setTimeout(() => { $('#pend').innerHTML = ''; }, 400);
  const saved = edits.length === 1 ? T('Saved 1 cell.') : T('Saved {n} cells.', { n: edits.length });
  status(`<span class="ok">${saved}</span> ${T('Press ▶ Play to try it.')}`);
});
const layerOf = () => W.tool === 'overlay' ? 1 : 0;
function paintCell(gx, gy) {
  if (gx < 0 || gy < 0 || gx > 255 || gy > 255) return;
  const key = `${gx},${gy}`; if (stroke.has(key)) return;
  const z = zoom(), el = document.createElement('div');
  Object.assign(el.style, { left: gx * 16 * z + 'px', top: gy * 16 * z + 'px', width: 16 * z + 'px', height: 16 * z + 'px' });
  el.className = 'pv';
  if (W.tool === 'region') {
    stroke.set(key, { gx, gy, layer: 0, kind: W.kind });
    el.style.background = KIND_COLOURS[W.kind] || '#fff'; el.style.opacity = .5;
  } else {
    const l = layerOf(), b = W.block[l];
    stroke.set(key, { gx, gy, layer: l, block: b });
    const cols = 18;
    el.style.background = `url(/api/world/atlas/${l}.png?cols=${cols}) ${-(b % cols) * 16 * z}px ${-Math.floor(b / cols) * 16 * z}px / ${cols * 16 * z}px auto`;
    el.style.imageRendering = 'pixelated';
  }
  $('#pend').appendChild(el);
}
function drawPending() { $('#pend').innerHTML = ''; }
async function hover(gx, gy) {
  const c = await cells(gx, gy), kind = (c[0] >>> 24) & 0x7f, code = (c[0] >>> 16) & 0xff;
  const st = code && W.data?.places.steps.find(s => s.gx === gx && s.gy === gy);
  const region = W.data?.regions[kind] || T('Region {n}', { n: kind });
  const leads = st?.lead ? ` · ${st.lead.label ? T('leads to <b>{place}</b>', { place: esc(st.lead.label) }) : T('leads to <b>nowhere</b>')}` : '';
  status(`${esc(region)}${leads}` +
    (W.adv ? ` · ${T('cell {x},{y} · ground {ground} · overlay {overlay} · code {code}', { x: gx, y: gy, ground: c[0] & 0xffff, overlay: c[1] & 0xffff, code })}${c[0] >>> 31 ? ` · ${T('bank')}` : ''}` : ` · ${gx},${gy}`));
}

// ---- block and region palettes ----------------------------------------------------------
function showPane(which) {
  $('#blockPane').style.display = which === 'block' ? '' : 'none';
  $('#kindPane').style.display = which === 'kind' ? '' : 'none';
  $('#iconPane').style.display = which === 'icon' ? '' : 'none';
  $('#battlePane').style.display = which === 'kind' ? '' : 'none';
}
function setTool(t) {
  W.tool = t; W.sel = null; W.widen = null;
  for (const b of document.querySelectorAll('#tools button')) b.classList.toggle('on', b.dataset.tool === t);
  $('#toolTitle').textContent = HELP[t][0]; $('#toolHelp').textContent = HELP[t][1];
  if (t === 'ground' || t === 'overlay') {
    showPane('block'); $('#atlas').src = `/api/world/atlas/${layerOf()}.png?cols=18`; drawPick(); drawRecent();
  } else if (t === 'region') { showPane('kind'); if (!$('#ovKind').checked) { $('#ovKind').checked = true; buildTiles(); } if (W.data) buildBattles(); }
  else showPane(null);
  W.placing = null;
  $('#newIconPane').style.display = t === 'icons' ? '' : 'none';
  if (t === 'icons') fillIconSprites();
  drawMarks();
}
// New town icons: a picture the game's own towns use, a click on the map, then where it leads.
function fillIconSprites() {
  const sel = $('#newIconSprite'); if (!W.data || sel.options.length) return;
  for (const s of W.data.icon_sprites || []) sel.add(new Option(s.name, s.sprite));
  sel.onchange = () => { $('#newIconImg').src = `/api/asset/sprite/${sel.value}.png`; };
  sel.onchange();
}
$('#newIconGo').onclick = () => {
  if (!$('#newIconSprite').value) return;
  W.placing = +$('#newIconSprite').value;
  status(T('Click the map where the new icon should go.'));
};
$('#iconRemove').onclick = async () => {
  const actor = W.sel?.actor; if (actor == null || !confirm(T('Remove this icon?'))) return;
  const r = await api('/api/world/icon', { action: 'remove', actor });
  if (r.error) return status(`<span class="err">${esc(r.error)}</span>`);
  W.sel = null; await loadPlaces(); showPane(null);
  status(`<span class="ok">${T('Removed the icon.')}</span> ${T('Press ▶ Play to try it.')}`);
};
$('#atlas').onclick = e => {
  const r = $('#atlas').getBoundingClientRect(), sc = 288 / r.width;
  const b = Math.floor((e.clientY - r.top) * sc / 16) * 18 + Math.floor((e.clientX - r.left) * sc / 16);
  if (b < W.data.blocks) pickBlock(b);
};
function pickBlock(b) {
  const l = layerOf(); W.block[l] = b;
  W.recent[l] = [b, ...W.recent[l].filter(x => x !== b)].slice(0, 12);
  drawPick(); drawRecent();
}
function blockCanvas(b, l, cv) {
  const g = cv.getContext('2d'), img = new Image();
  img.onload = () => { g.imageSmoothingEnabled = false; g.clearRect(0, 0, 16, 16); g.drawImage(img, (b % 18) * 16, Math.floor(b / 18) * 16, 16, 16, 0, 0, 16, 16); };
  img.src = `/api/world/atlas/${l}.png?cols=18`;
}
function drawPick() {
  const l = layerOf(), b = W.block[l];
  $('#pickText').textContent = b == null ? localWords(T('Pick a block, or ⌥-click the map')) : (W.adv ? T('block {n}', { n: b }) : T('Selected block'));
  if (b != null) blockCanvas(b, l, $('#pickCv')); else $('#pickCv').getContext('2d').clearRect(0, 0, 16, 16);
}
function drawRecent() {
  const l = layerOf(); $('#recent').innerHTML = '';
  for (const b of W.recent[l]) {
    const cv = document.createElement('canvas'); cv.width = cv.height = 16; cv.style.width = cv.style.height = '24px';
    cv.onclick = () => pickBlock(b); blockCanvas(b, l, cv); $('#recent').appendChild(cv);
  }
}
function buildKinds() {
  const pane = $('#kindPane'); pane.innerHTML = '';
  for (const [k, label] of Object.entries(W.data.regions)) {
    const b = document.createElement('button');
    b.className = +k === W.kind ? 'on' : '';
    b.innerHTML = `<i style="background:${KIND_COLOURS[k] || '#888'}"></i>${esc(label)}${W.adv ? ` <span class="note">[${k}]</span>` : ''}`;
    b.onclick = () => { W.kind = +k; buildKinds(); };
    pane.appendChild(b);
  }
  if (W.tool === 'region') buildBattles();
}

// The region's random battles (gsmap/encounters.py): per zone (open ground,
// forests) how often they come, and which groups of enemies with what chance.
async function buildBattles() {
  const pane = $('#battlePane');
  if (!W.enc) W.enc = await api('/api/world/encounters');
  if (W.enc.error) { pane.innerHTML = `<div class="note err">${esc(W.enc.error)}</div>`; pane.style.display = ''; return; }
  const reg = W.enc.regions.find(r => r.region === W.kind);
  pane.style.display = '';
  if (!reg) { pane.innerHTML = `<div class="note">${T('No random battles here.')}</div>`; return; }
  battleBoxes(pane, reg.zones.map(z => ({ ...z, note: z.environments.join(', ') })), W.enc.formations, W.adv, async (zone, rate, groups) => {
    const r = await api('/api/world/encounters', { zone, rate, groups });
    if (r.error) return status(`<span class="err">${esc(r.error)}</span>`);
    W.enc = null; await buildBattles(); refreshUndoSave();
    status(r.changed ? `<span class="ok">${T("Saved the region's battles.")}</span> ${T('Press ▶ Play to try it.')}` : T('Nothing changed.'));
  });
}

// ---- undo, build, play --------------------------------------------------------------------
// Everything here saves as it's made, so Undo and Redo step through the saved
// history (common.js), newest first, as they do in the place editor.
function updateButtons() {
  $('#undo').disabled = !HIST.last; $('#undo').title = localWords(historyTitle(false) + (HIST.last ? ' (⌘Z)' : ''));
  $('#redo').disabled = !HIST.next; $('#redo').title = localWords(historyTitle(true) + (HIST.next ? ' (⇧⌘Z)' : ''));
}
async function reloadWorld() { W.enc = null; await loadPlaces(); W.ver++; buildTiles(); }
function placeLabel(n) { const m = W.maps?.find(x => x.number === n); return m ? (m.label || m.folder) : null; }
$('#undo').onclick = () => historyStep(false, reloadWorld);
$('#redo').onclick = () => historyStep(true, reloadWorld);
$('#build').onclick = async () => {
  $('#build').disabled = true; status(T('Building your game…'));
  const r = await api('/api/build', { target: 'tbs-en' }); $('#build').disabled = false;
  if (r.error) return status(`<span class="err">${esc(r.error)}</span>`);
  if (r.exit === 0) return status(`<span class="ok">${T('Your game is built.')}</span>`);
  failDialog(T("Your changes couldn't be turned into a game"), T('Your files are safe. Use Undo to step back, then try again.'), (r.tail || []).join('\n'));
};
$('#play').onclick = () => buildAndPlay($('#play'), 2);  // 2: the world map's scene
$('#resetWorld').onclick = async () => {
  if (!confirm(T('Put the world map back as the original game has it?') + '\n\n' + T('Your painting, moved towns and changed links go. You can bring them back with Undo.'))) return;
  const r = await api('/api/world/reset', {});
  if (r.error) return status(`<span class="err">${esc(r.error)}</span>`);
  await reloadWorld(); refreshUndoSave();
  const nothing = !r.files && !r.tables && !r.text;
  status(nothing ? T('The world map already matches the original.') : `<span class="ok">${T('The world map is back to the original.')}</span>`);
};

// ---- destination picker (as in the place editor) ----------------------------------------------
const PK = {};
function openPicker() {
  const cur = W.sel?.actor ? W.data.places.icons.find(i => i.actor === W.sel.actor)?.lead : W.sel?.step?.lead;
  PK.scene = cur?.scene ?? null; PK.entrance = cur?.entrance ?? null;
  $('#pkFilter').value = ''; pkList(); $('#picker').style.display = 'flex';
  if (PK.scene != null) pkScene(PK.scene, PK.entrance); else pkUpdate();
}
function pkList() {
  const q = $('#pkFilter').value.trim().toLowerCase();
  $('#pkList').innerHTML = W.scenes.filter(sc => sc.map != null)
    .map(sc => ({ id: sc.id, label: W.names.sceneById[sc.id]?.label || sc.name || T('scene {n}', { n: sc.id }) }))
    .filter(sc => !q || sc.label.toLowerCase().includes(q))
    .map(sc => `<div data-id="${sc.id}" class="${sc.id === PK.scene ? 'on' : ''}">${esc(sc.label)}</div>`).join('');
}
$('#pkFilter').oninput = pkList;
$('#pkList').onclick = e => { const id = e.target.closest('[data-id]')?.dataset.id; if (id != null) pkScene(+id, null); };
async function pkScene(id, entrance) {
  PK.scene = id; PK.entrance = entrance; pkList();
  const r = await api(`/api/scene/${id}/arrivals`); if (PK.scene !== id) return;
  $('#pkHint').style.display = 'none'; const dots = $('#pkDots'); dots.innerHTML = '';
  $('#pkArrivals').innerHTML = r.arrivals.length ? '' : `<div class="note" style="padding:12px">${T('No arrival points listed; the party arrives at the default spot (0).')}</div>`;
  if (!r.arrivals.length) PK.entrance = 0;
  if (r.map) {
    $('#pkImg').src = `/api/map/${r.map}/render.png`;
    for (const a of r.arrivals) {
      const b = document.createElement('button'); b.textContent = a.entrance; b.dataset.e = a.entrance;
      b.style.left = (a.x - r.bounds[0] * 8) + 'px'; b.style.top = (a.z - r.bounds[1] * 8) + 'px';
      b.onclick = () => { PK.entrance = a.entrance; pkUpdate(); }; dots.appendChild(b);
    }
  }
  pkUpdate();
}
function pkUpdate() {
  for (const b of $('#pkDots').children) b.classList.toggle('on', +b.dataset.e === PK.entrance);
  const label = PK.scene != null ? (W.names.sceneById[PK.scene]?.label || T('scene {n}', { n: PK.scene })) : '';
  $('#pkSel').innerHTML = !label ? '' : PK.entrance != null ? T('<b>{place}</b>, arrival point {n}', { place: esc(label), n: PK.entrance })
    : T('<b>{place}</b> · click an arrival point', { place: esc(label) });
  $('#pkOk').disabled = PK.scene == null || PK.entrance == null;
}
$('#pkCancel').onclick = () => { $('#picker').style.display = 'none'; };
$('#pkOk').onclick = async () => {
  $('#picker').style.display = 'none';
  const body = { target_scene: PK.scene, target_entrance: PK.entrance };
  const r = W.sel.newStep ? await api('/api/world/step', { action: 'add', ...W.sel.newStep, ...body })
    : W.sel.newIcon ? await api('/api/world/icon', { action: 'add', ...W.sel.newIcon, ...body })
    : await api('/api/world/icon', { action: 'relink', trigger: W.sel.trigger, ...body });
  if (r.error) return status(`<span class="err">${esc(r.error)}</span>`);
  if (W.sel.newStep) { W.cells = {}; showPane(null); }
  if (W.sel.newIcon) { W.sel = null; showPane(null); }
  await loadPlaces();
  status(`<span class="ok">${T('Now leads to <b>{place}</b>.', { place: esc(r.label) })}</span> ${T('Press ▶ Play to try it.')}`);
};
$('#iconLink').onclick = openPicker;

// ---- start ---------------------------------------------------------------------------------
for (const b of document.querySelectorAll('#tools button')) b.onclick = () => setTool(b.dataset.tool);
$('#zoom').onchange = () => {
  const v = $('#view'), z0 = W.z || zoom(), cx = (v.scrollLeft + v.clientWidth / 2) / z0, cy = (v.scrollTop + v.clientHeight / 2) / z0;
  W.z = zoom(); buildTiles(); v.scrollTo(cx * W.z - v.clientWidth / 2, cy * W.z - v.clientHeight / 2);
};
$('#ovWalk').onchange = $('#ovKind').onchange = buildTiles;
$('#ovPlaces').onchange = drawMarks;
$('#advanced').onchange = () => { W.adv = $('#advanced').checked; document.body.classList.toggle('advanced', W.adv); try { localStorage.setItem('gsmap.advanced', W.adv); } catch (e) {} drawMarks(); buildKinds(); };
window.addEventListener('keydown', e => {
  const dialog = openDialog();
  if (dialog) { if (e.key === 'Escape') dialog.style.display = 'none'; return; }
  if (e.key === 'Escape' && W.widen != null) { W.widen = null; status(T('Done adding squares.')); return; }
  if (isTyping(e.target)) return;  // typing isn't a shortcut
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'z') { e.preventDefault(); (e.shiftKey ? $('#redo') : $('#undo')).click(); return; }
  const t = { v: 'view', g: 'ground', o: 'overlay', r: 'region', t: 'icons', p: 'steps' }[e.key.toLowerCase()];
  if (t && !e.metaKey && !e.ctrlKey) setTool(t);
});
(async () => {
  try { W.adv = JSON.parse(localStorage.getItem('gsmap.advanced')) || false; } catch (e) { W.adv = false; }
  $('#advanced').checked = W.adv; document.body.classList.toggle('advanced', W.adv);
  const [names, scenes, maps] = await Promise.all([api('/api/names'), api('/api/scenes'), api('/api/maps')]);
  W.maps = maps;
  W.names = names; W.names.sceneById = Object.fromEntries(names.scenes.map(s => [s.id, s])); W.scenes = scenes;
  W.z = zoom(); buildTiles(); setTool('view');
  await loadPlaces();
  refreshUndoSave();
  // start over Vale
  const vale = W.data.places.icons.find(i => i.lead?.scene === 5) || { x: 5678, z: 1200 };
  const v = $('#view'); v.scrollTo(vale.x / 2 * zoom() - v.clientWidth / 2, vale.z / 2 * zoom() - v.clientHeight / 2);
  status(T('The world map. Pick a tool above; hover anywhere to see its region and what it does.'));
})();
