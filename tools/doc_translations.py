"""Keep the translated README and docs in step with the English ones.

The English files are the originals. Each translation lives at
README.<lang>.md (beside README.md) or docs/<lang>/<path> (for docs/<path>),
and opens with a hidden line naming the English text it was made from:

    <!-- translated from docs/SPEC.md @ 1a2b3c4d5e6f -->

(the first 12 hex digits of the English file's SHA-1).

Run: python3 tools/doc_translations.py          check, and list translations
                                                 whose English has changed since
     python3 tools/doc_translations.py --stamp  record the current English
                                                 text in every translation's
                                                 first line (after retranslating)

The check fails when a translation is missing, a link in one leads nowhere
(a file, or a #heading in the same or another page), or a translation lost
or changed a web address or a `code` span the English has. An out-of-date
translation is listed but doesn't fail: each one says the English is current.
"""

import glob
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from gsmap.i18n import LANGS  # noqa: E402

TRANSLATED = [l for l in LANGS if l != "en"]
# What is translated. docs/upstream-issues.md is written for alchemy's English
# issue tracker, docs/releases/ are notes already published with each release,
# and THIRD_PARTY_NOTICES.md is licence text: those stay English only.
DOCS = ["docs/DEVELOPING.md", "docs/PRODUCT.md", "docs/SPEC.md"]


def originals():
    research = sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, "docs", "research", "*.md")))
    return ["README.md"] + DOCS + research


def translation(original, lang):
    if original == "README.md":
        return f"README.{lang}.md"
    return os.path.join("docs", lang, os.path.relpath(original, "docs"))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def digest(rel):
    return hashlib.sha1(read(rel).encode("utf-8")).hexdigest()[:12]


STAMP = re.compile(r"^<!-- translated from (\S+) @ ([0-9a-f]{12}) -->\n")


def stamp_line(original):
    return f"<!-- translated from {original} @ {digest(original)} -->\n"


FENCE = re.compile(r"^```.*?^```", re.S | re.M)


def prose(text):
    """The text outside fenced code blocks (whose comments may be translated)."""
    return FENCE.sub("", text)


def slug(heading):
    """GitHub's anchor for a heading."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)  # links keep their text
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors(text):
    seen, out = {}, set()
    for m in re.finditer(r"^#{1,6}\s+(.+?)\s*#*\s*$", prose(text), re.M):
        s = slug(m.group(1))
        n = seen.get(s, 0)
        seen[s] = n + 1
        out.add(s if n == 0 else f"{s}-{n}")
    out.update(re.findall(r'<a (?:name|id)="([^"]+)"', text))
    return out


LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
URL = re.compile(r"https?://[^\s)>\]`\"]+")
CODE = re.compile(r"`([^`\n]+)`")


def check_links(rel, text, problems):
    here = os.path.dirname(rel)
    for target in LINK.findall(prose(text)):
        if re.match(r"[a-z]+:", target):
            continue
        path, _, frag = target.partition("#")
        dest = os.path.normpath(os.path.join(here, path)) if path else rel
        full = os.path.join(ROOT, dest)
        if not os.path.exists(full):
            problems.append(f"{rel}: link to {target}: no such file")
            continue
        if frag and dest.endswith(".md") and frag not in anchors(read(dest)):
            problems.append(f"{rel}: link to {target}: no such heading")


def same_details(original, rel, text, problems):
    eng = prose(read(original))
    tra = prose(text)
    lost = set(URL.findall(eng)) - set(URL.findall(tra))
    if lost:
        problems.append(f"{rel}: web addresses missing: {sorted(lost)[:3]}")
    lost = set(CODE.findall(eng)) - set(CODE.findall(tra))
    if lost:
        problems.append(f"{rel}: `code` spans missing or changed: {sorted(lost)[:5]}")


def main():
    stamp = "--stamp" in sys.argv
    problems, stale = [], []
    for original in originals():
        check_links(original, read(original), problems)
        for lang in TRANSLATED:
            rel = translation(original, lang)
            if not os.path.exists(os.path.join(ROOT, rel)):
                problems.append(f"{rel}: missing (a translation of {original})")
                continue
            text = read(rel)
            m = STAMP.match(text)
            if stamp:
                text = stamp_line(original) + (text[m.end():] if m else text)
                with open(os.path.join(ROOT, rel), "w", encoding="utf-8") as f:
                    f.write(text)
            elif not m or m.group(1) != original:
                problems.append(f"{rel}: first line should be {stamp_line(original).strip()}")
            elif m.group(2) != digest(original):
                stale.append(rel)
            check_links(rel, text, problems)
            same_details(original, rel, text, problems)
    for p in problems:
        print("FAIL " + p)
    for s in stale:
        print("out of date (the English changed since): " + s)
    print(f"{len(originals())} documents in {len(TRANSLATED)} languages: "
          + (f"{len(problems)} problems" if problems else "ok") + (f", {len(stale)} out of date" if stale else ""))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
