"""Old-layout map files to alchemy's table files (gsmap/legacy_maps.py), which
the in-app update uses to carry a player's map changes across.

Run: python3 tests/legacy_maps.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from gsmap import legacy_maps as lm  # noqa: E402
from gsmap.update import merge_rows  # noqa: E402

failures = []


def check(what, ok, info=""):
    print(("ok   " if ok else "FAIL ") + what + ("" if ok else f"  ({info})"))
    if not ok:
        failures.append(what)


# A 3x2 grid: a picture with a layer marker and priority, a wall, a shape.
grid = "grid:3x2\tat:0,0\tfill:fff:0:0\n9005 fff:255\nfff fff fff:0:4\n"
t = lm.grid_tables(grid)
check("the picture keeps its low twelve bits", t["grid_picture.tsv"] == "0\t1\t2\n5\t4095\t4095\n4095\t4095\t4095\n",
      t["grid_picture.tsv"])
check("behavior and shape are their own grids",
      t["grid_behavior.tsv"].split("\n")[1] == "0\t255\t0" and t["grid_shape.tsv"].split("\n")[2] == "0\t0\t4")
check("the top nibble becomes the cell's layer and priority", t["grid_actors.tsv"] == "column\trow\tlayer\tpriority\n0\t0\t1\t2\n",
      t["grid_actors.tsv"])
check("no actors file for a grid with none", lm.grid_tables("grid:1x1\tat:0,0\tfill:1:0:0\n")["grid_actors.tsv"] is None)
check("an edition's grid keeps its suffix", "grid_shape_es.tsv" in lm.convert("map_es.txt", grid))

cells = "top_left:u16\ttop_right:u16\tbottom_left:u16\tbottom_right:u16\n0x1c4\t0x9045\t0x1e4\t0x1e5\n0xc12\t0\t0\t0\n"
check("a tile word becomes tile, flip and palette", lm.cell_tiles(cells).split("\n")[1:3] == [
    "452\t\t0\t69\t\t9\t484\t\t0\t485\t\t0", "18\thv\t0\t0\t\t0\t0\t\t0\t0\t\t0"], lm.cell_tiles(cells))
check("shapes lose their column types", lm.shapes("shape:u8\theight0:u8\n0\t24\n") == "shape\theight0\n0\t24\n")

# A map file whose chests the editor saved in the English branch only.
inc = """Field_X:
\tmap_header 0, 0, 60, 188, 3, 2, 1, 1, 2, 2, 0, 0
\tmap_layer 0, 0, 16, 16, 0, 0, 0xff, 0xff
\tmap_layer 60, 0, 16, 16, 0, 0, 0xff, 0xff
\tmap_layer 120, 0, 16, 16, 0, 0, 0xff, 0xff
\t.ifdef TBS_EDITION_EN
\ttreasure_spot 24, 55, 100
\ttreasure_spot 12, 40, 150
\ttreasure_spots_end
\t.else
\ttreasure_spot 24, 55, 100
\ttreasure_spots_end
\t.endif
"""
out = lm.convert("map.inc", inc)
check("the header is one row", out["header.tsv"].split("\n")[1] == "0\t0\t60\t188\t3\t2\t1\t1\t2\t2\t0\t0")
check("layers are three rows", out["layers.tsv"].count("\n") == 4 and "\n60\t0\t16\t16\t0\t0\t255\t255\n" in out["layers.tsv"])
spots = lm.read_spots(out["spots.tsv"])
check("chests that differ by edition are kept per edition",
      spots["en"] == [[24, 55, 100], [12, 40, 150]] and spots["ja"] == [[24, 55, 100]], out["spots.tsv"])
same = lm.convert("map.inc", inc.replace("\ttreasure_spot 12, 40, 150\n", ""))["spots.tsv"]
check("chests every edition shares are plain rows", same == "column\trow\tsubject\tedition\n24\t55\t100\n", same)
check("no spots file for a map with no chests", lm.spots_table({e: [] for e in lm.EDITIONS}) is None)
try:
    lm.convert("map.inc", inc.replace("\tmap_layer 120,", "\t.ifeq EDITION_INTERNATIONAL\n\tmap_layer 121, 0, 16, 16, 0, 0, 0xff, 0xff\n"
                                      "\t.else\n\tmap_layer 120, 0, 16, 16, 0, 0, 0xff, 0xff\n\t.endif\n\tmap_layer 120,"))
    check("layers that differ by edition are refused", False)
except ValueError:
    check("layers that differ by edition are refused", True)

# The update's merge, per edition: the new version's rows, less what the
# player removed, plus what they added.
theirs = lm.read_spots("column\trow\tsubject\tedition\n24\t55\t100\n53\t56\t101\n")
base = {e: [[24, 55, 100], [53, 56, 101]] for e in lm.EDITIONS}
mine = dict(base, en=[[24, 55, 100], [12, 40, 150]])
merged = {e: merge_rows(base[e], mine[e], theirs[e], [])[:-1] for e in lm.EDITIONS}
check("a chest the player moved in English moves only there",
      merged["en"] == [[24, 55, 100], [12, 40, 150]] and merged["de"] == [[24, 55, 100], [53, 56, 101]], merged)

print("all ok" if not failures else f"{len(failures)} FAILED")
sys.exit(1 if failures else 0)
