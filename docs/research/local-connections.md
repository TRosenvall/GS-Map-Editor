# Local maps: how they connect and how they are populated (TBS, with TLA notes)

Source tree: `alchemy/` (read-only). Paths below are relative to `alchemy/games/tbs/` unless they start with `games/`, `tools/` or `out/`. "VERIFIED" = read in code/data, or checked by a script over all files; "INFERRED" = deduced, not proven.

## Summary

1. A **scene** is a row of `gField_SceneTable` (`src/field/scenes.s`): overlay resource id, group, variant, **layered-map row**. The scene id is the row index. 201 rows. (VERIFIED)
2. The map row indexes `gMap_LayeredScenes` (`src/field/layered.tsv`, 186 rows). Each row holds 6 resource offsets from `ResourceId_Map001`: map header, palette, 3 tile sheets, layer data. So the scene table picks the map **and** the tileset together, and the row number is **not** the `map_NNN` number. (VERIFIED)
3. Each overlay's code (`scene/<place>.c`) returns five tables through six entry veneers: Entrances, Exits, Placements, Events, Regions, plus Initialize. Getters may pick between tables by flag or scene id. (VERIFIED)
4. **Exits work through events.** A cell's collision code (1..239) matches an `EVENT_EXIT` event (value = exit kind), a touch-event script calls `Engine_EventRequestExit(kind)`, or a region box applies. The exit table then maps (current scene, kind) to (scene, entrance). (VERIFIED)
5. On arrival, the first `SceneEntrance` row whose `entrance` matches and whose flag is set (or -1) places the party and clamps the camera. If no row matches, row 0 is used. (VERIFIED)
6. **Markers** (`markers.tsv`: x, z, id) are chest and Psynergy-stone positions. The id equals the cell's collision code in all 417 markers. What a marker holds comes from the scene's `SEARCH` event with that trigger. (VERIFIED)
7. **NPCs** are `ScenePlacement` rows. Actor number = 8 + row index, whether or not the row's condition holds (the scene README says otherwise). Positions are 16.16. 396 of 2,321 rows are at (0,0) and get positioned by code; there are 405 inline `Engine_ActorSetPosition` calls. (VERIFIED)
8. Every connection table is a plain file-scope C initializer made of literals and macros. All of them can be rewritten if the tool edits in place, keeping `#if` blocks, symbolic names and `const`. Scene ids in exit words are **numeric literals**. In code they are `(s32)&SceneId_X` linker symbols. (VERIFIED)
9. TLA keeps per-map entrances, points and camera bounds in a 7th map block (`scene_*.tsv`). Its overlays mostly carry a one-row `SceneEntrance`. That is an engine difference, so TBS cannot move to the same files. (VERIFIED layout, INFERRED semantics)
10. To add a new map or scene, take the 25 `unused` directory slots and append rows to the scene and layered tables. Fixed bank addresses and **~3.5–43 KB of ROM headroom per edition** (8 MB pad) are the hard limits. (VERIFIED)

---

## 1. Scene ↔ map wiring

### 1.1 Scene table (VERIFIED)

`src/field/scenes.s:1-9`:

```
.macro scene name, code, area, kind, map
  .equiv SceneId_\name, (. - gField_SceneTable) / 8   ; id = row index
  .2byte \code   ; overlay resource id (= directory index, 0x36f..0x3ce)
  .byte \area, \kind  ; group, variant
  .2byte \map, 0      ; gMap_LayeredScenes row, reserved
```

- `struct SceneRecord` is at `include/field_runtime.h:18-26`: `resourceId, group, variant, mapIndex, reserved`, 8 bytes.
- The table has 201 rows (script count). Unnamed rows (`scene , 0x376, ...`) get no `SceneId_` symbol.
- `Game_ResetForNewGame` (`src/object/object/scene.c:204-289`) does `record = &table[gGameState.scene]`, then `gGameState.map = record->mapIndex` (`:286`), then `Scene_LoadOverlay` → `Resource_LoadCode(table[scene].resourceId, &gOverlayArea)` (`:294-298`), then `Scene_TakeExit(Field_RunScene(entrance))` (`:288`).
- `group` is used for:
  - music rules and area-name rules (`src/object/scene_rules.s`, read by `Scene_ResolveInteractionResult` and `Scene_GetAreaNameIndex` in `src/object/object/encounter.c:279-345`);
  - clearing flags 0x300-0x3ff on a group change;
  - the "visited" flag `(group & 0x7f) + 0x180` (`scene.c:344`), so a group must be ≤ 0x7f.
- `variant` 2 marks towns. It turns off walking-distance PP regen and blocks Retreat (`src/object/object/run_scene.c`, `sceneVariant == 2`).
- Several scenes can share one overlay, for example Bilibin1/2/3 = 0x38b and AltinPeak1..11 = 0x3a4. They also share one `.c` file.
- **Scene ids in C code are linker symbols.** `scene_ids.h` declares `extern char SceneId_X;` and code compares `gGameState.scene == (s32)&SceneId_X`, which loads from a literal-pool word. There are 487 such uses in `src/scene/*.c`.
- Run_scene compares `gGameState.map == (s32)&SceneId_Clear`, which is 1, to detect the world map (`run_scene.c:45`). (VERIFIED)
- **Scene ids in data tables** (exit words) are plain integers or the few `enum SceneId` names in `include/field_scene.h:13-24`. They are not symbols, so they do **not** follow a renumbering. (VERIFIED)

### 1.2 Map selection: layered table (VERIFIED)

`src/field/layered.s` does `.incbin "layered.table"`, built from `src/field/layered.tsv`. Its columns are `map0..map5:u16` and it has 186 rows. The object is placed in `rom_main_01` (objects.tsv:59).

`struct LayeredSceneEntry { u16 resources[6]; }` is at `src/field/field/map_layers.c:164`. `Map_LoadLayeredScene(index)` (`:211`) uses the six resources like this:

| Column | Resource | How it is used |
|---|---|---|
| [0] | map header | `Resource_GetTableEntry(resources[0] + ResourceId_Map001)` (`:233`) |
| [1] | palette | decoded; colour 0 (the backdrop) is kept (`:337`) |
| [2] | tile sheet | char block 1 (`:345-357`) |
| [3] | tile sheet | char block 2 |
| [4] | tile sheet | char block 3 |
| [5] | layer data | decoded to `gMapLayerData` |

All values are offsets from `ResourceId_Map001`. Expanding the directory macros resolves them by name (scratch script):

- rows 0 and 1 are `Field_Map001` + `Blank*`. Title, Clear and WorldMap use them; the world map path never loads them.
- row 2 is `Field_Map000` + `Set00{Palette,TilesA-D}`;
- row 5 is `Field_Map004` + `Set03*`;
- row 12 is `Field_Map010` + Set09 palette/A/B/C + **Set08TilesD**.

123 of 186 rows are not six consecutive resources: a row can mix sheets from different sets, and recolours reuse sheets. So the editor must treat the row as six independent references.

`map_NNN/` is named after `Field_MapNNN` (the directory's numbering, `src/map/README.md` "The map numbers are the directory's"). For example, scene ValeHome (id 5) has mapIndex 4 → `Field_Map003` = `src/map/map_003/`. That map's `markers.tsv` (13,44,100) matches ValeHome's `SEARCH(...)` event with trigger 100 (`src/scene/vale_home.c`, events). See the Appendix for all 201 scenes.

Two maps carry place names instead of numbers: `gondowan_passage/` (`Field_GondowanPassage`) and `venus_entrance/` (`Field_VenusEntrance`). Of 182 distinct map resources referenced, 8 are used by more than one scene.

### 1.3 Resource directory (VERIFIED)

`src/system/resource/directory.s` holds the macros `resource`, `group`, `area SET, sheets, maps...`, `recolor`, `overlays`, `unused` (`:1-51`).

- An entry's id is its **position**: `ResourceId_X = (. - Resource_DirectoryTable)/4`.
- `area SetNN, ABCD, mmm` emits `Field_Mapmmm`, then `Tileset_SetNNPalette`, then `TilesA..D`.
- The overlays come last, `overlays 36F … 3CE` (96 entries, `:299-306`), followed by `unused 25` (`:307`). Each unused slot is `.4byte 0`.
- `Resource_GetTableEntry(i)` is just `Resource_DirectoryTable[i]` with no bounds check (`src/runtime/runtime/system.c:150-152`).
- The directory sits at the start of `rom_tail_02`, which is **pinned** at 0x08320000 in EN (`main.ld`, last `ABSOLUTE`; `out/tbs-en/tbs-en.map:7353`).
- Map data (`map_NNN/map.s`, which also carries the tileset sheets it owns), then `src/system/overlay/overlays` follow in `rom_tail_02` order (objects.tsv:436-631).
- Inserting a directory entry before the overlays renumbers every later resource. That breaks the overlay ids in scenes.s (`0x36f`…) and every `layered.tsv` offset after the insertion point. Use the `unused` slots: indices 0x3cf..0x3e7. (INFERRED from the positional macro; the arithmetic is VERIFIED.)

### 1.4 Overlays: entry, import, objects.tsv, overlays.tsv, linker (VERIFIED)

`src/scene/README.md` and `src/system/overlay/overlay.ld` describe the overlays.

- **Entry** (`scene/entry/<place>.s`) is six `overlay_veneer` lines in a fixed order: Initialize, GetEntrances, GetExits, GetPlacements, GetEvents, GetRegions. Each veneer is `ldr r4; bx r4; .4byte target` (`src/system/overlay.s:5-11`). The engine reads them as `struct SceneEntries` (`include/field_runtime.h:42-57`): a veneer word plus a function pointer each, 48 bytes. It calls `gOverlayArea.entrances()` and so on.
- **Import** (`scene/import/<place>.s`) is `.set overlay_imports,1`, then `.set import.NAME,1` for each engine routine the C calls, then `.include overlay.inc`. `overlay.inc` holds the master ordered list of ~405 `import NAME, TARGET` rows. Only the rows that are set emit a stub (`src/system/overlay.inc:9-25`). Overlays cannot call each other.
- **objects.tsv** gives each overlay three `text` rows in order (`entry/<place>`, `<place>`, `import/<place>`) with the first column = overlay id in hex (e.g. `374 text games/tbs/src/scene/vale_home`). An optional `bss` row may follow (`.bss COMMON`, or `resource_<id>_overlay .bss` from `src/system/overlay/ovl_<id>.s`).
- **overlays.tsv** gives the `.bss` output-section header (e.g. `.bss ALIGN(16)`) for the 36 overlays that have bss rows. `tools/ags-objects/ags-objects.c:165-205` fails with "bss header and rows disagree" if exactly one of the two exists.
- **Linking.**
  - Each overlay links at 0x2008000 against `symbols.elf` (Makefile:209-219).
  - Inside an overlay all `.text` comes first, then all `.rodata`, then all `.data`, in object order (`ags-objects.c` `render()` passes). So `const` tables go in `.rodata` and non-const ones in `.data`.
  - The image is packed by `tools/ags-overlays` into `resource_<id>.lz` and embedded by `src/system/overlay/overlays.s` (`Resource_Overlay36F: .incbin ...` plus per-edition `PACKER:` residue bytes).
  - `Resource_LoadCode` decodes it to `gOverlayArea` and patches Thumb BLs (`system.c:228`).
- The overlay area is 32 KB, and code + rodata + data + bss must fit. Measured from `out/tbs-en/overlays/*.map`, the largest are 0x3b1 at 32,648 B (120 B free), 0x373 Vale at 30,764 and 0x3c8 at 30,732. (VERIFIED from build output.)

### 1.5 Other scene-keyed tables (VERIFIED)

These use `SceneId_` symbols or the group, so they stay correct when appending:

- `src/object/scene_rules.s`:
  - `gScene_InteractionRuleTable` (music: `scene_cue` / `group_cue`);
  - `gScene_AreaNameRules` (`scene_name` / `group_name`);
  - `gParty_PairResolveRules` (`return_to`, defeat return points);
  - `gBattle_BackdropScenes`.
- `src/object/location_rules.s` `gBattle_LocationRules`: encounter zones per (scene, entrance, flag).
- `src/scene/world_map.c` `gWorldMapExits` (`SCENE_EXITS(2)`…) and its `EVENT_EXIT` events (44): how the world map enters local scenes.

---

## 2. Exits and entrances

### 2.1 `struct SceneEntrance` (24 bytes, `include/field_scene.h:54-70`) (VERIFIED)

| # | Field | Type | Meaning |
|---|---|---|---|
| 1 | entrance | s16 | the entrance number the exit word names; -1 ends the table |
| 2 | requiredFlag | s16 | -1, or a flag that must be **set** (plain `GameFlag_TestFar`, no 0x1000 encoding) |
| 3 | x | s16 | pixels |
| 4 | y | s16 | pixels (height; non-zero in 20/1520 rows) |
| 5 | z | s16 | pixels (map "down") |
| 6 | facing | u16 | 1/65536 turn (`enum Facing`, 0x2000 steps) |
| 7 | unused1 | s16 | 0 everywhere, not read |
| 8 | cameraLeft | s16 | pixels, -1 = keep the map header bound |
| 9 | cameraTop | s16 | likewise |
| 10 | cameraRight | s16 | likewise |
| 11 | cameraBottom | s16 | likewise |
| 12 | unused2 | s16 | 0 everywhere, not read |

`Scene_ApplyEntrance` (`src/object/object/run_scene.c:461-505`):

1. Scans for `entrance == gGameState.entrance && (flag == -1 || flag set)`. If nothing matches, it uses **row 0**.
2. Unless `FLAG_KEEP_PARTY_POSITION`, it writes `gGameState.x/y/z = value << 16` and `heading = facing`.
3. Clamps the camera bounds, with a minimum 240×160 view.

Stats over 189 tables / 1,520 rows:

- 3 rows use a flag;
- 1,023 set camera bounds;
- both unused fields are 0 everywhere;
- the entrance column is a symbolic constant in 21 rows.

### 2.2 How an exit fires (VERIFIED)

There are three ways to leave a scene:

1. **Exit cell.** `Field_ProcessStep` reads the leader's cell collision code (`src/object/object/step.c:240-249`).
   - Codes `1..239` (`STEP_EVENT_FIRST/LAST`, `:19-27`) set `work->action = code`.
   - `Scene_RunTouchOrExit(code)` (`src/object/object/events.c:333-385`) first looks for an `EVENT_TOUCH` event with `trigger == code`. If one exists, it runs its message or script, and the script gets the code as its argument.
   - Otherwise it looks for `EVENT_EXIT` with `trigger == code`: it plays the exit sound (bits 5..4 of control: 0 normal, 0x20 → SE_128 + effect 26, 0x30 → SE_129 + effect 25, 0x10 none) and sets `work->exit = event.value`, the **exit kind**.
2. **Script.** A touch/talk/Psynergy script calls `Engine_EventRequestExit(kind)`. That is imported as `Event_SetExitRequestFar` (`src/system/overlay.inc:321`). There are about 200 call sites. Typical doors use `TOUCH_WALKING_INTO(FACING_NORTH)` on the door's collision code, animate the door cells, walk the leader in, then request the exit (`vale_home.c:444-471`). Door animation coordinates are **inline call arguments** (`Event_OpenDoorAndWalkThrough(44, 7, 248, 279)`, `Map_CopyCellsTo(...)`) or `u16 ...DoorCells[]` `MAP_CELL_STEP(srcX,srcY,w,h,frames)` arrays (`include/field_event.h:59-61`).
3. **Region.**
   - `struct SceneRegion` (`include/field_runtime.h:30-37`, 16 B) is `minX,minY,minZ,maxX,maxY,maxZ` (pixels; min inclusive, max exclusive), `condition`, and `value` = exit kind. minX -1 ends the table.
   - It is checked by `Field_CheckExitRegions` (`step.c:135-186`) whenever the leader's cell code is non-zero.
   - There are 14 region tables, 38 rows; most scenes return NULL.

`Field_RunScene` returns `work->exit`. `Scene_TakeExit(kind)` (`src/object/object/scene.c:25-89`) then:

- walks the overlay's exit table for the header word equal to the current scene id;
- takes the first exit word whose `kind == exitKind` or whose kind is `0xff` (any), **and** whose flag is not set (`SCENE_EXIT_IF`: the flag word follows; the exit is **skipped while the flag is set**);
- falls back to the scene of the first exit, with entrance 0, if it reaches a word with kind 0 or the end (0x1ff) first.

### 2.3 Exit word encoding (VERIFIED)

`include/field_scene.h:72-77`:

```
SCENE_EXITS(scene)              = scene                         // header
SCENE_EXIT(kind, scene, ent)    = kind<<20 | ent<<12 | scene
SCENE_EXIT_IF(k, s, e, flag)    = SCENE_EXIT(k,s,e) | 0x10000000, flag   // two words
SCENE_EXITS_END                 = 0x1ff
```

| Field | Bits |
|---|---|
| scene | 0..11 (the fallback masks only 9 bits, and 0x1ff is the end, so scene ids must be < 511) |
| entrance | 12..19 (0..255) |
| kind | 20..27 (1..254 real, 0xff any, 0 = **header**) |
| flag-follows | bit 28 |

**`SCENE_EXIT(0, N, 0)` is a scene header, identical to `SCENE_EXITS(N)`.** Shared-overlay tables use it: `gAltinPeak_Exits` (`altin_peak.c:2671-2722`) holds 11 scenes' exit lists after one `SCENE_EXITS(77)`. A script found headers for 200 of the 201 overlay scenes; only unnamed scene 59 (overlay 0x39d) has none. TLA additionally treats a flag word of -1 as "always" (`games/tla/src/field/common/take_exit.c`).

### 2.4 Table catalogue in `src/scene/*.c` (+ `common/*.h`) (VERIFIED by script)

| Kind (identify by **type**, names vary: `gX_Exits`, `gXExits`, `gXExits1`…) | Tables | Rows | Tables with `#if` inside | `const` |
|---|---|---|---|---|
| `struct SceneEntrance` | 189 | 1,520 | 0 | 5 |
| `u32` exit tables (`SCENE_EXITS`) | 99 | 1,479 exit words | 1 | 5 |
| `struct ScenePlacement` | 274 | 2,321 | 4 | 18 |
| `struct SceneEvent` | 263 | 5,891 | 10 | 13 |
| `struct SceneRegion` | 14 | 38 | 3 | 1 |
| Door/cell step arrays (`u16` `MAP_CELL_STEP`, `u32` packed cells, `struct MapCellAnim`) | ~10 | — | — | — |

Event kinds by row count:

- `PSYNERGY_ON_ACTOR` 1585
- `EVENT_TALK` 1374
- `EVENT_EXIT` 903
- `EVENT_TOUCH` 531
- `SEARCH(..)` 506
- `TOUCH_WALKING_INTO` 493
- raw hex controls such as `0x31`/`0x21` (exit with sound bits), `0xc4f3`, `0x8413`: about 220

All are file-scope initialized arrays, one brace row per record (exits: one macro per word, sometimes two per line under clang-format, e.g. `world_map.c:2802`). The getters return them, possibly chosen by flag or scene (`vale_home.c:104-160`, `bilibin.c:106-114`). Placement tables are mostly **non-const** because `Scene_AssignViewFlags` writes the `condition` of rows whose condition is 0 at runtime (`src/object/object/actors.c:325`).

---

## 3. Markers (chests, Psynergy stones)

- **Format** (VERIFIED). `markers.tsv` has the header `x:u8	z:u8	event:u8`, rows of cell column, cell row and id, and ends with the row `0xff 0xff 0xff`. It is encoded raw (`markers.table`, **not** LZ) and incbin'd as the 6th header block (`src/map/map_004/map.s:25`). Values may be decimal or `0x` hex: `map_002/markers_es.tsv` differs from `markers.tsv` only in number formatting.
  - There are 118 marker files: 106 base and 12 edition variants (`*_ja/_de/_es.tsv`, chosen by `.ifdef TBS_EDITION_*` in map.s).
  - 76 map.s files point at the empty `map_000/markers.table`.
- **Loader** (VERIFIED). The marker list is not decoded: `work->script = header + header->markers` (`map_layers.c:258`). `Field_PlaceMapMarkers` (`src/object/object/markers.c:30-131`), called from `run_scene.c:73`, does the following:
  - Only ids **100..239** are considered.
  - For each one it takes the first scene event with `trigger == id`:
    - `control & 0x1ff == 19` (`SEARCH(SEARCH_CHEST)`): it creates object **20** (chest) at the cell centre `(col<<20)+0x80000`, snapped to terrain. If the event's condition flag is set, the chest is shown open (animation 2); if the flag is set and the value is a mimic (`0x5xxxxx`), it is not placed at all.
    - other `SEARCH` with value `0x300000` (`FIND_PSYNERGY_STONE`) whose flag is clear: it creates object **28** (stone).
  - At most `MARKER_MAX` = 10 are placed. A marker with no matching event places nothing.
- **Id = collision code** (VERIFIED). All 417 marker rows in TBS have `grid_collision[x,z] == id` (scratch script). The search itself is keyed on the collision code of the cell ahead (`Scene_FindEvent(EVENT_SEARCH, code)`, `events.c:111`, `Field_SearchTile` `events.c:429`). A marker without the matching collision code would show a chest that cannot be opened. **The editor must write both.**
- **Contents and flags** (VERIFIED). Contents live in the scene's event table: `{ SEARCH(SEARCH_CHEST), <id>, <opened-flag>, FIND_ITEM(ITEM_X) | FIND_COINS(n) | FIND_PSYNERGY_STONE | FIND_MESSAGE(m) | 0x5xxxxx mimic | EVENT_SCRIPT(fn) }` (`include/field_scene.h:118-217`).
  - The condition is the "opened" flag. Per the README, most chest flags are ≥ 0xe00. The flag is set when the chest is taken (`events.c:500-560`).
  - Bit 16 of the value means "the party cannot open it".
  - There are 135 `SEARCH(SEARCH_CHEST)` rows and 17 `FIND_PSYNERGY_STONE` rows. Some stones use `SEARCH_FACING(...)` rows with a named `TRIGGER_STONE` constant, and some stones are plain scripts (ValeHome's `Event_UsePsynergyStone`).
- Codes 242..247 are fixed "search spot" messages, 250 is hazard ground, and 252..254 are ledges/climb spots (`step.c:19-27`, `events.c:387-418`). 0xff is a wall.

---

## 4. NPCs and objects

`struct ScenePlacement` (24 B, `include/field_scene.h:81-98`) (VERIFIED):

| Field | Type | Meaning |
|---|---|---|
| sprite | s16 | object/sprite kind; 0-7 = party characters (own slots), -1 ends the table |
| condition | s16 | -1 always; `flag\|0x1000` = flag set; else flag clear; 0 = "in view" (rewritten by `Scene_AssignViewFlags`) |
| behavior | s32 | `ACTOR_STAND`=1, `ACTOR_WANDER`=2, small ints (e.g. 3), or a pointer to an `s32 ...[]` SC_ action script |
| x, y, z | s32 | 16.16 pixels via `PIXELS(n)` |
| facing | u16 | 1/65536 turn |
| talkFacing | u8 | TALK_FACE_PARTY 0, _AND_BACK 1, KEEP 2, 3 follows the leader |
| flags | u8 | bit 0 `PLACEMENT_SHARE_PREVIOUS_SPRITE` |

**Spawning** (`src/object/object/actors.c:75-180`, `ObjectTable_ResetForObject` `:217`) (VERIFIED):

- The leader is spawned from `gGameState`, then the table from slot 8.
- **`actorIndex = slot++` runs before the condition test (`:105-107`)**, so a skipped row still uses its number: **actor = 8 + row index** for sprites > 7. `EVENT_TALK` and `PSYNERGY_ON_ACTOR` triggers name these numbers, so reordering or inserting rows renumbers every talk event.
- Height: y is added to the terrain height off the world map.
- The maximum is 58 placed actors (slots 8..65).
- Djinn flag rows (48..127) also need `condition+80`.

Behavior column counts over 2,321 rows: STAND 1,705, WANDER 132, integer 306, script symbol 178.

- 396 rows are at x=z=0. These are actors the Initialize code positions or moves.
- Inline positioning is common:
  - `Engine_ActorSetPosition`: 405 calls
  - `OBJ_POS_SET(no,x,z)` (pixels, `include/event.h:13`): 119
  - `Engine_ObjectCreate(kind,x,y,z)`: 53, for effects and extra objects
  - `Engine_ActorWalkTo`: 36

So static NPC placement is data, but cutscene staging is code.

---

## 5. TLA `scene_*.tsv` (map block, not overlay)

TLA `map.s` has **7** blocks: metatiles, shapes, grid, shape_grid, animation, blend, scene (`games/tla/src/map/map_008/map.s`). There is no markers block and TLA has no `markers.tsv`.

The scene block is `scene.parts.lz`, LZ-packed. `scene.tsv` lists its parts in order: `SCENE_HEADER, SCENE_POINTS, SCENE_ENTRANCES, SCENE_PATCHES, SCENE_BOUNDS`. It is present in 286 maps.

| File | Columns | Notes |
|---|---|---|
| `scene_header.tsv` | `entrances:u16 patches:u16 bounds:u16 none:u16` | byte offsets from the block start; points start at 8. Checked for all 286: entrances = 8 + size(points), patches = entrances + size(entrances), bounds = patches + size(patches); `none` = 0 everywhere (VERIFIED) |
| `scene_points.tsv` | `id:u8 x:u16 z:u16` | ends with `0xff`; 579 points, ids mostly 1..28, 99 ×10. Meaning unknown (INFERRED: script or camera points; not chests, which are cell-based in TBS) |
| `scene_entrances.tsv` | `id:u8 x:u16 z:u16 flags:u8` | 1,970 rows. INFERRED: equivalent to TBS `SceneEntrance` (id, x, z). The flags' low nibble = facing>>12 (values 4=S 1105×, 12=N 685×, 0=E, 8=W, 2/6/14 diagonals), and bit 4 (16) is an extra flag (28, 20) |
| `scene_patches.tsv` | `key:u16 source_x:u8 source_y:u8 x:u8 y:u8 width:u8 height:u8` | ends with `0xffff`; **empty in all 286** |
| `scene_bounds.tsv` | `left:s8 top:s8 right:s8 bottom:s8` | usually one row + `-1`. INFERRED: camera bounds in 16-px cells (map_008: 0,0,40,34) |

On the overlay side, TLA scenes still have Exits/Placements/Events in C (`games/tla/src/scene/<place>/data.c`). 86 of 97 `SceneEntrance` tables have a single row, the fallback, which strongly suggests TLA's engine takes positions from the map block (INFERRED; the reader is not decompiled). A script trying to match TLA exit (scene, entrance) pairs against map entrance ids by a fixed scene→map offset was inconclusive, because TLA's layered table is not in source.

**Will TBS migrate?** INFERRED **no**, at least not to the same files. TBS ROM maps have 6 blocks with markers, and its engine reads entrances from overlays, so the data lives where the ROM puts it. Git history:

- TLA map files: "TLA: the four field maps still copied, from editable tables" (a20313083f) and others.
- Recent TBS scene work is C humanization ("Align scene table getters with the engine contracts", db7167f0b0).

None of these mention moving scene tables to TSV.

---

## 6. Adding a new map or scene (checklist)

Prefer **appending** over inserting everywhere.

1. **Map data.**
   - Create `src/map/map_180/`: `map.s` (`.global Field_Map180`, `map_header`, 3×`map_layer`, 6×`map_block`, incbins) and the TSVs.
   - Reuse an existing tileset (no new sheets) or add sheets and a palette after it.
   - Unused blocks are `map_block Field_Map180` with an offset of 0. For markers, point at `map_000/markers.table` or your own.
2. **objects.tsv.** Add `main rom_tail_02 games/tbs/src/map/map_180/map` **before** the `system/overlay/overlays` row (objects.tsv:631). This gives the ROM order; no address is pinned after 0x08320000.
3. **directory.s.** Turn one `unused` into `resource , Field_Map180`, and into palette/tiles if new; reduce `unused 25` accordingly (`:307`). The new ids are 0x3cf+ and existing ids do not shift.
4. **layered.tsv.** Append a row of offsets from `ResourceId_Map001`: map, palette, tiles ×3, layer data. Its row index is the scene's `map`. It is placed in `rom_main_01`, with free space before the fixed `rom_main_02` start: EN 4,020 B, DE 1,204 B, ES/FR 1,972 B (12 B per row).
5. **Scene overlay** (to give the scene its own code):
   - `src/scene/<place>.c`, `entry/<place>.s` (6 veneers), `import/<place>.s` (imports in `overlay.inc` order);
   - prototypes in `include/unit/scene/<place>.h` (91 exist);
   - objects.tsv rows `3cf text .../entry/<place>`, `3cf text .../<place>`, `3cf text .../import/<place>`, plus optional `3cf bss ...` with an `overlays.tsv` header row;
   - `src/system/overlay/overlays.s`: `Resource_Overlay3CF: .incbin "overlays/resource_3cf.lz"` + `.balign 4`;
   - directory: one `unused` slot becomes `resource , Resource_Overlay3CF`.
   - Alternatively, reuse an existing overlay as a variant, like the Altin Peak rooms: add a scene row with the same code and branch on `SceneId_` in the getters.
6. **scenes.s.** **Append** `scene NewPlace, 0x3cf, <group>, <variant>, <layered row>` at the end. The new id is 201, so all existing numeric ids stay valid. The table is in `rom_main_04`, 8 B per row; free before the fixed bank: EN 3,448 B, DE 1,040 B. Add `extern char SceneId_NewPlace;` to `include/scene_ids.h`. The group must be ≤ 0x7f (visited flag). Scene ids must be < 0x1ff (exit word fallback).
7. **Connections.**
   - Add an exit word in each neighbour's exit table under **its** header: `SCENE_EXIT(kind, 201, entrance)`.
   - Add an `EVENT_EXIT` (or touch script) row in the neighbour's events for the collision code you paint on the exit cells.
   - Paint that code in the neighbour's `grid_collision.tsv`.
   - Mirror the same in the new scene: `SCENE_EXITS(201)` header, its exits, entrances whose numbers match what the neighbours' exit words name, placements, events.
8. **Rules.** Music (`scene_cue`/`group_cue`), area name (`scene_name`/`group_name`), defeat return (`return_to`) and backdrop in `src/object/scene_rules.s`; encounters in `src/object/location_rules.s`. Without rows you get MUS_018, no name, no encounters, and the last backdrop.
9. **Text.** Add messages to `text/<lang>.po`, with a `msgctxt` per message symbol.
10. **Budget** (VERIFIED, `out/tbs-*/tbs-*.map`).
    - ROM is padded to 0x08800000 (Makefile:134). Free space at the end: EN 11,076 B, IT 11,040, DE 10,108, ES 4,128, FR 3,584, JA 43,100.
    - A new map plus overlay will likely exceed this, so the 8 MB `ROM_END_tbs` has to be raised. `MEMORY ROM` already allows 32M (`main.ld`). This makes the ROM non-matching. (INFERRED: safe; untested.)
    - Overlay RAM ≤ 32 KB.

---

## 7. Code-generation feasibility (per table)

General rule: values compile to fixed bytes, so formatting and whitespace are free. Byte-exactness depends on:

- the same row order;
- the same values, including symbolic ones (`MSGNO(Msg…)` resolves to message numbers, `EVENT_SCRIPT(fn)` to relocations, flag names from `flags.h`);
- the same `const`, which picks `.rodata` vs `.data` placement;
- the same per-edition and per-patch `#if TBS_PATCH_n` / `LANGUAGE` blocks;
- the same table order in the file.

| Table | Rewrite-safe? | How to round-trip |
|---|---|---|
| SceneEntrance | Yes, very regular: 12 literal fields, 21 symbolic entrance names | CST-preserving edit of one `{...}` row; keep a symbol when the value is unchanged |
| Exit `u32[]` | Yes, with care: macros only, but per-scene `#define`s (`ROOM_ENTRANCE(exit)`, `LUNPA_EXIT_TO_*`), `SCENE_EXIT(0,N,0)` headers, `#if !TBS_PATCH_3` (vale_home.c) | parse macro calls, evaluate to words, re-emit only the touched calls; never collapse `SCENE_EXIT(0,..)` and `SCENE_EXITS` |
| ScenePlacement | Mostly: `PIXELS(n)`, `FACING_X + FACING_STEP`, character names (`GARET`), script symbols, 4 tables with `#if` | edit fields in place; keep row order (actor numbers) |
| SceneEvent | Hardest: bitfield macros plus ~220 raw hex controls, message and function symbols, 10 `#if` | treat as opaque tokens except the fields edited (trigger, condition, FIND_ value) |
| SceneRegion | Yes, small: 3 with `#if` | in place |
| markers.tsv | Yes, data file | rewrite TSV; decimal and hex both accepted |
| scenes.s / layered.tsv / directory.s | Yes, line-oriented | append only |

Verification:

- Rebuild and run `make compare` / `compare-tbs` (Makefile:48-51).
- For quick checks, diff `out/tbs-<ed>/overlays/resource_<id>.elf` sections before and after a no-op rewrite. A pure reformat must give identical overlay `.bin` and `.lz` output.
- Avoid regenerating whole files: they hold code, `// clang-format off` regions, comments and `#ifdef UBFIX` blocks.

---

## 8. Unknowns

- What writes `EventWork.touchedTrigger` (`include/field/event_work.h:26`), which scripts read. It has no named writer in main code (INFERRED: the touched code).
- `ScenePlacement.behavior` small integers other than 1 and 2 (3 is common): `ObjectMotion_SetActionCallback` semantics are not traced here.
- The full sprite-kind table (object ids 20 = chest, 28 = stone and 0x8000 = camera are VERIFIED from markers.c and actors.c).
- TLA: the meaning of `scene_points`, `scene_entrances.flags` bit 4, bounds units, the scene→map resolution, and the scene table's 6th column (also XXX in `games/tla/src/field/README.md`).
- Whether directory `unused` slots and a ROM larger than 8 MB work on hardware and emulators (INFERRED yes).
- Scene 59 (unnamed, 0x39d) has no exit header. Exits there leave the scene unchanged (`Scene_TakeExit` keeps the state when no header is found).

---

## 9. Proposed editor data model

```
Project
  scenes[id]            // from scenes.s (append-only ids)
    name, overlayId, group, variant, layeredRow
    overlay -> OverlaySource (.c path; shared by N scenes)
  layered[row]          // layered.tsv: {map, palette, tiles[3], layerData} as resource refs
  maps[NNN]             // map_NNN/: header, planes, metatiles, shapes, anim, blend,
    markers[]: {x,z,id}  //   + edition variants; id must == grid_collision[x,z]
  overlay tables (per C array, identified by type, with source span + #if context):
    Entrance  {entrance, requiredFlag, x,y,z, facing, camera{l,t,r,b}}
    ExitTable {segments: [{headerScene, exits:[{kind, scene, entrance, flag?}]}]}
    Placement {sprite, condition, behavior(enum|script ref), x,y,z (px), facing, talkFacing, flags}
              // derived: actorId = 8 + rowIndex
    Event     {kind+detail (decoded control), trigger, condition, value(msg|script|FIND_*)}
    Region    {min{x,y,z}, max{x,y,z}, condition, exitKind}
    getter    {which tables, chosen by which flags/scene ids}  // read-only, shown
  derived graph: Scene --(collision code / script / region)--> exitKind
                 --exit table--> (scene, entrance) --> Entrance row
```

Editing operations:

- **Move an exit cell:** grid_collision code plus the `EVENT_EXIT` row.
- **Retarget:** edit the exit word.
- **Add a chest:** marker row, collision code, and a `SEARCH(SEARCH_CHEST)` event with a fresh flag ≥ 0xe00.
- **Move an NPC:** edit the placement x/z, and warn if the row's x=z=0 means code positions it.

Validate across all of these:

- entrance numbers referenced by every exit word exist in the target's Entrances (the row-0 fallback otherwise);
- actor-number shifts when placement rows are inserted;
- the marker limit of 10;
- the 32 KB overlay and ROM budgets.

---
