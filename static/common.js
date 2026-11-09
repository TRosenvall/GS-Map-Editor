// What the place editor and the world map share. Each page defines api() and status().

// Text for innerHTML: anything that came from a file or a patch goes through this.
function esc(text) {
  return String(text ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// The pages are written with a Mac's keys and words. Elsewhere (Windows,
// through WSL, and Linux) the same shortcuts use Ctrl and Alt.
const ON_MAC = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
function localWords(text) {
  if (ON_MAC) return text;
  return String(text).replace(/⇧⌘/g, 'Ctrl+Shift+').replace(/⌘/g, 'Ctrl+').replace(/⌥-click/g, 'Alt-click')
    .replace(/⌥/g, 'Alt+').replace(/Show in Finder/g, 'Show the file').replace(/this Mac\b/g, 'this computer');
}
function localizePage(root) {
  if (ON_MAC) return;
  const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n = walk.nextNode(); n; n = walk.nextNode()) n.nodeValue = localWords(n.nodeValue);
  root.querySelectorAll('[title]').forEach(el => { el.title = localWords(el.title); });
}
document.addEventListener('DOMContentLoaded', () => localizePage(document.body));

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
      <details><summary>Show details</summary><pre></pre></details>
      <div class="row"><button class="copy">Copy details for a bug report</button><span style="flex:1"></span><button class="ok primary">OK</button></div></div>`;
    document.body.appendChild(d);
    d.querySelector('.ok').onclick = () => { d.style.display = 'none'; };
    d.querySelector('.copy').onclick = async e => {
      const text = d.querySelector('pre').textContent;
      try { await navigator.clipboard.writeText(text); e.target.textContent = 'Copied'; }
      catch (err) { const r = document.createRange(); r.selectNodeContents(d.querySelector('pre')); d.querySelector('details').open = true; getSelection().removeAllRanges(); getSelection().addRange(r); }
    };
  }
  d.querySelector('h2').textContent = title;
  d.querySelector('.why').textContent = why;
  d.querySelector('pre').textContent = details || '(none)';
  d.querySelector('details').open = false;
  d.querySelector('.copy').textContent = 'Copy details for a bug report';
  d.style.display = 'flex';
}

// Build, then open the game, starting at `scene` if given. `button` is disabled
// meanwhile. True when it played.
async function buildAndPlay(button, scene, entrance) {
  if (button) button.disabled = true;
  try {
    status('Getting your game ready… (usually under a minute)');
    const b = await api('/api/build', { target: 'tbs-en', playable: true });
    if (b.error) { failDialog("Your game couldn't be built", b.error, b.error); status(''); return false; }
    if (b.exit !== 0) {
      failDialog("Your changes couldn't be turned into a game",
        b.why || 'Your files are safe. Use “Undo last save” to step back, then try again.',
        (b.tail || []).join('\n'));
      status('<span class="err">The game didn’t build.</span>');
      return false;
    }
    const r = await api('/api/play', { scene, entrance });
    if (r.error) { failDialog("Your game is ready, but couldn't be opened", r.error, r.error); status(''); return false; }
    status(`<span class="ok">${esc(r.note)}</span>`);
    return true;
  } finally {
    if (button) button.disabled = false;
  }
}

// “Undo last save” steps back through saved actions, whichever tool made them.
async function refreshUndoSave() {
  const b = document.getElementById('undoSave');
  if (!b) return;
  const r = await api('/api/history');
  b.disabled = !r.last;
  b.title = r.last ? `Undo ${r.last.label}` : 'Nothing saved to undo yet';
}
async function undoLastSave(after) {
  const r = await api('/api/history/undo', {});
  if (r.error) return status(`<span class="err">${esc(r.error)}</span>`);
  await after();
  status(r.label ? `<span class="ok">Undid ${esc(r.label)}.</span>` : 'Nothing saved to undo.');
  refreshUndoSave();
}

// Escape closes whatever dialog is open; a dialog being open also stops the tool keys.
const DIALOGS = ['failDialog', 'evEdit', 'picker', 'checks', 'conn', 'exp', 'ptc'];
function openDialog() {
  return DIALOGS.map(id => document.getElementById(id)).find(d => d && getComputedStyle(d).display !== 'none');
}
