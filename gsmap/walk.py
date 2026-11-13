"""Where the party can walk on a map, and where a person can stand, by the
game's own rules (alchemy's games/tbs/src/field):

- A step is 8 pixels, and is taken only when five probes 8 pixels out, straight
  ahead and 22.5 and 45 degrees either side, are clear (player_control.c).
- A probe is clear unless its cell is a wall (cell behavior 255), or its ground
  is more than 8 pixels above, or 12 below, the ground the walker stands on
  (terrain.c, MapGrid_CheckCollision).
- Heights come from each cell's shape: a kind and up to three samples, read by
  one of sixteen functions (terrain.c), with two tables (terrain_tables.c).
- A ledge (252) is hopped down, a climbing spot (253) climbed, a gap (254)
  jumped two cells forward (field/README.md, "Cells that act on their own").
- Talking reaches the nearest person within 32 pixels and 48 above or below
  (field/README.md, "Talking"). Two people bump when they come within their
  radii less 2 pixels each: 8 for a standard sprite, so 12 apart.
- A step trigger whose script slides the leader (Imil's ice) is followed as
  Imil_RunIceSlide does: cell by cell until a wall, ground more than 8 pixels
  up, or another kind of cell.

The party is followed from every arrival point of the scene. Psynergy and story
events that change cells are not followed, so a place they open shows as cut
off. People are not obstacles, except the one being checked.
"""

import collections
import math
import os
import re

from . import layout
from .i18n import N_, tr, translate

WALL, LEDGE, CLIMB, GAP = 255, 252, 253, 254
FIXED = 1 << 16
STEP_UP, STEP_DOWN = 8 * FIXED, 12 * FIXED
TALK_REACH, TALK_HEIGHT = 32, 48
BUMP = 12              # two standard radii of 8, less 2 each
GRID = 8               # walking is followed on an 8-pixel lattice
SEARCH_REACH = 16      # a search looks at the cell 16 pixels ahead
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
SOUTH, NORTH = (0, 1), (0, -1)
# The five probes of a step, as (cos, sin) turns of the heading.
PROBES = tuple((math.cos(math.radians(a)), math.sin(math.radians(a))) for a in (0, 22.5, -22.5, 45, -45))
# Each heading's probes as offsets from where the walker stands, worked out the
# way Walk._step_ok always has: 8 * (dx * c - dz * s), 8 * (dz * c + dx * s).
PROBE_OFFSETS = {(dx, dz): tuple((8 * (dx * c - dz * s), 8 * (dz * c + dx * s)) for c, s in PROBES)
                 for dx, dz in DIRS}

TABLES = f"{layout.SRC}/field/terrain_tables.c"


def _tables(games_root):
    """gTerrain_LerpWeightTable and gTerrain_SampleIndexTable, read from the checkout."""
    path = os.path.join(games_root, TABLES)
    with open(path, encoding="utf-8") as f:
        text = re.sub(r"/\*.*?\*/|//[^\n]*", "", f.read(), flags=re.S)
    out = []
    for name in ("gTerrain_LerpWeightTable", "gTerrain_SampleIndexTable"):
        m = re.search(rf"{name}\s*\[\s*256\s*\]\s*=\s*\{{(.*?)\}}", text, re.S)
        if not m:
            raise ValueError(f"{name} isn't in {TABLES}")
        values = [int(v, 0) for v in re.findall(r"0x[0-9a-fA-F]+|\d+", m.group(1))]
        if len(values) != 256:
            raise ValueError(f"{name} doesn't have 256 entries")
        out.append(values)
    return out


def _tdiv(a, b):
    """C's division, which rounds towards zero."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def height_at(row, x, y, lerp, index):
    """Ground height (16.16 pixels) at pixel (x, y) of a cell whose shape row is
    [kind, s0, s1, s2] as unsigned bytes. Follows terrain.c line for line."""
    if not row:
        return 0
    kind = row[0] & 15
    raw = row[1:4]
    s = [v - 256 if v > 127 else v for v in raw]

    def f(v):
        return v * (1 << 19)  # a sample is 8 pixels

    if kind in (0, 14, 15):
        return f(s[0])
    if kind in (1, 2):
        t = x if kind == 1 else y
        start = f(s[0])
        d = (f(s[1]) - start) * t
        if d < 0:
            d += 15
        return start + (d >> 4)
    if kind in (3, 4):
        first, second = f(s[0]), f(s[1])
        higher = max(first, second)
        v = x + y if kind == 3 else y - x + 15
        if v == 15:
            return higher
        return first if v < 15 else second
    if kind == 5:
        first, mid, last = f(s[0]), f(s[1]), f(s[2])
        v = x + y
        if v == 15:
            return mid
        if v < 15:
            return first + _tdiv((mid - first) * v, 15)
        return mid + _tdiv((last - mid) * (v - 15), 15)
    if kind == 6:
        first, mid, last = f(s[0]), f(s[1]), f(s[2])
        pd = y - x
        v = pd + 15
        if v == 15:
            return mid
        if 0 <= v < 15:
            p = (mid - first) * v
            if p < 0:
                p += 15
            return first + (p >> 4)
        p = pd * (last - mid)
        if p < 0:
            p += 15
        return mid + (p >> 4)
    if kind == 7:
        start = f(s[0])
        return start + (f(s[1]) - start) * lerp[x + y * 16]
    if kind in (8, 9):
        t = x if kind == 8 else y
        return f(s[0] if t < 8 else s[1])
    if kind in (10, 11):
        v = s if kind == 10 else raw  # TERRAIN_BEND_Y reads its samples unsigned
        t = x if kind == 10 else y
        end, mid = f(v[0]), f(v[1])
        if t < 8:
            d = (mid - end) * t
            if d < 0:
                d += 7
            return end + (d >> 3)
        d = (f(v[2]) - mid) * (t - 8)
        if d < 0:
            d += 7
        return mid + (d >> 3)
    if kind == 12:
        return f(s[index[x + (y << 4)]])
    # kind 13: the same table mirrored left to right
    return f(s[index[(y << 4) - x + 15]])


class Walk:
    """The walking graph of one map for one scene, on layer 0 (the layer actor
    placements stand on: Event_SpawnActorPlacements reads its height).

    Positions are map pixels, as actor placements and entrances store them.
    `edits` is a list of {plane, x, y, value} grid edits not yet saved, and
    `shapes` the heights made in the editor but not yet saved, as
    [kind, h0, h1, h2] after the table's own (shape edits name them by index)."""

    def __init__(self, project, info, events, entrances, edits=(), shapes=()):
        self.info = info
        self.ox, self.oz = project.layer_origin(info, 0)
        self.x0, self.z0 = info.bounds[0] * 8, info.bounds[1] * 8
        self.w, self.h = info.size
        self.col = [row[:] for row in project.load_grid(info, "collision").cells]
        self.shp = [row[:] for row in project.load_grid(info, "shape").cells]
        for e in edits or ():
            grid = {"collision": self.col, "shape": self.shp}.get(e.get("plane"))
            if grid is not None:
                grid[int(e["y"])][int(e["x"])] = int(e["value"])
        self.rows = [[v + 256 if v < 0 else v for v in r] for r in project.shape_rows(info)]
        self.rows += [[int(v) & 0xFF for v in r[:4]] for r in shapes or ()]
        self.lerp, self.index = _tables(project.root)
        self.events = events
        self.entrances = entrances
        self.slide = {e["trigger"] for e in events
                      if e["kind"] == "touch" and "slide" in (e.get("script") or "").lower()}
        self._heights = {}  # shape id -> its 16x16 heights, row-major (16.16 pixels)
        self._before = {}  # arrival lattice point -> (reach, standing) with no one in the way
        self._standable = {}  # lattice point -> whether standing() keeps it
        self._build()

    # ---- the map, in map pixels ------------------------------------------------------

    def inside(self, x, z):
        return self.x0 <= x < self.x0 + self.w * 16 and self.z0 <= z < self.z0 + self.h * 16

    def grid_cell(self, x, z):
        """The 128x128 grid cell under map pixel (x, z) on layer 0."""
        return (self.ox + int(x) // 16) % 128, (self.oz + int(z) // 16) % 128

    def behavior(self, x, z):
        gx, gz = self.grid_cell(x, z)
        return self.col[gz][gx]

    def ground(self, x, z):
        """Ground height at map pixel (x, z), 16.16 pixels."""
        x, z = int(x), int(z)
        v = self.shp[(self.oz + z // 16) % 128][(self.ox + x // 16) % 128]
        heights = self._heights.get(v)
        if heights is None:
            heights = self._shape_heights(v)
        return heights[(z & 15) * 16 + (x & 15)]

    def _shape_heights(self, v):
        """height_at over every pixel of a cell of shape v, row-major."""
        row = self.rows[v] if v < len(self.rows) else None
        heights = self._heights[v] = [height_at(row, px, pz, self.lerp, self.index)
                                      for pz in range(16) for px in range(16)]
        return heights

    def ground_px(self, x, z):
        return self.ground(x, z) / FIXED

    # ---- the graph ------------------------------------------------------------------

    def _node(self, x, z):
        """The lattice point nearest map pixel (x, z)."""
        return (int(round((x - self.x0) / GRID)) * GRID + self.x0, int(round((z - self.z0) / GRID)) * GRID + self.z0)

    def _clear(self, x, z, ground):
        if not self.inside(x, z) or self.behavior(x, z) == WALL:
            return False
        d = self.ground(x, z) - ground
        return -STEP_DOWN <= d <= STEP_UP

    def _step_ok(self, x, z, dx, dz):
        # _clear for each probe, written out: this runs for every lattice point.
        g = self.ground(x, z)
        x0, z0 = self.x0, self.z0
        x1, z1 = x0 + self.w * 16, z0 + self.h * 16
        col, shp, ox, oz, heights = self.col, self.shp, self.ox, self.oz, self._heights
        floor = math.floor
        for ax, az in PROBE_OFFSETS[(dx, dz)]:
            px, pz = floor(x + ax), floor(z + az)
            if not (x0 <= px < x1 and z0 <= pz < z1):
                return False
            gx, gz = (ox + px // 16) % 128, (oz + pz // 16) % 128
            if col[gz][gx] == WALL:
                return False
            v = shp[gz][gx]  # self.ground(px, pz), written out
            d = (heights.get(v) or self._shape_heights(v))[(pz & 15) * 16 + (px & 15)] - g
            if not -STEP_DOWN <= d <= STEP_UP:
                return False
        return True

    def _slide_end(self, x, z, dx, dz):
        """Where Imil_RunIceSlide leaves the leader who has just stepped onto
        the slide cell under (x, z) going (dx, dz): a cell centre."""
        cx, cz = (int(x) // 16) * 16 + 8, (int(z) // 16) * 16 + 8
        start = self.behavior(cx, cz)
        passed = [(cx, cz)]
        while True:
            nx, nz = cx + 16 * dx, cz + 16 * dz
            if (not self.inside(nx, nz) or self.behavior(nx, nz) == WALL
                    or self.ground(nx, nz) - self.ground(cx, cz) > STEP_UP):
                return (cx, cz), passed
            cx, cz = nx, nz
            passed.append((cx, cz))
            if self.behavior(cx, cz) != start:
                return (cx, cz), passed

    def _moves(self, x, z):
        """[(to, kind)] from lattice point (x, z): kind is walk, slide, hop, climb or jump."""
        out = []
        here = self.behavior(x, z)
        for dx, dz in DIRS:
            tx, tz = x + GRID * dx, z + GRID * dz
            ahead = self.behavior(tx, tz) if self.inside(tx, tz) else WALL
            if self._step_ok(x, z, dx, dz):
                if ahead in self.slide and self.grid_cell(tx, tz) != self.grid_cell(x, z):
                    end, _ = self._slide_end(tx, tz, dx, dz)
                    out.append((end, "slide"))
                else:
                    out.append(((tx, tz), "walk"))
                continue
            # The field's own cells answer a push the probes refused.
            if (dx, dz) == SOUTH and LEDGE in (here, ahead):
                g = self.ground(x, z)
                for k in range(2, 10):
                    lx, lz = x, z + GRID * k
                    if not self.inside(lx, lz) or self.behavior(lx, lz) == WALL:
                        break
                    if self.behavior(lx, lz) != LEDGE and self.ground(lx, lz) < g:
                        out.append(((lx, lz), "hop"))
                        break
            if (dx, dz) in (NORTH, SOUTH) and CLIMB in (here, ahead):
                for k in range(1, 40):
                    lx, lz = x, z + GRID * dz * k
                    if not self.inside(lx, lz) or self.behavior(lx, lz) == WALL:
                        break
                    if self.behavior(lx, lz) != CLIMB and k > 1:
                        out.append(((lx, lz), "climb"))
                        break
            if ahead == GAP:
                lx, lz = x + 32 * dx, z + 32 * dz
                if self.inside(lx, lz) and self.behavior(lx, lz) != WALL:
                    out.append(((lx, lz), "jump"))
        return out

    def _build(self):
        self.nodes = [(self.x0 + i * GRID, self.z0 + j * GRID)
                      for j in range(self.h * 16 // GRID) for i in range(self.w * 16 // GRID)]
        self.edges = {}
        self.slide_ends = set()
        for n in self.nodes:
            if self.behavior(*n) == WALL:
                continue
            moves = self._moves(*n)
            self.edges[n] = moves
            self.slide_ends.update(m for m, k in moves if k == "slide")
        self.starts = []
        for e in self.entrances:
            if self.inside(e["x"], e["z"]):
                self.starts.append((e, self._node(e["x"], e["z"])))
        self.reach = self.flood()

    def _near(self, x, z, reach):
        """Lattice points within `reach` pixels of (x, z): every point the
        graph has is one (x0 + 8i, z0 + 8j), so this is all a test of
        distance can find. A sorted list of (point, distance)."""
        out = []
        i0 = math.ceil((x - reach - self.x0) / GRID)
        j0 = math.ceil((z - reach - self.z0) / GRID)
        for j in range(j0, math.floor((z + reach - self.z0) / GRID) + 1):
            for i in range(i0, math.floor((x + reach - self.x0) / GRID) + 1):
                p = (self.x0 + i * GRID, self.z0 + j * GRID)
                out.append((p, math.hypot(p[0] - x, p[1] - z)))
        return out

    def flood(self, blocked=None, starts=None):
        """Lattice points reachable from the arrival points (or `starts`),
        never coming within BUMP of `blocked` (a map pixel point)."""
        # Only graph points are ever added, and those are lattice points, so
        # the ones too near `blocked` can be listed beforehand.
        near = {p for p, d in self._near(*blocked, BUMP) if d < BUMP} if blocked is not None else ()
        edges = self.edges
        seen = set()
        q = collections.deque()
        for n in (starts if starts is not None else [s for _, s in self.starts]):
            if n in edges and n not in seen:
                seen.add(n)
                q.append(n)
        add, push, pop = seen.add, q.append, q.popleft
        while q:
            n = pop()
            for m, _ in edges.get(n, ()):
                if m not in seen and m in edges and m not in near:
                    add(m)
                    push(m)
        return seen

    def standing(self, reach=None):
        """Reachable points where the party can stop: not partway along a slide."""
        reach = self.reach if reach is None else reach
        out = set()
        known = self._standable
        for n in reach:
            ok = known.get(n)
            if ok is None:
                # On a slide cell only where a slide ends.
                ok = known[n] = self.behavior(*n) not in self.slide or n in self.slide_ends
            if ok:
                out.add(n)
        return out

    # ---- what a spot means ----------------------------------------------------------

    def talk_points(self, x, z, standing):
        """Standing points from which a person at (x, z) can be talked to."""
        g = self.ground_px(x, z)
        return [s for s in standing
                if math.hypot(s[0] - x, s[1] - z) <= TALK_REACH and abs(self.ground_px(*s) - g) <= TALK_HEIGHT]

    def _can_talk(self, x, z, standing):
        """bool(talk_points(x, z, standing)) for a set of lattice points,
        looking only at the points within reach."""
        g = self.ground_px(x, z)
        return any(d <= TALK_REACH and p in standing and abs(self.ground_px(*p) - g) <= TALK_HEIGHT
                   for p, d in self._near(x, z, TALK_REACH))

    def targets(self):
        """What must stay reachable: [(label, test(standing) -> bool)]."""
        out = []

        def cell_px(gx, gz):
            return ((gx - self.ox) % 128) * 16 + 8, ((gz - self.oz) % 128) * 16 + 8

        for e in self.events:
            cells = [cell_px(*c) for c in e.get("cells") or []]
            if e["kind"] == "exit" and cells:
                label = _way_to(e.get("does") or tr("a way out"))
                out.append((label, cells, "step"))
            elif e["kind"] == "touch" and cells and e["trigger"] not in self.slide:
                name = (e.get("script") or "").lower()
                label = tr("a door") if "door" in name else tr("a way out") if ("exit" in name or "leave" in name) \
                    else tr("a spot where something happens")
                out.append((label, cells, "step"))
            elif e["kind"] == "search" and cells:
                out.append((e.get("what") or tr("something to search"), cells, "search"))
        return out

    def target_reached(self, cells, how, reach, standing):
        if how == "step":
            return any(self._node(*c) in reach or (c[0] - 4, c[1] - 4) in reach for c in cells)
        # A search looks 16 pixels ahead: stand next to the cell.
        return any(math.hypot(s[0] - c[0], s[1] - c[1]) <= SEARCH_REACH + 6 and self.grid_cell(*s) != self.grid_cell(*c)
                   for c in cells for s in standing)

    def cells(self):
        """Per window cell (row-major, w x h): what standing a person there means.
        good: the party can walk up and stand here; talk: the party can't stand
        here but can talk to someone here from nearby; slide: a slide cell
        (someone there is in the way of a slide); trigger: a door, exit or step
        spot (keep it clear); cut: the party can't get near; wall: a wall."""
        standing = self.standing()
        stand_cells = {}
        for s in standing:
            stand_cells.setdefault(((s[0] - self.x0) // 16, (s[1] - self.z0) // 16), []).append(s)
        trig = set()
        for _, cells, how in self.targets():
            if how == "step":
                for c in cells:
                    trig.add(((c[0] - self.x0) // 16, (c[1] - self.z0) // 16))
        out = []
        index = collections.defaultdict(list)
        for s in standing:
            index[(s[0] // 32, s[1] // 32)].append(s)
        for j in range(self.h):
            for i in range(self.w):
                x, z = self.x0 + i * 16 + 8, self.z0 + j * 16 + 8
                b = self.behavior(x, z)
                if b == WALL:
                    out.append("wall")
                elif (i, j) in trig:
                    out.append("trigger")
                elif b in self.slide:
                    out.append("slide")
                elif (i, j) in stand_cells and (x, z) in standing:
                    out.append("good")
                else:
                    near = [s for dx in (-1, 0, 1) for dz in (-1, 0, 1) for s in index[(x // 32 + dx, z // 32 + dz)]]
                    out.append("talk" if self.talk_points(x, z, near) else "cut")
        return out

    def check(self, x, z, ignore=None):
        """Problems with a person standing at map pixels (x, z), each
        {kind, text}: what the player would meet, in plain words."""
        return self.review(x, z, ignore)[0]

    def review(self, x, z, ignore=None):
        """(problems, notes) for a person standing at map pixels (x, z). Notes
        are worth knowing but nothing goes wrong."""
        problems, notes = [], []
        if not self.inside(x, z):
            return [{"kind": "outside", "text": tr("That's outside the map.")}], []
        b = self.behavior(x, z)
        g = self.ground_px(x, z)
        if b == WALL:
            problems.append({"kind": "wall", "text": tr("This square is a wall, so they'd stand inside it.")})
        drawn = z - g
        if drawn < self.z0:
            problems.append({"kind": "offscreen",
                             "text": tr("The ground here is {n} pixels high, so they'd be drawn above the top of the map, "
                                        "off screen.", n=f"{g:g}")})
        standing = self.standing()
        for label, cells, how in self.targets():
            if how == "step" and any(self.grid_cell(*c) == self.grid_cell(x, z) for c in cells):
                problems.append({"kind": "trigger", "text": tr("This square is {what}. Someone standing on it would be "
                                                               "in the way.", what=label)})
        talk = self.talk_points(x, z, standing)
        if b in self.slide:
            if [s for s in talk if self.behavior(*s) not in self.slide]:
                text = tr("This is ice the party slides across. They could be talked to from the edge, "
                          "but they'd be in the way of anyone sliding past.")
            else:
                text = tr("This is ice the party slides across. They can't stop next to someone here, so nobody could "
                          "talk to them.")
            problems.append({"kind": "slide", "text": text})
        elif talk and (self._node(x, z) not in standing or self.behavior(*self._node(x, z)) == WALL):
            notes.append({"kind": "talk", "text": tr("The party can't walk onto this square, but can talk to them from "
                                                     "beside it.")})
        elif not talk and b != WALL:
            near = min(standing, key=lambda s: math.hypot(s[0] - x, s[1] - z), default=None)
            if near is not None:
                dh = g - self.ground_px(*near)
                if abs(dh) > TALK_HEIGHT and math.hypot(near[0] - x, near[1] - z) <= TALK_REACH and dh > 0:
                    text = tr("The party can't get near enough to talk: the ground here is {n} levels higher than "
                              "the path beside it.", n=f"{round(abs(dh) / 8, 1):g}")
                elif abs(dh) > TALK_HEIGHT and math.hypot(near[0] - x, near[1] - z) <= TALK_REACH:
                    text = tr("The party can't get near enough to talk: the ground here is {n} levels lower than "
                              "the path beside it.", n=f"{round(abs(dh) / 8, 1):g}")
                elif dh > 8:
                    text = tr("The party can't get near enough to talk: the ground here is {n} levels higher than "
                              "the nearest path, too steep to step up.", n=f"{round(dh / 8, 1):g}")
                elif dh < -12:
                    text = tr("The party can't get near enough to talk: the ground here is {n} levels lower than "
                              "the nearest path, too far to step down.", n=f"{round(-dh / 8, 1):g}")
                else:
                    text = tr("The party can't get near enough to talk: walls or steep ground close it off.")
            else:
                text = tr("The party can't get near enough to talk: there's nowhere to walk on this map.")
            problems.append({"kind": "cut", "text": text})
        if b != WALL:
            lost = self.blocked_by(x, z, ignore)
            if lost:
                problems.append({"kind": "blocks", "text": tr("Standing here would cut the party off from {what}.",
                                                              what=_summary(lost))})
        return problems, notes

    def blocked_by(self, x, z, ignore=None):
        """What a solid person at (x, z) would cut off from an arrival point
        that reaches it now: door, exit and search labels, ("person", name)
        for people, or "part of this place"."""
        lost = {}
        targets = self.targets()
        people = self.people_spots(ignore)
        for _, start in self.starts:
            if math.hypot(start[0] - x, start[1] - z) < BUMP:
                continue  # an arrival on top of them: the game moves on
            # Without anyone in the way it's the same every time: keep it.
            if start not in self._before:
                reach = self.flood(starts=[start])
                self._before[start] = (reach, self.standing(reach))
            before, sb = self._before[start]
            # Nowhere near anything reachable: nothing can be cut off.
            if not any(d < BUMP and p in before for p, d in self._near(x, z, BUMP)):
                continue
            after = self.flood(blocked=(x, z), starts=[start])
            if len(after) >= len(before):
                continue
            sa = self.standing(after)
            for k, (label, cells, how) in enumerate(targets):
                if self.target_reached(cells, how, before, sb) and not self.target_reached(cells, how, after, sa):
                    lost[("target", k)] = label
            for k, (name, px, pz) in enumerate(people):
                if self._can_talk(px, pz, sb) and not self._can_talk(px, pz, sa):
                    lost[("person", k)] = ("person", name)
            if len(before) - len(after) > 4 * (BUMP // GRID + 1) ** 2:
                lost.setdefault("part", tr("part of this place"))
        if len(lost) > 1:
            lost.pop("part", None)
        return list(lost.values())

    def people_spots(self, ignore=None):
        out = []
        seen = set()
        for e in self.events:
            if e["kind"] == "talk" and e.get("at") and e.get("actor") != ignore and e.get("actor") not in seen:
                seen.add(e.get("actor"))
                out.append((e.get("who") or tr("someone"), e["at"][0], e["at"][1]))
        return out

    def nearest_good(self, x, z, ignore=None, limit=40):
        """The nearest map pixel point (cell centre) where a person stands with
        nothing to say against it, or None."""
        cells = self.cells()
        cand = []
        for j in range(self.h):
            for i in range(self.w):
                if cells[j * self.w + i] == "good":
                    cx, cz = self.x0 + i * 16 + 8, self.z0 + j * 16 + 8
                    cand.append((math.hypot(cx - x, cz - z), cx, cz))
        cand.sort()
        taken = [(px, pz) for _, px, pz in self.people_spots(ignore)]
        for _, cx, cz in cand[:limit]:
            if any(math.hypot(cx - px, cz - pz) < 2 * BUMP for px, pz in taken):
                continue
            if not self.check(cx, cz, ignore):
                return cx, cz
        return None

    def level(self, x, z, shapes_by_height):
        """Grid edits that bring the ground from the nearest path to (x, z) at
        the path's height, so the party can walk there: {height, cells:
        [{plane, x, y, value}], count}, or None. `shapes_by_height` maps a
        height in pixels to a flat shape id the map already has."""
        if not self.inside(x, z) or self.behavior(x, z) == WALL:
            return None
        standing = self.standing()
        good = {((s[0] - self.x0) // 16, (s[1] - self.z0) // 16) for s in standing
                if self.behavior(*s) not in self.slide}
        target = ((x - self.x0) // 16, (z - self.z0) // 16)
        if target in good:
            return None
        # Fewest changed cells: a walk through cells that aren't walls, free
        # where the party already stands.
        dist = {target: 0}
        prev = {}
        q = collections.deque([target])
        found = None
        while q:
            c = q.popleft()
            if c in good:
                found = c
                break
            for dx, dz in DIRS:
                n = (c[0] + dx, c[1] + dz)
                if not (0 <= n[0] < self.w and 0 <= n[1] < self.h) or n in dist:
                    continue
                if self.behavior(self.x0 + n[0] * 16 + 8, self.z0 + n[1] * 16 + 8) == WALL:
                    continue
                dist[n] = dist[c] + 1
                prev[n] = c
                q.append(n)
        if found is None:
            return None
        height = round(self.ground_px(self.x0 + found[0] * 16 + 8, self.z0 + found[1] * 16 + 8))
        shape = shapes_by_height.get(height)
        if shape is None:
            close = [h for h in shapes_by_height if abs(h - height) <= 8]
            if not close:
                return None
            height = min(close, key=lambda h: abs(h - height))
            shape = shapes_by_height[height]
        path = []
        c = prev.get(found)
        while c is not None:
            path.append(c)
            c = prev.get(c)
        edits = []
        for i, j in path:
            gx, gz = self.grid_cell(self.x0 + i * 16, self.z0 + j * 16)
            if self.shp[gz][gx] != shape:
                edits.append({"plane": "shape", "x": gx, "y": gz, "value": shape})
        return {"height": height, "cells": edits, "count": len(edits)} if edits else None


def flat_shapes(project, info):
    """{height in pixels: shape id} of the flat shapes this map has, first one each."""
    out = {}
    for i, r in enumerate(project.shape_rows(info)):
        if (r[0] & 15) in (0, 14, 15) and r[1] * 8 not in out:
            out[r[1] * 8] = i
    return out


class _WayTo(str):
    """An exit's label, "the way to World Map": a str that _summary lists first."""


def _way_to(does):
    """An exit event's "does" text ("Leads to World Map", in the editor's
    language) as the way to that place; any other text as it is."""
    before, mark, after = tr("Leads to {place}").partition("{place}")
    if mark and len(does) >= len(before) + len(after) and does.startswith(before) and does.endswith(after):
        return _WayTo(tr("the way to {place}", place=does[len(before):len(does) - len(after)]))
    return does


# Things a blocked way can lead to, and how several of them are counted. Each
# language says its plurals whole; the singulars are the targets the editor
# names (events.search_targets and the ways out above).
_PLURALS = [
    (N_("a door"), N_("{n} doors")),
    (N_("a way out"), N_("{n} ways out")),
    (N_("a chest"), N_("{n} chests")),
    (N_("a jar"), N_("{n} jars")),
    (N_("a barrel"), N_("{n} barrels")),
    (N_("a grave"), N_("{n} graves")),
    (N_("a wooden box"), N_("{n} wooden boxes")),
    (N_("a well"), N_("{n} wells")),
    (N_("a spot where something happens"), N_("{n} spots where something happens")),
    (N_("a wall"), N_("{n} walls")),
    (N_("a rock"), N_("{n} rocks")),
    (N_("a hole"), N_("{n} holes")),
    (N_("a tree"), N_("{n} trees")),
    (N_("a chimney"), N_("{n} chimneys")),
    (N_("a bed"), N_("{n} beds")),
    (N_("a bookcase"), N_("{n} bookcases")),
    (N_("a stone coffin"), N_("{n} stone coffins")),
    (N_("a fireplace"), N_("{n} fireplaces")),
    (N_("a stone pillar"), N_("{n} stone pillars")),
    (N_("a stalactite"), N_("{n} stalactites")),
    (N_("a fountain"), N_("{n} fountains")),
    (N_("an oven"), N_("{n} ovens")),
    (N_("a table"), N_("{n} tables")),
    (N_("a stone statue"), N_("{n} stone statues")),
    (N_("a stone tablet"), N_("{n} stone tablets")),
    (N_("a shelf"), N_("{n} shelves")),
    (N_("a wardrobe"), N_("{n} wardrobes")),
]


def _summary(lost):
    """What a blocked way leads to, most important first, counted where there
    are several: "the way to World Map, 2 doors, a chest and 3 people"."""
    ways = [x for x in lost if isinstance(x, _WayTo)]
    people = [x for x in lost if isinstance(x, tuple)]
    rest = collections.Counter(x for x in lost if isinstance(x, str) and x not in ways)
    words = list(dict.fromkeys(ways))
    part = tr("part of this place")
    plural = {translate(one): translate(many) for one, many in _PLURALS}
    for label, count in rest.items():
        if label == part:
            continue
        if count == 1:
            words.append(label)
        elif label in plural:
            words.append(plural[label].replace("{n}", str(count)))
        else:
            # No plural form for it ("the ground"): the count beside it.
            words.append(tr("{what} (×{n})", n=count, what=label))
    if people:
        words.append(people[0][1] if len(people) == 1 else tr("{n} people", n=len(people)))
    if not words:
        words.append(part)
    return _join(words[:5]) if len(words) <= 5 else _join(words[:4] + [tr("more")])


def _join(items):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return tr("{list} and {last}", list=", ".join(items[:-1]), last=items[-1])
