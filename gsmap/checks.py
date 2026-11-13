"""Plain-language checks over every map: what would go wrong in the game.

Each issue says what the player would see, where, and what to do about it.
The original game has quirks of its own (doors left over from cut story
stages, codes nothing uses), so every issue is also looked for in the
unmodified game: the scenes' own tables, and the map files as they are in
the commit the mod starts from (patch.base_commit). Issues found there too
are marked "original" and hidden by default; the rest are what your edits
introduced.
"""

import os
import subprocess

from . import layout
from .i18n import tr
from .chests import CHEST_CONTROL, ChestEditor, MARKER_MAX, placed_codes
from .doors import DoorEditor
from .messages import Messages
from .modgen import Overrides, reconcile
from .sceneedit import EVENTS_END
from .tileset import retired_blocks

_STOCK = {}  # game source root -> keys of the issues the unmodified game has
TEMP_FLAGS = range(0x200, 0x400)  # scene and group temporaries: cleared on entering
CHEST_FLAGS = range(0xE00, 0x1000)


def changed_maps(project):
    """Maps whose files differ from the commit the mod starts from (new maps
    included), or None when that can't be told (no git)."""
    from .patch import base_commit
    from .setup import load_settings
    try:
        settings = load_settings()
    except (OSError, ValueError):
        settings = None
    base = base_commit(project.root, settings)
    if not base:
        return None
    try:
        out = subprocess.run(["git", "diff", "--name-only", base, "--", layout.MAPS],
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
        self._bad_cells = {}  # map number -> _bad_blocks, for one run's two passes

    def run(self):
        self._bad_cells = {}
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
                self._check_map(p, info, doors, chests, add, arrival_numbers, out)
            except Exception as e:  # noqa: BLE001  one damaged place mustn't hide the rest
                if not stock:
                    add("error", "map-unreadable", info,
                        tr("This place's files can't be read, so it can't be checked and the game may not build "
                           "({detail}).", detail=f"{os.path.relpath(info.folder, p.root)}: {type(e).__name__}"),
                        tr("Open it and use Reset place, or Undo."), "read")

        out += self._flag_issues(chests, add, stock)
        try:
            self._world_issues(add, arrival_numbers, stock)
        except Exception as e:  # noqa: BLE001  a world map that can't be read mustn't hide the rest
            if not stock:
                add("error", "world-unreadable", None,
                    tr("The world map's files can't be read, so it can't be checked ({detail}).",
                       detail=type(e).__name__),
                    tr("Open the world map and use Reset world map, or Undo."), "read", place=tr("World map"))
        if not stock:
            out += self._override_issues(add)
        return out

    def _check_map(self, p, info, doors, chests, add, arrival_numbers, out):
        try:
            col = p.load_grid(info, "collision").cells
        except FileNotFoundError:
            return
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
                        tr("A door in {place} leads nowhere: stepping on it does nothing.", place=sname),
                        tr("Link it to a place with the Doors tool, or remove it."),
                        f"{sid}:{d['code']}", cell, "doors", sid)
                elif d.get("fallback"):
                    add("info", "door-fallback", info,
                        tr("A door in {place} has no exit of its own, so the game sends it to {target}, "
                           "arrival point 0, the scene's first exit.", place=sname, target=d["label"]),
                        tr("Give it a destination with the Doors tool if that isn't what you want."),
                        f"{sid}:{d['code']}", cell, "doors", sid)
                elif d["entrance"] not in arrival_numbers(d["scene"]) and arrival_numbers(d["scene"]):
                    add("warning", "door-no-arrival", info,
                        tr("A door in {place} leads to {target}, arrival point {n}, which "
                           "doesn't exist there: the party appears at that place's first arrival point instead.",
                           place=sname, target=d["label"], n=d["entrance"]),
                        tr("Pick an arrival point that exists with the Doors tool."),
                        f"{sid}:{d['code']}", cell, "doors", sid)
        # Chests and Psynergy stones
        markers = p.markers(info)
        # The limit is per scene: on loading, the game places at most MARKER_MAX
        # of the markers that scene's own events make a chest or a Psynergy
        # Stone (treasure_spots.c). A map holding several houses has a scene per
        # house, each counting only its own.
        codes = {code for _, _, code in markers}
        ov = doors._read_overrides()
        for sid in sorted(doors._map_scene_ids(info)):
            try:
                tables = doors._tables(doors._overlays(info, sid), ov, "events", need=False, scene_ids={sid})
            except (ValueError, FileNotFoundError, StopIteration):
                continue
            for _, name, rows in tables:
                # A chest (SEARCH(SEARCH_CHEST)) or a Psynergy Stone (a plain search
                # finding FIND_PSYNERGY_STONE), as treasure_spots.c tells them.
                placed = placed_codes(rows, codes)
                if len(placed) > MARKER_MAX:
                    add("error", "too-many-chests", info,
                        tr("{place} has {n} chests and stones: the game shows only the first {max}.",
                           place=self.names.scene_label(sid), n=len(placed), max=MARKER_MAX),
                        tr("Remove some with the Chest tool."), f"count:{sid}:{name}", None, "chest", sid)
        listed = {(c["x"], c["z"]): c for c in chests.list(info)}
        for x, z, code in markers:
            if not (0 <= z < len(col) and 0 <= x < len(col[0])) or col[z][x] != code:
                add("error", "chest-locked", info,
                    tr("A chest can't be opened: the ground under it doesn't carry its code."),
                    tr("Remove the chest and add it again with the Chest tool."), f"{x},{z}", [x, z], "chest")
            c = listed.get((x, z))
            if c is not None and c["value"] is None and self._scene_count(info):
                add("warning", "chest-empty", info,
                    tr("A chest spot has nothing defined, so no chest appears there."),
                    tr("Remove it, or add a chest there with the Chest tool."), f"{x},{z}", [x, z], "chest")
            elif c and c["chest"] and c["flag"] in TEMP_FLAGS:
                add("warning", "chest-refills", info,
                    tr("The chest with {contents} uses a temporary flag, so it fills up again "
                       "every time you come back.", contents=c["contents"]),
                    tr("Remove it and add it again: the Chest tool picks a permanent flag."),
                    f"{x},{z}", [x, z], "chest")
        # Blocks
        out += self._block_issues(info, add)

    def _block_issues(self, info, add):
        # The map files are the same in both passes (only the scene tables
        # differ), so their cells are looked at once per run.
        if info.number not in self._bad_cells:
            self._bad_cells[info.number] = self._bad_blocks(info)
        found = self._bad_cells[info.number]
        if found is None:
            return []
        self._shape_issues(info, add)
        missing, ghost = found
        if missing:
            add("error", "block-missing", info,
                tr("{n} cell(s) use a block this map doesn't have; they draw garbage.", n=len(missing)),
                tr("Paint over them with the Paint tool."), "missing", missing[0], "block")
        if ghost:
            add("error", "block-retired", info,
                tr("{n} cell(s) use a block whose tiles were reused for an imported image; "
                   "they draw the image's pieces instead.", n=len(ghost)),
                tr("Paint over them with the Paint tool."), "retired", ghost[0], "block")
        return []

    def _bad_blocks(self, info):
        """([x, z] of cells using a block the map lacks, of cells using a retired
        one), or None when the map's files aren't there."""
        p = self.project
        try:
            count = len(p.load_metatiles(info).rows)
            retired = retired_blocks(p, info)
            # Kept with the grid until it changes, for the window, block count
            # and retired blocks it was worked out for. Shared: read-only.
            key = ("bad-blocks", tuple(info.bounds), tuple(map(tuple, info.layers)), tuple(info.priority),
                   count, frozenset(retired))
            return p._parsed(info.grid_path(), lambda path: self._scan_blocks(info, count, retired), key=key)
        except FileNotFoundError:
            return None

    def _scan_blocks(self, info, count, retired):
        p = self.project
        blocks = p.resolved_blocks(info)
        missing, ghost = [], []
        for li in range(len(info.layers)):
            if not info.priority[li]:
                continue
            ox, oz = p.layer_origin(info, li)
            bx, bz = info.bounds[0] // 2, info.bounds[1] // 2
            w, h = info.size
            cols = [(ox + bx + x) % 128 for x in range(w)]
            for z in range(h):
                row = blocks[(oz + bz + z) % 128]
                values = [row[c] & 0xFFF for c in cols]
                # Most rows are fine: look at their few distinct blocks first.
                if not values or (max(values) < count and not retired.intersection(values)):
                    continue
                for x, b in enumerate(values):
                    if b >= count:
                        missing.append([x, z])
                    elif b in retired:
                        ghost.append([x, z])
        return missing, ghost

    def _shape_issues(self, info, add):
        """A cell's height row must exist: past the table the game reads whatever
        comes next in memory as the ground's height."""
        p = self.project
        try:
            rows = len(p.shape_rows(info))
            cells = p.load_grid(info, "shape").cells
        except FileNotFoundError:
            return
        cols = [x % 128 for x in range(info.bounds[0] // 2, info.bounds[2] // 2)]
        bad = 0
        for z in range(info.bounds[1] // 2, info.bounds[3] // 2):
            row = cells[z % 128]
            values = [row[c] for c in cols]
            if values and max(values) >= rows:
                bad += sum(1 for v in values if v >= rows)
        if bad:
            add("error", "height-missing", info,
                tr("{n} square(s) here use a height this place doesn't have, so the game reads nonsense "
                   "for how high the ground is.", n=bad),
                tr("Repaint them with the Height tool."), "shape", None, "shape")

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
            joined = places[0]
            for other in places[1:]:
                joined = tr("{list} and {last}", list=joined, last=other)
            add("warning", "chest-shared-flag", None,
                tr("{n} chests share one \"opened\" flag ({places}): opening one "
                   "makes the others appear opened.", n=len(who), places=joined),
                tr("Remove the newer chest and add it again: the Chest tool picks a fresh flag."),
                f"{flag:#x}", place=joined)
        return []

    def _world_issues(self, add, arrival_numbers, stock):
        """Step spots and town icons on the world map that lead nowhere, or to an
        arrival point their place doesn't have."""
        from . import world as worldmod
        w = worldmod.World(self.project.root)
        places = worldmod.world_places(w, self.project, self.scenes, self.names, stock=stock)
        where = tr("World map")
        things = [(tr("A step spot at {x},{y}", x=s["gx"], y=s["gy"]), s["lead"], f"step:{s['code']}") for s in places["steps"]]
        things += [(tr("The icon for {place}", place=ic["lead"]["label"]) if ic["lead"] and ic["lead"]["label"]
                    else tr("A town icon"), ic["lead"], f"icon:{ic['actor']}") for ic in places["icons"] if ic["x"] or ic["z"]]
        seen = set()
        for what, lead, key in things:
            if not lead or lead.get("scripted") or key in seen:
                continue  # a scene script decides where it leads; a wide spot is said once
            seen.add(key)
            if lead["scene"] is None:
                add("warning", "world-nowhere", None,
                    tr("{what} on the world map leads nowhere: touching it does nothing.", what=what),
                    tr("Link it to a place with the Towns or Step spots tool, or remove it."), key, tool="world", place=where)
            elif lead["entrance"] not in arrival_numbers(lead["scene"]) and arrival_numbers(lead["scene"]):
                add("warning", "world-no-arrival", None,
                    tr("{what} on the world map leads to {target}, arrival point {n}, which doesn't exist there: "
                       "the party appears at that place's first arrival point instead.",
                       what=what, target=lead["label"], n=lead["entrance"]),
                    tr("Pick an arrival point that exists with the Towns or Step spots tool."), key, tool="world", place=where)

    def _override_issues(self, add):
        """Edits kept for scene tables that no longer exist or changed shape."""
        ov = Overrides(self.project.root)
        for t in reconcile(ov, self.scenes):
            add("error", "override-stale", None,
                tr("An edit of yours ({table}) was made for an older version of the game source "
                   "and no longer fits, so it's left out of your game for now.", table=t["symbol"]),
                tr("Redo that edit, or remove it with Revert to original in the Story and scene panel."), t["symbol"])
        for n, text, why in Messages(self.project.root).bad_lines():
            shown = " ".join(text.replace("{page_break}", " ").replace("{end_wait}", "").split())
            add("error", "text-unbuildable", None,
                tr("A line you wrote, “{line}”, can't be built. {why}", line=shown, why=why),
                tr("Change its words in the Events panel, or use Undo."), n)
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
        return self.names.scene_label(sc["id"]) if sc else tr("overlay {n}", n=f"{ovl:#x}")

    def _scene_count(self, info):
        rows = {r["row"] for r in [info.resources] + info.alternates if r}
        return len(self.scenes.for_rows(rows))

    def _place(self, info):
        if info is None:
            return None
        rows = {r["row"] for r in [info.resources] + info.alternates if r}
        scs = self.scenes.for_rows(rows)
        return self.names.scene_label(scs[0]["id"]) if scs else tr("map {n}", n=info.number)
