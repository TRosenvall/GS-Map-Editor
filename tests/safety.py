"""What must never go wrong with a user's mod: run on a throwaway copy of the
game's editable files, with the built scene code read from the real checkout.

Run: python3 tests/safety.py [path/to/built/alchemy]
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gsmap import fsio, grid, patch, preflight  # noqa: E402
from gsmap import tileset as tilesetmod  # noqa: E402
from gsmap.chests import ChestEditor  # noqa: E402
from gsmap.doors import DoorEditor  # noqa: E402
from gsmap.events import EventEditor  # noqa: E402
from gsmap.getters import tables_for_scene  # noqa: E402
from gsmap.modgen import Overrides, ensure_hook, generate, reconcile, validate_rows  # noqa: E402
from gsmap.names import Names  # noqa: E402
from gsmap.project import DirectoryError, Project  # noqa: E402
from gsmap.scenes import Scenes  # noqa: E402
from gsmap.setup import ALCHEMY_PIN, build_env  # noqa: E402
from gsmap.tileset import own_tileset  # noqa: E402
from gsmap.world import World, apply_world_edits  # noqa: E402

source = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/gs_project/alchemy-port")
os.environ["PATH"] = build_env()["PATH"]
failed = 0


def check(what, ok, info=""):
    global failed
    print(("ok   " if ok else "FAIL ") + what + (f"  ({info})" if info and not ok else ""))
    failed += not ok


def fixture(tmp):
    os.makedirs(os.path.join(tmp, "games/tbs/src"))
    os.makedirs(os.path.join(tmp, "games/tbs/text"))
    tbs, real = os.path.join(tmp, "games/tbs"), os.path.join(source, "games/tbs")
    for name in ("src/map", "src/mod", "src/graphics/tileset"):
        if os.path.exists(os.path.join(real, name)):
            shutil.copytree(os.path.join(real, name), os.path.join(tbs, name))
    shutil.copy(os.path.join(real, "text/en.po"), os.path.join(tbs, "text/en.po"))
    shutil.copy(os.path.join(real, "objects.tsv"), os.path.join(tbs, "objects.tsv"))
    os.makedirs(os.path.join(tbs, "src/system"))
    shutil.copy(os.path.join(real, "src/system/main_routine.c"), os.path.join(tbs, "src/system/main_routine.c"))
    for name in ("src/scene", "src/debug", "src/field", "src/game", "src/gamepak", "include"):
        os.symlink(os.path.join(real, name), os.path.join(tbs, name))
    for name in os.listdir(os.path.join(real, "src/graphics")):
        if name != "tileset":
            os.symlink(os.path.join(real, "src/graphics", name), os.path.join(tbs, "src/graphics", name))
    os.symlink(os.path.join(source, "out"), os.path.join(tmp, "out"))
    return Project(tmp), Scenes(tmp), Names(tmp)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def snapshot(root):
    out = {}
    for base, _, files in os.walk(os.path.join(root, "games/tbs/src/map")):
        for f in files:
            if f in ("map.txt", "map.s"):
                out[os.path.join(base, f)] = read(os.path.join(base, f))
    for rel in ("games/tbs/text/en.po", "games/tbs/src/mod/overrides.json", "games/tbs/src/mod/mod.c"):
        out[rel] = read(os.path.join(root, rel))
    return out


with tempfile.TemporaryDirectory() as tmp:
    p, s, n = fixture(tmp)
    chests = ChestEditor(p, s, n)
    events = EventEditor(p, s, n)
    doors = DoorEditor(p, s, n)
    by_name = {x["name"]: x for x in s.scenes}

    # ---- rooms keep to their own tables
    o = s.overlay(by_name["FuchinFallsCaveEntrance"]["overlay"])
    names = {sc: tables_for_scene(p.tbs, o, "events", sc) for sc in
             ("FuchinFallsCaveEntrance", "FuchinFallsCaveArcticBlade", "FuchinFallsCaveOrbOfForce")}
    check("each Fuchin Falls room resolves to one table of its own",
          all(len(v) == 1 for v in names.values()) and len({v[0] for v in names.values()}) == 3, names)
    stages = tables_for_scene(p.tbs, s.overlay(by_name["Vale"]["overlay"]), "events", "Vale")
    check("a scene's story stages all count", len(stages) == 3, stages)

    room = next(m for m in p.maps.values() if by_name["FuchinFallsCaveArcticBlade"]["layered_row"] in
                {r["row"] for r in [m.resources] + m.alternates if r} and 100 in [c for _, _, c in p.markers(m)])
    x, z, _ = next(c for c in p.markers(room) if c[2] == 100)
    before = {t: list(o.rows(t)) for t in o.tables if o.tables[t]["kind"] == "events" and o.tables[t]["editable"]}
    chests.set_contents(room, x, z, {"coins": 77})
    ov = Overrides(tmp)
    edited = [k for k in ov.data["tables"] if k.startswith(f"{o.id:x}:")]
    check("changing a chest edits only its own room's table",
          len(edited) == 1 and "ArcticBlade" in edited[0], edited)
    listed = [c for c in chests.list(room) if c["code"] == 100]
    check("the chest reads back with its new contents", listed and listed[0]["contents"] == "77 coins", listed)
    check("generate produced mod.c without error", "Mod_" in read(os.path.join(tmp, "games/tbs/src/mod/mod.c")))
    chests.set_contents(room, x, z, {"item": 1})
    # back to clean for what follows
    ov = Overrides(tmp)
    ov.data["tables"] = {k: v for k, v in ov.data["tables"].items() if "ArcticBlade" not in k}
    ov.save()
    generate(tmp, s, ov)

    # ---- nothing half done
    sandbox = p.maps["173"] if "173" in p.maps else None
    before = snapshot(tmp)
    try:
        with fsio.transaction(tmp):
            p.apply_edits(sandbox, [{"plane": "collision", "x": 8, "y": 8, "value": 255}])
            events.add_spot(sandbox, 192, events.describe(sandbox, 192)["symbol"], 9, 8, "search", "Half done.")
            raise RuntimeError("the power went out")
    except RuntimeError:
        pass
    check("a failure part way undoes every file", snapshot(tmp) == before)
    with fsio.transaction(tmp):
        p.apply_edits(sandbox, [{"plane": "collision", "x": 8, "y": 8, "value": 255}])
        fsio.abort()
    check("abort() undoes the action too", snapshot(tmp) == before)
    check("no journal left behind", not os.path.exists(os.path.join(tmp, fsio.JOURNAL)))
    # A crash: the journal is there and the process never got to clean up.
    t = fsio._Transaction(tmp)
    fsio._current.txn = t
    p.apply_edits(sandbox, [{"plane": "collision", "x": 8, "y": 8, "value": 255}])
    fsio._current.txn = None
    check("the crash left a changed file", snapshot(tmp) != before)
    check("the next start restores it", fsio.recover(tmp) and snapshot(tmp) == before)
    check("and a clean start does nothing", fsio.recover(tmp) is False)
    target = os.path.join(tmp, "probe.txt")
    fsio.atomic_write(target, "first")
    real_replace = os.replace
    try:
        os.replace = lambda *a: (_ for _ in ()).throw(OSError("disk full"))
        try:
            fsio.atomic_write(target, "second")
        except OSError:
            pass
    finally:
        os.replace = real_replace
    check("a failed write leaves the old file whole", read(target) == "first")
    check("and no temp file", not [f for f in os.listdir(tmp) if f.startswith(".tmp-")])

    # ---- bad input can't poison the mod
    for bad, why in (([{"control": 2 ** 40, "trigger": 1, "condition": -1, "value": 0}], "too big"),
                     ([{"control": 0xFFFFFFFF, "trigger": "x", "condition": -1, "value": 0}], "not a number"),
                     ([{"control": 0, "trigger": 1, "condition": -1}], "missing a field")):
        try:
            validate_rows("events", bad)
            check(f"validate refuses a row {why}", False)
        except ValueError:
            check(f"validate refuses a row {why}", True)
    try:
        grid.parse("grid:128x128\tat:0,0\tfill:0:0:0\n" + "\n".join(["1"] * 200) + "\n")
        check("a grid with too many rows is refused", False)
    except ValueError:
        check("a grid with too many rows is refused", True)
    try:
        p.apply_edits(sandbox, [{"plane": "block", "x": 1, "y": 1, "value": 70000}])
        check("a block value too big is refused", False)
    except ValueError:
        check("a block value too big is refused", True)

    # ---- an alchemy update can't jam the mod
    ov = Overrides(tmp)
    key = next(iter(ov.data["tables"]))
    t = dict(ov.data["tables"][key])
    good_symbol = t["symbol"]
    known = t.get("fingerprint")
    check("edits carry a fingerprint after generating", bool(known))
    del ov.data["tables"][key]
    ov.data["tables"][f"{t['overlay']:x}:gOldName"] = dict(t, symbol="gOldName")
    ov.save()
    summary = generate(tmp, s, Overrides(tmp))
    check("a renamed table follows its fingerprint", summary["stale"] == [] and
          good_symbol in json.dumps(Overrides(tmp).data["tables"]), summary)
    ov = Overrides(tmp)
    key = next(k for k in ov.data["tables"] if ov.data["tables"][k]["symbol"] == good_symbol)
    ov.data["tables"][key]["fingerprint"]["stock"] = "not-what-it-was"
    ov.save()
    summary = generate(tmp, s, Overrides(tmp))
    check("an edit to a table whose original changed is left out, not built",
          good_symbol in summary["stale"] and good_symbol not in read(os.path.join(tmp, "games/tbs/src/mod/mod.c")), summary)
    check("the checker can see it", any(x["symbol"] == good_symbol for x in reconcile(Overrides(tmp), s)))
    ov = Overrides(tmp)
    key = next(k for k in ov.data["tables"] if ov.data["tables"][k]["symbol"] == good_symbol)
    ov.data["tables"][key]["fingerprint"]["stock"] = known["stock"]
    ov.save()
    generate(tmp, s, Overrides(tmp))

    # ---- Play's start-at-a-place code
    ov = Overrides(tmp)
    ov.data["playable"] = True
    ov.save()
    generate(tmp, s, ov)
    modc = os.path.join(tmp, "games/tbs/src/mod/mod.c")
    check("Play's build carries the start-at-a-place code", "gModPlaytestTarget" in read(modc))
    ov = Overrides(tmp)
    ov.data["playable"] = False
    ov.save()
    generate(tmp, s, ov)
    check("an exported build doesn't", "Playtest" not in read(modc))

    # ---- image import
    shared = [m for m in p.maps.values() if m.resources and m.number in ("005", "032", "003")]
    check("maps sharing even one tile sheet can't take an import", not any(own_tileset(p, m) for m in shared))
    check("the sandbox can", own_tileset(p, sandbox))

    # ---- a layout the editor can't read says so
    os.remove(os.path.join(tmp, "games/tbs/src/gamepak"))
    shutil.copytree(os.path.join(source, "games/tbs/src/gamepak"), os.path.join(tmp, "games/tbs/src/gamepak"))
    directory = os.path.join(tmp, "games/tbs/src/gamepak/resource_directory.s")
    text = read(directory)
    with open(directory, "w", encoding="utf-8") as f:
        f.write(text.replace("\tunused 20\n", "\twhatever Something\n\tunused 20\n"))
    try:
        Project(tmp).directory_entries()
        check("an unknown directory line is refused, not skipped", False)
    except DirectoryError as e:
        check("an unknown directory line is refused, not skipped", "doesn't understand" in str(e))
    check("the startup check reports it", any("doesn't understand" in x for x in preflight.check(tmp)))
    with open(directory, "w", encoding="utf-8") as f:
        f.write(text)

    # ---- hook
    main = os.path.join(tmp, "games/tbs/src/system/main_routine.c")
    objects = os.path.join(tmp, "games/tbs/objects.tsv")
    a, b = read(main), read(objects)
    ensure_hook(tmp)
    check("the hook isn't installed twice", read(main) == a and read(objects) == b)
    with open(objects, "w", encoding="utf-8") as f:
        f.write("nothing to anchor to\n")
    plain = a.replace("  MOD_SCENE_LOADED(gMainRoutineWork.next, &gOverlayArea);\n", "").replace('#include "../mod/mod_hook.h"\n', "")
    with open(main, "w", encoding="utf-8") as f:
        f.write(plain)
    try:
        ensure_hook(tmp)
        check("a source it can't hook is refused", False)
    except ValueError:
        check("a source it can't hook is refused", True)
    check("with nothing changed", read(main) == plain)
    with open(main, "w", encoding="utf-8") as f:
        f.write(a)
    with open(objects, "w", encoding="utf-8") as f:
        f.write(b)

    # ---- snowy world cells
    w = World(source)
    snowy = next((cx, cy) for cy in range(16) for cx in range(16)
                 if w.is_snowy(cx, cy) and w.shown_chunk(cx, cy) != w.chunk_of(cx, cy))
    w.blocks_path = os.path.join(tmp, "blocks.tsv")
    gx, gy = snowy[0] * 16 + 3, snowy[1] * 16 + 3
    shown = w.shown_chunk(*snowy)
    was = w.word(shown, 3, 3) & 0xFFFF
    apply_world_edits(w, [{"gx": gx, "gy": gy, "block": (was + 1) % len(w.block_tiles)}])
    check("a snowy world edit lands on the cells drawn", w.word(shown, 3, 3) & 0xFFFF != was and
          w.cell(gx, gy)[0] & 0xFFFF != was)

# ---- hostile patches fail quickly and plainly
src = bytes(range(256)) * 16


def crc_tail(body, source=src, target=b""):
    body = bytes(body) + zlib.crc32(source).to_bytes(4, "little") + zlib.crc32(target).to_bytes(4, "little")
    return body + zlib.crc32(body).to_bytes(4, "little")


def refused(name, fn):
    started = time.time()
    try:
        fn()
        check(f"{name} is refused", False)
    except ValueError:
        check(f"{name} is refused, quickly", time.time() - started < 1)


good = patch.bps_encode(src, src[:100] + b"changed" + src[107:], b"name: test\n")
check("a real patch still applies", patch.bps_apply(src, good)[100:107] == b"changed")
check("and its IPS and UPS paths aren't disturbed", patch.ips_apply(src, patch.ips_encode(src, src[:9] + b"x" + src[10:]))[9:10] == b"x")
vlq = patch._vlq
refused("a BPS asking for a huge game", lambda: patch.bps_apply(src, crc_tail(b"BPS1" + bytes(vlq(len(src))) + bytes(vlq(10 ** 12)) + bytes(vlq(0)))))
bomb = b"BPS1" + bytes(vlq(len(src))) + bytes(vlq(1000)) + bytes(vlq(0)) + bytes(vlq(((10 ** 11 - 1) << 2) | 3)) + bytes(vlq(0))
refused("a copy longer than the game it claims", lambda: patch.bps_apply(src, crc_tail(bomb)))
neg = b"BPS1" + bytes(vlq(len(src))) + bytes(vlq(1000)) + bytes(vlq(0)) + bytes(vlq((9 << 2) | 2)) + bytes(vlq((5 << 1) | 1))
refused("a copy from before the game's start", lambda: patch.bps_apply(src, crc_tail(neg)))
refused("a UPS asking for a huge game", lambda: patch.ups_apply(src, crc_tail(b"UPS1" + bytes(vlq(len(src))) + bytes(vlq(10 ** 12)))))
refused("an IPS cut short", lambda: patch.ips_apply(src, b"PATCH\x00\x00\x10\x00\xff"))
refused("a damaged BPS", lambda: patch.bps_apply(src, good[:40] + b"!" + good[41:]))
refused("rubbish", lambda: patch.apply_any(src, b"this is not a patch"))

# The README names the alchemy commit setup really downloads.
readme = open(os.path.join(os.path.dirname(__file__), "..", "README.md"), encoding="utf-8").read()
check("README names the pinned alchemy commit", ALCHEMY_PIN in readme and f"`{ALCHEMY_PIN[:10]}`" in readme)

# The list the import refusal offers agrees with the check an import makes.
listed = set(tilesetmod.own_tileset_maps(Project(source)))
listing = Project(source)
check("import: the places offered are the ones an import accepts",
      listed == {n for n, m in listing.maps.items() if own_tileset(listing, m)})

# Names come from the player's checkout, and none ship in the editor's data.
names = Names(source)
check("names: items, places, sprites and characters read from the checkout",
      names.item_name(1) != "item 1" and names.place(4) != "scene 4" and names.characters
      and not names.sprites[0]["name"].startswith("Sprite "))
data_dir = os.path.join(os.path.dirname(__file__), "..", "gsmap", "data")
shipped = "".join(open(os.path.join(data_dir, f), encoding="utf-8").read() for f in sorted(os.listdir(data_dir)))
game_words = {it["name"] for it in names.items.values() if not it["unused"]}
game_words |= {p["area_name"] for p in names.places.values() if p.get("area_name")}
game_words |= set(names.characters)
found = sorted(w for w in game_words if len(w) > 4 and w in shipped)
check("names: no game names in gsmap/data", not found, found[:5])
missing = Names(os.path.join(tempfile.gettempdir(), "gsmapedit-no-such-checkout"))
check("names: a missing checkout shows numbers, not a crash",
      missing.item_name(5) == "item 5" and missing.scene_label(3) == "scene 3")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)
