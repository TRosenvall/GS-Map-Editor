"""A map's files as alchemy kept them up to 0240eeebad, in the table files it
keeps them in since.

Before: map.inc (map.s before 2026-11-17) holds the header, the three layers
and the chests (`treasure_spot` rows); map.txt (map_<lang>.txt for an edition
of its own) the grid; cell_pictures.tsv a tile word per corner of each cell;
shapes.tsv typed columns.

After: header.tsv, layers.tsv and spots.tsv; grid_picture, grid_behavior and
grid_shape (<name>_<lang>.tsv for an edition), and grid_actors for the cells
whose picture had a layer marker or priority in its top nibble; cell_tiles.tsv
with each corner's tile, flip and palette apart; shapes.tsv untyped. ags-maps
and ags-graphics build the game's data from them.

Converting every stock map of 0240eeebad this way gives 9bf56b6993's files
byte for byte. tools/port_mod.py and gsmap/update.py use it to carry a mod's
changes across.
"""

import re

from . import grid as gridmod

FLIPS = {0: "", 1: "h", 2: "v", 3: "hv"}
CORNERS = ("top_left", "top_right", "bottom_left", "bottom_right")
HEADER_COLUMNS = ("left\ttop\tright\tbottom\tpriority0\tpriority1\tpriority2\tchars0\tchars1\tchars2\tpad0\tpad1"
                  "\tedition")
LAYER_COLUMNS = "x\ty\trate_x\trate_y\tdrift_x\tdrift_y\ta\tb\tedition"
SPOT_COLUMNS = "column\trow\tsubject\tedition"
OLD_GRID = re.compile(r"^map(_[a-z]{2})?\.txt$")  # map.txt, map_es.txt
OLD_FILES = ("cell_pictures.tsv", "shapes.tsv", "map.inc", "map.s")
EDITIONS = ("ja", "en", "de", "es", "fr", "it")


def is_old_file(name):
    """A file name the old layout keeps a map in, which the new one doesn't."""
    return bool(OLD_GRID.match(name)) or name in OLD_FILES


def grid_tables(text, suffix=""):
    """map.txt -> {table file name: text}: grid_picture, grid_behavior,
    grid_shape and, where any cell has one, grid_actors. The picture keeps its
    low twelve bits; of its top nibble, the low two bits are the layer marker
    and the high two the drawing priority, listed by cell."""
    g = gridmod.parse(text)
    pic, beh, shape = (g.plane(p) for p in gridmod.PLANES)
    head = "\t".join(str(x) for x in range(g.width)) + "\n"

    def plane(value):
        return head + "".join("\t".join(str(value(x, y)) for x in range(g.width)) + "\n" for y in range(g.height))

    tables = {f"grid_picture{suffix}.tsv": plane(lambda x, y: pic.get(x, y) & 0xFFF),
              f"grid_behavior{suffix}.tsv": plane(beh.get),
              f"grid_shape{suffix}.tsv": plane(shape.get)}
    actors = "".join(f"{x}\t{y}\t{pic.get(x, y) >> 12 & 3}\t{pic.get(x, y) >> 14}\n"
                     for y in range(g.height) for x in range(g.width) if pic.get(x, y) >> 12)
    # A map with no such cell has no file: ags-graphics wants a row.
    tables[f"grid_actors{suffix}.tsv"] = "column\trow\tlayer\tpriority\n" + actors if actors else None
    return tables


def cell_tiles(text):
    """cell_pictures.tsv -> cell_tiles.tsv."""
    out = ["\t".join(f"{c}\t{c}_flip\t{c}_palette" for c in CORNERS)]
    for line in text.strip("\n").split("\n")[1:]:
        words = [int(w, 0) for w in line.split("\t")]
        out.append("\t".join(f"{w & 0x3FF}\t{FLIPS[w >> 10 & 3]}\t{w >> 12}" for w in words))
    return "\n".join(out) + "\n"


def shapes(text):
    """shapes.tsv, its columns' types dropped."""
    head, _, body = text.partition("\n")
    return re.sub(r":\w+", "", head) + "\n" + body


def edition_lines(text, edition):
    """The lines of an old map file one edition assembles: its .ifdef
    TBS_EDITION_<LANG> and .ifeq EDITION_INTERNATIONAL (Japanese) blocks."""
    out, stack = [], []
    for line in text.split("\n"):
        s = line.strip()
        m = re.match(r"\.(ifdef|ifndef)\s+TBS_EDITION_(\w+)", s)
        n = re.match(r"\.(ifeq|ifne)\s+EDITION_INTERNATIONAL\b", s)
        if m or n:
            cond = ((m.group(2).lower() == edition) == (m.group(1) == "ifdef") if m
                    else (edition == "ja") == (n.group(1) == "ifeq"))
            stack.append([cond, cond])
        elif re.match(r"\.if", s):
            raise ValueError(s)  # nothing else conditional is expected in a map file
        elif s == ".else":
            stack[-1][0] = not stack[-1][1]
        elif s == ".endif":
            stack.pop()
        elif all(level[0] for level in stack):
            out.append(s)
    return out


def map_file(text):
    """map.inc -> {edition: (header, layers, spots)}: the header's twelve
    numbers, each layer's eight, and each chest's column, row and subject."""
    def numbers(line):
        return [int(v, 0) for v in line.split(None, 1)[1].split(",")]
    out = {}
    for edition in EDITIONS:
        lines = edition_lines(text, edition)
        header = next((numbers(line) for line in lines if line.startswith("map_header ")), None)
        layers = [numbers(line) for line in lines if line.startswith("map_layer ")][:3]
        spots = [numbers(line) for line in lines if line.startswith("treasure_spot ")]
        out[edition] = (header, layers, spots)
    return out


def header_table(header):
    return HEADER_COLUMNS + "\n" + "\t".join(map(str, header)) + "\n"


def layers_table(layers):
    return LAYER_COLUMNS + "\n" + "".join("\t".join(map(str, layer)) + "\n" for layer in layers)


def spots_table(by_edition):
    """spots.tsv for {edition: chests}: plain rows when every edition has the
    same, else each edition's rows marked with it, in its own order. None for
    none (the file is only where a map has any)."""
    lists = [by_edition[e] for e in EDITIONS]
    if not any(lists):
        return None
    if all(rows == lists[0] for rows in lists):
        body = "".join("\t".join(map(str, s)) + "\n" for s in lists[0])
    else:
        body = "".join("\t".join(map(str, s)) + f"\t{e}\n" for e in EDITIONS for s in by_edition[e])
    return SPOT_COLUMNS + "\n" + body


def read_spots(text):
    """spots.tsv -> {edition: [[column, row, subject], ...]}: each edition's
    chests, its own rows and the plain ones, in file order."""
    out = {e: [] for e in EDITIONS}
    for line in (text or "").strip("\n").split("\n")[1:]:
        if not line:
            continue
        cells = line.split("\t")
        row, only = [int(v) for v in cells[:3]], cells[3] if len(cells) > 3 and cells[3] else None
        for e in EDITIONS:
            if only in (None, e):
                out[e].append(row)
    return out


def convert(name, text):
    """{new file name: text, or None for no file} for one old file's text."""
    m = OLD_GRID.match(name)
    if m:
        return grid_tables(text, m.group(1) or "")
    if name == "cell_pictures.tsv":
        return {"cell_tiles.tsv": cell_tiles(text)}
    if name == "shapes.tsv":
        return {"shapes.tsv": shapes(text)}
    parsed = map_file(text)
    first = parsed[EDITIONS[0]]
    if first[0] is None or any(parsed[e][:2] != first[:2] for e in EDITIONS):
        raise ValueError(name)  # a header or layers that differ by edition: not carried
    return {"header.tsv": header_table(first[0]), "layers.tsv": layers_table(first[1]),
            "spots.tsv": spots_table({e: parsed[e][2] for e in EDITIONS})}
