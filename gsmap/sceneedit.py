"""What chest and door actions share: the scene tables a map's scenes can
load, as the mod build sees them (editor overrides first), and the collision
codes they can still use.

A collision code only means something through the event tables of the scenes
that load a map, and one overlay's tables may serve several scenes and maps
(the debug hub and the sandbox share the test rooms' tables). A new code is
therefore one that no event table of those overlays uses and no map of those
scenes has in its collision, so nothing else starts reacting to it.
"""

import os
import subprocess

from .i18n import tr
from .modgen import Overrides

FIRST_ACTOR, LAST_PARTY_SPRITE, MAX_ACTOR = 8, 7, 65  # field_work.h, scene_tables.h, actors.c


def actor_numbers(rows):
    """Each live placement row's actor number, as Event_SpawnActorPlacements gives
    them: the party's own sprites (0 to 7) are their own actors and take no slot;
    everyone else takes the next one, whether or not their condition lets them appear."""
    out, slot = [], FIRST_ACTOR
    for r in rows:
        if r["sprite"] < 0:
            break
        if r["sprite"] <= LAST_PARTY_SPRITE:
            out.append(r["sprite"])
        else:
            out.append(slot)
            slot += 1
    return out


EVENTS_END = 0xFFFFFFFF
EXITS_END = 0x1FF


def copy_rows(rows):
    """Rows the caller may change: an exit segment holds a list of exits too."""
    return [{**r, "exits": [dict(e) for e in r["exits"]]} if "exits" in r else dict(r) for r in rows]


def scene_tables(tbs, overlay, kind, scene_name):
    """getters.tables_for_scene, kept on the overlay until it or the scene
    sources change: reading a getter's C is slow, and every map asks."""
    from .doors import sources_generation
    from .getters import tables_for_scene
    key = (tbs, kind, scene_name, sources_generation(tbs))
    memo = overlay.memo
    if key not in memo:
        found = tables_for_scene(tbs, overlay, kind, scene_name)
        memo[key] = tuple(found) if found is not None else None
    found = memo[key]
    return list(found) if found is not None else None


class SceneEditor:
    def __init__(self, project, scenes, names, stock=False):
        """stock: read the scenes' own tables, ignoring the editor's overrides
        (what the unmodified game does). Writing always uses the overrides."""
        self.project, self.scenes, self.names, self.stock = project, scenes, names, stock

    def _read_overrides(self):
        ov = Overrides(self.project.root)
        if self.stock:
            ov.data["tables"] = {}
        return ov

    def _map_rows(self, info):
        return {r["row"] for r in [info.resources] + info.alternates if r}

    def _overlays(self, info, scene_id=None):
        """Overlays of the map's scenes (or of one of them)."""
        found = [s for s in self.scenes.for_rows(self._map_rows(info))
                 if scene_id is None or s["id"] == scene_id]
        if not found:
            raise ValueError(tr("no scene uses this map") if scene_id is None
                             else tr("scene {n} doesn't use this map", n=scene_id))
        return [self.scenes.overlay(i) for i in sorted({s["overlay"] for s in found})]

    def _scene_rows(self, scene_ids):
        """{overlay id: [scene rows]} for these scenes."""
        out = {}
        for s in self.scenes.scenes:
            if s["id"] in scene_ids:
                out.setdefault(s["overlay"], []).append(s)
        return out

    def _names_for(self, overlay, kind, scene_ids):
        """The table names of `kind` these scenes can load, or None for all."""
        names = set()
        for s in self._scene_rows(scene_ids).get(overlay.id, []):
            found = scene_tables(self.project.tbs, overlay, kind, s["name"])
            if found is None:
                return None
            names |= set(found)
        return names

    def _map_scene_ids(self, info):
        return {s["id"] for s in self.scenes.for_rows(self._map_rows(info))}

    def _tables(self, overlays, ov, kind, need=True, scene_ids=None):
        """[(overlay, symbol, rows as the mod build sees them)] for every table
        of `kind`, or with scene_ids only the ones those scenes can load: one
        overlay's rooms reuse the same codes for different things."""
        out = []
        for o in overlays:
            only = self._names_for(o, kind, scene_ids) if scene_ids is not None else None
            for name, t in o.tables.items():
                if t["kind"] != kind or (only is not None and name not in only):
                    continue
                # Named like a table but its bytes don't decode as one
                # (gTest_EntrancesHead, which nothing reads): not one to edit.
                if not t["editable"]:
                    continue
                over = ov.get(o.id, name)
                rows = over["rows"] if over else o.rows(name)
                out.append((o, name, copy_rows(rows)))
        if need and not out:
            raise ValueError(tr("this map's scene has no {kind} table", kind=kind))
        return out

    def _sharing_maps(self, overlays):
        """Maps of every scene that loads one of these overlays."""
        ids = {o.id for o in overlays}
        rows = {s["layered_row"] for s in self.scenes.scenes if s["overlay"] in ids}
        return [m for m in self.project.maps.values()
                if any(r and r["row"] in rows for r in [m.resources] + m.alternates)]

    def _taken_codes(self, overlays, event_tables):
        taken = {r["trigger"] for _, _, rs in event_tables for r in rs}
        for m in self._sharing_maps(overlays):
            try:
                taken |= {v for line in self.project.load_grid(m, "collision").cells for v in line}
            except FileNotFoundError:
                pass
        return taken

    def _restored_code(self, info, col, x, z, code):
        """What a square goes back to when its chest, door or sign goes: the
        original game's value, if that carried no event, else a guess from around it."""
        from . import grid as gridmod, patch
        root = self.project.root
        rel = os.path.relpath(info.grid_path(), root)
        base = patch.base_commit(root)
        shown = subprocess.run(["git", "-C", root, "show", f"{base}:{rel}"], capture_output=True) if base else None
        if shown is not None and shown.returncode == 0:
            try:
                v = gridmod.parse(shown.stdout.decode("utf-8")).plane("collision").cells[z][x]
                if v != code and not 1 <= v <= 239:
                    return v
            except (ValueError, IndexError, KeyError):
                pass
        return self._neighbour_code(col, x, z, code)

    @staticmethod
    def _neighbour_code(col, x, z, code):
        """Most common code around (x, z) that carries no event (floor, wall...)."""
        counts = {}
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if 0 <= z + dz < len(col) and 0 <= x + dx < len(col[0]):
                v = col[z + dz][x + dx]
                if v != code and not 1 <= v <= 239:
                    counts[v] = counts.get(v, 0) + 1
        return max(counts, key=counts.get) if counts else 0
