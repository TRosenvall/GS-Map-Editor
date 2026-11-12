<!-- translated from docs/research/overworld.md @ 52c37110966a -->
# ワールドマップ（オーバーワールド）の調査: Golden Sun TBS、alchemy のソースから

*これは英語版 [overworld.md](../../research/overworld.md) の翻訳です。両者が異なる場合は英語版が最新です。*

ソースツリー: `~/gs_project/alchemy`（読み取り専用）。以下のパスは、`games/` または `tools/` で始まるものを除き
`games/tbs/` からの相対パスです。タグ: **[V]** = 検証済み（VERIFIED: コードやデータで読んだ、
またはプロトタイプの描画で確認した）、**[I]** = 推定（INFERRED）。

プロトタイプのスクリプトと描画結果（作業用で、このリポジトリには含まれません）:
`(a scratch folder)`
（`render_world.py`、`render_area.py`、`render_gameplay.py`、`world_mixed.png`、`world_annotated.png`、`collision.png`、`terrain_kind.png`、`north_compare.png`）。

## 概要

1. ワールドマップの地面全体は1つのテーブルです: `src/map/world/blocks.tsv`。16進 u32 の **セルワード** が 320 行 x 512 列並び、`tools/ags-graphics`（形式 `blocks`）で `blocks.blocks` にビルドされ、`src/map/map.s` がそれを `Field_PerspectiveDataA` として incbin します [V]。
2. テーブルは 16x16 セルの **チャンク** を 640 個持ちます（コードではチャンクを "tile" と呼びます）。チャンク 0-319 はレイヤー 0（BG3、地面）、320-639 はレイヤー 1（BG2、上層: 山、木、海岸）で、レイヤー 1 のチャンク = レイヤー 0 のチャンク + 320 です [V]。
3. ワールドは 16x16 チャンク = 256x256 セルです。1 セルはワールド座標で 32 ピクセル（画面/BG では 16 ピクセル）なので、ワールドは 8192x8192 ワールド px で、端がつながっています [V]。チャンク id 0-255 はワールドチャンク (id%16, id//16) に置かれ、256-319 はコードが差し替える代替チャンクです [V]。
4. セルワード: ビット 0-15 がブロック id、ビット 16-23 がステップ/イベントコード、ビット 24-30 が地形の種類（エンカウント地域。21 = 雪のグラフィックセット）、ビット 31 が挙動バンクのフラグです [V]。
5. ブロック id は `src/map/default/cells.tsv`（4 バイトのブロックが 4386 個: 左上、右上、左下、右下の 8x8 タイル番号）を指します [V]。タイルは 8bpp で、レイヤーごとに 256 枚: セット A = `tiles_a+b`（レイヤー 0）と `tiles_c+d`（レイヤー 1）、パレット `palette_a.png`（224 色）。セット B（雪）= `tiles_f..i`、`palette_b` です [V]。
6. 描画はモード 2（アフィン BG2+BG3）で、「モード 7」風の遠近表示のためにスキャンラインごとの HBlank-DMA 行列を使います。平面の真上視点の描画にはそのどれも要りません。プロトタイプは 4096x4096 BG ピクセルのマップ全体を正しく描画します [V]。
7. 通行可否はセル単位ではなく 8x8 のグラフィックタイル単位です: `default/attributes.tsv` が各タイルに 4 ビットの衝突値の 4x4 グリッドを与えます（上のレイヤーが下より優先。0 = なし。既定値 7）。5-12 が通行可能です [V]。
8. ランダムエンカウント: 地形の種類（セルのビット 24-30）+ 地形の挙動（衝突値から。バンクはビット 31 / 種類 21 から）-> `gWorldMap_EncounterRules`（`src/object/zonedata.c`）-> `src/object/encounter.tsv` のゾーン行 [V]。
9. 町やダンジョンは `gWorldMapPlacements`（`src/scene/world_map.c`）に配置されたアクター（アイコンのスプライト）です。アクター N に触れるとトリガー 100+N が発生し、`gWorldMapEvents` の `EVENT_EXIT` と照合されます -> 出口番号 -> `gWorldMapExits` -> (シーン, 入口)。一部の入口はセルのステップコード（ビット 16-23）を使います [V]。町から出るときは、その町の出口テーブル `SCENE_EXIT(n, 2, e)` -> `gWorldMapEntrances[e]` の位置を使います [V]。
10. TBS ではワールドマップのデータにエディション別の違いはありません。ROM 末尾の開始アドレスはエディションごとに異なり、どんな変更もバイト一致の「compare OK」を壊します [V]。

## ファイルと形式

| データ | ソースファイル | 形式 | ビルド先 / 接続元 |
| --- | --- | --- | --- |
| 地面のセル（両レイヤー） | `src/map/world/blocks.tsv` | ヘッダーなし。320 行 x タブ区切りのトークン 512 個。各トークンは `0x` なしの小文字 16 進で、先頭のゼロなし（`0`、`1b`、`9500014a`）、改行は LF、末尾に LF [V]。`tools/ags-graphics/tables.c:235-282` の `blocks()` が読みます: 行数は 16 の倍数、すべての行が同じ幅（16 の倍数）でなければなりません [V]。16x16 のまとまりはすべて `-`（省略、オフセット 0）にできますが、一部だけは不可 [V。TBS にはなく、TLA には 969 個]。 | `blocks.blocks`: 640 x u32 のオフセットテーブルの後に、各チャンクの 256 個の u32 ワード（1024 バイト）が LZ の種類 `plz` で個別に圧縮されて続きます（`tables.c:262-276`）[V]。`src/map/map.s:1-4` が `Field_PerspectiveDataA` として `.incbin` し、その後に `.byte 0x01 @ PACKER` が続きます [V]。ディレクトリ項目 `group Field, PerspectiveDataA, ...` は `src/system/resource/directory.s:123` [V]。 |
| TSV 内のチャンク番号 | 同上 | チャンク `i` は TSV の行 `(i//32)*16..+15`、列 `(i%32)*16..+15` を占めます（チャンクは横 32 個、行優先で並ぶ）[V: `tables.c:257`]。これはワールドの配置では**ありません**: ワールドは横 16 チャンクなので、TSV のチャンク 1 行にはワールドのチャンク 2 行分が横並びで入っています [描画で V]。 | |
| ブロック（メタタイル） | `src/map/default/cells.tsv` | ヘッダー `cell0:u8 ... cell15:u8`、値は `0x6b` 形式。1097 行で最後の行は短い（8 値）= 17544 バイト = 4386 ブロック x 4 バイト [V]。ブロック b = バイト `4b..4b+3` = 左上、右上、左下、右下のタイル番号（u8）[V: `src/field/field/world_map.c:71-91`、`444-451`]。両レイヤーで共有し、レイヤーがタイルバンクを選びます。 | `cells.table.lz`。`map.s:5-7` で `Field_DefaultMapCells`（+1 PACKER バイト）。`world_map.c:158-160` が `Ram_MapCellBuffer`（`gMapCellBuffer`、0xc000 バイト、`src/system/ewram.s:223-226`）に展開します [V]。同じテーブルがレイヤードマップの「既定セル」でもあります（README `src/map/README.md` の `default/` の行）。 |
| タイルの衝突 | `src/map/default/attributes.tsv` | ヘッダー `attr0:u8..attr15:u8`。256 行 = 4096 バイト [V]。バイト 0x000-0x7ff: 下レイヤー（BG3）のタイル 0-255、各 8 バイト。0x800-0xfff: 上レイヤー（BG2）のタイル 0-255 [V: `src/field/field/terrain.c:535-580`]。タイルごとに 4 行 x 2 バイト。各バイトは 4 ビット値を 2 つ持ち、下位ニブル = 左。1 つの値 = 2x2 BG px（4x4 ワールド px）。 | `attributes.table.lz`、`map.s:11-13` `Field_DefaultMetatileAttributes`。`Ram_MapCollision` に展開されます（`world_map.c:161-163`）[V]。 |
| タイルアニメーション | `src/map/default/animation.tsv` | ヘッダー `word0:u16..word7:u16`、ハーフワード 465 個。チャンネルスクリプト（`0xfdNN` チャンネル、元タイル/枚数/先タイル/フレームのまとまり、`0xfeNN` ジャンプ、`0xfeff` 停止、`0xffff` ループ）[V: `src/field/field/map_animation.c:7-13`]。元タイルが 0x600 以上なら `gMapLayerData`（= `tiles_e`/`tiles_j`）から取ります [V: `map_animation.c:57-61`]。 | `animation.table.lz`、`map.s:8-10`。`Ram_MapCollision+0x1000` に展開され開始されます（`world_map.c:149-152`）[V]。 |
| タイルのグラフィック | `src/graphics/world_map/tiles_{a..j}.png` | インデックス PNG。ピクセル値 = 生の 8bpp カラーインデックス、PNG パレット = `palette_*.png` [V]。a-d、f-i: 128x64（各 128 タイル）。e、j: 128x128（256 タイル、アニメーションの元）[V]。 | `tiles_X.8bpp.lz`、`src/graphics/world_map/worldmap.s`（それぞれ後に PACKER バイト）[V]。ディレクトリ `directory.s:124-135`（`WorldMapPaletteA`、`WorldMapTilesA..J`）[V]。 |
| パレット | `palette_a.png`、`palette_b.png` | 16x14 のインデックス PNG = 224 色 [V]。BG パレット 0-223 に読み込まれ、色 0 は現在の背景色に置き換えられます（`world_map.c:331-335`）[V]。 | `.gbapal.plz`（`worldmap.s:4`、`:26`）[V]。 |
| グラフィックセットのテーブル | `src/field/world_map_resources.c:11-28` | `gWorldMap_GraphicsResources[2][6]` = セット A（A..E）とセット B（F..J）それぞれの {パレット, タイル x5} [V]。 | C。 |
| 地形別のエンカウント規則 | `src/object/zonedata.c:7-15` | `gWorldMap_EncounterRules[132]` s16: 規則 32 個 {種類, 挙動（-1 は任意）, フラグ（-1 はなし / 立つと規則が無効）, ゾーン} + 終端の種類 -1 [V]。 | C。 |
| エンカウントゾーン | `src/object/encounter.tsv` | ヘッダー `rate:u16 level:u16 group0..7:u16 weight0..7:u8 zone`（最後の列はラベルで、エンコードされない）。ゾーン 104 個 [V]。 | `encounter.table`、`src/object/arcspark.s:10-13` [V]。 |
| 地形の挙動 | `src/field/mapdata.c:37-41` | `gWorldMap_TerrainBehaviorTable[48]` u8。インデックス = 衝突値 + バンク（セルのビット 31 なら 0x10、種類 21 なら 0x20）[V]。 | C。 |
| シーンのテーブル | `src/scene/world_map.c` | `gWorldMapEntrances`（`:2717`）、`gWorldMapExits`（`:2802`）、`gWorldMapPlacements`（`:2863`）+ ストーリー別の版（`:2966-3058`）、`gWorldMapEvents`（`:3060`）[V]。形式は `include/field_scene.h:54-150` [V]。 | ワールドマップのオーバーレイ 0x371（`objects.tsv:640-644`）、0x2008000 にリンク、上限 32 KB（`src/scene/README.md` の Limits）[V]。 |
| ポーズ画面のマップマーカー | `src/object/scripts.s:340-383` | `gWorldMap_PlaceMarkers`: {tile<<16 \| flag, 地名} の組。行 i はアクター 11+i を表します。0 の行はアクターを1つ確保し、-1 で終わります [V: `src/object/psynergy_effects/world_map.c:282-323`]。 | asm `.4byte`。 |
| ポーズ画面の絵 | `src/graphics/world_map/picture.png` | 240x160 8bpp、ワールドの x 4096-8192、z 0-4096 を覆います [V: `psynergy_effects/world_map.c:10-11, 318-322`]。手描きで、ブロックから生成されたものではありません [I]。 | `src/graphics/title/title.s:68-71` `Field_WorldMapPicture` [V]。 |
| ストーリーのフレーム | `src/graphics/world_map/story.png`、`storymap.tsv`、`storypal.png` | ワールドマップのオーバーレイにあるストーリーの差し込みグラフィック [V: `story.s`]。地面のデータではありません。 | `story.s`、オーバーレイのオブジェクト `objects.tsv:643` [V]。 |

ワールドマップのシーン id: `scene WorldMap, 0x371, 0x02, 1, 0x01` はシーン 2 です（`src/field/scenes.s:17`）。シーン id = `gField_SceneTable` の行番号です（`scenes.s:1-5`）[V]。そのマップインデックス 1 は `SceneId_Clear` と等しく、これが `Field_RunScene` で遠近モードを選ぶ条件です（`src/object/object/run_scene.c:45-49`）[V]。

## 描画

階層（TBS）[V]:

```
world (wraps)  16 x 16 chunks                      8192 x 8192 world px, 4096 x 4096 BG px
chunk          16 x 16 cells   (code: "tile")      512 world px, 256 BG px; 1 KB decoded
cell           u32 word, low 16 bits = block id    32 world px, 16 BG px
block          2 x 2 tiles (4 bytes in cells.tsv)  
tile           8 x 8, 8bpp, from bank per layer    16 world px, 8 BG px
```

- **表示**: `Map_InitializePerspectiveScene`（`world_map.c:112-264`）は BG3 = キャラベース 2、スクリーンベース 8、BG2 = キャラベース 3、スクリーンベース 10 を設定します。どちらも 512x512 px のアフィンで端がつながります（`:164-174`）。BG1 は静止画表示用のテキストレイヤー。`DISPCNT_MODE_2`（`:249`）[V]。BG2 は BG3 の上に描かれ、色 0 は透明です（`view.c:66-69` のコメント: 透明な所では BG2 の下に BG3 が見える）[V]。
- **タイルバンク**: セットの tiles[1]（A）-> キャラブロック 2、tiles[2]（B）-> ブロック 2 + 0x2000、tiles[3]（C）-> キャラブロック 3、tiles[4]（D）-> ブロック 3 + 0x2000、tiles[5]（E）-> `gMapLayerData`（`world_map.c:336-352`）[V]。したがってレイヤー 0 のタイル番号 0-127 = `tiles_a`、128-255 = `tiles_b`。レイヤー 1 は `tiles_c`、`tiles_d` です [描画で V]。
- **ストリーミング**: BG マップはプレイヤーの周り 2x2 チャンクの窓を保持します。`perspective->tileIds[256]` は各ワールドチャンクの枠をチャンク id に対応させ、初期値は恒等写像です（`world_map.c:262-263`）。`Map_WriteLayerCellTile` はチャンク `id`（レイヤー 1 は `id + 320` を使う、`:298`、`:640`）を LZ 展開して `Ram_MapBlocks` の 4 分の 1 の領域 `(x&1, y&1)` に入れ、ブロックテーブルからアフィンマップのバイトを書きます（`:38-95`）[V]。窓のインデックスは `& 15` を使うので、ワールドは 16 チャンクごとに端がつながります [V]。
- **遠近**: `WorldMap_BuildScanlineTable`（`src/field/field/view.c`）と ARM ルーチン `Transform_UpdateVertices` が、スキャンラインごとにアフィンの組（BG2/BG3 PA..Y）を1つ作ります。`MapAnimation_ApplyAffineFrame` がライン 0 を読み込み、残りを HBlank-DMA します（`world_map.c:386-441`）[V]。既定のピッチ 0xe000（-1/8 回転）、遠方面 0x1fe0000、中心 (120,96)（`:198-249`）[V]。真上視点のエディタ表示ではこれらはすべて無視できます。
- **グラフィックセット B**: `WorldMap_LoadGraphics(x,z)` は、パーティーの下にあるレイヤー 0 のセルの種類が 21 ならセット B を選びます。これはシーン読み込み時だけです（`world_map.c:323-329`、`run_scene.c:76-78` から呼ばれる）[V]。セット B のときは、チャンク枠 10-12 と 26-28 も代替チャンク 0x10a-0x10c、0x11a-0x11c に向けます（`:366-374`）[V]。描画により、セット B は雪の北部（Imil 周辺）だと確認できます。セット A ではそれらの枠に白い仮置きが表示されます [V: `north_compare.png`]。
- **ストーリーによるチャンク差し替え**: `FieldMap_SetWindowCellTile(128, 256, 176, 56)`（`src/scene/world_map.c:534`）は、`FLAG_LAMAKAN_SAND_MONSTER_BEATEN` が立っていない間、チャンク 264 を枠 59（ワールドチャンク (11,3)）に置きます。計算は `world_map.c:271-300` [V]。見た目では 264 と 59 は橋の有無が違います [描画で V。意味は I]。呼び出しはこれだけです（grep）[V]。64 個の代替チャンク（256-319 とそのレイヤー 1 の対）のうち 57 個は TBS のコードから参照されていません [I: grep で他の利用者は見つからず、64 個すべてが空でなく 0-255 とも異なる]。
- **アニメーション**: タイルアニメーションのチャンネルは `gMapLayerData`（タイル E/J）から VRAM にコピーします。静止画の描画には関係ありません [V]。

真上視点の描画アルゴリズム（`render_world.py` に実装、純 Python で 7 秒）[V]:

```
for layer L in (0,1), world chunk (cx,cy) in 16x16:
    c = cy*16 + cx + 320*L                         # セット B / ストーリー差し替えには tileIds の上書きを使う
    for cell (x,y) in 16x16: word = tsv[(c//32)*16 + y][(c%32)*16 + x]
        b = word & 0xffff; t[0..3] = cells_bytes[4b..4b+3]
        draw tile t[k] from bank L at BG px ((cx*16+x)*16 + (k&1)*8, (cy*16+y)*16 + (k>>1)*8)
        (layer 1: skip pixel value 0)
palette: palette_a.png (or palette_b.png for kind-21 cells / set B)
```

結果: `world_mixed.png`（セット A、種類 21 のセルはセット B で描画）では、右上の 4 分の 1（チャンク x 8-15、y 0-7）に Angara と Gondowan があり、残りは海です。大陸の西端には平らな埋め草の陸地、小島が 3 つあります [V]。`gWorldMapEntrances` と配置の位置をワールド/2 で重ねると、Vale のアイコン（アクター 11、5678,1200）、そのすぐ南に入口 0-2、隣にステップコード 90（Flint）が来ます [V: `world_annotated_zoom.png`]。

## ゲームプレイのデータ

### セルワード（レイヤー 0）[V]

| ビット | 意味 | 根拠 |
| --- | --- | --- |
| 0-15 | `cells.tsv` へのブロック id（16 ビット全体。ワールドマップには 12 ビットのマスクなし） | `world_map.c:82-86, 445` |
| 16-23 | ステップコード（`struct MapCell.collisionCode`）: 1-239 シーンのステップイベント、240-241 エンカウントする地面、252-254 ワープ、0xff 壁（レイヤードマップでの意味） | `include/map.h:13-22`、`src/object/object/step.c:20-25, 231-245` |
| 24-30 | 地形の種類 = エンカウント地域（0 なし、1-6、21、31 を使用） | `terrain.c:619-624`、`zonedata.c` |
| 31 | 挙動バンク 0x10 を選ぶ | `terrain.c:615-617` |

レイヤー 1 のセルはビット 0-15 だけを使い、上位ビットはデータ上すべて 0 です [V: 統計]。読まれるのはレイヤー 0 の上位ビットだけです（コードは `Ram_MapBlocks` の行 0-31、つまりレイヤー 0 を参照します）[V]。コードのコメント `struct WorldMapCell {tile:24, kind:7, flag:1}`（`world_map.c:17-23`）はステップコードを "tile" にまとめていますが、読む側はバイトを別々に使います [V]。

値の集計（レイヤー 0、全 320 チャンク）: 種類 0 74215、1 915、2 1542、3 1001、4 771、5 494、6 1304、21 1334、31 156。ビット 31 が立つセルは 188 個。存在するステップコード: 13、15、18、28、29、32、42、47、50、51、55、61、74、75、90、91、92、93、95、96、100 [V]。

### 通行可否 / 地形 [V]

- `GetWorldMapCollision`（`terrain.c:535-580`）: その位置のスクリーンブロック 10（上レイヤー）の BG マップのバイト（8x8 タイル番号）を取り、`Ram_MapCollision + 0x800` でそのニブルを引きます。0 なら、スクリーンブロック 8（下レイヤー）について `Ram_MapCollision` で同じことをします。それでも 0 なら 7 を返します。ニブルは 2 ワールド px 単位で、`((y>>1)&3)` が行、`((x>>2)&1)` がバイト、`(x>>1)&1` が上位ニブルを選びます。
- `CheckWorldMapWalkable`（`terrain.c:586-592`）: 値が 5..12 のときに限り通行可能。
- 挙動 = `gWorldMap_TerrainBehaviorTable[bank + value]`（`mapdata.c:37-41`）: バンク 0: 5->1、6->7、7/8/10-13->1、9->2。バンク 0x10（ビット 31）: 5->4、9->6。バンク 0x20（種類 21）: 5-13->5、ただし 9->6。挙動は戦闘背景も選びます（`encounter.c:118`、`Battle_SelectTerrainBackdrop` `encounter.c:404-429`）: 1 草原、2 森、3 砂漠、4 と 7 浜辺、5 と 6 雪原、それ以外は Sol Sanctum [V]。
- 合成した衝突マップの集計: 値 1-4、14、15（通行不可。水/山/崖）と 5-10（通行可能）が現れます。エンカウントのラベルによれば 9 = 森（挙動 2）[データで V。「森」のラベルは `encounter.tsv` から]。
- 高さ: ワールドマップにはありません（セルに形状バイトがなく、アクターは y=0 で地形の高さなしに配置されます、`src/object/object/actors.c:143-158`）[V]。

### ランダムエンカウント [V]

ワールドマップで1歩ごとに: `Field_ProcessStep` -> `Encounter_RollWorldMap(&leader->x, speed)`（`step.c:261-263`）-> `Encounter_ResolveWorldMapZoneAndBackdrop`（`encounter.c:103-120`）: `gWorldMap_EncounterRules` の中で、種類が一致し、挙動が一致（または -1）し、フラグが立っていない最初の規則がゾーンを決めます。次に `Encounter_SelectEnemyGroup`（`encounter.c:130-218`）が `encounter.tsv` の行を使います: 出現率（パーティーのレベルが `level` を超えるごとに +5、最大 5）、偏り、重み付きの 8 グループ（`src/battle/formatn.tsv` の行）。フィールドシーンの規則（`src/object/location_rules.s`）はワールドマップでは使われません（`Encounter_SelectSceneZones(0)`、`run_scene.c:49`）。

規則（種類: 挙動 -> ゾーン）: 1: 4,7,1->7、2->8。2: 4,7,1->13、2->14。21: 5->29、6->30。31: 1->37、2->38。3: 3,4,7,1->45、2->46。4: ...->54、2->55。5: ...->64、2->65。6: ...->80、2->81。ゾーンには `encounter.tsv` でラベルが付いています（"World map: terrain kind 1, grassland and beach" など）。挙動 3（砂漠）は規則に載っていますが挙動テーブルが決して生み出さないため、TBS のワールドマップでは砂漠の地面は草原/浜辺として扱われます [テーブルの読みは V、ゲームプレイ上の効果は I]。ジン戦: `gEncounter_AreaEntryTable`（`zonedata.c:19-29`）経由でゾーン 100-103。

`terrain_kind.png` はまとまった地域を示しています（Vale 周辺に種類 1、Bilibin に 2、北の雪に 21、…）[描画で V。地名は I]。

### 町やダンジョンに入る [V]

仕組みは2つあり、どちらも `gWorldMapEvents`（`src/scene/world_map.c:3060-3125`）に行き着きます:

1. **場所のアイコン（ほとんどの町）**: `gWorldMapPlacements`（`:2863-2964`）の行は行順にアクター 8、9、… です。条件を満たさない行も枠を消費します（`actors.c:103-108`）。`WorldMap_UpdateLocationContacts`（`world_map.c:416-466`）は、リーダーの |dx|+|dz| が拡大縮小した半径の和より小さい（かつ `FLAG_CONTACT_BLOCKED` 0x104 が立っていない）とき `touchedTrigger = actor + 100` を設定します。イベント `{ EVENT_EXIT, 100+actor, cond, exitNo }` がそれを出口に対応させます。例: 行 3（アクター 11、スプライト 0x105、5678,1200）-> トリガー 111 -> 出口 1 -> `SCENE_EXIT(1, 5, 10)` = シーン 5（Vale の村）の入口 10。一部のトリガーは代わりにスクリプトを実行します（通路 116/125/130/150/151 は近づく向きで出口を選ぶ、`:367-410`）。
2. **マップ内のステップコード**: セルのビット 16-23 = コード。`{ EVENT_EXIT, code, cond, exitNo }`（コード 13、15、18、28、29、32、42、47、50、51、55、61、75）、または `EVENT_TOUCH`/`SEARCH` スクリプト（90-96 ジン、移動、難破船。100 Turtle Boots を調べる。112 移動ルート。74 東端）。

出口のエンコード `SCENE_EXIT(exit, scene, entrance) = exit<<20 | entrance<<12 | scene`。フラグ付きの形は 0x10000000 を足し、フラグのワードを加えます。テーブルは `SCENE_EXITS(own scene)` で始まり 0x1ff で終わります（`include/field_scene.h:72-77`）。

### 町から出る [V]

町自身の出口テーブルがシーン 2 を指します: 例 `gValeHome_Exits` `SCENE_EXIT(10, 2, 1)`（`src/scene/vale_home.c:1903`）、Bilibin `SCENE_EXIT(1, 2, 5)`（`bilibin.c:805`）。入口 `e` は `gWorldMapEntrances` の行です（`struct SceneEntrance`、24 バイト: entrance、requiredFlag、x、y、z（s16 ピクセル）、facing、unused、カメラの L/T/R/B、unused。`field_scene.h:54-67`）。入口 1 = (5680, 0, 1226) で南向き、Vale のアイコンのすぐ下です。特別な入口（33、49、64-80、90、91、99）は配置テーブルやカットシーンも選びます（`world_map.c:308-342`、`496-560`）。

## 制限と制約

- チャンクの数と配置はコードで固定されています: 640 チャンク、レイヤーのオフセット 320（`0x140`、`world_map.c:298, 640`）、16x16 の枠グリッド（`& 15`）、固定 id 0x10a-0x10c、0x11a-0x11c、264 の代替チャンク [V]。`blocks.tsv` はちょうど 320x512 に保ってください。
- 各チャンクは 1024 バイトに展開され、0x400 のヒープブロックに入ります（`world_map.c:56-57`）[V]。
- タイル: レイヤーごとに 256（アフィンマップの項目はバイト）[V]。パレットは 224 色で、インデックス 0 は背景色に強制されます [V]。タイル E/J のバンク（256 タイル）はアニメーションに使われます [V]。
- ブロック: セル内のブロック id は 16 ビットですが、`cells.tsv` は `gMapCellBuffer`（0xc000 バイト、`ewram.s:225`）に展開される -> 最大 12288 ブロック [I]。同じバッファがイベント中に 240x160 の静止画を保持し（`world_map.c:711-712`）、その後に再読み込みされます（`:766-767`）[V]。
- 衝突テーブルは 4096 バイト固定（2 x 256 タイル x 8）[V]。アニメーションスクリプトはその後ろ、`gMapCollision`（合計 0x4000、+0x1000 から開始）に収まる必要があります [I]。
- 配置: アクターの枠は 8..65（`actors.c:98`、`CONTACT_LAST_ACTOR = 65`）。場所のトリガー 108..165 は、他のイベントに使われるステップコードとぶつかってはいけません [V/I]。`gWorldMap_PlaceMarkers` の行 i はアクター 11+i と揃っていなければなりません [V]。
- ワールドマップのオーバーレイ（コード + テーブル + ストーリーのグラフィック）は 0x2008000 の 32 KB に収まる必要があります [V: シーンの README]。入口の座標は s16 です [V]。
- 圧縮: すべてのチャンクは `plz` LZ（`tools/common/lz.c`、`LZ_PALETTE_UNTAGGED`、マシン `{4123, 485, 4126, 272}`）。cells/attributes/animation は `.table.lz`、タイルは `.8bpp.lz`、パレットは `.gbapal.plz` [V]。ビルドは TSV/PNG から再エンコードするので、エディタはソースだけを書けばよく、`.blocks`/`.lz` を手で書いてはいけません。
- バイト一致: 変更していないソースは元の ROM を再現します（PACKER のリテラルバイトと `_patch.tsv` の仕組み、`src/map/README.md` の "How the build encodes a map"）。どんな編集でもそのエディションは異なるものになり、つまり `make compare-editions` は設計上失敗します [V]。`map.s`/`worldmap.s` の末尾の `PACKER:` バイトは、編集後は無害な古いデータです [I]。
- ROM の配置: `rom_tail_02`（`map.s` を含む、`objects.tsv:443`）はエディションごとに固定のアドレスから始まり（`main.ld:122-126`）、最後の領域です。増えると後ろのデータだけがずれます。TBS のカートリッジの終端は 0x08800000（`Makefile` の `ROM_END_tbs`）[V]。それを超えた場合のチェックは私は確かめていません [I]。
- エディション: `map/world`、`map/default`、`graphics/world_map`、`zonedata.c`、`mapdata.c`、`world_map_resources.c` に `_ja/_de/...` の版や `.ifdef TBS_EDITION_*` はありません [grep で V]。`scene/world_map.c` には `TBS_PATCH_3` のコードの違いだけがあります（`:1657-1666`）[V]。地名やメッセージは言語ごとの PO カタログです（`games/tbs/text/*.po`）[シーンの README で V]。

### TLA との違い（簡単に）

- `games/tla/src/map/world/blocks.tsv` は 1024 行 x 512 = 2048 チャンク。レイヤー 1 のオフセットは 0x400（`games/tla/src/field/common/map/perspective.c:42`）、チャンクの窓は 32x32（`tiles[32][32]`、`:8`）-> ワールドは 32x32 チャンク（16384 ワールド px）[V]。969 チャンクが省略（`-`）されています [V]。
- `games/tla/src/map/world/blocks.s`（専用ファイル、`.balign 4, 0`）で配置されます [V]。
- グラフィックセットは A-D の 4 つで、それぞれパレット + タイルシート 6 枚（`tiles_a1..d6.png`）、さらにセットごとのアニメーション/属性テーブル（`anim_b/d.tsv`、`attr_b/c/d.tsv`）が `games/tla/src/graphics/world_map/` にあります。ディレクトリは `games/tla/src/system/resource/directory.s:420-458` [V]。`cells.tsv` はより大きいです（2745 行）[V]。
- TLA のワールドマップのエンジンコードの大半はまだアセンブリです（`object_dispatch_5.s`）。種類/フラグの意味は共通だと仮定しています [I]。

## 未解明の点

alchemy が印を付けているもの:
- XXX `world_map.c:569`: `WorldMap_UpdateView` は追従する位置を NULL チェックなしで読みます。
- XXX `world_map.c:778`: `Map_LoadDefaultCellsAndUpdateBlock` が `animationActive` を立てたままにするのが意図的かどうか。
- XXX `src/scene/world_map.c:500-504`: フラグ 0x161 と 0x85c（入口 99 と 1 が立てる）はどの TBS コードも読みません。
- XXX `actors.c:101-102`: 配置の生成における 0x2705 のスプライトの区切り。
- エンカウントのフラグ 351/353 は名前がありません（`encounter.c:148-152`）。「フラグ 5 / ユニット 5 の経験値 > 130」の規則。
- レイヤードマップの XXX（仮置きブロック 0xfff、ヘッダーの詰め物バイト）は当てはまりません: ワールドマップは 12 ビットのマスクを使いません [V]。

この調査で解決していないもの:
- セルのビット 31 の設計意図: 仕組みとしては衝突値 5 を挙動 4（浜辺の背景）に、9 を 6（雪原の背景）に変えます [V]。なぜその 188 セルに付いているのかは不明です [I]。
- なぜ衝突値 6 が挙動 7（2つ目の浜辺の id）になるのか [I]。
- TBS のコードが参照しない 57 個の代替チャンクの目的（残り物か TLA 時代のものか）[I]。
- 衝突値 1-4、14、15（水か山か崖か）と 6、8、10 のそれぞれの正確な意味 [I]。
- `picture.png`（ポーズ画面のマップ）が地面のデータから作られたかどうか。海岸線を変えるエディタは、それを手で描き直す必要があります [I]。
- 各 `EVENT_EXIT` が人にとってどのシーン/入口に行くかを知るには、`gField_SceneTable` の名前と突き合わせる必要があります（alchemy のシーン名の一部はずれていることが知られています。例: シーン 5 の `ValeHome` は Vale の村）[例については V]。

## エディタのデータモデル案

Python 層で、入出力はすべて alchemy のソースファイルに対してだけ行います。差分を見やすくするため、元のテキストの書式を保ちます。

| エンティティ | フィールド | ファイル（読み/書き） | 往復変換の注意 |
| --- | --- | --- | --- |
| `WorldGrid` | `chunks[640][16][16]: u32` と、枠の対応を通した派生ビュー `cell(layer, gx, gy)`。`slot_map[256] = identity` | `src/map/world/blocks.tsv` | ちょうど 320x512 個のトークンを書きます。`format(v, 'x')`（小文字、詰め物なし、ゼロは `0`）、タブ区切り、改行は `\n` + 末尾に `\n`。TBS では `-` を決して出力しないこと。変更していないファイルをバイト単位で同じに書き直せることをテストにすべきです。 |
| `Cell` | `block: u16`、`step_code: u8`、`kind: u7`、`bank_flag: bool`（レイヤー 0）。レイヤー 1 は `block` のみ | `WorldGrid` に詰め込み | レイヤー 1 の上位ビット（すべて 0）と未知のビットはそのまま保ちます。 |
| `Alternates` | `set_b_swaps {10:0x10a, 11:0x10b, 12:0x10c, 26:0x11a, 27:0x11b, 28:0x11c}`、`story_swaps {59:264}` | `world_map.c:366-372`、`scene/world_map.c:534` の定数（読み取り専用） | エディタは代替チャンクを元のチャンクと並べて編集し、両方の表示を見せるべきです。 |
| `BlockTable` | `blocks[4386][4]: u8` | `src/map/default/cells.tsv` | ヘッダー行は保持。1 行 16 値、`0x%02x`、最後の短い行は可。レイヤードマップと共有: ブロックを編集すると既定セルを使うすべてのマップが変わるので、新しいブロックは末尾に追加するのが望ましいです。 |
| `TileCollision` | `lower[256][4][4]`、`upper[256][4][4]` のニブル | `src/map/default/attributes.tsv` | 1 行 16 バイト、`0x%02x`、ヘッダー保持。レイヤードマップの既定データとも共有 [I]。 |
| `Tileset` | セットごと: パレット（224 RGB）、バンク L0（A+B）、L1（C+D）、アニメーション用バンク（E/J） | `src/graphics/world_map/*.png` | PNG のモード P、正確なサイズ、`palette_*.png` と同一のパレット（インデックス = 色）を保ちます。インデックスが保たれていれば PNG の書き直しはビルド上問題ありません。ファイルの同一性ではなくピクセルの同一性を確認してください。 |
| `Animation` | チャンネルスクリプト（u16 のリスト） | `src/map/default/animation.tsv` | 最初は中身のわからないワードとして扱います。 |
| `Entrance` | `id, required_flag, x, y, z, facing, camera[4]` | `src/scene/world_map.c:2717-2800` の `gWorldMapEntrances` | C ソース: 既知の目印の間にある初期化ブロックだけを解析・再生成します。`CONDITION_ALWAYS`、`FACING_*` の名前は保ちます。 |
| `Exit` | `exit_no, scene, entrance, flag?` | `gWorldMapExits`（`:2802-2839`）と町の `*_Exits` | 同様。マクロの形 `SCENE_EXIT(...)` を保ちます。 |
| `Placement`（場所のアイコン） | `row/actor, sprite, condition, behavior, x, z, facing, talk, flags` | `gWorldMapPlacements`（`:2863-2964`） | アクター番号 = 8 + 行。行を挿入/削除するとトリガー（100+actor）と `gWorldMap_PlaceMarkers` の揃え（アクター 11+i）の番号が変わります。その場での編集が望ましいです。 |
| `Event` | `kind/control, trigger, condition, value` | `gWorldMapEvents`（`:3060-3125`） | 出口: `{ EVENT_EXIT, trigger, cond, exit_no }`。スクリプトは C の関数を参照します（エディタでは読み取り専用）。 |
| `EncounterRule` | `kind, behavior, flag, zone` | `src/object/zonedata.c:7-15` | 終端を含めて s16 が 132 個。規則を追加する場合は配列サイズのリテラルを更新する必要があります。 |
| `EncounterZone` | `rate, level, groups[8], weights[8], label` | `src/object/encounter.tsv` | 表形式。参照（コードや規則のゾーン id）によって 104 行に固定。 |
| `PlaceMarker` | アクター 11+i ごとの `tile, flag, name_id` | `src/object/scripts.s:340-383` | asm の `.4byte` 行。 |

推奨するエディタの表示: (1) セルごとにセットを選ぶ真上視点の合成（種類 21 -> セット B）、(2) セルのタイル番号を通した `TileCollision` からの衝突オーバーレイ（上、次に下、それでもなければ 7）、(3) 種類とステップコードのオーバーレイ、(4) ワールド/2 での入口/配置。座標の補助: ワールド px = BG px x 2、セル = ワールド // 32、チャンク枠 = セル // 16、レイヤー L の TSV (行, 列) = `((c//32)*16 + gy%16, (c%32)*16 + gx%16)`、ここで `c = slot_map[(gy//16)*16 + gx//16] + 320*L`。
