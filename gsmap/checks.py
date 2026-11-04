"""Plain-language checks over every map: what would go wrong in the game.

Each issue says what the player would see, where, and what to do about it.
The original game has quirks of its own (doors left over from cut story
stages, codes nothing uses), so every issue is also looked for in the
unmodified game: the scenes' own tables, and the map files as they are on
alchemy's `main` branch. Issues found there too are marked "original" and
hidden by default; the rest are what your edits introduced.
"""

import os
import subprocess

from . import layout
from .chests import CHEST_CONTROL, ChestEditor, MARKER_MAX
from .doors import DoorEditor
from .modgen import Overrides, reconcile
from .sceneedit import EVENTS_END
from .tileset import retired_blocks

_STOCK = {}  # game source root -> keys of the issues the unmodified game has
TEMP_FLAGS = range(0x200, 0x400)  # scene and group temporaries: cleared on entering
CHEST_FLAGS = range(0xE00, 0x1000)


def changed_maps(project):
    """Maps whose files differ from alchemy's main branch (new maps included),
    or None when that can't be told (no git, no main)."""
    try:
        out = subprocess.run(["git", "diff", "--name-only", "main", "--", layout.MAPS],
                             cwd=project.root, capture_output=True, text=True, timeout=60)
        untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "--", layout.MAPS],
                                   cwd=project.root, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    paths = {os.path.join(project.root, p) for p in (out.stdout + untracked.stdout).split()}
    folders = {os.path.dirname(p) for p in paths}
    # A map's tables can live in another map's folder (maps 174 to 179 draw map_001's).
    return {n for n, m in project.maps.items()
            if m.folder in folders or {m.grid_path(), m.source("CELL_PICTURES", "cell_pictures.tsv")} & paths}


class Checker:
    def __init__(self, project, scenes, names):
        self.project, self.scenes, self.names = project, scenes, names

    def run(self):
        changed = changed_maps(self.project)
        mine = self._issues(stock=False)
        # What the unmodified game has doesn't change while the editor runs. On a
        # map you've edited it's not consulted (see below), so one pass does.
        stock = _STOCK.get(self.project.root)
        if stock is None:
            stock = _STOCK[self.project.root] = {i["key"] for i in self._issues(stock=True)}
        for i in mine:
            # Original: the unmodified game has it too, on a map we didn't change.
            i["original"] = i["key"] in stock and (changed is None or i.get("map") not in changed)
        order = {"error": 0, "warning": 1, "info": 2}
        mine.sort(key=lambda i: (i["original"], order[i["severity"]], i.get("map") or "", i["message"]))
        return mine

    # ---- all checks, against the mod or the stock tables -------------------------

    def _issues(self, stock):
        p = self.project
        doors = DoorEditor(p, self.scenes, self.names, stock=stock)
        chests = ChestEditor(p, self.scenes, self.names, stock=stock)
        out = []

        def add(severity, kind, info, message, fix, key, cell=None, tool="view", scene=None, place=None):
            out.append({"severity": severity, "kind": kind, "map": info.number if info else None,
                        "place": place or self._place(info), "cell": cell, "tool": tool, "scene": scene,
                        "message": message, "fix": fix, "key": f"{kind}:{info.number if info else ''}:{key}"})

        arrivals = {}

        def arrival_numbers(scene_id):
            if scene_id not in arrivals:
                try:
                    arrivals[scene_id] = {e["entrance"] for e in doors.entrances(scene_id)}
                except (StopIteration, FileNotFoundError, ValueError):
                    arrivals[scene_id] = set()
            return arrivals[scene_id]

        for n, info in sorted(p.maps.items()):
            if not info.resources:
                continue
            try:
                col = p.load_grid(info, "collision").cells
            except FileNotFoundError:
                continue
            # Doors
            try:
                by_scene = doors.list(info)
            except (ValueError, FileNotFoundError):
                by_scene = {}
            for sid, ds in by_scene.items():
                sname = self.names.scene_label(sid)
                for d in ds:
                    cell = d["cells"][0]
                    if d["scene"] is None:
                        add("warning", "door-nowhere", info,
                            f"A door in {sname} leads nowhere: stepping on it does nothing.",
                            "Link it to a place with the Doors tool, or remove it.",
                            f"{sid}:{d['code']}", cell, "doors", sid)
                    elif d.get("fallback"):
                        add("info", "door-fallback", info,
                            f"A door in {sname} has no exit of its own, so the game sends it to {d['label']}, "
                            "arrival point 0, the scene's first exit.",
                            "Give it a destination with the Doors tool if that isn't what you want.",
                            f"{sid}:{d['code']}", cell, "doors", sid)
                    elif d["entrance"] not in arrival_numbers(d["scene"]) and arrival_numbers(d["scene"]):
                        add("warning", "door-no-arrival", info,
                            f"A door in {sname} leads to {d['label']}, arrival point {d['entrance']}, which "
                            "doesn't exist there: the party appears at that place's first arrival point instead.",
                            "Pick an arrival point that exists with the Doors tool.",
                            f"{sid}:{d['code']}", cell, "doors", sid)
            # Chests and Psynergy stones
            markers = p.markers(info)
            if len(markers) > MARKER_MAX:
                add("error", "too-many-chests", info,
                    f"{len(markers)} chests and stones: the game shows only the first {MARKER_MAX}.",
                    "Remove some with the Chest tool.", "count", None, "chest")
            listed = {(c["x"], c["z"]): c for c in chests.list(info)}
            for x, z, code in markers:
                if not (0 <= z < len(col) and 0 <= x < len(col[0])) or col[z][x] != code:
                    add("error", "chest-locked", info,
                        "A chest can't be opened: the ground under it doesn't carry its code.",
                        "Remove the chest and add it again with the Chest tool.", f"{x},{z}", [x, z], "chest")
                c = listed.get((x, z))
                if c is not None and c["value"] is None and self._scene_count(info):
                    add("warning", "chest-empty", info,
                        "A chest spot has nothing defined, so no chest appears there.",
                        "Remove it, or add a chest there with the Chest tool.", f"{x},{z}", [x, z], "chest")
                elif c and c["chest"] and c["flag"] in TEMP_FLAGS:
                    add("warning", "chest-refills", info,
                        f"The chest with {c['contents']} uses a temporary flag, so it fills up again "
                        "every time you come back.",
                        "Remove it and add it again: the Chest tool picks a permanent flag.",
                        f"{x},{z}", [x, z], "chest")
            # Blocks
            out += self._block_issues(info, add)

        out += self._flag_issues(chests, add, stock)
        if not stock:
            out += self._override_issues(add)
        return out

    def _block_issues(self, info, add):
        p = self.project
        try:
            blocks = p.resolved_blocks(info)
            count = len(p.load_metatiles(info).rows)
        except FileNotFoundError:
            return []
        self._shape_issues(info, add)
        retired = retired_blocks(p, info)
        missing, ghost = [], []
        for li in range(len(info.layers)):
            if not info.priority[li]:
                continue
            ox, oz = p.layer_origin(info, li)
            bx, bz = info.bounds[0] // 2, info.bounds[1] // 2
            w, h = info.size
            for z in range(h):
                for x in range(w):
                    b = blocks[(oz + bz + z) % 128][(ox + bx + x) % 128] & 0xFFF
                    if b >= count:
                        missing.append([x, z])
                    elif b in retired:
                        ghost.append([x, z])
        if missing:
            add("error", "block-missing", info,
                f"{len(missing)} cell(s) use a block this map doesn't have; they draw garbage.",
                "Paint over them with the Block tool.", "missing", missing[0], "block")
        if ghost:
            add("error", "block-retired", info,
                f"{len(ghost)} cell(s) use a block whose tiles were reused for an imported image; "
                "they draw the image's pieces instead.",
                "Paint over them with the Block tool.", "retired", ghost[0], "block")
        return []

    def _shape_issues(self, info, add):
        """A cell's height row must exist: past the table the game reads whatever
        comes next in memory as the ground's height."""
        p = self.project
        try:
            rows = len(p.shape_rows(info))
            cells = p.load_grid(info, "shape").cells
        except FileNotFoundError:
            return
        bad = sum(1 for z in range(info.bounds[1] // 2, info.bounds[3] // 2) for x in range(info.bounds[0] // 2, info.bounds[2] // 2)
                  if cells[z % 128][x % 128] >= rows)
        if bad:
            add("error", "height-missing", info,
                f"{bad} square(s) here use a height this place doesn't have, so the game reads nonsense "
                "for how high the ground is.",
                "Repaint them with the Height tool.", "shape", None, "shape")

    def _flag_issues(self, chests, add, stock):
        """Chests sharing an "opened" flag open together."""
        ov = chests._read_overrides()
        owners = {}  # flag -> {(overlay, trigger)}
        for o in {self.scenes.overlay(s["overlay"]) for s in self.scenes.scenes
                  if self._overlay_exists(s["overlay"])}:
            for _, name, rows in chests._tables([o], ov, "events", need=False) if self._all_editable(o, "events") else []:
                for r in rows:
                    if r["control"] == EVENTS_END:
                        break
                    if r["control"] & 0x1FF == CHEST_CONTROL and r["condition"] >= 0:
                        owners.setdefault(r["condition"], set()).add((o.id, r["trigger"], r["value"]))
        for flag, who in owners.items():
            # The same code and contents under one flag is one chest, on a map
            # two scenes load, not two chests sharing.
            if len({(trigger, value) for _, trigger, value in who}) < 2:
                continue
            places = sorted({self._overlay_place(o) for o, _, _ in who})
            add("warning", "chest-shared-flag", None,
                f"{len(who)} chests share one \"opened\" flag ({' and '.join(places)}): opening one "
                "makes the others appear opened.",
                "Remove the newer chest and add it again: the Chest tool picks a fresh flag.",
                f"{flag:#x}", place=" and ".join(places))
        return []

    def _override_issues(self, add):
        """Edits kept for scene tables that no longer exist or changed shape."""
        ov = Overrides(self.project.root)
        for t in reconcile(ov, self.scenes):
            add("error", "override-stale", None,
                f"An edit of yours ({t['symbol']}) was made for an older version of the game source "
                "and no longer fits, so it's left out of your game for now.",
                "Redo that edit, or remove it with Forget stale edits.", t["symbol"])
        return []

    # ---- helpers ---------------------------------------------------------------------

    def _overlay_exists(self, ovl):
        try:
            self.scenes.overlay(ovl)
            return True
        except FileNotFoundError:
            return False

    @staticmethod
    def _all_editable(o, kind):
        return all(t["editable"] for t in o.tables.values() if t["kind"] == kind)

    def _overlay_place(self, ovl):
        sc = next((s for s in self.scenes.scenes if s["overlay"] == ovl), None)
        return self.names.scene_label(sc["id"]) if sc else f"overlay {ovl:#x}"

    def _scene_count(self, info):
        rows = {r["row"] for r in [info.resources] + info.alternates if r}
        return len(self.scenes.for_rows(rows))

    def _place(self, info):
        if info is None:
            return None
        rows = {r["row"] for r in [info.resources] + info.alternates if r}
        scs = self.scenes.for_rows(rows)
        return self.names.scene_label(scs[0]["id"]) if scs else f"map {info.number}"
