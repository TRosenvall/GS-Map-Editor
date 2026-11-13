"""The world map's random battles: which enemies each encounter region has.

Read from alchemy (games/tbs/src):
  field/world_map_encounter_rules.c  gWorldMap_EncounterRules: {region, battle
                 environment (-1 any), flag, zone} rows ended by region -1; the
                 first matching row wins. Each region has a zone for open
                 ground and one for its forests.
  field/encounter_zones.c  gEncounterZones: per zone a rate, a level, and up to
                 8 formations with relative chances (weights).
  battle/formations.c  gFormations: up to five kinds of enemy, with the fewest
                 and most of each, as ENEMY_ROW(ENEMY_X).
  include/enemy_ids.h  enum EnemyId, one per enemy row in order; their names
                 are the MsgEnemyName messages of en.po, one per row.

Editing rewrites a zone's initializer in encounter_zones.c in the file's own
layout; zones nobody changes keep their text byte for byte.
"""

import os
import re

from . import layout
from .fsio import atomic_write
from .i18n import N_, tr, translate
from .messages import Messages

ZONES = f"{layout.SRC}/field/encounter_zones.c"
RULES = f"{layout.SRC}/field/world_map_encounter_rules.c"
SCENE_RULES = f"{layout.SRC}/field/encounter_rules.s"  # gScene_EncounterRules: places' zones
FORMATIONS = f"{layout.SRC}/battle/formations.c"
ENEMY_IDS = f"{layout.INCLUDE}/enemy_ids.h"
MAX_GROUPS = 8   # ENCOUNTER_GROUP_COUNT
FORESTS = {2, 6}  # BATTLE_ENVIRONMENT_FOREST, BATTLE_ENVIRONMENT_SNOW_FOREST
ENVIRONMENTS = {0: N_("no backdrop"), 1: N_("grassland"), 2: N_("forest"), 3: N_("desert"), 4: N_("beach"),
                5: N_("snowfield"), 6: N_("snowy forest"), 7: N_("shallows")}


def _read(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as f:
        return f.read()


def _strip_comments(text):
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


def _array_body(text, name):
    """The text between the braces of `name[...] = { ... };`."""
    m = re.search(rf"\b{name}\s*\[[^\]]*\]\s*=\s*\{{", text)
    if not m:
        raise ValueError(tr("Can't find {name} in the game source.", name=name))
    depth, i = 1, m.end()
    while depth:
        c = text[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return m.end(), i - 1


def _entries(text, name):
    """[(start, end)] spans of the top-level { } entries of an array."""
    start, end = _array_body(text, name)
    spans, depth, at = [], 0, None
    i = start
    while i < end:
        c = text[i]
        if text.startswith("//", i):
            i = text.index("\n", i)
            continue
        if c == "{":
            if depth == 0:
                at = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                spans.append((at, i + 1))
        i += 1
    return spans


def _field(entry, name):
    m = re.search(rf"\.{name}\s*=\s*(\{{[^}}]*\}}|[^,}}\n]+)", entry)
    if not m:
        return None
    v = m.group(1).strip()
    return v[1:-1] if v.startswith("{") else v


def _ints(v):
    return [int(x, 0) for x in re.findall(r"-?(?:0x[0-9a-fA-F]+|\d+)", v or "")]


class Encounters:
    def __init__(self, root):
        self.root = root
        self.text = _read(root, ZONES)
        self.zones = [self._zone(self.text[a:b]) for a, b in _entries(self.text, "gEncounterZones")]
        self.rules = self._rules()
        self.scene_rules = self._scene_rules()
        self.enemies = self._enemies()
        self.formations = self._formations()

    # ---- reading -----------------------------------------------------------------

    @staticmethod
    def _zone(entry):
        f = _ints(_field(entry, "formations"))
        w = _ints(_field(entry, "weights"))
        return {"rate": int(_field(entry, "rate") or "0", 0), "level": int(_field(entry, "level") or "0", 0),
                "formations": f, "weights": w + [0] * (len(f) - len(w))}

    def _rules(self):
        start, end = _array_body(_strip_comments(_read(self.root, RULES)), "gWorldMap_EncounterRules")
        values = _ints(_strip_comments(_read(self.root, RULES))[start:end])
        out = []
        for i in range(0, len(values) - 3, 4):
            region, env, flag, zone = values[i:i + 4]
            if region == -1:
                break
            out.append({"region": region, "environment": env, "flag": flag, "zone": zone})
        return out

    def _scene_rules(self):
        """gScene_EncounterRules: [{scene (name), entrance, flag, shift, zone}]. On
        entering, the first rule for the scene and arrival point that its flag
        doesn't turn off gives the zones (Encounter_SelectMapZones): encounter
        ground A (walkability 240) takes the zone, or with shift ordinary ground."""
        try:
            text = _read(self.root, SCENE_RULES)
        except OSError:
            return []
        out = []
        for m in re.finditer(r"^\s*encounter_rule\s+(\w+),\s*(-?\w+),\s*(-?\w+),\s*(\d+),\s*(\d+)", text, re.M):
            out.append({"scene": m.group(1), "entrance": int(m.group(2), 0), "flag": int(m.group(3), 0),
                        "shift": int(m.group(4)), "zone": int(m.group(5))})
        return out

    def _zone_view(self, zid):
        zone = self.zones[zid]
        return {"zone": zid, "rate": zone["rate"], "level": zone["level"],
                "groups": [{"formation": f, "weight": w, "label": self.formation_label(f)}
                           for f, w in zip(zone["formations"], zone["weights"])]}

    def scene_battles(self, scene_name, flag_label=None, scene_label=None):
        """The battles of one place: per rule, where they happen (an arrival
        point, a story flag) and its zone, and the other places sharing it."""
        out = []
        for r in self.scene_rules:
            if r["scene"] != scene_name or not r["zone"]:
                continue
            others = sorted({x["scene"] for x in self.scene_rules if x["zone"] == r["zone"] and x["scene"] != scene_name})
            when = []
            if r["entrance"] != -1:
                when.append(tr("arriving at point {n}", n=r["entrance"]))
            if r["flag"] != -1:
                when.append(tr("until {flag} is set", flag=flag_label(r["flag"]) if flag_label else hex(r["flag"])))
            out.append(dict(self._zone_view(r["zone"]),
                            where=tr("Anywhere you walk") if r["shift"] else tr("On encounter ground A"),
                            when=", ".join(when),
                            shared=[scene_label(s) if scene_label else s for s in others]))
        # The same zone listed once, with every condition it comes under.
        merged = {}
        for b in out:
            m = merged.setdefault(b["zone"], dict(b, when=[]))
            if b["when"] and b["when"] not in m["when"]:
                m["when"].append(b["when"])
        return [dict(b, when="; ".join(b["when"])) for b in merged.values()]

    def _enemies(self):
        text = _strip_comments(_read(self.root, ENEMY_IDS))
        m = re.search(r"enum\s+EnemyId\s*\{(.*?)\}", text, re.S)
        if not m:
            raise ValueError(tr("Can't find the enemy list ({path}).", path=ENEMY_IDS))
        ids = [re.match(r"\s*(\w+)", part).group(1) for part in m.group(1).split(",") if part.strip()]
        try:
            msgs = Messages(self.root)
        except (OSError, ValueError):
            msgs = None
        from .names import _message_block
        names = _message_block(msgs, "MsgEnemyName", len(ids))
        return [{"id": e, "name": names[i] if i < len(names) and names[i] else e.replace("ENEMY_", "").title()}
                for i, e in enumerate(ids)]

    def _formations(self):
        text = _read(self.root, FORMATIONS)
        rows = {e["id"]: i for i, e in enumerate(self.enemies)}
        out = []
        for a, b in _entries(text, "gFormations"):
            entry = text[a:b]
            members = [rows.get(x) for x in re.findall(r"ENEMY_ROW\((\w+)\)", _field(entry, "memberIds") or "")]
            low, high = _ints(_field(entry, "minimumCounts")), _ints(_field(entry, "maximumCounts"))
            out.append([{"enemy": m, "min": low[i] if i < len(low) else 0, "max": high[i] if i < len(high) else 0}
                        for i, m in enumerate(members) if m is not None])
        return out

    def formation_label(self, f):
        """"2 Wild Mushroom", "Vermin, 1–2 Bat": the enemies a formation brings."""
        parts = []
        for m in self.formations[f] if 0 <= f < len(self.formations) else []:
            name = self.enemies[m["enemy"]]["name"]
            lo, hi = m["min"], max(m["min"], m["max"])
            count = "" if lo == hi == 1 else (f"{lo} " if lo == hi else f"{lo}–{hi} ")
            parts.append(count + name)
        return ", ".join(parts) or tr("nobody")

    def regions(self, region_names=None):
        """[{region, name, zones: [{zone, where, rate, level, groups}]}] for the
        world map's encounter regions."""
        out = {}
        for r in self.rules:
            reg = out.setdefault(r["region"], {"region": r["region"], "zones": {}})
            z = reg["zones"].setdefault(r["zone"], {"zone": r["zone"], "environments": []})
            if r["environment"] not in z["environments"]:
                z["environments"].append(r["environment"])
        result = []
        for region, reg in sorted(out.items()):
            zones = []
            for zid, z in reg["zones"].items():
                zone = self.zones[zid]
                forest = all(e in FORESTS for e in z["environments"])
                zones.append({"zone": zid, "where": tr("Forests") if forest else tr("Open ground"),
                              "environments": [translate(ENVIRONMENTS.get(e, N_("any"))) for e in z["environments"]],
                              "rate": zone["rate"], "level": zone["level"],
                              "groups": [{"formation": f, "weight": w, "label": self.formation_label(f)}
                                         for f, w in zip(zone["formations"], zone["weights"])]})
            name = (region_names or {}).get(region) or tr("Region {n}", n=region)
            result.append({"region": region, "name": name, "zones": zones})
        return result

    def formation_choices(self):
        """Every formation a zone could use: [{formation, label}], the empty ones left out."""
        return [{"formation": i, "label": self.formation_label(i)} for i, f in enumerate(self.formations) if f]

    # ---- writing -----------------------------------------------------------------

    def world_zones(self):
        return {r["zone"] for r in self.rules}

    def editable_zones(self):
        """Zones the world map or a place uses for random battles."""
        return self.world_zones() | {r["zone"] for r in self.scene_rules if r["zone"]}

    def set_zone(self, zone_id, rate, groups):
        """Change a world map zone's rate and its formations with their chances."""
        if zone_id not in self.editable_zones():
            raise ValueError(tr("That isn't a zone of random battles."))
        rate = int(rate)
        if not 0 <= rate <= 100:
            raise ValueError(tr("The rate should be 0 to 100."))
        groups = [(int(g["formation"]), int(g["weight"])) for g in groups]
        if not 1 <= len(groups) <= MAX_GROUPS:
            raise ValueError(tr("A zone has 1 to {n} groups of enemies.", n=MAX_GROUPS))
        for f, w in groups:
            if not (0 < f < len(self.formations) and self.formations[f]):
                raise ValueError(tr("There's no group of enemies {n}.", n=f))
            if not 1 <= w <= 255:
                raise ValueError(tr("Each group's chance should be 1 to 255."))
        zone = self.zones[zone_id]
        new = {"rate": rate, "level": zone["level"], "formations": [f for f, _ in groups], "weights": [w for _, w in groups]}
        if new == zone:
            return False
        spans = _entries(self.text, "gEncounterZones")
        a, b = spans[zone_id]
        lines = ["{"]
        if new["rate"]:
            lines.append(f"        .rate = {new['rate']},")
        if new["level"]:
            lines.append(f"        .level = {new['level']},")
        lines.append("        .formations = {" + ", ".join(map(str, new["formations"])) + "},")
        lines.append("        .weights = {" + ", ".join(map(str, new["weights"])) + "},")
        lines.append("    }")
        self.text = self.text[:a] + "\n".join(lines) + self.text[b:]
        self.zones[zone_id] = new
        atomic_write(os.path.join(self.root, ZONES), self.text)
        return True
