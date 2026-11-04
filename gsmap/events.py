"""Scene events in plain words, and the edits that need no C.

A scene event (the game's struct Trigger, include/field/scene_tables.h) is
{control, trigger, condition, value} (kind, subject, condition, value there):
  control   kind in bits 3..0 (talk, exit, touch, search, item, Psynergy,
            raised, 7 = talk to a stopped person) plus detail bits;
  trigger   the person (actor 8 + placement row) or a cell's collision code;
  condition -1 always, flag | 0x1000 while the flag is set, else while clear;
  value     a message (< 0x10000), a FIND_* value for searches, an exit kind
            for exits, else a scene script (C, read-only here).
The engine takes the first event that matches, so rows keep their order and
new rows go just before the end row.

What the editor changes (all through overrides of one event table, the story
stage being edited): what a line says (a new message, so other uses of the old
one stay), when an event happens, making a person say something, signs you
read with A and messages you get by stepping somewhere, adding a person, and
removing events. Scripts are shown with their own description. A step message
is stored as a message; mod.c runs it through a function that shows it once
per visit (modgen.step_message_functions).
"""

from .doors import DoorEditor, script_docs
from .messages import Messages, compose, plain
from .modgen import Overrides, generate
from .names import read_flag_names
from .sceneedit import EVENTS_END

KINDS = {0: "talk", 1: "exit", 2: "touch", 3: "search", 4: "item", 5: "psynergy", 6: "raised", 7: "talk-stopped"}
SEARCH_TARGETS = ["something", "a chest", "a jar", "a barrel", "a wall", "the ground", "a rock", "a hole",
                  "a grave", "a tree", "the underbrush", "a door", "a chimney", "a wooden box", "a bed",
                  "a bookcase", "a stone coffin", "a fireplace", "the water", "a stone pillar", "a stalactite",
                  "some boards", "a fountain", "an oven", "a table", "a stone statue", "a stone tablet",
                  "a shelf", "a wardrobe", "firewood", "some books", "a well"]
FLAG_SET = 0x1000
ABILITY_NAMES = 819  # message 819 + ability id is its name (all 34 named abilities, ability_ids.h)
FIRST_ACTOR = 8
MAX_ACTOR = 65
def flag_names(root):
    return read_flag_names(root)


def flag_label(n, names):
    name = names.get(n)
    if not name:
        return f"story flag {n:#05x}"
    words = name.replace("FLAG_", "").replace("_", " ").lower()
    return words[0].upper() + words[1:]


def condition_text(cond, names):
    if cond == -1:
        return "Always"
    flag = cond & 0xFFF
    return (f"Only once “{flag_label(flag, names)}” is set" if cond & FLAG_SET
            else f"Only while “{flag_label(flag, names)}” isn't set")


class EventEditor(DoorEditor):
    def _ctx(self, scene_id):
        sc = next(s for s in self.scenes.scenes if s["id"] == scene_id)
        return self.scenes.overlay(sc["overlay"])

    def _table(self, o, symbol, kind="events"):
        ov = Overrides(self.project.root)
        for oo, name, rows in self._tables([o], ov, kind):
            if name == symbol:
                return ov, rows
        raise ValueError(f"{symbol} isn't one of this scene's {kind} tables")

    @staticmethod
    def _stage_placements(symbol, placement_tables):
        """The people table for an events table's story stage (by name), else the first."""
        want = symbol.replace("Triggers", "ActorPlacements")
        for _, name, rows in placement_tables:
            if name == want:
                return name, rows
        return (placement_tables[0][1], placement_tables[0][2]) if placement_tables else (None, [])

    # ---- reading ---------------------------------------------------------------------

    def describe(self, info, scene_id, symbol=None):
        """Every event of one events table (the scene's first unless named), in words."""
        o = self._ctx(scene_id)
        ov = self._read_overrides()
        tables = self._tables([o], ov, "events", scene_ids={scene_id})
        # A stage from another map or scene isn't one of these: show the first.
        if symbol not in {n for _, n, _ in tables}:
            symbol = tables[0][1]
        rows = next(r for _, n, r in tables if n == symbol)
        people_table, people = self._stage_placements(
            symbol, self._tables([o], ov, "placements", need=False, scene_ids={scene_id}))
        exits = self._tables([o], ov, "exits", need=False, scene_ids={scene_id})
        msgs = Messages(self.project.root)
        docs = script_docs(self.project.tbs, o)
        fnames = flag_names(self.names.root)
        col = self.project.load_grid(info, "collision").cells
        cells = {}
        for gx, gz in self._window(info):
            cells.setdefault(col[gz][gx], []).append([gx, gz])
        out = []
        for i, r in enumerate(rows):
            if r["control"] == EVENTS_END:
                break
            c, kind = r["control"], KINDS.get(r["control"] & 0xF, "other")
            ev = {"index": i, "kind": kind, "control": c, "trigger": r["trigger"], "condition": r["condition"],
                  "value": r["value"], "when": condition_text(r["condition"], fnames),
                  "message": None, "text": None, "script": None, "editable_text": False, "cells": [], "actor": None}
            on_actor = kind in ("talk", "talk-stopped") or (kind in ("item", "psynergy") and c & 0x10)
            if on_actor:
                ev["actor"] = r["trigger"]
                row = r["trigger"] - FIRST_ACTOR
                p = people[row] if 0 <= row < len(people) and people[row]["sprite"] >= 0 else None
                spr = self.names.sprites.get(p["sprite"]) if p else None
                ev["who"] = (spr or {}).get("name") or (f"person {r['trigger']}" if p is None else f"sprite {p['sprite']}")
                if p:
                    ev["at"] = [p["x"] >> 16, p["z"] >> 16]
            else:
                ev["cells"] = cells.get(r["trigger"] & 0xFF, [])
            v = r["value"]
            if kind == "exit":
                ex = self._destination(exits, scene_id, v)
                ev["does"] = f"Leads to {self.names.scene_label(ex['scene'])}" if ex else "An exit that leads nowhere"
            elif kind == "search" and v >> 20 in (1, 2, 3, 5):
                ev["does"] = "Finds " + self.names.find_value(v)
            elif (kind == "search" and v >> 20 == 4) or (kind != "search" and 0 < v < 0x10000):
                m = v & 0xFFFF
                ev["message"], ev["text"] = m, msgs.get(m)
                ev["editable_text"] = True
                ev["does"] = "Says"
            elif v >= 0x10000:
                name, doc = docs.get(v & ~1, (None, ""))
                ev["script"] = name or f"{v:#x}"
                ev["does"] = doc or "Runs a scene script"
            else:
                ev["does"] = "Nothing"
            if kind == "search":
                ev["what"] = SEARCH_TARGETS[(c >> 4) & 0x1F] if ((c >> 4) & 0x1F) < len(SEARCH_TARGETS) else "something"
            elif kind == "item":
                ev["what"] = self.names.item_name((c >> 8) & 0xFF)
            elif kind == "psynergy":
                ability = (c >> 8) & 0xFF
                ev["what"] = msgs.get(ABILITY_NAMES + ability) or f"Psynergy {ability}"
                if ev["what"] == "Mind Read" and ev["message"] is not None:
                    ev["does"] = "Thinks"
            out.append(ev)
        return {"symbol": symbol, "people_table": people_table,
                "tables": [n for _, n, _ in tables], "events": out,
                "people": [{"actor": FIRST_ACTOR + i, "sprite": p["sprite"], "x": p["x"] >> 16, "z": p["z"] >> 16,
                            "name": (self.names.sprites.get(p["sprite"]) or {}).get("name")}
                           for i, p in enumerate(people) if p["sprite"] >= 0]}

    # ---- writing ---------------------------------------------------------------------

    def _save_table(self, ov, o, symbol, kind, rows):
        if rows == o.rows(symbol):
            ov.remove(o.id, symbol)
        else:
            ov.set(o.id, symbol, kind, rows)
        ov.save()
        generate(self.project.root, self.scenes, ov)

    def _message(self, text, current=None, raw=False):
        msgs = Messages(self.project.root)
        game_text = text if raw else compose(text)
        if current is not None and msgs.owned(current):
            msgs.set(current, game_text)
            return current
        return msgs.add(game_text)

    @staticmethod
    def _condition(when):
        """{"always": true} | {"flag": n, "set": bool} -> the condition field."""
        if not when or when.get("always"):
            return -1
        flag = int(when["flag"])
        if not 0 <= flag <= 0xFFF:
            raise ValueError("no such story flag")
        return flag | (FLAG_SET if when.get("set", True) else 0)

    def set_text(self, scene_id, symbol, index, text, raw=False):
        o = self._ctx(scene_id)
        ov, rows = self._table(o, symbol)
        r = self._row(rows, index)
        kind, v = r["control"] & 0xF, r["value"]
        if kind == 3 and v >> 20 == 4:
            r["value"] = 0x400000 | self._message(text, v & 0xFFFF, raw)
        elif kind != 3 and 0 < v < 0x10000:
            r["value"] = self._message(text, v, raw)
        else:
            raise ValueError("This is part of a story scene, so its words can't be changed here.")
        self._save_table(ov, o, symbol, "events", rows)
        return {"message": r["value"] & 0xFFFF}

    def set_when(self, scene_id, symbol, index, when):
        o = self._ctx(scene_id)
        ov, rows = self._table(o, symbol)
        self._row(rows, index)["condition"] = self._condition(when)
        self._save_table(ov, o, symbol, "events", rows)
        return {}

    @staticmethod
    def _row(rows, index):
        if not 0 <= index < len(rows) or rows[index]["control"] == EVENTS_END:
            raise ValueError("no such event")
        return rows[index]

    def _append(self, rows, row):
        end = next(i for i, r in enumerate(rows) if r["control"] == EVENTS_END)
        rows.insert(end, row)
        return end

    def add_talk(self, scene_id, symbol, actor, text, when=None):
        """Make a person say something (when they don't already talk, or as the
        first line for the condition, since the first match wins)."""
        o = self._ctx(scene_id)
        ov, rows = self._table(o, symbol)
        row = {"control": 0, "trigger": int(actor), "condition": self._condition(when), "value": self._message(text)}
        # Before the person's other talk rows, so a conditional line can take precedence.
        first = next((i for i, r in enumerate(rows) if r["control"] & 0xF == 0 and r["trigger"] == int(actor)), None)
        if first is not None and row["condition"] != -1:
            rows.insert(first, row)
            idx = first
        else:
            if first is not None:
                raise ValueError("this person already talks; change their line instead, or add one for a story moment")
            idx = self._append(rows, row)
        self._save_table(ov, o, symbol, "events", rows)
        return {"index": idx, "message": row["value"]}

    def add_spot(self, info, scene_id, symbol, x, z, how, text, target=0, when=None):
        """A message at a cell: read with A ("search", a sign) or on stepping there ("touch")."""
        if how not in ("search", "touch"):
            raise ValueError("a spot is read with A (search) or by stepping on it (touch)")
        p = self.project
        col = p.load_grid(info, "collision").cells
        if not (0 <= x < 128 and 0 <= z < 128):
            raise ValueError("that cell is outside the map")
        here = col[z][x]
        o = self._ctx(scene_id)
        overlays = self._overlays(info)
        ov = Overrides(p.root)
        events_all = self._tables(overlays, ov, "events")
        if 1 <= here <= 239:
            code = here  # the spot already has a code: add to it (e.g. a sign beside a door's code is rare)
            if any(r["trigger"] == code and r["control"] & 0xF in (2, 3) for _, _, rs in events_all for r in rs):
                raise ValueError("that spot already has a message or search; change it instead")
        else:
            taken = self._taken_codes(overlays, events_all)
            code = next((c for c in list(range(1, 100)) + list(range(239, 99, -1)) if c not in taken), None)
            if code is None:
                raise ValueError("This place has no room for more of these.")
        ov, rows = self._table(o, symbol)
        msg = self._message(text)
        if how == "search":
            control = 3 | (int(target) & 0x1F) << 4
            value = 0x400000 | msg
        else:
            control, value = 2, msg
        idx = self._append(rows, {"control": control, "trigger": code, "condition": self._condition(when), "value": value})
        if here != code:
            p.apply_edits(info, [{"plane": "collision", "x": x, "y": z, "value": code}])
        self._save_table(ov, o, symbol, "events", rows)
        return {"index": idx, "code": code, "message": msg}

    def remove(self, info, scene_id, symbol, index):
        o = self._ctx(scene_id)
        ov, rows = self._table(o, symbol)
        r = self._row(rows, index)
        del rows[index]
        self._save_table(ov, o, symbol, "events", rows)
        # A code no event uses any more goes back to ground on this map.
        kind = r["control"] & 0xF
        restored = 0
        if kind in (2, 3) and info is not None:
            overlays = self._overlays(info, scene_id)
            still = any(rr["trigger"] == r["trigger"] for _, _, rs in self._tables(overlays, Overrides(self.project.root), "events")
                        for rr in rs if rr["control"] != EVENTS_END)
            if not still:
                col = self.project.load_grid(info, "collision").cells
                cells = [(gx, gz) for gx, gz in self._window(info) if col[gz][gx] == r["trigger"]]
                if cells:
                    self.project.apply_edits(info, [{"plane": "collision", "x": gx, "y": gz,
                                                     "value": self._neighbour_code(col, gx, gz, r["trigger"])}
                                                    for gx, gz in cells])
                    restored = len(cells)
        return {"restored_cells": restored}

    def add_person(self, scene_id, symbol, sprite, x, z, text=None, wander=False, when=None):
        """A new person standing (or wandering) at map pixels (x, z), optionally
        with a line. Added after everyone else, so no existing actor renumbers."""
        o = self._ctx(scene_id)
        ov = Overrides(self.project.root)
        placements = self._tables([o], ov, "placements", scene_ids={scene_id})
        people_table, rows = self._stage_placements(symbol, placements)
        end = next(i for i, r in enumerate(rows) if r["sprite"] < 0)
        actor = FIRST_ACTOR + end
        if actor > MAX_ACTOR:
            raise ValueError("this scene already has as many people as the game allows")
        rows.insert(end, {"sprite": int(sprite), "condition": self._condition(when), "behavior": 2 if wander else 1,
                          "x": int(x) << 16, "y": 0, "z": int(z) << 16, "facing": 0x4000, "talkFacing": 0, "flags": 0})
        self._save_table(ov, o, people_table, "placements", rows)
        out = {"actor": actor, "table": people_table}
        if text:
            out.update(self.add_talk(scene_id, symbol, actor, text, when))
        return out

    # ---- regions: boxes that are exits --------------------------------------------------

    def regions(self, scene_id):
        o = self._ctx(scene_id)
        ov = self._read_overrides()
        exits = self._tables([o], ov, "exits", need=False, scene_ids={scene_id})
        out = []
        for _, name, rows in self._tables([o], ov, "regions", need=False, scene_ids={scene_id}):
            for i, r in enumerate(rows):
                if r["minX"] == -1:
                    break
                ex = self._destination(exits, scene_id, r["value"])
                out.append({**r, "table": name, "index": i,
                            "label": self.names.scene_label(ex["scene"]) if ex else None,
                            "entrance": ex["entrance"] if ex else None})
        return out

    def edit_region(self, scene_id, symbol, index, box=None, target=None, when=None, remove=False):
        o = self._ctx(scene_id)
        ov, rows = self._table(o, symbol, "regions")
        if not 0 <= index < len(rows) or rows[index]["minX"] == -1:
            raise ValueError("no such area")
        r = rows[index]
        if remove:
            del rows[index]
        if box and not remove:
            x0, z0, x1, z1 = (int(v) for v in box)
            if not (0 <= x0 < x1 and 0 <= z0 < z1):
                raise ValueError("draw the area as a box on the map")
            r.update(minX=x0, minZ=z0, maxX=x1, maxZ=z1)
        if when is not None and not remove:
            r["condition"] = self._condition(when)
        self._save_table(ov, o, symbol, "regions", rows)
        if target and not remove:
            self.relink_scene(scene_id, r["value"], int(target["scene"]), int(target["entrance"]),
                              by_kind=True)
        return {}
