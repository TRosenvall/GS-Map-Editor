# Naming layer: collision codes, items, sprites, places, dialogue, flags (TBS)

> **Since this was written:** the name tables described below are no longer shipped. `gsmap/names.py` reads names at runtime from the checkout (`en.po`, `flags.h`, `sprite_ids.h`, `item_table.c`, `scenes.s`, `scene_rules.s`). `gsmap/data` keeps only preview frames, free chest flags and our own walkability descriptions.

Source tree: `alchemy/` (read-only), English build `out/tbs-en`. Paths are relative to `alchemy/games/tbs/` unless they start with `out/` or `tools/`. **VERIFIED** means read in code or data, or checked by a script over every file. **INFERRED** means deduced and not proven. Generated data is in `docs/research/names/`. The scripts that produce it are copied to `docs/research/names/scripts/`; the originals and the intermediate files are in the scratch directory `(a scratch folder)`.

## Summary

1. **Collision codes** come in three groups: global engine meanings, scene triggers, and markers. (VERIFIED)
   - **Global meanings:**
     - 0 floor
     - 240/241 encounter ground
     - 242..247 fixed empty search spots: jar, barrel, box, grave, books, well
     - 249 chain-jump
     - 250 hazard
     - 251 Cloak shadow
     - 252 ledge
     - 253 climb
     - 254 jump gap
     - 255 wall
   - **1..239 are scene triggers.** Their meaning comes from the scene's event tables: an exit, a touch script, or a search.
   - **Markers (chests and stones) can only use 100..239.**
   - The editor should name 1..239 per map from the events. `collision_by_map.json` (scratch) is that legend, already resolved: for exits, the target place; for scripts, the script name; for searches, the item or text.
2. **Items:**
   - Name = message `MsgItemName` (386) + id.
   - Icon = `items.tsv` column `icon` → `graphics/ui/menu_icons/item_{icon:03d}.png` (16×16, embedded palette).
   - Chest value = `FIND_ITEM(id)` = `0x100000|id`, `FIND_COINS(n)` = `0x200000|n`, mimic = `0x500000|slot` (slots 0..7), or `FIND_PSYNERGY_STONE` = `0x300000`.
   - (VERIFIED)
3. **Sprites:**
   - The placement sprite id is used directly as the row of `graphics/sprite/sprites.tsv` (513 rows).
   - Its graphics are `graphics/sprite/spr_NNN.png`, a vertical strip of w×h frames drawn with the shared 224-colour OBJ palette.
   - The preview frame is animation 1's first frame plus the facing offset.
   - 249 ids are covered, including all 219 used. 71 names are VERIFIED (decomp symbols and comments); 178 are INFERRED from the image and the scenes that use them.
4. **Places:**
   - `gScene_AreaNameRules` (`src/object/scene_rules.s:168`) gives each scene or group (optionally per entrance) an area index.
   - The text is message `MsgDebugEntryName` (2459 in EN) + index.
   - 199 of 201 scenes get a name. (VERIFIED)
5. **Dialogue:**
   - The `en.po` `msgid` is the zero-padded 5-digit message number. `msgctxt` is the symbol name, or `message` when the message has none.
   - A `SceneEvent` value below 0x10000 is a message number. Above that, it is a script; its lines are the `Msg*` symbols in its body.
   - A talk event's trigger is the actor number, which is 8 + the placement row.
   - (VERIFIED)
6. **Flags:**
   - There are 4,096 flags (0..0xfff).
   - New chests should take flags from **0xe00..0xfff**, using only flags no table, code or literal references. **251 are free** (`flags.json` `free_chest_flags`), the lowest being 0xe01, 0xe03..0xe0f, and so on.
   - Never use 0x200..0x3ff: those are scene and group temporaries that get reset.

---

## 1. Collision codes

### 1.1 Engine meaning (VERIFIED unless marked)

A cell's code is `struct MapCell.collisionCode` (`include/map.h:13-22`), read from the leader's layer (`terrainId`) window, one 16-px cell at a time.

| Code | Name (player-facing) | Engine behaviour | Evidence | Editor |
|---|---|---|---|---|
| 0 | **Floor** | Walkable. Uses encounter ground 0, which has no encounters unless the scene's location rule shift = 1 moves the first zone onto it. | `src/object/object/step.c:240-276`; `src/object/object/encounter.c:76-90`; `src/object/location_rules.s:1-7` | brush |
| 1..239 | **Trigger** (exit / event / search) | Stepping on the cell raises `work->action = code` (`step.c:247`). `Scene_RunTouchOrExit` first runs the scene's `EVENT_TOUCH` with that trigger (message or script); if there is none, it uses `EVENT_EXIT`, whose value is the exit kind (`events.c:333-380`). Pressing A on the cell ahead looks up `EVENT_SEARCH` with the same code (`run_scene.c:440-450`). `USE_ITEM` and `PSYNERGY_IN_AREA` events can also key on it. Any non-zero code also tests the exit regions (`step.c:244-245`). | as listed | trigger: named per map from events (§1.3) |
| 100..239 | **Chest / stone / search id** | Everything in 1..239, plus: this is the only range `Field_PlaceMapMarkers` accepts (`markers.c:57`). A `SEARCH(SEARCH_CHEST)` event shows a chest (object 20, `markers.c:70`); `FIND_PSYNERGY_STONE` shows a stone (object 28, `markers.c:105`). | | trigger; markers own these |
| 240 | **Monster ground** | Walkable. Encounters use `encounterGroups[1]`, the rule's first zone, instead of ground 0. Common as dungeon floor: 23 maps, e.g. map_009 (133 cells). | `step.c:22-23,264-267` | brush |
| 241 | Monster ground 2 | Like 240, but uses `encounterGroups[2]`. **No map uses it.** | `step.c:22-23` | brush (advanced) |
| 242 | Empty jar | When searched, says "checked the jar… but didn't find anything". Message offset 2 from `MsgTileChecked` (2344) and `MsgTileResult` (2376). Only fires when the ground ahead is 0..64 px above the leader. | `src/object/fxdata.c:22-31`; `events.c:439-448`; `run_scene.c:441-447` | brush |
| 243 | Empty barrel | offset 3 | same | brush |
| 244 | Empty wooden box | offset 13 | same | brush |
| 245 | Empty grave | offset 8 | same | brush |
| 246 | Bookshelf (books) | offset 30 | same | brush |
| 247 | Well | offset 31. Unused in maps. | same | brush |
| 248 | (unused) | No reader found, and no map uses it (INFERRED inert). | — | don't touch |
| 249 | **Stepping-stone hop** | Never raised by `Field_ProcessStep`. After a forward jump, landing on 0xf9 jumps again (chained hops). Used in 3 maps (029, 098, 148). | `events.c:383-405`; `src/object/psynergy_effects/climbing.c:18-23,99-103` | brush (advanced) |
| 250 | **Hazard ground** | While walking, the hazard step count rises, and at `hazardLimit` the party takes `hazardDamage`. The scene sets the mode, limit and damage. Maps 063-067. | `step.c:24,293-327` | brush |
| 251 | **Shadow (Cloak)** | Walkable. Cloak keeps the party hidden only on this code; leaving it ends Cloak (`CLOAK_TILE`). Maps 111 and 130-142 (Lunpa Fortress, Altmiller Cave…). | `src/object/psynergy_effects/cloak.c:7-11,71` | brush |
| 252 | **Ledge (jump down)** | Push against it for more than 12 frames while holding Down, and the leader jumps down. | `step.c:25-27,249`; `events.c:394-399` | brush |
| 253 | **Climbable wall / ladder** | Push for more than 12 frames: Up climbs, Down descends. While climbing, a step is allowed only into a cell with the same code. Arriving on two stacked 0xfd cells with y≠0 starts the party in climbing mode. | `events.c:407-415`; `src/field/field/player_control.c:874-881`; `src/object/object/actors.c:250-262` | brush |
| 254 | **Jump gap** | Push for more than 12 frames: the leader jumps 2 cells forward if the landing allows it (`Field_TryJumpForward`). 77 maps. | `events.c:400-405`; `climbing.c:13-30` | brush |
| 255 | **Wall** | Always blocks (`Map_CheckObjectStep` returns 2). | `src/field/field/terrain.c:477,526` | brush |

Walkability also depends on height. A step more than 8 px up or more than 12 px down is refused (`terrain.c:494-497`), so a "floor" code on a cliff is still blocked. The walkability overlay should combine the code with `grid_shape` heights. Water is **not** a collision code in TBS local maps: it is wall or height, and puddles and the like are scene triggers (INFERRED from the histogram: no dedicated code).

Codes on cells are also changed at run time by scene code (`SetMapCellCollision`, `terrain.c:422`), in Colosso, Altin Peak, Crossbone Isle, Venus Lighthouse, Tolbi and Sol Sanctum. Codes 96..99 in maps 078-083 (Altin Peak) have no static event, so they are read by script (INFERRED).

### 1.2 Usage histogram (VERIFIED by `coll_hist.py`, 182 maps, cells in the 3 layer windows)

| Code | Cells | Maps | Note |
|---|---|---|---|
| 0 | 1,300,642 | 182 | floor |
| 255 | 47,077 | 151 | wall |
| 240 | 4,308 | 23 | monster ground (dungeons/forests: 009, 016, 025-030, 043, 046, 050, 055, 056, 062, 064, 066, 067, 078, 133, 136, 137, 164, 166, 167) |
| 21 | 4,244 | 34 | e.g. Lamakan Desert map 091: 2,677 cells of `EVENT_TOUCH 21 → HeatGauge_CountStep` |
| 251 | 1,729 | 9 | Cloak shadow |
| 10 / 30 / 11 / 1 / 2 | 963 / 683 / 357 / 340 / 255 | 96 / 23 / 78 / 150 / 140 | low codes are mostly exits and door touch scripts |
| 254 / 253 / 252 | 928 / 484 / 59 | 77 / 60 / 28 | jump / climb / ledge |
| 243 / 244 / 242 / 245 / 246 | 500 / 482 / 388 / 32 / 18 | 29 / 29 / 28 / 6 / 3 | empty barrels/boxes/jars/graves/books |
| 100..107 | 100, 67, 37, 21, 8, 5, 3, 4 | 95..3 | chests (`SEARCH_CHEST` 66× on 100) and other searches |
| 200..212 | 2..35 | 14..1 | non-marker search spots (hidden items in jars/barrels…) |
| 250 | 77 | 4 | hazard |
| 249 | 3 | 3 | hop |
| 241, 247, 248 | 0 | 0 | unused |

The event kinds behind 1..239 across maps (count = maps): code 1 → EXIT 130, TOUCH 44; code 10 → TOUCH 65, EXIT 36; 100 → SEARCH_CHEST 66, SEARCH 36. Full table: `coll_hist.json` (scratch). 136 (map, code) pairs in 1..239 have **no** static event in the scenes using the map. They are used by scripts or left over: show them as "Scripted / unknown".

### 1.3 Per-map legend (VERIFIED, generated)

`collision_legend.py` writes `collision_by_map.json` (scratch, 1 MB). For each map it gives:
- `scenes`;
- `cells_per_layer`, a code histogram for each layer window;
- `events_by_code[code]`, a list of `{scene, table, kind: exit|touch|search|use_item|raised, control, condition, …}`, where:
  - an exit has `exit_kind, to_scene, to_entrance, to_name, to_symbol`;
  - a script has `script` (the ELF symbol, e.g. `Event_EnterSanctum`, `HeatGauge_CountStep`);
  - a message has `message, text`;
  - a search has `search_target` (one of the 32 `SearchTarget` names, `include/field_scene.h:176-209`), `marker_chest`, and `find_item/item_name | find_coins | psynergy_stone | mimic_slot`;
  - a touch has `needs_push` (0x200) and `needs_facing` (0x400).

The label rule for the UI is:
- "Exit → {to_name}"
- "Event: {humanized script}"
- "Chest: {item}"
- "Search {target}: {item | text}"

When there is no event, the label is "Unused trigger". Several tables per scene are chosen by story flags, so the UI should show the union and mark it "depends on story".

**Editor data:** `names/collision.json` (generated by `collision_json.py`):
```json
{"notes":[...],
 "ranges":[{"lo":0,"hi":0,"name":"Floor","category":"walk|block|move|search|trigger|unknown",
            "editor":"brush|trigger|trigger (markers own 100..239)|brush (advanced)|don't-touch",
            "meaning":"...","evidence":["src/...:lines"],"confidence":"VERIFIED","color":"#rrggbbaa"}],
 "codes":[{"code":240,"hex":"0xf0","range":"240-240","cells":4308,"maps":23}]}
```
Plus a per-map legend generated at load time, in the shape of `collision_by_map.json` (`{map: {scenes, cells_per_layer[3]{code:count}, events_by_code{code:[event…]}}}`). The editor should build it at run time from the built overlays (gsmap `Scenes`) rather than ship it.

Brush palette for players: Floor, Monster ground, Wall, Ledge, Climb, Jump gap, Shadow, Hazard, and Empty jar/barrel/box/grave/books. Triggers (1..239) are never painted freely. They are created by actions such as "add door" or "add chest", which allocate a code unused on that map (and below 100 for non-markers).

---

## 2. Items

- **Ids and symbols.** `include/item_ids.h` names only the ids the code uses (VERIFIED). The item table `src/game/items.tsv` has one row per id (id = line − 2, 324 rows), a `label` column with the English name, and the columns price, type, flags, equip_mask, icon, … The struct is `ItemDefinition`, 0x2c bytes (`include/game/item.h:104-137`).
  - Types: 0 none (consumable/key), 1 weapon, 2 armor, 3 shield, 4 helm, 5 boots, 6 Psynergy item, 8 ring, 9 shirt (`item.h:43-55`).
  - Flags: 1 cursed, 2 can't unequip, 4 rare, **8 indispensable (key item)**, 0x10 stackable (`item.h:26-32`).
- **English name** = en.po message `MsgItemName + id` = **386 + id** (`item_ids.h:7-8`, en.po:1579; used at `src/shop/shop/buy.c:350`, `src/window/window/decode.c:541`). Strip the `{article_class:N}` prefix. Only ids 0..268 have names: 655 is `MsgEnemyName`. Description = `MsgItemPlainName` (117) + id (`buy.c:68`). Checked: 1 Long Sword, 180 Herb, 181 Nut, 268 Cleric's Ring (VERIFIED).
- **Icons.** `src/graphics/ui/menu_icons/item_000.png`..`item_254.png`: 16×16 indexed PNGs, each with its own 16-colour palette, index 0 transparent. Pointer table: `gUiIcon_ItemIconPointers` (`src/graphics/ui/menu_icons.s:4-261`). An item's icon = `items.tsv` `icon` (`ItemDefinition.icon`, `item.h:109`), drawn by `ItemIcon_Compose` (`src/window/window/icons.c:114`); an index ≥ count becomes 0 (`icons.c:63-64`). Herb → icon 117, Nut → 132.
  - **Atlas rule:** icon k at (k%16·16, k//16·16) in a 256×256 sheet.
  - The atlas was built and checked by eye (scratch `items/item_icon_atlas.png`, `items/item_preview.png`): swords, armor, Herb leaf, keys and orbs all match their names.
  - JA-only variants `item_080_ja`/`item_098_ja` are not used by EN.
  - INFERRED: the in-game palette equals the PNG's embedded one.
- **Chest values** (`include/field_scene.h:211-214`; `Field_SearchTile`, `src/object/object/events.c:429-560`), VERIFIED:
  - `value & 0x0f000000 ≠ 0` → a script (function pointer).
  - Else the type is `value & 0xfff00000`:
    - `0x100000` item: low half = item id; anything not 2/3/4/5 also takes the item path.
    - `0x200000` coins: `(u16)` → 0..65535; the game uses 1..999.
    - `0x300000` Psynergy stone: restores all PP.
    - `0x400000` message.
    - `0x500000` mimic: battle `Encounter_GetEnemyGroupAtSlot(99, slot)`. Zone 99 is "Mimic chests" (`src/object/encounter.tsv` line 101, groups 350..357). Only slots 0..7 are valid (`encounter.c:244`).
  - `(value & 0xf0000) == 0x10000` → "Can't open it" for the party (unused).
  - The event's `condition` is the opened flag: the chest is shown open while the flag is set, and the flag is set on taking the contents. If the party's bag is full the item stays and the flag stays clear (`events.c:565-590`).
  - Control `SEARCH(SEARCH_CHEST)` = 0x13. Bits 4..8 pick the "checked the X" line.
  - Survey of 155 marker chests: 130 items, 17 coins, 8 mimics (0x500000..0x500007, each once). No chest uses a Psynergy stone or a script.

**Editor data:** `names/items.json` (generated by `scripts/items/build_items.py`):
```json
[{"id":180,"symbol":"ITEM_HERB","symbol_in_header":true,"name":"Herb","description":"Replenishes 50 HP",
  "type":"none","type_id":0,"price":10,"flags":["stackable"],"key_item":false,"unused":false,
  "icon":117,"atlas":{"x":80,"y":112,"w":16,"h":16},"evidence":"items.tsv line 182; en.po msg 566"}]
```
The picker's output is `{"kind":"item","id":180}` → `FIND_ITEM(ITEM_HERB)` (0x1000b4), `{"kind":"coins","n":50}` → `FIND_COINS(50)`, `{"kind":"mimic","slot":0..7}` → `0x500000|slot`, or `{"kind":"psynergy_stone"}` → `FIND_PSYNERGY_STONE`. Hide entries with `unused` (name "?"/"???"/none) and flag `key_item` entries with a warning. The atlas is built at run time from the player's alchemy checkout, never shipped.

---

## 3. Sprites / NPCs

- **Id → object** (VERIFIED):
  - `Event_SpawnObjectTable` (`src/object/object/actors.c:97-118`): ids 0-7 = party slots, and `Party_RemapCharacterIdByFlags` (`actors.c:12-36`) swaps child sprites 0x12/0x13 under `FLAG_CHILDHOOD`. Other ids take actor slots 8+ in row order (actor = 8 + row).
  - Then `Object_CreateFar(id)`, select animation 1, and set the angle from `facing`.
  - `FieldObject_Create` (`src/field/field/objects.c:245-290`): `id>>12` is the kind. Kind 0 = one sprite `id & 0xfff`; kind 2 (0x2000|n) = a two-sprite group n, n+1; other kinds have no sprite, e.g. 0x8000 = camera (`actors.c:266`).
- **Sprite table:** `gCharacter_DescriptorTable[id & 0xfff]` (`src/system/resource/metadata_get_record.c:7-9`) comes from `src/graphics/sprite/sprites.tsv` (513 rows; row = id; columns width, height, scale, drawKind, adjust, box, codec, frames, animations). Width 0 = no image (`src/field/field/animation.c:512`).
- **PNG rule** (`tools/ags-graphics/sprite.c:120-160,295-330`):
  - `graphics/sprite/spr_NNN.png` of the frames-owner row; an alias row is written `SPR_X=SPR_Y`.
  - The sheet is a vertical strip, with frame k at y = k·height. An optional `spr_NNN.tsv` `list` remaps frames, and its `anim` lines are the animations.
  - Palette: 8bpp, using the shared 224-colour `gSystem_BasicColorPalette` (`src/runtime/runtime/text.c:199`), which is embedded in every PNG, with index 0 transparent.
- **Preview frame:** animation 1's first frame command (values < 239 are frames; 240 sets the draw kind; 254 jumps to another animation; `src/field/field_internal.h:83-91`), plus the facing offset for that draw kind (`src/field/facing.c`, applied in `src/field/field/sprite_draw.c:150-185`; bit 7 = mirrored). Use facing 0x3800 for a straight front view. At exactly 0x4000, kinds 3 and 5 draw base+0 mirrored.
- **Special ids:**
  - 20 treasure chest (VERIFIED, `markers.c:70`).
  - 28 Psynergy stone (VERIFIED, `markers.c:105`).
  - 22 invisible 16×16 marker, used 68× for counters and item spots.
  - 4 and 7 have empty rows.
  - 261-279 and 504 are world-map icons.
  - Placement tables use ids 0..504.
- **Names.** There is no global sprite enum. Names come from:
  - `include/game/character_ids.h`;
  - file-local `SPRITE_*` enums (`src/scene/lunpa.h`, `vault_jail.c`, `tunnel_ruins.c`, `altin.c`, `altin_peak.c`, `tret_tree_*.c`, …);
  - row comments.

  That gives 71 VERIFIED names. The other 178 are INFERRED from the image and the scenes using the id (e.g. "Townsperson A", "Dog"); `name_evidence` says which.
- The contact sheets were checked by eye: correct front frames and colours, no garbage. They are `sprites/contact_sheet_npc60.png` and `sprites/contact_sheet_all.png` in scratch.

**Editor data:** `names/sprites.json` (generated by `scripts/sprites/build_sprites.py`, using `spritelib.py`, `usage.py`, `names.py`, `names_manual.py` and `sheet.py`):
```json
[{"id":28,"hex":"0x1c","name":"Psynergy Stone","confidence":"VERIFIED","name_evidence":"...",
  "usage":1,"scenes":["MogallForest1"],"party_slot":false,"has_image":true,
  "png":"games/tbs/src/graphics/sprite/spr_028.png","frame":{"x":0,"y":0,"w":16,"h":16},
  "frame_index":0,"mirrored":false,"palette":{...},"draw_kind":11,"animation":1,"base_frame":0,
  "sheet_frames":11,"scale":256,"adjust":[0,2],"box":[20,16],"evidence":"sprites.tsv row 28 ..."}]
```
The UI crops `png` at `frame` (mirrored if set) at run time. An "edit name" override file on the editor's side is recommended for the INFERRED names.

---

## 4. Place names

- `Scene_GetAreaNameIndex(scene, entrance)` (`src/object/object/encounter.c:326-350`) walks `gScene_AreaNameRules` (`src/object/scene_rules.s:168-301`). Each row is `scene_name Scene, entrance, index` or `group_name group, entrance, index` (`scene_rules.s:12-20`). The **first** matching row wins; entrance -1 matches any entrance. Group = `gField_SceneTable[scene].group` (`src/object/object/scene.c:157-159`; the column in `src/field/scenes.s`). No match gives index 0. (VERIFIED)
- Text = message **`MsgDebugEntryName` + index** (`src/object/psynergy_effects/world_map.c:400`, `src/window/battle_command/debug.c:23`). In EN, `MsgDebugEntryName` = 2459 = `RENDER_RESOURCE_BASE` 0x99B for patched non-European editions (`include/tbs_edition.h:264-271`, used by `src/window/window/shortcuts.c:29`). Read the base from en.po's `msgctxt "MsgDebugEntryName"`, not as a constant. (VERIFIED)
- `.if EDITION_INTERNATIONAL` rows (Altin Peak 4, entrances 6/7) are on for EN (`include/game/ed_asm.h:11-16`).
- Result:
  - 199/201 scenes get a name; Title (0) and LinkLobby (190, named only for entrance 1) do not.
  - 21 scenes have no `scenes.s` symbol, so they are labelled "Scene N" plus their area name.
  - Entrance-specific names exist, e.g. Sanctum: 1/2/20/21 Vale Sanctum, 10-12 Vault Sanctum, 35 Bilibin, 32 Xian, 29 Altin; VaultJail entrance 2 = "Lunpa".
  - Display: "{area_name} — {label}", e.g. "Vale — Vale Home". Area names repeat across many scenes, so the scene label disambiguates.

**Editor data:** `names/places.json` (generated by `scripts/places.py`):
```json
{"area_message_base":2459,
 "scenes":[{"id":5,"symbol":"ValeHome","label":"Vale Home","group":3,"variant":2,"overlay":"0x374",
            "layered_row":4,"map":"003","area_index":10,"area_name":"Vale",
            "area_name_by_entrance":{},"area_message":2469}]}
```

---

## 5. Dialogue

- **en.po scheme** (VERIFIED). Each entry is `msgctxt "<symbol>|message"`, `msgid "NNNNN"` (the message number, zero-padded to 5 digits), and `msgstr` (text). There are 10,723 entries, 0..10722, with no gaps. The symbols come out as `out/tbs-en/text/msg_ids.h` (`#define TEXT_MESSAGE_NUMBER_<Sym> n`, `MSGNO(name)`). Scene C writes `MSGNO(MsgX)` in tables and bare `MsgX` in code (`src/scene/README.md:60-61`).
- **Text markup:** `{page_break}` (new box), `{end_wait}` / `{end_now}` (end), `{line_break}`, and arguments `{protagonist_name}`, `{actor_name:N}`, `{argument_item_name:N}`, `{text_color:…}`, `{article_class:N}` (`tools/ags-text/symbols.c:28-60`). A literal `\n` is a display line. Render the names as placeholders like "[Isaac]".
- **Talk lookup** (`Scene_TalkToActor`, `src/object/object/events.c:197-290`; `Scene_FindEvent` `:111-165`):
  - Kind 0 `EVENT_TALK`, with trigger = actor id = 8 + placement row.
  - The first row whose condition holds wins (-1 always; `flag|0x1000` = set; else clear), so an NPC can have several rows chosen by story flags.
  - `value < 0x10000` → one message. All 881 direct talk messages end in `{end_*}` (survey), so one id is the whole speech.
  - Otherwise the value is a script. Kind 7 is the line said when the party has stopped the actor (`events.c:175-186`).
  - `talkFacing` controls turning.
- For scripts, the dialogue is the `Msg*` symbols in the function body. Example: `Event_TalkAboutTheMayorAndTremors` (`src/scene/vale.c:160`) shows `MsgValeTheGroundStillShakes` or `MsgValeYourGrandpaIsTheMayor` depending on `FLAG_PARTY_LEFT_VALE`. That gives a list of possible lines, not their order or conditions (INFERRED adequate for previews).
- Search spots show `MsgTileChecked + target` and then the `FIND_MESSAGE` or result text (`events.c:452-470`).

**Editor data:** `dialogue.json` (scratch, 650 KB, generated by `scripts/dialogue.py`; 152 scenes, 2,475 talk rows). It contains game text, so the editor generates it at run time:
```json
{"4":{"symbol":"Vale","tables":{"gVale_Events":[
  {"actor":8,"placement_row":0,"kind":"talk|talk_paused","condition":null|{"flag":2069,"when":"set|clear"},
   "message":3967,"msgctxt":"MsgValeMtAlephLooksBeautifulTodayIts","text":"Mt. Aleph looks\nbeautiful today..."},
  {"actor":10,"placement_row":2,"kind":"talk","condition":null,"script":"Event_TalkAboutTheMayorAndTremors",
   "source":"src/scene/vale.c","script_messages":[{"message":4556,"text":"..."}]}]}}}
```
Editing text means editing `text/en.po` `msgstr` by msgid. The other 5 language catalogs must keep the same msgid set (`src/game/README.md:97-110`).

---

## 6. Flags

- **Storage:** 4,096 bits in `gGameFlagBytes`. Bits 0-2 of the flag number pick the bit and bits 3-11 the byte (`src/game/game/flags.c:7-24`, `include/game/game_flags.h:12`). Byte accessors treat 8 consecutive flags as one counter (`src/game/README.md:110-121`). All of them are saved (README; save checksum covers `gGameFlagBytes`, `include/save_state.h:55`).
- **Conditions:** `-1` always, `flag|0x1000` = set, otherwise the flag is clear. 0 on a placement = "in view" (`events.c:59-77`).
- **Ranges** (`src/scene/README.md:48-59`, `include/flags.h:7-20`):
  - 0x000-0x0ff: party (0-7) and Djinn (48-127).
  - 0x100-0x1ff: engine/system.
  - **0x200-0x2ff: scene temporaries, cleared on every entrance.**
  - **0x300-0x3ff: group flags, reset on entering another group, numbers reused per place.**
  - 0x400-0x7ff: no use found (one reference, 0x400; INFERRED unused, but avoid).
  - 0x800-0xdff: story.
  - 0xe00-0xfff: chest/find flags.
- **Naming:** `include/flags.h` (970 lines) `#define FLAG_* value` with `///` comments, e.g. `FLAG_ALTIN_PEAK_LUCKY_MEDAL 0xf78 ///< room 8's chest`. Scene-local flags are `#define`d in the scene's own file and are not in flags.h.
- **Usage survey** (`flags_survey.py`, VERIFIED to the extent of its sources):
  1. Every condition, requiredFlag, exit flag and region condition in the built overlay tables.
  2. Every flag-accessor call with a constant argument in `clang -E` output of each `src/**/*.c`. The output goes to stdout only and alchemy is not touched.
  3. The flag fields of `scene_cue`/`group_cue`/`location` rows in `scene_rules.s` and `location_rules.s`.
  4. All flags.h defines.

  Found in use: 0xe00-0xfff 213/512; 0x800-0xdff 300; 0x300-0x3ff 108.
- **Conservative free list** (`flags_free.py`): additionally excludes any 0xe00..0xfff value (or its 0x1e00 condition form) that appears as a hex literal anywhere in `src`/`include`, outside graphics and map data. That leaves **251 free** flags. Runs: 0xe03-0xe0f, 0xe49-0xe58, 0xe61-0xe73, 0xe81-0xea1, 0xef8-0xeff, 0xf09-0xf12, 0xfdb-0xfe0, … (`flags.json` `free_chest_flags`).
- **Allocation rule for a new chest:**
  1. Take the lowest flag in `free_chest_flags` that is not already used by the mod's own override tables (`games/tbs/src/mod/`) or by other pending edits.
  2. Write it as the `SEARCH(SEARCH_CHEST)` event's condition.
  3. Record it in the mod manifest so it is never reused, even after the chest is deleted (old saves may have it set).
  4. Re-verify on every alchemy pin bump by rerunning the survey; the free list is a function of the commit.
- **Check that a flag is unused**, in this order:
  1. It is not in `used` of a fresh `flags_survey.py` run (tables + code + rules).
  2. There is no hex literal match (`flags_free.py`).
  3. It is not in the byte of any byte-accessor flag (the survey marks all 8).
  4. It is not in 0x200-0x3ff.
  5. After building, `grep` the overlay `.bin` for the halfword is **not** reliable (false positives), so rely on 1-4.

**Editor data:** `names/flags.json` (generated from the two scripts):
```json
{"total_flags":4096,
 "ranges":[{"lo":3584,"hi":4095,"meaning":"chest / find flags","editor":"allocate new chest flags here"}],
 "names":{"0xf78":["FLAG_ALTIN_PEAK_LUCKY_MEDAL"]},
 "used":{"0xf78":["flags.h","table 3a4:gAltinPeak_Events..."]},
 "free_chest_flags":[3585,3587,...]}
```

---

## Generated files and how they were made

All scripts are in `names/scripts/` (copies) and in the scratch dir above. They depend on gs-mapedit's `gsmap` (Project, Scenes, grid) and on `out/tbs-en`.

| File | Script | Inputs |
|---|---|---|
| `names/collision.json` | `collision_json.py` (after `coll_hist.py`) | engine reading above; histogram over `src/map/*/grid_collision.tsv` |
| scratch `collision_by_map.json` | `collision_legend.py` | grids + built event/exit tables + `places.json` + `items.json` + en.po |
| `names/items.json` | `items/build_items.py` | `src/game/items.tsv`, en.po, `item_ids.h`, `graphics/ui/menu_icons/` |
| scratch `items/search_events.json` | `items/survey_chests.py` | built event tables |
| `names/sprites.json` | `sprites/build_sprites.py` (+ `spritelib.py`, `usage.py`, `names.py`, `names_manual.py`, `sheet.py`) | `graphics/sprite/sprites.tsv`, `spr_*.png`/`.tsv`, built placement tables, scene sources |
| `names/places.json` | `places.py` (+ `po.py`) | `src/field/scenes.s`, `src/object/scene_rules.s`, en.po, `layered.tsv` via gsmap |
| scratch `dialogue.json` | `dialogue.py` | built event tables, overlay ELF symbols, `src/scene/**`, `out/tbs-en/text/msg_ids.h`, en.po |
| `names/flags.json` | `flags_survey.py` → `flags_free.py` → inline merge | built tables, `clang -E` of `src/**/*.c`, rule `.s` files, flags.h |

Images (icon atlas, contact sheets) and game text are deliberately not committed; per PRODUCT.md's legal posture the app builds them from the player's checkout.

## Unknowns

- What 248 means (no reader, unused), and whether 241 works as expected (no map uses it).
- Codes 96..99 (Altin Peak) and 136 (map, code) pairs in 1..239 have no static event. They are presumably read by scene code (`GetMapCellCollision` callers) or are leftovers.
- Collision meaning on the **world map** is a separate system (`blocks.tsv` step byte, `attributes.tsv`): see `overworld.md`.
- `touched_trigger` writer, and the event control high bits on 22 chests (0x400, 0x8400, 0xc400). Bit 0x400 of the *trigger* skips the "checked" line; the meaning of the control bits is not confirmed.
- The in-game palette slot for item icons (the PNG palette is assumed).
- The 178 INFERRED sprite names. Some are guesses (e.g. 44 "Dodonpa", 66/67, 69 "Lady Layana"). The 0x2705 actor-index cutoff is marked XXX in source. JA/IT use `spriteja.tsv`/`spriteit.tsv`.
- Whether a message without `{end_*}` runs on into the next id. No direct talk message lacks one, so it doesn't matter for previews.
- The flag survey misses flags reached only through variables or computed expressions (5,191 non-constant accessor calls, including definitions and loops) and flags in C data arrays. The hex-literal pass covers most of these; 0x400-0x7ff looks unused but is not proven.
- Whether the mimic slot can exceed 7 safely (it reads into the next zone, so it is not useful).
