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
from .modgen import PLAYTEST_SYMBOL
from .scenes import readelf_symbols

ROM_BASE = 0x08000000
KEPT = 3  # mGBA can hold a copy open, and saves beside it


def make_copy(root, folder, scene, entrance):
    """Path of a copy of the built ROM that starts at (scene, entrance)."""
    symbols = readelf_symbols(os.path.join(root, layout.ELF))
    if PLAYTEST_SYMBOL not in symbols:
        raise ValueError("This build can't start at a chosen place yet; build it again.")
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
