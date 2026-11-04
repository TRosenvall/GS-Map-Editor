# Overworld (world map) research: Golden Sun TBS, from alchemy sources

Source tree: `~/gs_project/alchemy` (read-only). Paths below are relative to
`games/tbs/` unless they start with `games/` or `tools/`. Tags: **[V]** = VERIFIED (read in code or data,
or confirmed by the prototype render), **[I]** = INFERRED.

Prototype scripts and renders (scratch, not part of this repo):
`(a scratch folder)`
(`render_world.py`, `render_area.py`, `render_gameplay.py`, `world_mixed.png`, `world_annotated.png`, `collision.png`, `terrain_kind.png`, `north_compare.png`).

## Summary

1. The whole overworld ground is one table: `src/map/world/blocks.tsv`, 320 rows x 512 columns of hex u32 **cell words**, built by `tools/ags-graphics` (form `blocks`) into `blocks.blocks`, which `src/map/map.s` incbins as `Field_PerspectiveDataA` [V].
2. The table holds 640 **chunks** of 16x16 cells (the code calls a chunk a "tile"). Chunks 0-319 are layer 0 (BG3, ground), 320-639 are layer 1 (BG2, overlay: mountains, trees, coast), with layer-1 chunk = layer-0 chunk + 320 [V].
3. The world is 16x16 chunks = 256x256 cells; one cell is 32 world pixels (16 screen/BG pixels), so the world is 8192x8192 world px and wraps [V]. Chunk ids 0-255 sit at world chunk (id%16, id//16); 256-319 are alternates swapped in by code [V].
4. A cell word: bits 0-15 block id, bits 16-23 step/event code, bits 24-30 terrain kind (encounter region; 21 = snow graphics set), bit 31 behaviour-bank flag [V].
5. A block id indexes `src/map/default/cells.tsv` (4386 blocks of 4 bytes: TL, TR, BL, BR 8x8 tile numbers) [V]. Tiles are 8bpp, 256 per layer: set A = `tiles_a+b` (layer 0) and `tiles_c+d` (layer 1), palette `palette_a.png` (224 colours); set B (snow) = `tiles_f..i`, `palette_b` [V].
6. Rendering is mode 2 (affine BG2+BG3) with per-scanline HBlank-DMA matrices for the "mode 7" perspective; a flat top-down render needs none of that. The prototype renders the full 4096x4096 BG-pixel map correctly [V].
7. Walkability is per 8x8 graphics tile, not per cell: `default/attributes.tsv` gives each tile a 4x4 grid of 4-bit collision values (upper layer wins over lower; 0 = none; default 7); 5-12 walkable [V].
8. Random encounters: terrain kind (cell bits 24-30) + terrain behaviour (from collision value, bank from bit 31 / kind 21) -> `gWorldMap_EncounterRules` (`src/object/zonedata.c`) -> zone row of `src/object/encounter.tsv` [V].
9. Towns/dungeons are placed actors (icon sprites) in `gWorldMapPlacements` (`src/scene/world_map.c`); touching actor N raises trigger 100+N, matched by an `EVENT_EXIT` in `gWorldMapEvents` -> exit number -> `gWorldMapExits` -> (scene, entrance). Some entrances are cell step codes (bits 16-23) instead [V]. Leaving a town uses that town's exit table `SCENE_EXIT(n, 2, e)` -> `gWorldMapEntrances[e]` position [V].
10. No per-edition variants of any world map data in TBS; ROM tail start addresses differ per edition, and any change breaks "compare OK" byte matching [V].

## Files and formats

| Data | Source file(s) | Format | Built as / wired by |
| --- | --- | --- | --- |
| Ground cells, both layers | `src/map/world/blocks.tsv` | No header. 320 lines x 512 tab-separated tokens; each token lowercase hex without `0x`, no leading zeros (`0`, `1b`, `9500014a`), LF line ends, final LF [V]. Read by `blocks()` in `tools/ags-graphics/tables.c:235-282`: lines must be a multiple of 16, all rows same width (multiple of 16) [V]. A 16x16 group may be all `-` (omitted, offset 0) but never partly [V; TBS has none, TLA has 969]. | `blocks.blocks`: 640 x u32 offset table, then each chunk's 256 u32 words (1024 bytes) packed separately with LZ kind `plz` (`tables.c:262-276`) [V]. `src/map/map.s:1-4` `.incbin` as `Field_PerspectiveDataA`, followed by `.byte 0x01 @ PACKER` [V]. Directory entry `group Field, PerspectiveDataA, ...` at `src/system/resource/directory.s:123` [V]. |
| Chunk numbering in the TSV | same | Chunk `i` occupies TSV rows `(i//32)*16..+15`, cols `(i%32)*16..+15` (chunks laid 32 wide, row-major) [V: `tables.c:257`]. This is NOT the world layout: world is 16 chunks wide, so one TSV chunk-row holds two world chunk-rows side by side [V by render]. | |
| Blocks (metatiles) | `src/map/default/cells.tsv` | Header `cell0:u8 ... cell15:u8`; values `0x6b`; 1097 rows, last row short (8 values) = 17544 bytes = 4386 blocks x 4 bytes [V]. Block b = bytes `4b..4b+3` = top-left, top-right, bottom-left, bottom-right tile number (u8) [V: `src/field/field/world_map.c:71-91`, `444-451`]. Shared by both layers; layer selects the tile bank. | `cells.table.lz`; `map.s:5-7` as `Field_DefaultMapCells` (+1 PACKER byte); decoded to `Ram_MapCellBuffer` (`gMapCellBuffer`, 0xc000 bytes, `src/system/ewram.s:223-226`) by `world_map.c:158-160` [V]. Same table is the "default cells" of layered maps too (README `src/map/README.md` row `default/`). |
| Tile collision | `src/map/default/attributes.tsv` | Header `attr0:u8..attr15:u8`; 256 rows = 4096 bytes [V]. Bytes 0x000-0x7ff: lower layer (BG3) tiles 0-255, 8 bytes each; 0x800-0xfff: upper layer (BG2) tiles 0-255 [V: `src/field/field/terrain.c:535-580`]. Per tile: 4 rows x 2 bytes; each byte holds two 4-bit values, low nibble = left; one value = 2x2 BG px (4x4 world px). | `attributes.table.lz`, `map.s:11-13` `Field_DefaultMetatileAttributes`; decoded to `Ram_MapCollision` (`world_map.c:161-163`) [V]. |
| Tile animation | `src/map/default/animation.tsv` | Header `word0:u16..word7:u16`, 465 halfwords; channel script (`0xfdNN` channel, groups source tile/count/dest tile/frames, `0xfeNN` jump, `0xfeff` stop, `0xffff` loop) [V: `src/field/field/map_animation.c:7-13`]. Source tiles >= 0x600 come from `gMapLayerData` (= `tiles_e`/`tiles_j`) [V: `map_animation.c:57-61`]. | `animation.table.lz`, `map.s:8-10`; decoded to `Ram_MapCollision+0x1000` and started (`world_map.c:149-152`) [V]. |
| Tile graphics | `src/graphics/world_map/tiles_{a..j}.png` | Indexed PNG, pixel value = raw 8bpp colour index, PNG palette = `palette_*.png` [V]. a-d, f-i: 128x64 (128 tiles each); e, j: 128x128 (256 tiles, animation source) [V]. | `tiles_X.8bpp.lz`, `src/graphics/world_map/worldmap.s` (each followed by PACKER bytes) [V]. Directory `directory.s:124-135` (`WorldMapPaletteA`, `WorldMapTilesA..J`) [V]. |
| Palettes | `palette_a.png`, `palette_b.png` | 16x14 indexed PNG = 224 colours [V]. Loaded to BG palette 0-223, colour 0 replaced by the current backdrop (`world_map.c:331-335`) [V]. | `.gbapal.plz` (`worldmap.s:4`, `:26`) [V]. |
| Graphics set table | `src/field/world_map_resources.c:11-28` | `gWorldMap_GraphicsResources[2][6]` = {palette, tiles x5} for set A (A..E) and set B (F..J) [V]. | C. |
| Encounter rules by terrain | `src/object/zonedata.c:7-15` | `gWorldMap_EncounterRules[132]` s16: 32 rules {kind, behavior (-1 any), flag (-1 none / rule off once set), zone} + terminator kind -1 [V]. | C. |
| Encounter zones | `src/object/encounter.tsv` | Header `rate:u16 level:u16 group0..7:u16 weight0..7:u8 zone` (last column is a label, not encoded); 104 zones [V]. | `encounter.table`, `src/object/arcspark.s:10-13` [V]. |
| Terrain behaviour | `src/field/mapdata.c:37-41` | `gWorldMap_TerrainBehaviorTable[48]` u8, index = collision value + bank (0x10 if cell bit 31, 0x20 if kind 21) [V]. | C. |
| Scene tables | `src/scene/world_map.c` | `gWorldMapEntrances` (`:2717`), `gWorldMapExits` (`:2802`), `gWorldMapPlacements` (`:2863`) + story variants (`:2966-3058`), `gWorldMapEvents` (`:3060`) [V]. Formats in `include/field_scene.h:54-150` [V]. | World map overlay 0x371 (`objects.tsv:640-644`), linked at 0x2008000, 32 KB limit (`src/scene/README.md` Limits) [V]. |
| Pause-screen map markers | `src/object/scripts.s:340-383` | `gWorldMap_PlaceMarkers`: pairs {tile<<16 \| flag, place name}; row i describes actor 11+i; 0-rows reserve an actor; -1 ends [V: `src/object/psynergy_effects/world_map.c:282-323`]. | asm `.4byte`. |
| Pause-screen picture | `src/graphics/world_map/picture.png` | 240x160 8bpp, covers world x 4096-8192, z 0-4096 [V: `psynergy_effects/world_map.c:10-11, 318-322`]. Hand-drawn, not generated from blocks [I]. | `src/graphics/title/title.s:68-71` `Field_WorldMapPicture` [V]. |
| Story frames | `src/graphics/world_map/story.png`, `storymap.tsv`, `storypal.png` | Story cut-in graphics in the world map overlay [V: `story.s`]. Not ground data. | `story.s`, overlay object `objects.tsv:643` [V]. |

Scene id of the world map: `scene WorldMap, 0x371, 0x02, 1, 0x01` is scene 2 (`src/field/scenes.s:17`); scene id = row index of `gField_SceneTable` (`scenes.s:1-5`) [V]. Its map index 1 equals `SceneId_Clear`, which is what selects perspective mode in `Field_RunScene` (`src/object/object/run_scene.c:45-49`) [V].

## Rendering

Hierarchy (TBS) [V]:

```
world (wraps)  16 x 16 chunks                      8192 x 8192 world px, 4096 x 4096 BG px
chunk          16 x 16 cells   (code: "tile")      512 world px, 256 BG px; 1 KB decoded
cell           u32 word, low 16 bits = block id    32 world px, 16 BG px
block          2 x 2 tiles (4 bytes in cells.tsv)  
tile           8 x 8, 8bpp, from bank per layer    16 world px, 8 BG px
```

- **Display**: `Map_InitializePerspectiveScene` (`world_map.c:112-264`) sets BG3 = char base 2, screen base 8; BG2 = char base 3, screen base 10; both 512x512 px affine, wrapping (`:164-174`); BG1 text layer for the still view; `DISPCNT_MODE_2` (`:249`) [V]. BG2 is drawn over BG3, colour 0 transparent (`view.c:66-69` comment: BG2 falls back to BG3 where transparent) [V].
- **Tile banks**: set's tiles[1] (A) -> char block 2, tiles[2] (B) -> block 2 + 0x2000, tiles[3] (C) -> char block 3, tiles[4] (D) -> block 3 + 0x2000, tiles[5] (E) -> `gMapLayerData` (`world_map.c:336-352`) [V]. So layer 0 tile numbers 0-127 = `tiles_a`, 128-255 = `tiles_b`; layer 1: `tiles_c`, `tiles_d` [V by render].
- **Streaming**: the BG maps hold a 2x2-chunk window around the player. `perspective->tileIds[256]` maps each world chunk slot to a chunk id, initialised to identity (`world_map.c:262-263`). `Map_WriteLayerCellTile` LZ-decodes chunk `id` (layer 1 uses `id + 320`, `:298`, `:640`) into `Ram_MapBlocks` quarter `(x&1, y&1)` and writes the affine map bytes from the block table (`:38-95`) [V]. Window index uses `& 15`, hence the world wraps every 16 chunks [V].
- **Perspective**: `WorldMap_BuildScanlineTable` (`src/field/field/view.c`) + ARM routine `Transform_UpdateVertices` build one affine pair (BG2/BG3 PA..Y) per scanline; `MapAnimation_ApplyAffineFrame` loads line 0 and HBlank-DMAs the rest (`world_map.c:386-441`) [V]. Default pitch 0xe000 (-1/8 turn), far plane 0x1fe0000, centre (120,96) (`:198-249`) [V]. A top-down editor view ignores all of this.
- **Graphics set B**: `WorldMap_LoadGraphics(x,z)` picks set B if the layer-0 cell under the party has kind 21, at scene load only (`world_map.c:323-329`, called from `run_scene.c:76-78`) [V]. With set B it also points chunk slots 10-12 and 26-28 at alternate chunks 0x10a-0x10c, 0x11a-0x11c (`:366-374`) [V]. Render confirms set B is the snowy north (Imil area); in set A those slots show a white placeholder [V: `north_compare.png`].
- **Story chunk swap**: `FieldMap_SetWindowCellTile(128, 256, 176, 56)` (`src/scene/world_map.c:534`) puts chunk 264 in slot 59 (world chunk (11,3)) while `FLAG_LAMAKAN_SAND_MONSTER_BEATEN` is clear; arithmetic in `world_map.c:271-300` [V]. Visually 264 vs 59 differ by a bridge [V render; meaning I]. It is the only call (grep) [V]. 57 of the 64 alternate chunks (256-319, and their layer-1 twins) are not referenced by TBS code [I: grep found no other users; all 64 are non-empty and distinct from 0-255].
- **Animation**: tile animation channels copy from `gMapLayerData` (tiles E/J) into VRAM; irrelevant for a static render [V].

Top-down render algorithm (implemented in `render_world.py`, 7 s in pure Python) [V]:

```
for layer L in (0,1), world chunk (cx,cy) in 16x16:
    c = cy*16 + cx + 320*L                         # use tileIds overrides for set B / story swaps
    for cell (x,y) in 16x16: word = tsv[(c//32)*16 + y][(c%32)*16 + x]
        b = word & 0xffff; t[0..3] = cells_bytes[4b..4b+3]
        draw tile t[k] from bank L at BG px ((cx*16+x)*16 + (k&1)*8, (cy*16+y)*16 + (k>>1)*8)
        (layer 1: skip pixel value 0)
palette: palette_a.png (or palette_b.png for kind-21 cells / set B)
```

Result: `world_mixed.png` (set A, kind-21 cells drawn with set B) shows Angara and Gondowan in the top-right quadrant (chunks x 8-15, y 0-7), the rest ocean; flat filler land at the continent's west edge; three islets [V]. Overlaying `gWorldMapEntrances` and placement positions at world/2 lands Vale's icon (actor 11 at 5678,1200), entrances 0-2 just south of it, and step code 90 (Flint) beside it [V: `world_annotated_zoom.png`].

## Gameplay data

### Cell word (layer 0) [V]

| Bits | Meaning | Evidence |
| --- | --- | --- |
| 0-15 | block id into `cells.tsv` (full 16 bits, no 12-bit mask on the world map) | `world_map.c:82-86, 445` |
| 16-23 | step code (`struct MapCell.collisionCode`): 1-239 scene step events, 240-241 encounter ground, 252-254 warps, 0xff wall (layered-map meaning) | `include/map.h:13-22`, `src/object/object/step.c:20-25, 231-245` |
| 24-30 | terrain kind = encounter region (0 none, 1-6, 21, 31 used) | `terrain.c:619-624`, `zonedata.c` |
| 31 | selects behaviour bank 0x10 | `terrain.c:615-617` |

Layer-1 cells use only bits 0-15; all their upper bits are 0 in the data [V: stats]. Only layer 0's upper bits are read (code indexes `Ram_MapBlocks` rows 0-31, which is layer 0) [V]. Code comment `struct WorldMapCell {tile:24, kind:7, flag:1}` (`world_map.c:17-23`) lumps the step code into "tile"; the readers use bytes separately [V].

Value census (layer 0, all 320 chunks): kinds 0 74215, 1 915, 2 1542, 3 1001, 4 771, 5 494, 6 1304, 21 1334, 31 156; bit 31 set on 188 cells; step codes present: 13, 15, 18, 28, 29, 32, 42, 47, 50, 51, 55, 61, 74, 75, 90, 91, 92, 93, 95, 96, 100 [V].

### Walkability / terrain [V]

- `GetWorldMapCollision` (`terrain.c:535-580`): take the BG map byte (the 8x8 tile number) in screen block 10 (upper layer) at the position, look up its nibble in `Ram_MapCollision + 0x800`; if 0, same for screen block 8 (lower) at `Ram_MapCollision`; if still 0, return 7. Nibble = `((y>>1)&3)` row, `((x>>2)&1)` byte, `(x>>1)&1` selects high nibble, in 2-world-px units.
- `CheckWorldMapWalkable` (`terrain.c:586-592`): walkable iff value 5..12.
- Behaviour = `gWorldMap_TerrainBehaviorTable[bank + value]` (`mapdata.c:37-41`): bank 0: 5->1, 6->7, 7/8/10-13->1, 9->2; bank 0x10 (bit 31): 5->4, 9->6; bank 0x20 (kind 21): 5-13->5 except 9->6. Behaviour also picks the battle backdrop (`encounter.c:118`, `Battle_SelectTerrainBackdrop` `encounter.c:404-429`): 1 grassland, 2 forest, 3 desert, 4 and 7 beach, 5 and 6 snowfield, other Sol Sanctum [V].
- Census of the composed collision map: values 1-4, 14, 15 (blocked; water/mountain/cliff) and 5-10 (walkable) occur; 9 = forest (behaviour 2) per encounter labels [V data; "forest" label from `encounter.tsv`].
- Height: none on the world map (cells have no shape byte; actors placed with y=0 and no terrain height, `src/object/object/actors.c:143-158`) [V].

### Random encounters [V]

Per step on the world map: `Field_ProcessStep` -> `Encounter_RollWorldMap(&leader->x, speed)` (`step.c:261-263`) -> `Encounter_ResolveWorldMapZoneAndBackdrop` (`encounter.c:103-120`): first rule in `gWorldMap_EncounterRules` with matching kind, behaviour (or -1) and flag clear gives the zone; then `Encounter_SelectEnemyGroup` (`encounter.c:130-218`) uses `encounter.tsv` row: rate (+5 per party level above `level`, max 5), bias, 8 weighted groups (rows of `src/battle/formatn.tsv`). Field scenes' rules (`src/object/location_rules.s`) are not used on the world map (`Encounter_SelectSceneZones(0)`, `run_scene.c:49`).

Rules (kind: behaviour -> zone): 1: 4,7,1->7, 2->8; 2: 4,7,1->13, 2->14; 21: 5->29, 6->30; 31: 1->37, 2->38; 3: 3,4,7,1->45, 2->46; 4: ...->54, 2->55; 5: ...->64, 2->65; 6: ...->80, 2->81. Zones labelled in `encounter.tsv` ("World map: terrain kind 1, grassland and beach", ...). Behaviour 3 (desert) is listed in rules but the behaviour table never produces it, so on the TBS world map desert ground counts as grassland/beach [V table read; gameplay effect I]. Djinni battles: zones 100-103 via `gEncounter_AreaEntryTable` (`zonedata.c:19-29`).

`terrain_kind.png` shows coherent regions (kind 1 around Vale, 2 Bilibin, 21 north snow, ...) [V render; place names I].

### Entering towns/dungeons [V]

Two mechanisms, both ending in `gWorldMapEvents` (`src/scene/world_map.c:3060-3125`):

1. **Location icons (most towns)**: rows of `gWorldMapPlacements` (`:2863-2964`) are actors 8, 9, ... in row order; a row whose condition fails still consumes its slot (`actors.c:103-108`). `WorldMap_UpdateLocationContacts` (`world_map.c:416-466`) sets `touchedTrigger = actor + 100` when the leader's |dx|+|dz| < sum of scaled radii (and `FLAG_CONTACT_BLOCKED` 0x104 clear). An event `{ EVENT_EXIT, 100+actor, cond, exitNo }` maps it to an exit; e.g. row 3 (actor 11, sprite 0x105 at 5678,1200) -> trigger 111 -> exit 1 -> `SCENE_EXIT(1, 5, 10)` = scene 5 (Vale village) entrance 10. Some triggers run scripts instead (passages 116/125/130/150/151 choose an exit by approach side, `:367-410`).
2. **Step codes in the map**: cell bits 16-23 = code; `{ EVENT_EXIT, code, cond, exitNo }` (codes 13, 15, 18, 28, 29, 32, 42, 47, 50, 51, 55, 61, 75) or `EVENT_TOUCH`/`SEARCH` scripts (90-96 Djinn, travel, shipwreck; 100 Turtle Boots search; 112 transfer route; 74 east edge).

Exit encoding `SCENE_EXIT(exit, scene, entrance) = exit<<20 | entrance<<12 | scene`, flagged form adds 0x10000000 and a flag word; table starts `SCENE_EXITS(own scene)` and ends 0x1ff (`include/field_scene.h:72-77`).

### Leaving towns [V]

The town's own exit table names scene 2: e.g. `gValeHome_Exits` `SCENE_EXIT(10, 2, 1)` (`src/scene/vale_home.c:1903`); Bilibin `SCENE_EXIT(1, 2, 5)` (`bilibin.c:805`). Entrance `e` is a row of `gWorldMapEntrances` (`struct SceneEntrance`, 24 bytes: entrance, requiredFlag, x, y, z (s16 pixels), facing, unused, camera L/T/R/B, unused; `field_scene.h:54-67`). Entrance 1 = (5680, 0, 1226) facing south, just below Vale's icon. Special entrances (33, 49, 64-80, 90, 91, 99) also choose placement tables and cutscenes (`world_map.c:308-342`, `496-560`).

## Limits and constraints

- Chunk count and layout are fixed by code: 640 chunks, layer offset 320 (`0x140`, `world_map.c:298, 640`), 16x16 slot grid (`& 15`), alternates at fixed ids 0x10a-0x10c, 0x11a-0x11c, 264 [V]. Keep `blocks.tsv` at exactly 320x512.
- Each chunk decodes to 1024 bytes into a 0x400 heap block (`world_map.c:56-57`) [V].
- Tiles: 256 per layer (affine map entries are bytes) [V]; 224 palette colours, index 0 forced to backdrop [V]. Tile E/J banks (256 tiles) feed animation [V].
- Blocks: block id is 16-bit in the cell, but `cells.tsv` decodes into `gMapCellBuffer` (0xc000 bytes, `ewram.s:225`) -> at most 12288 blocks [I]; the same buffer holds the 240x160 still-view picture during events (`world_map.c:711-712`) and is reloaded after (`:766-767`) [V].
- Collision table 4096 bytes fixed (2 x 256 tiles x 8) [V]; animation script must fit after it in `gMapCollision` (0x4000 total, starts at +0x1000) [I].
- Placements: actor slots 8..65 (`actors.c:98`, `CONTACT_LAST_ACTOR = 65`); location triggers 108..165 must not collide with step codes used for other events [V/I]. `gWorldMap_PlaceMarkers` row i must stay aligned with actor 11+i [V].
- World map overlay (code + tables + story graphics) must fit 32 KB at 0x2008000 [V: scene README]. Entrance coordinates are s16 [V].
- Compression: every chunk is `plz` LZ (`tools/common/lz.c`, `LZ_PALETTE_UNTAGGED`, machine `{4123, 485, 4126, 272}`); cells/attributes/animation `.table.lz`, tiles `.8bpp.lz`, palettes `.gbapal.plz` [V]. The build re-encodes from TSV/PNG, so an editor only writes sources; never hand-write `.blocks`/`.lz`.
- Byte matching: unchanged sources reproduce the original ROM (PACKER literal bytes and `_patch.tsv` mechanism, `src/map/README.md` "How the build encodes a map"); any edit makes that edition differ, i.e. `make compare-editions` fails by design [V]. The trailing `PACKER:` bytes in `map.s`/`worldmap.s` are harmless stale data after an edit [I].
- ROM layout: `rom_tail_02` (which holds `map.s`, `objects.tsv:443`) starts at a fixed per-edition address (`main.ld:122-126`) and is the last region; growth shifts only later data; TBS cartridge end 0x08800000 (`Makefile` `ROM_END_tbs`) [V]; exceeding it is not checked by me [I].
- Editions: no `_ja/_de/...` variants or `.ifdef TBS_EDITION_*` in `map/world`, `map/default`, `graphics/world_map`, `zonedata.c`, `mapdata.c`, `world_map_resources.c` [V grep]. `scene/world_map.c` only has `TBS_PATCH_3` code differences (`:1657-1666`) [V]. Place names / messages are per-language PO catalogs (`games/tbs/text/*.po`) [V scene README].

### TLA differences (brief)

- `games/tla/src/map/world/blocks.tsv` is 1024 rows x 512 = 2048 chunks; layer-1 offset 0x400 (`games/tla/src/field/common/map/perspective.c:42`) and a 32x32 chunk window (`tiles[32][32]`, `:8`) -> world 32x32 chunks (16384 world px) [V]. 969 chunks are omitted (`-`) [V].
- Placed by `games/tla/src/map/world/blocks.s` (own file, `.balign 4, 0`) [V].
- Four graphics sets A-D, each palette + 6 tile sheets (`tiles_a1..d6.png`), plus per-set animation/attribute tables (`anim_b/d.tsv`, `attr_b/c/d.tsv`) in `games/tla/src/graphics/world_map/`; directory `games/tla/src/system/resource/directory.s:420-458` [V]. `cells.tsv` is larger (2745 rows) [V].
- Most TLA world-map engine code is still assembly (`object_dispatch_5.s`); kind/flag semantics are assumed shared [I].

## Unknowns

Marked by alchemy:
- XXX `world_map.c:569`: `WorldMap_UpdateView` reads the followed position without a NULL check.
- XXX `world_map.c:778`: whether `Map_LoadDefaultCellsAndUpdateBlock` leaving `animationActive` set is intended.
- XXX `src/scene/world_map.c:500-504`: flags 0x161 and 0x85c (set by entrances 99 and 1) are read by no TBS code.
- XXX `actors.c:101-102`: the 0x2705 sprite cutoff in placement spawning.
- Encounter flags 351/353 unnamed (`encounter.c:148-152`); "flag 5 / unit 5 experience > 130" rule.
- Layered-map XXX (placeholder block 0xfff, header pad bytes) do not apply: the world map uses no 12-bit mask [V].

Not resolved by this research:
- Designer intent of cell bit 31: mechanically it turns collision 5 into behaviour 4 (beach backdrop) and 9 into 6 (snowfield backdrop) [V]; why those 188 cells carry it is not known [I].
- Why collision value 6 maps to behaviour 7 (a second beach id) [I].
- Purpose of the 57 alternate chunks no TBS code references (leftovers or TLA-era) [I].
- Exact meaning of each collision value 1-4, 14, 15 (water vs mountain vs cliff) and of 6, 8, 10 [I].
- Whether `picture.png` (pause map) was derived from the ground data; an editor changing coastlines must redraw it manually [I].
- Which scene/entrance each `EVENT_EXIT` reaches in human terms requires joining `gField_SceneTable` names (some scene names in alchemy are known to be off, e.g. scene 5 `ValeHome` is Vale's village) [V for the example].

## Proposed editor data model

Python layer, all I/O on alchemy source files only. Keep original text formatting for diff-friendliness.

| Entity | Fields | File (read/write) | Round-trip notes |
| --- | --- | --- | --- |
| `WorldGrid` | `chunks[640][16][16]: u32` plus derived views `cell(layer, gx, gy)` via slot map; `slot_map[256] = identity` | `src/map/world/blocks.tsv` | Write exactly 320x512 tokens, `format(v, 'x')` (lowercase, no padding, `0` for zero), tab separators, `\n` line ends + final `\n`. Never emit `-` in TBS. Byte-identical rewrite of an unmodified file must be a test. |
| `Cell` | `block: u16`, `step_code: u8`, `kind: u7`, `bank_flag: bool` (layer 0); layer 1 only `block` | packed in `WorldGrid` | Preserve layer-1 upper bits (all 0) and any unknown bits verbatim. |
| `Alternates` | `set_b_swaps {10:0x10a, 11:0x10b, 12:0x10c, 26:0x11a, 27:0x11b, 28:0x11c}`, `story_swaps {59:264}` | constants from `world_map.c:366-372`, `scene/world_map.c:534` (read-only) | Editor should edit alternates alongside their base chunks and show both views. |
| `BlockTable` | `blocks[4386][4]: u8` | `src/map/default/cells.tsv` | Header line kept; 16 values a row, `0x%02x`, final short row allowed. Shared with layered maps: editing a block changes every map that uses default cells; prefer appending new blocks. |
| `TileCollision` | `lower[256][4][4]`, `upper[256][4][4]` nibbles | `src/map/default/attributes.tsv` | 16 bytes a row, `0x%02x`, header kept. Also shared with layered maps' default data [I]. |
| `Tileset` | per set: palette (224 RGB), banks L0 (A+B), L1 (C+D), anim bank (E/J) | `src/graphics/world_map/*.png` | Keep PNG mode P, exact sizes, and palette identical to `palette_*.png` (index = colour). Rewriting PNGs is fine for the build if indices are preserved; check pixel-identical rather than file-identical. |
| `Animation` | channel scripts (u16 list) | `src/map/default/animation.tsv` | Treat as opaque words initially. |
| `Entrance` | `id, required_flag, x, y, z, facing, camera[4]` | `gWorldMapEntrances` in `src/scene/world_map.c:2717-2800` | C source: parse/regenerate only the initializer block between known markers; keep `CONDITION_ALWAYS`, `FACING_*` names. |
| `Exit` | `exit_no, scene, entrance, flag?` | `gWorldMapExits` (`:2802-2839`) and towns' `*_Exits` | Same; keep macro form `SCENE_EXIT(...)`. |
| `Placement` (location icon) | `row/actor, sprite, condition, behavior, x, z, facing, talk, flags` | `gWorldMapPlacements` (`:2863-2964`) | Actor number = 8 + row; inserting/removing rows renumbers triggers (100+actor) and `gWorldMap_PlaceMarkers` alignment (actor 11+i). Prefer editing in place. |
| `Event` | `kind/control, trigger, condition, value` | `gWorldMapEvents` (`:3060-3125`) | Exits: `{ EVENT_EXIT, trigger, cond, exit_no }`; scripts reference C functions (read-only in editor). |
| `EncounterRule` | `kind, behavior, flag, zone` | `src/object/zonedata.c:7-15` | 132 s16 incl. terminator; array size literal must be updated if rules are added. |
| `EncounterZone` | `rate, level, groups[8], weights[8], label` | `src/object/encounter.tsv` | Table form; 104 rows fixed by references (zone ids in code/rules). |
| `PlaceMarker` | `tile, flag, name_id` per actor 11+i | `src/object/scripts.s:340-383` | asm `.4byte` lines. |

Recommended editor views: (1) top-down composite with per-cell set choice (kind 21 -> set B), (2) collision overlay from `TileCollision` via the cells' tile numbers (upper then lower then 7), (3) kind and step-code overlays, (4) entrances/placements at world/2. Coordinate helpers: world px = BG px x 2; cell = world // 32; chunk slot = cell // 16; TSV (row, col) for layer L = `((c//32)*16 + gy%16, (c%32)*16 + gx%16)` with `c = slot_map[(gy//16)*16 + gx//16] + 320*L`.
