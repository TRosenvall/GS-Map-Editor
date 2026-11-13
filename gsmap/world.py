"""The overworld (Golden Sun: The Broken Seal world map). Sources and evidence:
docs/research/overworld.md.

  blocks.tsv   320 rows x 512 hex words: 640 chunks of 16x16 cells, laid 32
               chunks wide; chunk c (0-255) sits at world chunk (c%16, c//16),
               layer 1 is chunk c+320, 256-319 are alternates swapped in by code.
  cell word    bits 0-15 block, 16-23 step code, 24-30 terrain kind
               (encounter region; 21 = snowy graphics), 31 behaviour bank.
               Layer 1 uses only the block.
  default/cell_pictures.tsv  4 tile bytes per block (TL TR BL BR).
  default/collision.txt      per 8x8 tile, 4x4 walkability nibbles, written as
               sheets of 16 tiles across; upper layer wins, then lower, else
               7; 5-12 walkable.
  graphics     set A: tiles a+b (ground) c+d (overlay), palette a;
               set B (snowy north, kind 21): tiles f+g, h+i, palette b.

Coordinates: a cell is 16 BG px (32 world px); the world is 256x256 cells.
Entrances and placements are in world px (placements 16.16).
"""

import os

from PIL import Image

from . import layout
from .sceneedit import actor_numbers
from . import table as tablemod
from .fsio import atomic_write
from .i18n import tr

CHUNKS, LAYER1 = 640, 320
WORLD_CHUNKS = 16  # per side
SNOW_KIND = 21
SET_B_SWAPS = {10: 0x10A, 11: 0x10B, 12: 0x10C, 26: 0x11A, 27: 0x11B, 28: 0x11C}
SETS = {"a": ("a", "b", "c", "d", "palette_a"), "b": ("f", "g", "h", "i", "palette_b")}
WALK_MIN, WALK_MAX = 5, 12


def parse_collision(text):
    """collision.txt as the bytes the game reads: 8 per tile, 2 per row of 4
    nibbles, the first nibble of each pair in its low half. The sheet has 16
    tiles across, 4 lines per row of tiles, and a blank line between rows."""
    out = []
    rows = [[line.split() for line in part.split("\n")] for part in text.strip("\n").split("\n\n")]
    for row in rows:
        for tile in range(len(row[0])):
            for line in row:
                n = [int(c, 16) for c in line[tile]]
                out += [n[0] | n[1] << 4, n[2] | n[3] << 4]
    return out


def parse_blocks(text):
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    return [[int(t, 16) for t in line.split("\t")] for line in lines]


def format_blocks(rows):
    return "".join("\t".join(format(v, "x") for v in row) + "\n" for row in rows)


class World:
    def __init__(self, root):
        self.root = root
        self.blocks_path = os.path.join(root, layout.WORLD_BLOCKS)
        self.cells_path = os.path.join(root, layout.WORLD_CELLS)
        self.attr_path = os.path.join(root, layout.WORLD_COLLISION)
        self.gfx = os.path.join(root, layout.WORLD_GRAPHICS)
        self.rows = parse_blocks(open(self.blocks_path, encoding="utf-8").read())
        flat = [v for r in tablemod.load(self.cells_path).rows for v in r]
        self.block_tiles = [flat[i:i + 4] for i in range(0, len(flat) - 3, 4)]
        self.attr = parse_collision(open(self.attr_path, encoding="utf-8").read())  # 0x000-0x7ff lower tiles, 0x800-0xfff upper
        self._tiles = {}
        self._snowy = {}

    # ---- cells -------------------------------------------------------------------

    @staticmethod
    def chunk_of(cx, cy, snowy=False):
        slot = cy * WORLD_CHUNKS + cx
        return SET_B_SWAPS.get(slot, slot) if snowy else slot

    def word(self, chunk, x, y):
        return self.rows[(chunk // 32) * 16 + y][(chunk % 32) * 16 + x]

    def set_word(self, chunk, x, y, v):
        self._snowy.clear()
        self.rows[(chunk // 32) * 16 + y][(chunk % 32) * 16 + x] = v

    def cell(self, gx, gy):
        """Layer-0 and layer-1 words at world cell (gx, gy), as shown."""
        c = self.shown_chunk(gx // 16, gy // 16)
        return self.word(c, gx % 16, gy % 16), self.word(c + LAYER1, gx % 16, gy % 16)

    @staticmethod
    def decode(word):
        return {"block": word & 0xFFFF, "code": (word >> 16) & 0xFF,
                "kind": (word >> 24) & 0x7F, "bank": word >> 31}

    def save(self):
        atomic_write(self.blocks_path, format_blocks(self.rows))

    # ---- graphics -------------------------------------------------------------------

    def _tile_images(self, set_name, layer):
        """256 RGBA 8x8 tiles of one bank; layer 1 keeps colour 0 transparent."""
        key = (set_name, layer)
        if key not in self._tiles:
            names = SETS[set_name]
            pal = Image.open(os.path.join(self.gfx, names[4] + ".png")).convert("RGB")
            colours = [pal.getpixel((i % 16, i // 16)) for i in range(16 * pal.height)]
            flat = [c for rgb in colours for c in rgb]
            tiles = []
            for sheet in names[layer * 2: layer * 2 + 2]:
                src = Image.open(os.path.join(self.gfx, f"tiles_{sheet}.png"))
                idx = src.copy()
                idx.putpalette((flat + [0] * 768)[:768])
                rgba = idx.convert("RGBA")
                if layer == 1:
                    mask = Image.new("L", src.size)
                    mask.putdata([0 if v == 0 else 255 for v in src.getdata()])
                    rgba.putalpha(mask)
                for t in range(128):
                    tiles.append(rgba.crop(((t % 16) * 8, (t // 16) * 8, (t % 16) * 8 + 8, (t // 16) * 8 + 8)))
            self._tiles[key] = tiles
        return self._tiles[key]

    def block_image(self, block, layer, set_name="a"):
        tiles = self._tile_images(set_name, layer)
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        if block < len(self.block_tiles):
            for k, t in enumerate(self.block_tiles[block]):
                img.alpha_composite(tiles[t], ((k & 1) * 8, (k >> 1) * 8))
        return img

    def is_snowy(self, cx, cy):
        """A chunk is drawn in set B (snowy) when most of its ground cells are
        kind 21, as the game picks the set from where the party stands."""
        if (cx, cy) not in self._snowy:
            slot = self.chunk_of(cx, cy)
            self._snowy[cx, cy] = sum(1 for y in range(16) for x in range(16)
                                      if (self.word(slot, x, y) >> 24) & 0x7F == SNOW_KIND) > 128
        return self._snowy[cx, cy]

    def shown_chunk(self, cx, cy):
        """The chunk drawn at (cx, cy): set B's alternate where it's snowy, so
        an edit lands on the cells you see."""
        return self.chunk_of(cx, cy, self.is_snowy(cx, cy))

    def render_chunk(self, cx, cy, layers=(0, 1)):
        """256x256 BG px of world chunk (cx, cy), in the set the game shows there."""
        snowy = self.is_snowy(cx, cy)
        set_name = "b" if snowy else "a"
        c = self.chunk_of(cx, cy, snowy)
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 255))
        for layer in layers:
            tiles = self._tile_images(set_name, layer)
            base = c + LAYER1 * layer
            for y in range(16):
                for x in range(16):
                    b = self.word(base, x, y) & 0xFFFF
                    if b >= len(self.block_tiles):
                        continue
                    for k, t in enumerate(self.block_tiles[b]):
                        img.alpha_composite(tiles[t], (x * 16 + (k & 1) * 8, y * 16 + (k >> 1) * 8))
        return img

    # ---- walkability and regions -------------------------------------------------------

    def _nibble(self, upper, tile, px, py):
        """Walkability value of 2x2-px unit (px, py) (0..3) of a tile."""
        byte = self.attr[(0x800 if upper else 0) + tile * 8 + py * 2 + px // 2]
        return (byte >> 4) if px & 1 else (byte & 0xF)

    def walk_grid(self, cx, cy):
        """64x64 walkability values (one per 4x4 world px) for chunk (cx, cy), set A."""
        c = self.chunk_of(cx, cy)
        out = [[7] * 128 for _ in range(128)]
        for y in range(16):
            for x in range(16):
                lo = self.block_tiles[self.word(c, x, y) & 0xFFFF] if (self.word(c, x, y) & 0xFFFF) < len(self.block_tiles) else [0] * 4
                hb = self.word(c + LAYER1, x, y) & 0xFFFF
                hi = self.block_tiles[hb] if hb < len(self.block_tiles) else [0] * 4
                for k in range(4):
                    for py in range(4):
                        for px in range(4):
                            v = self._nibble(True, hi[k], px, py) or self._nibble(False, lo[k], px, py) or 7
                            out[y * 8 + (k >> 1) * 4 + py][x * 8 + (k & 1) * 4 + px] = v
        return out

    def render_walk(self, cx, cy):
        """256x256 overlay: blocked ground tinted red, the rest clear."""
        g = self.walk_grid(cx, cy)
        small = Image.new("RGBA", (128, 128))
        small.putdata([(0, 0, 0, 0) if WALK_MIN <= v <= WALK_MAX else (230, 60, 50, 120)
                       for row in g for v in row])
        return small.resize((256, 256), Image.NEAREST)

    def render_kind(self, cx, cy, colours):
        """256x256 overlay: each cell tinted by its terrain kind (encounter region)."""
        c = self.chunk_of(cx, cy)
        small = Image.new("RGBA", (16, 16))
        small.putdata([colours.get((self.word(c, x, y) >> 24) & 0x7F, (0, 0, 0, 0))
                       for y in range(16) for x in range(16)])
        return small.resize((256, 256), Image.NEAREST)

    def chunk_cells(self, cx, cy):
        """[[ground word, overlay word]] for the 16x16 cells of a world chunk, as shown."""
        c = self.shown_chunk(cx, cy)
        return [[[self.word(c, x, y), self.word(c + LAYER1, x, y)] for x in range(16)] for y in range(16)]


# ---- the world map scene: town icons, step codes, arrival points -----------------------

WORLD_SCENE = 2
ICON_TRIGGER = 100  # touching actor N raises trigger 100 + N


def world_places(world, project, scenes, names, stock=False):
    """Icons (placements) and step-code cells with where they lead, and the
    arrival points, from the world map scene's tables as the mod sees them
    (with stock, as the original game has them)."""
    from .doors import DoorEditor
    de = DoorEditor(project, scenes, names, stock=stock)
    sc = next(s for s in scenes.scenes if s["id"] == WORLD_SCENE)
    o = scenes.overlay(sc["overlay"])
    ov = de._read_overrides()
    events = de._tables([o], ov, "events")
    exits = de._tables([o], ov, "exits")

    def lead(trigger):
        kind, scripted = de._exit_kind(events, trigger)
        if kind is None:
            return None
        ex = de._destination(exits, WORLD_SCENE, kind)
        if ex is None:
            return {"kind": kind, "scene": None, "entrance": None, "label": None, "scripted": scripted}
        return {"kind": kind, "scene": ex["scene"], "entrance": ex["entrance"],
                "label": names.scene_label(ex["scene"]), "scripted": scripted}

    icons = []
    rows = de._tables([o], ov, "placements")
    main = next((r for _, name, r in rows if name == layout.WORLD_PLACEMENTS), [])
    stock = stock_icons(scenes)
    for i, (actor, r) in enumerate(zip(actor_numbers(main), main)):
        icons.append({"actor": actor, "row": i, "sprite": r["sprite"], "x": r["x"] >> 16, "z": r["z"] >> 16,
                      "lead": lead(ICON_TRIGGER + actor), "added": i >= stock})
    steps = []
    for gy in range(256):
        for gx in range(256):
            code = (world.cell(gx, gy)[0] >> 16) & 0xFF
            if 1 <= code <= 239:
                steps.append({"gx": gx, "gy": gy, "code": code, "lead": lead(code)})
    arrivals = []
    for _, _, rs in de._tables([o], ov, "entrances", need=False):
        for r in rs:
            if r["entrance"] >= 0 and all(a["entrance"] != r["entrance"] for a in arrivals):
                arrivals.append({"entrance": r["entrance"], "x": r["x"], "z": r["z"]})
    return {"icons": icons, "steps": steps, "arrivals": arrivals}


def region_names(world, places, names):
    """{kind: label}: each terrain kind (encounter region) named after the
    places whose icons stand in it."""
    near = {}
    for ic in places["icons"]:
        if ic["lead"] and ic["lead"]["scene"] is not None and ic["x"]:
            kind = (world.cell(ic["x"] // 32, ic["z"] // 32)[0] >> 24) & 0x7F
            area = (names.places.get(ic["lead"]["scene"]) or {}).get("area_name") or ic["lead"]["label"]
            near.setdefault(kind, [])
            if area not in near[kind]:
                near[kind].append(area)
    out = {}
    for kind in sorted({(w >> 24) & 0x7F for row in world.rows[:160] for w in row}):
        if kind == 0:
            out[0] = tr("No encounters")
            continue
        towns = near.get(kind, [])
        base = tr("Snowfield") if kind == SNOW_KIND else tr("Region {n}", n=kind)
        out[kind] = (tr("{region} ({places})", region=base,
                        places=", ".join(towns[:3]) + ("…" if len(towns) > 3 else "")) if towns else base)
    return out


def apply_world_edits(world, edits):
    """edits: [{gx, gy, layer, word? | block?, kind?, code?}] in world cells
    (set A). Returns the words they replaced, for undo."""
    before = []
    for e in edits:
        gx, gy, layer = int(e["gx"]), int(e["gy"]), int(e.get("layer", 0))
        if not (0 <= gx < 256 and 0 <= gy < 256 and layer in (0, 1)):
            raise ValueError(tr("cell {x},{y} is outside the world", x=gx, y=gy))
        c = world.shown_chunk(gx // 16, gy // 16) + LAYER1 * layer
        w = world.word(c, gx % 16, gy % 16)
        before.append({"gx": gx, "gy": gy, "layer": layer, "word": w})
        if "word" in e:
            w = int(e["word"]) & 0xFFFFFFFF
            if (w & 0xFFFF) >= len(world.block_tiles) or (layer == 1 and w >> 16):
                raise ValueError("bad cell word")
        if "block" in e:
            b = int(e["block"])
            if not 0 <= b < len(world.block_tiles):
                raise ValueError(f"block {b} doesn't exist")
            w = (w & ~0xFFFF) | b
        if layer == 0 and "kind" in e:
            k = int(e["kind"])
            if not 0 <= k <= 0x7F:
                raise ValueError("bad region")
            w = (w & ~(0x7F << 24)) | (k << 24)
        if layer == 0 and "code" in e:
            k = int(e["code"])
            if not 0 <= k <= 0xFF:
                raise ValueError("bad step code")
            w = (w & ~(0xFF << 16)) | (k << 16)
        world.set_word(c, gx % 16, gy % 16, w & 0xFFFFFFFF)
    world.save()
    return before


def block_atlas(world, layer, cols=64):
    """All blocks of one layer (set A), `cols` per row."""
    n = len(world.block_tiles)
    img = Image.new("RGBA", (cols * 16, ((n + cols - 1) // cols) * 16), (0, 0, 0, 0))
    for b in range(n):
        img.alpha_composite(world.block_image(b, layer), ((b % cols) * 16, (b // cols) * 16))
    return img


def move_icon(project, scenes, names, actor, x, z, move_arrivals=True):
    """Move a town icon to world px (x, z), in every story stage's placement
    table that has it at the same spot. With move_arrivals, the arrival
    points the town's exits use (where the party appears on leaving it) move
    by the same amount, so leaving still puts you beside the icon."""
    from .connections import Connections
    from .doors import DoorEditor
    from .modgen import Overrides, generate
    de = DoorEditor(project, scenes, names)
    sc = next(s for s in scenes.scenes if s["id"] == WORLD_SCENE)
    o = scenes.overlay(sc["overlay"])
    ov = Overrides(project.root)
    placements = de._tables([o], ov, "placements")
    main = next(r for _, name, r in placements if name == layout.WORLD_PLACEMENTS)
    numbers = actor_numbers(main)
    if actor not in numbers:
        raise ValueError(f"no icon {actor}")
    row = numbers.index(actor)
    if not (0 <= x < 8192 and 0 <= z < 8192):
        raise ValueError(tr("that spot is outside the world"))
    old = main[row]
    ox, oz, sprite = old["x"] >> 16, old["z"] >> 16, old["sprite"]
    dx, dz = x - ox, z - oz
    changed = []
    for t in placements:
        _, name, rows = t
        for i, r in enumerate(rows):
            if r["sprite"] == sprite and (r["x"] >> 16, r["z"] >> 16) == (ox, oz) and (name != layout.WORLD_PLACEMENTS or i == row):
                r["x"], r["z"] = x << 16, z << 16
                if t not in changed:
                    changed.append(t)
    moved = []
    if move_arrivals and (dx or dz):
        lead = None
        events = de._tables([o], ov, "events")
        kind, _ = de._exit_kind(events, ICON_TRIGGER + actor)
        ex = de._destination(de._tables([o], ov, "exits"), WORLD_SCENE, kind) if kind is not None else None
        if ex:
            lead = ex["scene"]
        if lead is not None:
            # arrival points that exits from the town (and its other parts) use
            idx = Connections(project, scenes, names).index()
            area = (names.places.get(lead) or {}).get("area_name")
            towns = {s["id"] for s in scenes.scenes
                     if s["id"] == lead or (area and (names.places.get(s["id"]) or {}).get("area_name") == area)}
            nums = {e["entrance"] for t in towns for e in idx.get(t, []) if e["scene"] == WORLD_SCENE}
            for t in de._tables([o], ov, "entrances"):
                for r in t[2]:
                    if r["entrance"] in nums:
                        r["x"], r["z"] = r["x"] + dx, r["z"] + dz
                        if r["entrance"] not in moved:
                            moved.append(r["entrance"])
                        if t not in changed:
                            changed.append(t)
    for oo, name, rows in changed:
        if rows == oo.rows(name):
            ov.remove(oo.id, name)
        else:
            ov.set(oo.id, name, oo.tables[name]["kind"], rows)
    ov.save()
    generate(project.root, scenes, ov)
    return {"actor": actor, "x": x, "z": z, "arrivals_moved": sorted(moved)}


# ---- step spots: world cells whose code leads somewhere ---------------------------------

def _step_tables(project, scenes, names):
    from .doors import DoorEditor
    from .modgen import Overrides
    de = DoorEditor(project, scenes, names)
    sc = next(s for s in scenes.scenes if s["id"] == WORLD_SCENE)
    o = scenes.overlay(sc["overlay"])
    ov = Overrides(project.root)
    return de, o, ov


def _cells_with_code(world, code):
    return [(gx, gy) for gy in range(256) for gx in range(256) if (world.cell(gx, gy)[0] >> 16) & 0xFF == code]


def add_step(world, project, scenes, names, gx, gy, target_scene, target_entrance):
    """Make world cell (gx, gy) a step spot leading to the target: a free code
    in the cell, an exit event for it and the exit itself, as a door on a
    place's map is made (doors.py)."""
    from .doors import EVENT_EXIT
    from .sceneedit import EVENTS_END
    de, o, ov = _step_tables(project, scenes, names)
    de._check_target(target_scene, target_entrance)
    if not (0 <= gx < 256 and 0 <= gy < 256):
        raise ValueError(tr("cell {x},{y} is outside the world", x=gx, y=gy))
    if (world.cell(gx, gy)[0] >> 16) & 0xFF:
        raise ValueError(tr("Something already happens on that square. Pick another, or change that spot."))
    events = de._tables([o], ov, "events")
    exits = de._tables([o], ov, "exits")
    # Codes from 100 up are the town icons' triggers (100 + actor), so a new
    # spot takes a low code no event and no cell uses yet.
    taken = {r["trigger"] for _, _, rs in events for r in rs}
    taken |= {(w >> 16) & 0xFF for row in world.rows[:LAYER1 // 2] for w in row}
    code = next((c for c in range(1, ICON_TRIGGER) if c not in taken), None)
    used = {e["kind"] for _, _, segs in exits for s in segs for e in s.get("exits", [])}
    used |= {r["value"] for _, _, rs in events for r in rs if r["control"] & 0xF == EVENT_EXIT}
    kind = next((k for k in range(0xFE, 0, -1) if k not in used), None)
    if code is None or kind is None:
        raise ValueError(tr("The world map has no room for more step spots."))
    for _, _, rows in events:
        end = next(i for i, r in enumerate(rows) if r["control"] == EVENTS_END)
        rows.insert(end, {"control": EVENT_EXIT, "trigger": code, "condition": -1, "value": kind})
    de._set_exit(exits, WORLD_SCENE, kind, target_scene, target_entrance)
    apply_world_edits(world, [{"gx": gx, "gy": gy, "layer": 0, "code": code}])
    de._save(ov, events + exits)
    return {"code": code, "kind": kind, "label": names.scene_label(target_scene)}


def remove_step(world, project, scenes, names, gx, gy):
    """Clear the step spot at (gx, gy): every cell with its code, its exit
    event and its exit. Spots a scene script opens can't go."""
    from .doors import EVENT_EXIT
    de, o, ov = _step_tables(project, scenes, names)
    code = (world.cell(gx, gy)[0] >> 16) & 0xFF
    if not code:
        raise ValueError(tr("That square isn't a step spot."))
    events = de._tables([o], ov, "events")
    kind, scripted = de._exit_kind(events, code)
    if scripted:
        raise ValueError(tr("This spot is part of a story scene: you can change where it leads, but not remove it."))
    if kind is not None:
        exits = de._tables([o], ov, "exits")
        for _, _, rows in events:
            rows[:] = [r for r in rows if not (r["trigger"] == code and r["control"] & 0xF == EVENT_EXIT)]
        if not any(r["control"] & 0xF == EVENT_EXIT and r["value"] == kind for _, _, rs in events for r in rs):
            for _, _, segs in exits:
                for seg in segs:
                    if seg.get("scene") == WORLD_SCENE:
                        seg["exits"] = [e for e in seg["exits"] if e["kind"] != kind]
        de._save(ov, events + exits)
    cells = _cells_with_code(world, code)
    apply_world_edits(world, [{"gx": x, "gy": y, "layer": 0, "code": 0} for x, y in cells])
    return {"code": code, "cells": len(cells)}


# ---- new town icons ------------------------------------------------------------------------

FIRST_MARKER_ACTOR = 11  # gWorldPicture_AreaMarkers' row i is actor 11 + i (world_picture.c)


def marker_rows(root):
    """How many actors the pause-screen map has a marker row for, from actor 11
    up: the rows of gWorldPicture_AreaMarkers before its -1 end."""
    import re
    with open(os.path.join(root, layout.AREA_MARKERS), encoding="utf-8") as f:
        text = f.read()
    at = text.find(layout.AREA_MARKERS_LABEL + ":")
    if at < 0:
        raise ValueError(tr("Can't find the pause-screen map's markers ({path}).", path=layout.AREA_MARKERS))
    rows = 0
    for line in text[at:].splitlines()[1:]:
        m = re.match(r"\s*\.4byte\s+([^,]+),", line)
        if not m:
            if line.strip() and not line.strip().startswith(("@", "//", "/*")):
                break
            continue
        if m.group(1).strip() == "-1":
            break
        rows += 1
    return rows


def icon_sprites(project, scenes, names):
    """The sprites the game's own town icons use, with their names, commonest first."""
    from collections import Counter
    from .doors import DoorEditor
    de = DoorEditor(project, scenes, names)
    sc = next(s for s in scenes.scenes if s["id"] == WORLD_SCENE)
    o = scenes.overlay(sc["overlay"])
    main = o.rows(layout.WORLD_PLACEMENTS)
    counts = Counter(r["sprite"] for r in main if r["sprite"] > 7 and (r["x"] or r["z"]))
    return [{"sprite": sp, "name": names.sprite_name(sp) or tr("Sprite {n}", n=sp)} for sp, _ in counts.most_common()]


def add_icon(world, project, scenes, names, x, z, sprite, target_scene, target_entrance):
    """A new town icon at world px (x, z), leading to the target. Added after
    every other icon, so none renumbers; its trigger is 100 + its actor."""
    from .doors import EVENT_EXIT
    from .sceneedit import EVENTS_END, FIRST_ACTOR, MAX_ACTOR
    de, o, ov = _step_tables(project, scenes, names)
    de._check_target(target_scene, target_entrance)
    if not (0 <= x < 8192 and 0 <= z < 8192):
        raise ValueError(tr("that spot is outside the world"))
    if int(sprite) not in {s["sprite"] for s in icon_sprites(project, scenes, names)}:
        raise ValueError(tr("Pick one of the pictures the game's own towns use."))
    placements = de._tables([o], ov, "placements")
    main = next(r for _, name, r in placements if name == layout.WORLD_PLACEMENTS)
    end = next(i for i, r in enumerate(main) if r["sprite"] < 0)
    actor = FIRST_ACTOR + sum(1 for a in actor_numbers(main) if a >= FIRST_ACTOR)
    if actor > MAX_ACTOR:
        raise ValueError(tr("The world map already has as many icons as the game allows."))
    if actor < FIRST_MARKER_ACTOR + marker_rows(project.root):
        raise ValueError(tr("A new icon here would take another place's pause-screen marker."))
    trigger = ICON_TRIGGER + actor
    events = de._tables([o], ov, "events")
    exits = de._tables([o], ov, "exits")
    if any(r["trigger"] == trigger for _, _, rs in events for r in rs if r["control"] != EVENTS_END) or \
            any((w >> 16) & 0xFF == trigger for row in world.rows[:LAYER1 // 2] for w in row):
        raise ValueError(tr("The world map has no room for another icon."))
    used = {e["kind"] for _, _, segs in exits for s in segs for e in s.get("exits", [])}
    used |= {r["value"] for _, _, rs in events for r in rs if r["control"] & 0xF == EVENT_EXIT}
    kind = next((k for k in range(0xFE, 0, -1) if k not in used), None)
    if kind is None:
        raise ValueError(tr("The world map has no room for another icon."))
    like = next(r for r in main[:end] if r["sprite"] == int(sprite) and (r["x"] or r["z"]))
    main.insert(end, dict(like, sprite=int(sprite), condition=-1, x=int(x) << 16, z=int(z) << 16))
    for _, _, rows in events:
        e_end = next(i for i, r in enumerate(rows) if r["control"] == EVENTS_END)
        rows.insert(e_end, {"control": EVENT_EXIT, "trigger": trigger, "condition": -1, "value": kind})
    de._set_exit(exits, WORLD_SCENE, kind, target_scene, target_entrance)
    main_table = next(t for t in placements if t[1] == layout.WORLD_PLACEMENTS)
    de._save(ov, [main_table] + events + exits)
    return {"actor": actor, "trigger": trigger, "kind": kind, "label": names.scene_label(target_scene)}


def stock_icons(scenes):
    sc = next(s for s in scenes.scenes if s["id"] == WORLD_SCENE)
    stock = scenes.overlay(sc["overlay"]).rows(layout.WORLD_PLACEMENTS)
    return next((i for i, r in enumerate(stock) if r["sprite"] < 0), len(stock))


def remove_icon(world, project, scenes, names, actor):
    """Take away an icon the mod added, with its exit event and exit. Added
    icons after it move up a number, and their triggers follow them."""
    from .doors import EVENT_EXIT
    from .sceneedit import EVENTS_END
    de, o, ov = _step_tables(project, scenes, names)
    placements = de._tables([o], ov, "placements")
    main = next(r for _, name, r in placements if name == layout.WORLD_PLACEMENTS)
    numbers = actor_numbers(main)
    if int(actor) not in numbers:
        raise ValueError(f"no icon {actor}")
    row = numbers.index(int(actor))
    stock = stock_icons(scenes)
    if row < stock:
        raise ValueError(tr("This is one of the game's own places, so it can't be removed. You can move it, "
                            "or change where it leads."))
    events = de._tables([o], ov, "events")
    exits = de._tables([o], ov, "exits")
    trigger = ICON_TRIGGER + int(actor)
    kind, _ = de._exit_kind(events, trigger)
    del main[row]
    added = {ICON_TRIGGER + a for a in numbers[stock:]}  # only the mod's own icons renumber
    for _, _, rows in events:
        kept = []
        for r in rows:
            if r["control"] != EVENTS_END and r["control"] & 0xF == EVENT_EXIT and r["trigger"] in added \
                    and r["trigger"] >= trigger:
                if r["trigger"] == trigger:
                    continue
                r = dict(r, trigger=r["trigger"] - 1)
            kept.append(r)
        rows[:] = kept
    if kind is not None and not any(r["control"] & 0xF == EVENT_EXIT and r["value"] == kind
                                    for _, _, rs in events for r in rs):
        for _, _, segs in exits:
            for seg in segs:
                if seg.get("scene") == WORLD_SCENE:
                    seg["exits"] = [e for e in seg["exits"] if e["kind"] != kind]
    main_table = next(t for t in placements if t[1] == layout.WORLD_PLACEMENTS)
    de._save(ov, [main_table] + events + exits)
    return {"actor": int(actor)}
