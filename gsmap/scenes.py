"""Scenes and their overlay tables, read from a built edition.

Tables are read as bytes from each scene overlay's built image
(out/<edition>/overlays/resource_<id>.bin, loaded at gOverlayArea =
0x02008000) using the overlay ELF's symbols. This gives exact values, with
no C macros to evaluate. Layouts are from games/tbs/include/field/scene.h and
scene_tables.h, and the exit walk is Scene_TakeExit (system/main_routine.c).
"""

import os
import re
import struct

from . import layout

OVERLAY_BASE = 0x02008000
KINDS = ("entrances", "exits", "placements", "events", "regions")
# Offsets of the getter pointers in struct SceneEntryPoints (field/scene.h).
# The editor's kinds keep their own names: "placements" are the game's actor
# placements and "events" its triggers.
GETTER_OFFSETS = {"entrances": 0x0C, "exits": 0x14, "placements": 0x1C, "events": 0x24, "regions": 0x2C}

EXIT_SCENE_MASK = 0xFFF
EXIT_HAS_FLAG = 0x10000000
EXIT_TABLE_END = 0x1FF


ENTRY = struct.Struct("<IIIBBH")  # an ELF32 symbol


def readelf_symbols(elf):
    """{name: (value, size, "FUNC"|"OBJECT")} of an ELF's defined symbols, read
    directly: a scene overlay is opened often, and there are 200 of them."""
    with open(elf, "rb") as f:
        data = f.read()
    shoff, = struct.unpack_from("<I", data, 32)
    shentsize, shnum = struct.unpack_from("<HH", data, 46)
    sections = [struct.unpack_from("<10I", data, shoff + i * shentsize) for i in range(shnum)]
    syms = {}
    kinds = {1: "OBJECT", 2: "FUNC"}
    for sec in sections:
        if sec[1] != 2:  # SHT_SYMTAB
            continue
        strings = sections[sec[6]]
        first, end, step = sec[4], sec[4] + sec[5], sec[9]
        if step == ENTRY.size:  # as ELF32 always has it: read them in one go
            entries = ENTRY.iter_unpack(data[first:end - (end - first) % step])
        else:
            entries = (ENTRY.unpack_from(data, off) for off in range(first, end, step))
        for name, value, size, info, _, shndx in entries:
            kind = kinds.get(info & 15)
            if kind and shndx not in (0, 0xFFF1):
                start = strings[4] + name
                syms[data[start:data.index(b"\0", start)].decode()] = (value, size, kind)
    return syms


def table_kind(symbol):
    for kind, word in layout.TABLE_WORDS:
        if word in symbol:
            return kind
    return None


# ---- row codecs: bytes <-> dicts of named integer fields ---------------------

ENTRANCE = struct.Struct("<hhhhhHhhhhhh")
ENTRANCE_FIELDS = ("entrance", "requiredFlag", "x", "y", "z", "facing", "unused1",
                   "cameraLeft", "cameraTop", "cameraRight", "cameraBottom", "unused2")
PLACEMENT = struct.Struct("<hhiiiiHBB")
PLACEMENT_FIELDS = ("sprite", "condition", "behavior", "x", "y", "z", "facing", "talkFacing", "flags")
EVENT = struct.Struct("<IhhI")
EVENT_FIELDS = ("control", "trigger", "condition", "value")
REGION = struct.Struct("<hhhhhhhh")  # struct SceneExitRegion (field/scene.h): a box that is an exit
REGION_FIELDS = ("minX", "minY", "minZ", "maxX", "maxY", "maxZ", "condition", "value")

LAYOUTS = {
    "entrances": (ENTRANCE, ENTRANCE_FIELDS),
    "placements": (PLACEMENT, PLACEMENT_FIELDS),
    "events": (EVENT, EVENT_FIELDS),
    "regions": (REGION, REGION_FIELDS),
}


def decode_rows(kind, data):
    if kind == "exits":
        return decode_exits(data)
    st, fields = LAYOUTS[kind]
    return [dict(zip(fields, st.unpack_from(data, i))) for i in range(0, len(data) - st.size + 1, st.size)]


def encode_rows(kind, rows):
    if kind == "exits":
        return encode_exits(rows)
    st, fields = LAYOUTS[kind]
    return b"".join(st.pack(*(int(r[f]) for f in fields)) for r in rows)


def decode_exits(data):
    """Exit words as a list of segments: {"scene": header, "exits": [...]}.
    Words that are neither headers nor in a segment are kept as "raw"."""
    words = list(struct.unpack_from(f"<{len(data) // 4}I", data))
    segs, i = [], 0
    while i < len(words):
        w = words[i]
        i += 1
        if w & ~EXIT_SCENE_MASK:  # an exit word outside any header: keep it raw
            segs.append({"raw": w})
            continue
        seg = {"scene": w & EXIT_SCENE_MASK, "exits": []}
        segs.append(seg)
        if seg["scene"] == EXIT_TABLE_END:
            break
        while i < len(words) and words[i] & ~EXIT_SCENE_MASK:
            w = words[i]
            i += 1
            ex = {
                "kind": (w & 0x0FF00000) >> 20,
                "entrance": (w & 0xFF000) >> 12,
                "scene": w & EXIT_SCENE_MASK,
                "flag": None,
                "extra": w & 0xE0000000,  # bits the engine ignores, kept verbatim
            }
            if w & EXIT_HAS_FLAG:
                ex["flag"] = words[i]
                i += 1
            seg["exits"].append(ex)
    # trailing words after the end marker (padding), kept verbatim
    for w in words[i:]:
        segs.append({"raw": w})
    return segs


def encode_exits(segs):
    words = []
    for seg in segs:
        if "raw" in seg:
            words.append(seg["raw"])
            continue
        words.append(seg["scene"])
        for ex in seg.get("exits", []):
            w = (ex["kind"] << 20) | (ex["entrance"] << 12) | ex["scene"] | ex.get("extra", 0)
            if ex.get("flag") is not None:
                words += [w | EXIT_HAS_FLAG, ex["flag"]]
            else:
                words.append(w & ~EXIT_HAS_FLAG)
    return struct.pack(f"<{len(words)}I", *words)


class Overlay:
    def __init__(self, ovl_id, elf, binary):
        self.id = ovl_id
        self.elf = elf
        self.image = open(binary, "rb").read()
        self.symbols = readelf_symbols(elf)
        self.getters = {
            k: struct.unpack_from("<I", self.image, off)[0] for k, off in GETTER_OFFSETS.items()
        }
        self.memo = {}  # answers worked out from this build of the overlay (sceneedit.scene_tables)
        self._funcs = None  # function address -> its first name, for getter_name
        self.tables = {}
        # In address order, the order the game's own source lays them out, so
        # "the scene's first table" doesn't depend on what symbols are named.
        for name, (addr, size, typ) in sorted(self.symbols.items(), key=lambda kv: kv[1][0]):
            kind = table_kind(name)
            if typ == "OBJECT" and kind and OVERLAY_BASE <= addr < OVERLAY_BASE + len(self.image):
                self.tables[name] = {"kind": kind, "addr": addr, "size": size}
        # Editable only when the bytes decode and re-encode exactly. A few
        # symbols named like tables hold other records or split tables.
        for name, t in self.tables.items():
            data = self.table_bytes(name)
            t["editable"] = encode_rows(t["kind"], decode_rows(t["kind"], data)) == data

    def table_bytes(self, name):
        t = self.tables[name]
        off = t["addr"] - OVERLAY_BASE
        return self.image[off: off + t["size"]]

    def rows(self, name):
        """The table's rows; shared, so copy them before changing any."""
        t = self.tables[name]
        if "rows" not in t:
            t["rows"] = decode_rows(t["kind"], self.table_bytes(name))
        return t["rows"]

    def getter_name(self, kind):
        if self._funcs is None:
            funcs = {}
            for name, (a, _, typ) in self.symbols.items():
                if typ == "FUNC":
                    funcs.setdefault(a & ~1, name)  # the first, as a search in symbol order finds
            self._funcs = funcs
        return self._funcs.get(self.getters[kind] & ~1)


class Scenes:
    """The scene table (field/scenes.s) and each scene's overlay, for one edition."""

    def __init__(self, root, edition="en"):
        self.root = root
        self.edition = edition
        self.out = os.path.join(root, "out", f"tbs-{edition}")
        self.scenes = self._read_scene_table()
        self._overlays = {}

    def _read_scene_table(self):
        path = os.path.join(self.root, layout.SCENE_TABLE)
        rows = []
        text = open(path, encoding="utf-8").read()
        # A scene's map is a number or an .equiv name (MapIndex_World).
        named = {n: int(v, 0) for n, v in re.findall(r"\.equiv\s+(\w+)\s*,\s*(\w+)", text) if re.fullmatch(r"\d+|0x[0-9a-fA-F]+", v)}
        for line in text.split("\n"):
            m = re.match(r"\s*scene\s+(\w*)\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)", line)
            if m:
                rows.append({
                    "id": len(rows),
                    "name": m.group(1) or None,
                    "overlay": int(m.group(2), 0),
                    "group": int(m.group(3), 0),
                    "variant": int(m.group(4), 0),
                    "layered_row": named[m.group(5)] if m.group(5) in named else int(m.group(5), 0),
                })
        return rows

    def overlay(self, ovl_id):
        base = os.path.join(self.out, "overlays", f"resource_{ovl_id:x}")
        try:
            stamp = os.stat(base + ".elf").st_mtime_ns
        except FileNotFoundError:
            raise FileNotFoundError(f"{base}.elf: build tbs-{self.edition} first") from None
        hit = self._overlays.get(ovl_id)
        if hit is None or hit[0] != stamp:  # a build replaces them
            hit = self._overlays[ovl_id] = (stamp, Overlay(ovl_id, base + ".elf", base + ".bin"))
        return hit[1]

    def for_rows(self, rows):
        """Scenes whose gMaps row is in `rows`."""
        return [s for s in self.scenes if s["layered_row"] in rows]
