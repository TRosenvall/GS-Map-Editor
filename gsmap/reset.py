"""Put a place, or the world map, back as the unmodified game has it.

A map's files come back from the commit the mod started from: its own folder,
the folders it borrows its grid and blocks from, and any picture imported into
its tile sheets. The editor's edits to the scene tables only this place loads
are dropped; tables other places share are left alone, and reported, since
dropping them would undo those places too. Text you wrote is removed once
nothing uses any of it. One save, so Undo brings it all back.
"""

import os
import subprocess

from . import fsio, layout, patch, tileset
from .i18n import tr
from .messages import BEGIN, END, Messages
from .modgen import Overrides, generate
from .sceneedit import SceneEditor

TABLES = ("map.txt", "cell_pictures.tsv", "shapes.tsv", "markers.tsv")
RESTORED = (".s", ".tsv", ".txt", ".png")
KINDS = ("entrances", "exits", "placements", "events", "regions")


def _git(root, *args):
    return subprocess.run(["git", "-C", root, *args], capture_output=True)


def _restore(root, base, rel):
    """Make one file match the original game. True if that changed it."""
    shown = _git(root, "show", f"{base}:{rel}")
    if shown.returncode != 0:
        return False
    path = os.path.join(root, rel)
    current = None
    if os.path.exists(path):
        with open(path, "rb") as f:
            current = f.read()
    if current == shown.stdout:
        return False
    fsio.atomic_write(path, shown.stdout)
    return True


def _base(root, settings):
    base = patch.base_commit(root, settings)
    if not base:
        raise ValueError(tr("The editor's copy of the game has no record of the original, so it can't reset this."))
    return base


def _drop_tables(root, scenes, names, project, mine, shared_too=False):
    """Forget edits to tables only the scenes in `mine` load, or, with shared_too,
    any they load. (dropped, shared and kept)."""
    editor = SceneEditor(project, scenes, names)
    others = {s["id"] for s in scenes.scenes} - mine
    ov = Overrides(root)
    shared = dropped = 0
    for overlay in {scenes.overlay(s["overlay"]) for s in scenes.scenes if s["id"] in mine}:
        for kind in KINDS:
            own = editor._names_for(overlay, kind, mine)
            elsewhere = editor._names_for(overlay, kind, others)
            for name in (own if own is not None else [n for n, t in overlay.tables.items() if t["kind"] == kind]):
                if ov.get(overlay.id, name) is None:
                    continue
                if not shared_too and (elsewhere is None or name in elsewhere):
                    shared += 1
                else:
                    ov.remove(overlay.id, name)
                    dropped += 1
    if dropped:
        ov.save()
        generate(root, scenes, ov)
    return dropped, shared


def _drop_unused_text(root, base):
    """Once no event uses a line you wrote, the editor's block leaves en.po, and
    nothing else does. Lines can't be taken out one at a time, since message numbers
    have to stay continuous. A block in the checkout's last commit stays: code the
    mod's author wrote could be using it."""
    msgs = Messages(root)
    begin, end = msgs.text.find(BEGIN), msgs.text.find(END)
    if not 0 <= begin < end:
        return False
    committed = _git(root, "show", f"HEAD:{layout.TEXT_EN}")
    if committed.returncode != 0 or BEGIN.encode() in committed.stdout:
        return False
    used = {r["value"] & 0xFFFF for t in Overrides(root).data["tables"].values() if t["kind"] == "events"
            for r in t["rows"]}
    mine = {n for n in msgs.entries if msgs.owned(n)}
    if mine and (mine & used or any(n > min(mine) and n not in mine for n in msgs.entries)):
        return False
    fsio.atomic_write(msgs.path, msgs.text[:begin].rstrip("\n") + "\n" + msgs.text[end + len(END):].lstrip("\n"))
    return True


def _refuse_if_set_up_by_hand(project, base, info):
    """A place given its own art outside the editor has a changed row in the map
    list. Its folder alone can't go back: the original files would be drawn with
    the new art, or none."""
    original = _git(project.root, "show", f"{base}:{layout.MAP_TABLE}")
    if original.returncode != 0:
        return
    rows = project.parse_map_rows(original.stdout.decode("utf-8", "replace"))
    now = project.map_rows()
    for r in [info.resources] + info.alternates:
        if r and (r["row"] >= len(rows) or rows[r["row"]] != now[r["row"]]):
            raise ValueError(tr("This place's art was set up outside the editor, so Reset can't put it back safely. "
                                "Nothing has been changed."))


def reset_map(project, scenes, names, info, settings=None, shared_too=False):
    root = project.root
    base = _base(root, settings)
    folder = os.path.relpath(info.folder, root)
    listing = _git(root, "ls-tree", "-r", "--name-only", base, folder + "/").stdout.decode().split()
    if not listing:
        raise ValueError(tr("The original game has no copy of this place to go back to (you made it)."))
    # A place can draw another's grid or blocks (maps 174 to 179 draw map_001's).
    borrowed = {os.path.relpath(p, root) for p in (info.grid_path(), info.source("CELL_PICTURES", "cell_pictures.tsv"),
                                                   info.source("SHAPES", "shapes.tsv"))} - set(listing)
    _refuse_if_set_up_by_hand(project, base, info)
    changed = 0
    for rel in [r for r in listing if r.endswith(RESTORED)] + sorted(borrowed):
        changed += _restore(root, base, rel)
    for name in TABLES:
        rel = f"{folder}/{name}"
        if rel not in listing and rel not in borrowed and os.path.exists(os.path.join(root, rel)):
            fsio.remove(os.path.join(root, rel))
            changed += 1
    # Imported pictures live in the place's own tile sheets.
    meta = tileset.load_meta(root)
    if info.number in meta:
        for label in filter(None, info.resources["blocks"] if info.resources else []):
            path = project.label_path(label)
            if path:
                changed += _restore(root, base, os.path.relpath(path, root))
        del meta[info.number]
        tileset.save_meta(root, meta)
        changed += 1
    mine = SceneEditor(project, scenes, names)._map_scene_ids(info)
    dropped, shared = _drop_tables(root, scenes, names, project, mine, shared_too)
    text = _drop_unused_text(root, base)
    project.reload()
    return {"files": changed, "tables": dropped, "shared_tables": shared, "text": text}


def reset_world(project, scenes, names, settings=None):
    """The world map: its painted blocks, its towns' places and links, and its battles."""
    root = project.root
    base = _base(root, settings)
    from .encounters import ZONES
    changed = sum(_restore(root, base, rel) for rel in (layout.WORLD_BLOCKS, layout.WORLD_CELLS, layout.WORLD_COLLISION, ZONES))
    from .world import WORLD_SCENE
    dropped, shared = _drop_tables(root, scenes, names, project, {WORLD_SCENE}, True)
    text = _drop_unused_text(root, base)
    project.reload()
    return {"files": changed, "tables": dropped, "shared_tables": shared, "text": text}
