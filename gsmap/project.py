"""The Broken Seal's field maps as alchemy stores them.

Facts this relies on, each checked against alchemy's engine source or by
rendering (see README.md):

- A map is games/tbs/src/map/<dir>/map.s plus its tables: map.txt (the grid),
  cell_pictures.tsv, shapes.tsv; the chests are `treasure_spot` lines inside
  map.s. Its header gives the map bounds and the layer origins in 8 px tile units, three BG priorities
  (0 = layer off) and three BG char bases (16 KiB blocks).
- Each layer's cells start at (x/2, y/2) in the 128x128 cell grid.
- A cell's low 12 bits pick a block (a cell picture). 0xfff marks the map's next
  unique block: at load the k-th 0xfff cell, row-major over the whole
  128x128 grid, becomes block k with its top nibble kept
  (field/map_grid_convert.s). The placeholder count always
  equals the number of rows in cell_pictures.tsv.
- A cell picture is 2x2 GBA text-BG entries: tile 10 bits, hflip 0x400,
  vflip 0x800, palette in the top 4 bits.
- Absolute tile = char_base*512 + (entry & 0x3ff); char block 1..3 hold the
  three tile sheets the map's gMaps row names; block 0 is window tiles.
- map/maps.c (gMaps) gives each map's resources as positions in the
  expanded resource directory counted from Field_Map001: header, palette,
  char blocks 1-3, and sheet D (tile animation source).
- Layer windows wrap at 128 cells.
"""

import glob
import os
import re

from PIL import Image

from . import layout
from .fsio import atomic_write
from .i18n import tr
from . import grid as gridmod
from . import table as tablemod

EDITION = "TBS_EDITION_EN"
EMPTY = 0xFFF
# Every value a cell holding a placeholder can have (cells are 16 bits): a
# quick test of whether a grid row holds any.
_PLACEHOLDERS = frozenset((top << 12) | EMPTY for top in range(16))


INTERNATIONAL = 1  # EDITION_INTERNATIONAL for the English edition


def resolve_asset(games_root, path):
    """Absolute path of an .incbin or grid-index path, in any of alchemy's
    conventions: repository-relative ("games/tbs/src/map/..."), the older
    shared folder ("common/map/..."), or relative to the game's src."""
    if path.startswith("games/"):
        return os.path.join(os.path.dirname(games_root), path)
    if path.startswith("common/"):
        return os.path.join(games_root, "common/src", path[len("common/"):])
    return os.path.join(games_root, "tbs/src", path)


def _kept_lines(text, defined):
    """(line number, line) of the lines of an assembly file `defined` selects.

    Understands .ifdef/.ifndef on edition symbols and .ifeq/.ifne on
    EDITION_INTERNATIONAL; any other .if (e.g. inside a macro body) keeps
    both branches, which is harmless because macro bodies are not parsed.
    """
    out, stack = [], []
    for number, line in enumerate(text.split("\n")):
        s = line.strip()
        m = re.match(r"\.(ifdef|ifndef)\s+(\w+)", s)
        if m:
            cond = (m.group(2) in defined) == (m.group(1) == "ifdef")
            stack.append([cond, cond, True])
            continue
        m = re.match(r"\.(ifeq|ifne)\s+EDITION_INTERNATIONAL\b", s)
        if m:
            cond = (INTERNATIONAL == 0) == (m.group(1) == "ifeq")
            stack.append([cond, cond, True])
            continue
        if re.match(r"\.if\w*\b", s):
            stack.append([True, True, False])
            continue
        if s == ".else":
            top = stack[-1]
            if top[2]:
                top[0] = not top[1]
            continue
        if s == ".endif":
            stack.pop()
            continue
        if all(t[0] for t in stack):
            out.append((number, line))
    return out


_KEPT = {}  # map.s path -> ((mtime, size), its English edition's lines); a map is opened often


def _kept_file_lines(path):
    """_kept_lines of a file for the English edition, read again only when the
    file changes. Shared: treat the list as read-only."""
    st = os.stat(path)
    stamp = (st.st_mtime_ns, st.st_size)
    hit = _KEPT.get(path)
    if hit is None or hit[0] != stamp:
        with open(path, encoding="utf-8") as f:
            hit = _KEPT[path] = (stamp, _kept_lines(f.read(), {EDITION}))
    return hit[1]


def _preprocess(text, defined):
    return "\n".join(line for _, line in _kept_lines(text, defined))


class DirectoryError(Exception):
    """The resource directory isn't laid out as expected (see gsmap/preflight.py)."""


class Markers:
    """A map's chests and Psynergy stones: the `treasure_spot` lines of its
    map.s, in the English edition's branch. Rows are [x, z, code], the last
    being the 0xff end row, so they read like a table; save() rewrites only
    those lines, leaving other editions' branches alone."""

    END = [0xFF, 0xFF, 0xFF]

    def __init__(self, path):
        self.path = path
        lines = self._lines()
        self.rows = [[int(v, 0) for v in line.split(None, 1)[1].split(",")]
                     for _, line in lines if line.strip().startswith("treasure_spot ")]
        self.rows.append(list(self.END))

    def _lines(self):
        """The list's lines, label excluded, end line included."""
        kept = _kept_file_lines(self.path)
        start = next(i for i, (_, line) in enumerate(kept) if re.match(r"\.LField_\w*_MARKERS:", line.strip()))
        out = []
        for number, line in kept[start + 1:]:
            out.append((number, line))
            if line.strip() == "treasure_spots_end":
                return out
        raise ValueError(f"{self.path}: no treasure_spots_end after the markers label")

    def set(self, row, col, value):
        self.rows[row][col] = value

    def insert(self, index, values):
        self.rows.insert(index, list(values))

    def delete(self, index):
        del self.rows[index]

    def save(self):
        text = open(self.path, encoding="utf-8").read().split("\n")
        numbers = [number for number, _ in self._lines()]
        new = [f"\ttreasure_spot {x}, {z}, {code}" for x, z, code in self.rows if [x, z, code] != self.END]
        new.append("\ttreasure_spots_end")
        text[numbers[0]:numbers[-1] + 1] = new
        atomic_write(self.path, "\n".join(text))


class MapInfo:
    def __init__(self, number, folder, map_s, games_root):
        self.number = number  # "009"
        self.folder = folder  # absolute path of map dir
        self.games_root = games_root
        text = _preprocess(map_s, {EDITION})
        # A table may come from another map's folder:
        # `.LField_Map172_GRID:` then `.incbin "games/tbs/src/map/map_001/map.grid.lz"`.
        self.sources = {}
        for kind, path in re.findall(
            r"^\.LField_\w*?_(CELL_PICTURES|SHAPES|GRID|ANIMATION|BLEND):\s*\n\s*\.incbin\s+\"([^\"]+)\"", text, re.M
        ):
            full = resolve_asset(games_root, path)
            stem = os.path.basename(full).split(".")[0]
            self.sources[kind] = os.path.join(os.path.dirname(full), stem + (".txt" if kind == "GRID" else ".tsv"))
        h = re.search(r"map_header ([^\n]+)", text)
        vals = [int(v, 0) for v in h.group(1).split(",")]
        self.bounds = vals[0:4]  # left, top, right, bottom (tile units)
        self.priority = vals[4:7]
        self.char_base = vals[7:10]
        self.layers = [
            [int(v, 0) for v in m.split(",")]
            for m in re.findall(r"map_layer ([^\n]+)", text)
        ][:3]
        self.tileset = None  # display name of the char block 1 tile set
        self.palette = None  # display name when a recolour palette is used
        self.resources = None  # from map/maps.c, see Project._read_directory
        self.alternates = []  # further gMaps rows naming this map

    @property
    def size(self):
        """Visible size in metatiles (16 px)."""
        left, top, right, bottom = self.bounds
        return (right - left) // 2, (bottom - top) // 2

    def source(self, kind, default_name):
        """Source file of a table (CELL_PICTURES, SHAPES, GRID, ...)."""
        return self.sources.get(kind, os.path.join(self.folder, default_name))

    def grid_path(self):
        """The grid file (map.txt, possibly in another map's folder)."""
        return self.source("GRID", "map.txt")


class Project:
    def __init__(self, root):
        self.root = root
        if not os.path.exists(os.path.join(root, layout.MAP_TABLE)):
            raise SystemExit(f"{root} isn't a version of alchemy this editor can read (no {layout.MAP_TABLE}).")
        self.tbs = os.path.join(root, layout.SRC)
        self.maps = {}
        self.symbols = {}  # Tileset_* label -> source PNG path
        self._scan_maps()
        self._scan_symbols()
        self._read_directory()
        self._sheet_cache = {}
        self._parse_cache = {}

    def reload(self):
        """Read the maps again: files changed in a way cached headers don't see."""
        self.maps = {}
        self.symbols = {}
        self._scan_maps()
        self._scan_symbols()
        self._read_directory()
        self._sheet_cache.clear()
        self._parse_cache.clear()

    # ---- discovery -------------------------------------------------------

    def _scan_maps(self):
        for path in sorted(glob.glob(os.path.join(self.root, layout.MAPS, "*/map.s"))):
            text = open(path, encoding="utf-8").read()
            # Numbered maps are Field_Map009; a few are named (Field_VinasuIriguchi).
            m = re.search(r"^Field_(?:Map(\d+)|(\w+)):", text, re.M)
            if m and "map_header" in text:
                key = m.group(1) or m.group(2)
                self.maps[key] = MapInfo(
                    key, os.path.dirname(path), text, os.path.join(self.root, "games")
                )

    def _scan_symbols(self):
        """Map every Tileset_* label to the PNG its .incbin is built from.

        Names do not always match folders: a set's label can be built from
        another set's sheet.
        """
        games = os.path.join(self.root, "games")
        files = glob.glob(os.path.join(self.tbs, "**/*.s"), recursive=True)
        files += glob.glob(os.path.join(self.tbs, "**/*.S"), recursive=True)
        for path in files:
            text = open(path, encoding="utf-8", errors="replace").read()
            if "Tileset_" not in text:
                continue
            text = _preprocess(text, {EDITION})
            for label, inc in re.findall(
                r"^(Tileset_\w+):\s*\n\s*\.incbin\s+\"([^\"]+)\"", text, re.M
            ):
                full = resolve_asset(games, inc)
                stem = os.path.basename(full).split(".")[0]
                self.symbols[label] = os.path.join(os.path.dirname(full), stem + ".png")

    def directory_entries(self):
        """The resource directory as an ordered list of labels, macros expanded."""
        path = os.path.join(self.root, layout.DIRECTORY)
        text = _preprocess(open(path, encoding="utf-8").read(), {EDITION})
        text = text.split(layout.DIRECTORY_LABEL, 1)[1]
        out = []
        for line in text.split("\n"):
            s = line.split("@")[0].strip()
            if not s or s.startswith("."):
                continue
            m = re.match(r"resource\s+(\w*)\s*,\s*(\S+)", s)
            if m:
                out.append(m.group(2))
                continue
            m = re.match(r"group\s+(\w+)\s*,\s*(.+)", s)
            if m:
                out += [f"{m.group(1)}_{n}" for n in re.findall(r"\w+", m.group(2))]
                continue
            m = re.match(r"tileset\s+(\w+)\s*,\s*([A-D-]+)\s*,\s*(.+)", s)
            if m:
                out += [f"Field_Map{n}" for n in re.findall(r"\w+", m.group(3))]
                out.append(f"Tileset_{m.group(1)}Palette")
                if m.group(2) != "-":
                    out += [f"Tileset_{m.group(1)}Tiles{c}" for c in m.group(2)]
                continue
            m = re.match(r"recolor\s+(\w+)\s*,\s*(.+)", s)
            if m:
                out += [f"Field_Map{n}" for n in re.findall(r"\w+", m.group(2))]
                out.append(f"Tileset_Palette{m.group(1)}")
                continue
            m = re.match(r"overlays\s+(.+)", s)
            if m:
                out += [f"Resource_Overlay{n}" for n in re.findall(r"\w+", m.group(1))]
                continue
            m = re.match(r"unused\s+(\w+)", s)
            if m:
                out += [None] * int(m.group(1), 0)
                continue
            if re.fullmatch(r"\w+:", s):  # the next label: the table is over
                break
            # Skipping a line would move every entry after it, and maps would
            # silently draw the wrong tiles.
            raise DirectoryError(tr("The resource directory has a line the editor doesn't understand: {line}. "
                                    "It would misplace every map's art after that point.", line=repr(s)))
        return out

    def maps_path(self):
        return os.path.join(self.root, layout.MAP_TABLE)

    def map_rows(self):
        """gMaps, as lists of six directory positions."""
        with open(self.maps_path(), encoding="utf-8") as f:
            return self.parse_map_rows(f.read())

    @staticmethod
    def parse_map_rows(text):
        return [[int(v, 0) for v in row.split(",")] for row in re.findall(r"\{\{([^{}]+)\}\}", text)]

    def _read_directory(self):
        """Give each map its palette, char blocks 1-3 and sheet D from
        gMaps in map/maps.c (positions in the directory from Field_Map001)."""
        entries = self.directory_entries()
        base = entries.index(layout.FIRST_MAP_ENTRY)
        for row, values in enumerate(self.map_rows()):
            labels = [entries[base + v] for v in values]
            m = re.fullmatch(r"Field_(?:Map(\d+)|(\w+))", labels[0] or "")
            key = m and (m.group(1) or m.group(2))
            info = self.maps.get(key)
            if info is None:
                continue
            res = {
                "row": row,
                "palette": labels[1],
                "blocks": labels[2:5],
                "sheet_d": labels[5],
            }
            if info.resources is None:
                info.resources = res
            else:
                info.alternates.append(res)
        for info in self.maps.values():
            r = info.resources
            if r is None:
                continue
            setm = re.match(r"Tileset_(\w+?)Tiles[A-D]$", r["blocks"][0] or "")
            info.tileset = setm.group(1) if setm else r["blocks"][0]
            palm = re.match(r"Tileset_Palette(\w+)$", r["palette"] or "")
            info.palette = palm.group(1) if palm else None

    # ---- assets ----------------------------------------------------------

    def label_path(self, label):
        """Source PNG of a Tileset_* directory label, or None."""
        p = self.symbols.get(label or "")
        return p if p and os.path.exists(p) else None

    def palette_path(self, info):
        p = self.label_path(info.resources and info.resources["palette"])
        if p is None:
            raise FileNotFoundError(f"no palette for map {info.number}")
        return p

    def palette_rows(self, info):
        img = Image.open(self.palette_path(info)).convert("RGB")
        return [[img.getpixel((x, y)) for x in range(16)] for y in range(img.height)]

    def _parsed(self, path, parse, key=None):
        """A parsed file, kept until it changes. Shared: treat it as read-only.
        `key` tells apart several things worked out from one file; they're
        dropped with it (_parse_cache.pop(path) after a save)."""
        st = os.stat(path)
        stamp = (st.st_mtime_ns, st.st_size)
        hit = self._parse_cache.get(path)
        if hit is None or hit[0] != stamp:
            hit = self._parse_cache[path] = (stamp, {})
        made = hit[1]
        if key not in made:
            made[key] = parse(path)
        return made[key]

    def load_grid(self, info, plane):
        return self._parsed(info.grid_path(), gridmod.load).plane(plane)

    def load_metatiles(self, info):
        return self._parsed(info.source("CELL_PICTURES", "cell_pictures.tsv"), tablemod.load)

    # ---- rendering -------------------------------------------------------

    def _sheet_rgba(self, path, pal_row, palette):
        key = (path, pal_row, tuple(map(tuple, palette)))
        img = self._sheet_cache.get(key)
        if img is None:
            p = Image.open(path).copy()
            # 4bpp PNGs may index 0..15; map every index into the 16 colours,
            # colour 0 of every 16 being transparent.
            flat = []
            for c in range(16):
                rgb = list(palette[pal_row][c]) if pal_row < len(palette) else [0, 0, 0]
                flat += rgb + [0 if c == 0 else 255]
            p.putpalette(flat * 16, "RGBA")
            img = p.convert("RGBA")
            self._sheet_cache[key] = img
        return img

    def metatile_atlas(self, info, char_base):
        """All metatiles as 16x16 RGBA tiles, 32 per row, for one char base."""
        mt = self.load_metatiles(info)
        palette = self.palette_rows(info)
        blocks = info.resources["blocks"] if info.resources else [None] * 3
        count = len(mt.rows)
        atlas = Image.new("RGBA", (32 * 16, ((count + 31) // 32) * 16), (0, 0, 0, 0))
        tiles = {}  # most blocks reuse the same few tile entries
        paths = {}  # char block -> its sheet, looked up once
        for i, entries in enumerate(mt.rows):
            ox, oy = (i % 32) * 16, (i // 32) * 16
            for k, e in enumerate(entries):
                if e in tiles:
                    if tiles[e] is not None:
                        atlas.paste(tiles[e], (ox + (k % 2) * 8, oy + (k // 2) * 8))
                    continue
                tiles[e] = None
                a = char_base * 512 + (e & 0x3FF)
                block = a // 512
                if not 1 <= block <= 3:
                    continue  # block 0 is window tiles; 4+ is not BG VRAM
                if block not in paths:
                    paths[block] = self.label_path(blocks[block - 1])
                path = paths[block]
                if path is None or (e >> 12) >= len(palette):
                    continue  # palette rows 14/15 belong to the UI
                sheet = self._sheet_rgba(path, e >> 12, palette)
                t = a % 512
                tile = sheet.crop(((t % 32) * 8, (t // 32) * 8, (t % 32) * 8 + 8, (t // 32) * 8 + 8))
                if e & 0x400:
                    tile = tile.transpose(Image.FLIP_LEFT_RIGHT)
                if e & 0x800:
                    tile = tile.transpose(Image.FLIP_TOP_BOTTOM)
                tiles[e] = tile
                atlas.paste(tile, (ox + (k % 2) * 8, oy + (k // 2) * 8))
        return atlas

    def layer_origin(self, info, li):
        """Top-left cell of layer `li` in the 128x128 grid."""
        return info.layers[li][0] // 2, info.layers[li][1] // 2

    @staticmethod
    def resolve_placeholders(cells):
        """Copy of the block plane with each 0xfff numbered as the game does:
        the k-th one, row-major, becomes block k with its top nibble kept."""
        out, k = [], 0
        for row in cells:
            r = list(row)
            if not _PLACEHOLDERS.isdisjoint(r):
                for i, v in enumerate(r):
                    if (v & 0xFFF) == EMPTY:
                        r[i] = (v & 0xF000) | k
                        k += 1
            out.append(r)
        return out

    @staticmethod
    def encode_placeholders(blocks):
        """Inverse of resolve_placeholders: walking row-major with a counter
        k, a cell holding block k is written 0xfff (top nibble kept) and k
        advances; any other cell keeps its explicit number. Exact inverse on
        all 182 TBS maps. Returns (cells, placeholder_count)."""
        out, k = [], 0
        for row in blocks:
            r = []
            for v in row:
                if (v & 0xFFF) == k:
                    r.append((v & 0xF000) | EMPTY)
                    k += 1
                else:
                    r.append(v)
            out.append(r)
        return out, k

    def render_inputs(self, info):
        """The files render() reads for this map: its map.s and tables, its
        palette and its tile sheets. A picture made from them stays right
        until one of them changes."""
        paths = {os.path.join(info.folder, "map.s"), info.grid_path(), *info.sources.values()}
        if info.resources:
            paths.add(self.label_path(info.resources["palette"]))
            paths.update(self.label_path(b) for b in info.resources["blocks"])
        return sorted(p for p in paths if p)

    def marker_path(self, info):
        """The file holding this map's chests and stones: its own map.s."""
        return os.path.join(info.folder, "map.s")

    def marker_users(self, path):
        """Maps whose markers are in `path`: only its own, since they're inline."""
        return sorted(n for n, m in self.maps.items() if self.marker_path(m) == path)

    def load_markers(self, info):
        """(path, Markers), which save themselves back into map.s."""
        path = self.marker_path(info)
        return path, Markers(path)

    def markers(self, info):
        """(x, z, id) rows, end marker excluded."""
        _, t = self.load_markers(info)
        if t is None:
            return []
        return [tuple(r[:3]) for r in t.rows if tuple(r[:3]) != (0xFF, 0xFF, 0xFF)]

    def apply_edits(self, info, edits, marker_ops=None):
        """Apply cell edits and save the grid TSVs.

        edits: [{"plane": "block"|"collision"|"shape", "x": gx, "y": gy,
        "value": int}] in 128x128 grid coordinates; block values are
        resolved block numbers with flags in the top nibble.
        Returns {"saved": [paths], "warnings": [...]}. Raises ValueError,
        with nothing written, when an invariant would break.
        """
        grid = gridmod.load(info.grid_path())
        planes = {p: grid.plane(p) for p in gridmod.PLANES}
        blocks = self.resolve_placeholders(planes["metatile"].cells)
        block_count = len(self.load_metatiles(info).rows)
        touched = set()
        for e in edits:
            x, y, v = int(e["x"]), int(e["y"]), int(e["value"])
            if not 0 <= v <= 0xFFFF:
                raise ValueError(f"{v} isn't a value a cell can hold")
            if not (0 <= x < 128 and 0 <= y < 128):
                raise ValueError(tr("cell {x},{y} is outside the 128x128 grid", x=x, y=y))
            if e["plane"] == "block":
                if (v & 0xFFF) >= block_count:
                    raise ValueError(f"block {v & 0xFFF:#x} does not exist (map has {block_count})")
                blocks[y][x] = v
                touched.add("metatile")
            elif e["plane"] in ("collision", "shape"):
                g = planes[e["plane"]]
                if not 0 <= v <= g.max_value:
                    raise ValueError(f"{e['plane']} value {v:#x} out of range")
                if e["plane"] == "shape" and v >= len(self.shape_rows(info)):
                    raise ValueError(tr("This place has no such height. Pick one from the Height panel."))
                g.cells[y][x] = v
                touched.add(e["plane"])
            else:
                raise ValueError(f"unknown plane {e['plane']!r}")
        # Marker moves: rewrite the row, write the id into the new cell's
        # collision code and restore the old cell, all in one save.
        marker_path, marker_table = self.load_markers(info)
        marker_rows = marker_table.rows if marker_table else []
        for op in marker_ops or []:
            if marker_table is None:
                raise ValueError(tr("this map has no chest list to edit"))
            if len(self.marker_users(marker_path)) > 1:
                raise ValueError(tr("{file} is shared by maps {maps}; not editable yet",
                                    file=os.path.basename(marker_path), maps=", ".join(self.marker_users(marker_path))))
            i = int(op["index"])
            if not (0 <= i < len(marker_rows)) or tuple(marker_rows[i][:3]) == (0xFF, 0xFF, 0xFF):
                raise ValueError(f"no marker #{i}")
            x, z = int(op["x"]), int(op["z"])
            if not (0 <= x < 128 and 0 <= z < 128):
                raise ValueError(tr("cell {x},{z} is outside the grid", x=x, z=z))
            ox, oz, mid = marker_rows[i][:3]
            if (x, z) == (ox, oz):
                continue
            if any(j != i and tuple(r[:2]) == (x, z) for j, r in enumerate(marker_rows)):
                raise ValueError(tr("cell {x},{z} already holds a marker", x=x, z=z))
            if 1 <= planes["collision"].cells[z][x] <= 239:
                raise ValueError(tr("That square already does something, like a door or a sign. "
                                    "Pick another square for the chest."))
            restore = int(op.get("restore", 0))
            if restore == mid or not 0 <= restore <= 0xFF:
                raise ValueError(f"old cell needs a collision code other than the marker's {mid:#x}")
            col = planes["collision"].cells
            col[oz][ox] = restore
            col[z][x] = mid
            marker_table.set(i, 0, x)
            marker_table.set(i, 1, z)
            touched.add("collision")
            touched.add("markers")
        # Chests and Psynergy stones: the marker id must equal the collision code.
        col = planes["collision"].cells
        for mx, mz, mid in [tuple(r[:3]) for r in marker_rows if tuple(r[:3]) != (0xFF, 0xFF, 0xFF)]:
            if col[mz][mx] != mid:
                raise ValueError(tr(
                    "The square at {x},{z} holds a chest or Psynergy Stone, so its walkability can't "
                    "be painted. Move or remove the chest first.", x=mx, z=mz))
        warnings = []
        if "metatile" in touched:
            # Fewer placeholders than blocks is fine: a painted cell is written
            # as its block's number, and the game draws those as they are.
            grid.planes["metatile"], _ = self.encode_placeholders(blocks)
        saved = []
        if touched - {"markers"}:
            gridmod.save(grid, info.grid_path())
            self._parse_cache.pop(info.grid_path(), None)
            saved.append(info.grid_path())
        if "markers" in touched:
            marker_table.save()
            saved.append(marker_path)
        return {"saved": saved, "warnings": warnings}

    def shape_rows(self, info):
        """[kind, h0, h1, h2] per shape id, heights signed, in 8-px units
        (field/field/terrain.c: a sample is in eight-pixel units)."""
        t = self._parsed(info.source("SHAPES", "shapes.tsv"), tablemod.load)
        return [[r[0]] + [v - 256 if v > 127 else v for v in r[1:4]] for r in t.rows]

    @staticmethod
    def cell_height(row):
        """Ground height (px) at a cell's centre: flat kinds use their sample,
        slopes along x or y the middle of theirs, steps the higher side."""
        if not row:
            return 0
        k, a, b, c = row[0] & 15, row[1], row[2], row[3]
        h = a if k == 0 else (a + b) / 2 if k in (1, 2) else max(a, b, c)
        return h * 8

    def ground_height(self, info, x, z, layer=0):
        """Ground height (px) under map pixel (x, z) on a layer's window."""
        ox, oz = self.layer_origin(info, layer)
        gx = (ox + info.bounds[0] // 2 + (x - info.bounds[0] * 8) // 16) % 128
        gz = (oz + info.bounds[1] // 2 + (z - info.bounds[1] * 8) // 16) % 128
        try:
            v = self.load_grid(info, "shape").cells[gz][gx]
            rows = self.shape_rows(info)
        except FileNotFoundError:
            return 0
        return self.cell_height(rows[v] if v < len(rows) else None)

    def resolved_blocks(self, info):
        """The block plane with placeholders numbered, kept until the grid
        changes. Shared: treat it as read-only."""
        return self._parsed(info.grid_path(), lambda path: self.resolve_placeholders(
            self.load_grid(info, "metatile").cells), key="resolved")

    def render_layer(self, info, li, blocks=None, atlas=None):
        """One layer's window (header bounds) as transparent RGBA."""
        w, h = info.size
        blocks = blocks or self.resolved_blocks(info)
        atlas = atlas or self.metatile_atlas(info, info.char_base[li])
        count = (atlas.width // 16) * (atlas.height // 16)
        tiles = {}  # cut from the atlas as they're first used
        lx, ly = self.layer_origin(info, li)
        left, top = info.bounds[0] // 2, info.bounds[1] // 2
        # Each cell is drawn once, over nothing: paste the tiles side by side,
        # then composite the whole layer over transparency in one go, which
        # gives every pixel what compositing tile by tile gave it.
        laid = Image.new("RGBA", (w * 16, h * 16), (0, 0, 0, 0))
        for y in range(h):
            row = blocks[(ly + top + y) % 128]
            for x in range(w):
                b = row[(lx + left + x) % 128] & 0xFFF
                if b < count:
                    tile = tiles.get(b)
                    if tile is None:
                        tile = tiles[b] = atlas.crop(((b % 32) * 16, (b // 32) * 16, (b % 32) * 16 + 16, (b // 32) * 16 + 16))
                    laid.paste(tile, (x * 16, y * 16))
        return Image.alpha_composite(Image.new("RGBA", (w * 16, h * 16), (0, 0, 0, 0)), laid)

    def render(self, info, layers=(0, 1, 2)):
        """Composite the visible map, back layer first. Returns RGBA image."""
        w, h = info.size
        blocks = self.resolved_blocks(info)
        out = Image.new("RGBA", (w * 16, h * 16), (0, 0, 0, 255))
        order = sorted(
            (i for i in layers if info.priority[i] != 0), key=lambda i: -info.priority[i]
        )
        atlases = {}  # layers on one char base draw from the same atlas
        for li in order:
            base = info.char_base[li]
            if base not in atlases:
                atlases[base] = self.metatile_atlas(info, base)
            out.alpha_composite(self.render_layer(info, li, blocks, atlases[base]))
        return out
