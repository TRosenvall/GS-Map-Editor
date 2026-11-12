<!-- translated from docs/research/naming.md @ 3e642cd20a29 -->
# 名前の層: 衝突コード、アイテム、スプライト、地名、会話、フラグ（TBS）

*これは英語版 [naming.md](../../research/naming.md) の翻訳です。両者が異なる場合は英語版が最新です。*

> **この文書を書いた後の変更:** 以下で説明している名前のテーブルは、もう同梱していません。`gsmap/names.py` は実行時にチェックアウトから名前を読みます（`en.po`、`flags.h`、`sprite_ids.h`、`item_table.c`、`scenes.s`、`scene_rules.s`）。`gsmap/data` に残っているのは、プレビューのフレーム、空いている宝箱フラグ、そして私たち自身が書いた通行可否の説明だけです。

ソースツリー: `alchemy/`（読み取り専用）、英語版のビルド `out/tbs-en`。パスは、`out/` または `tools/` で始まるものを除き `alchemy/games/tbs/` からの相対パスです。**検証済み**（VERIFIED）は、コードやデータで読んだ、またはスクリプトですべてのファイルを確認したことを意味します。**推定**（INFERRED）は、推論したが証明していないことを意味します。生成したデータは `docs/research/names/` にあります。それを作るスクリプトは `docs/research/names/scripts/` にコピーしてあり、元のスクリプトと中間ファイルは作業用ディレクトリ `(a scratch folder)` にあります。

## 概要

1. **衝突コード** は3つのグループに分かれます: エンジン全体での意味、シーンのトリガー、マーカー。（検証済み）
   - **全体での意味:**
     - 0 床
     - 240/241 エンカウントする地面
     - 242..247 何もない固定の調べる場所: つぼ、たる、箱、墓、本、井戸
     - 249 連続ジャンプ
     - 250 ダメージ床
     - 251 Cloak の影
     - 252 段差
     - 253 よじ登り
     - 254 ジャンプで越える隙間
     - 255 壁
   - **1..239 はシーンのトリガーです。** 意味はシーンのイベントテーブルから決まります: 出口、触れたときのスクリプト、または調べる対象。
   - **マーカー（宝箱とストーン）は 100..239 しか使えません。**
   - エディタは 1..239 にマップごとにイベントから名前を付けるべきです。`collision_by_map.json`（作業用）は、その凡例をすでに解決したものです: 出口なら行き先の場所、スクリプトならスクリプト名、調べる対象ならアイテムかテキスト。
2. **アイテム:**
   - 名前 = メッセージ `MsgItemName`（386）+ id。
   - アイコン = `items.tsv` の列 `icon` → `graphics/ui/menu_icons/item_{icon:03d}.png`（16×16、パレット埋め込み）。
   - 宝箱の値 = `FIND_ITEM(id)` = `0x100000|id`、`FIND_COINS(n)` = `0x200000|n`、ミミック = `0x500000|slot`（スロット 0..7）、または `FIND_PSYNERGY_STONE` = `0x300000`。
   - （検証済み）
3. **スプライト:**
   - 配置のスプライト id は、そのまま `graphics/sprite/sprites.tsv`（513 行）の行番号として使われます。
   - そのグラフィックは `graphics/sprite/spr_NNN.png` で、w×h のフレームを縦に並べた帯を、共有の 224 色 OBJ パレットで描いたものです。
   - プレビューのフレームは、アニメーション 1 の最初のフレームに向きのオフセットを足したものです。
   - 249 個の id を網羅し、使われている 219 個はすべて含みます。71 個の名前は検証済み（デコンパイルのシンボルとコメント）、178 個は画像とそれを使うシーンからの推定です。
4. **地名:**
   - `gScene_AreaNameRules`（`src/object/scene_rules.s:168`）が、各シーンまたはグループに（必要なら入口ごとに）地域インデックスを与えます。
   - テキストはメッセージ `MsgDebugEntryName`（EN では 2459）+ インデックスです。
   - 201 シーン中 199 に名前が付きます。（検証済み）
5. **会話:**
   - `en.po` の `msgid` は 5 桁にゼロ埋めしたメッセージ番号です。`msgctxt` はシンボル名で、シンボルのないメッセージでは `message` です。
   - `SceneEvent` の値が 0x10000 未満ならメッセージ番号です。それ以上ならスクリプトで、そのセリフは本体にある `Msg*` シンボルです。
   - 話しかけるイベントのトリガーはアクター番号で、8 + 配置の行です。
   - （検証済み）
6. **フラグ:**
   - フラグは 4,096 個あります（0..0xfff）。
   - 新しい宝箱は **0xe00..0xfff** から、どのテーブル、コード、リテラルも参照していないフラグだけを使うべきです。**251 個が空いて**おり（`flags.json` の `free_chest_flags`）、小さい方から 0xe01、0xe03..0xe0f、などです。
   - 0x200..0x3ff は決して使わないでください: これらはリセットされるシーンとグループの一時フラグです。

---

## 1. 衝突コード

### 1.1 エンジンでの意味（特記がない限り検証済み）

セルのコードは `struct MapCell.collisionCode`（`include/map.h:13-22`）で、リーダーのレイヤー（`terrainId`）の窓から、16 px のセル1つずつ読まれます。

| コード | 名前（プレイヤー向け） | エンジンの挙動 | 根拠 | エディタ |
|---|---|---|---|---|
| 0 | **Floor**（床） | 通行可能。エンカウント地面 0 を使い、シーンの場所規則の shift = 1 で最初のゾーンがここに移らない限りエンカウントはありません。 | `src/object/object/step.c:240-276`、`src/object/object/encounter.c:76-90`、`src/object/location_rules.s:1-7` | ブラシ |
| 1..239 | **Trigger**（トリガー: 出口 / イベント / 調べる） | そのセルを踏むと `work->action = code` が発生します（`step.c:247`）。`Scene_RunTouchOrExit` はまずそのトリガーを持つシーンの `EVENT_TOUCH`（メッセージかスクリプト）を実行し、なければ `EVENT_EXIT` を使います。その値は出口の種類です（`events.c:333-380`）。前方のセルで A を押すと、同じコードの `EVENT_SEARCH` を探します（`run_scene.c:440-450`）。`USE_ITEM` と `PSYNERGY_IN_AREA` のイベントもこれをキーにできます。0 でないコードは出口エリアの判定も行います（`step.c:244-245`）。 | 記載のとおり | トリガー: イベントからマップごとに命名（§1.3） |
| 100..239 | **宝箱 / ストーン / 調べる対象の id** | 1..239 のすべてに加えて: `Field_PlaceMapMarkers` が受け付ける唯一の範囲です（`markers.c:57`）。`SEARCH(SEARCH_CHEST)` イベントは宝箱を表示し（オブジェクト 20、`markers.c:70`）、`FIND_PSYNERGY_STONE` はストーンを表示します（オブジェクト 28、`markers.c:105`）。 | | トリガー。マーカーが所有 |
| 240 | **Monster ground**（敵の出る地面） | 通行可能。エンカウントは地面 0 の代わりに `encounterGroups[1]`、つまり規則の最初のゾーンを使います。ダンジョンの床としてよく使われます: 23 マップ、例 map_009（133 セル）。 | `step.c:22-23,264-267` | ブラシ |
| 241 | Monster ground 2（敵の出る地面 2） | 240 と同様ですが `encounterGroups[2]` を使います。**どのマップも使っていません。** | `step.c:22-23` | ブラシ（上級） |
| 242 | Empty jar（空のつぼ） | 調べると「つぼを調べた… しかし何も見つからなかった」と表示されます。`MsgTileChecked`（2344）と `MsgTileResult`（2376）からのメッセージオフセット 2。前方の地面がリーダーより 0..64 px 高い場合だけ反応します。 | `src/object/fxdata.c:22-31`、`events.c:439-448`、`run_scene.c:441-447` | ブラシ |
| 243 | Empty barrel（空のたる） | オフセット 3 | 同上 | ブラシ |
| 244 | Empty wooden box（空の木箱） | オフセット 13 | 同上 | ブラシ |
| 245 | Empty grave（空の墓） | オフセット 8 | 同上 | ブラシ |
| 246 | Bookshelf（本棚、本） | オフセット 30 | 同上 | ブラシ |
| 247 | Well（井戸） | オフセット 31。マップでは未使用。 | 同上 | ブラシ |
| 248 | （未使用） | 読む処理が見つからず、どのマップも使っていません（推定: 効果なし）。 | — | 触らない |
| 249 | **Stepping-stone hop**（飛び石の連続ジャンプ） | `Field_ProcessStep` からは決して発生しません。前方へジャンプした後、0xf9 に着地すると再びジャンプします（連続ジャンプ）。3 マップで使用（029、098、148）。 | `events.c:383-405`、`src/object/psynergy_effects/climbing.c:18-23,99-103` | ブラシ（上級） |
| 250 | **Hazard ground**（ダメージ床） | 歩いている間ダメージ床の歩数が増え、`hazardLimit` に達するとパーティーが `hazardDamage` を受けます。モード、上限、ダメージはシーンが設定します。マップ 063-067。 | `step.c:24,293-327` | ブラシ |
| 251 | **Shadow (Cloak)**（影） | 通行可能。Cloak はこのコードの上でだけパーティーを隠し続け、離れると Cloak が終わります（`CLOAK_TILE`）。マップ 111 と 130-142（Lunpa Fortress、Altmiller Cave…）。 | `src/object/psynergy_effects/cloak.c:7-11,71` | ブラシ |
| 252 | **Ledge (jump down)**（段差: 飛び降りる） | 下を押しながら 12 フレームより長く押し付けると、リーダーが飛び降ります。 | `step.c:25-27,249`、`events.c:394-399` | ブラシ |
| 253 | **Climbable wall / ladder**（登れる壁 / はしご） | 12 フレームより長く押し付ける: 上で登り、下で降ります。登っている間は、同じコードのセルにだけ進めます。y≠0 で縦に2つ重なった 0xfd セルに到着すると、パーティーはよじ登り状態で始まります。 | `events.c:407-415`、`src/field/field/player_control.c:874-881`、`src/object/object/actors.c:250-262` | ブラシ |
| 254 | **Jump gap**（ジャンプで越える隙間） | 12 フレームより長く押し付ける: 着地点が許せば、リーダーは 2 セル前方へジャンプします（`Field_TryJumpForward`）。77 マップ。 | `events.c:400-405`、`climbing.c:13-30` | ブラシ |
| 255 | **Wall**（壁） | 常に通れません（`Map_CheckObjectStep` が 2 を返す）。 | `src/field/field/terrain.c:477,526` | ブラシ |

通行可否は高さにも左右されます。8 px より高い上りや 12 px より深い下りの1歩は拒否されるので（`terrain.c:494-497`）、崖の上の「床」コードも通れません。通行可否のオーバーレイはコードと `grid_shape` の高さを組み合わせるべきです。TBS のローカルマップでは水は衝突コードでは**ありません**: 壁か高さで表され、水たまりなどはシーンのトリガーです（ヒストグラムからの推定: 専用のコードがない）。

セルのコードは実行中にシーンのコードによっても変えられます（`SetMapCellCollision`、`terrain.c:422`）。Colosso、Altin Peak、Crossbone Isle、Venus Lighthouse、Tolbi、Sol Sanctum で見られます。マップ 078-083（Altin Peak）のコード 96..99 には静的なイベントがないので、スクリプトが読んでいます（推定）。

### 1.2 使用頻度のヒストグラム（`coll_hist.py` で検証済み、182 マップ、3つのレイヤー窓のセル）

| コード | セル数 | マップ数 | 備考 |
|---|---|---|---|
| 0 | 1,300,642 | 182 | 床 |
| 255 | 47,077 | 151 | 壁 |
| 240 | 4,308 | 23 | 敵の出る地面（ダンジョン/森: 009、016、025-030、043、046、050、055、056、062、064、066、067、078、133、136、137、164、166、167） |
| 21 | 4,244 | 34 | 例: Lamakan Desert のマップ 091: `EVENT_TOUCH 21 → HeatGauge_CountStep` のセルが 2,677 個 |
| 251 | 1,729 | 9 | Cloak の影 |
| 10 / 30 / 11 / 1 / 2 | 963 / 683 / 357 / 340 / 255 | 96 / 23 / 78 / 150 / 140 | 小さいコードは主に出口とドアの触れたときのスクリプト |
| 254 / 253 / 252 | 928 / 484 / 59 | 77 / 60 / 28 | ジャンプ / よじ登り / 段差 |
| 243 / 244 / 242 / 245 / 246 | 500 / 482 / 388 / 32 / 18 | 29 / 29 / 28 / 6 / 3 | 空のたる/箱/つぼ/墓/本 |
| 100..107 | 100, 67, 37, 21, 8, 5, 3, 4 | 95..3 | 宝箱（100 で `SEARCH_CHEST` が 66 回）とその他の調べる対象 |
| 200..212 | 2..35 | 14..1 | マーカー以外の調べる場所（つぼ/たる…に隠されたアイテム） |
| 250 | 77 | 4 | ダメージ床 |
| 249 | 3 | 3 | 連続ジャンプ |
| 241, 247, 248 | 0 | 0 | 未使用 |

マップ全体で 1..239 の背後にあるイベントの種類（数 = マップ数）: コード 1 → EXIT 130、TOUCH 44。コード 10 → TOUCH 65、EXIT 36。100 → SEARCH_CHEST 66、SEARCH 36。全体の表: `coll_hist.json`（作業用）。1..239 の (マップ, コード) の組のうち 136 個は、そのマップを使うシーンに静的なイベントが**ありません**。スクリプトが使っているか残り物なので、「スクリプト / 不明」と表示してください。

### 1.3 マップごとの凡例（検証済み、生成）

`collision_legend.py` が `collision_by_map.json`（作業用、1 MB）を書き出します。マップごとに次を持ちます:
- `scenes`。
- `cells_per_layer`: レイヤー窓ごとのコードのヒストグラム。
- `events_by_code[code]`: `{scene, table, kind: exit|touch|search|use_item|raised, control, condition, …}` のリストで:
  - 出口は `exit_kind, to_scene, to_entrance, to_name, to_symbol` を持ちます。
  - スクリプトは `script`（ELF のシンボル、例 `Event_EnterSanctum`、`HeatGauge_CountStep`）を持ちます。
  - メッセージは `message, text` を持ちます。
  - 調べる対象は `search_target`（32 個の `SearchTarget` 名のいずれか、`include/field_scene.h:176-209`）、`marker_chest`、`find_item/item_name | find_coins | psynergy_stone | mimic_slot` を持ちます。
  - 触れるものは `needs_push`（0x200）と `needs_facing`（0x400）を持ちます。

UI のラベルの規則:
- 「出口 → {to_name}」
- 「イベント: {人が読める形にしたスクリプト名}」
- 「宝箱: {item}」
- 「調べる {target}: {item | text}」

イベントがない場合のラベルは「未使用のトリガー」です。シーンごとのテーブルのいくつかはストーリーフラグで選ばれるので、UI はそれらの和集合を表示し、「ストーリーによる」と印を付けるべきです。

**エディタのデータ:** `names/collision.json`（`collision_json.py` で生成）:
```json
{"notes":[...],
 "ranges":[{"lo":0,"hi":0,"name":"Floor","category":"walk|block|move|search|trigger|unknown",
            "editor":"brush|trigger|trigger (markers own 100..239)|brush (advanced)|don't-touch",
            "meaning":"...","evidence":["src/...:lines"],"confidence":"VERIFIED","color":"#rrggbbaa"}],
 "codes":[{"code":240,"hex":"0xf0","range":"240-240","cells":4308,"maps":23}]}
```
これに加えて、読み込み時に `collision_by_map.json` の形（`{map: {scenes, cells_per_layer[3]{code:count}, events_by_code{code:[event…]}}}`）でマップごとの凡例を生成します。エディタはこれを同梱するのではなく、ビルド済みのオーバーレイ（gsmap の `Scenes`）から実行時に作るべきです。

プレイヤー向けのブラシパレット: Floor、Monster ground、Wall、Ledge、Climb、Jump gap、Shadow、Hazard、それに Empty jar/barrel/box/grave/books。トリガー（1..239）は自由には塗りません。「ドアを追加」や「宝箱を追加」のような操作で作られ、そのマップで未使用のコード（マーカー以外なら 100 未満）が割り当てられます。

---

## 2. アイテム

- **id とシンボル。** `include/item_ids.h` が名前を付けているのは、コードが使う id だけです（検証済み）。アイテムテーブル `src/game/items.tsv` は id ごとに1行（id = 行番号 − 2、324 行）で、英語名の `label` 列と、price、type、flags、equip_mask、icon、… の列があります。構造体は `ItemDefinition`、0x2c バイトです（`include/game/item.h:104-137`）。
  - 種類: 0 なし（消耗品/大事なもの）、1 武器、2 鎧、3 盾、4 兜、5 靴、6 エナジーのアイテム、8 指輪、9 シャツ（`item.h:43-55`）。
  - フラグ: 1 呪い、2 外せない、4 レア、**8 なくてはならない（大事なもの）**、0x10 重ねて持てる（`item.h:26-32`）。
- **英語名** = en.po のメッセージ `MsgItemName + id` = **386 + id**（`item_ids.h:7-8`、en.po:1579。`src/shop/shop/buy.c:350`、`src/window/window/decode.c:541` で使用）。`{article_class:N}` の接頭辞は取り除きます。名前があるのは id 0..268 だけです: 655 は `MsgEnemyName` です。説明 = `MsgItemPlainName`（117）+ id（`buy.c:68`）。確認済み: 1 Long Sword、180 Herb、181 Nut、268 Cleric's Ring（検証済み）。
- **アイコン。** `src/graphics/ui/menu_icons/item_000.png`..`item_254.png`: 16×16 のインデックス PNG で、それぞれ独自の 16 色パレットを持ち、インデックス 0 が透明です。ポインターテーブル: `gUiIcon_ItemIconPointers`（`src/graphics/ui/menu_icons.s:4-261`）。アイテムのアイコン = `items.tsv` の `icon`（`ItemDefinition.icon`、`item.h:109`）で、`ItemIcon_Compose`（`src/window/window/icons.c:114`）が描きます。数以上のインデックスは 0 になります（`icons.c:63-64`）。Herb → アイコン 117、Nut → 132。
  - **アトラスの規則:** アイコン k は 256×256 のシートの (k%16·16, k//16·16)。
  - アトラスを作って目で確認しました（作業用 `items/item_icon_atlas.png`、`items/item_preview.png`）: 剣、鎧、Herb の葉、鍵、オーブがすべて名前と一致します。
  - JA だけの版 `item_080_ja`/`item_098_ja` は EN では使われません。
  - 推定: ゲーム中のパレットは PNG に埋め込まれたものと同じ。
- **宝箱の値**（`include/field_scene.h:211-214`、`Field_SearchTile`、`src/object/object/events.c:429-560`）、検証済み:
  - `value & 0x0f000000 ≠ 0` → スクリプト（関数ポインター）。
  - それ以外では種類は `value & 0xfff00000`:
    - `0x100000` アイテム: 下位の半分 = アイテム id。2/3/4/5 以外のものもアイテムの経路を通ります。
    - `0x200000` コイン: `(u16)` → 0..65535。ゲームでは 1..999 を使います。
    - `0x300000` エナジーストーン: PP を全回復します。
    - `0x400000` メッセージ。
    - `0x500000` ミミック: 戦闘 `Encounter_GetEnemyGroupAtSlot(99, slot)`。ゾーン 99 は "Mimic chests"（`src/object/encounter.tsv` の 101 行目、グループ 350..357）。有効なのはスロット 0..7 だけです（`encounter.c:244`）。
  - `(value & 0xf0000) == 0x10000` → パーティーには「開けられない」（未使用）。
  - イベントの `condition` は開封フラグです: フラグが立っている間は宝箱が開いた状態で表示され、中身を取るとフラグが立ちます。パーティーの袋がいっぱいなら、アイテムは残りフラグも立たないままです（`events.c:565-590`）。
  - control `SEARCH(SEARCH_CHEST)` = 0x13。ビット 4..8 が「X を調べた」の文を選びます。
  - マーカーの宝箱 155 個の調査: アイテム 130、コイン 17、ミミック 8（0x500000..0x500007、それぞれ1回）。エナジーストーンやスクリプトを使う宝箱はありません。

**エディタのデータ:** `names/items.json`（`scripts/items/build_items.py` で生成）:
```json
[{"id":180,"symbol":"ITEM_HERB","symbol_in_header":true,"name":"Herb","description":"Replenishes 50 HP",
  "type":"none","type_id":0,"price":10,"flags":["stackable"],"key_item":false,"unused":false,
  "icon":117,"atlas":{"x":80,"y":112,"w":16,"h":16},"evidence":"items.tsv line 182; en.po msg 566"}]
```
選択画面の出力は `{"kind":"item","id":180}` → `FIND_ITEM(ITEM_HERB)`（0x1000b4）、`{"kind":"coins","n":50}` → `FIND_COINS(50)`、`{"kind":"mimic","slot":0..7}` → `0x500000|slot`、または `{"kind":"psynergy_stone"}` → `FIND_PSYNERGY_STONE` です。`unused`（名前が "?"/"???"/なし）の項目は隠し、`key_item` の項目には警告を付けます。アトラスはプレイヤーの alchemy チェックアウトから実行時に作り、決して同梱しません。

---

## 3. スプライト / NPC

- **id → オブジェクト**（検証済み）:
  - `Event_SpawnObjectTable`（`src/object/object/actors.c:97-118`）: id 0-7 = パーティーの枠で、`Party_RemapCharacterIdByFlags`（`actors.c:12-36`）が `FLAG_CHILDHOOD` のとき子ども時代のスプライト 0x12/0x13 に差し替えます。それ以外の id は行順にアクター枠 8 以降を使います（アクター = 8 + 行）。
  - 次に `Object_CreateFar(id)`、アニメーション 1 を選び、`facing` から角度を設定します。
  - `FieldObject_Create`（`src/field/field/objects.c:245-290`）: `id>>12` が種類です。種類 0 = スプライト1つ `id & 0xfff`。種類 2（0x2000|n）= 2 スプライトのグループ n、n+1。それ以外の種類はスプライトがなく、例 0x8000 = カメラ（`actors.c:266`）。
- **スプライトテーブル:** `gCharacter_DescriptorTable[id & 0xfff]`（`src/system/resource/metadata_get_record.c:7-9`）は `src/graphics/sprite/sprites.tsv`（513 行。行 = id。列は width、height、scale、drawKind、adjust、box、codec、frames、animations）から作られます。幅 0 = 画像なし（`src/field/field/animation.c:512`）。
- **PNG の規則**（`tools/ags-graphics/sprite.c:120-160,295-330`）:
  - フレームを持つ行の `graphics/sprite/spr_NNN.png`。別名の行は `SPR_X=SPR_Y` と書きます。
  - シートは縦の帯で、フレーム k は y = k·height にあります。任意の `spr_NNN.tsv` の `list` がフレームを並べ替え、その `anim` 行がアニメーションです。
  - パレット: 8bpp で、共有の 224 色 `gSystem_BasicColorPalette`（`src/runtime/runtime/text.c:199`）を使います。これはすべての PNG に埋め込まれ、インデックス 0 が透明です。
- **プレビューのフレーム:** アニメーション 1 の最初のフレームコマンド（239 未満の値がフレーム。240 で描画の種類を設定。254 で別のアニメーションへジャンプ。`src/field/field_internal.h:83-91`）に、その描画の種類での向きのオフセットを足したもの（`src/field/facing.c`、`src/field/field/sprite_draw.c:150-185` で適用。ビット 7 = 左右反転）。真正面の表示には向き 0x3800 を使います。ちょうど 0x4000 では、種類 3 と 5 は base+0 を反転して描きます。
- **特別な id:**
  - 20 宝箱（検証済み、`markers.c:70`）。
  - 28 エナジーストーン（検証済み、`markers.c:105`）。
  - 22 見えない 16×16 のマーカーで、カウンターやアイテムの場所に 68 回使われます。
  - 4 と 7 は空の行です。
  - 261-279 と 504 はワールドマップのアイコンです。
  - 配置テーブルは id 0..504 を使います。
- **名前。** スプライト全体の enum はありません。名前の出どころ:
  - `include/game/character_ids.h`。
  - ファイルローカルの `SPRITE_*` の enum（`src/scene/lunpa.h`、`vault_jail.c`、`tunnel_ruins.c`、`altin.c`、`altin_peak.c`、`tret_tree_*.c`、…）。
  - 行のコメント。

  これで 71 個の検証済みの名前になります。残りの 178 個は、画像とその id を使うシーンからの推定です（例 "Townsperson A"、"Dog"）。どちらかは `name_evidence` に書いてあります。
- コンタクトシートを目で確認しました: 正面のフレームと色は正しく、ゴミはありません。作業用の `sprites/contact_sheet_npc60.png` と `sprites/contact_sheet_all.png` です。

**エディタのデータ:** `names/sprites.json`（`scripts/sprites/build_sprites.py` で生成。`spritelib.py`、`usage.py`、`names.py`、`names_manual.py`、`sheet.py` を使用）:
```json
[{"id":28,"hex":"0x1c","name":"Psynergy Stone","confidence":"VERIFIED","name_evidence":"...",
  "usage":1,"scenes":["MogallForest1"],"party_slot":false,"has_image":true,
  "png":"games/tbs/src/graphics/sprite/spr_028.png","frame":{"x":0,"y":0,"w":16,"h":16},
  "frame_index":0,"mirrored":false,"palette":{...},"draw_kind":11,"animation":1,"base_frame":0,
  "sheet_frames":11,"scale":256,"adjust":[0,2],"box":[20,16],"evidence":"sprites.tsv row 28 ..."}]
```
UI は実行時に `png` を `frame` で切り抜きます（設定されていれば反転）。推定の名前には、エディタ側に「名前を編集」用の上書きファイルを持つことを勧めます。

---

## 4. 地名

- `Scene_GetAreaNameIndex(scene, entrance)`（`src/object/object/encounter.c:326-350`）は `gScene_AreaNameRules`（`src/object/scene_rules.s:168-301`）をたどります。各行は `scene_name Scene, entrance, index` または `group_name group, entrance, index` です（`scene_rules.s:12-20`）。一致する**最初の**行が採用され、入口 -1 はどの入口にも一致します。グループ = `gField_SceneTable[scene].group`（`src/object/object/scene.c:157-159`、`src/field/scenes.s` の列）。一致しなければインデックス 0 です。（検証済み）
- テキスト = メッセージ **`MsgDebugEntryName` + インデックス**（`src/object/psynergy_effects/world_map.c:400`、`src/window/battle_command/debug.c:23`）。EN では `MsgDebugEntryName` = 2459 = パッチ済みの非ヨーロッパ版の `RENDER_RESOURCE_BASE` 0x99B（`include/tbs_edition.h:264-271`、`src/window/window/shortcuts.c:29` で使用）。基準値は定数としてではなく、en.po の `msgctxt "MsgDebugEntryName"` から読んでください。（検証済み）
- `.if EDITION_INTERNATIONAL` の行（Altin Peak 4、入口 6/7）は EN では有効です（`include/game/ed_asm.h:11-16`）。
- 結果:
  - 201 シーン中 199 に名前が付きます。Title（0）と LinkLobby（190、入口 1 のときだけ名前あり）には付きません。
  - 21 シーンには `scenes.s` のシンボルがないので、「Scene N」とその地域名で表示します。
  - 入口ごとの名前もあります。例: Sanctum: 1/2/20/21 Vale Sanctum、10-12 Vault Sanctum、35 Bilibin、32 Xian、29 Altin。VaultJail の入口 2 = "Lunpa"。
  - 表示: 「{area_name} — {label}」、例 "Vale — Vale Home"。地域名は多くのシーンで重なるので、シーンのラベルで区別します。

**エディタのデータ:** `names/places.json`（`scripts/places.py` で生成）:
```json
{"area_message_base":2459,
 "scenes":[{"id":5,"symbol":"ValeHome","label":"Vale Home","group":3,"variant":2,"overlay":"0x374",
            "layered_row":4,"map":"003","area_index":10,"area_name":"Vale",
            "area_name_by_entrance":{},"area_message":2469}]}
```

---

## 5. 会話

- **en.po の仕組み**（検証済み）。各項目は `msgctxt "<symbol>|message"`、`msgid "NNNNN"`（メッセージ番号、5 桁にゼロ埋め）、`msgstr`（テキスト）です。項目は 0..10722 の 10,723 個で、欠番はありません。シンボルは `out/tbs-en/text/msg_ids.h` として出力されます（`#define TEXT_MESSAGE_NUMBER_<Sym> n`、`MSGNO(name)`）。シーンの C はテーブルでは `MSGNO(MsgX)`、コードでは素の `MsgX` と書きます（`src/scene/README.md:60-61`）。
- **テキストのマークアップ:** `{page_break}`（新しい枠）、`{end_wait}` / `{end_now}`（終了）、`{line_break}`、引数 `{protagonist_name}`、`{actor_name:N}`、`{argument_item_name:N}`、`{text_color:…}`、`{article_class:N}`（`tools/ags-text/symbols.c:28-60`）。リテラルの `\n` は表示上の行です。名前は "[Isaac]" のようなプレースホルダーとして表示します。
- **話しかけの検索**（`Scene_TalkToActor`、`src/object/object/events.c:197-290`、`Scene_FindEvent` `:111-165`）:
  - 種類 0 `EVENT_TALK`、トリガー = アクター id = 8 + 配置の行。
  - 条件を満たす最初の行が採用されるので（-1 は常に。`flag|0x1000` = 立っている。それ以外は立っていない）、NPC はストーリーフラグで選ばれる複数の行を持てます。
  - `value < 0x10000` → メッセージ1つ。直接の話しかけメッセージ 881 個はすべて `{end_*}` で終わるので（調査）、id 1つがセリフ全体です。
  - それ以外の値はスクリプトです。種類 7 は、パーティーがアクターを止めたときのセリフです（`events.c:175-186`）。
  - `talkFacing` が振り向きを制御します。
- スクリプトの場合、会話は関数本体にある `Msg*` シンボルです。例: `Event_TalkAboutTheMayorAndTremors`（`src/scene/vale.c:160`）は、`FLAG_PARTY_LEFT_VALE` に応じて `MsgValeTheGroundStillShakes` か `MsgValeYourGrandpaIsTheMayor` を表示します。これで得られるのはありうるセリフの一覧で、順番や条件ではありません（推定: プレビューには十分）。
- 調べる場所は `MsgTileChecked + target` を表示し、その後に `FIND_MESSAGE` または結果のテキストを表示します（`events.c:452-470`）。

**エディタのデータ:** `dialogue.json`（作業用、650 KB、`scripts/dialogue.py` で生成。152 シーン、話しかけの行 2,475 個）。ゲームのテキストを含むので、エディタは実行時に生成します:
```json
{"4":{"symbol":"Vale","tables":{"gVale_Events":[
  {"actor":8,"placement_row":0,"kind":"talk|talk_paused","condition":null|{"flag":2069,"when":"set|clear"},
   "message":3967,"msgctxt":"MsgValeMtAlephLooksBeautifulTodayIts","text":"Mt. Aleph looks\nbeautiful today..."},
  {"actor":10,"placement_row":2,"kind":"talk","condition":null,"script":"Event_TalkAboutTheMayorAndTremors",
   "source":"src/scene/vale.c","script_messages":[{"message":4556,"text":"..."}]}]}}}
```
テキストの編集とは、`text/en.po` の `msgstr` を msgid で編集することです。他の 5 言語のカタログは同じ msgid の集合を保たなければなりません（`src/game/README.md:97-110`）。

---

## 6. フラグ

- **保存場所:** `gGameFlagBytes` の 4,096 ビット。フラグ番号のビット 0-2 がビットを、ビット 3-11 がバイトを選びます（`src/game/game/flags.c:7-24`、`include/game/game_flags.h:12`）。バイト単位のアクセサーは連続する 8 フラグを1つのカウンターとして扱います（`src/game/README.md:110-121`）。すべてセーブされます（README。セーブのチェックサムは `gGameFlagBytes` を含む、`include/save_state.h:55`）。
- **条件:** `-1` は常に、`flag|0x1000` = 立っている、それ以外はフラグが立っていない。配置での 0 = 「視界内」（`events.c:59-77`）。
- **範囲**（`src/scene/README.md:48-59`、`include/flags.h:7-20`）:
  - 0x000-0x0ff: パーティー（0-7）とジン（48-127）。
  - 0x100-0x1ff: エンジン/システム。
  - **0x200-0x2ff: シーンの一時フラグ。入口を通るたびに消去されます。**
  - **0x300-0x3ff: グループのフラグ。別のグループに入るとリセットされ、番号は場所ごとに使い回されます。**
  - 0x400-0x7ff: 用途が見つからない（参照は 0x400 の1つだけ。推定: 未使用だが避けること）。
  - 0x800-0xdff: ストーリー。
  - 0xe00-0xfff: 宝箱/発見のフラグ。
- **名前:** `include/flags.h`（970 行）の `#define FLAG_* value` と `///` コメント。例 `FLAG_ALTIN_PEAK_LUCKY_MEDAL 0xf78 ///< room 8's chest`。シーンローカルのフラグはシーン自身のファイルで `#define` されており、flags.h にはありません。
- **使用状況の調査**（`flags_survey.py`、元データの範囲で検証済み）:
  1. ビルド済みのオーバーレイテーブルにあるすべての condition、requiredFlag、出口のフラグ、エリアの条件。
  2. 各 `src/**/*.c` の `clang -E` 出力にある、定数引数を持つすべてのフラグアクセサー呼び出し。出力は標準出力だけに出し、alchemy には触れません。
  3. `scene_rules.s` と `location_rules.s` にある `scene_cue`/`group_cue`/`location` 行のフラグ欄。
  4. flags.h のすべての define。

  使用中と判明したもの: 0xe00-0xfff 213/512、0x800-0xdff 300、0x300-0x3ff 108。
- **控えめな空きリスト**（`flags_free.py`）: さらに、`src`/`include` のどこか（グラフィックとマップデータを除く）に 16 進リテラルとして現れる 0xe00..0xfff の値（またはその 0x1e00 の条件形）を除外します。残るのは **251 個の空き** フラグです。連続範囲: 0xe03-0xe0f、0xe49-0xe58、0xe61-0xe73、0xe81-0xea1、0xef8-0xeff、0xf09-0xf12、0xfdb-0xfe0、…（`flags.json` の `free_chest_flags`）。
- **新しい宝箱への割り当て規則:**
  1. `free_chest_flags` の中で、mod 自身の上書きテーブル（`games/tbs/src/mod/`）や他の保留中の編集がまだ使っていない、最も小さいフラグを取ります。
  2. それを `SEARCH(SEARCH_CHEST)` イベントの condition として書きます。
  3. 宝箱を削除した後でも二度と再利用しないよう、mod のマニフェストに記録します（古いセーブでは立っているかもしれません）。
  4. alchemy の固定バージョンを上げるたびに調査を再実行して確認し直します。空きリストはコミットに依存します。
- **フラグが未使用かの確認**、次の順で:
  1. 新しく実行した `flags_survey.py`（テーブル + コード + 規則）の `used` にないこと。
  2. 16 進リテラルの一致がないこと（`flags_free.py`）。
  3. バイト単位アクセサーのフラグのバイトに含まれていないこと（調査は 8 個すべてに印を付けます）。
  4. 0x200-0x3ff にないこと。
  5. ビルド後にオーバーレイの `.bin` をハーフワードで `grep` するのは信頼**できない**（誤検出がある）ので、1-4 に頼ってください。

**エディタのデータ:** `names/flags.json`（2つのスクリプトから生成）:
```json
{"total_flags":4096,
 "ranges":[{"lo":3584,"hi":4095,"meaning":"chest / find flags","editor":"allocate new chest flags here"}],
 "names":{"0xf78":["FLAG_ALTIN_PEAK_LUCKY_MEDAL"]},
 "used":{"0xf78":["flags.h","table 3a4:gAltinPeak_Events..."]},
 "free_chest_flags":[3585,3587,...]}
```

---

## 生成したファイルとその作り方

スクリプトはすべて `names/scripts/`（コピー）と上記の作業用ディレクトリにあります。gs-mapedit の `gsmap`（Project、Scenes、grid）と `out/tbs-en` に依存します。

| ファイル | スクリプト | 入力 |
|---|---|---|
| `names/collision.json` | `collision_json.py`（`coll_hist.py` の後） | 上記のエンジンの読み、`src/map/*/grid_collision.tsv` のヒストグラム |
| 作業用 `collision_by_map.json` | `collision_legend.py` | グリッド + ビルド済みのイベント/出口テーブル + `places.json` + `items.json` + en.po |
| `names/items.json` | `items/build_items.py` | `src/game/items.tsv`、en.po、`item_ids.h`、`graphics/ui/menu_icons/` |
| 作業用 `items/search_events.json` | `items/survey_chests.py` | ビルド済みのイベントテーブル |
| `names/sprites.json` | `sprites/build_sprites.py`（+ `spritelib.py`、`usage.py`、`names.py`、`names_manual.py`、`sheet.py`） | `graphics/sprite/sprites.tsv`、`spr_*.png`/`.tsv`、ビルド済みの配置テーブル、シーンのソース |
| `names/places.json` | `places.py`（+ `po.py`） | `src/field/scenes.s`、`src/object/scene_rules.s`、en.po、gsmap 経由の `layered.tsv` |
| 作業用 `dialogue.json` | `dialogue.py` | ビルド済みのイベントテーブル、オーバーレイの ELF シンボル、`src/scene/**`、`out/tbs-en/text/msg_ids.h`、en.po |
| `names/flags.json` | `flags_survey.py` → `flags_free.py` → その場で統合 | ビルド済みのテーブル、`src/**/*.c` の `clang -E`、規則の `.s` ファイル、flags.h |

画像（アイコンのアトラス、コンタクトシート）とゲームのテキストは意図的にコミットしていません。PRODUCT.md の法的な方針に従い、アプリはそれらをプレイヤーのチェックアウトから作ります。

## 未解明の点

- 248 の意味（読む処理がなく未使用）と、241 が期待どおりに動くか（どのマップも使っていない）。
- コード 96..99（Altin Peak）と、1..239 の (マップ, コード) の組 136 個には静的なイベントがありません。おそらくシーンのコード（`GetMapCellCollision` の呼び出し元）が読んでいるか、残り物です。
- **ワールドマップ** の衝突の意味は別の仕組みです（`blocks.tsv` のステップバイト、`attributes.tsv`）: `overworld.md` を参照してください。
- `touched_trigger` を書き込むもの、および 22 個の宝箱にある event control の上位ビット（0x400、0x8400、0xc400）。*トリガー* のビット 0x400 は「調べた」の文を飛ばします。control のビットの意味は確認できていません。
- アイテムアイコンのゲーム中のパレットの枠（PNG のパレットだと仮定しています）。
- 推定した 178 個のスプライト名。一部は当て推量です（例 44 "Dodonpa"、66/67、69 "Lady Layana"）。0x2705 のアクターインデックスの区切りはソースで XXX と印が付いています。JA/IT は `spriteja.tsv`/`spriteit.tsv` を使います。
- `{end_*}` のないメッセージが次の id に続けて表示されるかどうか。直接の話しかけメッセージにはそれがないものはないので、プレビューには関係ありません。
- フラグの調査は、変数や計算式を通してしか参照されないフラグ（定義やループを含む、定数でないアクセサー呼び出し 5,191 個）と、C のデータ配列にあるフラグを見落とします。16 進リテラルの確認がその大半をカバーします。0x400-0x7ff は未使用に見えますが、証明されてはいません。
- ミミックのスロットが 7 を超えても安全かどうか（次のゾーンを読んでしまうので、役には立ちません）。
