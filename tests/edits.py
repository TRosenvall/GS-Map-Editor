"""Saved edits reach map.txt and read back, on a copy of real maps.

Run: python3 tests/edits.py [path/to/alchemy]
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gsmap.project import Project  # noqa: E402
from gsmap.walk import Walk  # noqa: E402

root = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/gs_project/alchemy-port")
failed = 0


def check(what, ok):
    global failed
    print(("ok   " if ok else "FAIL ") + what)
    failed += not ok


with tempfile.TemporaryDirectory() as tmp:
    src = os.path.join(tmp, "games/tbs/src")
    os.makedirs(src)
    shutil.copytree(os.path.join(root, "games/tbs/src/map"), os.path.join(src, "map"))
    shutil.copytree(os.path.join(root, "games/tbs/src/gamepak"), os.path.join(src, "gamepak"))
    for name in ("games/tbs/src/graphics",):
        os.symlink(os.path.join(root, name), os.path.join(tmp, name))
    p = Project(tmp)
    for number in ("002", "003", "107"):
        info = p.maps[number]
        before = p.resolved_blocks(info)
        x, y = info.bounds[0] // 2 + 3, info.bounds[1] // 2 + 3
        new = (before[y][x] & 0xFFF) ^ 1
        col = p.load_grid(info, "collision").cells[y][x]
        p.apply_edits(info, [
            {"plane": "block", "x": x, "y": y, "value": new},
            {"plane": "collision", "x": x + 1, "y": y, "value": 255},
            {"plane": "shape", "x": x + 2, "y": y, "value": 0},
        ])
        again = Project(tmp).maps[number]
        after = p.resolved_blocks(again)
        check(f"map {number}: block paint saved", after[y][x] & 0xFFF == new)
        others = sum(1 for r0, r1 in zip(before, after) for a, b in zip(r0, r1) if a != b)
        check(f"map {number}: no other block changed ({others} differ)", others == 1)
        check(f"map {number}: walkability saved", p.load_grid(again, "collision").cells[y][x + 1] == 255)
        check(f"map {number}: collision under the block untouched", p.load_grid(again, "collision").cells[y][x] == col)

    # New heights: only the painted ones are added, an identical row is reused,
    # and painted squares are renumbered to the rows saved.
    info = p.maps["002"]
    rows = p.shape_rows(info)
    base = len(rows)
    x, y = info.bounds[0] // 2 + 5, info.bounds[1] // 2 + 5
    out = p.apply_edits(info, [
        {"plane": "shape", "x": x, "y": y, "value": base + 1},
        {"plane": "shape", "x": x + 1, "y": y, "value": base + 2},
    ], new_shapes=[[0, 99, 0, 0], [1, 60, 62, 0], list(rows[0])])
    again = Project(tmp).maps["002"]
    saved = p.shape_rows(again)
    grid = p.load_grid(again, "shape").cells
    check("new height: only the painted one is added", len(saved) == base + 1 and saved[base] == [1, 60, 62, 0])
    check("new height: the square points at it", grid[y][x] == base)
    check("new height: an identical row is reused", grid[y][x + 1] == 0)
    check("new height: the editor is told the renumbering", out.get("remap") == {base + 1: base, base + 2: 0})
    try:
        p.apply_edits(info, [{"plane": "shape", "x": x, "y": y, "value": base + 9}], new_shapes=[[0, 1, 0, 0]])
        check("a height that was never made is refused", False)
    except ValueError:
        check("a height that was never made is refused", True)
    # Malformed new heights are refused with nothing written, not a crash.
    shapes_before = open(info.source("SHAPES", "shapes.tsv")).read()
    for bad in ({"0": [0, 1, 0, 0]}, [[0, 1, 0]], [[0, 300, 0, 0]], [[16, 1, 0, 0]], [["0", 1, 0, 0]],
                [[0, 1.5, 0, 0]], [5], [None]):
        try:
            p.apply_edits(info, [{"plane": "shape", "x": x, "y": y, "value": len(saved)}], new_shapes=bad)
            ok = False
        except ValueError:
            ok = True
        except Exception as e:  # noqa: BLE001
            ok, bad = False, f"{bad!r} ({type(e).__name__})"
        check(f"malformed new height {bad!r} is refused", ok)
    check("refused heights leave shapes.tsv alone", open(info.source("SHAPES", "shapes.tsv")).read() == shapes_before)
    check("refused heights leave the square alone", p.load_grid(Project(tmp).maps["002"], "shape").cells[y][x] == base)
    # Signed and unsigned samples name the same row.
    out = p.apply_edits(info, [{"plane": "shape", "x": x, "y": y, "value": len(saved)}],
                        new_shapes=[[3, -2, 254, 0]])
    for bad in ([5], "abc", [[0, 1, 0]]):
        try:
            Walk(p, info, [], [], shapes=bad)
            ok = False
        except ValueError:
            ok = True
        except Exception:  # noqa: BLE001
            ok = False
        check(f"walking checks refuse malformed new height {bad!r}", ok)
    check("negative levels are saved as the game's bytes", p.shape_rows(Project(tmp).maps["002"])[-1] == [3, -2, -2, 0])

    # Another save added a row after the editor numbered its new heights:
    # they are still read by the editor's own numbering, not the file's.
    p = Project(tmp)
    info = p.maps["002"]
    seen = len(p.shape_rows(info))
    p.apply_edits(info, [{"plane": "shape", "x": 10, "y": 10, "value": seen}], new_shapes=[[0, 77, 0, 0]])
    out = p.apply_edits(p.maps["002"], [{"plane": "shape", "x": 11, "y": 10, "value": seen}],
                        new_shapes=[[0, 88, 0, 0]], shapes_base=seen)
    rows = p.shape_rows(Project(tmp).maps["002"])
    v = p.load_grid(Project(tmp).maps["002"], "shape").cells[10][11]
    check("a height saved after the table grew elsewhere keeps its own level", rows[v] == [0, 88, 0, 0] and rows[seen] == [0, 77, 0, 0])
    try:
        p.apply_edits(p.maps["002"], [{"plane": "shape", "x": 12, "y": 10, "value": 999}],
                      new_shapes=[[0, 1, 0, 0]], shapes_base=999)
        check("a table smaller than the editor saw is refused", False)
    except ValueError:
        check("a table smaller than the editor saw is refused", True)

sys.exit(1 if failed else 0)
