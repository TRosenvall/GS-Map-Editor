"""Chests as one action: add, change what's inside, remove.

A chest is four things that must agree (docs/research/local-connections.md §3):

  1. a `treasure_spot x, z, code` line in the map's map.s, which places the
     chest object; the game considers codes 100..239 and at most 10 markers;
  2. the collision code `code` at that cell, which is what searching reads;
  3. a `SEARCH(SEARCH_CHEST)` event {0x13, code, flag, FIND_*} in the scene's
     event table, which says what's inside; the marker loader takes the
     *first* event of any kind with that trigger;
  4. a fresh "opened" flag, set when the chest is taken.

So a new code must be unused by every event table the map's scenes can load,
and by the collision of every map sharing those tables (or a cell there would
become searchable). Event rows go into editor overrides (overrides.json ->
mod.c); scene .c files are never touched.
"""

from .modgen import Overrides, generate
from .i18n import tr
from .sceneedit import EVENTS_END, SceneEditor

CHEST_CONTROL = 0x13  # SEARCH(SEARCH_CHEST)
CODE_LO, CODE_HI = 100, 239
MARKER_MAX = 10
FIND_ITEM, FIND_COINS = 0x100000, 0x200000
FIND_STONE = 0x300000


def placed_codes(rows, codes):
    """The marker codes among `codes` that one event table turns into a chest or a
    Psynergy Stone: the only markers the game counts toward its 10
    (treasure_spots.c). A marker with no such event places nothing."""
    return {r["trigger"] for r in rows if r["control"] != EVENTS_END and r["trigger"] in codes
            and ((r["control"] & 0x1FF) == CHEST_CONTROL or
                 ((r["control"] & 0x1FF) == 3 and (r["value"] & 0xFFF00000) == FIND_STONE))}


def find_value(contents):
    """{"item": id} or {"coins": n} -> the event's FIND_* value."""
    if "item" in contents:
        item = int(contents["item"])
        if not 1 <= item <= 0xFFFF:
            raise ValueError(tr("pick an item"))
        return FIND_ITEM | item
    if "coins" in contents:
        coins = contents["coins"]
        if isinstance(coins, float) and coins != int(coins):
            raise ValueError(tr("coins must be a whole number"))
        n = int(coins)
        if not 1 <= n <= 0xFFFF:
            raise ValueError(tr("coins must be between 1 and 65535"))
        return FIND_COINS | n
    raise ValueError(tr("say what the chest holds: an item or coins"))


class ChestEditor(SceneEditor):
    def _event_tables(self, info, ov):
        """The event tables of the scenes on this map, not their overlays' others."""
        return self._tables(self._overlays(info), ov, "events", scene_ids=self._map_scene_ids(info))

    def _used_flags(self, ov):
        used = set()
        for t in ov.data["tables"].values():
            for r in t["rows"]:
                if isinstance(r, dict):
                    for k in ("condition", "flag", "required_flag"):
                        if isinstance(r.get(k), int) and r[k] >= 0:
                            used.add(r[k])
        return used

    # ---- actions ------------------------------------------------------------------

    def list(self, info):
        """[{x, z, code, flag, contents}] for this map's chests."""
        path, t = self.project.load_markers(info)
        ov = self._read_overrides()
        try:
            tables = self._event_tables(info, ov)
        except (ValueError, FileNotFoundError):
            tables = []
        out = []
        for x, z, code in [tuple(r[:3]) for r in t.rows if tuple(r[:3]) != (0xFF, 0xFF, 0xFF)]:
            ev = next((r for _, _, rows in tables for r in rows
                       if r["trigger"] == code and r["control"] != EVENTS_END), None)
            chest = ev is not None and ev["control"] & 0x1FF == CHEST_CONTROL
            out.append({"x": x, "z": z, "code": code, "chest": chest,
                        "flag": ev["condition"] if ev else None,
                        "value": ev["value"] if ev else None,
                        "contents": self.names.find_value(ev["value"]) if chest else None})
        return out

    def add(self, info, x, z, contents):
        p = self.project
        value = find_value(contents)
        if "item" in contents and int(contents["item"]) not in self.names.items:
            raise ValueError(tr("pick an item"))
        overlays = self._overlays(info)
        ov = Overrides(p.root)
        tables = self._event_tables(info, ov)
        path, mt = p.load_markers(info)
        rows = [r for r in mt.rows if tuple(r[:3]) != (0xFF, 0xFF, 0xFF)]
        codes = {r[2] for r in rows}
        if any(len(placed_codes(rs, codes)) >= MARKER_MAX for _, _, rs in tables):
            raise ValueError(tr("A place can hold at most {n} chests and Psynergy Stones.", n=MARKER_MAX))
        if any(tuple(r[:2]) == (x, z) for r in rows):
            raise ValueError(tr("that cell already holds a chest"))
        if not (0 <= x < 128 and 0 <= z < 128):
            raise ValueError(tr("that cell is outside the map"))
        col = p.load_grid(info, "collision").cells
        here = col[z][x]
        if 1 <= here <= 239:
            raise ValueError(tr("Something already happens on that square (a door or an event). Pick another."))

        # Free across whole overlays: a code in another room's table would still
        # mean something if that room ever shares this map.
        taken = self._taken_codes(overlays, self._tables(overlays, ov, "events")) | {r[2] for r in rows}
        code = next((c for c in range(CODE_LO, CODE_HI + 1) if c not in taken), None)
        if code is None:
            raise ValueError(tr("This place has no room for more chests."))
        free = self.names.free_chest_flags
        used = self._used_flags(ov)
        flag = next((f for f in free if f not in used), None)
        if flag is None:
            raise ValueError(tr("The game has no room for more chests."))

        row = {"control": CHEST_CONTROL, "trigger": code, "condition": flag, "value": value}
        for o, name, rs in tables:
            end = next(i for i, r in enumerate(rs) if r["control"] == EVENTS_END)
            rs.insert(end, dict(row))
            ov.set(o.id, name, "events", rs)
        mt.insert(len(rows), [x, z, code])
        p.apply_edits(info, [{"plane": "collision", "x": x, "y": z, "value": code}])
        mt.save()
        ov.save()
        generate(p.root, self.scenes, ov)
        return {"code": code, "flag": flag, "contents": self.names.find_value(value),
                "was": here}

    def _find(self, info, x, z):
        path, mt = self.project.load_markers(info)
        for i, r in enumerate(mt.rows):
            if tuple(r[:2]) == (x, z) and tuple(r[:3]) != (0xFF, 0xFF, 0xFF):
                return path, mt, i, r[2]
        raise ValueError(tr("no chest there"))

    def set_contents(self, info, x, z, contents):
        value = find_value(contents)
        if "item" in contents and int(contents["item"]) not in self.names.items:
            raise ValueError(tr("pick an item"))
        _, _, _, code = self._find(info, x, z)
        ov = Overrides(self.project.root)
        hit = False
        for o, name, rs in self._event_tables(info, ov):
            changed = False
            for r in rs:
                if r["trigger"] == code and r["control"] & 0x1FF == CHEST_CONTROL:
                    r["value"], changed = value, True
            if changed:
                ov.set(o.id, name, "events", rs)
                hit = True
        if not hit:
            raise ValueError(tr("This one is controlled by the story, so it can't be changed here."))
        ov.save()
        generate(self.project.root, self.scenes, ov)
        return {"code": code, "contents": self.names.find_value(value)}

    def remove(self, info, x, z):
        p = self.project
        path, mt, i, code = self._find(info, x, z)
        ov = Overrides(p.root)
        for o, name, rs in self._event_tables(info, ov):
            keep = [r for r in rs if not (r["trigger"] == code and r["control"] & 0x1FF == CHEST_CONTROL)]
            if len(keep) == len(rs):
                continue
            if keep == o.rows(name):
                ov.remove(o.id, name)  # back to the scene's own table
            else:
                ov.set(o.id, name, "events", keep)
        mt.delete(i)
        mt.save()
        restore = self._restored_code(info, p.load_grid(info, "collision").cells, x, z, code)
        p.apply_edits(info, [{"plane": "collision", "x": x, "y": z, "value": restore}])
        ov.save()
        generate(p.root, self.scenes, ov)
        return {"code": code, "restored": restore}
