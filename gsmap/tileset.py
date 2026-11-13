"""Custom images into a map's own tile set.

A map's tiles live in three 512-tile sheets (char blocks 1-3, the PNGs its
gMaps row names) and its colours in 14 palette rows of 16; there is no
more background VRAM. Importing an image therefore:

  1. cuts it into 8x8 tiles and gives each the palette row that fits it best
     (colour 0 is transparent);
  2. reuses an identical tile already in a reachable sheet (also mirrored);
  3. places new tiles in blank tiles no block uses, then, if needed, in tiles
     only used by blocks the map doesn't place - those blocks are *retired*:
     the editor hides them and Stamp refuses them, so nothing draws them;
  4. appends one block per 16x16 cell to the map's cell_pictures.tsv.

Only for maps with their own tile set (the debug sandbox). Retired blocks and
the block family (the table a map's blocks were copied from, for Stamp) are
kept in alchemy's games/tbs/src/mod/tilesets.json.
"""

from collections import Counter
import base64
import hashlib
import io
import json
import os

from PIL import Image

from . import layout
from . import table as tablemod
from .fsio import atomic_write
from .i18n import tr

ROWS = 14  # palette rows a map owns


def meta_path(root):
    return os.path.join(root, layout.MOD, "tilesets.json")


def load_meta(root):
    p = meta_path(root)
    try:
        with open(p, encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError):  # no notes, or unreadable: nothing is marked as retired
        return {}
    return meta if isinstance(meta, dict) else {}


def save_meta(root, meta):
    atomic_write(meta_path(root), json.dumps(meta, indent=1, sort_keys=True) + "\n")


def table_hash(path, rows=None):
    """Fingerprint of a block table, or of its first `rows` blocks."""
    lines = open(path, encoding="utf-8").read().split("\n")
    if rows is not None:
        lines = lines[: 1 + rows]
    return hashlib.sha1("\n".join(lines).encode()).hexdigest()[:16]


def block_family(project, info):
    """(family hash, family size): blocks 0..size-1 are shared with the
    family's other maps, so stamps between them keep their meaning."""
    meta = load_meta(project.root).get(info.number, {})
    path = info.source("CELL_PICTURES", "cell_pictures.tsv")
    if "family" in meta:
        return meta["family"], meta["family_size"]
    rows = len(project.load_metatiles(info).rows)
    return table_hash(path), rows


def retired_blocks(project, info):
    return set(load_meta(project.root).get(info.number, {}).get("retired", []))


def _sheets(project, info):
    return {project.label_path(label) for row in [info.resources] + info.alternates if row
            for label in row["blocks"] if label} - {None}


def own_tileset_maps(project):
    """Map numbers own_tileset accepts, working out every map's sheets once."""
    sheets = {n: _sheets(project, m) for n, m in project.maps.items()}
    users = Counter(path for paths in sheets.values() for path in paths)
    return sorted(n for n, paths in sheets.items() if paths and all(users[p] == 1 for p in paths))


def own_tileset(project, info):
    """True when no other map draws any of this map's tile sheets. Compares the
    files, since a set's label can be built from another set's sheet; one
    shared sheet is enough for an import to change how another map looks."""
    mine = _sheets(project, info)
    # Another map shares a sheet when one of its labels names a file in `mine`
    # (files that exist, so the existence test _sheets makes can be skipped).
    return bool(mine) and not any(
        m is not info and any(project.symbols.get(label or "") in mine
                              for row in [m.resources] + m.alternates if row for label in row["blocks"] if label)
        for m in project.maps.values())


def _tile(img, t):
    return img.crop(((t % 32) * 8, (t // 32) * 8, (t % 32) * 8 + 8, (t // 32) * 8 + 8))


def _key(pixels):
    return tuple(v & 15 for v in pixels)


def _flips(key):
    rows = [key[r * 8:(r + 1) * 8] for r in range(8)]
    h = tuple(v for r in rows for v in reversed(r))
    v = tuple(x for r in reversed(rows) for x in r)
    hv = tuple(x for r in reversed(rows) for x in reversed(r))
    return {(key, 0): 0, (h, 0): 0x400, (v, 0): 0x800, (hv, 0): 0xC00}


def import_image(project, info, png_bytes, layer, dry_run=True):
    """Fit an image into info's tile set for drawing on `layer`.
    Returns a report; unless dry_run, writes sheets, blocks and metadata."""
    if not own_tileset(project, info):
        raise ValueError(tr("This place shares its tile art with other places, so a picture here would change them too. Import pictures into a place with art of its own."))
    base = info.char_base[layer]
    reach = [b for b in (base, base + 1) if 1 <= b <= 3]  # char blocks a layer's 1024 tiles span
    sheets = {b: Image.open(project.label_path(info.resources["blocks"][b - 1])) for b in (1, 2, 3)}
    for b in sheets:
        sheets[b].load()
    pal_img = Image.open(project.palette_path(info)).convert("RGB")
    palette = [[pal_img.getpixel((c, r)) for c in range(16)] for r in range(min(ROWS, pal_img.height))]

    # Its size is in the file's header, so a huge picture is refused before it's decoded.
    try:
        img = Image.open(io.BytesIO(png_bytes), formats=["PNG", "GIF", "BMP"])
    except OSError:
        raise ValueError(tr("That doesn't look like a PNG, GIF or BMP picture.")) from None
    w16, h16 = (img.width + 15) // 16, (img.height + 15) // 16
    if w16 * h16 > 256:
        raise ValueError(tr("That picture is too big: at most 256 squares, for example 256×256 pixels."))
    img = img.convert("RGBA")
    canvas = Image.new("RGBA", (w16 * 16, h16 * 16), (0, 0, 0, 0))
    canvas.paste(img, (0, 0))

    mt_path = info.source("CELL_PICTURES", "cell_pictures.tsv")
    mt = tablemod.load(mt_path)
    retired = retired_blocks(project, info)

    # which blocks the map places, and which blocks use each tile
    placed = set()
    blocks = project.resolved_blocks(info)
    for li, l in enumerate(info.layers):
        if not info.priority[li]:
            continue
        ox, oy = project.layer_origin(info, li)
        left, top = info.bounds[0] // 2, info.bounds[1] // 2
        for y in range(info.size[1]):
            for x in range(info.size[0]):
                placed.add(blocks[(oy + top + y) % 128][(ox + left + x) % 128] & 0xFFF)
    users = {}
    bases = sorted({info.char_base[li] for li in range(len(info.layers)) if info.priority[li]})
    for bid, row in enumerate(mt.rows):
        if bid in retired:
            continue
        for e in row:
            for bs in bases:
                a = bs * 512 + (e & 0x3FF)
                users.setdefault((a // 512, a % 512), set()).add(bid)

    # existing tiles a layer can reach, for reuse
    known = {}
    for b in reach:
        for t in range(512):
            if (b, t) in users or t == 0:
                k = _key(_tile(sheets[b], t).getdata())
                for (fk, _), flip in _flips(k).items():
                    known.setdefault(fk, (b, t, flip))
    blank_rel = next(((b * 512 + t) - base * 512 for b in reach for t in range(512)
                      if all(v & 15 == 0 for v in _tile(sheets[b], t).getdata())), None)

    def nearest(row, rgb):
        return min(((c, (rgb[0] - row[c][0]) ** 2 + (rgb[1] - row[c][1]) ** 2 + (rgb[2] - row[c][2]) ** 2)
                    for c in range(1, 16)), key=lambda t: t[1])

    # One row for the whole image keeps its colours consistent from tile to
    # tile; only when no row comes close does each tile pick its own.
    opaque_px = [q[:3] for q in canvas.getdata() if q[3] >= 128]
    row_cost = [sum(nearest(row, c)[1] for c in opaque_px) for row in palette]
    image_row = min(range(len(palette)), key=lambda r: row_cost[r])
    per_tile = bool(opaque_px) and row_cost[image_row] / len(opaque_px) > 40 ** 2

    def fit(tile_rgba):
        """Palette row and 4-bit indices for one 8x8 tile."""
        px = list(tile_rgba.getdata())
        best = None
        for r, row in enumerate(palette):
            if not per_tile and r != image_row:
                continue
            idx, cost = [], 0
            for (rr, gg, bb, aa) in px:
                if aa < 128:
                    idx.append(0)
                    continue
                c, d = min(((c, (rr - row[c][0]) ** 2 + (gg - row[c][1]) ** 2 + (bb - row[c][2]) ** 2)
                            for c in range(1, 16)), key=lambda t: t[1])
                idx.append(c)
                cost += d
            if best is None or cost < best[0]:
                best = (cost, r, idx)
        return best[1], best[2]

    # free tiles: blank and unused first, then tiles only retireable blocks use
    free = [(b, t) for b in reach for t in range(1, 512)
            if (b, t) not in users and all(v & 15 == 0 for v in _tile(sheets[b], t).getdata())]
    reclaimable = sorted(
        ((b, t) for (b, t), us in users.items() if b in reach and t != 0 and not (us & placed)),
        key=lambda bt: len(users[bt]))

    preview = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    new_tiles, reused, newly_retired, in_use = {}, 0, set(), set()
    cells = []
    for cy in range(h16):
        row_ids = []
        for cx in range(w16):
            entries, opaque = [], False
            for sy in (0, 8):
                for sx in (0, 8):
                    t_rgba = canvas.crop((cx * 16 + sx, cy * 16 + sy, cx * 16 + sx + 8, cy * 16 + sy + 8))
                    if all(p[3] < 128 for p in t_rgba.getdata()):
                        if blank_rel is None:
                            raise ValueError(tr("no blank tile reachable for transparent parts"))
                        entries.append(blank_rel)
                        continue
                    opaque = True
                    r, idx = fit(t_rgba)
                    k = tuple(idx)
                    if k in known and known[k][:2] not in new_tiles.values():
                        b, t, flip = known[k]
                        reused += 1
                        in_use.add((b, t))
                    elif k in new_tiles:
                        b, t = new_tiles[k]
                        flip = 0
                    else:
                        if free:
                            b, t = free.pop(0)
                        elif reclaimable:
                            # never reclaim a tile this image reuses
                            while reclaimable and reclaimable[0] in in_use:
                                reclaimable.pop(0)
                            if not reclaimable:
                                raise ValueError(tr("no room left in this tile set"))
                            b, t = reclaimable.pop(0)
                            newly_retired |= users.get((b, t), set())
                        else:
                            raise ValueError(tr("no room left in this tile set"))
                        new_tiles[k] = (b, t)
                        flip = 0
                        sheets[b].putdata(_put(sheets[b], t, idx))
                    entries.append(((b * 512 + t) - base * 512) | flip | (r << 12))
                    # preview with the colours the game will show
                    pv = Image.new("RGBA", (8, 8))
                    pv.putdata([(0, 0, 0, 0) if v == 0 else palette[r][v] + (255,) for v in idx])
                    preview.paste(pv, (cx * 16 + sx, cy * 16 + sy))
            row_ids.append(entries if opaque else None)
        cells.append(row_ids)

    report = {
        "cells": [w16, h16], "layer": layer,
        "palette_row": None if per_tile else image_row,
        "new_tiles": len(new_tiles), "reused_tiles": reused,
        "retired_blocks": len(newly_retired), "free_tiles_left": len(free) + len(reclaimable),
    }
    buf = io.BytesIO()
    preview.save(buf, "PNG")
    report["preview"] = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    if dry_run:
        return report

    # write: sheets, blocks, metadata
    count = sum(1 for row in cells for entries in row if entries is not None)
    if len(mt.rows) + count > 4095:
        raise ValueError(tr("a map holds at most 4,095 blocks"))
    family, fsize = block_family(project, info)
    for b, im in sheets.items():
        if any(nb == b for nb, _ in new_tiles.values()):
            png = io.BytesIO()
            im.save(png, "PNG")
            atomic_write(project.label_path(info.resources["blocks"][b - 1]), png.getvalue())
    ids = []
    for row in cells:
        out = []
        for entries in row:
            if entries is None:
                out.append(None)
            else:
                mt.append(entries)
                out.append(len(mt.rows) - 1)
        ids.append(out)
    tablemod.save(mt, mt_path)
    project._parse_cache.pop(mt_path, None)
    meta = load_meta(project.root)
    entry = meta.setdefault(info.number, {})
    entry["family"], entry["family_size"] = family, fsize
    entry["retired"] = sorted(set(entry.get("retired", [])) | newly_retired)
    save_meta(project.root, meta)
    project._sheet_cache.clear()
    report["blocks"] = ids
    return report


def _put(sheet, t, idx):
    """Sheet pixels with tile t replaced by idx (4-bit values)."""
    data = list(sheet.getdata())
    w = sheet.width
    x0, y0 = (t % 32) * 8, (t // 32) * 8
    for i, v in enumerate(idx):
        data[(y0 + i // 8) * w + x0 + i % 8] = v
    return data
