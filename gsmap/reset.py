"""Put a place back as the unmodified game has it.

A map's own files come back from the commit the mod started from, and the
editor's edits to the scene tables only this place loads are dropped. Tables
other places share are left alone, and reported, since dropping them would
undo those places too. One save, so Undo last save brings it all back.
"""

import os
import subprocess

from . import fsio, patch, tileset
from .modgen import Overrides, generate
from .sceneedit import SceneEditor

TABLES = ("map.txt", "cell_pictures.tsv", "shapes.tsv", "markers.tsv")


def _git(root, *args):
    return subprocess.run(["git", "-C", root, *args], capture_output=True)


def reset_map(project, scenes, names, info, settings=None):
    root = project.root
    base = patch.base_commit(root, settings)
    if not base:
        raise ValueError("The editor's copy of the game has no record of the original, so it can't reset this place.")
    folder = os.path.relpath(info.folder, root)
    listing = _git(root, "ls-tree", "-r", "--name-only", base, folder + "/").stdout.decode().split()
    if not listing:
        raise ValueError("The original game has no copy of this place to go back to (you made it).")
    changed = 0
    for rel in listing:
        if not rel.endswith((".s", ".tsv", ".txt")):
            continue
        original = _git(root, "show", f"{base}:{rel}").stdout
        path = os.path.join(root, rel)
        current = open(path, "rb").read() if os.path.exists(path) else None
        if current != original:
            fsio.atomic_write(path, original)
            changed += 1
    for name in TABLES:
        rel = f"{folder}/{name}"
        if rel not in listing and os.path.exists(os.path.join(root, rel)):
            fsio.remove(os.path.join(root, rel))
            changed += 1
    # The scene tables only this place's scenes load.
    editor = SceneEditor(project, scenes, names)
    mine = editor._map_scene_ids(info)
    others = {s["id"] for s in scenes.scenes} - mine
    ov = Overrides(root)
    shared = dropped = 0
    for overlay in {scenes.overlay(s["overlay"]) for s in scenes.scenes if s["id"] in mine}:
        for kind in ("entrances", "exits", "placements", "events", "regions"):
            own = editor._names_for(overlay, kind, mine)
            elsewhere = editor._names_for(overlay, kind, others)
            for name in (own if own is not None else [n for n, t in overlay.tables.items() if t["kind"] == kind]):
                if ov.get(overlay.id, name) is None:
                    continue
                if elsewhere is None or name in elsewhere:
                    shared += 1
                else:
                    ov.remove(overlay.id, name)
                    dropped += 1
    if dropped:
        ov.save()
        generate(root, scenes, ov)
    meta = tileset.load_meta(root)
    if info.number in meta:
        del meta[info.number]
        tileset.save_meta(root, meta)
        changed += 1
    project.reload()
    return {"files": changed, "tables": dropped, "shared_tables": shared}

