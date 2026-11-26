"""Carry the debug hub and sandbox from the editor-port branch to alchemy's
table-file maps (9bf56b6993 and later).

A one-off, as each layout change is: the branch was built on alchemy
0240eeebad, whose maps are map.inc, map.txt and cell_pictures.tsv. Since then
a map is a folder of TSVs (header, layers, contents, spots, grid_picture,
grid_behavior, grid_shape, grid_actors, cell_tiles, shapes) that ags-maps
turns into assembly, the map list is map/resources.s, and resources are named
by symbol in gamepak/resource_directory.s. This reads the branch with
`git show` and writes the same content into a checkout of the new layout:

  - test_0 and test_1: their grids, cell tiles, shapes, header, layers and
    chests, each in its own files rather than the empty map's;
  - the map list's Test0 and Test1 rows: Sol Sanctum's tile set for test_0,
    the sandbox's own for test_1;
  - the sandbox's tile set (graphics/tileset/sandbox) and its directory rows;
  - the messages the hub and the editor added, and message 74, "Debug";
  - the mod folder's own files: mod_features.h, names.json, tilesets.json and
    overrides.json (scene tables keep their overlay numbers and names; each
    is checked by its address in the new build).

The C hooks are ordinary commits on the new branch, not made here. The new
checkout must have been built once (its overlays' symbols are read).

Run: python3 tools/port_mod.py OLD_CHECKOUT NEW_CHECKOUT
"""

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from gsmap import legacy_maps  # noqa: E402

BRANCH = "gsmod/editor-port"
MAPS = "games/tbs/src/map"
TILESETS = "games/tbs/src/graphics/tileset"
PO_BLOCKS = re.compile(r"\n# gsmod: debug hub messages BEGIN.*# gsmod: editor messages END\n", re.S)
SHEETS = ("palette", "tiles_a", "tiles_b", "tiles_c", "tiles_d")


def main(old, new):
    def show(path):
        return subprocess.run(["git", "-C", old, "show", f"{BRANCH}:{path}"], capture_output=True, check=True).stdout

    def text(path):
        return show(path).decode("utf-8")

    def read(path):
        with open(os.path.join(new, path), encoding="utf-8") as f:
            return f.read()

    def write(path, data):
        full = os.path.join(new, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode("utf-8"))

    # ---- the two maps -------------------------------------------------------------
    for folder in ("test_0", "test_1"):
        here = f"{MAPS}/{folder}"
        for old_name in ("map.txt", "cell_pictures.tsv", "shapes.tsv", "map.inc"):
            for name, table in legacy_maps.convert(old_name, text(f"{here}/{old_name}")).items():
                if table is not None:
                    write(f"{here}/{name}", table)
        # Its own tables, where the stock test maps borrow the empty map's.
        contents = read(f"{here}/contents.tsv")
        for block in ("cell_tiles", "shapes", "grid"):
            contents = re.sub(rf"^{block}\tempty_map/", f"{block}\t", contents, flags=re.M)
        write(f"{here}/contents.tsv", contents)

    # ---- which art they draw: the map list's rows and the sandbox's tile set -------
    resources = read(f"{MAPS}/resources.s")
    for row, sheets in (("Test0", "SolSanctumLunaSolRooms"), ("Test1", "Sandbox")):
        line = re.search(rf"^\tmap {row}, Field_{row}, .*$", resources, re.M)
        parts = ", ".join(f"Tileset_{sheets}{p}" for p in ("Palette", "TilesA", "TilesB", "TilesC", "TilesD"))
        new_line = re.sub(r"Tileset_\w+Palette, .*?TilesD", parts, line.group(0))
        resources = resources.replace(line.group(0), new_line)
    write(f"{MAPS}/resources.s", resources)

    # The sheets follow test_1's placeholder ones (placed.tsv, which ags-maps
    # writes after any tilesets.tsv), and take the first free directory rows,
    # where the branch had them, so the ROM comes out as it did.
    for sheet in SHEETS:
        write(f"{TILESETS}/sandbox/{sheet}.png", show(f"{TILESETS}/set_sandbox/{sheet}.png"))
    placed = read(f"{MAPS}/test_1/placed.tsv")
    placed += "".join(f"Tileset_Sandbox{name}\t../graphics/tileset/sandbox/{sheet}.{form}\t\t4\n"
                      for name, sheet, form in (("Palette", "palette", "gbapal.lz"), ("TilesA", "tiles_a", "4bpp.mtf"),
                                                ("TilesB", "tiles_b", "4bpp.mtf"), ("TilesC", "tiles_c", "4bpp.mtf"),
                                                ("TilesD", "tiles_d", "4bpp.mtf")))
    write(f"{MAPS}/test_1/placed.tsv", placed)

    directory = read("games/tbs/src/gamepak/resource_directory.s")
    free = "\tresource , 0\n" * 5
    at = directory.index(free, directory.rindex("\toverlay "))
    rows = "\t@ gs-mapedit: the debug sandbox's tile set\n" + "".join(
        f"\tmap_resource Tileset_Sandbox{t}\n" for t in ("Palette", "TilesA", "TilesB", "TilesC", "TilesD"))
    write("games/tbs/src/gamepak/resource_directory.s", directory[:at] + rows + directory[at + len(free):])

    # ---- messages -----------------------------------------------------------------
    old_en = text("games/tbs/text/en.po")
    for lang in ("en", "de", "es", "fr", "it"):
        path = f"games/tbs/text/{lang}.po"
        s = read(path)
        s, hits = re.subn(r'(msgid "00074"\nmsgstr )"[^"]*"', r'\1"Debug"', s)
        assert hits == 1, lang
        if lang == "en":
            s = s.rstrip("\n") + "\n" + PO_BLOCKS.search(old_en).group(0)
        write(path, s)

    # ---- the mod folder -----------------------------------------------------------
    for name in ("mod_features.h", "names.json", "tilesets.json", "overrides.json"):
        write(f"games/tbs/src/mod/{name}", show(f"games/tbs/src/mod/{name}"))
    over = json.loads(text("games/tbs/src/mod/overrides.json"))
    old_out = os.path.join(old, "out/tbs-en")
    new_out = os.path.join(new, "out/tbs-en")
    names = {int(m[1], 16): m[2] for m in re.finditer(r"^([0-9a-f]+) A OverlayId_(\w+)$", subprocess.run(
        ["arm-none-eabi-nm", os.path.join(new_out, "tbs-en.elf")], capture_output=True, text=True).stdout, re.M)}
    for t in over["tables"].values():
        def address(elf):
            out = subprocess.run(["arm-none-eabi-nm", elf], capture_output=True, text=True, check=True).stdout
            return re.search(rf"^([0-9a-f]+) \w {t['symbol']}$", out, re.M)[1]
        was = address(os.path.join(old_out, "overlays", f"resource_{t['overlay']:x}.elf"))
        now = address(os.path.join(new_out, "overlays", f"{names[t['overlay']]}.elf"))
        print(f"{t['overlay']:x}:{t['symbol']} {was} -> {names[t['overlay']]} {now}")
        assert was == now, "the table moved: match it by content before carrying the edit"


if __name__ == "__main__":
    main(*sys.argv[1:3])
