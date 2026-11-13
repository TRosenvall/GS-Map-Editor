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
from gsmap import fsio, grid, layout, patch, preflight  # noqa: E402
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
    for name in ("ld_script.ld", "objects.tsv"):
        if os.path.exists(os.path.join(real, name)):
            shutil.copy(os.path.join(real, name), os.path.join(tbs, name))
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

    # ---- people are numbered as the game numbers them
    from gsmap.sceneedit import actor_numbers
    check("party rows are their own actors and take no slot",
          actor_numbers([{"sprite": 100}, {"sprite": 0}, {"sprite": 3}, {"sprite": 101}, {"sprite": -1}, {"sprite": 102}])
          == [8, 0, 3, 9])
    vale = by_name["Vale"]["id"]
    vale_map = next(m for m in p.maps.values() if by_name["Vale"]["layered_row"] in
                    {r["row"] for r in [m.resources] + m.alternates if r})
    described = events.describe(vale_map, vale)
    vo = s.overlay(by_name["Vale"]["overlay"])
    vrows = vo.rows(described["people_table"])
    if any(0 <= r["sprite"] <= 7 for r in vrows):
        expect = actor_numbers(vrows)
        check("a table with party rows lists people by their real numbers",
              [x["actor"] for x in described["people"]] == [a for a, r in zip(expect, vrows) if r["sprite"] >= 0])
    before = snapshot(tmp)
    added = events.add_person(vale, described["symbol"], 100, 64, 64, "Hello.")
    now = Overrides(tmp).get(vo.id, described["people_table"])["rows"]
    check("a new person's line goes to the number the game gives them", actor_numbers(now)[-1] == added["actor"], added)
    try:
        events.add_person(vale, described["symbol"], 0, 64, 64)
        check("the party can't be added as people", False)
    except ValueError:
        check("the party can't be added as people", True)

    # ---- an added person can be removed, with their lines; the game's own can't
    second = events.add_person(vale, described["symbol"], 101, 80, 64, "Second.")
    events.remove_person(vale, described["symbol"], added["actor"])
    after = events.describe(vale_map, vale)
    mine = [x for x in after["people"] if x["added"]]
    check("removing an added person leaves the others", [x["sprite"] for x in mine] == [101], mine)
    check("a later person moves up a number", mine and mine[0]["actor"] == added["actor"])
    lines = [e for e in after["events"] if e["actor"] == added["actor"]]
    check("and keeps their own line", len(lines) == 1 and lines[0]["text"] and "Second" in lines[0]["text"], lines)
    events.remove_person(vale, described["symbol"], added["actor"])
    check("removing every added person leaves the stage as the game has it",
          Overrides(tmp).get(vo.id, described["people_table"]) is None
          and Overrides(tmp).get(vo.id, described["symbol"]) is None)
    stock = next(x for x in after["people"] if not x["added"])
    try:
        events.remove_person(vale, described["symbol"], stock["actor"])
        check("the game's own people can't be removed", False)
    except ValueError:
        check("the game's own people can't be removed", True)

    # ---- text the game can't build is refused, and typed punctuation just works
    from gsmap.messages import Messages, tidy
    msgs = Messages(tmp)
    check("the alphabet comes from the catalog", msgs.alphabet() == 123, msgs.alphabet())
    for bad in ("Caf\u00e9", "~", "a|b", "a}b", "\u65e5", "tab\there"):
        check(f"text refused: {bad!r}", msgs.check(bad + "{end_wait}") is not None)
    check("plain text with commands passes", msgs.check("Hello, {protagonist_name}!\nOK?{end_wait}") is None)
    check("typed punctuation becomes plain", msgs.check(tidy("\u201cIt\u2019s\u2026 \u2014 fine\u201d")) is None)
    check("every stock line passes the check", not [n for n, e in msgs.entries.items()
          if e["text"] and "{" not in e["text"] and msgs.check(e["text"]) and e["text"].isascii()])
    size_before = len(msgs.entries)
    try:
        events.add_talk(vale, described["symbol"], added["actor"] + 1, "Caf\u00e9")
        check("an unbuildable line is refused before saving", False)
    except ValueError:
        check("an unbuildable line is refused before saving", len(Messages(tmp).entries) == size_before)
    bad_po = read(os.path.join(tmp, "games/tbs/text/en.po"))
    with open(os.path.join(tmp, "games/tbs/text/en.po"), "w", encoding="utf-8") as f:
        f.write(bad_po.replace('msgstr "Hello.{end_wait}"', 'msgstr "Caf\u00e9.{end_wait}"'))
    check("a bad line already saved is named", [x[1] for x in Messages(tmp).bad_lines()] == ["Caf\u00e9.{end_wait}"])
    with open(os.path.join(tmp, "games/tbs/text/en.po"), "w", encoding="utf-8") as f:
        f.write(before["games/tbs/text/en.po"])
    with open(os.path.join(tmp, "games/tbs/src/mod/overrides.json"), "w", encoding="utf-8") as f:
        f.write(before["games/tbs/src/mod/overrides.json"])
    generate(tmp, s, Overrides(tmp))

    # ---- arrival points are the scene's own
    from gsmap.getters import tables_for_scene as tfs
    kol = by_name["KolimaTunnel"]
    koverlay = s.overlay(kol["overlay"])
    own = tfs(p.tbs, koverlay, "entrances", "KolimaTunnel")
    first = next(r for r in koverlay.rows(own[0]) if r["entrance"] >= 0)
    listed = next(a for a in doors.entrances(kol["id"]) if a["entrance"] == first["entrance"])
    check("a room lists its own arrival points, not a neighbour's", (listed["x"], listed["z"]) == (first["x"], first["z"]), listed)

    # ---- people go in the table of the stage being edited
    tables = [(None, n, []) for n in ("gX_ActorPlacements", "gX_StormActorPlacements", "gX_NoActorPlacements")]
    check("a stage takes its same-named people", events._stage_placements("gX_StormTriggers", tables)[0] == "gX_StormActorPlacements")
    check("an unclear stage is refused, not guessed", events._stage_placements("gX_LaterTriggers", tables)[0] is None)
    check("a scene's only table is the one", events._stage_placements("gX_LaterTriggers", tables[:1])[0] == "gX_ActorPlacements")

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
    for damaged in ("[]", '{"a": 3}', "not json"):
        os.makedirs(os.path.join(tmp, fsio.JOURNAL))
        with open(os.path.join(tmp, fsio.JOURNAL, "list.json"), "w") as f:
            f.write(damaged)
        check(f"a damaged journal ({damaged}) is set aside, not acted on",
              fsio.recover(tmp) is False and not os.path.exists(os.path.join(tmp, fsio.JOURNAL)))
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

    # ---- undo reaches the build, and history survives what Finder does to it
    hist = os.path.join(tmp, "history")
    undo_file = os.path.join(tmp, "undo.txt")
    fsio.atomic_write(undo_file, "stock")
    old = time.time() - 10000
    os.utime(undo_file, (old, old))
    with fsio.transaction(tmp, hist, "an edit"):
        fsio.atomic_write(undo_file, "edited")
    built = time.time() - 5
    os.utime(os.path.join(tmp, "undo.txt"), (built, built))
    with open(os.path.join(hist, ".DS_Store"), "w") as f:
        f.write("x")
    check("Finder's files in history are ignored", fsio.last_saved(hist)["label"] == "an edit")
    os.makedirs(os.path.join(hist, str(time.time_ns())))
    check("an entry cut short is skipped", fsio.last_saved(hist)["label"] == "an edit")
    check("undo steps past it", fsio.undo_last(hist) == "an edit" and read(undo_file) == "stock")
    check("a file undone is newer than the last build, so make rebuilds it",
          os.stat(undo_file).st_mtime > built)
    locked = os.path.join(tmp, "locked.txt")
    fsio.atomic_write(locked, "locked")
    other = os.path.join(tmp, "other.txt")
    fsio.atomic_write(other, "before")
    os.chflags(locked, 2)  # UF_IMMUTABLE, Finder's Locked
    try:
        with fsio.transaction(tmp, hist, "touches a locked file"):
            fsio.atomic_write(other, "after")
            fsio.atomic_write(locked, "changed")
        check("a locked file is refused", False)
    except OSError:
        check("a locked file is refused", True)
    os.chflags(locked, 0)
    check("and the rest of that action is undone", read(other) == "before" and read(locked) == "locked")
    check("and no journal is left to block later saves", not os.path.exists(os.path.join(tmp, fsio.JOURNAL)))
    with fsio.transaction(tmp, hist, "the next save"):
        fsio.atomic_write(other, "works")
    check("the next save works", read(other) == "works")
    readonly_history = os.path.join(tmp, "readonly-history")
    os.makedirs(readonly_history)
    os.chmod(readonly_history, 0o500)
    with fsio.transaction(tmp, readonly_history, "x"):
        fsio.atomic_write(other, "kept")
    os.chmod(readonly_history, 0o700)
    check("history that can't be written doesn't undo the save", read(other) == "kept")
    check("or leave a journal that would undo it next start", not os.path.exists(os.path.join(tmp, fsio.JOURNAL)))

    # ---- redo puts back what undo took, until something new is saved
    rh = os.path.join(tmp, "redo-history")
    one, made = os.path.join(tmp, "one.txt"), os.path.join(tmp, "made.txt")
    fsio.atomic_write(one, "1")
    with fsio.transaction(tmp, rh, "the second", "051"):
        fsio.atomic_write(one, "2")
    with fsio.transaction(tmp, rh, "the third"):
        fsio.atomic_write(one, "3")
        fsio.atomic_write(made, "new")
    check("undo takes back the newest", fsio.undo_last(rh, tmp) == "the third" and read(one) == "2" and not os.path.exists(made))
    check("and Redo offers it", (fsio.next_redo(rh) or {}).get("label") == "the third")
    check("undo again takes the one before", fsio.undo_last(rh, tmp) == "the second" and read(one) == "1")
    check("redo does them again in order", fsio.redo_last(rh, tmp) == "the second" and read(one) == "2"
          and fsio.last_saved(rh).get("where") == "051")
    check("all the way", fsio.redo_last(rh, tmp) == "the third" and read(one) == "3" and read(made) == "new")
    check("then there's nothing to redo", fsio.next_redo(rh) is None and fsio.redo_last(rh, tmp) is None)
    fsio.undo_last(rh, tmp)
    with fsio.transaction(tmp, rh, "something new"):
        fsio.atomic_write(one, "new")
    check("a new change clears Redo", fsio.next_redo(rh) is None)
    check("and Undo still steps back through it", fsio.undo_last(rh, tmp) == "something new" and read(one) == "2")
    check("undo and redo leave no journal", not os.path.exists(os.path.join(tmp, fsio.JOURNAL)))

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

    # ---- Play starts somewhere you can walk
    from gsmap import playtest
    class Grid:
        cells = [[255] * 128 for _ in range(128)]
    class Fake:
        heights = {}

        @staticmethod
        def load_grid(info, plane):
            return Grid

        @staticmethod
        def ground_height(info, x, z):
            return Fake.heights.get((x >> 4, z >> 4), 0)
    walled = {"entrance": 0, "x": 120, "z": 100}
    openfloor = {"entrance": 1, "x": 32, "z": 32}
    Grid.cells[2][2] = 0
    Grid.cells[2][3] = 0
    check("Play skips an arrival on a wall", playtest.landing(Fake, object(), [walled, openfloor]) == (openfloor, True))
    Fake.heights[(3, 2)] = 40
    check("or one boxed in by height", playtest.landing(Fake, object(), [openfloor]) == (openfloor, False))
    Fake.heights.clear()
    Grid.cells[2][2] = Grid.cells[2][3] = 255
    check("and says so when every arrival is walled in", playtest.landing(Fake, object(), [walled, openfloor]) == (walled, False))
    Grid.cells[2][2] = Grid.cells[2][3] = Grid.cells[5][5] = Grid.cells[5][6] = 0
    other = {"entrance": 2, "x": 88, "z": 88}
    class Boxed:  # the walking graph: from arrival 1 the party can barely move
        starts = [(openfloor, "a"), (other, "b")]
        @staticmethod
        def flood(starts):
            return set(range(5)) if starts == ["a"] else set(range(500))
    check("Play skips an arrival the party can barely move from",
          playtest.landing(Fake, object(), [openfloor, other], Boxed) == (other, True))
    check("but keeps the plain check's pick when nothing has room",
          playtest.landing(Fake, object(), [openfloor], Boxed) == (openfloor, True))
    Grid.cells[2][2] = Grid.cells[2][3] = Grid.cells[5][5] = Grid.cells[5][6] = 255

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
    objects = os.path.join(tmp, layout.object_list(tmp)[0])
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

# ---- nothing unexpected in a checkout or a settings file stops the app opening
from gsmap import setup as setupmod  # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    os.makedirs(os.path.join(tmp, "games/tbs/text"))
    os.makedirs(os.path.join(tmp, "games/tbs/include"))
    os.makedirs(os.path.join(tmp, "games/tbs/src/mod"))
    with open(os.path.join(tmp, "games/tbs/text/en.po"), "wb") as f:
        f.write(b'msgid "00000"\nmsgstr "\xff\xfe"\n')
    with open(os.path.join(tmp, "games/tbs/include/sprite_ids.h"), "w") as f:
        f.write("enum SpriteId { SPRITE_ONE, SPRITE_TWO = SPRITE_ONE, };\n")
    with open(os.path.join(tmp, "games/tbs/src/mod/names.json"), "w") as f:
        f.write("not json")
    try:
        Names(tmp)
        check("names: a damaged checkout shows numbers, not a crash", True)
    except Exception as e:  # noqa: BLE001
        check("names: a damaged checkout shows numbers, not a crash", False, repr(e))
    check("preflight answers in words, whatever it finds", all(isinstance(x, str) for x in preflight.check(tmp)) and preflight.check(tmp))
    check("a preflight that can't read anything still answers", preflight.check(os.path.join(tmp, "nothing")))
    with open(os.path.join(tmp, "games/tbs/src/mod/overrides.json"), "w") as f:
        f.write("{broken")
    try:
        Overrides(tmp)
        check("damaged saved edits are named, not misread", False)
    except ValueError as e:
        check("damaged saved edits are named, not misread", "overrides.json" in str(e))
    settings_backup = setupmod.SETTINGS
    setupmod.SETTINGS = os.path.join(tmp, "settings.json")
    with open(setupmod.SETTINGS, "w") as f:
        f.write("[]")
    check("settings that aren't settings are ignored", setupmod.load_settings() == {})
    setupmod.SETTINGS = settings_backup
    check("a path with a space is explained", setupmod.path_problem("/Users/a b/x") and not setupmod.path_problem("/Users/ab/x"))
    bytes_job = setupmod.Job("bytes", [["/usr/bin/printf", "caf\\351\\n"]])
    for _ in range(50):
        if bytes_job.done:
            break
        time.sleep(0.1)
    check("a stray byte in a step's output can't hang setup", bytes_job.done and bytes_job.ok)

# ---- Reset takes out the editor's text, and nothing else
from gsmap import layout, reset as resetmod  # noqa: E402
from gsmap.messages import BEGIN, END  # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    def git(*args):
        subprocess.run(["git", "-C", tmp, "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True, capture_output=True)
    po = os.path.join(tmp, layout.TEXT_EN)
    os.makedirs(os.path.dirname(po))
    stock = 'msgctxt "message"\nmsgid "00000"\nmsgstr "Stock."\n\n# hand-made\nmsgctxt "message"\nmsgid "00001"\nmsgstr "Hub."\n'
    block = f'\n{BEGIN}\n\nmsgctxt "message"\nmsgid "00002"\nmsgstr "Mine."\n\n{END}\n'
    with open(po, "w", encoding="utf-8") as f:
        f.write(stock)
    git("init", "-q")
    git("add", ".")
    git("commit", "-qm", "base")
    base = subprocess.run(["git", "-C", tmp, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    with open(po, "w", encoding="utf-8") as f:
        f.write(stock + block)
    check("unused text of ours is removed, leaving the rest exact", resetmod._drop_unused_text(tmp, base) and read(po) == stock)
    with open(po, "w", encoding="utf-8") as f:
        f.write(stock + block)
    ov = Overrides(tmp)
    ov.set(1, "gT", "events", [{"control": 0, "trigger": 8, "condition": -1, "value": 2}])
    ov.save()
    check("text an event uses stays", not resetmod._drop_unused_text(tmp, base) and read(po) == stock + block)
    os.remove(ov.path)
    git("add", ".")
    git("commit", "-qm", "the block, committed")
    check("a block in a commit stays: hand-written code may use it", not resetmod._drop_unused_text(tmp, base) and read(po) == stock + block)

# Pages run only the scripts beside them.
static = os.path.join(os.path.dirname(__file__), "..", "static")
for page in ("index.html", "world.html", "setup.html"):
    html = read(os.path.join(static, page))
    check(f"{page} has no inline script", "<script>" not in html and " onerror=" not in html and " onclick=" not in html)
for script in ("editor.js", "world.js", "common.js", "setup.js"):
    check(f"{script} writes no inline handlers", 'onerror="' not in read(os.path.join(static, script)))

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)
