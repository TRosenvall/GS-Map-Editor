// The atlas: every place on one canvas, joined by its doors (gsmap/atlas.py lays
// them out). Drag the background to look around, the wheel to zoom; drag a place
// to move it (the editor remembers where), click one to open it.
const $ = s => document.querySelector(s);
const A = { data: null, z: 0.5, x: 20, y: 20, byMap: {}, drag: null, pan: null };
function status(h) { $('#status').innerHTML = h; }
async function api(path, body) {
  const opt = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-GSMap': '1' }, body: JSON.stringify(body) };
  try { const r = await fetch(path, opt); return await r.json(); }
  catch (e) { return { error: T('The editor stopped answering. Is it still running?') }; }
}

function place() { $('#atlas').style.transform = `translate(${A.x}px, ${A.y}px) scale(${A.z})`; }
function zoomAt(f, cx, cy) {
  const z = Math.min(4, Math.max(0.05, A.z * f));
  A.x = cx - (cx - A.x) * z / A.z; A.y = cy - (cy - A.y) * z / A.z; A.z = z; place();
}
function fit() {
  const v = $('#view'), ms = A.data.maps;
  const w = Math.max(...ms.map(m => m.x + m.w)), h = Math.max(...ms.map(m => m.y + m.h));
  A.z = Math.min(v.clientWidth / (w + 40), v.clientHeight / (h + 60));
  A.x = 20; A.y = 30; place();
}
function centreOn(m, z) {
  const v = $('#view'); A.z = z ?? Math.max(A.z, 1);
  A.x = v.clientWidth / 2 - (m.x + m.w / 2) * A.z; A.y = v.clientHeight / 2 - (m.y + m.h / 2) * A.z; place();
}

function draw() {
  const box = $('#atlas'), svg = $('#links');
  for (const el of box.querySelectorAll('.m')) el.remove();
  for (const m of A.data.maps) {
    const el = document.createElement('div');
    el.className = 'm'; el.dataset.map = m.map;
    Object.assign(el.style, { left: m.x + 'px', top: m.y + 'px', width: m.w + 'px', height: m.h + 'px' });
    el.innerHTML = `<img loading="lazy" src="/api/map/${m.map}/thumb.png" alt=""><span>${esc(m.label)}</span>`;
    el.title = T('{place}: click to open it, drag to move it', { place: m.label });
    box.appendChild(el);
    m.el = el;
  }
  drawLinks();
}
function drawLinks() {
  const svg = $('#links');
  svg.innerHTML = '';
  if (!$('#showLinks').checked) return;
  const w = Math.max(...A.data.maps.map(m => m.x + m.w)), h = Math.max(...A.data.maps.map(m => m.y + m.h));
  svg.setAttribute('width', w); svg.setAttribute('height', h);
  for (const l of A.data.links) {
    const a = A.byMap[l.from], b = A.byMap[l.to]; if (!a || !b) continue;
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', a.x + l.fx); line.setAttribute('y1', a.y + l.fy);
    line.setAttribute('x2', b.x + l.tx); line.setAttribute('y2', b.y + l.ty);
    line.dataset.from = l.from; line.dataset.to = l.to;
    if (!l.door) line.classList.add('event');
    svg.appendChild(line);
  }
}
function highlight(n) {
  for (const line of $('#links').children) line.classList.toggle('on', line.dataset.from === n || line.dataset.to === n);
  const near = new Set(A.data.links.filter(l => l.from === n || l.to === n).map(l => l.from === n ? l.to : l.from));
  for (const m of A.data.maps) { m.el.classList.toggle('on', m.map === n); m.el.classList.toggle('near', near.has(m.map)); }
  const m = A.byMap[n];
  if (m) status(near.size ? T('{place} leads to or from {n} other places.', { place: `<b>${esc(m.label)}</b>`, n: near.size })
    : T('{place} has no doors to other places.', { place: `<b>${esc(m.label)}</b>` }));
}

// ---- moving around, moving places ---------------------------------------------------
$('#view').addEventListener('mousedown', e => {
  if (e.button !== 0) return;
  const el = e.target.closest('.m');
  if (el) {
    const m = A.byMap[el.dataset.map];
    A.drag = { m, x0: e.clientX, y0: e.clientY, mx: m.x, my: m.y, moved: false };
  } else {
    A.pan = { x0: e.clientX, y0: e.clientY, ax: A.x, ay: A.y }; $('#view').classList.add('panning');
  }
  e.preventDefault();
});
window.addEventListener('mousemove', e => {
  if (A.pan) { A.x = A.pan.ax + e.clientX - A.pan.x0; A.y = A.pan.ay + e.clientY - A.pan.y0; place(); return; }
  if (A.drag) {
    const d = A.drag, dx = (e.clientX - d.x0) / A.z, dy = (e.clientY - d.y0) / A.z;
    if (Math.abs(dx) + Math.abs(dy) > 3 / A.z) d.moved = true;
    d.m.x = Math.round(d.mx + dx); d.m.y = Math.round(d.my + dy);
    d.m.el.style.left = d.m.x + 'px'; d.m.el.style.top = d.m.y + 'px';
    drawLinks(); highlight(d.m.map);
    return;
  }
  const el = e.target.closest?.('.m');
  if (el && el.dataset.map !== A.hover) { A.hover = el.dataset.map; highlight(A.hover); }
});
window.addEventListener('mouseup', async () => {
  if (A.pan) { A.pan = null; $('#view').classList.remove('panning'); return; }
  const d = A.drag; A.drag = null;
  if (!d) return;
  if (!d.moved) {  // a click: open the place in the editor
    try { localStorage.setItem('gsmap.map', JSON.stringify(d.m.map)); } catch (e) {}
    location.href = '/?map=' + encodeURIComponent(d.m.map);
    return;
  }
  const r = await api('/api/atlas/move', { map: d.m.map, x: d.m.x, y: d.m.y });
  if (r.error) status(`<span class="err">${esc(r.error)}</span>`);
});
$('#view').addEventListener('wheel', e => {
  e.preventDefault();
  const r = $('#view').getBoundingClientRect();
  zoomAt(Math.exp(-e.deltaY * 0.0015), e.clientX - r.left, e.clientY - r.top);
}, { passive: false });
$('#zoomIn').onclick = () => zoomAt(1.4, $('#view').clientWidth / 2, $('#view').clientHeight / 2);
$('#zoomOut').onclick = () => zoomAt(1 / 1.4, $('#view').clientWidth / 2, $('#view').clientHeight / 2);
$('#fit').onclick = fit;
$('#showLinks').onchange = drawLinks;
$('#find').oninput = () => {
  const q = $('#find').value.trim().toLowerCase();
  const hits = q ? A.data.maps.filter(m => m.label.toLowerCase().includes(q)) : [];
  for (const m of A.data.maps) m.el.classList.toggle('found', hits.includes(m));
  if (hits.length) { centreOn(hits[0]); highlight(hits[0].map); }
  status(q ? (hits.length ? T('{n} places match.', { n: hits.length }) : T('No place matches.')) : '');
};
$('#resetLayout').onclick = async () => {
  if (!confirm(T('Put every place back where the atlas first laid it out?'))) return;
  const r = await api('/api/atlas/reset', {});
  if (r.error) return status(`<span class="err">${esc(r.error)}</span>`);
  await load(); status(T('Every place is back where the atlas laid it out.'));
};

async function load() {
  document.body.classList.add('busy');
  A.data = await api('/api/atlas');
  document.body.classList.remove('busy');
  if (A.data.error) return status(`<span class="err">${esc(A.data.error)}</span>`);
  A.byMap = Object.fromEntries(A.data.maps.map(m => [m.map, m]));
  draw();
}
(async () => {
  await load();
  if (!A.data || A.data.error) return;
  let last = null;
  try { last = JSON.parse(localStorage.getItem('gsmap.map')); } catch (e) {}
  if (last && A.byMap[last]) { centreOn(A.byMap[last], 1); highlight(last); } else fit();
  status(T('Every place, joined by its doors. Drag to look around, scroll to zoom, click a place to open it.'));
})();
