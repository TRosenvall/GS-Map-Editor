"""The atlas: every place's map on one canvas, with its doors drawn as lines.

Golden Sun's places don't join edge to edge: each map is its own, and the party
moves between them through exits. So the atlas lays them out itself. Each area
(the maps whose scenes share an area name, such as a town and its houses) is a
cluster: its entry map first, then the maps reached from it, a column per step
away. A cluster sits near where its area's icon stands on the world map, and
clusters are pushed apart until none overlap. Areas with no icon (reached only
from inside another) go in rows below.

Positions a person drags are kept in the editor's settings (editor-only: the
game never sees them). Units are thumbnail pixels, SCALE of a map pixel.
"""

import collections

from .connections import Connections
from .doors import DoorEditor
from .i18n import tr

SCALE = 0.25      # thumbnail pixels per map pixel
GAP = 24          # between maps in a cluster, thumbnail pixels
CLUSTER_GAP = 64  # between clusters
WORLD_SPREAD = 2.5  # world map pixels to atlas pixels, before clusters are pushed apart
WORLD_SCENE = 2


def _row_to_map(project):
    out = {}
    for n, info in project.maps.items():
        for r in [info.resources] + info.alternates:
            if r:
                out.setdefault(r["row"], n)
    return out


def _overlaps(a, b, gap):
    return not (a[0] + a[2] + gap <= b[0] or b[0] + b[2] + gap <= a[0] or
                a[1] + a[3] + gap <= b[1] or b[1] + b[3] + gap <= a[1])


def build(project, scenes, names, world_places=None, saved=None):
    """{maps: [{map, label, area, x, y, w, h}], links: [{from, to, fx, fy, tx, ty, label}]}."""
    rm = _row_to_map(project)
    scene_map = {s["id"]: rm.get(s["layered_row"]) for s in scenes.scenes}
    maps = {}
    for s in scenes.scenes:
        n = scene_map[s["id"]]
        if n is None or s["id"] == WORLD_SCENE or n in maps:
            continue
        p = names.places.get(s["id"]) or {}
        info = project.maps[n]
        maps[n] = {"map": n, "scene": s["id"], "label": names.scene_label(s["id"]),
                   "area": p.get("area_name") or names.scene_label(s["id"]),
                   "w": round(info.size[0] * 16 * SCALE), "h": round(info.size[1] * 16 * SCALE)}

    # Links: every exit of every scene, from its door square (when it has one)
    # to the arrival point it leads to, in map pixels of each window.
    conn = Connections(project, scenes, names)
    doors = DoorEditor(project, scenes, names)
    arrivals = {}

    def arrival(scene_id, entrance):
        if scene_id not in arrivals:
            try:
                arrivals[scene_id] = {a["entrance"]: a for a in doors.entrances(scene_id)}
            except (ValueError, StopIteration):
                arrivals[scene_id] = {}
        a = arrivals[scene_id].get(entrance) or next(iter(arrivals[scene_id].values()), None)
        return a

    def window_px(n, x, z):
        info = project.maps[n]
        return (x - info.bounds[0] * 8) * SCALE, (z - info.bounds[1] * 8) * SCALE

    def cell_px(n, gx, gz):
        # A ground cell's centre in map pixels, as walk.py works it out.
        info = project.maps[n]
        ox, oz = project.layer_origin(info, 0)
        return window_px(n, ((gx - ox) % 128) * 16 + 8, ((gz - oz) % 128) * 16 + 8)

    links, seen = [], set()
    edges = collections.defaultdict(set)
    for s in scenes.scenes:
        src = scene_map[s["id"]]
        if src not in maps:
            continue
        try:
            around = conn.around(s["id"], rm)
        except (ValueError, StopIteration, KeyError):
            continue
        for e in around["out"]:
            dst = e["map"]
            if dst not in maps or dst == src:
                continue
            edges[src].add(dst)
            edges[dst].add(src)
            key = (src, dst, tuple(e["cell"]) if e["cell"] else e["kind"])
            if key in seen:
                continue
            seen.add(key)
            f = cell_px(src, *e["cell"]) if e["cell"] else (maps[src]["w"] / 2, maps[src]["h"] / 2)
            a = arrival(e["scene"], e["entrance"])
            t = window_px(dst, a["x"], a["z"]) if a else (maps[dst]["w"] / 2, maps[dst]["h"] / 2)
            links.append({"from": src, "to": dst, "fx": f[0], "fy": f[1], "tx": t[0], "ty": t[1],
                          "label": e["label"], "door": bool(e["cell"])})

    # Clusters: an area's maps, laid out from its entry outward.
    entry_of, anchor_of = {}, {}
    for ic in (world_places or {}).get("icons", []):
        lead = ic.get("lead")
        if lead and lead.get("scene") is not None and (ic["x"] or ic["z"]):
            n = scene_map.get(lead["scene"])
            if n in maps:
                area = maps[n]["area"]
                entry_of.setdefault(area, n)
                anchor_of.setdefault(area, (ic["x"] * WORLD_SPREAD, ic["z"] * WORLD_SPREAD))
    by_area = collections.defaultdict(list)
    for n in sorted(maps):
        by_area[maps[n]["area"]].append(n)

    clusters = []
    for area, members in by_area.items():
        start = entry_of.get(area) or members[0]
        layers, placed = [], {start}
        frontier = [start]
        while frontier:
            layers.append(frontier)
            nxt = []
            for n in frontier:
                for m in sorted(edges[n]):
                    if m in members and m not in placed:
                        placed.add(m)
                        nxt.append(m)
            frontier = nxt
        rest = [m for m in members if m not in placed]
        if rest:
            layers.append(rest)
        x, pos = 0, {}
        for col in layers:
            y = 0
            for n in col:
                pos[n] = (x, y)
                y += maps[n]["h"] + GAP
            x += max(maps[n]["w"] for n in col) + GAP
        w = max(pos[n][0] + maps[n]["w"] for n in pos)
        h = max(pos[n][1] + maps[n]["h"] for n in pos)
        clusters.append({"area": area, "pos": pos, "w": w, "h": h, "anchor": anchor_of.get(area)})

    # Anchored clusters near their icons, pushed apart; the rest in rows below.
    boxes = []

    def free_spot(x, y, w, h, dx, dy):
        """Slide (x, y) in direction (dx, dy) past whatever it overlaps until it's clear."""
        for _ in range(len(boxes) + 1):
            hit = next((b for b in boxes if _overlaps((x, y, w, h), b, CLUSTER_GAP)), None)
            if hit is None:
                return x, y
            if dx > 0:
                x = hit[0] + hit[2] + CLUSTER_GAP
            elif dx < 0:
                x = hit[0] - w - CLUSTER_GAP
            elif dy > 0:
                y = hit[1] + hit[3] + CLUSTER_GAP
            else:
                y = hit[1] - h - CLUSTER_GAP
        return None

    # Largest first, so the small ones fit round them; each takes the nearest
    # clear spot to its icon, moving right, left, down or up.
    def settle(c, cx, cy):
        x, y = cx - c["w"] / 2, cy - c["h"] / 2
        spots = [s for s in (free_spot(x, y, c["w"], c["h"], *d) for d in ((1, 0), (-1, 0), (0, 1), (0, -1))) if s]
        c["x"], c["y"] = min(spots, key=lambda s: abs(s[0] - x) + abs(s[1] - y)) if spots else (x, y)
        boxes.append((c["x"], c["y"], c["w"], c["h"]))

    for c in sorted((c for c in clusters if c["anchor"]), key=lambda c: -c["w"] * c["h"]):
        settle(c, *c["anchor"])
    # An area with no icon (a dungeon reached from a town, a cave's inner rooms)
    # goes beside the placed area it has the most doors with, nearest first.
    area_of = {n: maps[n]["area"] for n in maps}
    by_name = {c["area"]: c for c in clusters}
    waiting = [c for c in clusters if not c["anchor"]]
    while waiting:
        best = None
        for c in waiting:
            counts = collections.Counter(area_of[m] for n in c["pos"] for m in edges[n]
                                         if area_of[m] != c["area"] and "x" in by_name[area_of[m]])
            if counts:
                near, k = counts.most_common(1)[0]
                if best is None or k > best[2]:
                    best = (c, by_name[near], k)
        if best is None:
            break
        c, near, _ = best
        settle(c, near["x"] + near["w"] / 2, near["y"] + near["h"] / 2)
        c["anchor"] = (c["x"], c["y"])
        waiting.remove(c)
    left = min((b[0] for b in boxes), default=0)
    y = max((b[1] + b[3] for b in boxes), default=0) + CLUSTER_GAP * 3
    x, row_h, width = left, 0, max((b[0] + b[2] for b in boxes), default=4000) - left
    for c in sorted((c for c in clusters if not c["anchor"]), key=lambda c: c["area"]):
        if x > left and x + c["w"] > left + width:
            x, y, row_h = left, y + row_h + CLUSTER_GAP, 0
        c["x"], c["y"] = x, y
        x += c["w"] + CLUSTER_GAP
        row_h = max(row_h, c["h"])

    # Shift everything to start at (0, 0), then apply positions people dragged.
    for c in clusters:
        for n, (px, py) in c["pos"].items():
            maps[n]["x"], maps[n]["y"] = c["x"] + px, c["y"] + py
    x0 = min(m["x"] for m in maps.values())
    y0 = min(m["y"] for m in maps.values())
    for m in maps.values():
        m["x"], m["y"] = round(m["x"] - x0), round(m["y"] - y0)
        if saved and m["map"] in saved:
            m["x"], m["y"] = int(saved[m["map"]][0]), int(saved[m["map"]][1])
        m["moved"] = bool(saved and m["map"] in saved)
    return {"scale": SCALE, "maps": sorted(maps.values(), key=lambda m: m["map"]), "links": links,
            "title": tr("Atlas")}
