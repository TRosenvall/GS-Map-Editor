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
const DIALOGS = ['failDialog', 'evEdit', 'picker', 'checks', 'conn', 'exp', 'ptc'];
function openDialog() {
  return DIALOGS.map(id => document.getElementById(id)).find(d => d && getComputedStyle(d).display !== 'none');
}
