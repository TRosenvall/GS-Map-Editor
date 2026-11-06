"""Doors as one action: see where a door leads, send it somewhere else, make
a new one, remove one.

A door is a chain (docs/research/local-connections.md §1-2):

    collision code at the cell -> EVENT_EXIT event {0x1, code, -1, kind}
    -> the scene's exit segment: kind -> (scene, entrance)
    -> the target scene's entrance row (where the party arrives)

The exit segment is chosen by the scene being left, so the same code can lead
to different places in different scenes sharing a map. Kind 255 in a segment
matches every kind. A scene may have several event and exit tables (story
stages); a door is changed in all of them, so it leads to the same place
throughout the game. Rows go into editor overrides; scene .c files are never
touched.

Cells are in the 128x128 grid of layer 0's window, which is where the game's
doors are painted.
"""

import glob
import os
import re

from . import layout
from .modgen import Overrides, generate
from .sceneedit import EVENTS_END, EXITS_END, SceneEditor

EVENT_EXIT, EVENT_TOUCH = 0x1, 0x2
ANY_KIND = 0xFF
_SCRIPT_CACHE = {}  # overlay id -> {function address: kinds}


_FILE_CACHE = {}  # scene .c path -> (mtime, defined table symbols, {function: kinds})
_SOURCES = {}  # game source root -> its scene sources
_EXIT_NAMES = {}  # scene_exits.h path -> {exit name: kind}
_REQUEST = layout.EXIT_REQUEST


def _named_numbers(text):
    """{NAME: value} of the enum constants and #defines in C text that spell out
    a number, counting on from the last one as C does for those that don't."""
    out = {}
    for block in re.findall(r"enum\s*\w*\s*\{(.*?)\}", text, re.S):
        value = -1
        block = re.sub(r"/\*.*?\*/|//[^\n]*", "", block, flags=re.S)
        for item in block.split(","):
            m = re.fullmatch(r"\s*([A-Za-z_]\w*)\s*(?:=\s*(\w+)\s*)?", item)
            if not m:
                value = None
                continue
            if m.group(2):
                value = int(m.group(2), 0) if re.fullmatch(r"\d+|0x[0-9a-fA-F]+", m.group(2)) else out.get(m.group(2))
            elif value is not None:
                value += 1
            if value is not None:
                out[m.group(1)] = value
    for name, value in re.findall(r"^#define\s+(\w+)\s+(\d+|0x[0-9a-fA-F]+)\s*$", text, re.M):
        out[name] = int(value, 0)
    return out


def _exit_names(path):
    """The exit kinds scene_exits.h names, for a scene source at `path`."""
    header = os.path.join(path.split(f"/{layout.SRC}/")[0], layout.EXIT_NAMES)
    if header not in _EXIT_NAMES:
        _EXIT_NAMES[header] = _named_numbers(open(header, encoding="utf-8").read()) if os.path.exists(header) else {}
    return _EXIT_NAMES[header]


def _scan(path):
    mtime = os.path.getmtime(path)
    hit = _FILE_CACHE.get(path)
    if hit and hit[0] == mtime:
        return hit
    text = open(path, encoding="utf-8").read()
    tables = set(re.findall(r"\b(g\w+)\s*\[[^\]]*\]\s*=", text))
    # Exit helpers: functions passing their one argument on as the exit kind
    # (Vale_RequestBackdropExit(no) ... Import_EventSetExitRequest(no)), in this
    # file or a scene header it includes (scene/shared/vale.h).
    helper_text = text
    for inc in re.findall(r'^#include "([^"]+)"', text, re.M):
        hp = os.path.join(os.path.dirname(path), inc)
        if os.path.exists(hp):
            helper_text += "\n" + open(hp, encoding="utf-8").read()
    helpers = {_REQUEST}
    for m in re.finditer(r"^(?:static\s+)?\w[\w\s\*]*?\b(\w+)\s*\(\s*s32\s+(\w+)\s*\)\s*\{(.*?)^\}",
                         helper_text, re.S | re.M):
        if re.search(rf"{_REQUEST}\(\s*{m.group(2)}\s*\)", m.group(3)):
            helpers.add(m.group(1))
    call = re.compile(r"\b(" + "|".join(sorted(helpers)) + r")\(\s*(\w+)\s*\)")
    numbers = {**_exit_names(path), **_named_numbers(helper_text)}

    def kind_of(word):
        return int(word, 0) if re.fullmatch(r"\d+|0x[0-9a-fA-F]+", word) else numbers.get(word)

    funcs, docs = {}, {}
    for m in re.finditer(r"((?:^///[^\n]*\n)*)^(?:static\s+)?\w[\w\s\*]*?\b(\w+)\s*\([^;{)]*\)\s*\{(.*?)^\}",
                         text, re.S | re.M):
        kinds = {kind_of(k) for _, k in call.findall(m.group(3))} - {None}
        if kinds and m.group(2) not in helpers:
            funcs[m.group(2)] = kinds
        if m.group(1):
            docs[m.group(2)] = " ".join(l[3:].strip() for l in m.group(1).splitlines()).strip()
    _FILE_CACHE[path] = (mtime, tables, funcs, docs)
    return _FILE_CACHE[path]


def _source_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def script_docs(tbs, overlay):
    """{function address: (name, its /// comment)} for an overlay's functions."""
    docs = {}
    for path in _scene_files(tbs, overlay.tables):
        docs.update(_scan(path)[3])
    return {addr & ~1: (name, docs.get(name, "")) for name, (addr, _, typ) in overlay.symbols.items()
            if typ == "FUNC"}


def _scene_files(tbs, table_names):
    """Scene sources defining any of these tables."""
    if tbs not in _SOURCES:
        root = tbs[:-len(layout.SRC)]
        _SOURCES[tbs] = [p for folder in layout.SCENE_SOURCES
                         for p in glob.glob(os.path.join(root, folder, "**", "*.c"), recursive=True)]
    names = set(table_names)
    return [p for p in _SOURCES[tbs] if _scan(p)[1] & names]


def _script_index(path):
    return _scan(path)[2]


def script_exit_kinds(tbs, overlay):
    """{function address: exit kinds it asks for} for an overlay's scene scripts."""
    by_name = {}
    for path in _scene_files(tbs, overlay.tables):
        by_name.update(_script_index(path))
    return {addr & ~1: sorted(by_name[name]) for name, (addr, _, typ) in overlay.symbols.items()
            if typ == "FUNC" and name in by_name}


class DoorEditor(SceneEditor):
    # ---- reading -------------------------------------------------------------

    def _window(self, info):
        """Grid cells of layer 0's visible window, as (gx, gz)."""
        ox, oz = self.project.layer_origin(info, 0)
        w, h = info.size
        bx, bz = info.bounds[0] // 2, info.bounds[1] // 2
        return [((ox + bx + x) % 128, (oz + bz + z) % 128) for z in range(h) for x in range(w)]

    def _script_kinds(self, overlay):
        """{function address: exit kinds it asks for} for the overlay's scene
        scripts, read from the scene's C source: Import_EventSetExitRequest(k)."""
        if overlay.id in _SCRIPT_CACHE:
            return _SCRIPT_CACHE[overlay.id]
        by_name = {}
        for path in _scene_files(self.project.tbs, overlay.tables):
            for name, kinds in _script_index(path).items():
                by_name[name] = kinds
        out = {}
        for name, (addr, _, typ) in overlay.symbols.items():
            if typ == "FUNC" and name in by_name:
                out[addr & ~1] = sorted(by_name[name])
        _SCRIPT_CACHE[overlay.id] = out
        return out

    def _exit_kind(self, event_tables, code):
        """(kind, scripted) of the door with this trigger, or (None, False).
        As Scene_RunStepTriggerOrExit: a touch event runs first (a script door when
        its function asks for exactly one exit kind), else the EVENT_EXIT row."""
        for touch in (True, False):
            for o, _, rows in event_tables:
                for r in rows:
                    if r["control"] == EVENTS_END:
                        break
                    if r["trigger"] != code:
                        continue
                    if touch and r["control"] & 0xF == EVENT_TOUCH and r["value"]:
                        if r["value"] < 0x10000:
                            return None, False  # shows a message
                        kinds = self._script_kinds(o).get(r["value"] & ~1, [])
                        return (kinds[0], True) if len(kinds) == 1 else (None, False)
                    if not touch and r["control"] & 0xF == EVENT_EXIT:
                        return r["value"], False
        return None, False

    @staticmethod
    def _destination(exit_tables, scene_id, kind):
        """The exit a kind takes, as Scene_TakeExit (system/main_routine.c) finds it:
        the first of that kind (or kind 255) in the scene's exits; when there
        is none, the scene of its first exit at arrival point 0 (marked
        "fallback"); with no exits for the scene, None: the game stays put."""
        first = None
        for _, _, segs in exit_tables:
            for seg in segs:
                if seg.get("scene") != scene_id:
                    continue
                for ex in seg.get("exits", []):
                    if ex["kind"] in (kind, ANY_KIND):
                        return ex
                if first is None and seg.get("exits"):
                    first = seg["exits"][0]
        if first is not None:
            return {"kind": kind, "scene": first["scene"], "entrance": 0, "flag": None, "fallback": True}
        return None

    def entrances(self, scene_id):
        """[{entrance, x, z}] arrival points of a scene (pixels), first row per number."""
        sc = next(s for s in self.scenes.scenes if s["id"] == scene_id)
        o = self.scenes.overlay(sc["overlay"])
        ov = self._read_overrides()
        seen, out = set(), []
        # Only this scene's tables: rooms sharing an overlay reuse the same numbers.
        for _, _, rows in self._tables([o], ov, "entrances", need=False, scene_ids={scene_id}):
            for r in rows:
                if r["entrance"] >= 0 and r["entrance"] not in seen:
                    seen.add(r["entrance"])
                    out.append({"entrance": r["entrance"], "x": r["x"], "z": r["z"]})
        return sorted(out, key=lambda e: e["entrance"])

    def list(self, info):
        """{scene id: [{code, kind, cells, scene, entrance, label}]} for the
        map's doors (codes with an EVENT_EXIT event), per scene."""
        col = self.project.load_grid(info, "collision").cells
        cells = {}
        for gx, gz in self._window(info):
            v = col[gz][gx]
            if 1 <= v <= 239:
                cells.setdefault(v, []).append([gx, gz])
        ov = self._read_overrides()
        out = {}
        for sc in self.scenes.for_rows(self._map_rows(info)):
            try:
                o = self.scenes.overlay(sc["overlay"])
                events = self._tables([o], ov, "events", need=False, scene_ids={sc["id"]})
                exits = self._tables([o], ov, "exits", need=False, scene_ids={sc["id"]})
            except (ValueError, FileNotFoundError):
                continue
            doors = []
            for code in sorted(cells):
                kind, scripted = self._exit_kind(events, code)
                if kind is None:
                    continue
                ex = self._destination(exits, sc["id"], kind)
                doors.append({
                    "code": code, "kind": kind, "cells": cells[code], "scripted": scripted,
                    "scene": ex["scene"] if ex else None,
                    "entrance": ex["entrance"] if ex else None,
                    "shared_kind": bool(ex) and ex["kind"] == ANY_KIND,
                    "fallback": bool(ex and ex.get("fallback")),
                    "label": self.names.scene_label(ex["scene"]) if ex else None,
                })
            out[sc["id"]] = doors
        return out

    # ---- writing --------------------------------------------------------------

    def _check_target(self, target_scene, target_entrance):
        if not any(s["id"] == target_scene for s in self.scenes.scenes):
            raise ValueError(f"no scene {target_scene}")
        nums = [e["entrance"] for e in self.entrances(target_scene)]
        if nums and target_entrance not in nums:
            raise ValueError(f"{self.names.scene_label(target_scene)} has no arrival point {target_entrance}")

    def _set_exit(self, exit_tables, scene_id, kind, target_scene, target_entrance):
        """Point (scene_id, kind) at the target in every exit table, adding the
        exit (before a kind-255 catch-all, which would otherwise win) or the
        scene's segment where missing."""
        new = {"kind": kind, "scene": target_scene, "entrance": target_entrance, "flag": None, "extra": 0}
        for _, _, segs in exit_tables:
            seg = next((s for s in segs if s.get("scene") == scene_id), None)
            if seg is None:
                end = next(i for i, s in enumerate(segs) if s.get("scene") == EXITS_END)
                seg = {"scene": scene_id, "exits": []}
                segs.insert(end, seg)
            ex = next((e for e in seg["exits"] if e["kind"] == kind), None)
            if ex is not None:
                ex["scene"], ex["entrance"] = target_scene, target_entrance
                continue
            wild = next((i for i, e in enumerate(seg["exits"]) if e["kind"] == ANY_KIND), None)
            seg["exits"].insert(len(seg["exits"]) if wild is None else wild, dict(new))

    def _save(self, ov, tables):
        for o, name, rows in tables:
            if rows == o.rows(name):
                ov.remove(o.id, name)  # same as the scene's own table again
            else:
                ov.set(o.id, name, o.tables[name]["kind"], rows)
        ov.save()
        generate(self.project.root, self.scenes, ov)

    def relink(self, info, scene_id, code, target_scene, target_entrance):
        """Send the door with this code (as scene_id sees it) somewhere else."""
        self._overlays(info, scene_id)  # the scene must use this map
        return self.relink_scene(scene_id, code, target_scene, target_entrance)

    def relink_scene(self, scene_id, code, target_scene, target_entrance, by_kind=False):
        """As relink, for any scene (the world map's icons have no local map).
        by_kind: `code` is the exit kind itself (an area's), not a trigger."""
        self._check_target(target_scene, target_entrance)
        sc = next(s for s in self.scenes.scenes if s["id"] == scene_id)
        overlays = [self.scenes.overlay(sc["overlay"])]
        ov = Overrides(self.project.root)
        events = self._tables(overlays, ov, "events", scene_ids={scene_id})
        kind = code if by_kind else self._exit_kind(events, code)[0]
        if kind is None:
            raise ValueError("that isn't a door in this scene")
        exits = self._tables(overlays, ov, "exits", scene_ids={scene_id})
        self._set_exit(exits, scene_id, kind, target_scene, target_entrance)
        self._save(ov, exits)
        return {"code": code, "kind": kind, "label": self.names.scene_label(target_scene)}

    def add(self, info, scene_id, x, z, target_scene, target_entrance):
        """Make the cell (x, z) a door to the target."""
        self._check_target(target_scene, target_entrance)
        p = self.project
        col = p.load_grid(info, "collision").cells
        if not (0 <= x < 128 and 0 <= z < 128):
            raise ValueError("that cell is outside the map")
        here = col[z][x]
        if 1 <= here <= 239:
            raise ValueError("Something already happens on that square (a door, chest or event). Pick another.")
        overlays = self._overlays(info, scene_id)
        ov = Overrides(p.root)
        events = self._tables(overlays, ov, "events", scene_ids={scene_id})
        exits = self._tables(overlays, ov, "exits", scene_ids={scene_id})
        # Doors take low codes, then 239 downward: chests need 100..239 for their
        # markers and take them from 100 upward. Free in every overlay that can
        # load this map: other scenes on it would otherwise react to the cell.
        every = self._overlays(info)
        taken = self._taken_codes(every, self._tables(every, ov, "events"))
        code = next((c for c in list(range(1, 100)) + list(range(239, 99, -1)) if c not in taken), None)
        if code is None:
            raise ValueError("This place has no room for more doors.")
        # A kind no exit, exit event or region of the overlay uses; high kinds,
        # since scene scripts ask for low ones by number.
        all_exits = self._tables(overlays, ov, "exits")
        all_events = self._tables(overlays, ov, "events")
        used = {e["kind"] for _, _, segs in all_exits for s in segs for e in s.get("exits", [])}
        used |= {r["value"] for _, _, rs in all_events for r in rs if r["control"] & 0xF == EVENT_EXIT}
        for _, _, rs in self._tables(overlays, ov, "regions", need=False):
            used |= {r["value"] for r in rs if r["minX"] != -1}
        kind = next((k for k in range(0xFE, 0, -1) if k not in used), None)
        if kind is None:
            raise ValueError("This place has no room for more doors.")
        for _, _, rows in events:
            end = next(i for i, r in enumerate(rows) if r["control"] == EVENTS_END)
            rows.insert(end, {"control": EVENT_EXIT, "trigger": code, "condition": -1, "value": kind})
        self._set_exit(exits, scene_id, kind, target_scene, target_entrance)
        p.apply_edits(info, [{"plane": "collision", "x": x, "y": z, "value": code}])
        self._save(ov, events + exits)
        return {"code": code, "kind": kind, "was": here, "label": self.names.scene_label(target_scene)}

    def remove(self, info, scene_id, x, z):
        """Turn every cell of the door at (x, z) back into ground; its event and
        exit go too unless another map sharing the tables still uses the code."""
        p = self.project
        col = p.load_grid(info, "collision").cells
        code = col[z][x]
        overlays = self._overlays(info, scene_id)
        ov = Overrides(p.root)
        events = self._tables(overlays, ov, "events", scene_ids={scene_id})
        kind, scripted = self._exit_kind(events, code)
        if kind is None:
            raise ValueError("that isn't a door in this scene")
        if scripted:
            raise ValueError("This door is part of a story scene: you can change where it leads, but not remove it.")
        cells = [(gx, gz) for gx, gz in self._window(info) if col[gz][gx] == code]
        others = [m for m in self._sharing_maps(overlays) if m is not info and any(
            code in line for line in p.load_grid(m, "collision").cells)]
        if not others:
            exits = self._tables(overlays, ov, "exits", scene_ids={scene_id})
            for _, _, rows in events:
                rows[:] = [r for r in rows if not (r["trigger"] == code and r["control"] & 0xF == EVENT_EXIT)]
            for _, _, segs in exits:
                for seg in segs:
                    if seg.get("scene") == scene_id:
                        seg["exits"] = [e for e in seg["exits"] if e["kind"] != kind]
            self._save(ov, events + exits)
        # The cells stay if another scene on this map, with tables of its own,
        # still reacts to that code.
        every = self._overlays(info)
        reader = Overrides(p.root)
        mine = {(o.id, name) for o, name, _ in events}
        still = any(r["trigger"] == code and r["control"] != EVENTS_END
                    for o, name, rs in self._tables(every, reader, "events", scene_ids=self._map_scene_ids(info))
                    if (o.id, name) not in mine for r in rs)
        if not still:
            p.apply_edits(info, [{"plane": "collision", "x": gx, "y": gz,
                                  "value": self._restored_code(info, col, gx, gz, code)} for gx, gz in cells])
        return {"code": code, "cells": 0 if still else len(cells), "tables_kept": bool(others) or still}
