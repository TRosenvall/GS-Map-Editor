"""Load and re-serialise every map grid, table and chest list; all must be identical.

Run: python3 tests/roundtrip.py [path/to/alchemy]
"""

import glob
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gsmap import grid, project, table, world  # noqa: E402

root = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/gs_project/alchemy-port")
maps = os.path.join(root, "games/tbs/src/map")

checked = failed = skipped = 0


def compare(path, text, out):
    global checked, failed
    checked += 1
    if out != text:
        failed += 1
        a, b = text.split("\n"), out.split("\n")
        line = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        print(f"MISMATCH {os.path.relpath(path, maps)} at line {line + 1}")


for path in sorted(glob.glob(f"{maps}/*/*.tsv") + glob.glob(f"{maps}/*/*.txt")):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    name = os.path.basename(path)
    if name == "blocks.tsv" and path.endswith("world/blocks.tsv"):
        out = world.format_blocks(world.parse_blocks(text))
    elif grid.is_grid_text(text):
        out = grid.parse(text).to_text()
    elif name.startswith(("cell_pictures", "shapes")):
        out = table.parse(text).to_text()
    else:
        skipped += 1
        continue
    compare(path, text, out)

# Chests live in map.s: saving an unchanged list must leave the file alone.
for path in sorted(glob.glob(f"{maps}/*/map.s")):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if "_MARKERS:" not in text:
        continue
    with tempfile.TemporaryDirectory() as d:
        copy = shutil.copy(path, os.path.join(d, "map.s"))
        project.Markers(copy).save()
        with open(copy, encoding="utf-8") as f:
            compare(path, text, f.read())

print(f"checked {checked}, mismatched {failed}, skipped (other formats) {skipped}")
sys.exit(1 if failed else 0)
