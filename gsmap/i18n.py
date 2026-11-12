"""The editor's own words in the player's language. The game being modded stays
the English edition: names and dialogue read from it are never translated.

Every message the editor shows is written in English in the code, wrapped in
tr() (Python) or T() (the pages' JavaScript), with any changing part as a
{name} placeholder. static/i18n/<lang>.json maps each English message to its
translation; tools/extract_strings.py keeps those files in step with the code,
and tests/i18n.py checks nothing is missing.

The chosen language is kept in the editor's settings. Until one is chosen,
the browser's (on a Mac, the system's) preferred languages decide.
"""

import json
import os
import re
import sys
import threading

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDER = os.path.join(HERE, "static", "i18n")
LANGS = {"en": "English", "es": "Español", "de": "Deutsch", "fr": "Français", "it": "Italiano", "ja": "日本語"}
DEFAULT = "en"

_local = threading.local()
_cache = {}
_lock = threading.Lock()


def strings(lang):
    """{English: translation} for a language; untranslated messages are left out."""
    if lang == DEFAULT or lang not in LANGS:
        return {}
    with _lock:
        if lang not in _cache:
            try:
                with open(os.path.join(FOLDER, f"{lang}.json"), encoding="utf-8") as f:
                    raw = json.load(f)
            except (OSError, ValueError):
                raw = {}
            _cache[lang] = {k: v for k, v in raw.items() if isinstance(v, str) and v}
        return _cache[lang]


def from_header(accept_language):
    """The first of the browser's preferred languages the editor speaks."""
    for part in (accept_language or "").split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in LANGS:
            return code
    return DEFAULT


def chosen():
    """The language picked in the editor, or None."""
    from . import setup
    lang = setup.load_settings().get("language")
    return lang if lang in LANGS else None


def choose(lang):
    from . import setup
    if lang not in LANGS:
        raise ValueError("unknown language")
    settings = setup.load_settings()
    settings["language"] = lang
    setup.save_settings(settings)


def begin(headers):
    """Called at the start of each request: messages made while answering it
    are in the chosen language, or the browser's."""
    _local.lang = chosen() or from_header(headers.get("Accept-Language", "") if headers else "")
    return _local.lang


def current():
    return getattr(_local, "lang", None) or chosen() or DEFAULT


def fill(text, values):
    """Put values in for {name} placeholders. Other braces, such as the game's
    own {end_wait}, are left alone."""
    if not values:
        return text
    return re.sub(r"\{(\w+)\}", lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), text)


def N_(text):
    """Marks a message to translate later: kept in English (in history files),
    translated with tr() when shown."""
    return text


# Off a Mac a few words differ ("Show the file" for "Show in Finder"); the
# catalogs hold both forms (tools/extract_strings.py), and static/i18n.js swaps
# them in English text as it's shown. A translation looks for this computer's
# form first, as the pages do.
MAC_WORDS = ((r"Show in Finder", "Show the file"), (r"this Mac\b", "this computer"))


def _lookup(table, text):
    if sys.platform != "darwin":
        other = text
        for mac, word in MAC_WORDS:
            other = re.sub(mac, word, other)
        if other != text and other in table:
            return table[other]
    return table.get(text, text)


def tr(text, **values):
    """`text` in the current language, with its placeholders filled in."""
    return fill(_lookup(strings(current()), text), values)


def translate(text):
    """A message that was kept in English (marked with N_) in the current language."""
    return tr(text)


def script(lang=None):
    """The pages' copy: a script that sets window.I18N before anything else runs."""
    lang = lang or current()
    data = {"lang": lang, "langs": LANGS, "chosen": chosen() is not None, "strings": strings(lang)}
    return "window.I18N = " + json.dumps(data, ensure_ascii=False) + ";\n"
