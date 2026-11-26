"""Cells a room's own code changes as it plays: a door Psynergy opens, a
pillar pushed into a gap, a bridge the story lowers.

The walking check (walk.py) reads the map as it is saved. Rooms whose paths
open later need the cells their scene code copies in, which it does with the
map grid's copy calls (alchemy's include/field/event.h):

    MapGrid_CopyCellAttributes(sourceX, sourceY, width, height, toX, toY);

copies where the party can walk and the height (everything but the picture);
MapGrid_CopyCells copies whole cells. Older alchemy versions call the routines
under them directly, some through a `Far` stand-in; those count the same. Copies of pictures alone change nothing
underfoot and are left out. Only calls written in plain numbers are read: a
copy to a place worked out while playing (where a pillar was pushed) can't be
known beforehand. Since 2026-11-25 many copies name their cells (an enum constant
in the scene's source or its header); those count as their numbers.

One overlay serves several rooms, and each room only runs part of its code.
What runs in a room is followed from what the room itself starts: its own
trigger and placement tables (the ones its getters return, getters.py) and its
branch of the overlay's start-up function. From those, every function or table
they name is followed in turn. A test of which room is playing is decided; any
other test (a story flag) could go either way, so both sides count.
"""

import re

from .doors import _scene_files, _source_text, sources_generation
from .getters import _decide, _matching, _scene_macros, _strip_comments
from .sceneedit import scene_tables

COPY = re.compile(r"\bMapGrid_(CopyCellAttributes|CopyCellAttributeRect|CopyCells|CopyCellPictureCellsRect|CopyCellTilesCellsRect)(?:Far)?"
                  r"\(([^;{}]*?)\)\s*;")
# An argument the editor can work out: numbers and the source's named numbers
# (an enum constant or #define, TREASURY_WALL_CELL_COLUMN since 2026-11-25),
# with + - * and brackets.
ARITHMETIC = re.compile(r"[\d\s+\-*()]+")
# A top-level definition: a function, or data with an initializer.
DEFINITION = re.compile(r"^(?!static\s+inline\b)[A-Za-z_][\w \t\*]*?\b(\w+)\s*(\([^;{}]*\)|\[[^\]]*\])?\s*(?:=\s*)?\{", re.M)
IDENTIFIER = re.compile(r"\b[A-Za-z_]\w*\b")
INLINE = re.compile(r"^static\s+inline\b[^;{]*?\b(\w+)\s*\([^;{}]*\)\s*\{", re.M)
ROOM_KINDS = ("events", "placements")
# Copy the picture as well (CopyCellPictureCellsRect is CopyCellTilesCellsRect since 2026-11-25).
WHOLE = {"CopyCells", "CopyCellPictureCellsRect", "CopyCellTilesCellsRect"}


def _definitions(text):
    """{name: body text} of a source's top-level functions and initialized data."""
    out = {}
    for pattern in (DEFINITION, INLINE):
        for m in pattern.finditer(text):
            start = m.end() - 1
            try:
                end = _matching(text, start, "{", "}")
            except ValueError:
                continue
            out.setdefault(m.group(1), text[start:end])
    return out


def _prune(body, scene_name):
    """The body with the branches a room never takes cut out: an `if` decided
    by which room is playing keeps only its taken side."""
    out, pos = [], 0
    for m in re.finditer(r"\bif\s*\(", body):
        if m.start() < pos:
            continue
        open_paren = m.end() - 1
        try:
            close = _matching(body, open_paren, "(", ")")
        except ValueError:
            break
        verdict = _decide(body[open_paren + 1:close - 1], scene_name)
        if verdict is None:
            continue
        then_start, then_end = _statement_span(body, close)
        else_span = None
        after = then_end
        while after < len(body) and body[after] in " \t\r\n":
            after += 1
        if body.startswith("else", after) and not re.match(r"\w", body[after + 4:after + 5]):
            else_span = _statement_span(body, after + 4)
        out.append(body[pos:m.start()])
        if verdict:
            out.append(_prune(body[then_start:then_end], scene_name))
        elif else_span:
            out.append(_prune(body[else_span[0]:else_span[1]], scene_name))
        pos = else_span[1] if else_span else then_end
    out.append(body[pos:])
    return "".join(out)


def _statement_span(text, pos):
    """(start, end) of the statement starting at or after pos."""
    while pos < len(text) and text[pos] in " \t\r\n":
        pos += 1
    if pos < len(text) and text[pos] == "{":
        return pos, _matching(text, pos, "{", "}")
    if re.match(r"if\s*\(", text[pos:]):
        close = _matching(text, text.index("(", pos), "(", ")")
        _, end = _statement_span(text, close)
        after = end
        while after < len(text) and text[after] in " \t\r\n":
            after += 1
        if text.startswith("else", after) and not re.match(r"\w", text[after + 4:after + 5]):
            _, end = _statement_span(text, after + 4)
        return pos, end
    return pos, text.index(";", pos) + 1


def room_changes(tbs, overlay, scene_name):
    """[(sourceX, sourceY, width, height, toX, toY, whole)] of the cell copies
    the room's code can make, in the order its source has them (grid cells);
    whole: the picture is copied too."""
    key = ("cell changes", tbs, scene_name, sources_generation(tbs))
    if key in overlay.memo:
        return overlay.memo[key]
    macros = _scene_macros(tbs)

    def scene_ids(text):
        return re.sub(r"\bSCENE_\w+\b", lambda m: f"(s32)&SceneId_{macros[m.group(0)]}"
                      if m.group(0) in macros else m.group(0), text)

    # The overlay's definitions are the same for every room it serves.
    defs_key = ("definitions", tbs, sources_generation(tbs))
    defs = overlay.memo.get(defs_key)
    if defs is None:
        defs = {}
        for path in _scene_files(tbs, overlay.tables):
            defs.update(_definitions(scene_ids(_strip_comments(_source_text(path)))))
        overlay.memo[defs_key] = defs
    roots = []
    for kind in ROOM_KINDS:
        found = scene_tables(tbs, overlay, kind, scene_name)
        roots += found if found is not None else [n for n, t in overlay.tables.items() if t["kind"] == kind]
    start = overlay.getter_name("initialize")
    if start:
        roots.append(start)
    seen, order, queue = set(), [], [r for r in roots if r in defs]
    seen.update(queue)
    while queue:
        name = queue.pop(0)
        body = _prune(defs[name], scene_name or "")
        order.append((name, body))
        for word in IDENTIFIER.findall(body):
            if word in defs and word not in seen:
                seen.add(word)
                queue.append(word)
    numbers_key = ("named numbers", tbs, sources_generation(tbs))
    numbers = overlay.memo.get(numbers_key)
    if numbers is None:
        numbers = overlay.memo[numbers_key] = _numbers(tbs, overlay)
    changes = []
    for _, body in order:
        for m in COPY.finditer(body):
            args = [_value(a, numbers) for a in _split_arguments(_expand(m.group(2), numbers))]
            if len(args) == 6 and None not in args:
                changes.append((*args, m.group(1) in WHOLE))
    changes = _through_saves(changes)
    overlay.memo[key] = changes
    return changes


def _numbers(tbs, overlay):
    """{NAME: value} of the enum constants and #defines in the overlay's
    sources and the headers next to them that they include."""
    import os
    from .doors import _named_numbers
    text = []
    for path in _scene_files(tbs, overlay.tables):
        source = _source_text(path)
        text.append(source)
        for inc in re.findall(r'^#include "([^"]+)"', source, re.M):
            header = os.path.join(os.path.dirname(path), inc)
            if os.path.exists(header):
                with open(header, encoding="utf-8") as f:
                    text.append(f.read())
    joined = "\n".join(text)
    numbers = _named_numbers(joined)
    # Object-like macros spelling out part of an argument list: `#define VINE_CELL 31, 0`.
    for name, body in re.findall(r"^#define\s+(\w+)[ \t]+([^\n]*?)\s*(?://[^\n]*)?$", joined, re.M):
        if name not in numbers and "," in body and re.fullmatch(r"[\w\s,+\-*()]+", body):
            numbers[name] = MacroText(body)
    return numbers


class MacroText(str):
    """A macro's text, put in place before a call's arguments are split."""


def _expand(text, numbers):
    for _ in range(4):  # macros naming macros
        new = re.sub(r"\b[A-Za-z_]\w*\b",
                     lambda m: numbers[m.group(0)] if isinstance(numbers.get(m.group(0)), MacroText) else m.group(0), text)
        if new == text:
            break
        text = new
    return text


def _split_arguments(text):
    """A call's arguments, split at the commas outside brackets."""
    out, depth, start = [], 0, 0
    for i, c in enumerate(text):
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == "," and depth == 0:
            out.append(text[start:i])
            start = i + 1
    out.append(text[start:])
    return out


def _value(argument, numbers):
    """An argument as a number, or None when it is worked out while playing."""
    text = re.sub(r"\b[A-Za-z_]\w*\b", lambda m: str(numbers[m.group(0)]) if isinstance(numbers.get(m.group(0)), int) else "?",
                  " ".join(argument.split()))
    if not ARITHMETIC.fullmatch(text) or not text.strip():
        return None
    try:
        return int(eval(text, {"__builtins__": {}}, {}))  # noqa: S307  digits and + - * ( ) only
    except (SyntaxError, ZeroDivisionError, TypeError):
        return None


def _through_saves(changes):
    """Copies read from a spare part of the map another copy saved cells to
    read those cells instead. Rooms save part of themselves off to the side
    and copy it back later; the walking check reads every source from the
    map as saved, where the spare part is still blank, so restoring would
    otherwise open what it closes."""
    saved = {(c[4], c[5], c[2], c[3]): c for c in changes}  # destination rect -> the copy filling it
    out = []
    for c in changes:
        sx, sy, w, h, dx, dy, whole = c
        filler = saved.get((sx, sy, w, h))
        if filler is not None and filler is not c:
            sx, sy = filler[0], filler[1]
        out.append((sx, sy, w, h, dx, dy, whole))
    return out
