"""A throwaway copy of the built game that starts at one place.

The game as built starts at the title screen, and it's what Export ships. For
Play, this writes the place into a copy's gModPlaytestTarget (see modgen.py), so
testing a change doesn't mean walking there from the start of a new game.
"""

import os
import shutil
import struct
import time

from . import layout
from .i18n import tr
from .modgen import PLAYTEST_SYMBOL
from .scenes import readelf_symbols

ROM_BASE = 0x08000000
WALL = 255
MAX_STEP_UP, MAX_STEP_DOWN = 8, 12  # pixels the game lets the party step
KEPT = 3  # mGBA can hold a copy open, and saves beside it


# Lattice points (8 pixels apart) the party must be able to reach from a start,
# by the game's walking rules (walk.py): about four squares by four. Fewer means
# it can barely move. Ways out aren't required: many places leave through exit
# areas, which the walking graph doesn't list.
MIN_ROOM = 64


def landing(project, info, arrivals, walk=None):
    """Which arrival point Play starts at: (arrival, sure). The first that isn't
    on a wall square or boxed in by the heights beside it and, given the map's
    walking graph, from which the party can move about. Some arrivals sit boxed
    in on purpose, for a story scene that moves the party on. Some can't be told
    apart from the files at all, so the page also offers a choice (Start at).
    sure is False when every one looks walled in."""
    if info is None or not arrivals:
        return (arrivals[0] if arrivals else None), True
    col = project.load_grid(info, "collision").cells
    nodes = {e["entrance"]: node for e, node in walk.starts} if walk is not None else {}

    def wall(x, z):
        return col[(z >> 4) % 128][(x >> 4) % 128] == WALL

    def open_beside(a):
        x, z = a["x"], a["z"]
        if wall(x, z):
            return False
        here = project.ground_height(info, x, z)
        return any(not wall(x + dx, z + dz) and -MAX_STEP_DOWN <= project.ground_height(info, x + dx, z + dz) - here <= MAX_STEP_UP
                   for dx, dz in ((16, 0), (-16, 0), (0, 16), (0, -16)))

    def room(a):
        node = nodes.get(a["entrance"])
        return walk is None or node is None or len(walk.flood(starts=[node])) >= MIN_ROOM

    open_ones = [a for a in arrivals if open_beside(a)]
    for a in open_ones:
        if room(a):
            return a, True
    return (open_ones[0], True) if open_ones else (arrivals[0], False)


def make_copy(root, folder, scene, entrance):
    """Path of a copy of the built ROM that starts at (scene, entrance)."""
    symbols = readelf_symbols(os.path.join(root, layout.ELF))
    if PLAYTEST_SYMBOL not in symbols:
        raise ValueError(tr("This build can't start at a chosen place yet; build it again."))
    os.makedirs(folder, exist_ok=True)
    # A new name each time: mGBA keeps a file it already has open as it was.
    path = os.path.join(folder, f"play-{time.time_ns()}.gba")
    shutil.copyfile(os.path.join(root, layout.ROM), path)
    with open(path, "r+b") as f:
        f.seek(symbols[PLAYTEST_SYMBOL][0] - ROM_BASE)
        f.write(struct.pack("<I", (scene & 0xFFFF) | (entrance & 0xFFFF) << 16))
    games = sorted((n for n in os.listdir(folder) if n.startswith("play-") and n.endswith(".gba")), reverse=True)
    for old in games[KEPT:]:
        for name in (old, old[:-4] + ".sav"):
            try:
                os.remove(os.path.join(folder, name))
            except FileNotFoundError:
                pass
    return path
