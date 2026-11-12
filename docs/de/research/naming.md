<!-- translated from docs/research/naming.md @ 3e642cd20a29 -->
# Namensschicht: Kollisionscodes, Gegenstände, Sprites, Orte, Dialoge, Flags (TBS)

_Dies ist eine Übersetzung der englischen Datei [naming.md](../../research/naming.md). Wenn sich die beiden unterscheiden, gilt die englische Fassung._

> **Seit dieser Text geschrieben wurde:** Die unten beschriebenen Namenstabellen werden nicht mehr mitgeliefert. `gsmap/names.py` liest die Namen zur Laufzeit aus dem Checkout (`en.po`, `flags.h`, `sprite_ids.h`, `item_table.c`, `scenes.s`, `scene_rules.s`). `gsmap/data` enthält nur noch Vorschauframes, freie Truhen-Flags und unsere eigenen Beschreibungen der Begehbarkeit.

Quellbaum: `alchemy/` (nur lesend), englischer Build `out/tbs-en`. Die Pfade sind relativ zu `alchemy/games/tbs/`, sofern sie nicht mit `out/` oder `tools/` beginnen. **VERIFIZIERT** bedeutet: im Code oder in den Daten gelesen oder per Skript über alle Dateien geprüft. **ERSCHLOSSEN** bedeutet: abgeleitet und nicht bewiesen. Erzeugte Daten liegen in `docs/research/names/`. Die Skripte, die sie erzeugen, sind nach `docs/research/names/scripts/` kopiert; die Originale und die Zwischendateien liegen im Arbeitsverzeichnis `(a scratch folder)`.

## Zusammenfassung

1. **Kollisionscodes** gibt es in drei Gruppen: globale Engine-Bedeutungen, Szenen-Trigger und Markierungen. (VERIFIZIERT)
   - **Globale Bedeutungen:**
     - 0 Boden
     - 240/241 Begegnungsboden
     - 242..247 feste leere Suchstellen: Krug, Fass, Kiste, Grab, Bücher, Brunnen
     - 249 Kettensprung
     - 250 Gefahr
     - 251 Cloak-Schatten
     - 252 Kante
     - 253 Klettern
     - 254 Sprunglücke
     - 255 Wand
   - **1..239 sind Szenen-Trigger.** Ihre Bedeutung ergibt sich aus den Ereignistabellen der Szene: ein Ausgang, ein Berührungsskript oder eine Suche.
   - **Markierungen (Truhen und Steine) können nur 100..239 verwenden.**
   - Der Editor sollte 1..239 pro Karte anhand der Ereignisse benennen. `collision_by_map.json` (Arbeitsdatei) ist genau diese Legende, bereits aufgelöst: bei Ausgängen der Zielort; bei Skripten der Skriptname; bei Suchen der Gegenstand oder der Text.
2. **Gegenstände:**
   - Name = Meldung `MsgItemName` (386) + ID.
   - Symbol = `items.tsv`-Spalte `icon` → `graphics/ui/menu_icons/item_{icon:03d}.png` (16×16, eingebettete Palette).
   - Truheninhalt = `FIND_ITEM(id)` = `0x100000|id`, `FIND_COINS(n)` = `0x200000|n`, Mimic = `0x500000|slot` (Slots 0..7) oder `FIND_PSYNERGY_STONE` = `0x300000`.
   - (VERIFIZIERT)
3. **Sprites:**
   - Die Sprite-ID einer Platzierung wird direkt als Zeile von `graphics/sprite/sprites.tsv` (513 Zeilen) verwendet.
   - Ihre Grafik ist `graphics/sprite/spr_NNN.png`, ein senkrechter Streifen aus w×h-Frames, gezeichnet mit der gemeinsamen OBJ-Palette aus 224 Farben.
   - Der Vorschauframe ist der erste Frame von Animation 1 plus der Blickrichtungs-Offset.
   - 249 IDs sind abgedeckt, darunter alle 219 verwendeten. 71 Namen sind VERIFIZIERT (Symbole und Kommentare der Dekompilierung); 178 sind aus dem Bild und den Szenen, die sie verwenden, ERSCHLOSSEN.
4. **Orte:**
   - `gScene_AreaNameRules` (`src/object/scene_rules.s:168`) gibt jeder Szene oder Gruppe (optional pro Eingang) einen Gebietsindex.
   - Der Text ist die Meldung `MsgDebugEntryName` (2459 in EN) + Index.
   - 199 von 201 Szenen erhalten einen Namen. (VERIFIZIERT)
5. **Dialoge:**
   - Die `msgid` in `en.po` ist die mit Nullen auf 5 Stellen aufgefüllte Meldungsnummer. `msgctxt` ist der Symbolname, oder `message`, wenn die Meldung keinen hat.
   - Ein `SceneEvent`-Wert unter 0x10000 ist eine Meldungsnummer. Darüber ist es ein Skript; seine Zeilen sind die `Msg*`-Symbole in seinem Rumpf.
   - Der Trigger eines Gesprächsereignisses ist die Akteurnummer, also 8 + Platzierungszeile.
   - (VERIFIZIERT)
6. **Flags:**
   - Es gibt 4,096 Flags (0..0xfff).
   - Neue Truhen sollten Flags aus **0xe00..0xfff** nehmen, und zwar nur Flags, auf die keine Tabelle, kein Code und kein Literal verweist. **251 sind frei** (`flags.json` `free_chest_flags`), die niedrigsten sind 0xe01, 0xe03..0xe0f usw.
   - Niemals 0x200..0x3ff verwenden: Das sind Szenen- und Gruppen-Temporärflags, die zurückgesetzt werden.

---

## 1. Kollisionscodes

### 1.1 Bedeutung in der Engine (VERIFIZIERT, sofern nicht anders markiert)

Der Code einer Zelle ist `struct MapCell.collisionCode` (`include/map.h:13-22`), gelesen aus dem Fenster der Ebene des Anführers (`terrainId`), jeweils eine 16-px-Zelle.

| Code | Name (für Spieler) | Verhalten in der Engine | Beleg | Editor |
|---|---|---|---|---|
| 0 | **Fußboden** | Begehbar. Verwendet Begegnungsboden 0, auf dem es keine Begegnungen gibt, es sei denn, die Ortsregel der Szene mit shift = 1 legt die erste Zone darauf. | `src/object/object/step.c:240-276`; `src/object/object/encounter.c:76-90`; `src/object/location_rules.s:1-7` | Pinsel |
| 1..239 | **Trigger** (Ausgang / Ereignis / Suche) | Betreten der Zelle setzt `work->action = code` (`step.c:247`). `Scene_RunTouchOrExit` führt zuerst das `EVENT_TOUCH` der Szene mit diesem Trigger aus (Meldung oder Skript); gibt es keins, verwendet es `EVENT_EXIT`, dessen Wert die Ausgangsart ist (`events.c:333-380`). Drücken von A auf die Zelle davor sucht `EVENT_SEARCH` mit demselben Code (`run_scene.c:440-450`). Auch Ereignisse vom Typ `USE_ITEM` und `PSYNERGY_IN_AREA` können darauf reagieren. Jeder von null verschiedene Code prüft außerdem die Ausgangsbereiche (`step.c:244-245`). | wie angegeben | Trigger: pro Karte aus den Ereignissen benannt (§1.3) |
| 100..239 | **Truhen- / Stein- / Such-ID** | Alles aus 1..239, dazu: Das ist der einzige Bereich, den `Field_PlaceMapMarkers` akzeptiert (`markers.c:57`). Ein Ereignis `SEARCH(SEARCH_CHEST)` zeigt eine Truhe (Objekt 20, `markers.c:70`); `FIND_PSYNERGY_STONE` zeigt einen Stein (Objekt 28, `markers.c:105`). | | Trigger; gehören den Markierungen |
| 240 | **Monsterboden** | Begehbar. Begegnungen verwenden `encounterGroups[1]`, die erste Zone der Regel, statt Boden 0. Häufig als Dungeonboden: 23 Karten, z. B. map_009 (133 Zellen). | `step.c:22-23,264-267` | Pinsel |
| 241 | Monsterboden 2 | Wie 240, verwendet aber `encounterGroups[2]`. **Keine Karte verwendet ihn.** | `step.c:22-23` | Pinsel (fortgeschritten) |
| 242 | Leerer Krug | Beim Untersuchen kommt „checked the jar… but didn't find anything“. Meldungs-Offset 2 ab `MsgTileChecked` (2344) und `MsgTileResult` (2376). Greift nur, wenn der Boden davor 0..64 px über dem Anführer liegt. | `src/object/fxdata.c:22-31`; `events.c:439-448`; `run_scene.c:441-447` | Pinsel |
| 243 | Leeres Fass | Offset 3 | ebenso | Pinsel |
| 244 | Leere Holzkiste | Offset 13 | ebenso | Pinsel |
| 245 | Leeres Grab | Offset 8 | ebenso | Pinsel |
| 246 | Bücherregal (Bücher) | Offset 30 | ebenso | Pinsel |
| 247 | Brunnen | Offset 31. In Karten nicht verwendet. | ebenso | Pinsel |
| 248 | (ungenutzt) | Kein Leser gefunden, und keine Karte verwendet ihn (ERSCHLOSSEN wirkungslos). | — | nicht anfassen |
| 249 | **Trittsteinsprung** | Wird von `Field_ProcessStep` nie ausgelöst. Nach einem Vorwärtssprung springt man beim Landen auf 0xf9 erneut (verkettete Sprünge). In 3 Karten verwendet (029, 098, 148). | `events.c:383-405`; `src/object/psynergy_effects/climbing.c:18-23,99-103` | Pinsel (fortgeschritten) |
| 250 | **Gefahrenboden** | Beim Gehen steigt der Gefahren-Schrittzähler, und bei `hazardLimit` erleidet die Gruppe `hazardDamage`. Die Szene legt Modus, Grenze und Schaden fest. Karten 063-067. | `step.c:24,293-327` | Pinsel |
| 251 | **Schatten (Cloak)** | Begehbar. Cloak hält die Gruppe nur auf diesem Code verborgen; wer ihn verlässt, beendet Cloak (`CLOAK_TILE`). Karten 111 und 130-142 (Lunpa Fortress, Altmiller Cave…). | `src/object/psynergy_effects/cloak.c:7-11,71` | Pinsel |
| 252 | **Kante (hinunterspringen)** | Drückt man mehr als 12 Frames lang mit gehaltenem Unten dagegen, springt der Anführer hinunter. | `step.c:25-27,249`; `events.c:394-399` | Pinsel |
| 253 | **Kletterwand / Leiter** | Mehr als 12 Frames drücken: Oben klettert hinauf, Unten hinab. Beim Klettern ist ein Schritt nur in eine Zelle mit demselben Code erlaubt. Kommt man auf zwei übereinanderliegenden 0xfd-Zellen mit y≠0 an, beginnt die Gruppe im Klettermodus. | `events.c:407-415`; `src/field/field/player_control.c:874-881`; `src/object/object/actors.c:250-262` | Pinsel |
| 254 | **Sprunglücke** | Mehr als 12 Frames drücken: Der Anführer springt 2 Zellen vorwärts, wenn die Landestelle es erlaubt (`Field_TryJumpForward`). 77 Karten. | `events.c:400-405`; `climbing.c:13-30` | Pinsel |
| 255 | **Wand** | Blockiert immer (`Map_CheckObjectStep` gibt 2 zurück). | `src/field/field/terrain.c:477,526` | Pinsel |

Die Begehbarkeit hängt auch von der Höhe ab. Ein Schritt mehr als 8 px nach oben oder mehr als 12 px nach unten wird abgelehnt (`terrain.c:494-497`), ein „Boden“-Code auf einer Klippe ist also trotzdem blockiert. Die Begehbarkeits-Überlagerung sollte den Code mit den Höhen aus `grid_shape` kombinieren. Wasser ist in den lokalen TBS-Karten **kein** Kollisionscode: Es ist Wand oder Höhe, und Pfützen und Ähnliches sind Szenen-Trigger (ERSCHLOSSEN aus dem Histogramm: kein eigener Code).

Codes auf Zellen werden außerdem zur Laufzeit vom Szenencode geändert (`SetMapCellCollision`, `terrain.c:422`), in Colosso, Altin Peak, Crossbone Isle, Venus Lighthouse, Tolbi und Sol Sanctum. Die Codes 96..99 in den Karten 078-083 (Altin Peak) haben kein statisches Ereignis, werden also per Skript gelesen (ERSCHLOSSEN).

### 1.2 Nutzungshistogramm (VERIFIZIERT durch `coll_hist.py`, 182 Karten, Zellen in den 3 Ebenenfenstern)

| Code | Zellen | Karten | Anmerkung |
|---|---|---|---|
| 0 | 1,300,642 | 182 | Boden |
| 255 | 47,077 | 151 | Wand |
| 240 | 4,308 | 23 | Monsterboden (Dungeons/Wälder: 009, 016, 025-030, 043, 046, 050, 055, 056, 062, 064, 066, 067, 078, 133, 136, 137, 164, 166, 167) |
| 21 | 4,244 | 34 | z. B. Lamakan Desert Karte 091: 2,677 Zellen mit `EVENT_TOUCH 21 → HeatGauge_CountStep` |
| 251 | 1,729 | 9 | Cloak-Schatten |
| 10 / 30 / 11 / 1 / 2 | 963 / 683 / 357 / 340 / 255 | 96 / 23 / 78 / 150 / 140 | niedrige Codes sind meist Ausgänge und Berührungsskripte von Türen |
| 254 / 253 / 252 | 928 / 484 / 59 | 77 / 60 / 28 | Sprung / Klettern / Kante |
| 243 / 244 / 242 / 245 / 246 | 500 / 482 / 388 / 32 / 18 | 29 / 29 / 28 / 6 / 3 | leere Fässer/Kisten/Krüge/Gräber/Bücher |
| 100..107 | 100, 67, 37, 21, 8, 5, 3, 4 | 95..3 | Truhen (`SEARCH_CHEST` 66× auf 100) und andere Suchen |
| 200..212 | 2..35 | 14..1 | Suchstellen ohne Markierung (versteckte Gegenstände in Krügen/Fässern…) |
| 250 | 77 | 4 | Gefahr |
| 249 | 3 | 3 | Sprung |
| 241, 247, 248 | 0 | 0 | ungenutzt |

Die Ereignisarten hinter 1..239 über alle Karten (Anzahl = Karten): Code 1 → EXIT 130, TOUCH 44; Code 10 → TOUCH 65, EXIT 36; 100 → SEARCH_CHEST 66, SEARCH 36. Vollständige Tabelle: `coll_hist.json` (Arbeitsdatei). 136 Paare (Karte, Code) in 1..239 haben in den Szenen, die die Karte verwenden, **kein** statisches Ereignis. Sie werden von Skripten verwendet oder sind Überbleibsel: als „Geskriptet / unbekannt“ anzeigen.

### 1.3 Legende pro Karte (VERIFIZIERT, erzeugt)

`collision_legend.py` schreibt `collision_by_map.json` (Arbeitsdatei, 1 MB). Für jede Karte enthält sie:
- `scenes`;
- `cells_per_layer`, ein Code-Histogramm für jedes Ebenenfenster;
- `events_by_code[code]`, eine Liste von `{scene, table, kind: exit|touch|search|use_item|raised, control, condition, …}`, wobei:
  - ein Ausgang `exit_kind, to_scene, to_entrance, to_name, to_symbol` hat;
  - ein Skript `script` hat (das ELF-Symbol, z. B. `Event_EnterSanctum`, `HeatGauge_CountStep`);
  - eine Meldung `message, text` hat;
  - eine Suche `search_target` (einer der 32 `SearchTarget`-Namen, `include/field_scene.h:176-209`), `marker_chest` und `find_item/item_name | find_coins | psynergy_stone | mimic_slot` hat;
  - eine Berührung `needs_push` (0x200) und `needs_facing` (0x400) hat.

Die Beschriftungsregel für die Oberfläche lautet:
- „Ausgang → {to_name}“
- „Ereignis: {humanized script}“
- „Truhe: {item}“
- „Untersuchen {target}: {item | text}“

Gibt es kein Ereignis, lautet die Beschriftung „Ungenutzter Trigger“. Mehrere Tabellen pro Szene werden über Story-Flags gewählt, die Oberfläche sollte also die Vereinigung zeigen und sie als „hängt von der Story ab“ kennzeichnen.

**Editor-Daten:** `names/collision.json` (erzeugt von `collision_json.py`):
```json
{"notes":[...],
 "ranges":[{"lo":0,"hi":0,"name":"Floor","category":"walk|block|move|search|trigger|unknown",
            "editor":"brush|trigger|trigger (markers own 100..239)|brush (advanced)|don't-touch",
            "meaning":"...","evidence":["src/...:lines"],"confidence":"VERIFIED","color":"#rrggbbaa"}],
 "codes":[{"code":240,"hex":"0xf0","range":"240-240","cells":4308,"maps":23}]}
```
Dazu eine beim Laden erzeugte Legende pro Karte in der Form von `collision_by_map.json` (`{map: {scenes, cells_per_layer[3]{code:count}, events_by_code{code:[event…]}}}`). Der Editor sollte sie zur Laufzeit aus den gebauten Overlays (gsmap `Scenes`) erstellen, statt sie mitzuliefern.

Pinselpalette für Spieler: Boden, Monsterboden, Wand, Kante, Klettern, Sprunglücke, Schatten, Gefahr sowie leerer Krug/Fass/Kiste/Grab/Bücher. Trigger (1..239) werden nie frei gemalt. Sie entstehen durch Aktionen wie „Tür hinzufügen“ oder „Truhe hinzufügen“, die einen auf dieser Karte ungenutzten Code vergeben (und für Nicht-Markierungen unter 100).

---

## 2. Gegenstände

- **IDs und Symbole.** `include/item_ids.h` benennt nur die IDs, die der Code verwendet (VERIFIZIERT). Die Gegenstandstabelle `src/game/items.tsv` hat eine Zeile pro ID (ID = Zeile − 2, 324 Zeilen), eine Spalte `label` mit dem englischen Namen und die Spalten price, type, flags, equip_mask, icon, … Die Struktur ist `ItemDefinition`, 0x2c Bytes (`include/game/item.h:104-137`).
  - Typen: 0 keiner (Verbrauchsgegenstand/Schlüssel), 1 Waffe, 2 Rüstung, 3 Schild, 4 Helm, 5 Stiefel, 6 Psynergie-Gegenstand, 8 Ring, 9 Hemd (`item.h:43-55`).
  - Flags: 1 verflucht, 2 nicht ablegbar, 4 selten, **8 unverzichtbar (Schlüsselgegenstand)**, 0x10 stapelbar (`item.h:26-32`).
- **Englischer Name** = en.po-Meldung `MsgItemName + id` = **386 + id** (`item_ids.h:7-8`, en.po:1579; verwendet in `src/shop/shop/buy.c:350`, `src/window/window/decode.c:541`). Das Präfix `{article_class:N}` entfernen. Nur die IDs 0..268 haben Namen: 655 ist `MsgEnemyName`. Beschreibung = `MsgItemPlainName` (117) + id (`buy.c:68`). Geprüft: 1 Long Sword, 180 Herb, 181 Nut, 268 Cleric's Ring (VERIFIZIERT).
- **Symbole.** `src/graphics/ui/menu_icons/item_000.png`..`item_254.png`: indizierte 16×16-PNGs, jedes mit eigener 16-Farben-Palette, Index 0 transparent. Zeigertabelle: `gUiIcon_ItemIconPointers` (`src/graphics/ui/menu_icons.s:4-261`). Das Symbol eines Gegenstands = `items.tsv` `icon` (`ItemDefinition.icon`, `item.h:109`), gezeichnet von `ItemIcon_Compose` (`src/window/window/icons.c:114`); ein Index ≥ Anzahl wird zu 0 (`icons.c:63-64`). Herb → Symbol 117, Nut → 132.
  - **Atlas-Regel:** Symbol k bei (k%16·16, k//16·16) in einem 256×256-Bogen.
  - Der Atlas wurde gebaut und mit bloßem Auge geprüft (Arbeitsdateien `items/item_icon_atlas.png`, `items/item_preview.png`): Schwerter, Rüstungen, Herb-Blatt, Schlüssel und Kugeln passen alle zu ihren Namen.
  - Die nur japanischen Varianten `item_080_ja`/`item_098_ja` werden von EN nicht verwendet.
  - ERSCHLOSSEN: Die Palette im Spiel entspricht der im PNG eingebetteten.
- **Truheninhalte** (`include/field_scene.h:211-214`; `Field_SearchTile`, `src/object/object/events.c:429-560`), VERIFIZIERT:
  - `value & 0x0f000000 ≠ 0` → ein Skript (Funktionszeiger).
  - Sonst ist der Typ `value & 0xfff00000`:
    - `0x100000` Gegenstand: untere Hälfte = Gegenstands-ID; alles, was nicht 2/3/4/5 ist, nimmt ebenfalls den Gegenstandsweg.
    - `0x200000` Münzen: `(u16)` → 0..65535; das Spiel verwendet 1..999.
    - `0x300000` Psynergie-Stein: stellt alle PP wieder her.
    - `0x400000` Meldung.
    - `0x500000` Mimic: Kampf `Encounter_GetEnemyGroupAtSlot(99, slot)`. Zone 99 ist „Mimic chests“ (`src/object/encounter.tsv` Zeile 101, Gruppen 350..357). Nur die Slots 0..7 sind gültig (`encounter.c:244`).
  - `(value & 0xf0000) == 0x10000` → „Can't open it“ für die Gruppe (ungenutzt).
  - Die `condition` des Ereignisses ist das Geöffnet-Flag: Die Truhe wird geöffnet angezeigt, solange das Flag gesetzt ist, und das Flag wird beim Entnehmen des Inhalts gesetzt. Ist der Beutel der Gruppe voll, bleibt der Gegenstand liegen und das Flag bleibt ungesetzt (`events.c:565-590`).
  - Steuerwert `SEARCH(SEARCH_CHEST)` = 0x13. Die Bits 4..8 wählen die Zeile „checked the X“.
  - Erhebung über 155 Truhen mit Markierung: 130 Gegenstände, 17 Münzen, 8 Mimics (0x500000..0x500007, jeder einmal). Keine Truhe verwendet einen Psynergie-Stein oder ein Skript.

**Editor-Daten:** `names/items.json` (erzeugt von `scripts/items/build_items.py`):
```json
[{"id":180,"symbol":"ITEM_HERB","symbol_in_header":true,"name":"Herb","description":"Replenishes 50 HP",
  "type":"none","type_id":0,"price":10,"flags":["stackable"],"key_item":false,"unused":false,
  "icon":117,"atlas":{"x":80,"y":112,"w":16,"h":16},"evidence":"items.tsv line 182; en.po msg 566"}]
```
Die Ausgabe der Auswahl ist `{"kind":"item","id":180}` → `FIND_ITEM(ITEM_HERB)` (0x1000b4), `{"kind":"coins","n":50}` → `FIND_COINS(50)`, `{"kind":"mimic","slot":0..7}` → `0x500000|slot` oder `{"kind":"psynergy_stone"}` → `FIND_PSYNERGY_STONE`. Einträge mit `unused` (Name „?“/„???“/keiner) ausblenden und Einträge mit `key_item` mit einer Warnung kennzeichnen. Der Atlas wird zur Laufzeit aus dem alchemy-Checkout des Spielers gebaut, nie mitgeliefert.

---

## 3. Sprites / NPCs

- **ID → Objekt** (VERIFIZIERT):
  - `Event_SpawnObjectTable` (`src/object/object/actors.c:97-118`): Die IDs 0-7 = Gruppenplätze, und `Party_RemapCharacterIdByFlags` (`actors.c:12-36`) tauscht unter `FLAG_CHILDHOOD` die Kinder-Sprites 0x12/0x13. Andere IDs belegen die Akteurplätze ab 8 in Zeilenreihenfolge (Akteur = 8 + Zeile).
  - Danach `Object_CreateFar(id)`, Animation 1 wählen und den Winkel aus `facing` setzen.
  - `FieldObject_Create` (`src/field/field/objects.c:245-290`): `id>>12` ist die Art. Art 0 = ein Sprite `id & 0xfff`; Art 2 (0x2000|n) = eine Gruppe aus zwei Sprites n, n+1; andere Arten haben kein Sprite, z. B. 0x8000 = Kamera (`actors.c:266`).
- **Sprite-Tabelle:** `gCharacter_DescriptorTable[id & 0xfff]` (`src/system/resource/metadata_get_record.c:7-9`) stammt aus `src/graphics/sprite/sprites.tsv` (513 Zeilen; Zeile = ID; Spalten width, height, scale, drawKind, adjust, box, codec, frames, animations). Breite 0 = kein Bild (`src/field/field/animation.c:512`).
- **PNG-Regel** (`tools/ags-graphics/sprite.c:120-160,295-330`):
  - `graphics/sprite/spr_NNN.png` der Zeile, der die Frames gehören; eine Alias-Zeile wird als `SPR_X=SPR_Y` geschrieben.
  - Der Bogen ist ein senkrechter Streifen, mit Frame k bei y = k·height. Eine optionale `spr_NNN.tsv` ordnet mit `list` die Frames neu zu, und ihre `anim`-Zeilen sind die Animationen.
  - Palette: 8bpp, mit der gemeinsamen 224-Farben-Palette `gSystem_BasicColorPalette` (`src/runtime/runtime/text.c:199`), die in jedes PNG eingebettet ist, Index 0 transparent.
- **Vorschauframe:** der erste Frame-Befehl von Animation 1 (Werte < 239 sind Frames; 240 setzt die Zeichenart; 254 springt zu einer anderen Animation; `src/field/field_internal.h:83-91`), plus der Blickrichtungs-Offset für diese Zeichenart (`src/field/facing.c`, angewendet in `src/field/field/sprite_draw.c:150-185`; Bit 7 = gespiegelt). Für eine gerade Vorderansicht Blickrichtung 0x3800 verwenden. Bei genau 0x4000 zeichnen die Arten 3 und 5 base+0 gespiegelt.
- **Besondere IDs:**
  - 20 Schatztruhe (VERIFIZIERT, `markers.c:70`).
  - 28 Psynergie-Stein (VERIFIZIERT, `markers.c:105`).
  - 22 unsichtbare 16×16-Markierung, 68× für Theken und Gegenstandsstellen verwendet.
  - 4 und 7 haben leere Zeilen.
  - 261-279 und 504 sind Weltkartensymbole.
  - Platzierungstabellen verwenden die IDs 0..504.
- **Namen.** Es gibt keine globale Sprite-Enum. Die Namen stammen aus:
  - `include/game/character_ids.h`;
  - dateilokalen `SPRITE_*`-Enums (`src/scene/lunpa.h`, `vault_jail.c`, `tunnel_ruins.c`, `altin.c`, `altin_peak.c`, `tret_tree_*.c`, …);
  - Zeilenkommentaren.

  Das ergibt 71 VERIFIZIERTE Namen. Die übrigen 178 sind aus dem Bild und den Szenen, die die ID verwenden, ERSCHLOSSEN (z. B. „Townsperson A“, „Dog“); `name_evidence` sagt, welche.
- Die Kontaktbögen wurden mit bloßem Auge geprüft: korrekte Vorderansichten und Farben, kein Datenmüll. Es sind `sprites/contact_sheet_npc60.png` und `sprites/contact_sheet_all.png` in den Arbeitsdateien.

**Editor-Daten:** `names/sprites.json` (erzeugt von `scripts/sprites/build_sprites.py` mithilfe von `spritelib.py`, `usage.py`, `names.py`, `names_manual.py` und `sheet.py`):
```json
[{"id":28,"hex":"0x1c","name":"Psynergy Stone","confidence":"VERIFIED","name_evidence":"...",
  "usage":1,"scenes":["MogallForest1"],"party_slot":false,"has_image":true,
  "png":"games/tbs/src/graphics/sprite/spr_028.png","frame":{"x":0,"y":0,"w":16,"h":16},
  "frame_index":0,"mirrored":false,"palette":{...},"draw_kind":11,"animation":1,"base_frame":0,
  "sheet_frames":11,"scale":256,"adjust":[0,2],"box":[20,16],"evidence":"sprites.tsv row 28 ..."}]
```
Die Oberfläche schneidet `png` zur Laufzeit bei `frame` zu (gespiegelt, falls gesetzt). Für die ERSCHLOSSENEN Namen wird eine Überschreibungsdatei „Namen bearbeiten“ auf Seiten des Editors empfohlen.

---

## 4. Ortsnamen

- `Scene_GetAreaNameIndex(scene, entrance)` (`src/object/object/encounter.c:326-350`) durchläuft `gScene_AreaNameRules` (`src/object/scene_rules.s:168-301`). Jede Zeile ist `scene_name Scene, entrance, index` oder `group_name group, entrance, index` (`scene_rules.s:12-20`). Die **erste** passende Zeile gewinnt; Eingang -1 passt auf jeden Eingang. Gruppe = `gField_SceneTable[scene].group` (`src/object/object/scene.c:157-159`; die Spalte in `src/field/scenes.s`). Ohne Treffer ergibt sich Index 0. (VERIFIZIERT)
- Text = Meldung **`MsgDebugEntryName` + Index** (`src/object/psynergy_effects/world_map.c:400`, `src/window/battle_command/debug.c:23`). In EN ist `MsgDebugEntryName` = 2459 = `RENDER_RESOURCE_BASE` 0x99B für gepatchte nicht-europäische Editionen (`include/tbs_edition.h:264-271`, verwendet von `src/window/window/shortcuts.c:29`). Die Basis aus `msgctxt "MsgDebugEntryName"` in en.po lesen, nicht als Konstante. (VERIFIZIERT)
- Die Zeilen unter `.if EDITION_INTERNATIONAL` (Altin Peak 4, Eingänge 6/7) sind für EN aktiv (`include/game/ed_asm.h:11-16`).
- Ergebnis:
  - 199/201 Szenen erhalten einen Namen; Title (0) und LinkLobby (190, nur für Eingang 1 benannt) nicht.
  - 21 Szenen haben kein Symbol in `scenes.s` und werden daher als „Scene N“ plus ihr Gebietsname beschriftet.
  - Es gibt eingangsspezifische Namen, z. B. Sanctum: 1/2/20/21 Vale Sanctum, 10-12 Vault Sanctum, 35 Bilibin, 32 Xian, 29 Altin; VaultJail Eingang 2 = „Lunpa“.
  - Anzeige: „{area_name} — {label}“, z. B. „Vale — Vale Home“. Gebietsnamen wiederholen sich über viele Szenen, daher unterscheidet die Szenenbeschriftung.

**Editor-Daten:** `names/places.json` (erzeugt von `scripts/places.py`):
```json
{"area_message_base":2459,
 "scenes":[{"id":5,"symbol":"ValeHome","label":"Vale Home","group":3,"variant":2,"overlay":"0x374",
            "layered_row":4,"map":"003","area_index":10,"area_name":"Vale",
            "area_name_by_entrance":{},"area_message":2469}]}
```

---

## 5. Dialoge

- **en.po-Schema** (VERIFIZIERT). Jeder Eintrag besteht aus `msgctxt "<symbol>|message"`, `msgid "NNNNN"` (die Meldungsnummer, mit Nullen auf 5 Stellen aufgefüllt) und `msgstr` (Text). Es gibt 10,723 Einträge, 0..10722, ohne Lücken. Die Symbole landen in `out/tbs-en/text/msg_ids.h` (`#define TEXT_MESSAGE_NUMBER_<Sym> n`, `MSGNO(name)`). Szenen-C schreibt in Tabellen `MSGNO(MsgX)` und im Code das blanke `MsgX` (`src/scene/README.md:60-61`).
- **Text-Auszeichnung:** `{page_break}` (neues Fenster), `{end_wait}` / `{end_now}` (Ende), `{line_break}` und die Argumente `{protagonist_name}`, `{actor_name:N}`, `{argument_item_name:N}`, `{text_color:…}`, `{article_class:N}` (`tools/ags-text/symbols.c:28-60`). Ein literales `\n` ist eine Anzeigezeile. Die Namen als Platzhalter wie „[Isaac]“ darstellen.
- **Gesprächssuche** (`Scene_TalkToActor`, `src/object/object/events.c:197-290`; `Scene_FindEvent` `:111-165`):
  - Art 0 `EVENT_TALK`, mit Trigger = Akteur-ID = 8 + Platzierungszeile.
  - Die erste Zeile, deren Bedingung erfüllt ist, gewinnt (-1 immer; `flag|0x1000` = gesetzt; sonst nicht gesetzt), ein NPC kann also mehrere Zeilen haben, die über Story-Flags gewählt werden.
  - `value < 0x10000` → eine einzige Meldung. Alle 881 direkten Gesprächsmeldungen enden mit `{end_*}` (Erhebung), eine ID ist also die ganze Rede.
  - Andernfalls ist der Wert ein Skript. Art 7 ist die Zeile, die gesagt wird, wenn die Gruppe den Akteur angehalten hat (`events.c:175-186`).
  - `talkFacing` steuert das Umdrehen.
- Bei Skripten sind die Dialoge die `Msg*`-Symbole im Funktionsrumpf. Beispiel: `Event_TalkAboutTheMayorAndTremors` (`src/scene/vale.c:160`) zeigt je nach `FLAG_PARTY_LEFT_VALE` `MsgValeTheGroundStillShakes` oder `MsgValeYourGrandpaIsTheMayor`. Das ergibt eine Liste möglicher Zeilen, nicht ihre Reihenfolge oder Bedingungen (ERSCHLOSSEN: für Vorschauen ausreichend).
- Suchstellen zeigen `MsgTileChecked + target` und danach den `FIND_MESSAGE`- oder Ergebnistext (`events.c:452-470`).

**Editor-Daten:** `dialogue.json` (Arbeitsdatei, 650 KB, erzeugt von `scripts/dialogue.py`; 152 Szenen, 2,475 Gesprächszeilen). Sie enthält Spieltext, deshalb erzeugt der Editor sie zur Laufzeit:
```json
{"4":{"symbol":"Vale","tables":{"gVale_Events":[
  {"actor":8,"placement_row":0,"kind":"talk|talk_paused","condition":null|{"flag":2069,"when":"set|clear"},
   "message":3967,"msgctxt":"MsgValeMtAlephLooksBeautifulTodayIts","text":"Mt. Aleph looks\nbeautiful today..."},
  {"actor":10,"placement_row":2,"kind":"talk","condition":null,"script":"Event_TalkAboutTheMayorAndTremors",
   "source":"src/scene/vale.c","script_messages":[{"message":4556,"text":"..."}]}]}}}
```
Text bearbeiten heißt, das `msgstr` in `text/en.po` anhand der msgid zu bearbeiten. Die anderen 5 Sprachkataloge müssen dieselbe Menge an msgids behalten (`src/game/README.md:97-110`).

---

## 6. Flags

- **Speicherung:** 4,096 Bits in `gGameFlagBytes`. Die Bits 0-2 der Flagnummer wählen das Bit und die Bits 3-11 das Byte (`src/game/game/flags.c:7-24`, `include/game/game_flags.h:12`). Byte-Zugriffsfunktionen behandeln 8 aufeinanderfolgende Flags als einen Zähler (`src/game/README.md:110-121`). Alle werden gespeichert (README; die Speicher-Prüfsumme umfasst `gGameFlagBytes`, `include/save_state.h:55`).
- **Bedingungen:** `-1` immer, `flag|0x1000` = gesetzt, andernfalls ist das Flag nicht gesetzt. 0 bei einer Platzierung = „in Sicht“ (`events.c:59-77`).
- **Bereiche** (`src/scene/README.md:48-59`, `include/flags.h:7-20`):
  - 0x000-0x0ff: Gruppe (0-7) und Djinn (48-127).
  - 0x100-0x1ff: Engine/System.
  - **0x200-0x2ff: Szenen-Temporärflags, bei jedem Betreten gelöscht.**
  - **0x300-0x3ff: Gruppenflags, beim Betreten einer anderen Gruppe zurückgesetzt, Nummern pro Ort wiederverwendet.**
  - 0x400-0x7ff: keine Verwendung gefunden (ein Verweis, 0x400; ERSCHLOSSEN ungenutzt, aber besser meiden).
  - 0x800-0xdff: Story.
  - 0xe00-0xfff: Truhen-/Fundflags.
- **Benennung:** `include/flags.h` (970 Zeilen) `#define FLAG_* value` mit `///`-Kommentaren, z. B. `FLAG_ALTIN_PEAK_LUCKY_MEDAL 0xf78 ///< room 8's chest`. Szenenlokale Flags werden in der eigenen Datei der Szene per `#define` festgelegt und stehen nicht in flags.h.
- **Nutzungserhebung** (`flags_survey.py`, VERIFIZIERT im Rahmen seiner Quellen):
  1. Jede condition, jedes requiredFlag, jedes Ausgangsflag und jede Bereichsbedingung in den gebauten Overlay-Tabellen.
  2. Jeder Aufruf einer Flag-Zugriffsfunktion mit konstantem Argument in der `clang -E`-Ausgabe jeder `src/**/*.c`. Die Ausgabe geht nur nach stdout, alchemy wird nicht angefasst.
  3. Die Flag-Felder der Zeilen `scene_cue`/`group_cue`/`location` in `scene_rules.s` und `location_rules.s`.
  4. Alle Definitionen in flags.h.

  In Verwendung gefunden: 0xe00-0xfff 213/512; 0x800-0xdff 300; 0x300-0x3ff 108.
- **Vorsichtige Liste freier Flags** (`flags_free.py`): schließt zusätzlich jeden Wert aus 0xe00..0xfff (oder seine Bedingungsform 0x1e00) aus, der irgendwo in `src`/`include` außerhalb von Grafik- und Kartendaten als Hex-Literal vorkommt. Damit bleiben **251 freie** Flags. Abschnitte: 0xe03-0xe0f, 0xe49-0xe58, 0xe61-0xe73, 0xe81-0xea1, 0xef8-0xeff, 0xf09-0xf12, 0xfdb-0xfe0, … (`flags.json` `free_chest_flags`).
- **Vergaberegel für eine neue Truhe:**
  1. Das niedrigste Flag in `free_chest_flags` nehmen, das nicht bereits von den eigenen Überschreibungstabellen des Mods (`games/tbs/src/mod/`) oder von anderen ausstehenden Änderungen verwendet wird.
  2. Es als condition des Ereignisses `SEARCH(SEARCH_CHEST)` schreiben.
  3. Es im Mod-Manifest festhalten, damit es nie wiederverwendet wird, auch nicht nach dem Löschen der Truhe (alte Spielstände können es gesetzt haben).
  4. Bei jeder Anhebung des alchemy-Pins durch erneutes Ausführen der Erhebung neu prüfen; die freie Liste ist eine Funktion des Commits.
- **Prüfen, ob ein Flag ungenutzt ist**, in dieser Reihenfolge:
  1. Es steht nicht in `used` eines frischen Laufs von `flags_survey.py` (Tabellen + Code + Regeln).
  2. Es gibt keinen Treffer als Hex-Literal (`flags_free.py`).
  3. Es liegt nicht im Byte eines Flags mit Byte-Zugriff (die Erhebung markiert alle 8).
  4. Es liegt nicht in 0x200-0x3ff.
  5. Nach dem Build per `grep` im Overlay-`.bin` nach dem Halbwort zu suchen ist **nicht** zuverlässig (Falschtreffer), daher auf 1-4 verlassen.

**Editor-Daten:** `names/flags.json` (aus den beiden Skripten erzeugt):
```json
{"total_flags":4096,
 "ranges":[{"lo":3584,"hi":4095,"meaning":"chest / find flags","editor":"allocate new chest flags here"}],
 "names":{"0xf78":["FLAG_ALTIN_PEAK_LUCKY_MEDAL"]},
 "used":{"0xf78":["flags.h","table 3a4:gAltinPeak_Events..."]},
 "free_chest_flags":[3585,3587,...]}
```

---

## Erzeugte Dateien und wie sie entstanden sind

Alle Skripte liegen in `names/scripts/` (Kopien) und im oben genannten Arbeitsverzeichnis. Sie hängen von `gsmap` aus gs-mapedit (Project, Scenes, grid) und von `out/tbs-en` ab.

| Datei | Skript | Eingaben |
|---|---|---|
| `names/collision.json` | `collision_json.py` (nach `coll_hist.py`) | oben beschriebenes Lesen der Engine; Histogramm über `src/map/*/grid_collision.tsv` |
| Arbeitsdatei `collision_by_map.json` | `collision_legend.py` | Raster + gebaute Ereignis-/Ausgangstabellen + `places.json` + `items.json` + en.po |
| `names/items.json` | `items/build_items.py` | `src/game/items.tsv`, en.po, `item_ids.h`, `graphics/ui/menu_icons/` |
| Arbeitsdatei `items/search_events.json` | `items/survey_chests.py` | gebaute Ereignistabellen |
| `names/sprites.json` | `sprites/build_sprites.py` (+ `spritelib.py`, `usage.py`, `names.py`, `names_manual.py`, `sheet.py`) | `graphics/sprite/sprites.tsv`, `spr_*.png`/`.tsv`, gebaute Platzierungstabellen, Szenenquellen |
| `names/places.json` | `places.py` (+ `po.py`) | `src/field/scenes.s`, `src/object/scene_rules.s`, en.po, `layered.tsv` über gsmap |
| Arbeitsdatei `dialogue.json` | `dialogue.py` | gebaute Ereignistabellen, ELF-Symbole der Overlays, `src/scene/**`, `out/tbs-en/text/msg_ids.h`, en.po |
| `names/flags.json` | `flags_survey.py` → `flags_free.py` → Zusammenführung inline | gebaute Tabellen, `clang -E` von `src/**/*.c`, Regel-`.s`-Dateien, flags.h |

Bilder (Symbolatlas, Kontaktbögen) und Spieltext werden bewusst nicht committet; gemäß der rechtlichen Haltung in PRODUCT.md baut die App sie aus dem Checkout des Spielers.

## Offene Fragen

- Was 248 bedeutet (kein Leser, ungenutzt) und ob 241 wie erwartet funktioniert (keine Karte verwendet ihn).
- Die Codes 96..99 (Altin Peak) und 136 Paare (Karte, Code) in 1..239 haben kein statisches Ereignis. Vermutlich werden sie vom Szenencode gelesen (Aufrufer von `GetMapCellCollision`) oder sind Überbleibsel.
- Die Kollisionsbedeutung auf der **Weltkarte** ist ein eigenes System (Schrittbyte in `blocks.tsv`, `attributes.tsv`): siehe `overworld.md`.
- Wer `touched_trigger` schreibt, und die oberen Steuerbits der Ereignisse bei 22 Truhen (0x400, 0x8400, 0xc400). Bit 0x400 des *Triggers* überspringt die „checked“-Zeile; die Bedeutung der Steuerbits ist nicht bestätigt.
- Der Palettenplatz im Spiel für Gegenstandssymbole (die PNG-Palette wird angenommen).
- Die 178 ERSCHLOSSENEN Sprite-Namen. Manche sind Vermutungen (z. B. 44 „Dodonpa“, 66/67, 69 „Lady Layana“). Die Akteurindex-Grenze 0x2705 ist im Quelltext als XXX markiert. JA/IT verwenden `spriteja.tsv`/`spriteit.tsv`.
- Ob eine Meldung ohne `{end_*}` in die nächste ID weiterläuft. Keiner direkten Gesprächsmeldung fehlt eines, für Vorschauen spielt es also keine Rolle.
- Die Flag-Erhebung übersieht Flags, die nur über Variablen oder berechnete Ausdrücke erreicht werden (5,191 Zugriffsaufrufe ohne Konstante, darunter Definitionen und Schleifen), sowie Flags in C-Datenarrays. Der Durchgang über Hex-Literale deckt die meisten davon ab; 0x400-0x7ff sieht ungenutzt aus, ist aber nicht bewiesen.
- Ob der Mimic-Slot gefahrlos größer als 7 sein kann (er liest in die nächste Zone hinein und ist daher nicht nützlich).
