"""Does this checkout look the way the editor expects?

Run when the editor starts, and on its own with `python3 -m gsmap.preflight
path/to/alchemy`. Alchemy reorganises often. Without this, a mismatch shows up
later and looks like something else (maps with the wrong tiles); with it, the
editor stops and says what it couldn't find. Problems are plain sentences; each
says which fact in gsmap/layout.py to look at.
"""

import os
import re
import sys

from . import layout


def check(root):
    """[plain-language problem], empty when the checkout can be read."""
    problems = []

    def need(rel, what):
        if not os.path.exists(os.path.join(root, rel)):
            problems.append(f"Can't find {what} ({rel}).")
            return False
        return True

    def read(rel):
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as f:
            return f.read()

    for rel, what in ((layout.MAPS, "the maps"), (layout.MAP_TABLE, "the map list"),
                      (layout.DIRECTORY, "the resource directory"), (layout.SCENE_TABLE, "the scene list"),
                      (layout.EXIT_NAMES, "the exit names"), (layout.TEXT_EN, "the English text"),
                      (layout.WORLD_BLOCKS, "the world map"), (layout.WORLD_CELLS, "the world map's blocks"),
                      (layout.WORLD_COLLISION, "the world map's walkability"),
                      (layout.WORLD_GRAPHICS, "the world map's art"), (layout.OBJECTS, "the object list"),
                      (layout.HOOK_FILE, "the code that loads scenes"),
                      (layout.FLAG_NAMES, "the flag names"), (layout.SPRITE_NAMES, "the sprite names"),
                      (layout.ITEM_TABLE, "the item list"), (layout.AREA_RULES, "the area names")):
        need(rel, what)
    for folder in layout.SCENE_SOURCES:
        need(folder, "the scene code")
    if problems:
        return problems

    # The layouts the editor reads table bytes with.
    for rel, sizes in layout.SCENE_HEADERS.items():
        if need(rel, "the scene table formats"):
            text = read(rel)
            for size in sizes:
                if size not in text:
                    problems.append(f"The game's format for {size.split(')')[0].replace('struct ', '')} "
                                    f"has changed ({rel}); the editor would misread scene tables.")

    # Where the editor reads the game's names.
    for rel, anchor, what in ((layout.SPRITE_NAMES, "enum SpriteId", "sprite names"),
                              (layout.AREA_RULES, "gArea_NameRules", "area names"),
                              (layout.TEXT_EN, 'msgctxt "MsgItemName"', "item names"),
                              (layout.TEXT_EN, 'msgctxt "MsgDebugAreaName"', "area names"),
                              (layout.TEXT_EN, 'msgctxt "MsgCharacterName"', "character names")):
        if anchor not in read(rel):
            problems.append(f"Can't find the {what} in {rel}, so things would show numbers instead of names.")

    # The hook must be there or have somewhere to go.
    source = read(layout.HOOK_FILE)
    if layout.HOOK_CALL not in source and layout.HOOK_AFTER not in source:
        problems.append(f"Can't find where scenes get loaded in {layout.HOOK_FILE}, so edits to people, doors "
                        "and events couldn't reach the game.")
    objects = read(layout.OBJECTS)
    if layout.OBJECTS_ROWS not in objects and layout.OBJECTS_AFTER not in objects:
        problems.append(f"Can't find the place for the mod in {layout.OBJECTS}.")

    # Maps, all the way down to the art they draw.
    from .project import Project, DirectoryError
    try:
        project = Project(root)
    except DirectoryError as e:
        return problems + [str(e)]
    except Exception as e:  # noqa: BLE001  anything at all here means a format changed
        return problems + [f"Couldn't read the maps: {type(e).__name__}: {e}"]
    if len(project.maps) < 100:
        problems.append(f"Only found {len(project.maps)} maps; expected about 180.")
    rows = project.map_rows()
    entries = project.directory_entries()
    if layout.FIRST_MAP_ENTRY not in entries:
        problems.append(f"The resource directory has no {layout.FIRST_MAP_ENTRY}, which map art is counted from.")
        return problems
    base = entries.index(layout.FIRST_MAP_ENTRY)
    too_far = sum(1 for row in rows for v in row if base + v >= len(entries))
    if too_far:
        problems.append(f"{too_far} map resources point past the end of the resource directory.")
    no_art, no_table = [], []
    for info in project.maps.values():
        if not info.resources:
            continue
        labels = [info.resources["palette"]] + [b for b in info.resources["blocks"] if b]
        if any(project.label_path(label) is None for label in labels):
            no_art.append(info.number)
        if not os.path.exists(info.grid_path()) or not os.path.exists(info.source("CELL_PICTURES", "cell_pictures.tsv")):
            no_table.append(info.number)
    if no_art:
        problems.append(f"{len(no_art)} maps have tile art the editor can't find (first: map {no_art[0]}).")
    if no_table:
        problems.append(f"{len(no_table)} maps are missing their grid or block files (first: map {no_table[0]}).")

    # Scenes, and any built code.
    from .scenes import Scenes, table_kind
    scenes = Scenes(root).scenes
    if len(scenes) < 100:
        problems.append(f"Only found {len(scenes)} scenes in {layout.SCENE_TABLE}; expected about 200.")
    bad = sum(1 for s in scenes if not 0 <= s["layered_row"] < len(rows))
    if bad:
        problems.append(f"{bad} scenes name a map that isn't in the map list.")
    text = "".join(read(os.path.join(dp, f).replace(root + os.sep, ""))
                   for folder in layout.SCENE_SOURCES for dp, _, fs in os.walk(os.path.join(root, folder))
                   for f in fs if f.endswith(".c"))
    if layout.EXIT_REQUEST not in text:
        problems.append(f"Scene code no longer calls {layout.EXIT_REQUEST}, so scripted doors wouldn't be found.")
    if layout.WORLD_PLACEMENTS not in text:
        problems.append(f"Scene code no longer has {layout.WORLD_PLACEMENTS}, so world map icons wouldn't be found.")
    found = {table_kind(name) for name in re.findall(r"\b(g\w+)\s*\[\s*\]\s*=", text)} - {None}
    missing = {k for k, _ in layout.TABLE_WORDS} - found
    if missing:
        problems.append(f"No scene tables are named for: {', '.join(sorted(missing))} (TABLE_WORDS in layout.py).")
    po = read(layout.TEXT_EN)
    if len(re.findall(r'^msgid "\d{5}"', po, re.M)) < 5000:
        problems.append(f"{layout.TEXT_EN} doesn't look like the game's text any more.")
    return problems


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    problems = check(root)
    for p in problems:
        print("PROBLEM:", p)
    print(f"{root}: {'can be read' if not problems else f'{len(problems)} problem(s)'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
