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
from .i18n import tr

BEGIN = "# gsmod: editor messages BEGIN (gs-mapedit; lines added in the editor)"
END = "# gsmod: editor messages END"
LINE_WIDTH, LINES_PER_BOX = 22, 3  # what fits a dialogue box comfortably
MAX_LINE = 4000  # far past anything the game says; a much longer line stops the build

# What phones and Macs type in place of plain punctuation.
TYPED = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-",
                       "\u2026": "...", "\u00a0": " "})
ALPHABET = re.compile(r'^"X-Alchemy-Symbol-Count: (\d+)', re.M)
COMMAND = re.compile(r"\{[^}]*\}")

ENTRY = re.compile(r'(?:^msgctxt "((?:[^"\\]|\\.)*)"\n)?^msgid "(\d{5})"\nmsgstr ((?:"(?:[^"\\]|\\.)*"\n?)+)', re.M)


def _unquote(chunks):
    out = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', chunks))
    return out.replace('\\"', '"').replace("\\\\", "\\")


def tidy(text):
    """Smart quotes, long dashes and the like, as the plain marks the game has."""
    return text.translate(TYPED)


def _symbol(ch):
    """The number ags-text gives a character, or None if it has none."""
    try:
        return ch.encode("cp1252")[0]
    except UnicodeEncodeError:
        return None


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
            # Commands the game's own lines use: a line of ours can't vouch for itself.
            b, e = text.find(BEGIN), text.find(END)
            stock = text[:b] + text[e:] if 0 <= b < e else text
            cached = _PARSED[self.path] = (stamp, text, entries, set(re.findall(r"\{[a-z_]+(?::\d+)?\}", stock)))
        _, self.text, self.entries, self.commands = cached

    def alphabet(self):
        """How many symbols this edition's text can use (its catalog's own header)."""
        m = ALPHABET.search(self.text)
        return int(m.group(1)) if m else 256

    def get(self, n):
        e = self.entries.get(n)
        return e["text"] if e else None

    def _block(self):
        # Searching 65,000 lines for the markers is slow, and bad_lines asks
        # once per message: keep the answer for this version of the text.
        if getattr(self, "_block_of", None) is not self.text:
            b, e = self.text.find(BEGIN), self.text.find(END)
            self._block_at = (b, e) if b >= 0 and e > b else (None, None)
            self._block_of = self.text
        return self._block_at

    def owned(self, n):
        b, e = self._block()
        ent = self.entries.get(n)
        return b is not None and ent is not None and b < ent["start"] < e

    def check(self, text):
        """Why the game can't show this text, or None."""
        limit = self.alphabet()
        if len(text) > MAX_LINE:
            return tr("That's far too long for the game. Split it into several lines.")
        for ch in COMMAND.sub("", text).replace("\n", ""):
            symbol = _symbol(ch)
            if symbol is None or symbol < 32 or symbol >= limit:
                return tr("The game's font has no “{ch}”, so it would stop your game from building. "
                          "Use plain letters, numbers and punctuation, with no accents.", ch=ch)
        for cmd in COMMAND.findall(text):
            if cmd not in self.commands:
                return tr("{command} isn't a text command the game knows. Remove it, or fix its spelling.", command=cmd)
        if not COMMAND.sub("", text).strip():
            return tr("The line is empty. Write what it says.")
        return None

    def bad_lines(self):
        """[(number, text, why)] of the editor's own lines the game can't build."""
        out = []
        for n, ent in self.entries.items():
            if self.owned(n):
                problem = self.check(ent["text"])
                if problem:
                    out.append((n, ent["text"], problem))
        return out

    def add(self, text):
        text = tidy(text)
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
            raise ValueError(tr("only lines added in the editor are changed in place"))
        text = tidy(text)
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
