"""Everything the editor knows about where alchemy keeps things and what it
calls them. When upstream reorganises, this file is where the fix goes, and
gsmap/preflight.py is what says so. Paths are relative to the checkout.
"""

import os

SRC = "games/tbs/src"
INCLUDE = "games/tbs/include"

# Maps and what they draw
MAPS = f"{SRC}/map"                                # <place>/map.inc, map.txt, cell_pictures.tsv, shapes.tsv (map_NNN/ before 2026-11-13)
MAP_FILES = ("map.inc", "map.s")                   # a place's header and markers (map.s before 2026-11-17)
MAP_TABLES = (f"{SRC}/map/resources.c", f"{SRC}/map/maps.c")  # gMaps: each map's resources (maps.c before 2026-11-17)
DIRECTORY = f"{SRC}/gamepak/resource_directory.s"  # Resource_DirectoryTable
DIRECTORY_LABEL = "Resource_DirectoryTable:"
FIRST_MAP_ENTRIES = ("Field_EmptyMap", "Field_Map001")  # what gMaps' positions count from (Map001 before 2026-11-17)

# Scenes
SCENE_TABLE = f"{SRC}/field/scenes.s"              # gScenes
# Since 2026-11-25 gScenes names its overlay (OverlayId_, a row of DIRECTORY),
# area (enum AreaId) and map (MapIndex_, a `map` row of MAP_ROWS).
AREA_IDS = f"{INCLUDE}/area_ids.h"
MAP_ROWS = f"{SRC}/map/resources.s"
SCENE_SOURCES = (f"{SRC}/scene", f"{SRC}/debug")   # where the overlays' C lives
EXIT_NAMES = f"{INCLUDE}/scene_exits.h"
EXIT_REQUEST = "Import_EventSetExitRequest"        # what a scene script calls to leave
WORLD_PLACEMENTS = "gWorldMapActorPlacements"
# Pause-map markers, actor 11 + row: gMapScreen_AreaMarkers in map_screen_markers.c since
# 2026-11-25, gWorldPicture_AreaMarkers before (scripts.s before 2026-11-17).
AREA_MARKERS = (f"{SRC}/field/map_screen_markers.c", f"{SRC}/field/world_picture_markers.c", f"{SRC}/field/scripts.s")
AREA_MARKERS_LABELS = ("gMapScreen_AreaMarkers", "gWorldPicture_AreaMarkers")
SCENE_HEADERS = {f"{INCLUDE}/field/scene.h": ["struct SceneEntryPoints) == 48", "struct SceneExitRegion) == 16"],
                 f"{INCLUDE}/field/scene_tables.h": ["struct SceneEntrance) == 24", "struct ActorPlacement) == 24",
                                                     "struct Trigger) == 12"]}

# What a table's name says it holds (scene overlay symbols), for gsmap.scenes.
TABLE_WORDS = (("entrances", "Entrances"), ("exits", "Exits"), ("placements", "Placements"),
               ("events", "Triggers"), ("regions", "Regions"))

# Text
TEXT_EN = "games/tbs/text/en.po"

# Where the editor reads the game's names from: none of them ship with it.
FLAG_NAMES = f"{INCLUDE}/flags.h"                  # FLAG_* defines
SPRITE_NAMES = f"{INCLUDE}/sprite_ids.h"           # enum SpriteId
ITEM_TABLE = f"{SRC}/game/item_table.c"            # type and icon per item
ITEM_NAMES = f"{INCLUDE}/item_ids.h"               # enum ItemId: which row each [ITEM_*] is
AREA_RULES = (f"{SRC}/field/area_name_rules.s", f"{SRC}/field/scene_rules.s")  # gArea_NameRules (scene_rules.s before 2026-11-25)
SPRITE_TABLE = f"{SRC}/graphics/sprite/sprites.tsv"  # a row per sprite id; its pictures column names <name>.png
SPRITE_PICTURE_DIR = f"{SRC}/graphics/sprite"
SPRITE_PICTURE = f"{SRC}/graphics/sprite/spr_{{id:03d}}.png"  # before 2026-11-13, with no sprites.tsv

# The world map
WORLD_BLOCKS = f"{SRC}/map/world/blocks.tsv"
# Newest first: cell_tiles.tsv and collision.tsv since 2026-11-25.
WORLD_CELLS = (f"{SRC}/map/default/cell_tiles.tsv", f"{SRC}/map/default/cell_pictures.tsv")
WORLD_COLLISION = (f"{SRC}/map/default/collision.tsv", f"{SRC}/map/default/collision.txt")
WORLD_GRAPHICS = f"{SRC}/graphics/world_map"

# Art cut at runtime
ITEM_ICON_LIST = f"{SRC}/graphics/ui/menu_icons/list.tsv"  # since 2026-11-25: a row per picture, `gItemIcons\t<name>` -> <name>.png beside it
ITEM_ICONS = f"{SRC}/graphics/ui/menu_icons.s"     # before: gItemIcons, icon n is its n-th label's .incbin, as a .png
ITEM_ICON = f"{SRC}/graphics/ui/menu_icons/item_{{icon:03d}}.png"  # before 2026-11-13

# The mod's folder and hook
MOD = f"{SRC}/mod"
HOOK_FILE = f"{SRC}/system/main_routine.c"
HOOK_AFTER = "  Overlay_Load(table[gMainRoutineWork.next].resourceId, &gOverlayArea);\n"
HOOK_CALL = "  MOD_SCENE_LOADED(gMainRoutineWork.next, &gOverlayArea);\n"
# Where the mod's object joins the link: last in the Game Pak, after the
# scene overlays. Alchemy lists objects in its linker script; copies set up
# before 2026-11-12 list them in objects.tsv instead.
OBJECT_LISTS = (
    ("games/tbs/ld_script.ld",
     f'        "*/{SRC}/system/overlay/overlays.o"(.data .overlays)\n',
     f'        "*/{MOD}/mod.o"(.text)\n'
     f'        "*/{MOD}/mod.o"(.rodata)\n'),
    ("games/tbs/objects.tsv",
     f"main\trom_tail_02\t{SRC}/system/overlay/overlays\n",
     f"main\trom_tail_02\t{MOD}/mod\t.text\n"
     f"main\trom_tail_02\t{MOD}/mod\t.rodata\n"),
)


def first_existing(root, paths):
    """The first of these paths this checkout has (the first when none is there)."""
    return next((p for p in paths if os.path.exists(os.path.join(root, p))), paths[0])


def first_map_entry(entries):
    """The directory label gMaps' positions count from, as this checkout names it."""
    return next((e for e in FIRST_MAP_ENTRIES if e in entries), FIRST_MAP_ENTRIES[0])


def map_table(root):
    return first_existing(root, MAP_TABLES)


def object_list(root):
    """(path, the line the mod's rows follow, the rows) for this checkout."""
    for entry in OBJECT_LISTS:
        if os.path.exists(os.path.join(root, entry[0])):
            return entry
    return OBJECT_LISTS[0]


MOD_INCLUDES = ("types.h", "field/scene.h", "field/scene_tables.h", "system/frame.h", "system/main_routine_work.h",
                "field/event_commands.h", "field/field_work.h", "scene_ids.h", "scene_exits.h", "game/game.h",
                "window/window.h", "system/system.h", "field/field.h")
# Before 2026-11-17 the headers sat flat or under module/<bank>/.
MOD_INCLUDES_FLAT = ("types.h", "field/scene.h", "field/scene_tables.h", "frame.h", "main_routine_work.h",
                     "module/field/event_commands.h", "field_work.h", "scene_ids.h", "scene_exits.h",
                     "module/game/game.h", "module/window/window.h", "module/system/system.h", "system.h", "game.h",
                     "field.h", "window.h")


def mod_includes(root):
    """The headers mod.c includes, as this checkout lays them out."""
    flat = os.path.isdir(os.path.join(root, INCLUDE, "module"))
    return MOD_INCLUDES_FLAT if flat else MOD_INCLUDES


# Build output
ROM = "out/tbs-en/tbs-en.gba"
ELF = "out/tbs-en/tbs-en.elf"
OVERLAYS = "out/tbs-en/overlays"
