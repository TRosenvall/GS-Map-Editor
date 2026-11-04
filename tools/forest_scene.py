"""NOT PORTED: written for the alchemy layout before map.txt; kept as a record of
how the hub and sandbox were made. tools/port_mod.py carried their result over.

Paint a small forest scene in the debug sandbox (map 173) by stamping
real tree groups from Vale (map 002), all three layers plus collision and
height. The sandbox carries Vale's exact block list, so block numbers copy
one to one. Saved through Project.apply_edits, the editor's save path.

Run from gs-mapedit:  python3 tools/forest_scene.py [--root ~/gs_project/alchemy]
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from gsmap.project import Project  # noqa: E402

SANDBOX, VALE = "173", "002"
GRASS_UPPER = 28  # the plain grass Vale's upper layers hold almost everywhere
TREE_SHARE = 0.30  # a block is tree when this share of its pixels isn't grass-coloured

# Stamps: (left, top, width, height) in Vale's visible cells, each a group of
# whole trees on open grass.
STAMPS = {
    "mixed": (1, 77, 7, 7),    # green, red and blue trees
    "pair": (15, 54, 5, 6),    # a red and a blue tree
    "grove": (18, 78, 7, 6),   # green and teal trees
    "red": (25, 80, 3, 4),     # one autumn tree
}

# Where each stamp goes in the 32x32 sandbox (its wall is row/column 0 and
# 31; the party arrives at (12, 12) and the way back is at (12, 14)).
LAYOUT = [
    ("mixed", 1, 1), ("grove", 9, 1), ("pair", 16, 1), ("grove", 23, 1),
    ("pair", 1, 9), ("red", 1, 16), ("mixed", 1, 21),
    ("grove", 24, 9), ("pair", 25, 16), ("red", 26, 23),
    ("grove", 9, 25), ("pair", 17, 25), ("red", 23, 27),
    ("red", 18, 10),  # an accent in the clearing
]
KEEP_CLEAR = {(12, 12), (12, 14)}
# Stamp cells that pass the colour test but aren't trees (a cliff corner).
SKIP = {"mixed": {(6, 6)}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser("~/gs_project/alchemy"))
    args = ap.parse_args()
    project = Project(args.root)
    sb, vale = project.maps[SANDBOX], project.maps[VALE]

    src = {
        "block": project.resolved_blocks(vale),
        "collision": project.load_grid(vale, "collision").cells,
        "shape": project.load_grid(vale, "shape").cells,
    }
    cur = {
        "block": project.resolved_blocks(sb),
        "collision": project.load_grid(sb, "collision").cells,
        "shape": project.load_grid(sb, "shape").cells,
    }
    # Which upper-layer blocks are tree (foliage, trunk, shadow) rather than
    # grass or a thin edge stroke: share of pixels far from Vale's grass colour.
    atlas = project.metatile_atlas(vale, vale.char_base[1])

    def pixels(b):
        t = atlas.crop(((b % 32) * 16, (b // 32) * 16, (b % 32) * 16 + 16, (b // 32) * 16 + 16))
        return [q[:3] for q in t.getdata() if q[3]]

    grass_px = pixels(GRASS_UPPER)
    gm = [sum(c[i] for c in grass_px) / len(grass_px) for i in range(3)]
    tree_cache = {}

    def is_tree(b):
        if b not in tree_cache:
            px = pixels(b)
            far = sum(1 for c in px if sum((c[i] - gm[i]) ** 2 for i in range(3)) > 70 ** 2)
            tree_cache[b] = bool(px) and far / len(px) > TREE_SHARE
        return tree_cache[b]

    w, h = sb.size
    # Start from the sandbox as made by debug_hub.py (no earlier stamps), so
    # reruns don't pile up.
    edits = {}
    u1, u2 = project.layer_origin(vale, 1), project.layer_origin(vale, 2)
    for name, dx, dy in LAYOUT:
        sx, sy, sw, shh = STAMPS[name]
        for j in range(shh):
            for i in range(sw):
                x, y = dx + i, dy + j
                if not (1 <= x < w - 1 and 1 <= y < h - 1) or (x, y) in KEEP_CLEAR:
                    continue  # keep the wall, the arrival point and the way back
                if (i, j) in SKIP.get(name, ()):
                    continue
                # Only tree cells: where an upper layer holds more than grass.
                vx, vy = sx + i, sy + j
                b1 = src["block"][u1[1] + vy][u1[0] + vx] & 0xFFF
                b2 = src["block"][u2[1] + vy][u2[0] + vx] & 0xFFF
                if not (is_tree(b1) or is_tree(b2)):
                    continue
                for li in range(3):
                    ox, oy = project.layer_origin(vale, li)
                    tx, ty = project.layer_origin(sb, li)
                    for plane, grid in src.items():
                        v = grid[oy + sy + j][ox + sx + i]
                        gx, gy = tx + x, ty + y
                        if cur[plane][gy][gx] != v:
                            edits[(plane, gx, gy)] = v
    result = project.apply_edits(sb, [
        {"plane": p, "x": x, "y": y, "value": v} for (p, x, y), v in edits.items()
    ])
    print(f"{len(edits)} cell changes; saved", [os.path.relpath(p, args.root) for p in result["saved"]])
    for wmsg in result["warnings"]:
        print("warning:", wmsg)
    img = Project(args.root).render(project.maps[SANDBOX])
    out = os.path.join(HERE, "..", "docs", "sandbox-forest.png")
    img.resize((img.width * 2, img.height * 2)).save(out)
    print("preview", os.path.relpath(out, os.path.join(HERE, "..")))


if __name__ == "__main__":
    main()
