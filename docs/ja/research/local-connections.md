<!-- translated from docs/research/local-connections.md @ 9ab200ba52b5 -->
# ローカルマップ: どうつながり、何が置かれるか（TBS、TLA の補足つき）

*これは英語版 [local-connections.md](../../research/local-connections.md) の翻訳です。両者が異なる場合は英語版が最新です。*

ソースツリー: `alchemy/`（読み取り専用）。以下のパスは、`games/`、`tools/`、`out/` で始まるものを除き `alchemy/games/tbs/` からの相対パスです。「検証済み」（VERIFIED）= コードやデータで読んだ、またはスクリプトですべてのファイルを確認した。「推定」（INFERRED）= 推論したが証明していない。

## 概要

1. **シーン** は `gField_SceneTable`（`src/field/scenes.s`）の1行です: オーバーレイのリソース id、グループ、変種、**レイヤードマップの行**。シーン id は行番号です。201 行。（検証済み）
2. マップの行は `gMap_LayeredScenes`（`src/field/layered.tsv`、186 行）を指します。各行は `ResourceId_Map001` からのリソースオフセットを 6 個持ちます: マップヘッダー、パレット、タイルシート 3 枚、レイヤーデータ。つまりシーンテーブルはマップ**と**タイルセットを一緒に選び、行番号は `map_NNN` の番号では**ありません**。（検証済み）
3. 各オーバーレイのコード（`scene/<place>.c`）は、6 つの入口ベニヤを通して 5 つのテーブルを返します: Entrances、Exits、Placements、Events、Regions、そして Initialize。ゲッターはフラグやシーン id でテーブルを選び分けることがあります。（検証済み）
4. **出口はイベントを通して働きます。** セルの衝突コード（1..239）が `EVENT_EXIT` イベント（値 = 出口の種類）に一致するか、触れたときのイベントのスクリプトが `Engine_EventRequestExit(kind)` を呼ぶか、エリアの箱が適用されます。その後、出口テーブルが (現在のシーン, 種類) を (シーン, 入口) に対応させます。（検証済み）
5. 到着時、`entrance` が一致し、フラグが立っている（または -1 の）最初の `SceneEntrance` 行がパーティーを配置し、カメラを制限します。一致する行がなければ行 0 を使います。（検証済み）
6. **マーカー**（`markers.tsv`: x、z、id）は宝箱とエナジーストーンの位置です。417 個のマーカーすべてで、id はセルの衝突コードと等しくなっています。マーカーの中身は、そのトリガーを持つシーンの `SEARCH` イベントから決まります。（検証済み）
7. **NPC** は `ScenePlacement` の行です。アクター番号 = 8 + 行番号で、行の条件を満たすかどうかに関係ありません（シーンの README は違うことを書いています）。位置は 16.16 です。2,321 行のうち 396 行は (0,0) にあり、コードで位置が決まります。インラインの `Engine_ActorSetPosition` 呼び出しは 405 個あります。（検証済み）
8. つながりのテーブルはすべて、リテラルとマクロからなるファイルスコープの素の C 初期化子です。ツールがその場で編集し、`#if` ブロック、シンボル名、`const` を保てば、どれも書き換えられます。出口ワードのシーン id は**数値リテラル**です。コード中では `(s32)&SceneId_X` のリンカーシンボルです。（検証済み）
9. TLA は、マップごとの入口、点、カメラ範囲を 7 番目のマップブロック（`scene_*.tsv`）に持っています。そのオーバーレイの大半は1行だけの `SceneEntrance` を持ちます。これはエンジンの違いなので、TBS が同じファイルに移ることはできません。（配置は検証済み、意味は推定）
10. 新しいマップやシーンを追加するには、25 個の `unused` のディレクトリ枠を使い、シーンテーブルとレイヤードテーブルに行を追加します。固定のバンクアドレスと、**エディションごとに約 3.5–43 KB の ROM の空き**（8 MB の詰め物）が絶対的な制限です。（検証済み）

---

## 1. シーン ↔ マップの接続

### 1.1 シーンテーブル（検証済み）

`src/field/scenes.s:1-9`:

```
.macro scene name, code, area, kind, map
  .equiv SceneId_\name, (. - gField_SceneTable) / 8   ; id = row index
  .2byte \code   ; overlay resource id (= directory index, 0x36f..0x3ce)
  .byte \area, \kind  ; group, variant
  .2byte \map, 0      ; gMap_LayeredScenes row, reserved
```

- `struct SceneRecord` は `include/field_runtime.h:18-26` にあります: `resourceId, group, variant, mapIndex, reserved`、8 バイト。
- テーブルは 201 行です（スクリプトで数えた）。名前のない行（`scene , 0x376, ...`）には `SceneId_` シンボルが付きません。
- `Game_ResetForNewGame`（`src/object/object/scene.c:204-289`）は `record = &table[gGameState.scene]`、次に `gGameState.map = record->mapIndex`（`:286`）、次に `Scene_LoadOverlay` → `Resource_LoadCode(table[scene].resourceId, &gOverlayArea)`（`:294-298`）、次に `Scene_TakeExit(Field_RunScene(entrance))`（`:288`）を行います。
- `group` の用途:
  - 音楽の規則と地名の規則（`src/object/scene_rules.s`。`src/object/object/encounter.c:279-345` の `Scene_ResolveInteractionResult` と `Scene_GetAreaNameIndex` が読む）。
  - グループが変わったときのフラグ 0x300-0x3ff の消去。
  - 「訪問済み」フラグ `(group & 0x7f) + 0x180`（`scene.c:344`）。したがってグループは 0x7f 以下でなければなりません。
- `variant` 2 は町を表します。歩数による PP 回復を止め、Retreat を使えなくします（`src/object/object/run_scene.c`、`sceneVariant == 2`）。
- 複数のシーンが1つのオーバーレイを共有できます。例えば Bilibin1/2/3 = 0x38b、AltinPeak1..11 = 0x3a4。それらは1つの `.c` ファイルも共有します。
- **C コード中のシーン id はリンカーシンボルです。** `scene_ids.h` は `extern char SceneId_X;` を宣言し、コードは `gGameState.scene == (s32)&SceneId_X` を比較します。これはリテラルプールのワードから読み込まれます。`src/scene/*.c` にこうした使用が 487 個あります。
- Run_scene はワールドマップを見分けるために `gGameState.map == (s32)&SceneId_Clear`（1 です）を比較します（`run_scene.c:45`）。（検証済み）
- **データテーブル中のシーン id**（出口ワード）は素の整数か、`include/field_scene.h:13-24` にあるいくつかの `enum SceneId` の名前です。シンボルではないので、番号を付け直しても追従**しません**。（検証済み）

### 1.2 マップの選択: レイヤードテーブル（検証済み）

`src/field/layered.s` は `.incbin "layered.table"` を行い、これは `src/field/layered.tsv` からビルドされます。列は `map0..map5:u16` で、186 行あります。オブジェクトは `rom_main_01` に置かれます（objects.tsv:59）。

`struct LayeredSceneEntry { u16 resources[6]; }` は `src/field/field/map_layers.c:164` にあります。`Map_LoadLayeredScene(index)`（`:211`）は 6 つのリソースを次のように使います:

| 列 | リソース | 使い方 |
|---|---|---|
| [0] | マップヘッダー | `Resource_GetTableEntry(resources[0] + ResourceId_Map001)`（`:233`） |
| [1] | パレット | 展開される。色 0（背景色）は保たれる（`:337`） |
| [2] | タイルシート | キャラブロック 1（`:345-357`） |
| [3] | タイルシート | キャラブロック 2 |
| [4] | タイルシート | キャラブロック 3 |
| [5] | レイヤーデータ | `gMapLayerData` に展開される |

値はすべて `ResourceId_Map001` からのオフセットです。ディレクトリのマクロを展開すると名前で解決できます（作業用スクリプト）:

- 行 0 と 1 は `Field_Map001` + `Blank*` です。Title、Clear、WorldMap が使いますが、ワールドマップの経路ではこれらは読み込まれません。
- 行 2 は `Field_Map000` + `Set00{Palette,TilesA-D}`。
- 行 5 は `Field_Map004` + `Set03*`。
- 行 12 は `Field_Map010` + Set09 のパレット/A/B/C + **Set08TilesD**。

186 行のうち 123 行は、連続した 6 つのリソースではありません: 1つの行が異なるセットのシートを混ぜることがあり、色違いはシートを再利用します。したがってエディタは、行を 6 つの独立した参照として扱わなければなりません。

`map_NNN/` は `Field_MapNNN` にちなんだ名前です（ディレクトリの番号付け。`src/map/README.md` の "The map numbers are the directory's"）。例えば、シーン ValeHome（id 5）は mapIndex 4 → `Field_Map003` = `src/map/map_003/` です。そのマップの `markers.tsv`（13,44,100）は、ValeHome のトリガー 100 の `SEARCH(...)` イベント（`src/scene/vale_home.c`、events）と一致します。

2つのマップは番号の代わりに地名を持ちます: `gondowan_passage/`（`Field_GondowanPassage`）と `venus_entrance/`（`Field_VenusEntrance`）。参照される 182 個の異なるマップリソースのうち、8 個は複数のシーンで使われています。

### 1.3 リソースディレクトリ（検証済み）

`src/system/resource/directory.s` はマクロ `resource`、`group`、`area SET, sheets, maps...`、`recolor`、`overlays`、`unused` を持ちます（`:1-51`）。

- 項目の id はその**位置**です: `ResourceId_X = (. - Resource_DirectoryTable)/4`。
- `area SetNN, ABCD, mmm` は `Field_Mapmmm`、次に `Tileset_SetNNPalette`、次に `TilesA..D` を出力します。
- オーバーレイは最後に来て、`overlays 36F … 3CE`（96 項目、`:299-306`）、その後に `unused 25`（`:307`）が続きます。未使用の枠はそれぞれ `.4byte 0` です。
- `Resource_GetTableEntry(i)` は境界チェックなしの単なる `Resource_DirectoryTable[i]` です（`src/runtime/runtime/system.c:150-152`）。
- ディレクトリは `rom_tail_02` の先頭にあり、EN では 0x08320000 に**固定**されています（`main.ld` の最後の `ABSOLUTE`。`out/tbs-en/tbs-en.map:7353`）。
- `rom_tail_02` の順番で、マップデータ（`map_NNN/map.s`。所有するタイルセットのシートも含む）、次に `src/system/overlay/overlays` が続きます（objects.tsv:436-631）。
- オーバーレイの前にディレクトリ項目を挿入すると、それ以降のすべてのリソースの番号が変わります。それは scenes.s のオーバーレイ id（`0x36f`…）と、挿入位置より後のすべての `layered.tsv` のオフセットを壊します。`unused` の枠を使ってください: インデックス 0x3cf..0x3e7。（位置で決まるマクロからの推定。計算は検証済み。）

### 1.4 オーバーレイ: entry、import、objects.tsv、overlays.tsv、リンカー（検証済み）

`src/scene/README.md` と `src/system/overlay/overlay.ld` がオーバーレイを説明しています。

- **Entry**（`scene/entry/<place>.s`）は決まった順番の 6 行の `overlay_veneer` です: Initialize、GetEntrances、GetExits、GetPlacements、GetEvents、GetRegions。各ベニヤは `ldr r4; bx r4; .4byte target` です（`src/system/overlay.s:5-11`）。エンジンはこれを `struct SceneEntries`（`include/field_runtime.h:42-57`）として読みます: それぞれベニヤのワードと関数ポインター、48 バイト。エンジンは `gOverlayArea.entrances()` などを呼びます。
- **Import**（`scene/import/<place>.s`）は `.set overlay_imports,1`、次に C が呼ぶエンジンのルーチンごとに `.set import.NAME,1`、次に `.include overlay.inc` です。`overlay.inc` は約 405 行の `import NAME, TARGET` の、順序付きの元リストを持ちます。設定された行だけがスタブを出力します（`src/system/overlay.inc:9-25`）。オーバーレイ同士は呼び合えません。
- **objects.tsv** は各オーバーレイに `text` 行を順番に 3 つ与えます（`entry/<place>`、`<place>`、`import/<place>`）。最初の列 = 16 進のオーバーレイ id です（例 `374 text games/tbs/src/scene/vale_home`）。任意で `bss` 行が続くことがあります（`.bss COMMON`、または `src/system/overlay/ovl_<id>.s` からの `resource_<id>_overlay .bss`）。
- **overlays.tsv** は、bss 行を持つ 36 個のオーバーレイについて、`.bss` 出力セクションのヘッダー（例 `.bss ALIGN(16)`）を与えます。2つのうち片方だけが存在すると、`tools/ags-objects/ags-objects.c:165-205` が "bss header and rows disagree" で失敗します。
- **リンク。**
  - 各オーバーレイは `symbols.elf` に対して 0x2008000 にリンクされます（Makefile:209-219）。
  - オーバーレイの中では、オブジェクト順に、すべての `.text` が先、次にすべての `.rodata`、次にすべての `.data` が来ます（`ags-objects.c` の `render()` の各パス）。したがって `const` のテーブルは `.rodata` に、const でないものは `.data` に入ります。
  - イメージは `tools/ags-overlays` によって `resource_<id>.lz` に圧縮され、`src/system/overlay/overlays.s` に埋め込まれます（`Resource_Overlay36F: .incbin ...` とエディションごとの `PACKER:` の残りバイト）。
  - `Resource_LoadCode` がそれを `gOverlayArea` に展開し、Thumb の BL を修正します（`system.c:228`）。
- オーバーレイ領域は 32 KB で、コード + rodata + data + bss が収まらなければなりません。`out/tbs-en/overlays/*.map` で測ると、最大のものは 0x3b1 の 32,648 B（空き 120 B）、0x373 Vale の 30,764、0x3c8 の 30,732 です。（ビルド出力で検証済み。）

### 1.5 シーンをキーにするその他のテーブル（検証済み）

これらは `SceneId_` シンボルかグループを使うので、末尾に追加しても正しいままです:

- `src/object/scene_rules.s`:
  - `gScene_InteractionRuleTable`（音楽: `scene_cue` / `group_cue`）。
  - `gScene_AreaNameRules`（`scene_name` / `group_name`）。
  - `gParty_PairResolveRules`（`return_to`、全滅時の戻り先）。
  - `gBattle_BackdropScenes`。
- `src/object/location_rules.s` の `gBattle_LocationRules`: (シーン, 入口, フラグ) ごとのエンカウントゾーン。
- `src/scene/world_map.c` の `gWorldMapExits`（`SCENE_EXITS(2)`…）とその `EVENT_EXIT` イベント（44 個）: ワールドマップからローカルシーンへの入り方。

---

## 2. 出口と入口

### 2.1 `struct SceneEntrance`（24 バイト、`include/field_scene.h:54-70`）（検証済み）

| # | フィールド | 型 | 意味 |
|---|---|---|---|
| 1 | entrance | s16 | 出口ワードが指す入口番号。-1 でテーブル終了 |
| 2 | requiredFlag | s16 | -1、または**立っている**必要があるフラグ（素の `GameFlag_TestFar`、0x1000 のエンコードなし） |
| 3 | x | s16 | ピクセル |
| 4 | y | s16 | ピクセル（高さ。1520 行中 20 行で 0 以外） |
| 5 | z | s16 | ピクセル（マップの「下」方向） |
| 6 | facing | u16 | 1/65536 回転（`enum Facing`、0x2000 刻み） |
| 7 | unused1 | s16 | どこでも 0、読まれない |
| 8 | cameraLeft | s16 | ピクセル。-1 = マップヘッダーの範囲のまま |
| 9 | cameraTop | s16 | 同様 |
| 10 | cameraRight | s16 | 同様 |
| 11 | cameraBottom | s16 | 同様 |
| 12 | unused2 | s16 | どこでも 0、読まれない |

`Scene_ApplyEntrance`（`src/object/object/run_scene.c:461-505`）:

1. `entrance == gGameState.entrance && (flag == -1 || flag set)` を探します。何も一致しなければ**行 0** を使います。
2. `FLAG_KEEP_PARTY_POSITION` でなければ、`gGameState.x/y/z = value << 16` と `heading = facing` を書きます。
3. カメラの範囲を制限します。表示は最低 240×160 です。

189 テーブル / 1,520 行の統計:

- フラグを使う行は 3 行。
- カメラ範囲を設定する行は 1,023 行。
- 2つの未使用フィールドはどこでも 0。
- entrance 列は 21 行でシンボル定数。

### 2.2 出口が発動する仕組み（検証済み）

シーンから出る方法は3つあります:

1. **出口セル。** `Field_ProcessStep` がリーダーのセルの衝突コードを読みます（`src/object/object/step.c:240-249`）。
   - コード `1..239`（`STEP_EVENT_FIRST/LAST`、`:19-27`）は `work->action = code` を設定します。
   - `Scene_RunTouchOrExit(code)`（`src/object/object/events.c:333-385`）は、まず `trigger == code` の `EVENT_TOUCH` イベントを探します。あれば、そのメッセージかスクリプトを実行し、スクリプトはコードを引数として受け取ります。
   - なければ `trigger == code` の `EVENT_EXIT` を探します: 出口の効果音を鳴らし（control のビット 5..4: 0 通常、0x20 → SE_128 + 効果 26、0x30 → SE_129 + 効果 25、0x10 なし）、`work->exit = event.value`、つまり**出口の種類**を設定します。
2. **スクリプト。** 触れたとき/話しかけたとき/エナジーのスクリプトが `Engine_EventRequestExit(kind)` を呼びます。これは `Event_SetExitRequestFar` としてインポートされます（`src/system/overlay.inc:321`）。呼び出し箇所は約 200 個あります。典型的なドアは、ドアの衝突コードに `TOUCH_WALKING_INTO(FACING_NORTH)` を使い、ドアのセルをアニメーションさせ、リーダーを中へ歩かせてから出口を要求します（`vale_home.c:444-471`）。ドアのアニメーションの座標は**インラインの呼び出し引数**（`Event_OpenDoorAndWalkThrough(44, 7, 248, 279)`、`Map_CopyCellsTo(...)`）か、`u16 ...DoorCells[]` の `MAP_CELL_STEP(srcX,srcY,w,h,frames)` 配列（`include/field_event.h:59-61`）です。
3. **エリア。**
   - `struct SceneRegion`（`include/field_runtime.h:30-37`、16 B）は `minX,minY,minZ,maxX,maxY,maxZ`（ピクセル。min は含み、max は含まない）、`condition`、`value` = 出口の種類です。minX が -1 でテーブル終了。
   - リーダーのセルのコードが 0 でないときは常に `Field_CheckExitRegions`（`step.c:135-186`）が判定します。
   - エリアのテーブルは 14 個、38 行で、ほとんどのシーンは NULL を返します。

`Field_RunScene` は `work->exit` を返します。その後 `Scene_TakeExit(kind)`（`src/object/object/scene.c:25-89`）は:

- オーバーレイの出口テーブルをたどり、現在のシーン id と等しいヘッダーワードを探します。
- `kind == exitKind` か種類が `0xff`（任意）で、**かつ**フラグが立っていない最初の出口ワードを採用します（`SCENE_EXIT_IF`: フラグのワードが後に続き、**フラグが立っている間その出口は飛ばされます**）。
- 先に種類 0 のワードか終端（0x1ff）に達した場合は、最初の出口のシーンの入口 0 に戻ります。

### 2.3 出口ワードのエンコード（検証済み）

`include/field_scene.h:72-77`:

```
SCENE_EXITS(scene)              = scene                         // header
SCENE_EXIT(kind, scene, ent)    = kind<<20 | ent<<12 | scene
SCENE_EXIT_IF(k, s, e, flag)    = SCENE_EXIT(k,s,e) | 0x10000000, flag   // two words
SCENE_EXITS_END                 = 0x1ff
```

| フィールド | ビット |
|---|---|
| scene | 0..11（戻り先の処理は 9 ビットしかマスクせず、0x1ff が終端なので、シーン id は 511 未満でなければならない） |
| entrance | 12..19（0..255） |
| kind | 20..27（1..254 が実際の種類、0xff は任意、0 = **ヘッダー**） |
| フラグが続く | ビット 28 |

**`SCENE_EXIT(0, N, 0)` はシーンのヘッダーで、`SCENE_EXITS(N)` と同一です。** オーバーレイを共有するテーブルはこれを使います: `gAltinPeak_Exits`（`altin_peak.c:2671-2722`）は、1つの `SCENE_EXITS(77)` の後に 11 シーン分の出口リストを持ちます。スクリプトで調べると、オーバーレイを持つ 201 シーンのうち 200 シーンでヘッダーが見つかりました。ヘッダーがないのは名前のないシーン 59（オーバーレイ 0x39d）だけです。TLA はさらに、フラグのワードが -1 なら「常に」として扱います（`games/tla/src/field/common/take_exit.c`）。

### 2.4 `src/scene/*.c`（+ `common/*.h`）のテーブル一覧（スクリプトで検証済み）

| 種類（名前はまちまちなので**型**で見分ける: `gX_Exits`、`gXExits`、`gXExits1`…） | テーブル | 行 | 内部に `#if` があるテーブル | `const` |
|---|---|---|---|---|
| `struct SceneEntrance` | 189 | 1,520 | 0 | 5 |
| `u32` の出口テーブル（`SCENE_EXITS`） | 99 | 出口ワード 1,479 | 1 | 5 |
| `struct ScenePlacement` | 274 | 2,321 | 4 | 18 |
| `struct SceneEvent` | 263 | 5,891 | 10 | 13 |
| `struct SceneRegion` | 14 | 38 | 3 | 1 |
| ドア/セルのステップ配列（`u16` `MAP_CELL_STEP`、`u32` の詰め込みセル、`struct MapCellAnim`） | 約 10 | — | — | — |

行数で見たイベントの種類:

- `PSYNERGY_ON_ACTOR` 1585
- `EVENT_TALK` 1374
- `EVENT_EXIT` 903
- `EVENT_TOUCH` 531
- `SEARCH(..)` 506
- `TOUCH_WALKING_INTO` 493
- `0x31`/`0x21`（効果音ビット付きの出口）、`0xc4f3`、`0x8413` などの生の 16 進 control: 約 220

すべてファイルスコープの初期化済み配列で、1レコードにつき波かっこ1行です（出口: 1ワードにつきマクロ1つ。clang-format により1行に2つのこともある。例 `world_map.c:2802`）。ゲッターがそれらを返し、フラグやシーンで選ぶこともあります（`vale_home.c:104-160`、`bilibin.c:106-114`）。配置テーブルはほとんどが**const でない**です。`Scene_AssignViewFlags` が実行時に、condition が 0 の行の `condition` を書き換えるからです（`src/object/object/actors.c:325`）。

---

## 3. マーカー（宝箱、エナジーストーン）

- **形式**（検証済み）。`markers.tsv` はヘッダー `x:u8	z:u8	event:u8` を持ち、各行はセルの列、セルの行、id で、`0xff 0xff 0xff` の行で終わります。生のままエンコードされ（`markers.table`、LZ では**ない**）、6 番目のヘッダーブロックとして incbin されます（`src/map/map_004/map.s:25`）。値は 10 進でも `0x` の 16 進でもかまいません: `map_002/markers_es.tsv` は数値の書式だけが `markers.tsv` と違います。
  - マーカーファイルは 118 個です: 基本が 106 個、エディション別の版が 12 個（`*_ja/_de/_es.tsv`。map.s の `.ifdef TBS_EDITION_*` で選ばれる）。
  - 76 個の map.s ファイルは空の `map_000/markers.table` を指しています。
- **読み込み**（検証済み）。マーカーのリストは展開されません: `work->script = header + header->markers`（`map_layers.c:258`）。`run_scene.c:73` から呼ばれる `Field_PlaceMapMarkers`（`src/object/object/markers.c:30-131`）は次のことを行います:
  - 対象になるのは id **100..239** だけです。
  - それぞれについて、`trigger == id` の最初のシーンイベントを取ります:
    - `control & 0x1ff == 19`（`SEARCH(SEARCH_CHEST)`）: セルの中心 `(col<<20)+0x80000` にオブジェクト **20**（宝箱）を作り、地形に合わせます。イベントの条件フラグが立っていれば宝箱は開いた状態で表示されます（アニメーション 2）。フラグが立っていて値がミミック（`0x5xxxxx`）なら、まったく置かれません。
    - 値が `0x300000`（`FIND_PSYNERGY_STONE`）でフラグが立っていない、その他の `SEARCH`: オブジェクト **28**（ストーン）を作ります。
  - 置かれるのは最大 `MARKER_MAX` = 10 個です。一致するイベントのないマーカーは何も置きません。
- **id = 衝突コード**（検証済み）。TBS の 417 個のマーカー行すべてで `grid_collision[x,z] == id` です（作業用スクリプト）。調べる処理自体は、前方のセルの衝突コードをキーにします（`Scene_FindEvent(EVENT_SEARCH, code)`、`events.c:111`、`Field_SearchTile` `events.c:429`）。一致する衝突コードのないマーカーは、開けられない宝箱を表示してしまいます。**エディタは両方を書かなければなりません。**
- **中身とフラグ**（検証済み）。中身はシーンのイベントテーブルにあります: `{ SEARCH(SEARCH_CHEST), <id>, <opened-flag>, FIND_ITEM(ITEM_X) | FIND_COINS(n) | FIND_PSYNERGY_STONE | FIND_MESSAGE(m) | 0x5xxxxx mimic | EVENT_SCRIPT(fn) }`（`include/field_scene.h:118-217`）。
  - 条件は「開封」フラグです。README によれば、宝箱のフラグのほとんどは 0xe00 以上です。宝箱の中身を取るとフラグが立ちます（`events.c:500-560`）。
  - 値のビット 16 は「パーティーには開けられない」を意味します。
  - `SEARCH(SEARCH_CHEST)` の行は 135 個、`FIND_PSYNERGY_STONE` の行は 17 個あります。一部のストーンは名前付きの `TRIGGER_STONE` 定数を持つ `SEARCH_FACING(...)` の行を使い、一部のストーンは素のスクリプトです（ValeHome の `Event_UsePsynergyStone`）。
- コード 242..247 は固定の「調べる場所」のメッセージ、250 はダメージ床、252..254 は段差/よじ登りの場所です（`step.c:19-27`、`events.c:387-418`）。0xff は壁です。

---

## 4. NPC とオブジェクト

`struct ScenePlacement`（24 B、`include/field_scene.h:81-98`）（検証済み）:

| フィールド | 型 | 意味 |
|---|---|---|
| sprite | s16 | オブジェクト/スプライトの種類。0-7 = パーティーのキャラクター（専用の枠）、-1 でテーブル終了 |
| condition | s16 | -1 は常に。`flag\|0x1000` = フラグが立っている。それ以外はフラグが立っていない。0 = 「視界内」（`Scene_AssignViewFlags` が書き換える） |
| behavior | s32 | `ACTOR_STAND`=1、`ACTOR_WANDER`=2、小さな整数（例 3）、または `s32 ...[]` の SC_ 行動スクリプトへのポインター |
| x, y, z | s32 | `PIXELS(n)` による 16.16 ピクセル |
| facing | u16 | 1/65536 回転 |
| talkFacing | u8 | TALK_FACE_PARTY 0、_AND_BACK 1、KEEP 2、3 はリーダーを追う |
| flags | u8 | ビット 0 `PLACEMENT_SHARE_PREVIOUS_SPRITE` |

**生成**（`src/object/object/actors.c:75-180`、`ObjectTable_ResetForObject` `:217`）（検証済み）:

- リーダーが `gGameState` から生成され、次にテーブルが枠 8 から生成されます。
- **`actorIndex = slot++` は条件の判定より前に実行されます（`:105-107`）**。したがって飛ばされた行もその番号を使います: スプライトが 7 より大きい場合 **アクター = 8 + 行番号**。`EVENT_TALK` と `PSYNERGY_ON_ACTOR` のトリガーはこの番号を指すので、行を並べ替えたり挿入したりするとすべての話しかけイベントの番号が変わります。
- 高さ: ワールドマップ以外では、y が地形の高さに足されます。
- 配置できるアクターは最大 58 体です（枠 8..65）。
- ジンのフラグの行（48..127）は `condition+80` も必要です。

2,321 行の behavior 列の内訳: STAND 1,705、WANDER 132、整数 306、スクリプトのシンボル 178。

- 396 行は x=z=0 にあります。これらは Initialize のコードが位置を決めたり動かしたりするアクターです。
- インラインでの位置決めはよくあります:
  - `Engine_ActorSetPosition`: 405 回
  - `OBJ_POS_SET(no,x,z)`（ピクセル、`include/event.h:13`）: 119
  - `Engine_ObjectCreate(kind,x,y,z)`: 53、効果や追加のオブジェクト用
  - `Engine_ActorWalkTo`: 36

つまり NPC の静的な配置はデータですが、カットシーンの演出はコードです。

---

## 5. TLA の `scene_*.tsv`（オーバーレイではなくマップブロック）

TLA の `map.s` は **7 つ**のブロックを持ちます: metatiles、shapes、grid、shape_grid、animation、blend、scene（`games/tla/src/map/map_008/map.s`）。markers ブロックはなく、TLA には `markers.tsv` がありません。

scene ブロックは LZ 圧縮された `scene.parts.lz` です。`scene.tsv` がその部品を順番に並べます: `SCENE_HEADER, SCENE_POINTS, SCENE_ENTRANCES, SCENE_PATCHES, SCENE_BOUNDS`。286 マップにあります。

| ファイル | 列 | 備考 |
|---|---|---|
| `scene_header.tsv` | `entrances:u16 patches:u16 bounds:u16 none:u16` | ブロック先頭からのバイトオフセット。points は 8 から始まる。286 個すべてで確認: entrances = 8 + size(points)、patches = entrances + size(entrances)、bounds = patches + size(patches)。`none` はどこでも 0（検証済み） |
| `scene_points.tsv` | `id:u8 x:u16 z:u16` | `0xff` で終わる。点は 579 個で、id はほとんど 1..28、99 が 10 個。意味は不明（推定: スクリプトかカメラの点。TBS ではセル単位の宝箱ではない） |
| `scene_entrances.tsv` | `id:u8 x:u16 z:u16 flags:u8` | 1,970 行。推定: TBS の `SceneEntrance`（id、x、z）に相当。flags の下位ニブル = facing>>12（値 4=南 1105 回、12=北 685 回、0=東、8=西、2/6/14 斜め）、ビット 4（16）は追加のフラグ（28、20） |
| `scene_patches.tsv` | `key:u16 source_x:u8 source_y:u8 x:u8 y:u8 width:u8 height:u8` | `0xffff` で終わる。**286 個すべてで空** |
| `scene_bounds.tsv` | `left:s8 top:s8 right:s8 bottom:s8` | たいてい1行 + `-1`。推定: 16 px のセル単位のカメラ範囲（map_008: 0,0,40,34） |

オーバーレイ側では、TLA のシーンはまだ Exits/Placements/Events を C で持っています（`games/tla/src/scene/<place>/data.c`）。97 個の `SceneEntrance` テーブルのうち 86 個は1行（戻り先）だけで、TLA のエンジンが位置をマップブロックから取ることを強く示唆しています（推定。読む処理はデコンパイルされていない）。TLA の出口の (シーン, 入口) の組を、固定のシーン→マップのオフセットでマップの入口 id と照合しようとしたスクリプトは、決め手がありませんでした。TLA のレイヤードテーブルがソースにないためです。

**TBS は移行するか?** 推定: **しない**。少なくとも同じファイルには。TBS の ROM のマップはマーカーを含む 6 ブロックを持ち、そのエンジンは入口をオーバーレイから読むので、データは ROM が置く場所にあります。Git の履歴:

- TLA のマップファイル: "TLA: the four field maps still copied, from editable tables"（a20313083f）など。
- 最近の TBS のシーンの作業は C の人間化です（"Align scene table getters with the engine contracts"、db7167f0b0）。

どれもシーンテーブルを TSV に移すことには触れていません。

---

## 6. 新しいマップやシーンを追加する（チェックリスト）

どこでも、挿入より**末尾への追加**を選んでください。

1. **マップデータ。**
   - `src/map/map_180/` を作ります: `map.s`（`.global Field_Map180`、`map_header`、3×`map_layer`、6×`map_block`、incbin）と TSV。
   - 既存のタイルセットを再利用するか（新しいシートなし）、その後にシートとパレットを追加します。
   - 使わないブロックはオフセット 0 の `map_block Field_Map180` です。マーカーについては、`map_000/markers.table` か自分のものを指します。
2. **objects.tsv。** `system/overlay/overlays` の行（objects.tsv:631）の**前に** `main rom_tail_02 games/tbs/src/map/map_180/map` を追加します。これで ROM の順番が決まります。0x08320000 より後に固定されたアドレスはありません。
3. **directory.s。** `unused` を1つ `resource , Field_Map180` に、新しいものがあればパレット/タイルにも変え、それに応じて `unused 25` を減らします（`:307`）。新しい id は 0x3cf 以降で、既存の id はずれません。
4. **layered.tsv。** `ResourceId_Map001` からのオフセットの行を末尾に追加します: マップ、パレット、タイル ×3、レイヤーデータ。その行番号がシーンの `map` です。`rom_main_01` に置かれ、固定された `rom_main_02` の開始までの空きは: EN 4,020 B、DE 1,204 B、ES/FR 1,972 B（1行 12 B）。
5. **シーンのオーバーレイ**（シーンに専用のコードを持たせる場合）:
   - `src/scene/<place>.c`、`entry/<place>.s`（ベニヤ 6 つ）、`import/<place>.s`（`overlay.inc` の順のインポート）。
   - `include/unit/scene/<place>.h` にプロトタイプ（91 個あります）。
   - objects.tsv の行 `3cf text .../entry/<place>`、`3cf text .../<place>`、`3cf text .../import/<place>`、それに任意で `3cf bss ...` と `overlays.tsv` のヘッダー行。
   - `src/system/overlay/overlays.s`: `Resource_Overlay3CF: .incbin "overlays/resource_3cf.lz"` + `.balign 4`。
   - ディレクトリ: `unused` の枠を1つ `resource , Resource_Overlay3CF` にします。
   - あるいは、Altin Peak の部屋のように既存のオーバーレイを変種として再利用します: 同じコードでシーンの行を追加し、ゲッターで `SceneId_` によって分岐します。
6. **scenes.s。** 末尾に `scene NewPlace, 0x3cf, <group>, <variant>, <layered row>` を**追加**します。新しい id は 201 なので、既存の数値 id はすべて有効なままです。テーブルは `rom_main_04` にあり、1行 8 B。固定のバンクまでの空き: EN 3,448 B、DE 1,040 B。`include/scene_ids.h` に `extern char SceneId_NewPlace;` を追加します。グループは 0x7f 以下（訪問済みフラグ）。シーン id は 0x1ff 未満（出口ワードの戻り先）でなければなりません。
7. **つながり。**
   - 隣のシーンの出口テーブルそれぞれに、**その**シーンのヘッダーの下で出口ワードを追加します: `SCENE_EXIT(kind, 201, entrance)`。
   - 出口のセルに塗る衝突コードについて、隣のシーンのイベントに `EVENT_EXIT`（または触れたときのスクリプト）の行を追加します。
   - そのコードを隣のシーンの `grid_collision.tsv` に塗ります。
   - 新しいシーンにも同じことを鏡のように行います: `SCENE_EXITS(201)` のヘッダー、その出口、隣のシーンの出口ワードが指す番号と一致する入口、配置、イベント。
8. **規則。** 音楽（`scene_cue`/`group_cue`）、地名（`scene_name`/`group_name`）、全滅時の戻り先（`return_to`）、背景は `src/object/scene_rules.s` に、エンカウントは `src/object/location_rules.s` にあります。行がないと MUS_018、名前なし、エンカウントなし、最後の背景になります。
9. **テキスト。** `text/<lang>.po` にメッセージを追加し、メッセージのシンボルごとに `msgctxt` を付けます。
10. **予算**（検証済み、`out/tbs-*/tbs-*.map`）。
    - ROM は 0x08800000 まで詰め物がされています（Makefile:134）。末尾の空き: EN 11,076 B、IT 11,040、DE 10,108、ES 4,128、FR 3,584、JA 43,100。
    - 新しいマップとオーバーレイを足すとおそらくこれを超えるので、8 MB の `ROM_END_tbs` を上げる必要があります。`MEMORY ROM` はすでに 32M を許しています（`main.ld`）。これで ROM は一致しなくなります。（推定: 安全。未テスト。）
    - オーバーレイの RAM は 32 KB 以下。

---

## 7. コード生成の実現性（テーブルごと）

一般則: 値は固定のバイトにコンパイルされるので、書式や空白は自由です。バイト単位の一致は次に依存します:

- 同じ行の順番。
- シンボルを含む同じ値（`MSGNO(Msg…)` はメッセージ番号に、`EVENT_SCRIPT(fn)` は再配置に、フラグ名は `flags.h` から解決される）。
- `.rodata` と `.data` のどちらに置くかを決める、同じ `const`。
- エディション別・パッチ別の同じ `#if TBS_PATCH_n` / `LANGUAGE` ブロック。
- ファイル内の同じテーブルの順番。

| テーブル | 書き換えて安全か | 往復変換のしかた |
|---|---|---|
| SceneEntrance | はい、とても規則的: リテラルのフィールド 12 個、シンボルの入口名 21 個 | `{...}` の1行を CST を保ったまま編集。値が変わらなければシンボルを保つ |
| 出口 `u32[]` | はい、注意して: マクロだけだが、シーンごとの `#define`（`ROOM_ENTRANCE(exit)`、`LUNPA_EXIT_TO_*`）、`SCENE_EXIT(0,N,0)` のヘッダー、`#if !TBS_PATCH_3`（vale_home.c）がある | マクロ呼び出しを解析してワードに評価し、触れた呼び出しだけを出力し直す。`SCENE_EXIT(0,..)` と `SCENE_EXITS` を決してまとめない |
| ScenePlacement | ほぼ: `PIXELS(n)`、`FACING_X + FACING_STEP`、キャラクター名（`GARET`）、スクリプトのシンボル、`#if` のあるテーブル 4 個 | フィールドをその場で編集。行の順番（アクター番号）を保つ |
| SceneEvent | 最も難しい: ビットフィールドのマクロと約 220 個の生の 16 進 control、メッセージと関数のシンボル、`#if` 10 個 | 編集するフィールド（trigger、condition、FIND_ の値）以外は中身のわからないトークンとして扱う |
| SceneRegion | はい、小さい: `#if` のあるもの 3 個 | その場で |
| markers.tsv | はい、データファイル | TSV を書き直す。10 進も 16 進も受け付ける |
| scenes.s / layered.tsv / directory.s | はい、行単位 | 末尾への追加のみ |

検証:

- 再ビルドして `make compare` / `compare-tbs` を実行します（Makefile:48-51）。
- 素早く確認するには、何も変えない書き直しの前後で `out/tbs-<ed>/overlays/resource_<id>.elf` のセクションを比較します。純粋な整形なら、オーバーレイの `.bin` と `.lz` の出力は同一になるはずです。
- ファイル全体を生成し直すのは避けてください: ファイルにはコード、`// clang-format off` の領域、コメント、`#ifdef UBFIX` のブロックが含まれています。

---

## 8. 未解明の点

- スクリプトが読む `EventWork.touchedTrigger`（`include/field/event_work.h:26`）を何が書き込むか。メインのコードに名前のある書き込み元はありません（推定: 触れたコード）。
- 1 と 2 以外の `ScenePlacement.behavior` の小さな整数（3 がよくある）: `ObjectMotion_SetActionCallback` の意味はここでは追跡していません。
- スプライトの種類の完全な表（オブジェクト id 20 = 宝箱、28 = ストーン、0x8000 = カメラは markers.c と actors.c で検証済み）。
- TLA: `scene_points` の意味、`scene_entrances.flags` のビット 4、範囲の単位、シーン→マップの解決、シーンテーブルの 6 列目（`games/tla/src/field/README.md` でも XXX）。
- ディレクトリの `unused` の枠と 8 MB を超える ROM が、実機やエミュレーターで動くかどうか（推定: 動く）。
- シーン 59（名前なし、0x39d）には出口のヘッダーがありません。そこでの出口はシーンを変えません（ヘッダーが見つからないとき `Scene_TakeExit` は状態をそのまま保ちます）。

---

## 9. エディタのデータモデル案

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

編集操作:

- **出口セルを動かす:** grid_collision のコードと `EVENT_EXIT` の行。
- **行き先を変える:** 出口ワードを編集。
- **宝箱を追加:** マーカーの行、衝突コード、新しい 0xe00 以上のフラグを持つ `SEARCH(SEARCH_CHEST)` イベント。
- **NPC を動かす:** 配置の x/z を編集。行の x=z=0 がコードで位置を決めることを意味するなら警告する。

これらすべてにわたって検証すること:

- すべての出口ワードが指す入口番号が、行き先の Entrances に存在すること（なければ行 0 に戻る）。
- 配置の行を挿入したときのアクター番号のずれ。
- マーカーの上限 10 個。
- 32 KB のオーバーレイと ROM の予算。

---
