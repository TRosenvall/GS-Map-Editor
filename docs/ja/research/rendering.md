<!-- translated from docs/research/rendering.md @ 5cc75b0f23d8 -->
# 描画の調査: レイヤー、ブレンド、タイルアニメーション、仮置き

*これは英語版 [rendering.md](../../research/rendering.md) の翻訳です。両者が異なる場合は英語版が最新です。*

出典: alchemy（`games/tbs/...`）。特に断りがない限り、パスは `games/tbs/` からの相対パスです。
「検証済み」（VERIFIED）は、エンジンのコードで読み、描画で確認したことを意味します。「推定」（INFERRED）は根拠のある推測です。
作業用のスクリプトと描画結果は
`(a scratch folder)`
にあります（`r2.py` が基準となるレンダラー、`dirmap.py` がシーンのリソーステーブルを解決します）。

## 概要

「ぐちゃぐちゃな」マップの原因は視差スクロールではありません。原因はビューアーの3つのバグで、そのうち2つはほぼすべてのマップに影響します:

1. **仮置きセル（0xfff）は本物の絵です。** 読み込み時、128×128 のグリッド全体を行優先で数えて k 番目の 0xfff セルがブロック k になります。**182 マップすべて**で、仮置きセルの数は `metatiles.tsv` の行数とちょうど同じです。ブロックテーブルは実質「読む順に並んだ固有のブロック」で、明示的なセル値はそれを再利用します。仮置きを空として描くと、どのマップでも大部分が抜け落ちます。（検証済み）
2. **タイルセットが間違ったテーブルから取られています。** ゲームはマップのパレット、3枚の VRAM シート、シート D を、`directory.s` の順番ではなく `src/field/layered.tsv`（`gMap_LayeredScenes`）から読み込みます。**182 マップのうち 117** が、ビューアーの想定とは違うパレットやシートの組み合わせを使っています。例: マップ 034 のキャラブロック 3 は `Set02TilesC` で、シート D は `Set26TilesC` です。VenusEntrance は `Set07` のシートを `Palette49` と組み合わせて使います。（検証済み）
3. **ヘッダーの範囲は既定のカメラ範囲にすぎません。** シーンの入口テーブルがそれを上書きできます。マップ 034（シーン Bilibin3）は入口によって 16..400 px に制限されます。その範囲の外では、128×128 タイルのヘッダー領域はグリッドの埋め草（ブロック 3）で、ゲーム中では決して見えません。（検証済み）

視差とドリフトがあるのは 8 マップだけです（047、103、104、147、148。090/091/092/169 では速度が 0 なのでマスクに効果がありません）。ブレンドは小さなスクリプトが設定する BLDCNT/BLDALPHA です。第1ターゲットはほとんどの場合レイヤー 2（BG1）で、ときどきレイヤー 1（BG2）です。タイルアニメーションは、シート D から VRAM への DMA によるタイルのコピーです。4つとも `r2.py` に実装し、描画で確認しました。

## (a) レイヤー、窓、スクロール

**構造体。** `struct LayeredSceneLayer {u8 x, y; s8 scrollX, scrollY, speedX, speedY; u8 periodX, periodY;}` は `src/field/field/map_layers.c:172-181` にあります。`map_layer` マクロの順番も同じです: x、y、rate_x、rate_y、drift_x、drift_y、period_x、period_y（`src/map/map.inc`）。

**読み込み**（`map_layers.c:274-303`、検証済み）:
- `offset = x<<19` と `y<<19`。つまり原点は 16.16 固定小数点で x×8 px です。
- `scale = scroll*4096`。つまり表示の rate/16 です。
- `speed = speed*4096`。つまり 1 フレームあたり speed/16 px です。
- `mask = period`。
- `phase = 0`。

**毎フレーム**（`Map_UpdateLayerScroll`、`map_layers.c:474-566`。`Map_SetCameraCenter` 572-630 も同じ、検証済み）:
```
view   = followed point - focus, clamped to [min, max - 240x160]        (min/max = header bounds*8 px, or scene overrides)
base   = view * scale            (Q16 multiply → view * rate/16)
if speed: phase += speed; base = (base + phase) & ((period<<19) | 0x7ffff)   # 折り返し。speed != 0 のときだけ適用
pos    = base + offset           # グリッドのピクセルで表したレイヤーの左上
BG(3-li) scroll = pos
```
描画は両軸とも `((pos/16) & 0x7f)` の位置のセルを読みます（`Map_RenderMetatileRow/Column`、411-462）。したがって **レイヤーの窓は 128 セル（2048 px）を法として折り返します**。窓の大きさ = 画面で、レイヤーごとの窓の大きさはありません。
レイヤー li は BG(3-li) に表示され、BGCNT の優先度 = ヘッダーの優先度バイト、キャラベース = ヘッダーのキャラバイト、スクリーンベース 5+li です（314-322）。

**カメラの範囲。** `work->min/max = header bounds << 19`（261-264）。`Scene_ApplyEntrance`（`src/object/object/run_scene.c:488-499`）は、入口の `cameraLeft/Top/Right/Bottom != -1` のとき、minX/minY/maxX/maxY をそれぞれピクセル単位で上書きします（`struct SceneEntrance`、`include/field_scene.h`）。マップ 034 = シーン `Bilibin3`（`src/field/scenes.s:50`、マップインデックス 0x24）。その入口 1 と 2 は範囲 16,16,400,400 を使います（`src/scene/bilibin.c:780-785`）。いくつかのシーンは範囲を直接書き込みもします（`tolbi_ship_deck.c:1062`、`vale_babi.c:418-421`、`psynergy_effects/view.c:16`）。

**既定でないレイヤーパラメーターを持つマップ**（それ以外はすべて `16,16,0,0,255,255`）:

| マップ | レイヤー | パラメーター | 意味 |
|---|---|---|---|
| 047 | 0 | rate 8,8 | 半分の速さの視差 |
| 103 | 0 | drift_y −25、period 255 | 背景が 25/16 px/フレームで上に流れ、2048 px で折り返す |
| 104 | 0（y=92） | rate 6,6 | 空/海の視差（船のマストの場面） |
| 147、148 | 2 | rate 20,20、drift −121/16、35/16 px/f、period 31 | 砂嵐の上層、256 px ごとに折り返す |
| 090-092（レイヤー 0,1）、169（レイヤー 0） | | period 127/63、speed 0 | 効果なし（マスクは speed ≠ 0 のときだけ使われる） |

**優先順位（GBA、描画で検証済み）。** `(-priority, layer index)` で並べて奥から手前へ描きます。優先度が同じなら BG 番号の小さい方が上なので、レイヤー 2（BG1）がレイヤー 0（BG3）の上になります。現在のビューアーの `sorted(key=-priority)` は安定ソートなので、すでに同じ結果になります。優先度 0 = 非表示。

**Python ビューアーの描画規則:**
- *フィールドのレイヤー*（rate 16、speed 0）: `grid_px = (origin_px + map_px) mod 2048`。ここで `map_px` は bounds.left からではなく、グリッド空間の (0,0) から測ります。これはどんなカメラでも正確です。現在の `render_layer` は left=top=0 のときはこのように動きますが、128 セルを法として折り返さず、0 でない bounds.left/top を無視します。
  - 正しい形: 範囲の窓の画面列 i について `gx = (x*8/16 + bounds.left/2 + i) % 128`、y も同様。
- *視差/ドリフトのレイヤー*には単一の静止画がありません。マップ表示の推奨規則: カメラ範囲の中央に基準を置きます。
  - `V = ((min + max(min, max-240))/2, same for y)`、`pos = layer_pos(V) + (map_px - V)`。
  - これはカメラが V にあるとき正確で、それ以外では連続的です。ドリフトの位相 = 0（または speed×フレーム数）。
  - さらに、`layer_pos(view)` をそのまま使う 240×160 の「カメラプレビュー」も用意します。
- わかっていればシーンのカメラ範囲で*切り抜き*、そうでなければヘッダーの範囲を使います。

## (b) ブレンド

**仕組み**（`src/field/field/map_animation.c:163-255`、検証済み）:
- `blend.tsv` はハーフワードにコンパイルされます: `control v` → v（BLDCNT の値で、上位ニブル 3 で識別）。`level v wait` → v, wait。`jump n` → 0xfe00|n（カーソル = スクリプト + 2n ハーフワード）。`stop` → 0xfeff。`end` → 0xffff（先頭へループ）。
- `level` では:
  - 直前の BLDCNT の効果ビット（7..6）が 01 なら `REG_BLDALPHA = v`、
  - そうでなければ `REG_BLDY = v`、
  - その後 `wait` フレーム待ちます。
- `end` だけのスクリプトは何も設定しません（`DisplayBlend_StartScript` 246）。
- 読み込み処理は最初に `REG_BLDCNT = 0` を設定します（`map_layers.c:365-367`）。

**GBA での意味:**
- BLDCNT のビット 0-5 は第1ターゲット（bit0 BG0、bit1 BG1 = レイヤー 2、bit2 BG2 = レイヤー 1、bit3 BG3 = レイヤー 0、bit4 OBJ、bit5 背景色）。
- ビット 6-7 は効果（1 アルファ、2 明るく、3 暗く）。
- ビット 8-13 は第2ターゲット。
- BLDALPHA: EVA = ビット 0-4（ターゲット1のレイヤーの重み）、EVB = ビット 8-12（その下にあるものの重み）、それぞれ上限 16。
- 5 ビットのチャンネルごとに `out = min(31, (top*EVA + below*EVB) >> 4)`。
- BLDY: `I + (31-I)*Y/16`（明るく）または `I - I*Y/16`（暗く）。

**TBS のマップで見つかった値**（`control` の後の最初の `level`）:

| BLDCNT | ターゲットのレイヤー | 効果 | マップ（例） |
|---|---|---|---|
| 0x3f42 | レイヤー 2（BG1）がすべての上 | アルファ | 005-007/032/076（0x1006: 6/16 + 16/16 の加算）、021、022-024/136/137、025-027/077-085（0xa09: 9/16 + 10/16 = 080 の水）、029、033/040/062/115/144（0x1003 の光、3-4 でアニメーション）、047（0xc04）、053、054-058/109/155/156/163、063-067/100、073、075、108、113、133、139-142（0xb0e）、154、164-167 |
| 0x3f44 | レイヤー 1（BG2） | アルファ | 009/145/146、010/019、012/013/016、014/015、018/038/052/094/095/099/102/120/121/151/160/161（0x1008）、061、086、105、124 |
| 0x3fc8 | レイヤー 0（BG3） | 暗く、BLDY 3-6 | 046 |
| （なし） | — | BLDY のみ、効果なし | 039/042/043、114、125: スクリプトは BLDCNT=0 のままレベルを書きます。シーンが BLDCNT を設定するはずです（推定） |
| `end` のみ | — | — | 36 マップ（020、028、031、036、037、048、051、060、072、074、089、093、… `map_020/blend` 経由の 134 を含む） |

EVB=16 のレベルのほとんどは **加算の光**（光の筋、たいまつ）です。wait が 43210 ならそのレベルは一定です。

**シーンが設定するブレンド**（`blend.tsv` にはない。コードで検証済み）:
- `src/scene/altmiller_cave.c:195-222, 313-320`: BLDCNT 0x3f42 と BLDALPHA 0x1000..0x600、または 0xc04。マップ 134 = シーン AltmillerCave5（`scenes.s:165`）は、暗闇のレイヤーがこの方法でブレンドされます。
- ほかに `tret_tree_branch.c:163`（BG1 4/12）、`tolbi_spring.c`、`vale_babi.c`、`mercury_lighthouse*.c`、`crossbone_isle_platform_rooms.c`、`lemurian_ship.c`。

**描画規則:**
- ブレンドスクリプトを解析し、BLDCNT と最初のレベルを取るか、フレーム t までシミュレートします。
- 奥から手前へ描く各レイヤーについて: その BG ビットが target1 にあり effect==1 なら、レイヤーが不透明な所で `rgb = min(31,(layer*EVA + below*EVB)>>4)`。「下」はすでに合成済みの色（または背景色）です。TBS のすべての control は第2ターゲット 0x3f を使います。
- 効果 2/3 では、そのレイヤーのピクセルに BLDY を適用します。
- 正確な結果を得るには 5 ビットの色（PNG の値 >> 3）を使います。
- 必要なら、シーンが設定するブレンド用にマップごとの小さな上書きテーブルを持ちます（134 → 0x3f42/0xc04）。

## (c) タイルアニメーション

**仕組み**（`src/field/field/map_animation.c:7-145`、検証済み）:
- `animation.tsv` はハーフワードにコンパイルされます: `channel n` → 0xfd00|n、`frame src cnt dst wait` → ハーフワード 4 個、`jump n` → 0xfe00|n、`stop` → 0xfeff、`end` → 0xffff。
- `MapAnimation_StartChannels` がストリームを走査します。各 0xfdNN は次のハーフワードからチャンネル NN&15 を開始し、ビット 7 が立っていれば一時停止状態にします（`channel 0x8N`。シーンが `Map_ClearLayerEntryFlag` で再開します）。
- 毎フレーム、一時停止していない各チャンネルについて:
  - timer>0 なら: timer−− して次のチャンネルへ。
  - そうでなければカーソル位置を実行:
    - 0xffff → カーソル = 先頭
    - 0xfeNN → カーソル = 先頭 + 2·NN ハーフワード
    - 0xfeff → 停止したまま
    - それ以外は `cnt` 枚のタイルをコピーし、timer = wait、カーソル += 4 として、同じフレーム内で再びループします。
  - したがって **wait W のコピーは W フレームの間画面に残り**、W=0 なら同じフレームで次のコピーに続きます。
- コピー（4bpp、`wideTiles==0`）は 32 バイトのタイル単位で、**キャラブロック 1** から数えます:
  - `src >= 0x600`: `Ram_DecodeBuffer (0x0201c000) + src*32` から。これは `gMapLayerData`（0x02028000、`src/system/ewram.s:236-244`、`include/ram_buffer.h`）+ (src−0x600)*32 です。つまり **シート D のタイル src−0x600**（シート D = `layered.tsv` の列 5、`map_layers.c:357-359` で gMapLayerData に展開）。
  - `src < 0x600`: VRAM のタイル `512+src`（ブロック 0 からの絶対位置）から。
  - コピー先: VRAM の絶対タイル `512+dst`。
- マップ項目の絶対タイルは `charBase*512 + (entry & 0x3ff)` です。

**フレーム t の作り方:**
1. VRAM の初期状態: ブロック 1/2/3 を `layered.tsv` の列 2/3/4 から、シート D を列 5 から。
2. 上のとおりにチャンネルを作ります。一時停止中のチャンネル（`channel 0x8N`）は飛ばします。
3. 更新を t+1 回実行し、VRAM のタイル配列を書き換えます。
4. その後、書き換えたタイルで通常どおり描画します。

ループは短いです（34 の水のサイクルは 24 フレーム、127 は 10+10 フレームの後にジャンプ）。GIF/プレビューは 1..N フレーム進められます。メタタイルのアトラスはフレームごとに作り直すか、タイル単位でキャッシュする方が良いです。

## (d) 仮置き 0xfff

**仕組み**（検証済み）:
- `Tilemap_ConvertBuffer`（`src/field/field/map_layers.c:110-122`）がブロック面に対して `Tile_ConvertMap`（`src/graphics/tile/convert_map.s:8-50`）を実行します。
- r5 = 0xFFF00000 で `(cell<<20) == 0xfff<<20` を調べます。
- r4 は 0xFFFFF001 から始まり、`cell + r4`（16 ビットに切り詰め）= `(cell & 0xf000) | k` で、r4 は仮置きごとに増えます。
- 使われていない C 版の `Tilemap_NumberPlaceholderBlocks`（84-103）も同じことをします。
- 結果: **下位 12 ビットが 0xfff の k 番目のセル（0 始まり、128×128 セル全体を行優先、全レイヤーまとめて）がブロック k になります。上位ニブルは保たれます。**
- 描画はその後 `Ram_MapBlocks[(cell<<20)>>19]`（下位 12 ビットのみ、411-437）を使います。

**検証。** 182 マップのそれぞれで、仮置きの数は `metatiles.tsv` の行数と等しくなります（`allph.py`）。034 と VenusEntrance の描画はまとまった絵になります（下記参照）。つまり仮置きは未知のコードで埋められるのではなく、読む順に並んだマップ固有のブロックです。`src/map/README.md` の `XXX` に答えられます。（数えるのは読み込み時にちょうど 0xfff を持つセルだけです。実行中のセルのコピー `Map_CopyMetatileIndicesRect` はその後に起こります。）

**規則:** 描画の前に `n=0; for y in 0..127: for x in 0..127: if cell&0xfff==0xfff: cell=(cell&0xf000)|n; n+=1`。
エディタにとっては次の影響があります:
- セルを 0xfff に、または 0xfff から塗り替えると、それより後のすべての仮置きの番号が変わります。
- 編集では仮置きの数をブロック数と等しく保たなければなりません。そうしないと保存されたブロックがずれます。
- 解決後のブロック番号を表示し、保存時は `resolved == running count` の所だけに 0xfff を格納します。あるいは、セルをそのまま保ち、0xfff を「次の固有ブロック」として扱います。

## 検証済みの描画結果

すべて `(a scratch folder)` にあります:
- `cur_034.png`、`cur_VenusEntrance.png`: 現在のビューアー（壊れている）。
- `ph_034.png`、`ph_VenusEntrance.png`: 仮置きの修正だけ（034 はまとまる。Venus はまだタイルセットが違う）。
- `new_034.png`: すべての修正。セル 1..25 に川や森がまとまって表示。残りはカメラ外の埋め草。
- `new_VenusEntrance.png`: すべての修正。正しい森と Venus Lighthouse の入口。
- `new_040.png` と `new_040_noblend.png`: 加算のたいまつの光（0x3f42、0x1003）。
- `new_080.png` と `_noblend`: 9/16 + 10/16 でブレンドされた水。
- `new_016.png`: Sol Sanctum の部屋、レイヤー 1 に 0x3f44。
- `new_134.png`: 不透明な暗闇。`new_134_sceneblend.png`: Altmiller の 0x3f42/0xc04 を使い、暗闇が 4/16。
- `new_104.png`（カメラ中央の基準）、`cam_104_0_0.png`、`cam_104_128_208.png`: 視差のある空。
- `new_147.png`: 流れる砂の上層。
- `new_047.png`、`new_103.png`。
- `anim_034_f00..f40.png`、`anim_034.gif`、`anim_034_compare.png`: 水アニメーションのフレーム 0 と 24 が異なる。

## gsmap/project.py への推奨変更点

1. **シーンのリソース**（`_read_directory` の対応付けを置き換える）:
   - `directory.s` を順序付きの項目リストに展開します。マクロを正確に適用します: `group K, a,b` → `K_a, K_b`。`area S, L, maps` → `Field_MapNN…, Tileset_SPalette, Tileset_STiles<L…>`。`recolor P, maps` → `Field_MapNN…, Tileset_PaletteP`。`overlays`。`unused N` → 項目 N 個。`resource , X` → X。
   - `base = index('Field_Map001')` とします。
   - `src/field/layered.tsv` の各行は `[header, palette, blk1, blk2, blk3, sheetD]` です。それぞれを `entries[base+v]` に対応させます。
   - ヘッダーのラベル（`Field_MapNNN` / `Field_<Name>`）をキーにし、最初の行を使います。マップ 108 と 110 には異なるパレットを持つ行が2つあります（45/58 と 15/18）。もう一方も選べるようにします。
   - ラベルは既存の `self.symbols` で解決します。参考実装: `dirmap.py`。
2. **アトラス:** 絶対タイル `a = char_base*512 + (e&0x3ff)`。
   - ブロック `a//512` が 1..3 → `[blk1, blk2, blk3][a//512-1]`。ブロック 0 はウィンドウのタイルなので飛ばします。4 以上は無効です。
   - パレットの行 14/15 はマップのものではありません（UI 用）。透明かデバッグ用の色で表示します。
3. **仮置き:** 描画用に `load_grid` で 0xfff → 連番（(d) の規則）に解決します。`== EMPTY → skip` の判定はやめます。保存用には生のグリッドを保ちます。
4. **窓:** `gx = (layer.x//2 + bounds.left//2 + i) % 128`、y も同様（飛ばすのではなく折り返す）。rate≠16 または drift≠0 のレイヤーには (a) のカメラ中央基準の規則を使います。
5. **ブレンド:** blend.tsv（`control`/`level`/`jump`/`stop`/`end`）を解析します。(b) の BLDCNT/BLDALPHA/BLDY の式で奥から手前へ合成します。レイヤーの不透明度スライダーの既定値を EVA/16 にするのは近似にすぎません（正確な結果は加算: `top*EVA + below*EVB`）。
6. **アニメーション:** 書き換え可能な `vram[2048]` のタイル配列と `sheetD[512]` を持ちます。(c) のとおりにチャンネルを進めます。フレーム番号か再生操作を用意します。
7. **カメラの範囲（任意）:** 既定はヘッダーの範囲。「中身に合わせて切り抜く」かシーンの入口の範囲を選べるようにします。シーン → マップインデックスは `src/field/scenes.s` から（`scene name, code, area, kind, map`、ここで map = `layered.tsv` の行）。範囲は `src/scene/*.c` の `struct SceneEntrance` テーブルにあります。

## 未解明の点

- スクリプトに `control` がないマップ（039/042/043/114/125）でブレンドがどう働くか。推定: シーンが BLDCNT を設定する。追跡していません。
- マップごとのシーンが設定するブレンドとアニメーションの再開（`channel 0x8N`）: 追跡したのは Altmiller（134）だけです。
- マップに行が2つある場合（108、110）にシーンがどちらの `layered.tsv` の行を使うか。どちらのパレットも有効です。
- なぜ縦方向のドリフトだけが BG の 32 行すべてを埋めるのか（`map_layers.c:600-604`、alchemy の XXX）。静止画の描画には関係ありません。
- 034 以外のマップのカメラ範囲は表にしていません。`scenes.s` と入口テーブルから得られます。
- 確認したのは EN エディションの分岐だけです。`layered.tsv` にエディション別の版はありません。
