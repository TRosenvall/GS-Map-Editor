"""The editor's languages: every message the code shows has a translation in
every language, and each translation keeps what the code fills in or the page
needs: its {placeholders}, its HTML tags and the keys it names (⌘ ⇧ ⌥ ▶).

Run: python3 tests/i18n.py
"""

import collections
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from gsmap import i18n  # noqa: E402
import extract_strings  # noqa: E402

failed = 0


def check(what, ok, info=""):
    global failed
    print(("ok   " if ok else "FAIL ") + what + (f"  ({info})" if info and not ok else ""))
    failed += not ok


def parts(text):
    return (collections.Counter(re.findall(r"\{\w+\}", text)),
            collections.Counter(re.findall(r"</?\w+[^>]*>", text)),
            collections.Counter(c for c in text if c in "⌘⇧⌥▶"))


# ---- the machinery
check("a placeholder is filled in", i18n.fill("Moved {n} squares.", {"n": 3}) == "Moved 3 squares.")
check("the game's own braces are left alone", i18n.fill("Hi {name}{end_wait}", {"name": "Isaac"}) == "Hi Isaac{end_wait}")
check("the browser's language is used when it's one the editor has",
      i18n.from_header("es-MX,es;q=0.9,en;q=0.8") == "es" and i18n.from_header("pt-BR,ru") == "en")
check("English needs no catalog", i18n.strings("en") == {})

# ---- the catalogs
found, problems = extract_strings.messages()
check("every message is a plain string with placeholders", not problems, problems[:5])
check("there are messages to translate", len(found) > 300, len(found))
for lang in i18n.LANGS:
    if lang == "en":
        continue
    with open(os.path.join(i18n.FOLDER, f"{lang}.json"), encoding="utf-8") as f:
        cat = json.load(f)
    missing = [k for k in found if not cat.get(k)]
    check(f"{lang}: every message is translated", not missing, f"{len(missing)}, e.g. {missing[:3]}")
    stale = [k for k in cat if k not in found]
    check(f"{lang}: no translations of messages the code no longer has", not stale, f"{len(stale)}, e.g. {stale[:3]}")
    broken = [k for k, v in cat.items() if v and parts(k) != parts(v)]
    check(f"{lang}: translations keep their placeholders, tags and keys", not broken,
          "; ".join(f"{k!r} -> {cat[k]!r}" for k in broken[:3]))

print("all ok" if not failed else f"{failed} FAILED")
sys.exit(1 if failed else 0)
