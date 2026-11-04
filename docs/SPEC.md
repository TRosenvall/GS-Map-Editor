# gs-mapedit: editor spec and build plan

Scope: a map editor for **Golden Sun: The Broken Seal** built on alchemy's source tree. It covers **local maps** (towns, dungeons, interiors) and the **overworld**. The Lost Age shares the local map format, so it comes later at low cost. Its overworld engine is still mostly assembly in alchemy.

The editor reads and writes only alchemy's source files: TSV, PNG, and narrow regions of C/asm tables. It never touches a ROM. Detailed evidence, with file:line references, is in `docs/research/` (`rendering.md`, `local-connections.md`, `overworld.md`). This file states the decisions.

## Ground rules

1. **Byte-exact round trip.** Loading and saving anything unedited must reproduce the file byte-for-byte. Every file kind gets a round-trip test over the whole tree. An unedited build must still `compare` OK.
2. **Edit in place; append, don't insert.** Table row positions are identities. Actor number = 8 + placement row. Scene id = row in `scenes.s`. Exit tables use plain scene numbers. Inserting a row silently renumbers things, so new rows go at the end.
3. **Validate before save.** Every operation has invariants (below). The editor refuses to save a state that breaks one, or flags it loudly.
4. **The build is the judge.** After saving, run `make tbs-en`. The editor surfaces build errors. A playtest in mGBA is the final check.
5. **Pin alchemy.** Work against a known commit. Before moving to a new one, run `tests/roundtrip.py` and the render-all check (about 2 minutes). They caught the Oct 19 path restructure immediately.

## Local maps

### Rendering (implemented, verified on all 182 maps)

- **Resources:** each map's palette, char blocks 1–3 and sheet D come from its `gMaps` row (`map/maps.c`), resolved through the expanded `gamepak/resource_directory.s`. Maps 001, 002, 108 and 110 have alternate rows.
- **Placeholders:** the k-th `0xfff` cell, row-major over the whole 128×128 grid, is block k with its top nibble kept (`field/map_grid_convert.s`). The placeholder count equals the `metatiles.tsv` row count on all 182 maps.
- **Windows:** each layer's window starts at the layer origin plus the header bounds and wraps at 128.
- **Still to do:**
  - blend compositing (`blend.tsv`: BLDCNT/BLDALPHA/BLDY);
  - tile animation (`animation.tsv`, sheet D);
  - parallax anchoring for maps 047, 103, 104, 147 and 148;
  - optional camera bounds from scene entrances.

  The rules are in `rendering.md`.

### Editable data and invariants

| Thing | File | Edit | Invariants / notes |
|---|---|---|---|
| Blocks per cell (3 layers) | `map.txt`, each cell's picture | paint resolved block ids | Saved with the **placeholder encoder**: walk row-major with counter k. A cell whose block == k is written `0xfff` (top nibble kept) and k++; other cells are written explicitly. Verified to be the exact inverse on all 182 maps. |
| Block definitions | `cell_pictures.tsv` | append new 2×2 tile combos | Max 4,095 blocks. Row number = block id. |
| Collision codes | `map.txt`, each cell's behavior | paint | Per layer window. Codes 1–239 can carry events (exits, chests). |
| Height / shape | `map.txt`, each cell's shape, + `shapes.tsv` | paint | Per layer window. |
| Chests / Psynergy stones | `treasure_spot x, z, id` lines in `map.s` | add/move/remove | **id must equal the collision code at (x, z)**: verified 418/418. Max 10 per map. End marker row `ff ff ff`. Contents need a `SEARCH(SEARCH_CHEST)` event in the scene with a fresh flag. |
| Tile animation | `animation.tsv` | later | 16 channels max. |

Shared files: blocks can come from another map's folder, and `default/` cells and attributes are shared too. The editor shows when a file is shared and warns before editing it.

### Scene tables: one hook, editor-owned overrides

**Design (owner's direction): minimal changes to alchemy's files.**
- The engine reads every scene table through `gOverlayArea`, the scene overlay's entry table in RAM. Overlays are loaded in exactly one place: `Scene_LoadOverlay` (`system/main_routine.c`).
- The editor adds **one line** there, `MOD_SCENE_LOADED(gMainRoutineWork.next, &gOverlayArea);`. It's a macro that expands to nothing unless the build defines `GSMOD`, so the stock build keeps matching retail.
- With `GSMOD`, the macro calls editor-generated code in `games/tbs/src/mod/`. That code swaps the entry table's function pointers (entrances, exits, placements, events, regions) for functions returning the editor's override tables for that scene, and leaves the rest alone.
- The world map is also a scene overlay, so the same hook covers overworld icons, exits and events.
- Scene `.c` files are never rewritten. Override tables live in the mod folder, in ROM. Pure data files (map tables, chest lines) are still edited directly.

The underlying tables, for reference:

Scenes live in `games/tbs/src/scene/<place>.c`. They hold five table kinds, all file-scope C arrays of literals and macros:

| Table | Count | Row fields |
|---|---|---|
| Entrances | 189 | entrance, required_flag, x, y, z, facing, camera bounds |
| Exits | 99 | kind → (scene, entrance), optional flag |
| Placements | 274 | sprite, condition, behaviour, x, y, z, facing, talk facing, flags |
| Events | 263 | kind/control, trigger, condition, value |
| Regions | 14 | min/max box, condition, exit kind |

The editor *reads* these arrays from the scene `.c` files, seeding an override with a scene's original rows, and *writes* only the override copies in `mod/`. Events: decode the known control words and keep unknown ones verbatim (about 220 are raw hex).

Validation:
- Every exit's target entrance exists in the target scene.
- Placement rows aren't inserted mid-table (actor-number shift).
- Overlay size stays under 32 KB (the largest has 120 B free).
- Rows with x=z=0 are positioned by code; the editor marks them read-only.

The exit graph is: collision code / script / region → exit kind → exit table → (scene, entrance) → entrance row. The editor shows it as clickable links between maps.

### New maps (last stage)

The checklist is in `local-connections.md` §6:
- 25 spare resource-directory slots, pinned at 0x08320000;
- append rows to `gMaps` (`map/maps.c`) and `scenes.s`;
- add the map row to `objects.tsv` before the overlays, plus the overlay, music, area-name and encounter rules;
- group ≤ 0x7f, scene ids < 511.

**ROM space is the real limit:** 3.5–43 KB free at the 8 MB end, depending on edition. A real new map probably means growing the ROM past 8 MB, which is untested.

## Overworld

| Thing | File | Notes |
|---|---|---|
| Ground + overlay cells | `map/world/blocks.tsv` | 320×512 u32. Chunks are 16×16 cells, laid 32 wide in the TSV and 16×16 in the world. Ground = chunk c, overlay = c + 320. Alternates 256–319 (snow set, story bridge). Cell bits: 0–15 block, 16–23 step/event code, 24–30 terrain kind (= encounter region), 31 behaviour bank. |
| Blocks | `map/default/cells.tsv` | 4,386 × 4 tile bytes. **Shared with local maps.** Prefer appending. |
| Walkability | `map/default/attributes.tsv` | Per 8×8 tile, 4×4 nibbles. Overlay wins, then ground, else 7. Values 5–12 are walkable. Also shared. |
| Graphics | `graphics/world_map/*.png` | 8bpp, 256 tiles per layer, 224 colours. Set B is the snowy north. Preserve PNG mode and indices. |
| Town icons / entering | `scene/world_map.c` `gWorldMapPlacements`, `gWorldMapEvents`, `gWorldMapExits` | Icon = actor 8 + row. Touching raises trigger 100 + actor → `EVENT_EXIT` → exit → (scene, entrance). Some entries are step codes instead. Must stay aligned with `gWorldMap_PlaceMarkers` (actor 11 + i). |
| Leaving to the world | `gWorldMapEntrances` | A town's `SCENE_EXIT(n, 2, e)` places the party at row e. |
| Encounters | `object/zonedata.c` rules → `object/encounter.tsv` zones | Terrain kind + behaviour → rule → zone (104 fixed rows). |

Caveats:
- The pause-screen map (`picture.png`) is separate art, so it needs repainting by hand after coastline edits.
- There are no per-language overworld variants in TBS.
- The Lost Age's overworld differs (2048 chunks, 32×32) and its engine is mostly assembly, so it's out of scope until alchemy matches it.

## Build plan

| Stage | Delivers | Verification |
|---|---|---|
| **1. Viewer** ✅ | All 182 local maps rendered correctly; overlays; hover info | round trip 895 files; render-all; visual checks |
| **1b. Render fidelity** | Blend compositing, animated tiles (play/frame), parallax anchoring, camera-bounds crop | Compare against `rendering.md` validated renders; ideally mGBA screenshots |
| **2. Local painting** ✅ except the new-block composer | Block palette from atlas; paint per layer; collision/height brushes; new block composer (pick 4 tiles); undo/redo; save with the placeholder encoder | Unedited save byte-identical; edited save builds (`make tbs-en`); boots in mGBA |
| **3. Markers + scene tables** ✅ adding, filling, moving and removing chests; doors linked by clicking (relink, add, remove, script doors included); events in words with new lines, signs, step messages, people and conditions; exit areas; moving stones; entrances, NPCs, exits | Chest/stone placement (marker + collision + event); entrance/exit/placement editing; exit graph navigation between maps | Table round trip byte-identical over all 201 scenes; build; playtest an exit change |
| **4. Overworld viewer** ✅ | Top-down world with set A/B, overlay layer, walkability, terrain-kind/encounter overlay, town icons and exit links | Port the research prototype; compare `world_mixed_small.png` |
| **5. Overworld editing** ✅ ground/overlay blocks, regions, icon moves and links; step codes, encounter zones and new icons still to do | Paint cells (block, terrain kind, step code); edit icons, exits, entrances; encounter zones | Round trip of `blocks.tsv` and tables; build; playtest |
| **6. New maps / scenes** | Wizard for the new-map checklist; ROM budget meter | Build; playtest |

Stages 2–3 make the local editor genuinely useful. 4–5 add the overworld. 6 is the riskiest, because it depends on ROM space.

## Open questions

- ~~Does the build require placeholder count = block count?~~ **No.** Tested: an edit leaving 56 placeholders for 441 blocks builds and links. The encoder writes later blocks explicitly once a first appearance is painted over, so the diff is larger but valid. In-game appearance still needs a playtest.
- Maps whose `blend.tsv` never sets BLDCNT (039, 042, 043, 114, 125): the blend probably comes from scene code.
- What TLA's `scene_points` are; what writes `touched_trigger`; placement behaviour values above 2.
- Whether a ROM over 8 MB boots and saves correctly on target emulators and hardware.
