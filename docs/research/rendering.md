# Rendering research: layers, blending, tile animation, placeholders

Source: alchemy (`games/tbs/...`). Paths are relative to `games/tbs/` unless they say otherwise.
VERIFIED means the claim was read in engine code and confirmed by rendering. INFERRED means it is a reasoned guess.
Scratch scripts and renders are in
`(a scratch folder)`
(`r2.py` is the reference renderer, `dirmap.py` resolves the scene resource table).

## Summary

The "scrambled" maps are not caused by parallax. Three bugs in the viewer cause them, and two of them affect almost every map:

1. **Placeholder cells (0xfff) are real art.** At load time the k-th 0xfff cell, counted row-major over the whole 128×128 grid, becomes block k. In **all 182 maps**, the number of placeholder cells is exactly the number of rows in `metatiles.tsv`. The block table is effectively "unique blocks in reading order", and explicit cell values reuse them. Drawing placeholders as empty drops most of every map. (VERIFIED)
2. **The tileset comes from the wrong table.** The game loads a map's palette, its three VRAM sheets and its sheet D from `src/field/layered.tsv` (`gMap_LayeredScenes`), not from the order in `directory.s`. **117 of 182 maps** use a different palette or sheet combination than the viewer assumes. Examples: map 034's char block 3 is `Set02TilesC` and its sheet D is `Set26TilesC`. VenusEntrance uses `Set07` sheets with `Palette49`. (VERIFIED)
3. **Header bounds are only the default camera bounds.** A scene's entrance table can override them. Map 034 (scene Bilibin3) is clamped to 16..400 px by its entrances. Outside that range, the 128×128-tile header area is grid fill (block 3), which is never seen in game. (VERIFIED)

Parallax and drift exist on only 8 maps (047, 103, 104, 147, 148; on 090/091/092/169 the masks have no effect because speed is 0). Blending is BLDCNT/BLDALPHA set by a small script. The first target is almost always layer 2 (BG1), sometimes layer 1 (BG2). Tile animation is DMA tile copies from sheet D into VRAM. All four were implemented in `r2.py` and checked by rendering.

## (a) Layers, windows and scrolling

**Structures.** `struct LayeredSceneLayer {u8 x, y; s8 scrollX, scrollY, speedX, speedY; u8 periodX, periodY;}` is at `src/field/field/map_layers.c:172-181`. The `map_layer` macro order is the same: x, y, rate_x, rate_y, drift_x, drift_y, period_x, period_y (`src/map/map.inc`).

**Load** (`map_layers.c:274-303`, VERIFIED):
- `offset = x<<19` and `y<<19`, so the origin is x×8 px in 16.16 fixed point.
- `scale = scroll*4096`, so rate/16 of the view.
- `speed = speed*4096`, so speed/16 px per frame.
- `mask = period`.
- `phase = 0`.

**Per frame** (`Map_UpdateLayerScroll`, `map_layers.c:474-566`; same in `Map_SetCameraCenter` 572-630, VERIFIED):
```
view   = followed point - focus, clamped to [min, max - 240x160]        (min/max = header bounds*8 px, or scene overrides)
base   = view * scale            (Q16 multiply → view * rate/16)
if speed: phase += speed; base = (base + phase) & ((period<<19) | 0x7ffff)   # wrap; only applied when speed != 0
pos    = base + offset           # layer's top-left in grid pixels
BG(3-li) scroll = pos
```
Drawing reads cells at `((pos/16) & 0x7f)` in both axes (`Map_RenderMetatileRow/Column`, 411-462). So **a layer window wraps modulo 128 cells (2048 px)**. Window size = screen; there is no per-layer window size.
Layer li is shown on BG(3-li), with BGCNT priority = the header priority byte, char base = the header char byte, and screen base 5+li (314-322).

**Camera bounds.** `work->min/max = header bounds << 19` (261-264). `Scene_ApplyEntrance` (`src/object/object/run_scene.c:488-499`) overrides each of minX/minY/maxX/maxY in pixels when the entrance's `cameraLeft/Top/Right/Bottom != -1` (`struct SceneEntrance`, `include/field_scene.h`). Map 034 = scene `Bilibin3` (`src/field/scenes.s:50`, map index 0x24). Its entrances 1 and 2 use bounds 16,16,400,400 (`src/scene/bilibin.c:780-785`). A few scenes also write the bounds directly (`tolbi_ship_deck.c:1062`, `vale_babi.c:418-421`, `psynergy_effects/view.c:16`).

**Maps with non-default layer params** (everything else is `16,16,0,0,255,255`):

| map | layer | params | meaning |
|---|---|---|---|
| 047 | 0 | rate 8,8 | half-speed parallax |
| 103 | 0 | drift_y −25, period 255 | background flows up 25/16 px/frame, wraps at 2048 px |
| 104 | 0 at y=92 | rate 6,6 | sky/sea parallax (ship mast scene) |
| 147, 148 | 2 | rate 20,20, drift −121/16, 35/16 px/f, period 31 | sandstorm overlay, wraps every 256 px |
| 090-092 (layer 0,1), 169 (layer 0) | | period 127/63, speed 0 | no effect (mask only used when speed ≠ 0) |

**Priority order (GBA, VERIFIED by render).** Draw back to front sorted by `(-priority, layer index)`. At equal priority, the lower BG number is on top, so layer 2 (BG1) is over layer 0 (BG3). The current viewer's `sorted(key=-priority)` is stable, so it already gives the same result. Priority 0 = off.

**Rendering rule for a Python viewer:**
- *Field layers* (rate 16, speed 0): `grid_px = (origin_px + map_px) mod 2048`, where `map_px` is measured from (0,0) of the grid space, not from bounds.left. This is exact for any camera. The current `render_layer` behaves like this for left=top=0, but it does not wrap modulo 128 cells and it ignores a non-zero bounds.left/top.
  - Correct form: `gx = (x*8/16 + bounds.left/2 + i) % 128` for screen column i of the bounds window, and the same for y.
- *Parallax/drift layers* have no single static image. Recommended map-view rule: anchor at the middle of the camera range.
  - `V = ((min + max(min, max-240))/2, same for y)` and `pos = layer_pos(V) + (map_px - V)`.
  - This is exact for the camera at V and continuous elsewhere. Drift phase = 0 (or speed×frames).
  - Also offer a 240×160 "camera preview" that uses `layer_pos(view)` exactly.
- *Crop* to scene camera bounds when known; otherwise use the header bounds.

## (b) Blending

**Mechanism** (`src/field/field/map_animation.c:163-255`, VERIFIED):
- `blend.tsv` compiles to halfwords: `control v` → v (a BLDCNT value, recognised by top nibble 3); `level v wait` → v, wait; `jump n` → 0xfe00|n (cursor = script + 2n halfwords); `stop` → 0xfeff; `end` → 0xffff (loop to start).
- On a `level`:
  - if the last BLDCNT's effect bits (7..6) are 01, then `REG_BLDALPHA = v`;
  - otherwise `REG_BLDY = v`;
  - then wait `wait` frames.
- A script that is only `end` installs nothing (`DisplayBlend_StartScript` 246).
- The loader sets `REG_BLDCNT = 0` first (`map_layers.c:365-367`).

**GBA semantics:**
- BLDCNT bits 0-5 are the 1st target (bit0 BG0, bit1 BG1 = layer 2, bit2 BG2 = layer 1, bit3 BG3 = layer 0, bit4 OBJ, bit5 backdrop).
- Bits 6-7 are the effect (1 alpha, 2 brighten, 3 darken).
- Bits 8-13 are the 2nd target.
- BLDALPHA: EVA = bits 0-4 (weight of the target-1 layer), EVB = bits 8-12 (weight of what is below), each capped at 16.
- `out = min(31, (top*EVA + below*EVB) >> 4)` per 5-bit channel.
- BLDY: `I + (31-I)*Y/16` (brighten) or `I - I*Y/16` (darken).

**Values found in the TBS maps** (first `level` after `control`):

| BLDCNT | target layer | effect | maps (examples) |
|---|---|---|---|
| 0x3f42 | layer 2 (BG1) over everything | alpha | 005-007/032/076 (0x1006: 6/16 + 16/16 additive), 021, 022-024/136/137, 025-027/077-085 (0xa09: 9/16 + 10/16 = 080's water), 029, 033/040/062/115/144 (0x1003 glow, animated 3-4), 047 (0xc04), 053, 054-058/109/155/156/163, 063-067/100, 073, 075, 108, 113, 133, 139-142 (0xb0e), 154, 164-167 |
| 0x3f44 | layer 1 (BG2) | alpha | 009/145/146, 010/019, 012/013/016, 014/015, 018/038/052/094/095/099/102/120/121/151/160/161 (0x1008), 061, 086, 105, 124 |
| 0x3fc8 | layer 0 (BG3) | darken, BLDY 3-6 | 046 |
| (none) | — | BLDY only, no effect | 039/042/043, 114, 125: the script writes levels with BLDCNT=0. A scene must set BLDCNT (INFERRED) |
| `end` only | — | — | 36 maps (020, 028, 031, 036, 037, 048, 051, 060, 072, 074, 089, 093, … incl. 134 via `map_020/blend`) |

Most levels with EVB=16 are **additive glow** (light shafts, torches). A wait of 43210 means the level is constant.

**Scene-set blends** (not in `blend.tsv`; VERIFIED in code):
- `src/scene/altmiller_cave.c:195-222, 313-320`: BLDCNT 0x3f42 with BLDALPHA 0x1000..0x600, or 0xc04. Map 134 = scene AltmillerCave5 (`scenes.s:165`) has its darkness layer blended this way.
- Also `tret_tree_branch.c:163` (BG1 4/12), `tolbi_spring.c`, `vale_babi.c`, `mercury_lighthouse*.c`, `crossbone_isle_platform_rooms.c`, `lemurian_ship.c`.

**Rendering rule:**
- Parse the blend script and take the BLDCNT and the first level, or simulate it to frame t.
- For each layer drawn back to front: if its BG bit is in target1 and effect==1, `rgb = min(31,(layer*EVA + below*EVB)>>4)` where the layer is opaque. "Below" is the already-composited colour (or the backdrop); all TBS controls use 2nd target 0x3f.
- For effect 2/3, apply BLDY to that layer's pixels.
- Use 5-bit colour (PNG value >> 3) for exact results.
- Optionally keep a small per-map override table for scene-set blends (134 → 0x3f42/0xc04).

## (c) Tile animation

**Mechanism** (`src/field/field/map_animation.c:7-145`, VERIFIED):
- `animation.tsv` compiles to halfwords: `channel n` → 0xfd00|n, `frame src cnt dst wait` → 4 halfwords, `jump n` → 0xfe00|n, `stop` → 0xfeff, `end` → 0xffff.
- `MapAnimation_StartChannels` scans the stream. Each 0xfdNN starts channel NN&15 at the next halfword, paused if bit 7 is set (`channel 0x8N`; a scene resumes it via `Map_ClearLayerEntryFlag`).
- Each frame, for each unpaused channel:
  - if timer>0: timer−− and move to the next channel.
  - else execute at the cursor:
    - 0xffff → cursor = start
    - 0xfeNN → cursor = start + 2·NN halfwords
    - 0xfeff → stay stopped
    - otherwise copy `cnt` tiles, set timer = wait, cursor += 4, and loop again in the same frame.
  - So **a copy with wait W stays on screen for W frames**, and W=0 chains to the next copy in the same frame.
- Copy (4bpp, `wideTiles==0`), in 32-byte tiles counted from **char block 1**:
  - `src >= 0x600`: from `Ram_DecodeBuffer (0x0201c000) + src*32`, which is `gMapLayerData` (0x02028000, `src/system/ewram.s:236-244`, `include/ram_buffer.h`) + (src−0x600)*32. That is **sheet D tile src−0x600** (sheet D = `layered.tsv` column 5, decoded to gMapLayerData at `map_layers.c:357-359`).
  - `src < 0x600`: from VRAM tile `512+src` (absolute, from block 0).
  - Destination: VRAM absolute tile `512+dst`.
- A map entry's absolute tile is `charBase*512 + (entry & 0x3ff)`.

**How to produce frame t:**
1. Start VRAM: blocks 1/2/3 from `layered.tsv` columns 2/3/4, and sheet D from column 5.
2. Build channels as above; skip paused channels (`channel 0x8N`).
3. Run the update t+1 times, mutating a VRAM tile array.
4. Then render normally with the mutated tiles.

The loops are short (34's water cycle is 24 frames; 127 jumps after 10+10 frames). A GIF/preview can step 1..N frames. The metatile atlas must be rebuilt per frame, or better, cached per tile.

## (d) Placeholders 0xfff

**Mechanism** (VERIFIED):
- `Tilemap_ConvertBuffer` (`src/field/field/map_layers.c:110-122`) runs `Tile_ConvertMap` (`src/graphics/tile/convert_map.s:8-50`) on the block plane.
- r5 = 0xFFF00000 tests `(cell<<20) == 0xfff<<20`.
- r4 starts at 0xFFFFF001; `cell + r4` (truncated to 16 bits) = `(cell & 0xf000) | k`, and r4 increments per placeholder.
- The unused C twin `Tilemap_NumberPlaceholderBlocks` (84-103) does the same.
- Result: **the k-th cell (0-based, row-major over all 128×128 cells, all layers together) whose low 12 bits are 0xfff becomes block k. Its top nibble is kept.**
- Drawing then uses `Ram_MapBlocks[(cell<<20)>>19]` (low 12 bits only, 411-437).

**Validation.** For every one of the 182 maps, the placeholder count equals the number of rows in `metatiles.tsv` (`allph.py`). Renders of 034 and VenusEntrance become coherent art (see below). So placeholders are not filled by unknown code: they are the map's unique blocks in reading order. The `XXX` in `src/map/README.md` can be answered. (Only cells that hold exactly 0xfff at load are counted; runtime cell copies `Map_CopyMetatileIndicesRect` happen later.)

**Rule:** before rendering, `n=0; for y in 0..127: for x in 0..127: if cell&0xfff==0xfff: cell=(cell&0xf000)|n; n+=1`.
For an editor this has consequences:
- Painting a cell to or from 0xfff renumbers every later placeholder.
- Editing must keep the placeholder count equal to the block count, or the stored blocks shift.
- Show the resolved block number, and when saving, store 0xfff only where `resolved == running count`. Alternatively, keep cells as they are and treat 0xfff as "next unique block".

## Validated renders

All in `(a scratch folder)`:
- `cur_034.png`, `cur_VenusEntrance.png`: the current viewer (broken).
- `ph_034.png`, `ph_VenusEntrance.png`: placeholder fix only (034 coherent; Venus still wrong tileset).
- `new_034.png`: all fixes. Coherent river/forest in cells 1..25. The rest is off-camera fill.
- `new_VenusEntrance.png`: all fixes. Correct forest and Venus Lighthouse entrance.
- `new_040.png` vs `new_040_noblend.png`: additive torch glow (0x3f42, 0x1003).
- `new_080.png` vs `_noblend`: water blended 9/16 + 10/16.
- `new_016.png`: Sol Sanctum rooms, 0x3f44 on layer 1.
- `new_134.png`: opaque darkness. `new_134_sceneblend.png`: with Altmiller's 0x3f42/0xc04, darkness at 4/16.
- `new_104.png` (mid-camera anchor), `cam_104_0_0.png`, `cam_104_128_208.png`: parallax sky.
- `new_147.png`: drifting sand overlay.
- `new_047.png`, `new_103.png`.
- `anim_034_f00..f40.png`, `anim_034.gif`, `anim_034_compare.png`: water animation frames 0 vs 24 differ.

## Exact changes recommended for gsmap/project.py

1. **Scene resources** (replace `_read_directory` pairing):
   - Expand `directory.s` into an ordered entry list. Apply the macros exactly: `group K, a,b` → `K_a, K_b`; `area S, L, maps` → `Field_MapNN…, Tileset_SPalette, Tileset_STiles<L…>`; `recolor P, maps` → `Field_MapNN…, Tileset_PaletteP`; `overlays`; `unused N` → N entries; `resource , X` → X.
   - Set `base = index('Field_Map001')`.
   - Each row of `src/field/layered.tsv` is `[header, palette, blk1, blk2, blk3, sheetD]`; map each to `entries[base+v]`.
   - Key by the header label (`Field_MapNNN` / `Field_<Name>`), and use the first row. Maps 108 and 110 have two rows with different palettes (45/58 and 15/18). Expose the alternative.
   - Resolve labels through the existing `self.symbols`. Reference implementation: `dirmap.py`.
2. **Atlas:** absolute tile `a = char_base*512 + (e&0x3ff)`.
   - Block `a//512` 1..3 → `[blk1, blk2, blk3][a//512-1]`. Block 0 = window tiles, so skip it. 4+ is invalid.
   - Palette rows 14/15 are not the map's (UI). Show them as transparent or a debug colour.
3. **Placeholders:** resolve 0xfff → running ordinal (rule in d) in `load_grid` for rendering. Drop the `== EMPTY → skip` test. Keep the raw grid for saving.
4. **Windows:** `gx = (layer.x//2 + bounds.left//2 + i) % 128`, and the same for y (wrap, not skip). For layers with rate≠16 or drift≠0, use the mid-camera anchor rule from (a).
5. **Blend:** parse blend.tsv (`control`/`level`/`jump`/`stop`/`end`). Composite back to front with the BLDCNT/BLDALPHA/BLDY formulas in (b). Default the layer opacity slider to EVA/16 only as an approximation (the exact result is additive: `top*EVA + below*EVB`).
6. **Animation:** keep a mutable `vram[2048]` tile array plus `sheetD[512]`. Step channels per (c). Expose a frame number or play control.
7. **Camera bounds (optional):** default to the header bounds. Offer "crop to content" or scene entrance bounds. Scene → map index comes from `src/field/scenes.s` (`scene name, code, area, kind, map`, where map = the row in `layered.tsv`). The bounds are in `struct SceneEntrance` tables in `src/scene/*.c`.

## Unknowns

- How blends work for maps whose script has no `control` (039/042/043/114/125). INFERRED: a scene sets BLDCNT; not traced.
- Scene-set blends and animation resumes (`channel 0x8N`) per map: only Altmiller (134) was traced.
- Which `layered.tsv` row a scene uses when a map has two (108, 110). Both palettes are valid.
- Why only vertical drift fills all 32 BG rows (`map_layers.c:600-604`, an alchemy XXX). This doesn't matter for a static render.
- Camera bounds for maps other than 034 were not tabulated. `scenes.s` + entrance tables would give them.
- Only the EN edition branch was checked; `layered.tsv` has no edition variants.
