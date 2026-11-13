"""Player-facing names and previews (see docs/research/naming.md).

Names (items, places, characters, sprites, flags) and images (item icons, sprite
previews) are read at runtime from the player's own alchemy checkout, so the app
ships neither the game's art nor its text. gsmap/data holds only the editor's
own findings: which picture frame previews each sprite, which flags are free for
new chests, and what each walkability code does, in our words.
"""

import io
import json
import os
import re

from PIL import Image

from . import layout
from .i18n import tr, translate
from .messages import Messages

DATA = os.path.join(os.path.dirname(__file__), "data")

EVENT_TALK, EVENT_EXIT, EVENT_TOUCH, EVENT_SEARCH = 0, 1, 2, 3
SEARCH_CHEST_CONTROL = 19  # SEARCH(1): control & 0x1ff


def _load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def _source(root, rel):
    """A checkout file's text, "" if it's missing (setup hasn't finished, or
    preflight will say what moved): things then show their numbers."""
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _messages(root):
    try:
        return Messages(root)
    except (OSError, ValueError):  # missing, or not text: preflight says which
        return None


def _message_block(msgs, symbol, count):
    """Text of up to `count` messages from a linker symbol, game commands
    removed. The next symbol is another block (item rows outrun the item names,
    and the enemies' follow them)."""
    if not msgs:
        return []
    base = next((n for n, e in msgs.entries.items() if e["ctx"] == symbol), None)
    if base is None:
        return []
    out = []
    for n in range(base, base + count):
        e = msgs.entries.get(n)
        if not e or (n > base and e["ctx"] not in (None, "message")):
            break
        out.append(re.sub(r"\{[^}]*\}", "", e["text"]).strip())
    return out


def _read_items(root, msgs):
    """{id: item}: rows of gItem_DefinitionTable in order, named from the text.
    A row whose name is only question marks is a blank the game never hands out."""
    text = _source(root, layout.ITEM_TABLE)
    text = text[text.find("gItem_DefinitionTable"):]
    rows = re.split(r"^\s*\[ITEM_\w+\]\s*=", text, flags=re.M)[1:]  # rows hold nested braces
    names = _message_block(msgs, "MsgItemName", len(rows))
    items = {}
    for i, row in enumerate(rows):
        kind = re.search(r"\.type\s*=\s*ITEM_TYPE_(\w+)", row)
        icon = re.search(r"\.icon\s*=\s*(\d+)", row)
        name = names[i] if i < len(names) and names[i] else f"item {i}"
        items[i] = {"id": i, "name": name, "type": kind.group(1).lower() if kind else "none",
                    "icon": int(icon.group(1)) if icon else 0, "unused": i >= len(names) or set(name) <= {"?"}}
    return items


def _read_places(root, msgs):
    """{scene id: place}: its name in the scene list, and the area name the
    game's rules give it when no particular entrance is asked about."""
    scenes = re.findall(r"^\s*scene\s+(\w*)\s*,\s*\w+\s*,\s*(\d+)\s*,", _source(root, layout.SCENE_TABLE), re.M)
    ids = {name: i for i, (name, _) in enumerate(scenes) if name}
    text = _source(root, layout.AREA_RULES)
    rules = re.findall(r"^\s*(area|scene)_name\s+(\w+)\s*,\s*(-?\w+)\s*,\s*(\d+)", text, re.M)
    by_scene, by_area = {}, {}
    for kind, who, entrance, index in rules:
        if entrance != "-1":
            continue
        if kind == "area":
            if who.lstrip("-").isdigit():
                by_area.setdefault(int(who), int(index))
        else:
            by_scene.setdefault(ids.get(who, int(who) if who.isdigit() else -1), int(index))
    highest = max([*by_scene.values(), *by_area.values()], default=0)
    areas = _message_block(msgs, "MsgDebugAreaName", highest + 1)
    places = {}
    for sid, (name, area) in enumerate(scenes):
        index = by_scene.get(sid, by_area.get(int(area), 0))
        area_name = areas[index] if index < len(areas) else None
        places[sid] = {
            "id": sid, "symbol": name or None,
            # An unnamed scene's label is "Scene 12", in the editor's language (Names._label).
            "label": re.sub(r"(?<=[a-z0-9])(?=[A-Z])(?<!Mc)", " ", name) if name else None,
            # Bracketed names are the game's notes on empty slots, not places.
            "area_name": None if not area_name or area_name.startswith("(") else area_name,
        }
    return places


def _read_sprites(root):
    """{id: sprite}: the frames we preview, named from enum SpriteId. A row the
    game's source hasn't named yet keeps its number."""
    enum = re.search(r"enum SpriteId\s*\{(.*?)\}", _source(root, layout.SPRITE_NAMES), re.S)
    body = re.sub(r"/\*.*?\*/|//[^\n]*", "", enum.group(1), flags=re.S) if enum else ""
    names, n = {}, 0
    for part in body.split(","):
        m = re.fullmatch(r"\s*SPRITE_(\w+)\s*(?:=\s*(\w+)\s*)?", part)
        if not m:
            continue
        if m.group(2):
            try:
                n = int(m.group(2), 0)
            except ValueError:  # an alias of another name: it takes no new number
                continue
        if not m.group(1).isdigit():
            names[n] = re.sub(r"\bMc([a-z])", lambda c: "Mc" + c.group(1).upper(), m.group(1).replace("_", " ").title())
        n += 1
    sprites = {}
    for s in _load("sprites.json"):
        sid = s["id"]
        sprites[sid] = {**s, "name": names.get(sid),  # None: sprite_name() says "Sprite 12"
                        "png": layout.SPRITE_PICTURE.format(id=sid) if s.get("has_image") else None}
    return sprites


_FLAGS = {}  # flags.h path -> (mtime, names)


def read_flag_names(root):
    """{flag number: its name in flags.h}; the first name of a shared number."""
    path = os.path.join(root, layout.FLAG_NAMES)
    try:
        stamp = os.stat(path).st_mtime_ns
    except OSError:
        return {}
    cached = _FLAGS.get(path)
    if not cached or cached[0] != stamp:
        names = {}
        for name, value in re.findall(r"^#define\s+(FLAG_\w+)\s+(0[xX][0-9a-fA-F]+|\d+)\s*(?:$|/)",
                                      _source(root, layout.FLAG_NAMES), re.M):
            names.setdefault(int(value, 0), name)
        cached = _FLAGS[path] = (stamp, names)
    return cached[1]


class Names:
    def __init__(self, root):
        self.root = root
        msgs = _messages(root)
        self.collision = _load("collision.json")["ranges"]
        self.items = _read_items(root, msgs)
        self.sprites = _read_sprites(root)
        self.places = _read_places(root, msgs)
        self.characters = _message_block(msgs, "MsgCharacterName", 7)
        self.free_chest_flags = _load("flags.json")["free_chest_flags"]
        # Names the mod gives its own scenes (games/tbs/src/mod/names.json).
        mod_names = os.path.join(root, layout.MOD, "names.json")
        if os.path.exists(mod_names):
            try:
                with open(mod_names, encoding="utf-8") as f:
                    for sid, label in json.load(f).get("scenes", {}).items():
                        p = self.places.setdefault(int(sid), {"id": int(sid)})
                        p["label"], p["area_name"] = label, None
            except (OSError, ValueError, AttributeError, TypeError):
                pass  # only names: the places still work, under their own
        self._png_cache = {}

    # ---- lookups ------------------------------------------------------------

    def collision_range(self, code):
        for r in self.collision:
            if r["lo"] <= code <= r["hi"]:
                return r
        return None

    def item_name(self, item_id):
        it = self.items.get(item_id)
        return it["name"] if it else tr("item {n}", n=item_id)

    def sprite_name(self, sprite_id):
        """A sprite's name from enum SpriteId, "Sprite 12" if it has none, or
        None if there's no such sprite."""
        s = self.sprites.get(sprite_id)
        if s is None:
            return None
        return s.get("name") or tr("Sprite {n}", n=sprite_id)

    @staticmethod
    def _label(scene_id, p):
        """A place's label; a scene the scene list leaves unnamed is "Scene 12"."""
        return p.get("label") or (tr("Scene {n}", n=scene_id) if "symbol" in p else None)

    def place(self, scene_id):
        p = self.places.get(scene_id)
        if not p:
            return tr("scene {n}", n=scene_id)
        return p.get("area_name") or self._label(scene_id, p) or tr("scene {n}", n=scene_id)

    def scene_label(self, scene_id):
        """Area name plus the scene's own label, e.g. "Vale · Vale Home"."""
        p = self.places.get(scene_id)
        if not p:
            return tr("scene {n}", n=scene_id)
        area, label = p.get("area_name"), self._label(scene_id, p)
        if area and label and area != label:
            return f"{area} · {label}"
        return area or label or tr("scene {n}", n=scene_id)

    def find_value(self, value):
        """A chest/search value (FIND_*) in words."""
        kind, arg = value & 0x00F00000, value & 0xFFFF
        if kind == 0x00100000:
            return self.item_name(arg)
        if kind == 0x00200000:
            return tr("{n} coins", n=arg)
        if kind == 0x00300000:
            return tr("Psynergy Stone")
        if kind == 0x00400000:
            return tr("message {n}", n=arg)
        if kind == 0x00500000:
            return tr("Mimic")
        return f"{value:#x}"

    def client_tables(self):
        """Everything the UI needs to name things, in one payload."""
        return {
            # Walkability brushes: data/collision.json keeps them in English;
            # tools/extract_strings.py collects their names and meanings.
            "collision": [dict(r, name=translate(r["name"]), meaning=translate(r["meaning"])) for r in self.collision],
            "items": [
                {"id": i, "name": it["name"], "type": it.get("type"), "unused": it.get("unused", False)}
                for i, it in sorted(self.items.items())
            ],
            "sprites": [
                {"id": i, "name": self.sprite_name(i), "has_image": s.get("has_image", False)}
                for i, s in sorted(self.sprites.items())
            ],
            "scenes": [
                {"id": i, "label": self.scene_label(i), "area": p.get("area_name")}
                for i, p in sorted(self.places.items())
            ],
            "characters": self.characters,
            "free_chest_flags": self.free_chest_flags,
        }

    # ---- images from the player's checkout -----------------------------------

    def _png(self, rel):
        path = os.path.join(self.root, rel)
        if path not in self._png_cache:
            self._png_cache[path] = Image.open(path)
        return self._png_cache[path]

    @staticmethod
    def _rgba(img):
        """Indexed PNG -> RGBA with palette index 0 transparent."""
        if img.mode == "P":
            out = img.convert("RGBA")
            mask = Image.new("L", img.size)  # from raw indices, not palette colours
            mask.putdata([0 if v == 0 else 255 for v in img.getdata()])
            out.putalpha(mask)
            return out
        return img.convert("RGBA")

    def item_icon_png(self, item_id):
        it = self.items.get(item_id)
        icon = it["icon"] if it else 0
        img = self._png(layout.ITEM_ICON.format(icon=icon))
        buf = io.BytesIO()
        self._rgba(img).save(buf, "PNG")
        return buf.getvalue()

    def sprite_png(self, sprite_id):
        s = self.sprites.get(sprite_id)
        if not s or not s.get("has_image") or not s.get("png"):
            return None
        f = s["frame"]
        img = self._rgba(self._png(s["png"]).crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"])))
        if s.get("mirrored"):
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()

    # ---- per-map legend --------------------------------------------------------

    def map_legend(self, scene_list, scenes):
        """{collision code: [descriptions]} for codes the scene tables give a
        meaning to. scene_list: scenes using the map (Scenes rows)."""
        legend = {}

        def add(code, text):
            lst = legend.setdefault(code, [])
            if text not in lst:
                lst.append(text)

        from .modgen import Overrides
        ov = Overrides(self.root)

        def rows(o, name):  # a table as the mod build sees it
            over = ov.get(o.id, name)
            return over["rows"] if over else o.rows(name)

        from .doors import script_exit_kinds
        from .sceneedit import scene_tables
        tbs = os.path.join(self.root, layout.SRC)
        script_kinds = {}
        for sc in scene_list:
            o = scenes.overlay(sc["overlay"])
            exit_tables = [rows(o, n) for n, t in o.tables.items() if t["kind"] == "exits" and t["editable"]]
            only = scene_tables(tbs, o, "events", sc["name"])  # this room's, not its overlay's others
            for name, t in o.tables.items():
                if t["kind"] != "events" or not t["editable"] or (only is not None and name not in only):
                    continue
                for r in rows(o, name):
                    control = r["control"]
                    if control == 0xFFFFFFFF:
                        break
                    kind, code = control & 0xF, r["trigger"] & 0xFF
                    if kind == EVENT_EXIT:
                        dest = self._exit_destination(sc["id"], r["value"], exit_tables)
                        add(code, tr("Exit → {place}", place=dest) if dest else tr("Exit (kind {n})", n=r["value"]))
                    elif kind == EVENT_SEARCH and (control & 0x1FF) == SEARCH_CHEST_CONTROL:
                        add(code, tr("Chest: {what}", what=self.find_value(r["value"])))
                    elif kind == EVENT_SEARCH:
                        v = r["value"]
                        add(code, tr("Search: {what}", what=self.find_value(v)) if v & 0x00F00000 else tr("Search: scripted"))
                    elif kind == EVENT_TOUCH and r["value"] < 0x10000:
                        add(code, tr("Touch: shows a message"))
                    elif kind == EVENT_TOUCH:
                        # A door script asks for one exit kind (read from the scene's C, as the Doors tool does).
                        kinds = script_kinds.setdefault(o.id, script_exit_kinds(
                            os.path.join(self.root, layout.SRC), o)).get(r["value"] & ~1, [])
                        dest = self._exit_destination(sc["id"], kinds[0], exit_tables) if len(kinds) == 1 else None
                        add(code, tr("Door to {place}", place=dest) if dest else tr("Scripted event"))
        return legend

    def _exit_destination(self, scene_id, exit_kind, exit_tables):
        """As Scene_TakeExit: the kind's exit, else the scene's first exit's scene."""
        first = None
        for rows in exit_tables:
            for seg in rows:
                if seg.get("scene") != scene_id:
                    continue
                for ex in seg.get("exits", []):
                    if ex["kind"] in (exit_kind, 0xFF):
                        return self.scene_label(ex["scene"])
                if first is None and seg.get("exits"):
                    first = seg["exits"][0]["scene"]
        return tr("{place} (by default)", place=self.scene_label(first)) if first is not None else None
