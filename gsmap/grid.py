"""Read and write a map's grid (map.txt) without changing a byte.

Format (header, then one text row per grid row):

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
    for i, row in enumerate(rows):
        y = ay + i
        tokens = row.split()
        if ax + len(tokens) > w:
            raise ValueError(f"grid row {i} has {len(tokens)} cells, more than its {w}")
        for j, token in enumerate(tokens):
            x = ax + j
            pictures[y][x], behaviors[y][x], shapes[y][x] = _cell(token)
    return g


def load(path):
    with open(path, encoding="utf-8") as f:
        return parse(f.read())


def save(grid, path):
    atomic_write(path, grid.to_text())
