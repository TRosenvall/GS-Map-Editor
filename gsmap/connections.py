"""How places connect: for one scene, where it leads and what leads to it.

Links come from exit tables (as the mod build sees them): scene A's segment
says exit kind k goes to (scene B, arrival e). Whether something on A's map
actually asks for kind k (a door cell, a door script) comes from DoorEditor;
other kinds are asked for by scene scripts or regions we can't place.
"""

from .doors import DoorEditor


class Connections:
    def __init__(self, project, scenes, names):
        self.project, self.scenes, self.names = project, scenes, names
        self.doors = DoorEditor(project, scenes, names)
        self._index = None

    def _exits(self, scene):
        """Unique (kind, scene, entrance) exits in every exit table of the
        scene's overlay, from the scene's own segments."""
        try:
            o = self.scenes.overlay(scene["overlay"])
            tables = self.doors._tables([o], self.doors._read_overrides(), "exits", need=False)
        except (FileNotFoundError, ValueError):
            return []
        seen, out = set(), []
        for _, _, segs in tables:
            for seg in segs:
                if seg.get("scene") != scene["id"]:
                    continue
                for e in seg.get("exits", []):
                    k = (e["kind"], e["scene"], e["entrance"])
                    if k not in seen:
                        seen.add(k)
                        out.append({"kind": e["kind"], "scene": e["scene"], "entrance": e["entrance"]})
        return out

    def index(self):
        """{scene id: [exits]} for every scene."""
        if self._index is None:
            self._index = {s["id"]: self._exits(s) for s in self.scenes.scenes}
        return self._index

    def _map_of(self, scene_id, row_to_map):
        sc = next((s for s in self.scenes.scenes if s["id"] == scene_id), None)
        return row_to_map.get(sc["layered_row"]) if sc else None

    def _place(self, scene_id, row_to_map):
        p = self.names.places.get(scene_id) or {}
        return {"scene": scene_id, "label": self.names.scene_label(scene_id),
                "area": p.get("area_name"), "map": self._map_of(scene_id, row_to_map)}

    def around(self, scene_id, row_to_map):
        idx = self.index()
        me = self._place(scene_id, row_to_map)
        # door cells on this scene's map, by the exit kind they ask for
        cells = {}
        info = self.project.maps.get(me["map"]) if me["map"] else None
        if info is not None:
            try:
                for d in self.doors.list(info).get(scene_id, []):
                    cells.setdefault(d["kind"], {"cell": d["cells"][0], "scripted": d["scripted"]})
            except (ValueError, FileNotFoundError):
                pass
        out = []
        for e in idx.get(scene_id, []):
            via = cells.get(e["kind"]) or (cells.get(next(iter(cells), None)) if e["kind"] == 0xFF and cells else None)
            out.append({**self._place(e["scene"], row_to_map), "entrance": e["entrance"], "kind": e["kind"],
                        "cell": via["cell"] if via else None,
                        "how": ("door" if not via["scripted"] else "scripted door") if via else "scene event"})
        incoming = []
        for src, exits in idx.items():
            for e in exits:
                if e["scene"] == scene_id and src != scene_id:
                    incoming.append({**self._place(src, row_to_map), "entrance": e["entrance"], "kind": e["kind"]})
        return {**me, "out": out, "in": incoming}
