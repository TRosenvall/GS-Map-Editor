"""Where people can stand (gsmap/walk.py), checked against the game itself: the
people Camelot placed must be ones the party can talk to, and Imil, with its
ice and snowy ledges, must say what's wrong with a bad spot and how to fix it.

Run: python3 tests/placement.py [path/to/alchemy]
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gsmap.doors import DoorEditor  # noqa: E402
from gsmap.events import EventEditor  # noqa: E402
from gsmap.names import Names  # noqa: E402
from gsmap.project import Project  # noqa: E402
from gsmap.scenes import Scenes  # noqa: E402
from gsmap.walk import Walk, flat_shapes, height_at  # noqa: E402

root = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/gs_project/alchemy-port")
failed = 0


def check(what, ok, info=""):
    global failed
    print(("ok   " if ok else "FAIL ") + what + (f"  ({info})" if info and not ok else ""))
    failed += not ok


p, s, n = Project(root), Scenes(root), Names(root)
by_name = {x["name"]: x for x in s.scenes}


def walk(name):
    sc = by_name[name]
    info = next(m for m in p.maps.values() if sc["layered_row"] in {r["row"] for r in [m.resources] + m.alternates if r})
    d = EventEditor(p, s, n).describe(info, sc["id"])
    return info, d, Walk(p, info, d["events"], DoorEditor(p, s, n).entrances(sc["id"]))


# ---- heights, as terrain.c works them out
lerp, index = [1] * 256, [0] * 256
check("a flat cell is its sample", height_at([0, 4, 0, 0], 3, 3, lerp, index) == 32 << 16)
check("a slope runs from one sample towards the next",
      height_at([1, 0, 2, 0], 8, 0, lerp, index) == 8 << 16 and height_at([1, 0, 2, 0], 0, 0, lerp, index) == 0)
check("a negative sample is below the ground", height_at([0, 0xfe, 0, 0], 0, 0, lerp, index) == -(16 << 16))
check("a step changes at the middle",
      height_at([8, 0, 2, 0], 7, 0, lerp, index) == 0 and height_at([8, 0, 2, 0], 8, 0, lerp, index) == 16 << 16)

# ---- the people Camelot placed in towns can be talked to
for town in ("Vale", "Vault", "Bilibin", "Kolima", "Imil", "Xian", "Kalay", "Lunpa"):
    info, d, w = walk(town)
    standing = w.standing()
    people = [x for x in d["people"] if x["sprite"] > 7 and (x["x"], x["z"]) != (0, 0) and w.inside(x["x"], x["z"])]
    talkable = [x for x in people if w.talk_points(x["x"], x["z"], standing)]
    check(f"{town}: the party can talk to the people the game placed",
          len(talkable) >= 0.8 * len(people) and people, f"{len(talkable)} of {len(people)}")
    exits = [t for t in w.targets() if t[0].startswith("the way to")]
    check(f"{town}: its ways out can be walked to",
          sum(w.target_reached(c, h, w.reach, standing) for _, c, h in exits) >= len(exits) - 1, len(exits))

# ---- Imil: ice, snowy ledges and narrow lanes
info, d, w = walk("Imil")
cells = w.cells()
check("Imil's ice is found from its slide trigger", w.slide == {90}, w.slide)
check("the ice shows as ice", cells.count("slide") > 50, cells.count("slide"))
ice = next((i, j) for j in range(w.h) for i in range(w.w) if cells[j * w.w + i] == "slide")
problems = w.check(ice[0] * 16 + 8, ice[1] * 16 + 8)
check("someone on the ice is warned about", [q["kind"] for q in problems] == ["slide"], problems)
near = w.nearest_good(ice[0] * 16 + 8, ice[1] * 16 + 8)
check("and offered a good spot nearby", near is not None and not w.check(*near)
      and math.hypot(near[0] - ice[0] * 16, near[1] - ice[1] * 16) < 120, near)

cut = next((i, j) for j in range(w.h) for i in range(w.w) if cells[j * w.w + i] == "cut")
x, z = cut[0] * 16 + 8, cut[1] * 16 + 8
problems = w.check(x, z)
check("a snowy spot the party can't reach says why", bool(problems) and problems[0]["kind"] == "cut"
      and ("levels" in problems[0]["text"] or "close it off" in problems[0]["text"]), problems)
level = w.level(x, z, flat_shapes(p, info))
check("leveling to the path is offered", level and level["count"] > 0 and all(e["plane"] == "shape" for e in level["cells"]),
      level)
events, entrances = d["events"], DoorEditor(p, s, n).entrances(by_name["Imil"]["id"])
leveled = Walk(p, info, events, entrances, level["cells"])
check("and once leveled the party can walk up and talk", not [q for q in leveled.check(x, z) if q["kind"] == "cut"],
      leveled.check(x, z))

lanes = [(i, j) for j in range(w.h) for i in range(w.w) if cells[j * w.w + i] == "good"
         and w.blocked_by(i * 16 + 8, j * 16 + 8)]
check("Imil's narrow lanes are found", len(lanes) >= 5, len(lanes))
blocking = w.check(lanes[0][0] * 16 + 8, lanes[0][1] * 16 + 8)
check("someone standing in one is warned about", any(q["kind"] == "blocks" for q in blocking), blocking)
good = next((i, j) for j in range(w.h) for i in range(w.w) if cells[j * w.w + i] == "good" and (i, j) not in lanes)
check("an open spot on the path is fine", w.check(good[0] * 16 + 8, good[1] * 16 + 8) == [])
door = next((i, j) for j in range(w.h) for i in range(w.w) if cells[j * w.w + i] == "trigger")
check("a doorstep is kept clear", any(q["kind"] == "trigger" for q in w.check(door[0] * 16 + 8, door[1] * 16 + 8)))
wall = next((i, j) for j in range(w.h) for i in range(w.w) if cells[j * w.w + i] == "wall")
check("a wall is refused", any(q["kind"] == "wall" for q in w.check(wall[0] * 16 + 8, wall[1] * 16 + 8)))

# ---- Play starts where the party can walk
from gsmap import playtest  # noqa: E402
for name, want in (("AltmillerCaveDraught", 1), ("ValeCaveMouth", 0)):
    info, d, w = walk(name)
    arrival, sure = playtest.landing(p, info, DoorEditor(p, s, n).entrances(by_name[name]["id"]), w)
    check(f"{name}: Play starts at arrival point {want}", arrival["entrance"] == want and sure, arrival["entrance"])

print("all ok" if not failed else f"{failed} FAILED")
sys.exit(1 if failed else 0)
