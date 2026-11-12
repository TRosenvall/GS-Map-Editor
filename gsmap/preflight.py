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
from .i18n import fill, tr


class Damage(str):
    """A problem that means the files themselves are damaged, rather than from a
    version the editor can't read; setup words its advice differently."""


def check(root):
    """[plain-language problem], empty when the checkout can be read. Whatever is
    wrong with the checkout, this answers in words: it runs before anything can
    show a message, so a crash here would look like an app that won't open."""
    try:
        return _check(root)
    except Exception as e:  # noqa: BLE001
        return [Damage(tr("The game source has been damaged, so it couldn't be read ({error}). Move this folder "
                          "aside, then use a fresh download.", error=type(e).__name__))]


def _check(root):
    problems = []

    def need(rel, problem):
        """problem: the sentence to give if rel is missing, with {path} for rel."""
        if not os.path.exists(os.path.join(root, rel)):
            problems.append(fill(problem, {"path": rel}))
            return False
        return True

    def read(rel):
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as f:
            return f.read()

    for rel, problem in ((layout.MAPS, tr("Can't find the maps ({path}).")),
                         (layout.MAP_TABLE, tr("Can't find the map list ({path}).")),
                         (layout.DIRECTORY, tr("Can't find the resource directory ({path}).")),
                         (layout.SCENE_TABLE, tr("Can't find the scene list ({path}).")),
                         (layout.EXIT_NAMES, tr("Can't find the exit names ({path}).")),
                         (layout.TEXT_EN, tr("Can't find the English text ({path}).")),
                         (layout.WORLD_BLOCKS, tr("Can't find the world map ({path}).")),
                         (layout.WORLD_CELLS, tr("Can't find the world map's blocks ({path}).")),
                         (layout.WORLD_COLLISION, tr("Can't find the world map's walkability ({path}).")),
                         (layout.WORLD_GRAPHICS, tr("Can't find the world map's art ({path}).")),
                         (layout.OBJECTS, tr("Can't find the object list ({path}).")),
                         (layout.HOOK_FILE, tr("Can't find the code that loads scenes ({path}).")),
                         (layout.FLAG_NAMES, tr("Can't find the flag names ({path}).")),
                         (layout.SPRITE_NAMES, tr("Can't find the sprite names ({path}).")),
                         (layout.ITEM_TABLE, tr("Can't find the item list ({path}).")),
                         (layout.AREA_RULES, tr("Can't find the area names ({path})."))):
        need(rel, problem)
    for folder in layout.SCENE_SOURCES:
        need(folder, tr("Can't find the scene code ({path})."))
    if problems:
        return problems

    # Text the editor rewrites has to be real text: a stray byte can't be saved back.
    for rel in (layout.TEXT_EN, layout.SCENE_TABLE):
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as f:
                f.read()
        except UnicodeDecodeError:
            problems.append(Damage(tr("{path} has been damaged: it isn't plain text any more. Restore it, or move "
                                      "this folder aside and download a fresh copy.", path=rel)))
    if problems:
        return problems

    # The layouts the editor reads table bytes with.
    for rel, sizes in layout.SCENE_HEADERS.items():
        if need(rel, tr("Can't find the scene table formats ({path}).")):
            text = read(rel)
            for size in sizes:
                if size not in text:
                    problems.append(tr("The game's format for {name} has changed ({path}); the editor would "
                                       "misread scene tables.", name=size.split(')')[0].replace('struct ', ''),
                                       path=rel))

    # Where the editor reads the game's names.
    sprites = tr("Can't find the sprite names in {path}, so things would show numbers instead of names.")
    areas = tr("Can't find the area names in {path}, so things would show numbers instead of names.")
    items = tr("Can't find the item names in {path}, so things would show numbers instead of names.")
    characters = tr("Can't find the character names in {path}, so things would show numbers instead of names.")
    alphabet = tr("Can't find the text alphabet in {path}, so things would show numbers instead of names.")
    for rel, anchor, problem in ((layout.SPRITE_NAMES, "enum SpriteId", sprites),
                                 (layout.AREA_RULES, "gArea_NameRules", areas),
                                 (layout.TEXT_EN, 'msgctxt "MsgItemName"', items),
                                 (layout.TEXT_EN, 'msgctxt "MsgDebugAreaName"', areas),
                                 (layout.TEXT_EN, 'msgctxt "MsgCharacterName"', characters),
                                 (layout.TEXT_EN, "X-Alchemy-Symbol-Count:", alphabet)):
        if anchor not in read(rel):
            problems.append(fill(problem, {"path": rel}))

    # The hook must be there or have somewhere to go.
    source = read(layout.HOOK_FILE)
    if layout.HOOK_CALL not in source and layout.HOOK_AFTER not in source:
        problems.append(tr("Can't find where scenes get loaded in {path}, so edits to people, doors "
                           "and events couldn't reach the game.", path=layout.HOOK_FILE))
    objects = read(layout.OBJECTS)
    if layout.OBJECTS_ROWS not in objects and layout.OBJECTS_AFTER not in objects:
        problems.append(tr("Can't find the place for the mod in {path}.", path=layout.OBJECTS))

    # Maps, all the way down to the art they draw.
    from .project import Project, DirectoryError
    try:
        project = Project(root)
    except DirectoryError as e:
        return problems + [str(e)]
    except Exception as e:  # noqa: BLE001  anything at all here means a format changed
        return problems + [tr("Couldn't read the maps: {error}", error=f"{type(e).__name__}: {e}")]
    if len(project.maps) < 100:
        problems.append(tr("Only found {n} maps; expected about 180.", n=len(project.maps)))
    rows = project.map_rows()
    entries = project.directory_entries()
    if layout.FIRST_MAP_ENTRY not in entries:
        problems.append(tr("The resource directory has no {name}, which map art is counted from.",
                           name=layout.FIRST_MAP_ENTRY))
        return problems
    base = entries.index(layout.FIRST_MAP_ENTRY)
    too_far = sum(1 for row in rows for v in row if base + v >= len(entries))
    if too_far:
        problems.append(tr("{n} map resources point past the end of the resource directory.", n=too_far))
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
        problems.append(tr("{n} maps have tile art the editor can't find (first: map {first}).",
                           n=len(no_art), first=no_art[0]))
    if no_table:
        problems.append(tr("{n} maps are missing their grid or block files (first: map {first}).",
                           n=len(no_table), first=no_table[0]))

    # Scenes, and any built code.
    from .scenes import Scenes, table_kind
    scenes = Scenes(root).scenes
    if len(scenes) < 100:
        problems.append(tr("Only found {n} scenes in {path}; expected about 200.", n=len(scenes),
                           path=layout.SCENE_TABLE))
    bad = sum(1 for s in scenes if not 0 <= s["layered_row"] < len(rows))
    if bad:
        problems.append(tr("{n} scenes name a map that isn't in the map list.", n=bad))
    text = "".join(read(os.path.join(dp, f).replace(root + os.sep, ""))
                   for folder in layout.SCENE_SOURCES for dp, _, fs in os.walk(os.path.join(root, folder))
                   for f in fs if f.endswith(".c"))
    if layout.EXIT_REQUEST not in text:
        problems.append(tr("Scene code no longer calls {name}, so scripted doors wouldn't be found.",
                           name=layout.EXIT_REQUEST))
    if layout.WORLD_PLACEMENTS not in text:
        problems.append(tr("Scene code no longer has {name}, so world map icons wouldn't be found.",
                           name=layout.WORLD_PLACEMENTS))
    found = {table_kind(name) for name in re.findall(r"\b(g\w+)\s*\[\s*\]\s*=", text)} - {None}
    missing = {k for k, _ in layout.TABLE_WORDS} - found
    if missing:
        problems.append(tr("No scene tables are named for: {kinds} (TABLE_WORDS in layout.py).",
                           kinds=", ".join(sorted(missing))))
    po = read(layout.TEXT_EN)
    if len(re.findall(r'^msgid "\d{5}"', po, re.M)) < 5000:
        problems.append(tr("{path} doesn't look like the game's text any more.", path=layout.TEXT_EN))
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
