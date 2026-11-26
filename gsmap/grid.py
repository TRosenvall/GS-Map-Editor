"""Read and write a map's grid without changing a byte, in either of
alchemy's layouts.

Since 2026-11-25 a grid is four tables beside each other in the map's folder
(grid_picture.tsv, grid_behavior.tsv, grid_shape.tsv, grid_actors.tsv; an
edition's own grid adds its suffix, grid_picture_es.tsv), read by TableGrid
below. Each of the first three is a header of column numbers and 128 rows of
128 decimal values. grid_actors.tsv lists only the cells whose block word has
its top nibble set: `column row layer priority`, the layer marker being bits
12-13 and the priority bits 14-15 (field/map_grid.c).

Before that it was one text file, map.txt (header, then one text row per grid row):

    grid:128x128	at:0,0	fill:1c:0:0
    fff fff:30:1 4fff:255 1c ...

A cell is `picture:behavior:shape`, a field left off the end being 0. The
picture is lowercase hex without a prefix, its top nibble the priority and
layer flags; behavior (the collision code) and shape are decimal. Each row
stops at its last non-fill cell, and trailing all-fill rows are left out.
`at:x,y` is where the first written row and column sit in the grid.

The rest of the editor works on one plane at a time ("metatile" for the
picture, "collision" for the behavior, "shape"), so MapGrid hands those out
as lists sharing its own cells.
"""

import os
import re

from .fsio import atomic_write
from .i18n import tr

HEADER = re.compile(r"^grid:(\d+)x(\d+)\tat:(\d+),(\d+)\tfill:([0-9a-f]+)(?::(\d+))?(?::(\d+))?$")
PLANES = ("metatile", "collision", "shape")


class Plane:
    """One plane of a grid: its rows and the largest value a cell can hold."""

    def __init__(self, cells, max_value):
        self.cells = cells
        self.max_value = max_value

    def get(self, x, y):
        return self.cells[y][x]

    def set(self, x, y, value):
        if not 0 <= value <= self.max_value:
            raise ValueError(tr("{value} does not fit this plane", value=f"{value:#x}"))
        self.cells[y][x] = value


def _cell(token):
    parts = token.split(":")
    return (int(parts[0], 16), int(parts[1]) if len(parts) > 1 else 0, int(parts[2]) if len(parts) > 2 else 0)


def _format(picture, behavior, shape):
    if shape:
        return f"{picture:x}:{behavior}:{shape}"
    if behavior:
        return f"{picture:x}:{behavior}"
    return f"{picture:x}"


class MapGrid:
    def __init__(self, width, height, fill, at_x=0, at_y=0):
        self.width, self.height, self.fill, self.at_x, self.at_y = width, height, fill, at_x, at_y
        self.planes = {name: [[fill[i]] * width for _ in range(height)] for i, name in enumerate(PLANES)}

    def plane(self, name):
        return Plane(self.planes[name], 0xFFFF if name == "metatile" else 0xFF)

    def to_text(self):
        pictures, behaviors, shapes = (self.planes[n] for n in PLANES)
        lines = [f"grid:{self.width}x{self.height}\tat:{self.at_x},{self.at_y}"
                 f"\tfill:{self.fill[0]:x}:{self.fill[1]}:{self.fill[2]}"]
        rows = []
        for y in range(self.at_y, self.height):
            cells = list(zip(pictures[y], behaviors[y], shapes[y]))[self.at_x:]
            end = len(cells)
            while end and cells[end - 1] == self.fill:
                end -= 1
            rows.append(" ".join(_format(*c) for c in cells[:end]))
        while rows and rows[-1] == "":
            rows.pop()
        return "\n".join(lines + rows) + "\n"


def is_grid_text(text):
    return HEADER.match(text.split("\n", 1)[0]) is not None


def parse(text):
    first, _, body = text.partition("\n")
    m = HEADER.match(first)
    if not m:
        raise ValueError(f"not a grid file header: {first!r}")
    w, h, ax, ay = (int(v) for v in m.groups()[:4])
    fill = (int(m.group(5), 16), int(m.group(6) or 0), int(m.group(7) or 0))
    g = MapGrid(w, h, fill, ax, ay)
    pictures, behaviors, shapes = (g.planes[n] for n in PLANES)
    rows = body.split("\n")
    if rows and rows[-1] == "":
        rows.pop()
    if ay + len(rows) > h:
        raise ValueError(f"grid has {len(rows)} rows, more than its {h}")
    seen = {}  # a map uses few distinct cells: each is read once
    for i, row in enumerate(rows):
        y = ay + i
        tokens = row.split()
        n = len(tokens)
        if ax + n > w:
            raise ValueError(f"grid row {i} has {n} cells, more than its {w}")
        if not n:
            continue
        cells = []
        for token in tokens:
            c = seen.get(token)
            if c is None:
                c = seen[token] = _cell(token)
            cells.append(c)
        pictures[y][ax:ax + n], behaviors[y][ax:ax + n], shapes[y][ax:ax + n] = zip(*cells)
    return g


def load(path):
    if is_table_grid(path):
        return load_tables(path)
    with open(path, encoding="utf-8") as f:
        return parse(f.read())


def save(grid, path):
    if isinstance(grid, TableGrid):
        return save_tables(grid)
    atomic_write(path, grid.to_text())
    return [path]


# ---- the table layout (since 2026-11-25) -----------------------------------

TABLE_PLANES = (("metatile", "grid_picture"), ("collision", "grid_behavior"), ("shape", "grid_shape"))
ACTORS = "grid_actors"
ACTORS_HEADER = "column\trow\tlayer\tpriority"


def is_table_grid(path):
    """Whether this grid path is the picture table of the table layout."""
    return os.path.basename(path).startswith("grid_picture")


def table_paths(picture_path):
    """{name: path} of the four tables of the grid whose picture table this is."""
    folder, name = os.path.split(picture_path)
    suffix = name[len("grid_picture"):]  # ".tsv", "_es.tsv"
    return {stem: os.path.join(folder, stem + suffix) for stem in ("grid_picture", "grid_behavior", "grid_shape", ACTORS)}


def parse_plane(text):
    """One 128x128 plane table: its rows of ints, header dropped."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    rows = [[int(v) for v in line.split("\t")] for line in lines[1:]]
    if len(rows) != 128 or any(len(r) != 128 for r in rows):
        raise ValueError(f"a grid table should be 128 rows of 128 values, not {len(rows)}")
    return rows


def _plane_text(rows):
    return "\t".join(str(i) for i in range(128)) + "\n" + "".join("\t".join(map(str, r)) + "\n" for r in rows)


class TableGrid:
    """A grid in the table layout, its planes shaped as MapGrid's: the
    "metatile" plane holds the whole block word, the actors' bits included."""

    def __init__(self, paths, planes, texts):
        self.paths = paths
        self.planes = planes
        self._texts = texts  # the files as read: a table left alone is not rewritten

    def plane(self, name):
        return Plane(self.planes[name], 0xFFFF if name == "metatile" else 0xFF)

    def to_files(self):
        """{path: text} of every table, as the planes now stand."""
        words = self.planes["metatile"]
        out = {}
        for name, stem in TABLE_PLANES:
            rows = [[w & 0xFFF for w in r] for r in words] if name == "metatile" else self.planes[name]
            out[self.paths[stem]] = _plane_text(rows)
        actors = [f"{x}\t{y}\t{(w >> 12) & 3}\t{w >> 14}" for y, r in enumerate(words) for x, w in enumerate(r) if w >> 12]
        if actors or self._texts.get(self.paths[ACTORS]) is not None:
            out[self.paths[ACTORS]] = "\n".join([ACTORS_HEADER] + actors) + "\n"
        return out


def load_tables(picture_path):
    paths = table_paths(picture_path)
    texts = {}
    for path in paths.values():
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                texts[path] = f.read()
    return parse_tables(paths, texts)


def parse_tables(paths, texts):
    """A TableGrid from its files' texts ({path: text}; the actors' may be missing)."""
    planes = {name: parse_plane(texts[paths[stem]]) for name, stem in TABLE_PLANES}
    words = planes["metatile"]
    actors = texts.get(paths[ACTORS])
    if actors is not None:
        lines = [line for line in actors.split("\n")[1:] if line]
        for line in lines:
            x, y, layer, priority = (int(v) for v in line.split("\t")[:4])
            words[y][x] |= (layer << 12) | (priority << 14)
    return TableGrid(paths, planes, texts)


def save_tables(grid):
    """Write the tables that changed; their paths."""
    written = []
    for path, text in grid.to_files().items():
        if grid._texts.get(path) != text:
            atomic_write(path, text)
            grid._texts[path] = text
            written.append(path)
    return written

