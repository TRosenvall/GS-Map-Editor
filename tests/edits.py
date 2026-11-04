"""Saved edits reach map.txt and read back, on a copy of real maps.

Run: python3 tests/edits.py [path/to/alchemy]
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gsmap.project import Project  # noqa: E402

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

sys.exit(1 if failed else 0)
