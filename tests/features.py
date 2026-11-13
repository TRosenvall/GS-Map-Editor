"""The newer features' edge cases: removing added people, Play's start point,
export names, world map step spots and town icons, encounter zones, Reset's
battles, the atlas cache and Check's world issues. Like safety.py, it works on
throwaway copies, with the built scene code read from the real checkout.

Run: python3 tests/features.py [path/to/built/alchemy]
"""

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gsmap import atlas as atlasmod  # noqa: E402
from gsmap import encounters as enc  # noqa: E402
from gsmap import patch, playtest  # noqa: E402
from gsmap import reset as resetmod  # noqa: E402
from gsmap import world as worldmod  # noqa: E402
from gsmap.checks import Checker  # noqa: E402
from gsmap.doors import EVENT_EXIT, DoorEditor  # noqa: E402
from gsmap.events import EventEditor  # noqa: E402
from gsmap.modgen import Overrides  # noqa: E402
from gsmap.names import Names  # noqa: E402
from gsmap.project import Project  # noqa: E402
from gsmap.scenes import Scenes  # noqa: E402
from gsmap.setup import build_env  # noqa: E402
from gsmap.world import World  # noqa: E402

source = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/gs_project/alchemy-port")
os.environ["PATH"] = build_env()["PATH"]
failed = 0


def check(what, ok, info=""):
    global failed
    print(("ok   " if ok else "FAIL ") + what + (f"  ({info})" if info and not ok else ""))
    failed += not ok


def refused(what, fn):
    try:
        fn()
        check(what, False)
    except ValueError:
        check(what, True)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def fixture(tmp):
    """As safety.py's: the editable files copied, the rest linked to the real
    checkout (so nothing here may write under src/field, src/scene and the like)."""
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


def copy_files(tmp, rels):
    for rel in rels:
        os.makedirs(os.path.dirname(os.path.join(tmp, rel)), exist_ok=True)
        shutil.copy(os.path.join(source, rel), os.path.join(tmp, rel))


with tempfile.TemporaryDirectory() as tmp:
    p, s, n = fixture(tmp)
    events = EventEditor(p, s, n)
    by_name = {x["name"]: x for x in s.scenes}
    overrides = os.path.join(tmp, "games/tbs/src/mod/overrides.json")
    if not os.path.exists(overrides):  # a fresh checkout: no edits yet
        os.makedirs(os.path.dirname(overrides), exist_ok=True)
        Overrides(tmp).save()
    stock_ov = read(overrides)
    stock_tables = sorted(Overrides(tmp).data["tables"])  # the mod's own edits, already there

    # ---- removing an added person leaves the other rooms of their overlay alone
    # Goma Cave's bridge has one table of people; the stream room beside it, in
    # the same overlay, talks to its own person 8, the number a new person on the
    # bridge takes.
    bridge = by_name["GomaCaveBridge"]["id"]
    bmap = next(m for m in p.maps.values() if by_name["GomaCaveBridge"]["layered_row"] in
                {r["row"] for r in [m.resources] + m.alternates if r})
    stage = events.describe(bmap, bridge)
    added = events.add_person(bridge, stage["symbol"], 100, 64, 64, "On the bridge.")
    events.remove_person(bridge, stage["symbol"], added["actor"])
    left = sorted(Overrides(tmp).data["tables"])
    check("removing a person leaves another room's lines to its own people",
          not any("GomaCaveStream" in k for k in left), left)
    check("and the place is as the game has it again", left == stock_tables, left)

    # ---- two added people: removing the last leaves the first, with their line
    vale = by_name["Vale"]["id"]
    vmap = next(m for m in p.maps.values() if by_name["Vale"]["layered_row"] in
                {r["row"] for r in [m.resources] + m.alternates if r})
    stage = events.describe(vmap, vale)
    one = events.add_person(vale, stage["symbol"], 100, 64, 64, "First.")
    two = events.add_person(vale, stage["symbol"], 101, 80, 64, "Second.")
    events.remove_person(vale, stage["symbol"], two["actor"])
    after = events.describe(vmap, vale)
    mine = [x for x in after["people"] if x["added"]]
    check("removing the last added person leaves the first", [x["actor"] for x in mine] == [one["actor"]], mine)
    check("still saying their line", any(e["actor"] == one["actor"] and "First" in (e["text"] or "") for e in after["events"]))
    check("and nothing of the second is left", not any(e["actor"] == two["actor"] for e in after["events"]))
    refused("a person already removed can't be removed again",
            lambda: events.remove_person(vale, stage["symbol"], two["actor"]))
    events.remove_person(vale, stage["symbol"], one["actor"])
    write(overrides, stock_ov)

    # ---- Play: the wall check reads the grid where the window starts
    class Grid:
        cells = [[255] * 128 for _ in range(128)]

    class Shifted:  # a map whose layer starts 46 rows down the grid, as map 104's does
        @staticmethod
        def load_grid(info, plane):
            return Grid

        @staticmethod
        def ground_height(info, x, z):
            return 0

        @staticmethod
        def layer_origin(info, layer):
            return 0, 46
    spot = {"entrance": 0, "x": 32, "z": 32}  # cell (2, 2) of the window, (2, 48) of the grid
    for gz, gx in ((48, 2), (48, 3)):
        Grid.cells[gz][gx] = 0
    check("Play reads walls where the map's window is in its grid",
          playtest.landing(Shifted, object(), [spot]) == (spot, True))

    class Walk:  # two rows for arrival point 0: the first is where arrivals lists it
        starts = [({"entrance": 0}, "near"), ({"entrance": 0}, "far")]

        @staticmethod
        def flood(starts):
            return set(range(500)) if starts == ["near"] else set()
    other = {"entrance": 1, "x": 32, "z": 32}
    check("an arrival point's room is the first row's of its number",
          playtest.landing(Shifted, object(), [spot, other], Walk) == (spot, True))

    # ---- export names
    check("a name Windows keeps for a device isn't used", patch.slug("CON") != "con" and patch.slug("lpt1") != "lpt1")
    check("a very long name is cut to fit", len(patch.slug("x" * 400)) <= patch.MAX_SLUG)
    check("a name with no letters still gets one", patch.slug("!!!") == "my-mod")
    outdir = os.path.join(tmp, "exports")
    os.makedirs(outdir)
    open(os.path.join(outdir, "a.ips"), "w").close()
    check("an IPS alone counts as taken when keeping", patch.file_base(outdir, "A", keep=True).endswith("a-2"))

    # Export again without IPS: the old IPS (an older mod) goes.
    rom_root = os.path.join(tmp, "romroot")
    os.makedirs(os.path.join(rom_root, "out", "tbs-en"))
    with open(os.path.join(rom_root, "out", "tbs-en", "tbs-en.gba"), "wb") as f:
        f.write(bytes(range(256)) * 4 + b"mod")
    stock_path = os.path.join(tmp, "stock.gba")
    with open(stock_path, "wb") as f:
        f.write(bytes(range(256)) * 4 + b"old")

    class FakeMake:
        stdout = []

        def __init__(self, *a, **k):
            pass

        @staticmethod
        def wait():
            return 0
    real_popen, real_stock = patch.subprocess.Popen, patch.stock_rom
    try:
        patch.subprocess.Popen = FakeMake
        patch.stock_rom = lambda *a, **k: (stock_path, "0" * 40)
        patch.export(rom_root, outdir, tmp, {}, lambda line: None, "Twice", ips=True)
        check("an export with IPS writes both", all(os.path.exists(os.path.join(outdir, "twice" + e)) for e in (".bps", ".ips")))
        patch.export(rom_root, outdir, tmp, {}, lambda line: None, "Twice")
        check("replacing it without IPS takes the old IPS away", not os.path.exists(os.path.join(outdir, "twice.ips")))
    finally:
        patch.subprocess.Popen, patch.stock_rom = real_popen, real_stock

    # ---- world step spots
    w = World(tmp)
    blocks_before = read(w.blocks_path)
    story = next(((gx, gy) for gy in range(256) for gx in range(256)
                  if (w.cell(gx, gy)[0] >> 16) & 0xFF == 90), None)
    if story:
        refused("a square that starts a story scene isn't removed as a step spot",
                lambda: worldmod.remove_step(w, p, s, n, story[0], story[1]))
        check("and its squares keep their code", read(w.blocks_path) == blocks_before)
    refused("a square outside the world is refused", lambda: worldmod.remove_step(w, p, s, n, -1, 3))
    free = [(gx, gy) for gy in range(60, 200, 7) for gx in range(60, 200, 7) if not (w.cell(gx, gy)[0] >> 16) & 0xFF]
    a = worldmod.add_step(w, p, s, n, free[0][0], free[0][1], vale, 0)
    b = worldmod.add_step(w, p, s, n, free[1][0], free[1][1], vale, 0)
    de = DoorEditor(p, s, n)
    o = s.overlay(next(x for x in s.scenes if x["id"] == worldmod.WORLD_SCENE)["overlay"])
    script_kinds = {k for ks in de._script_kinds(o).values() for k in ks}
    check("two spots take their own codes and exit kinds", a["code"] != b["code"] and a["kind"] != b["kind"], (a, b))
    check("and no kind a scene script asks for", not {a["kind"], b["kind"]} & script_kinds)
    worldmod.remove_step(w, p, s, n, free[0][0], free[0][1])
    places = worldmod.world_places(World(tmp), p, s, n)
    st = next((x for x in places["steps"] if (x["gx"], x["gy"]) == free[1]), None)
    check("removing the first leaves the second leading where it did", st and st["lead"] and st["lead"]["scene"] == vale, st)
    worldmod.extend_step(w, p, s, n, free[2][0], free[2][1], b["code"])
    found = []
    Checker(p, s, n)._world_issues(lambda *x, **k: found.append(x[5]), lambda sid: {99} if sid == vale else set(), False)
    check("Check names a wide spot once", found.count(f"step:{b['code']}") == 1, found)
    worldmod.remove_step(w, p, s, n, free[1][0], free[1][1])
    check("removing it takes every square", read(w.blocks_path) == blocks_before)
    check("and its tables", read(overrides) == stock_ov)

    # A step spot of the game's own whose exit kind a scene script also asks for:
    # the exit stays for the script.
    events_t = de._tables([o], Overrides(tmp), "events")
    shared_kind = next((r for _, _, rs in events_t for r in rs if r["control"] & 0xF == EVENT_EXIT
                        and r["value"] in script_kinds and r["trigger"] < worldmod.ICON_TRIGGER), None)
    if shared_kind:
        cell = next(((gx, gy) for gy in range(256) for gx in range(256)
                     if (w.cell(gx, gy)[0] >> 16) & 0xFF == shared_kind["trigger"]), None)
        if cell:
            worldmod.remove_step(w, p, s, n, *cell)
            exits = de._tables([o], Overrides(tmp), "exits")
            check("an exit a scene script takes stays when its step spot goes",
                  any(e["kind"] == shared_kind["value"] for _, _, segs in exits for seg in segs
                      if seg.get("scene") == worldmod.WORLD_SCENE for e in seg.get("exits", [])))
            write(w.blocks_path, blocks_before)
            write(overrides, stock_ov)
            w = World(tmp)

    # ---- town icons: removing the last added leaves the first
    sprite = worldmod.icon_sprites(p, s, n)[0]["sprite"]
    first = worldmod.add_icon(w, p, s, n, 4000, 4000, sprite, vale, 0)
    second = worldmod.add_icon(w, p, s, n, 4100, 4000, sprite, vale, 0)
    check("icons take kinds no scene script asks for", not {first["kind"], second["kind"]} & script_kinds)
    worldmod.remove_icon(w, p, s, n, second["actor"])
    places = worldmod.world_places(World(tmp), p, s, n)
    mine = [i for i in places["icons"] if i["added"]]
    check("removing the last icon leaves the first where it was, leading where it did",
          len(mine) == 1 and mine[0]["actor"] == first["actor"] and mine[0]["x"] == 4000
          and mine[0]["lead"] and mine[0]["lead"]["scene"] == vale, mine)
    again = worldmod.add_icon(w, p, s, n, 4200, 4000, sprite, vale, 0)
    check("a new icon after a removal takes the freed number", again["actor"] == second["actor"], again)
    worldmod.remove_icon(w, p, s, n, first["actor"])
    worldmod.remove_icon(w, p, s, n, first["actor"])
    check("removing them all puts the tables back", read(overrides) == stock_ov)

    # ---- the atlas layout follows where doors are
    key = atlasmod.layout_key(p, "en")
    grid = bmap.grid_path()
    os.utime(grid, ns=(os.stat(grid).st_atime_ns, os.stat(grid).st_mtime_ns + 10**9))
    check("the atlas is laid out again when a map's squares change", atlasmod.layout_key(p, "en") != key)

# ---- encounter zones
with tempfile.TemporaryDirectory() as etmp:
    copy_files(etmp, (enc.ZONES, enc.RULES, enc.SCENE_RULES, enc.FORMATIONS, enc.ENEMY_IDS, "games/tbs/text/en.po"))
    zones_path = os.path.join(etmp, enc.ZONES)
    original = read(zones_path)
    e = enc.Encounters(etmp)
    last = max(e.editable_zones())
    z = e.zones[last]
    groups = [{"formation": f, "weight": wt} for f, wt in zip(z["formations"], z["weights"])]
    e.set_zone(last, 100, [{"formation": groups[0]["formation"], "weight": 255}] * enc.MAX_GROUPS)
    again = enc.Encounters(etmp)
    check("a zone takes the most groups, rate and chance allowed",
          again.zones[last]["rate"] == 100 and again.zones[last]["weights"] == [255] * enc.MAX_GROUPS)
    check("and every other zone keeps its text", [again.zones[i] for i in range(len(again.zones)) if i != last]
          == [enc.Encounters.__new__(enc.Encounters)._zone(original[a:b])
              for i, (a, b) in enumerate(enc._entries(original, "gEncounterZones")) if i != last])
    for what, rate, gs in (("a rate over 100", 101, groups), ("a ninth group", 10, [groups[0]] * 9),
                           ("a chance over 255", 10, [dict(groups[0], weight=256)]), ("no group at all", 10, []),
                           ("a group that doesn't exist", 10, [dict(groups[0], formation=len(e.formations))])):
        refused(f"{what} is refused", lambda: again.set_zone(last, rate, gs))
    again.set_zone(last, z["rate"], groups)
    check("putting it back gives the file back byte for byte", read(zones_path) == original)

    # Braces in comments don't move the zones.
    plain = enc.Encounters(etmp).zones
    write(zones_path, original.replace("    // ENCOUNTER_ZONE_NONE\n", "    // ENCOUNTER_ZONE_NONE {\n    /* } */\n"))
    check("braces in comments don't change the zones", enc.Encounters(etmp).zones == plain)
    write(zones_path, original)

    # World rules written with names would shift every rule after them.
    rules_path = os.path.join(etmp, enc.RULES)
    rules = read(rules_path)
    write(rules_path, rules.replace("1,  4,  -1, 7,", "1,  BATTLE_ENVIRONMENT_BEACH,  -1, 7,", 1))
    refused("world battle rules it can't read are said, not misread", lambda: enc.Encounters(etmp))
    write(rules_path, rules)

    # ---- Reset: the world map's zones go back, places' battles stay
    def git(*args):
        subprocess.run(["git", "-C", etmp, *args], capture_output=True, check=True)
    git("init", "-q")
    git("-c", "user.name=t", "-c", "user.email=t@t", "add", ".")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    base = subprocess.run(["git", "-C", etmp, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    e = enc.Encounters(etmp)
    world_zone = min(e.world_zones())
    place_zone = min(z for z in e.editable_zones() if z not in e.world_zones())
    for zid in (world_zone, place_zone):
        zz = e.zones[zid]
        e.set_zone(zid, 50, [{"formation": zz["formations"][0], "weight": 9}])
    check("Reset world puts the world map's zones back", resetmod._restore_zones(etmp, base, e.world_zones()) == 1)
    after = enc.Encounters(etmp)
    check("and leaves the places' battles as they were edited",
          after.zones[world_zone] == enc.Encounters.__new__(enc.Encounters)._zone(
              original[slice(*enc._entries(original, "gEncounterZones")[world_zone])])
          and after.zones[place_zone]["rate"] == 50)

    class FewScenes:
        scenes = [{"id": 1, "name": "SolSanctumCorridor"}, {"id": 2, "name": "SolSanctumReliefs"}]
    zones, shared = resetmod._place_zones(etmp, FewScenes, {2})
    reliefs = {r["zone"] for r in e.scene_rules if r["scene"] == "SolSanctumReliefs"}
    check("a place resets every zone its scenes use", zones == reliefs, zones)
    check("and knows which other places share", shared == reliefs & {
        r["zone"] for r in e.scene_rules if r["scene"] != "SolSanctumReliefs"}, shared)
    check("Reset place puts its own battles back", resetmod._restore_zones(etmp, base, {place_zone}) == 1
          and read(zones_path) == original)

    # An original in an older alchemy's layout isn't put back: it wouldn't build.
    e.set_zone(place_zone, 50, [{"formation": e.zones[place_zone]["formations"][0], "weight": 9}])
    edited = read(zones_path)
    old_layout = original.replace(".formations =", ".enemies =")
    check("zones from an older layout are left as they are",
          enc.restore_zones(etmp, old_layout, {place_zone}) is None and read(zones_path) == edited)
    write(zones_path, original)

# ---- the commit the mod starts from: the pin, not a stale local main
with tempfile.TemporaryDirectory() as gtmp:
    def git(*args):
        return subprocess.run(["git", "-C", gtmp, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                              capture_output=True, text=True, check=True).stdout.strip()
    git("init", "-q", "-b", "main")
    commits = []
    for name in ("old main", "the pin", "the mod"):
        if name == "the mod":
            git("checkout", "-q", "-b", "mod")
        write(os.path.join(gtmp, "f.txt"), name)
        git("add", ".")
        git("commit", "-qm", name)
        commits.append(git("rev-parse", "HEAD"))
    git("branch", "-f", "main", commits[0])  # a clone's main, never moved on
    import gsmap.setup as setupmod
    real_pin = setupmod.ALCHEMY_PIN
    try:
        setupmod.ALCHEMY_PIN = commits[1]
        check("the mod starts from the pin, not an old main", patch.base_commit(gtmp) == commits[1])
        git("checkout", "-q", commits[0])
        check("a checkout older than the pin starts from itself", patch.base_commit(gtmp) == commits[0])
        git("checkout", "-q", "mod")
        setupmod.ALCHEMY_PIN = "0" * 40
        check("with no pin in the clone, main is the fallback", patch.base_commit(gtmp) == commits[0])
        check("a base chosen at setup comes first", patch.base_commit(gtmp, {"base_commit": "abc"}) == "abc")
    finally:
        setupmod.ALCHEMY_PIN = real_pin

# ---- small helpers -------------------------------------------------------------------
from gsmap.chests import CHEST_CONTROL, placed_codes  # noqa: E402
from gsmap.events import plain_doc  # noqa: E402
from gsmap.sceneedit import EVENTS_END  # noqa: E402
rows = [{"control": CHEST_CONTROL, "trigger": 100, "condition": 1, "value": 0},
        {"control": 3, "trigger": 101, "condition": 2, "value": 0x300005},   # a Psynergy Stone
        {"control": 3, "trigger": 102, "condition": 3, "value": 0x100005},   # a plain search
        {"control": EVENTS_END, "trigger": 0, "condition": 0, "value": 0}]
check("only chests and Psynergy Stones count toward the 10", placed_codes(rows, {100, 101, 102, 103}) == {100, 101})
check("a script's comment loses its code names",
      plain_doc("Walking into the pillar (PushedActor_AdvancePair) pushes it.  More here.") == "Walking into the pillar pushes it.")
check("joined place names are split", plain_doc("At BabiLighthouseStoneDoor, a switch hides.") == "At Babi Lighthouse Stone Door, a switch hides.")
check("a comment that can't be said plainly is left out", plain_doc("Sets FLAG_X when it ends.") == "")


# ---- heights, grids and walking graphs read the same, only faster
from gsmap import grid as gridmod  # noqa: E402
from gsmap import walk as walkmod  # noqa: E402
ch = Project.cell_height
check("a step below level 0 reads its own samples, not the unread third",
      ch([3, -2, -1, 0]) == -8 and ch([8, -3, -1, 0]) == -8)
check("flat, ramp and three-sample heights",
      ch([0, 2, 5, 9]) == 16 and ch([15, 2, 5, 9]) == 16 and ch([1, 2, 4, 0]) == 24 and ch([5, -3, -2, -1]) == -8)
g = gridmod.parse("grid:4x4\tat:1,1\tfill:1c:0:0\nfff fff:30:1 fff\n\n4fff:255 1c\n")
check("a grid reads repeated cells and empty rows as written",
      g.planes["metatile"] == [[0x1c] * 4, [0x1c, 0xfff, 0xfff, 0xfff], [0x1c] * 4, [0x1c, 0x4fff, 0x1c, 0x1c]]
      and g.planes["collision"][1] == [0, 0, 30, 0] and g.planes["shape"][1] == [0, 0, 1, 0]
      and g.planes["collision"][3] == [0, 255, 0, 0]
      and g.to_text() == "grid:4x4\tat:1,1\tfill:1c:0:0\nfff fff:30:1 fff\n\n4fff:255\n")
walk_project = Project(source)
walk_map = walk_project.maps["009"]
first = walkmod.Walk(walk_project, walk_map, [], [])
again = walkmod.Walk(walk_project, walk_map, [], [])
check("a map's walking graph is reused when nothing it reads changed", again.edges is first.edges)
gx, gz = first.grid_cell(first.x0 + 40, first.z0 + 40)
walled = walkmod.Walk(walk_project, walk_map, [], [], [{"plane": "collision", "x": gx, "y": gz, "value": 255}])
check("and made afresh around an unsaved wall", walled.edges is not first.edges
      and walled.edges != first.edges and walled.edges == walkmod.Walk(walk_project, walk_map, [], [], [
          {"plane": "collision", "x": gx, "y": gz, "value": 255}]).edges)

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)
