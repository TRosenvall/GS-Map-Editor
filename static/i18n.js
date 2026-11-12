// The editor's words in the chosen language (gsmap/i18n.py). /i18n-strings.js,
// loaded just before this, sets window.I18N: the language and its
// translations, keyed by the English text.
//
// T('Moved {n} squares.', { n }) translates a message made in script. Text the
// pages hold, or put in with innerHTML, is translated as it appears, when a
// whole text or a title matches a message exactly. Anything inside an element
// marked data-notr (the game's own names and dialogue) is left alone.

const I18N_DATA = window.I18N || { lang: 'en', langs: { en: 'English' }, strings: {} };
const I18N_STRINGS = I18N_DATA.strings || {};
document.documentElement.lang = I18N_DATA.lang;

// The pages are written with a Mac's keys and words. Elsewhere (Windows,
// through WSL, and Linux) the same shortcuts use Ctrl and Alt.
const ON_MAC = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
function localWords(text) {
  if (ON_MAC) return text;
  return String(text).replace(/⇧⌘/g, 'Ctrl+Shift+').replace(/⌘/g, 'Ctrl+').replace(/⌥-click/g, 'Alt-click')
    .replace(/⌥/g, 'Alt+').replace(/Show in Finder/g, 'Show the file').replace(/this Mac\b/g, 'this computer');
}

// Off a Mac a few words differ ("Show the file" for "Show in Finder"); the
// catalogs hold both forms, so look for this computer's first.
const MAC_WORDS = [[/Show in Finder/g, 'Show the file'], [/this Mac\b/g, 'this computer']];
function lookup(key) {
  if (!ON_MAC) {
    const other = MAC_WORDS.reduce((k, [re, w]) => k.replace(re, w), key);
    if (other !== key && I18N_STRINGS[other] != null) return I18N_STRINGS[other];
  }
  return I18N_STRINGS[key];
}
function T(text, values) {
  let t = lookup(text) ?? text;
  if (values) t = t.replace(/\{(\w+)\}/g, (m, k) => (k in values ? values[k] : m));
  return t;
}

// A text as shown: translated when it is a message, with this computer's keys.
function shownText(s) {
  const key = s.replace(/\s+/g, ' ').trim();
  const t = key && lookup(key);
  return localWords(t ? s.match(/^\s*/)[0] + t + s.match(/\s*$/)[0] : s);
}
const I18N_ATTRS = ['title', 'placeholder', 'aria-label'];
function skipped(node) {
  const el = node.nodeType === 1 ? node : node.parentElement;
  return !el || el.closest('[data-notr], script, style, textarea');
}
function translateNode(node) {
  if (node.nodeType === 3) {
    if (skipped(node)) return;
    const v = shownText(node.nodeValue);
    if (v !== node.nodeValue) node.nodeValue = v;
  } else if (node.nodeType === 1) {
    if (skipped(node)) return;
    for (const a of I18N_ATTRS) {
      const v = node.getAttribute(a);
      if (v) { const t = shownText(v); if (t !== v) node.setAttribute(a, t); }
    }
    for (const c of node.childNodes) translateNode(c);
  }
}
if (I18N_DATA.lang !== 'en' || !ON_MAC) {
  const watch = new MutationObserver(list => {
    for (const m of list) {
      if (m.type === 'childList') m.addedNodes.forEach(translateNode);
      else if (m.type === 'characterData') translateNode(m.target);
      else if (m.type === 'attributes') translateNode(m.target);
    }
  });
  document.addEventListener('DOMContentLoaded', () => {
    translateNode(document.body);
    watch.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: I18N_ATTRS });
  });
}

// A <select> that switches the editor's language, and reloads the page in it.
function langPicker(select) {
  if (!select) return;
  select.innerHTML = Object.entries(I18N_DATA.langs).map(([code, name]) => `<option value="${code}">${name}</option>`).join('');
  select.value = I18N_DATA.lang;
  select.onchange = async () => {
    await fetch('/api/language', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-GSMap': '1' }, body: JSON.stringify({ lang: select.value }) });
    location.reload();
  };
}
document.addEventListener('DOMContentLoaded', () => langPicker(document.getElementById('lang')));
