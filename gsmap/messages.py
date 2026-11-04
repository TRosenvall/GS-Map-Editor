"""The game's English text (games/tbs/text/en.po): read every line, add new
ones, and edit the ones the editor added.

Each message is a gettext entry: `msgctxt` (its linker name, or "message"),
`msgid` (its 5-digit number) and `msgstr` (the text, possibly split over
several quoted lines). In the text, \\n starts a display line, {page_break}
a new box, and {end_wait} waits for a button at the end.

New messages take the next numbers and live in one block the editor owns,
between `# gsmod: editor messages BEGIN/END`. The game's own lines are
never rewritten in place: changing what someone says points their event at
a new line, so any other use of the old one stays as it was.
"""

import os
import re

from . import layout
from .fsio import atomic_write

BEGIN = "# gsmod: editor messages BEGIN (gs-mapedit; lines added in the editor)"
END = "# gsmod: editor messages END"
LINE_WIDTH, LINES_PER_BOX = 22, 3  # what fits a dialogue box comfortably

ENTRY = re.compile(r'(?:^msgctxt "((?:[^"\\]|\\.)*)"\n)?^msgid "(\d{5})"\nmsgstr ((?:"(?:[^"\\]|\\.)*"\n?)+)', re.M)


def _unquote(chunks):
    out = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', chunks))
    return out.replace('\\"', '"').replace("\\\\", "\\")


def _quote(text):
    """msgstr lines for text (with real newlines), as the file writes them."""
    esc = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n\n")
    esc = esc.replace("{page_break}", "{page_break}\n")
    parts = [p for p in esc.split("\n") if p]
    if len(parts) == 1:
        return f'msgstr "{parts[0]}"\n'
    return 'msgstr ""\n' + "".join(f'"{l}"\n' for l in parts)


_PARSED = {}  # en.po path -> (mtime, text, entries, commands); 65,000 lines take a while


class Messages:
    def __init__(self, root):
        self.path = os.path.join(root, layout.TEXT_EN)
        stamp = os.stat(self.path).st_mtime_ns
        cached = _PARSED.get(self.path)
        if not cached or cached[0] != stamp:
            text = open(self.path, encoding="utf-8").read()
            entries = {}
            for m in ENTRY.finditer(text):
                entries[int(m.group(2))] = {
                    "ctx": m.group(1), "text": _unquote(m.group(3)).replace("\\n", "\n"),
                    "start": m.start(), "end": m.end(),
                }
            cached = _PARSED[self.path] = (stamp, text, entries, set(re.findall(r"\{[a-z_]+(?::\d+)?\}", text)))
        _, self.text, self.entries, self.commands = cached

    def get(self, n):
        e = self.entries.get(n)
        return e["text"] if e else None

    def _block(self):
        b, e = self.text.find(BEGIN), self.text.find(END)
        return (b, e) if b >= 0 and e > b else (None, None)

    def owned(self, n):
        b, e = self._block()
        ent = self.entries.get(n)
        return b is not None and ent is not None and b < ent["start"] < e

    def check(self, text):
        """Why the game can't show this text, or None."""
        try:
            re.sub(r"\{[^}]*\}", "", text).encode("cp1252")
        except UnicodeEncodeError as e:
            return f"the game's font has no {text[e.start]!r}"
        for cmd in re.findall(r"\{[^}]*\}", text):
            if cmd not in self.commands:
                return f"{cmd} isn't a text command the game knows"
        if not text.strip():
            return "the line is empty"
        return None

    def add(self, text):
        problem = self.check(text)
        if problem:
            raise ValueError(problem)
        n = max(self.entries) + 1
        entry = f'msgctxt "message"\nmsgid "{n:05d}"\n' + _quote(text) + "\n"
        b, e = self._block()
        if b is None:
            self.text = self.text.rstrip("\n") + "\n\n" + BEGIN + "\n\n" + entry + END + "\n"
        else:
            self.text = self.text[:e] + entry + self.text[e:]
        self._save()
        return n

    def set(self, n, text):
        if not self.owned(n):
            raise ValueError("only lines added in the editor are changed in place")
        problem = self.check(text)
        if problem:
            raise ValueError(problem)
        ent = self.entries[n]
        new = f'msgctxt "{ent["ctx"] or "message"}"\nmsgid "{n:05d}"\n' + _quote(text)
        self.text = self.text[:ent["start"]] + new + self.text[ent["end"]:]
        self._save()

    def _save(self):
        atomic_write(self.path, self.text)
        _PARSED.pop(self.path, None)
        self.__init__(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(self.path)))))


def compose(text, width=LINE_WIDTH, lines_per_box=LINES_PER_BOX):
    """Plain writing -> game text: words wrapped to the box (a line break you
    type is kept), a new box every few lines or at a blank line, {end_wait}
    at the end. Text commands
    ({protagonist_name}…) count as about five letters."""
    def length(s):
        return len(re.sub(r"\{[^}]*\}", "xxxxx", s))

    boxes = []
    for para in re.split(r"\n\s*\n", text.strip()):
        lines = []
        for forced in para.split("\n"):  # a single line break is kept
            cur = ""
            for word in forced.split():
                if cur and length(cur) + 1 + length(word) > width:
                    lines.append(cur)
                    cur = word
                else:
                    cur = f"{cur} {word}" if cur else word
            if cur:
                lines.append(cur)
        for i in range(0, len(lines), lines_per_box):
            boxes.append("\n".join(lines[i:i + lines_per_box]))
    return "{page_break}".join(boxes) + "{end_wait}"


def plain(game_text):
    """Game text -> plain writing, for editing: boxes become blank lines."""
    t = game_text.replace("{end_wait}", "").replace("{page_break}", "\n\n")
    return re.sub(r"(?<!\n)\n(?!\n)", " ", t).strip()
