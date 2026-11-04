"""Everything the editor knows about where alchemy keeps things and what it
calls them. When upstream reorganises, this file is where the fix goes, and
gsmap/preflight.py is what says so. Paths are relative to the checkout.
"""

SRC = "games/tbs/src"
INCLUDE = "games/tbs/include"

# Maps and what they draw
MAPS = f"{SRC}/map"                                # map_NNN/map.s, map.txt, cell_pictures.tsv, shapes.tsv
MAP_TABLE = f"{SRC}/map/maps.c"                    # gMaps: each map's resources
DIRECTORY = f"{SRC}/gamepak/resource_directory.s"  # Resource_DirectoryTable
DIRECTORY_LABEL = "Resource_DirectoryTable:"
FIRST_MAP_ENTRY = "Field_Map001"                   # what gMaps' positions count from

# Scenes
SCENE_TABLE = f"{SRC}/field/scenes.s"              # gScenes
SCENE_SOURCES = (f"{SRC}/scene", f"{SRC}/debug")   # where the overlays' C lives
EXIT_NAMES = f"{INCLUDE}/scene_exits.h"
EXIT_REQUEST = "Import_EventSetExitRequest"        # what a scene script calls to leave
WORLD_PLACEMENTS = "gWorldMapActorPlacements"
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
AREA_RULES = f"{SRC}/field/scene_rules.s"          # gArea_NameRules
SPRITE_PICTURE = f"{SRC}/graphics/sprite/spr_{{id:03d}}.png"

# The world map
WORLD_BLOCKS = f"{SRC}/map/world/blocks.tsv"
WORLD_CELLS = f"{SRC}/map/default/cell_pictures.tsv"
WORLD_COLLISION = f"{SRC}/map/default/collision.txt"
WORLD_GRAPHICS = f"{SRC}/graphics/world_map"

# Art cut at runtime
ITEM_ICON = f"{SRC}/graphics/ui/menu_icons/item_{{icon:03d}}.png"

# The mod's folder and hook
MOD = f"{SRC}/mod"
HOOK_FILE = f"{SRC}/system/main_routine.c"
HOOK_AFTER = "  Overlay_Load(table[gMainRoutineWork.next].resourceId, &gOverlayArea);\n"
HOOK_CALL = "  MOD_SCENE_LOADED(gMainRoutineWork.next, &gOverlayArea);\n"
OBJECTS = "games/tbs/objects.tsv"
OBJECTS_AFTER = f"main\trom_tail_02\t{SRC}/system/overlay/overlays\n"
OBJECTS_ROWS = (f"main\trom_tail_02\t{MOD}/mod\t.text\n"
                f"main\trom_tail_02\t{MOD}/mod\t.rodata\n")
MOD_INCLUDES = ("types.h", "field/scene.h", "field/scene_tables.h", "frame.h", "main_routine_work.h",
                "module/field/event_commands.h", "field_work.h", "scene_ids.h", "scene_exits.h", "module/game/game.h",
                "module/window/window.h", "module/system/system.h", "system.h", "game.h", "field.h", "window.h")

# Build output
ROM = "out/tbs-en/tbs-en.gba"
ELF = "out/tbs-en/tbs-en.elf"
OVERLAYS = "out/tbs-en/overlays"
