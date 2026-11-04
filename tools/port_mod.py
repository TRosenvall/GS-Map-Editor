"""Carry the debug hub and sandbox from the old mod branch to the new layout.

A one-off: gsmod/debug-menu was built on alchemy e123af37, whose map files and
symbol names have since changed. This reads that branch with `git show` and
writes the same content into a checkout of the new layout, which has already
been built (its overlays name the scene tables):

  - maps 172 and 173: their grids, cell pictures, shapes and chests;
  - gMaps rows 178 and 179, the sandbox's tile set and its directory rows;
  - the messages the hub and the editor added;
  - overrides.json, its tables renamed by their address, which didn't change
    since both versions build the same game; then mod.c from it.

The C hooks are ordinary commits on the new branch, not made here.

Run: python3 tools/port_mod.py OLD_CHECKOUT OLD_BUILT_STOCK NEW_CHECKOUT
"""

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from gsmap import grid as gridmod  # noqa: E402
from gsmap import table as tablemod  # noqa: E402
from gsmap.modgen import Overrides, generate  # noqa: E402
from gsmap.project import Markers, Project  # noqa: E402
from gsmap.scenes import Scenes, readelf_symbols, table_kind  # noqa: E402
from gsmap.setup import build_env  # noqa: E402
from gsmap.tileset import table_hash  # noqa: E402

BRANCH = "gsmod/debug-menu"
BASE = "e123af37b41e4d91467ca38188c0b0826cd2aeee"
MAPS = "games/tbs/src/map"
PO_BLOCKS = re.compile(r"# gsmod: debug hub messages BEGIN.*# gsmod: editor messages END\n", re.S)
SHEETS = ("palette", "tiles_a", "tiles_b", "tiles_c", "tiles_d")


def old_plane(text):
    """An old grid_<plane>.tsv's rows, its fill and its size."""
    head, _, body = text.partition("\n")
    m = re.match(r"cell:\w+\tgrid:(\d+)x(\d+)\tfill:([0-9a-f]+)\tat:(\d+),(\d+)$", head)
    w, h, fill, ax, ay = int(m[1]), int(m[2]), int(m[3], 16), int(m[4]), int(m[5])
    cells = [[fill] * w for _ in range(h)]
    for i, row in enumerate(body.split("\n")):
        for j, v in enumerate(row.split()):
            cells[ay + i][ax + j] = int(v, 16)
    return cells, fill, w, h


def main(old, old_stock, new):
    def show(path, ref=BRANCH):
        return subprocess.run(["git", "-C", old, "show", f"{ref}:{path}"], capture_output=True, check=True).stdout

    def text(path, ref=BRANCH):
        return show(path, ref).decode("utf-8")

    def write(path, data):
        full = os.path.join(new, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode("utf-8"))

    # ---- the two maps -------------------------------------------------------------
    for n in ("172", "173"):
        folder = f"{MAPS}/map_{n}"
        planes = {p: old_plane(text(f"{folder}/grid_{p}.tsv")) for p in gridmod.PLANES}
        w, h = planes["metatile"][2:]
        grid = gridmod.MapGrid(w, h, tuple(planes[p][1] for p in gridmod.PLANES))
        for p in gridmod.PLANES:
            grid.planes[p] = planes[p][0]
        write(f"{folder}/map.txt", grid.to_text())
        write(f"{folder}/cell_pictures.tsv", text(f"{folder}/metatiles.tsv"))
        shapes = tablemod.parse(text(f"{folder}/shapes.tsv"))
        write(f"{folder}/shapes.tsv", "\n".join(
            ["\t".join(f"{a}:{b}" for a, b in shapes.columns)] +
            ["\t".join(str(v) for v in r) for r in shapes.rows]) + "\n")
        s = open(os.path.join(new, folder, "map.s"), encoding="utf-8").read()
        for table in ("cell_pictures.delta0.lz", "shapes.table.lz", "map.grid.lz"):
            s = s.replace(f"{MAPS}/map_001/{table}", f"{folder}/{table}")
        if n == "173":
            s = s.replace("""map_header 0, 0, 64, 64, 3, 0, 0, 0, 2, 2, 0, 0
	map_layer 0, 0, 16, 16, 0, 0, 0xff, 0xff
	map_layer 0, 0, 16, 16, 0, 0, 0xff, 0xff
	map_layer 0, 0, 16, 16, 0, 0, 0xff, 0xff""", """map_header 0, 0, 64, 64, 3, 2, 1, 1, 2, 2, 0, 0
	map_layer 0, 0, 16, 16, 0, 0, 0xff, 0xff
	map_layer 64, 0, 16, 16, 0, 0, 0xff, 0xff
	map_layer 128, 0, 16, 16, 0, 0, 0xff, 0xff""")
            tail = text(f"{folder}/map.s")
            s = s.rstrip("\n") + "\n" + tail[tail.index("\n@ gs-mapedit: the debug sandbox's own"):]
        write(f"{folder}/map.s", s)
        markers = Markers(os.path.join(new, folder, "map.s"))
        if n == "173":
            for row in tablemod.parse(text(f"{folder}/markers.tsv")).rows[:-1]:
                markers.insert(len(markers.rows) - 1, row)
            markers.save()

    # ---- which art they draw: gMaps rows and the sandbox's tile set ---------------
    old_rows = [[int(v, 0) for v in line.split("\t")] for line in text("games/tbs/src/field/layered.tsv").strip().split("\n")[1:]]
    maps_c = os.path.join(new, "games/tbs/src/map/maps.c")
    s = open(maps_c, encoding="utf-8").read()
    found = list(re.finditer(r"\{\{([^{}]+)\}\}", s))
    for row in (179, 178):  # later first, so earlier spans stay valid
        m = found[row]
        s = s[:m.start()] + "{{" + ", ".join(str(v) for v in old_rows[row]) + "}}" + s[m.end():]
    write("games/tbs/src/map/maps.c", s)
    for sheet in SHEETS:
        path = f"games/tbs/src/graphics/tileset/set_sandbox/{sheet}.png"
        write(path, show(path))
    directory = os.path.join(new, "games/tbs/src/gamepak/resource_directory.s")
    s = open(directory, encoding="utf-8").read()
    assert "\tunused 25\n" in s
    rows = "".join(f"\tresource , Tileset_Sandbox{t}\n" for t in ("Palette", "TilesA", "TilesB", "TilesC", "TilesD"))
    write("games/tbs/src/gamepak/resource_directory.s",
          s.replace("\tunused 25\n", "\t@ gs-mapedit: the debug sandbox's tile set\n" + rows + "\tunused 20\n"))

    # ---- messages -----------------------------------------------------------------
    old_en = text("games/tbs/text/en.po")
    for lang in ("en", "de", "es", "fr", "it"):
        path = os.path.join(new, f"games/tbs/text/{lang}.po")
        s = open(path, encoding="utf-8").read()
        s, hits = re.subn(r'(msgid "00074"\nmsgstr )"[^"]*"', r'\1"Debug"', s)
        assert hits == 1, lang
        if lang == "en":
            s = s.rstrip("\n") + "\n\n" + PO_BLOCKS.search(old_en).group(0)
        write(f"games/tbs/text/{lang}.po", s)

    # ---- editor files -------------------------------------------------------------
    write("games/tbs/src/mod/names.json", show("games/tbs/src/mod/names.json"))
    old_over = json.loads(text("games/tbs/src/mod/overrides.json"))
    project, scenes = Project(new), Scenes(new)
    over = Overrides(new)
    over.data = {"version": old_over.get("version", 1), "scenes": old_over.get("scenes", {}), "tables": {}}
    env = build_env()
    os.environ["PATH"] = env["PATH"]
    for t in old_over["tables"].values():
        old_elf = os.path.join(old_stock, "out/tbs-en/overlays", f"resource_{t['overlay']:x}.elf")
        addr = readelf_symbols(old_elf)[t["symbol"]][0]
        o = scenes.overlay(t["overlay"])
        name = next(n for n, x in o.tables.items() if x["addr"] == addr and x["kind"] == table_kind(n))
        print(f"{t['symbol']} -> {name}")
        over.set(t["overlay"], name, t["kind"], t["rows"])
    over.save()
    generate(new, scenes, over)

    # A stamp family is a hash of the table it was copied from: find that table
    # by its old hash, and record its new one.
    meta = json.loads(text("games/tbs/src/mod/tilesets.json"))
    for number, entry in meta.items():
        size = entry["family_size"]
        for info in project.maps.values():
            old_path = f"{MAPS}/{os.path.basename(info.folder)}/metatiles.tsv"
            try:
                lines = text(old_path, BASE).split("\n")
            except subprocess.CalledProcessError:
                continue
            import hashlib
            if hashlib.sha1("\n".join(lines).encode()).hexdigest()[:16] == entry["family"]:
                entry["family"] = table_hash(info.source("CELL_PICTURES", "cell_pictures.tsv"))
                print(f"map {number}: stamp family is map {info.number}'s, {size} blocks")
                break
        else:
            raise SystemExit(f"map {number}: no map has its family's table")
    write("games/tbs/src/mod/tilesets.json", json.dumps(meta, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:4])
