"""Collect every message the editor shows and keep static/i18n/<lang>.json in
step: new messages are added untranslated (empty), messages no longer used
are dropped, translations are kept.

Messages are found in four places:
- Python: tr("…") and N_("…") calls in gsmap/, server.py and desktop.py (a plain string,
  never an f-string: changing parts are {name} placeholders);
- the pages' scripts: T('…') calls in static/*.js;
- the pages themselves: each text and title, placeholder or aria-label in
  static/*.html, outside script, style and data-notr elements;
- the walkability brushes' names and meanings in gsmap/data/collision.json.

Run: python3 tools/extract_strings.py          update the catalogs
     python3 tools/extract_strings.py --check  fail if they're out of step or
                                               anything is untranslated
"""

import ast
import glob
import html
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from gsmap.i18n import FOLDER, LANGS  # noqa: E402

ATTRS = ("title", "placeholder", "aria-label")
# Off a Mac the pages say these instead (MAC_WORDS in static/i18n.js and gsmap/i18n.py).
MAC_WORDS = (("Show in Finder", "Show the file"), ("this Mac", "this computer"))


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def wanted(s):
    return bool(re.search(r"[A-Za-z]{2}", s))


def from_python(problems):
    out = {}
    files = glob.glob(os.path.join(ROOT, "gsmap", "*.py")) + [os.path.join(ROOT, n) for n in ("server.py", "desktop.py")]
    for path in files:
        if path.endswith(os.path.join("gsmap", "i18n.py")):
            continue  # the machinery itself
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", None)) in ("tr", "N_") and node.args:
                arg = node.args[0]
                where = f"{os.path.relpath(path, ROOT)}:{node.lineno}"
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    out.setdefault(arg.value, where)
                else:
                    problems.append(f"{where}: tr() needs a plain string, with {{name}} placeholders")
    return out


JS_CALL = re.compile(r"""\bT\(\s*(?:'((?:\\.|[^'\\])*)'|"((?:\\.|[^"\\])*)"|`((?:\\.|[^`\\])*)`)""", re.S)


def js_unescape(s):
    return re.sub(r"\\(u[0-9a-fA-F]{4}|.)", lambda m: chr(int(m.group(1)[1:], 16)) if m.group(1)[0] == "u" and len(m.group(1)) == 5
                  else {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), s)


def from_js(problems):
    out = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "static", "*.js"))):
        if path.endswith("i18n.js"):
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for m in JS_CALL.finditer(text):
            raw = next(g for g in m.groups() if g is not None)
            line = text.count("\n", 0, m.start()) + 1
            where = f"{os.path.relpath(path, ROOT)}:{line}"
            if "${" in raw:
                problems.append(f"{where}: T() needs a plain string, with {{name}} placeholders")
                continue
            out.setdefault(js_unescape(raw), where)
    return out


class _Page(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.found = [], []

    def skipping(self):
        return any(tag in ("script", "style", "textarea") or notr for tag, notr in self.stack)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        notr = "data-notr" in a
        if not (self.skipping() or notr):
            for name in ATTRS:
                if a.get(name):
                    self.found.append(a[name])
        if tag not in self.VOID:
            self.stack.append((tag, notr))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if not self.skipping():
            self.found.append(data)


def from_html():
    out = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "static", "*.html"))):
        p = _Page()
        with open(path, encoding="utf-8") as f:
            p.feed(f.read())
        for s in p.found:
            s = norm(html.unescape(s))
            if s and wanted(s):
                out.setdefault(s, os.path.relpath(path, ROOT))
    return out


def from_data():
    """The walkability brushes' names and meanings (gsmap/names.py translates them)."""
    with open(os.path.join(ROOT, "gsmap", "data", "collision.json"), encoding="utf-8") as f:
        ranges = json.load(f)["ranges"]
    return {r[k]: "gsmap/data/collision.json" for r in ranges for k in ("name", "meaning") if r.get(k)}


def messages():
    problems = []
    found = {}
    for part in (from_html(), from_js(problems), from_python(problems), from_data()):
        for k, v in part.items():
            found.setdefault(k, v)
    for k in list(found):
        for mac, other in MAC_WORDS:
            if mac in k:
                found.setdefault(k.replace(mac, other), found[k])
    return found, problems


def main():
    check = "--check" in sys.argv
    found, problems = messages()
    keys = sorted(found)
    changed, missing = [], {}
    os.makedirs(FOLDER, exist_ok=True)
    for lang in LANGS:
        if lang == "en":
            continue
        path = os.path.join(FOLDER, f"{lang}.json")
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
        except (OSError, ValueError):
            old = {}
        new = {k: old.get(k, "") for k in keys}
        missing[lang] = [k for k in keys if not new[k]]
        if new != old or list(new) != list(old):
            changed.append(lang)
            if not check:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(new, f, ensure_ascii=False, indent=1)
                    f.write("\n")
    for p in problems:
        print(p)
    print(f"{len(keys)} messages; " + ", ".join(f"{lang}: {len(m)} untranslated" for lang, m in missing.items()))
    if check:
        if changed:
            print("out of step with the code: " + ", ".join(changed) + " (run tools/extract_strings.py)")
        sys.exit(1 if problems or changed or any(missing.values()) else 0)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
