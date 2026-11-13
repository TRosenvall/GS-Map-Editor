// What the place editor and the world map share. Each page defines api() and status().

// Text for innerHTML: anything that came from a file or a patch goes through this.
function esc(text) {
  return String(text ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// ON_MAC, localWords and T come from i18n.js, which every page loads first.

// Pages forbid inline script, so a picture that may not exist asks for this instead.
document.addEventListener('error', e => { if (e.target.matches?.('img[data-hide-broken]')) e.target.remove(); }, true);

// Ticking a box or moving a slider leaves it focused, which isn't typing.
function isTyping(el) {
  if (el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') return true;
  return el.tagName === 'INPUT' && !['checkbox', 'radio', 'range', 'button'].includes(el.type);
}

// A menu keeps the keyboard after you pick from it, which would swallow the tool keys.
document.addEventListener('change', e => { if (e.target.tagName === 'SELECT') e.target.blur(); });

function failDialog(title, why, details) {
  let d = document.getElementById('failDialog');
  if (!d) {
    d = document.createElement('div');
    d.id = 'failDialog';
    d.innerHTML = `<div class="box"><h2></h2><p class="why"></p>
      <details><summary>${T('Show details')}</summary><pre></pre></details>
      <div class="row"><button class="copy">${T('Copy details for a bug report')}</button><span style="flex:1"></span><button class="ok primary">${T('OK')}</button></div></div>`;
    document.body.appendChild(d);
    d.querySelector('.ok').onclick = () => { d.style.display = 'none'; };
    d.querySelector('.copy').onclick = async e => {
      const text = d.querySelector('pre').textContent;
      try { await navigator.clipboard.writeText(text); e.target.textContent = T('Copied'); }
      catch (err) { const r = document.createRange(); r.selectNodeContents(d.querySelector('pre')); d.querySelector('details').open = true; getSelection().removeAllRanges(); getSelection().addRange(r); }
    };
  }
  d.querySelector('h2').textContent = title;
  d.querySelector('.why').textContent = why;
  d.querySelector('pre').textContent = details || T('(none)');
  d.querySelector('details').open = false;
  d.querySelector('.copy').textContent = T('Copy details for a bug report');
  d.style.display = 'flex';
}

// Build, then open the game, starting at `scene` if given. `button` is disabled
// meanwhile. True when it played.
async function buildAndPlay(button, scene, entrance) {
  if (button) button.disabled = true;
  try {
    status(T('Getting your game ready… (usually under a minute)'));
    const b = await api('/api/build', { target: 'tbs-en', playable: true });
    if (b.error) { failDialog(T("Your game couldn't be built"), b.error, b.error); status(''); return false; }
    if (b.exit !== 0) {
      failDialog(T("Your changes couldn't be turned into a game"),
        b.why || T('Your files are safe. Use Undo to step back, then try again.'),
        (b.tail || []).join('\n'));
      status(`<span class="err">${T('The game didn’t build.')}</span>`);
      return false;
    }
    const r = await api('/api/play', { scene, entrance });
    if (r.error) { failDialog(T("Your game is ready, but couldn't be opened"), r.error, r.error); status(''); return false; }
    status(`<span class="ok">${esc(r.note)}</span>`);
    return true;
  } finally {
    if (button) button.disabled = false;
  }
}

// Saved history: every action that writes files (painting once saved, chests,
// doors, events, people, the world map) can be undone and then redone, newest
// first, whichever tool made it. Each page's Undo and Redo fall back to it once
// nothing unsaved is left to take back. HIST holds what they would do.
const HIST = { last: null, next: null };
async function refreshUndoSave() {
  const r = await api('/api/history');
  HIST.last = r.last || null; HIST.next = r.next || null;
  if (typeof updateButtons === 'function') updateButtons();
}
// Where a history entry's change was: 'world', a place's name (from the page's
// place names), or null.
function historyWhere(where) {
  if (where == null) return null;
  if (where === 'world') return 'world';
  return (typeof placeLabel === 'function' ? placeLabel(where) : null) || null;
}
function historyTitle(redo) {
  const e = redo ? HIST.next : HIST.last;
  if (!e) return redo ? T('Nothing to redo') : T('Nothing to undo');
  const what = e.label, place = historyWhere(e.where);
  if (place === 'world') return redo ? T('Redo {what} on the world map', { what }) : T('Undo {what} on the world map', { what });
  if (place) return redo ? T('Redo {what} in {place}', { what, place }) : T('Undo {what} in {place}', { what, place });
  return redo ? T('Redo {what}', { what }) : T('Undo {what}', { what });
}
// What a history step did, in words ("Undid painting in Imil."), for innerHTML.
function historyDone(redo, label, where) {
  const what = esc(label), w = historyWhere(where), place = esc(w);
  if (w === 'world') return redo ? T('Redid {what} on the world map.', { what }) : T('Undid {what} on the world map.', { what });
  if (w) return redo ? T('Redid {what} in {place}.', { what, place }) : T('Undid {what} in {place}.', { what, place });
  return redo ? T('Redid {what}.', { what }) : T('Undid {what}.', { what });
}
// Undo (or redo) the newest saved action; `after(r)` reloads what the page shows.
async function historyStep(redo, after) {
  const r = await api(`/api/history/${redo ? 'redo' : 'undo'}`, {});
  if (r.error) return status(`<span class="err">${esc(r.error)}</span>`);
  HIST.last = r.last || null; HIST.next = r.next || null;
  if (r.label) await after(r);
  status(r.label ? `<span class="ok">${historyDone(redo, r.label, r.where)}</span>`
    : (redo ? T('Nothing to redo.') : T('Nothing to undo.')));
  if (typeof updateButtons === 'function') updateButtons();
}

// Escape closes whatever dialog is open; a dialog being open also stops the tool keys.
const DIALOGS = ['failDialog', 'evEdit', 'picker', 'checks', 'conn', 'exp', 'ptc', 'battles'];
function openDialog() {
  return DIALOGS.map(id => document.getElementById(id)).find(d => d && getComputedStyle(d).display !== 'none');
}

// The random battles of some encounter zones, editable (gsmap/encounters.py): for
// each, how often they come and which groups of enemies with what chance. Used by
// the world map's regions and the place editor's Battles dialog. zones: [{zone,
// where, note?, when?, shared?, level, rate, groups: [{formation, weight}]}];
// save(zone, rate, groups) is called with a zone's new values.
function battleBoxes(pane, zones, formations, advanced, save) {
  const choices = formations.map(f => `<option value="${f.formation}">${esc(f.label)}${advanced ? ` [${f.formation}]` : ''}</option>`).join('');
  const row = g => `<div class="grp"><select>${choices}</select><input type="number" min="1" max="255" value="${g.weight}" title="${T('How likely, compared with the other groups')}"><button class="drop" title="${T('Remove this group')}">×</button></div>`;
  pane.innerHTML = `<div class="note"><b>${T('Battles here')}</b></div>` + zones.map((z, zi) => `
    <div class="battle" data-z="${zi}">
      <div><b>${esc(z.where)}</b> <span class="note">${z.note ? esc(z.note) + ' · ' : ''}${T('made for level {n}', { n: z.level })}</span></div>
      ${z.when ? `<div class="note">${esc(z.when)}</div>` : ''}
      ${z.shared?.length ? `<div class="note warn">${T('Also used by {places}: a change shows there too.', { places: esc(z.shared.slice(0, 4).join(', ') + (z.shared.length > 4 ? '…' : '')) })}</div>` : ''}
      <label class="note">${T('How often (0 = never, higher is more often)')} <input type="number" min="0" max="100" class="rate" value="${z.rate}" style="width:56px"></label>
      <div class="note">${T('Groups of enemies, and how likely each is')}</div>
      <div class="grps">${z.groups.map(row).join('')}</div>
      <div class="row"><button class="add">${T('Add a group')}</button><button class="save primary">${T('Save')}</button></div>
    </div>`).join('');
  for (const box of pane.querySelectorAll('.battle')) {
    const z = zones[+box.dataset.z];
    box.querySelectorAll('.grp select').forEach((s, i) => { s.value = z.groups[i].formation; });
    box.querySelector('.add').onclick = () => {
      if (box.querySelectorAll('.grp').length >= 8) return status(`<span class="warn">${T('A zone holds at most 8 groups.')}</span>`);
      box.querySelector('.grps').insertAdjacentHTML('beforeend', row({ formation: formations[0].formation, weight: 4 }));
    };
    box.querySelector('.grps').onclick = e => { if (e.target.closest('.drop')) e.target.closest('.grp').remove(); };
    box.querySelector('.save').onclick = () => save(z.zone, +box.querySelector('.rate').value,
      [...box.querySelectorAll('.grp')].map(g => ({ formation: +g.querySelector('select').value, weight: +g.querySelector('input').value })));
  }
}
