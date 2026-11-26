"""Where the party can walk on a map, and where a person can stand, by the
game's own rules (alchemy's games/tbs/src/field):

- A step is 8 pixels, and is taken only when five probes 8 pixels out, straight
  ahead and 22.5 and 45 degrees either side, are clear (field_player_control.c).
- A probe is clear unless its cell is a wall (cell behavior 255), or its ground
  is more than 8 pixels above, or 12 below, the ground the walker stands on
  (field_terrain.c, MapGrid_CheckCollision).
- Heights come from each cell's shape: a kind and up to three samples, read by
  one of sixteen functions (field_terrain.c), with two tables (terrain_tables.c).
- A ledge (252) is hopped down, a climbing spot (253) climbed, a gap (254)
  jumped two cells forward (field/README.md, "Cells that act on their own").
- Talking reaches the nearest person within 32 pixels and 48 above or below
  (field/README.md, "Talking"). Two people bump when they come within their
  radii less 2 pixels each: 8 for a standard sprite, so 12 apart.
- A step trigger whose script slides the leader (Imil's ice) is followed as
  Leader_SlideOnIce does (scene/shared/leader_slide_on_ice.c): cell by cell
  until a wall, ground more than 8 pixels up, or another kind of cell.
- A cell whose word carries a layer marker (bits 12-13, the layer + 1) moves
  whoever stands on it onto that layer, whose window then gives the cells
  under them (field_actor_camera.c): a bridge over a floor. Off a bridge's
  own ground, that layer is followed only over the floor under it (not a
  wall, and within a step of its height), so blank cells don't open walls. Points on layer 0 are (x, z); points on
  another layer are (x, z, layer).

The party is followed from every arrival point of the scene. Cells the room's
own code changes as it plays (a door Psynergy opens, a bridge the story lowers;
scene_cells.py) are followed too: a step counts if it can be taken on the map
as saved or with those changes made, except out of a door or event cell on
the changed map (its script runs there), and what only the changes open is
told apart ("later"). People are not obstacles, except the one being checked.
"""

import collections
import math
import os
import re
import threading

from . import layout
from .project import shape_row
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
# way the steps always have been: 8 * (dx * c - dz * s), 8 * (dz * c + dx * s).
PROBE_OFFSETS = {(dx, dz): tuple((8 * (dx * c - dz * s), 8 * (dz * c + dx * s)) for c, s in PROBES)
                 for dx, dz in DIRS}
# The same offsets rounded down: from a whole pixel (every lattice point is
# one), floor(x + ax) is x + floor(ax), so a probe needs no rounding of its own.
PROBE_STEPS = {d: tuple((math.floor(ax), math.floor(az)) for ax, az in offsets) for d, offsets in PROBE_OFFSETS.items()}

TABLES = f"{layout.SRC}/field/terrain_tables.c"
GRAPHS_KEPT = 8  # walking graphs kept for reuse (Walk._build), the newest
_GRAPHS = collections.OrderedDict()
_GRAPHS_LOCK = threading.Lock()


def _tables(games_root):
    """gTerrain_LerpWeightTable and gTerrain_SampleIndexTable, read from the checkout."""
    path = os.path.join(games_root, TABLES)
    with open(path, encoding="utf-8") as f:
        text = re.sub(r"/\*.*?\*/|//[^\n]*", "", f.read(), flags=re.S)
    out = []
    # The weights are gTerrain_RoundedSquareMask since 2026-11-25.
    for names in (("gTerrain_RoundedSquareMask", "gTerrain_LerpWeightTable"), ("gTerrain_SampleIndexTable",)):
        m = next(filter(None, (re.search(rf"{name}\s*\[\s*256\s*\]\s*=\s*\{{(.*?)\}}", text, re.S) for name in names)), None)
        if not m:
            raise ValueError(f"{names[-1]} isn't in {TABLES}")
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
    [kind, s0, s1, s2] as unsigned bytes. Follows field_terrain.c line for line."""
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
    """The walking graph of one map for one scene, from layer 0 (the layer
    actor placements stand on: Event_SpawnActorPlacements reads its height)
    onto any layer its markers lead to.

    Positions are map pixels, as actor placements and entrances store them.
    `edits` is a list of {plane, x, y, value} grid edits not yet saved (a
    block edit counts for its layer marker), and
    `shapes` the heights made in the editor but not yet saved, as
    [kind, h0, h1, h2] after the table's own (shape edits name them by index).
    `changes` are the room's own cell copies (scene_cells.room_changes)."""

    def __init__(self, project, info, events, entrances, edits=(), shapes=(), changes=()):
        self.info = info
        self.origins = [project.layer_origin(info, li) for li in range(len(info.layers))]
        self.ox, self.oz = self.origins[0]
        self.x0, self.z0 = info.bounds[0] * 8, info.bounds[1] * 8
        self.w, self.h = info.size
        self.col = [row[:] for row in project.load_grid(info, "collision").cells]
        self.blocks = project.resolve_placeholders(project.load_grid(info, "metatile").cells)
        self.shp = [row[:] for row in project.load_grid(info, "shape").cells]
        for e in edits or ():
            grid = {"collision": self.col, "shape": self.shp, "block": self.blocks}.get(e.get("plane"))
            if grid is not None:
                grid[int(e["y"])][int(e["x"])] = int(e["value"])
        # {grid cell: layer} of every layer marker; one onto a layer whose
        # window is layer 0's changes nothing that walking reads.
        self.markers = {}
        for gz, row in enumerate(self.blocks):
            for gx, v in enumerate(row):
                k = (v >> 12) & 3
                if k and k - 1 < len(self.origins):
                    self.markers[(gx, gz)] = k - 1 if self.origins[k - 1] != self.origins[0] else 0
        self.rows = [[v + 256 if v < 0 else v for v in r] for r in project.shape_rows(info)]
        if not isinstance(shapes or [], (list, tuple)):
            raise ValueError(f"new heights should be a list of rows, not {shapes!r}")
        self.rows += [shape_row(r) for r in shapes or ()]
        self.lerp, self.index = _tables(project.root)
        self.events = events
        self.entrances = entrances
        self.slide = {e["trigger"] for e in events
                      if e["kind"] == "touch" and "slide" in (e.get("script") or "").lower()}
        self._heights = {}  # shape id -> its 16x16 heights, row-major (16.16 pixels)
        self._before = {}  # arrival lattice point -> (reach, standing) with no one in the way
        self._standable = {}  # lattice point -> whether standing() keeps it
        self._cells = None  # what cells() gives
        self.changes = tuple(tuple(c) for c in changes or ())
        self._build()

    # ---- the map, in map pixels ------------------------------------------------------

    def inside(self, x, z):
        return self.x0 <= x < self.x0 + self.w * 16 and self.z0 <= z < self.z0 + self.h * 16

    def grid_cell(self, x, z, layer=0):
        """The 128x128 grid cell under map pixel (x, z) on `layer`."""
        ox, oz = self.origins[layer]
        return (ox + int(x) // 16) % 128, (oz + int(z) // 16) % 128

    def behavior(self, x, z, layer=0):
        gx, gz = self.grid_cell(x, z, layer)
        return self.col[gz][gx]

    def ground(self, x, z, layer=0):
        """Ground height at map pixel (x, z) on `layer`, 16.16 pixels."""
        gx, gz = self.grid_cell(x, z, layer)
        x, z = int(x), int(z)
        v = self.shp[gz][gx]
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

    def _blank(self, blocks):
        """A test of map pixel (x, z): does its cell show nothing (block 0)?"""
        def blank(x, z, layer=0):
            gx, gz = self.grid_cell(x, z, layer)
            return blocks[gz][gx] & 0xFFF == 0
        return blank

    def ground_px(self, x, z, layer=0):
        return self.ground(x, z, layer) / FIXED

    def _point(self, x, z, layer):
        """The graph point for map pixel (x, z), reached on `layer`: a layer
        marker under it moves the walker onto its layer."""
        layer = self.markers.get(self.grid_cell(x, z, layer), layer)
        return (x, z) if layer == 0 else (x, z, layer)

    # ---- the graph ------------------------------------------------------------------

    def _node(self, x, z):
        """The lattice point nearest map pixel (x, z)."""
        return (int(round((x - self.x0) / GRID)) * GRID + self.x0, int(round((z - self.z0) / GRID)) * GRID + self.z0)

    def _slide_end(self, x, z, dx, dz, layer=0):
        """Where Leader_SlideOnIce leaves the leader who has just stepped onto
        the slide cell under (x, z) going (dx, dz): a cell centre."""
        cx, cz = (int(x) // 16) * 16 + 8, (int(z) // 16) * 16 + 8
        start = self.behavior(cx, cz, layer)
        passed = [(cx, cz)]
        while True:
            nx, nz = cx + 16 * dx, cz + 16 * dz
            if (not self.inside(nx, nz) or self.behavior(nx, nz, layer) == WALL
                    or self.ground(nx, nz, layer) - self.ground(cx, cz, layer) > STEP_UP):
                return (cx, cz), passed
            cx, cz = nx, nz
            passed.append((cx, cz))
            if self.behavior(cx, cz, layer) != start:
                return (cx, cz), passed

    def _moves(self, x, z, layer=0):
        """[(to, kind)] from lattice point (x, z) on `layer`: kind is walk,
        slide, hop, climb or jump, and `to` a graph point (_point)."""
        out = []
        L = layer
        markers = self.markers
        at = (lambda p, kind: out.append((self._point(*p, L), kind))) if markers else \
            (lambda p, kind: out.append((p if L == 0 else (*p, L), kind)))  # _point, with no markers
        # A step is taken when each of its probes is inside the map, not a
        # wall, and no more than STEP_UP above or STEP_DOWN below the ground
        # here. Written out: this runs for every lattice point, and (x, z) is
        # always one, in whole pixels (see PROBE_STEPS). _cell_heights holds
        # each cell's heights, as ground() reads them (made by _graph).
        (ox, oz), col, cell_heights = self.origins[L], self.col, self._cell_heights
        x0, z0 = self.x0, self.z0
        x1, z1 = x0 + self.w * 16, z0 + self.h * 16
        gx, gz = (ox + x // 16) % 128, (oz + z // 16) % 128
        here = col[gz][gx]
        g = cell_heights[gz][gx][(z & 15) * 16 + (x & 15)]
        for dx, dz in DIRS:
            tx, tz = x + GRID * dx, z + GRID * dz
            ahead = col[(oz + tz // 16) % 128][(ox + tx // 16) % 128] if x0 <= tx < x1 and z0 <= tz < z1 else WALL
            for ax, az in PROBE_STEPS[(dx, dz)]:
                px, pz = x + ax, z + az
                if not (x0 <= px < x1 and z0 <= pz < z1):
                    break
                qx, qz = (ox + px // 16) % 128, (oz + pz // 16) % 128
                if col[qz][qx] == WALL:
                    break
                d = cell_heights[qz][qx][(pz & 15) * 16 + (px & 15)] - g
                if not -STEP_DOWN <= d <= STEP_UP:
                    break
            else:  # every probe clear: the step is taken
                if ahead in self.slide and self.grid_cell(tx, tz, L) != self.grid_cell(x, z, L):
                    end, _ = self._slide_end(tx, tz, dx, dz, L)
                    at(end, "slide")
                else:
                    at((tx, tz), "walk")
                continue
            # The field's own cells answer a push the probes refused.
            if (dx, dz) == SOUTH and LEDGE in (here, ahead):
                g = self.ground(x, z, L)
                for k in range(2, 10):
                    lx, lz = x, z + GRID * k
                    if not self.inside(lx, lz) or self.behavior(lx, lz, L) == WALL:
                        break
                    if self.behavior(lx, lz, L) != LEDGE and self.ground(lx, lz, L) < g:
                        at((lx, lz), "hop")
                        break
            if (dx, dz) in (NORTH, SOUTH) and CLIMB in (here, ahead):
                for k in range(1, 40):
                    lx, lz = x, z + GRID * dz * k
                    if not self.inside(lx, lz) or self.behavior(lx, lz, L) == WALL:
                        break
                    if self.behavior(lx, lz, L) != CLIMB and k > 1:
                        at((lx, lz), "climb")
                        break
            if ahead == GAP:
                lx, lz = x + 32 * dx, z + 32 * dz
                if self.inside(lx, lz) and self.behavior(lx, lz, L) != WALL:
                    at((lx, lz), "jump")
        return out

    def _build(self):
        nodes, edges, slide_ends = self._graph()
        self.nodes, self.edges, self.slide_ends = nodes, edges, slide_ends
        self.starts = []
        for e in self.entrances:
            if self.inside(e["x"], e["z"]):
                self.starts.append((e, self._node(e["x"], e["z"])))
        self.reach = self.before_reach = self.flood()
        if not self.changes:
            return
        # On the changed map: from where the saved map already reaches, a
        # step of either map counts; beyond that the party is only ever on
        # the changed map, so only its steps do. A copy counts only once the
        # party can reach its destination or the square beside it: rooms also
        # copy cells to spare ground off to the side and back (to save and
        # restore a part), and that ground is never walked. As copies open
        # ground, the ones it reaches count in turn. Two more rules keep the
        # walk to ground the game lets the party walk:
        # - A door or event the party steps on runs its script there (it
        #   leaves, falls, is moved): the walk ends on such a cell. Copies
        #   often fill a path with one.
        # - It doesn't go onto a cell that shows nothing (block 0): the empty
        #   space around a room's parts is often level floor.
        stops = {e["trigger"] for e in self.events if e["kind"] in ("exit", "touch")} - self.slide
        before, applied = self.before_reach, []
        for _ in range(len(self.changes)):
            reached = {self.grid_cell(*n) for n in self.reach}
            near = {((gx + dx) % 128, (gz + dz) % 128) for gx, gz in reached for dx in (-1, 0, 1) for dz in (-1, 0, 1)}
            more = [c for c in self.changes if c not in applied and any(
                ((c[4] + i) % 128, (c[5] + j) % 128) in near for j in range(c[3]) for i in range(c[2]))]
            if not more:
                break
            applied += more
            col, shp = self.col, self.shp
            self.col, self.shp = _changed(col, applied), _changed(shp, applied)
            blank = self._blank(_changed(self.blocks, [c for c in applied if c[6:7] == (True,)]))
            try:
                _, after, after_ends = self._graph(base=(edges, col, shp))
                after = {n: [] if self.behavior(*n) in stops or blank(*n) else [mv for mv in moves if not blank(*mv[0])]
                         for n, moves in after.items()}
            finally:
                self.col, self.shp = col, shp
            self.edges = {n: list(dict.fromkeys([*edges.get(n, ()), *after.get(n, ())])) if n in before
                          else after.get(n, []) for n in {*edges, *after}}
            self.slide_ends = slide_ends | after_ends
            self.reach = self.flood()
        self.applied = applied

    def _graph(self, base=None):
        """(nodes, edges, slide ends) of the map's cells as they stand now.
        base: (edges, collision, shapes) of a graph made from other cells,
        when only the moves near the cells that differ need working out."""
        # The moves depend only on the cells, heights and slides, which several
        # scenes of a map share and most saves (an event, a door) leave alone:
        # a graph made from the same ones is reused. Shared: treat it as read-only.
        key = (tuple(self.origins), frozenset(self.markers.items()), self.x0, self.z0, self.w, self.h, frozenset(self.slide),
               tuple(map(tuple, self.rows)), tuple(map(tuple, self.col)), tuple(map(tuple, self.shp)),
               tuple(self.lerp), tuple(self.index))
        with _GRAPHS_LOCK:
            hit = _GRAPHS.get(key)
            if hit is not None:
                _GRAPHS.move_to_end(key)
        if hit is None:
            # Every cell's heights, looked up once for _moves' many probes.
            heights = self._heights
            self._cell_heights = [[heights.get(v) or self._shape_heights(v) for v in row] for row in self.shp]
            nodes = [(self.x0 + i * GRID, self.z0 + j * GRID)
                     for j in range(self.h * 16 // GRID) for i in range(self.w * 16 // GRID)]
            if base is not None:
                edges = self._patched(nodes, *base)
                slide_ends = {m for moves in edges.values() for m, k in moves if k == "slide"}
                self._other_layers(edges, slide_ends)
            else:
                edges, slide_ends = {}, set()
                for n in nodes:
                    if self.behavior(*n) == WALL:
                        continue
                    moves = self._moves(*n)
                    edges[n] = moves
                    slide_ends.update(m for m, k in moves if k == "slide")
            self._other_layers(edges, slide_ends)
            hit = (nodes, edges, slide_ends)
            with _GRAPHS_LOCK:
                _GRAPHS[key] = hit
                while len(_GRAPHS) > GRAPHS_KEPT:
                    _GRAPHS.popitem(last=False)
        return hit

    def _patched(self, nodes, edges, col, shp):
        """edges, made from cells col and shp, with the moves redone wherever
        the current cells could change them. A point's moves read cells at
        most three cells away (a step's probes, a jump), except along its own
        row and column, which hops, climbs and slides follow any distance."""
        changed = [(gx, gz) for gz in range(128) for gx in range(128)
                   if self.col[gz][gx] != col[gz][gx] or self.shp[gz][gx] != shp[gz][gx]]
        cols = {(gx + d) % 128 for gx, _ in changed for d in range(-3, 4)}
        rows = {(gz + d) % 128 for _, gz in changed for d in range(-3, 4)}
        near = {((gx + i) % 128, (gz + j) % 128) for gx, gz in changed for i in range(-3, 4) for j in range(-3, 4)}
        far = {LEDGE, CLIMB, *self.slide}  # cells whose moves follow a row or column
        out = dict(edges)
        for n in [*nodes, *(n for n in edges if len(n) == 3)]:
            gx, gz = self.grid_cell(*n)
            if gx in cols or gz in rows:
                # Further than three cells from every change, only a hop, climb
                # or slide reaches one, and those start from such a cell here
                # or a step away.
                if len(n) == 2 and (gx, gz) not in near and not self._starts_far(n, far):
                    continue
                if self.behavior(*n) == WALL or (len(n) == 3 and not self._layer_point(n)):
                    out.pop(n, None)
                else:
                    out[n] = self._moves(*n)
        return out

    def _starts_far(self, n, far):
        """Whether layer-0 point n, or a cell a step from it, is one of `far`."""
        x, z = n
        if self.behavior(x, z) in far:
            return True
        return any(self.inside(x + GRID * dx, z + GRID * dz) and self.behavior(x + GRID * dx, z + GRID * dz) in far
                   for dx, dz in DIRS)

    def _other_layers(self, edges, slide_ends):
        """Adds to `edges` the moves from every point on another layer that a
        move leads to, and from the points those lead to, and so on."""
        todo = [m for moves in edges.values() for m, _ in moves if len(m) == 3 and m not in edges]
        while todo:
            n = todo.pop()
            if n in edges:
                continue
            if not self._layer_point(n):
                continue
            moves = edges[n] = self._moves(*n)
            slide_ends.update(m for m, k in moves if k == "slide")
            todo += [m for m, _ in moves if len(m) == 3 and m not in edges]

    def _layer_point(self, n):
        """Whether point n on another layer is in the graph. On its layer's
        own ground (on_sheet), unless a wall. Elsewhere that layer's cells are
        blank, and read as level floor wherever the window reaches: rooms
        that use them close them off as they play (the game writes cell
        behaviors to any layer), so the walk follows them only over floor
        the player can see, layer 0's at the same height and not a wall."""
        if self.behavior(*n) == WALL:
            return False
        if self.on_sheet(n):
            return True
        x, z = n[0], n[1]
        return self.behavior(x, z) != WALL and abs(self.ground(x, z) - self.ground(*n)) <= STEP_UP

    def on_sheet(self, n):
        """Whether graph point n is on ground of its own layer, as the editor
        draws a second layer's ground: a cell with a shape or cell behavior.
        Elsewhere the second layer is blank, and whoever walks there stands,
        as the player sees it, on the floor below (the floor's own point)."""
        if len(n) == 2:
            return False
        gx, gz = self.grid_cell(*n)
        return bool(self.col[gz][gx] or self.shp[gz][gx])

    def floor_view(self, points):
        """`points` with each one off its layer's ground (on_sheet) as the
        floor's own point: what the player sees reached."""
        if all(len(n) == 2 for n in points):
            return points
        return {n if len(n) == 2 or self.on_sheet(n) else n[:2] for n in points}

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
            reach = self.floor_view(reach)
            return any(self._node(*c) in reach or (c[0] - 4, c[1] - 4) in reach for c in cells)
        # A search looks 16 pixels ahead: stand next to the cell.
        return any(math.hypot(s[0] - c[0], s[1] - c[1]) <= SEARCH_REACH + 6 and self.grid_cell(*s) != self.grid_cell(*c)
                   for c in cells for s in standing)

    def cells(self):
        """Per window cell (row-major, w x h): what standing a person there means.
        good: the party can walk up and stand here; talk: the party can't stand
        here but can talk to someone here from nearby; later: the party can
        stand here once the room's own code opens the way (Psynergy, the
        story); slide: a slide cell (someone there is in the way of a slide);
        trigger: a door, exit or step spot (keep it clear); cut: the party
        can't get near; wall: a wall."""
        # The graph doesn't change once built, and the editor asks again each
        # time the walk is shown: worked out once.
        if self._cells is None:
            self._cells = self._work_out_cells()
        return list(self._cells)

    def _work_out_cells(self):
        standing = self.floor_view(self.standing())
        before = self.floor_view(self.before_reach)
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
                    out.append("good" if (x, z) in before else "later")
                else:
                    near = [s for dx in (-1, 0, 1) for dz in (-1, 0, 1) for s in index[(x // 32 + dx, z // 32 + dz)]]
                    out.append("talk" if self.talk_points(x, z, near) else "cut")
        return out

    def layer_cells(self):
        """{layer: per window cell (row-major, w x h)} for each layer other
        than 0 the party walks on: good or later (as cells() says them) where
        the party can stand on that layer, else None."""
        standing = self.standing()
        out = {}
        for n in standing:
            if self.on_sheet(n):
                cells = out.setdefault(n[2], [None] * (self.w * self.h))
                i, j = (n[0] - self.x0) // 16, (n[1] - self.z0) // 16
                if (n[0] - self.x0) % 16 == 8 and (n[1] - self.z0) % 16 == 8:
                    cells[j * self.w + i] = "good" if n in self.before_reach else "later"
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
        standing = self.floor_view(self.standing())
        good = {((s[0] - self.x0) // 16, (s[1] - self.z0) // 16) for s in standing
                if len(s) == 2 and self.behavior(*s) not in self.slide}
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


def _changed(grid, changes):
    """A copy of a 128x128 grid plane with every cell copy made, in order."""
    out = [row[:] for row in grid]
    for sx, sy, w, h, dx, dy, *_ in changes:
        for j in range(h):
            for i in range(w):
                if 0 <= sx + i < 128 and 0 <= sy + j < 128 and 0 <= dx + i < 128 and 0 <= dy + j < 128:
                    out[dy + j][dx + i] = grid[sy + j][sx + i]
    return out


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
