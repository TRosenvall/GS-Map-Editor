<!-- translated from docs/research/local-connections.md @ 9ab200ba52b5 -->
# Lokale Karten: wie sie verbunden und bevölkert werden (TBS, mit Anmerkungen zu TLA)

_Dies ist eine Übersetzung der englischen Datei [local-connections.md](../../research/local-connections.md). Wenn sich die beiden unterscheiden, gilt die englische Fassung._

Quellbaum: `alchemy/` (nur lesend). Die Pfade unten sind relativ zu `alchemy/games/tbs/`, sofern sie nicht mit `games/`, `tools/` oder `out/` beginnen. „VERIFIZIERT“ = im Code/in den Daten gelesen oder per Skript über alle Dateien geprüft; „ERSCHLOSSEN“ = abgeleitet, nicht bewiesen.

## Zusammenfassung

1. Eine **Szene** ist eine Zeile von `gField_SceneTable` (`src/field/scenes.s`): Overlay-Ressourcen-ID, Gruppe, Variante, **Zeile der geschichteten Karte**. Die Szenen-ID ist der Zeilenindex. 201 Zeilen. (VERIFIZIERT)
2. Die Kartenzeile indiziert `gMap_LayeredScenes` (`src/field/layered.tsv`, 186 Zeilen). Jede Zeile enthält 6 Ressourcen-Offsets ab `ResourceId_Map001`: Kartenkopf, Palette, 3 Kachelbögen, Ebenendaten. Die Szenentabelle wählt also die Karte **und** den Kachelsatz zusammen, und die Zeilennummer ist **nicht** die `map_NNN`-Nummer. (VERIFIZIERT)
3. Der Code jedes Overlays (`scene/<place>.c`) liefert über sechs Einsprung-Veneers fünf Tabellen: Entrances, Exits, Placements, Events, Regions, dazu Initialize. Die Getter können je nach Flag oder Szenen-ID zwischen Tabellen wählen. (VERIFIZIERT)
4. **Ausgänge funktionieren über Ereignisse.** Der Kollisionscode einer Zelle (1..239) entspricht einem `EVENT_EXIT`-Ereignis (Wert = Ausgangsart), ein Berührungsskript ruft `Engine_EventRequestExit(kind)` auf, oder ein Bereichskasten greift. Die Ausgangstabelle ordnet dann (aktuelle Szene, Art) einem (Szene, Eingang) zu. (VERIFIZIERT)
5. Bei der Ankunft platziert die erste `SceneEntrance`-Zeile, deren `entrance` passt und deren Flag gesetzt ist (oder -1), die Gruppe und begrenzt die Kamera. Passt keine Zeile, wird Zeile 0 verwendet. (VERIFIZIERT)
6. **Markierungen** (`markers.tsv`: x, z, id) sind die Positionen von Truhen und Psynergie-Steinen. Die ID ist in allen 417 Markierungen gleich dem Kollisionscode der Zelle. Was eine Markierung enthält, ergibt sich aus dem `SEARCH`-Ereignis der Szene mit diesem Trigger. (VERIFIZIERT)
7. **NPCs** sind `ScenePlacement`-Zeilen. Akteurnummer = 8 + Zeilenindex, unabhängig davon, ob die Bedingung der Zeile erfüllt ist (das Szenen-README sagt etwas anderes). Positionen sind 16.16. 396 von 2,321 Zeilen liegen bei (0,0) und werden vom Code positioniert; es gibt 405 Inline-Aufrufe von `Engine_ActorSetPosition`. (VERIFIZIERT)
8. Jede Verbindungstabelle ist ein schlichter C-Initialisierer auf Dateiebene aus Literalen und Makros. Alle lassen sich neu schreiben, wenn das Werkzeug an Ort und Stelle bearbeitet und dabei `#if`-Blöcke, symbolische Namen und `const` erhält. Szenen-IDs in Ausgangswörtern sind **numerische Literale**. Im Code sind sie Linker-Symbole `(s32)&SceneId_X`. (VERIFIZIERT)
9. TLA hält Eingänge, Punkte und Kameragrenzen pro Karte in einem 7. Kartenblock (`scene_*.tsv`). Seine Overlays tragen meist eine einzeilige `SceneEntrance`. Das ist ein Unterschied in der Engine, TBS kann daher nicht auf dieselben Dateien umsteigen. (Anordnung VERIFIZIERT, Semantik ERSCHLOSSEN)
10. Um eine neue Karte oder Szene hinzuzufügen, nimmt man die 25 `unused`-Plätze im Verzeichnis und hängt Zeilen an die Szenen- und die geschichtete Tabelle an. Feste Bankadressen und **etwa 3.5–43 KB ROM-Reserve pro Edition** (8-MB-Auffüllung) sind die harten Grenzen. (VERIFIZIERT)

---

## 1. Verdrahtung Szene ↔ Karte

### 1.1 Szenentabelle (VERIFIZIERT)

`src/field/scenes.s:1-9`:

```
.macro scene name, code, area, kind, map
  .equiv SceneId_\name, (. - gField_SceneTable) / 8   ; id = row index
  .2byte \code   ; overlay resource id (= directory index, 0x36f..0x3ce)
  .byte \area, \kind  ; group, variant
  .2byte \map, 0      ; gMap_LayeredScenes row, reserved
```

- `struct SceneRecord` steht in `include/field_runtime.h:18-26`: `resourceId, group, variant, mapIndex, reserved`, 8 Bytes.
- Die Tabelle hat 201 Zeilen (per Skript gezählt). Unbenannte Zeilen (`scene , 0x376, ...`) erhalten kein `SceneId_`-Symbol.
- `Game_ResetForNewGame` (`src/object/object/scene.c:204-289`) führt `record = &table[gGameState.scene]` aus, dann `gGameState.map = record->mapIndex` (`:286`), dann `Scene_LoadOverlay` → `Resource_LoadCode(table[scene].resourceId, &gOverlayArea)` (`:294-298`), dann `Scene_TakeExit(Field_RunScene(entrance))` (`:288`).
- `group` wird verwendet für:
  - Musikregeln und Gebietsnamenregeln (`src/object/scene_rules.s`, gelesen von `Scene_ResolveInteractionResult` und `Scene_GetAreaNameIndex` in `src/object/object/encounter.c:279-345`);
  - das Löschen der Flags 0x300-0x3ff bei einem Gruppenwechsel;
  - das „besucht“-Flag `(group & 0x7f) + 0x180` (`scene.c:344`), eine Gruppe muss also ≤ 0x7f sein.
- `variant` 2 kennzeichnet Städte. Es schaltet die PP-Regeneration durch Gehen ab und blockiert Retreat (`src/object/object/run_scene.c`, `sceneVariant == 2`).
- Mehrere Szenen können sich ein Overlay teilen, zum Beispiel Bilibin1/2/3 = 0x38b und AltinPeak1..11 = 0x3a4. Sie teilen sich dann auch eine `.c`-Datei.
- **Szenen-IDs im C-Code sind Linker-Symbole.** `scene_ids.h` deklariert `extern char SceneId_X;`, und der Code vergleicht `gGameState.scene == (s32)&SceneId_X`, was aus einem Wort im Literal-Pool lädt. In `src/scene/*.c` gibt es 487 solcher Verwendungen.
- Run_scene vergleicht `gGameState.map == (s32)&SceneId_Clear`, also 1, um die Weltkarte zu erkennen (`run_scene.c:45`). (VERIFIZIERT)
- **Szenen-IDs in Datentabellen** (Ausgangswörter) sind einfache Ganzzahlen oder die wenigen `enum SceneId`-Namen in `include/field_scene.h:13-24`. Sie sind keine Symbole und folgen daher einer Neunummerierung **nicht**. (VERIFIZIERT)

### 1.2 Kartenauswahl: geschichtete Tabelle (VERIFIZIERT)

`src/field/layered.s` führt `.incbin "layered.table"` aus, gebaut aus `src/field/layered.tsv`. Ihre Spalten sind `map0..map5:u16`, und sie hat 186 Zeilen. Das Objekt wird in `rom_main_01` platziert (objects.tsv:59).

`struct LayeredSceneEntry { u16 resources[6]; }` steht in `src/field/field/map_layers.c:164`. `Map_LoadLayeredScene(index)` (`:211`) verwendet die sechs Ressourcen so:

| Spalte | Ressource | Verwendung |
|---|---|---|
| [0] | Kartenkopf | `Resource_GetTableEntry(resources[0] + ResourceId_Map001)` (`:233`) |
| [1] | Palette | dekodiert; Farbe 0 (der Hintergrund) bleibt erhalten (`:337`) |
| [2] | Kachelbogen | Zeichenblock 1 (`:345-357`) |
| [3] | Kachelbogen | Zeichenblock 2 |
| [4] | Kachelbogen | Zeichenblock 3 |
| [5] | Ebenendaten | nach `gMapLayerData` dekodiert |

Alle Werte sind Offsets ab `ResourceId_Map001`. Das Expandieren der Verzeichnismakros löst sie nach Namen auf (Arbeitsskript):

- die Zeilen 0 und 1 sind `Field_Map001` + `Blank*`. Title, Clear und WorldMap verwenden sie; der Weltkartenpfad lädt sie nie.
- Zeile 2 ist `Field_Map000` + `Set00{Palette,TilesA-D}`;
- Zeile 5 ist `Field_Map004` + `Set03*`;
- Zeile 12 ist `Field_Map010` + Set09 Palette/A/B/C + **Set08TilesD**.

123 von 186 Zeilen sind nicht sechs aufeinanderfolgende Ressourcen: Eine Zeile kann Bögen aus verschiedenen Sätzen mischen, und Umfärbungen verwenden Bögen wieder. Der Editor muss die Zeile also als sechs unabhängige Verweise behandeln.

`map_NNN/` ist nach `Field_MapNNN` benannt (die Nummerierung des Verzeichnisses, `src/map/README.md` „The map numbers are the directory's“). Zum Beispiel hat Szene ValeHome (ID 5) den mapIndex 4 → `Field_Map003` = `src/map/map_003/`. Die `markers.tsv` dieser Karte (13,44,100) passt zum `SEARCH(...)`-Ereignis von ValeHome mit Trigger 100 (`src/scene/vale_home.c`, Ereignisse).

Zwei Karten tragen Ortsnamen statt Nummern: `gondowan_passage/` (`Field_GondowanPassage`) und `venus_entrance/` (`Field_VenusEntrance`). Von 182 verschiedenen referenzierten Kartenressourcen werden 8 von mehr als einer Szene verwendet.

### 1.3 Ressourcenverzeichnis (VERIFIZIERT)

`src/system/resource/directory.s` enthält die Makros `resource`, `group`, `area SET, sheets, maps...`, `recolor`, `overlays`, `unused` (`:1-51`).

- Die ID eines Eintrags ist seine **Position**: `ResourceId_X = (. - Resource_DirectoryTable)/4`.
- `area SetNN, ABCD, mmm` gibt `Field_Mapmmm` aus, dann `Tileset_SetNNPalette`, dann `TilesA..D`.
- Die Overlays kommen zuletzt, `overlays 36F … 3CE` (96 Einträge, `:299-306`), gefolgt von `unused 25` (`:307`). Jeder ungenutzte Platz ist `.4byte 0`.
- `Resource_GetTableEntry(i)` ist einfach `Resource_DirectoryTable[i]` ohne Bereichsprüfung (`src/runtime/runtime/system.c:150-152`).
- Das Verzeichnis liegt am Anfang von `rom_tail_02`, das in EN bei 0x08320000 **fixiert** ist (`main.ld`, letztes `ABSOLUTE`; `out/tbs-en/tbs-en.map:7353`).
- Kartendaten (`map_NNN/map.s`, das auch die Kachelbögen enthält, die ihm gehören), dann folgt `src/system/overlay/overlays` in der Reihenfolge von `rom_tail_02` (objects.tsv:436-631).
- Wer vor den Overlays einen Verzeichniseintrag einfügt, nummeriert jede spätere Ressource neu. Das bricht die Overlay-IDs in scenes.s (`0x36f`…) und jeden `layered.tsv`-Offset nach der Einfügestelle. Die `unused`-Plätze verwenden: Indizes 0x3cf..0x3e7. (ERSCHLOSSEN aus dem Positionsmakro; die Arithmetik ist VERIFIZIERT.)

### 1.4 Overlays: entry, import, objects.tsv, overlays.tsv, Linker (VERIFIZIERT)

`src/scene/README.md` und `src/system/overlay/overlay.ld` beschreiben die Overlays.

- **Entry** (`scene/entry/<place>.s`) sind sechs `overlay_veneer`-Zeilen in fester Reihenfolge: Initialize, GetEntrances, GetExits, GetPlacements, GetEvents, GetRegions. Jeder Veneer ist `ldr r4; bx r4; .4byte target` (`src/system/overlay.s:5-11`). Die Engine liest sie als `struct SceneEntries` (`include/field_runtime.h:42-57`): je ein Veneer-Wort plus ein Funktionszeiger, 48 Bytes. Sie ruft `gOverlayArea.entrances()` usw. auf.
- **Import** (`scene/import/<place>.s`) ist `.set overlay_imports,1`, dann `.set import.NAME,1` für jede Engine-Routine, die das C aufruft, dann `.include overlay.inc`. `overlay.inc` enthält die geordnete Hauptliste aus ~405 `import NAME, TARGET`-Zeilen. Nur die gesetzten Zeilen erzeugen einen Stub (`src/system/overlay.inc:9-25`). Overlays können einander nicht aufrufen.
- **objects.tsv** gibt jedem Overlay drei `text`-Zeilen in dieser Reihenfolge (`entry/<place>`, `<place>`, `import/<place>`), mit erster Spalte = Overlay-ID in Hex (z. B. `374 text games/tbs/src/scene/vale_home`). Optional kann eine `bss`-Zeile folgen (`.bss COMMON` oder `resource_<id>_overlay .bss` aus `src/system/overlay/ovl_<id>.s`).
- **overlays.tsv** gibt den Kopf des `.bss`-Ausgabeabschnitts an (z. B. `.bss ALIGN(16)`) für die 36 Overlays mit bss-Zeilen. `tools/ags-objects/ags-objects.c:165-205` bricht mit „bss header and rows disagree“ ab, wenn genau eines von beiden existiert.
- **Linken.**
  - Jedes Overlay wird bei 0x2008000 gegen `symbols.elf` gelinkt (Makefile:209-219).
  - Innerhalb eines Overlays kommt zuerst aller `.text`, dann aller `.rodata`, dann aller `.data`, jeweils in Objektreihenfolge (Durchläufe von `render()` in `ags-objects.c`). `const`-Tabellen landen also in `.rodata` und nicht-konstante in `.data`.
  - Das Abbild wird von `tools/ags-overlays` zu `resource_<id>.lz` gepackt und von `src/system/overlay/overlays.s` eingebettet (`Resource_Overlay36F: .incbin ...` plus editionsabhängige `PACKER:`-Restbytes).
  - `Resource_LoadCode` dekodiert es nach `gOverlayArea` und patcht Thumb-BLs (`system.c:228`).
- Der Overlay-Bereich ist 32 KB groß, und Code + rodata + data + bss müssen hineinpassen. Gemessen an `out/tbs-en/overlays/*.map` sind die größten 0x3b1 mit 32,648 B (120 B frei), 0x373 Vale mit 30,764 und 0x3c8 mit 30,732. (VERIFIZIERT anhand der Build-Ausgabe.)

### 1.5 Weitere nach Szene geschlüsselte Tabellen (VERIFIZIERT)

Diese verwenden `SceneId_`-Symbole oder die Gruppe und bleiben daher beim Anhängen korrekt:

- `src/object/scene_rules.s`:
  - `gScene_InteractionRuleTable` (Musik: `scene_cue` / `group_cue`);
  - `gScene_AreaNameRules` (`scene_name` / `group_name`);
  - `gParty_PairResolveRules` (`return_to`, Rückkehrpunkte nach Niederlagen);
  - `gBattle_BackdropScenes`.
- `src/object/location_rules.s` `gBattle_LocationRules`: Begegnungszonen pro (Szene, Eingang, Flag).
- `src/scene/world_map.c` `gWorldMapExits` (`SCENE_EXITS(2)`…) und seine `EVENT_EXIT`-Ereignisse (44): wie die Weltkarte lokale Szenen betritt.

---

## 2. Ausgänge und Eingänge

### 2.1 `struct SceneEntrance` (24 Bytes, `include/field_scene.h:54-70`) (VERIFIZIERT)

| # | Feld | Typ | Bedeutung |
|---|---|---|---|
| 1 | entrance | s16 | die Eingangsnummer, die das Ausgangswort nennt; -1 beendet die Tabelle |
| 2 | requiredFlag | s16 | -1 oder ein Flag, das **gesetzt** sein muss (einfaches `GameFlag_TestFar`, keine 0x1000-Kodierung) |
| 3 | x | s16 | Pixel |
| 4 | y | s16 | Pixel (Höhe; in 20/1520 Zeilen von null verschieden) |
| 5 | z | s16 | Pixel (auf der Karte „nach unten“) |
| 6 | facing | u16 | 1/65536 Umdrehung (`enum Facing`, Schritte von 0x2000) |
| 7 | unused1 | s16 | überall 0, nicht gelesen |
| 8 | cameraLeft | s16 | Pixel, -1 = Grenze aus dem Kartenkopf beibehalten |
| 9 | cameraTop | s16 | ebenso |
| 10 | cameraRight | s16 | ebenso |
| 11 | cameraBottom | s16 | ebenso |
| 12 | unused2 | s16 | überall 0, nicht gelesen |

`Scene_ApplyEntrance` (`src/object/object/run_scene.c:461-505`):

1. Sucht nach `entrance == gGameState.entrance && (flag == -1 || flag set)`. Passt nichts, verwendet es **Zeile 0**.
2. Sofern nicht `FLAG_KEEP_PARTY_POSITION` gilt, schreibt es `gGameState.x/y/z = value << 16` und `heading = facing`.
3. Begrenzt die Kameragrenzen, mit einer Mindestansicht von 240×160.

Statistik über 189 Tabellen / 1,520 Zeilen:

- 3 Zeilen verwenden ein Flag;
- 1,023 setzen Kameragrenzen;
- beide ungenutzten Felder sind überall 0;
- die Spalte entrance ist in 21 Zeilen eine symbolische Konstante.

### 2.2 Wie ein Ausgang ausgelöst wird (VERIFIZIERT)

Es gibt drei Wege, eine Szene zu verlassen:

1. **Ausgangszelle.** `Field_ProcessStep` liest den Kollisionscode der Zelle des Anführers (`src/object/object/step.c:240-249`).
   - Die Codes `1..239` (`STEP_EVENT_FIRST/LAST`, `:19-27`) setzen `work->action = code`.
   - `Scene_RunTouchOrExit(code)` (`src/object/object/events.c:333-385`) sucht zuerst ein `EVENT_TOUCH`-Ereignis mit `trigger == code`. Gibt es eins, führt es dessen Meldung oder Skript aus, und das Skript erhält den Code als Argument.
   - Andernfalls sucht es `EVENT_EXIT` mit `trigger == code`: Es spielt den Ausgangston (Bits 5..4 von control: 0 normal, 0x20 → SE_128 + Effekt 26, 0x30 → SE_129 + Effekt 25, 0x10 keiner) und setzt `work->exit = event.value`, die **Ausgangsart**.
2. **Skript.** Ein Berührungs-/Gesprächs-/Psynergie-Skript ruft `Engine_EventRequestExit(kind)` auf. Das wird als `Event_SetExitRequestFar` importiert (`src/system/overlay.inc:321`). Es gibt etwa 200 Aufrufstellen. Typische Türen verwenden `TOUCH_WALKING_INTO(FACING_NORTH)` auf dem Kollisionscode der Tür, animieren die Türzellen, lassen den Anführer hineingehen und fordern dann den Ausgang an (`vale_home.c:444-471`). Die Koordinaten der Türanimation sind **Inline-Aufrufargumente** (`Event_OpenDoorAndWalkThrough(44, 7, 248, 279)`, `Map_CopyCellsTo(...)`) oder `u16 ...DoorCells[]`-Arrays aus `MAP_CELL_STEP(srcX,srcY,w,h,frames)` (`include/field_event.h:59-61`).
3. **Bereich.**
   - `struct SceneRegion` (`include/field_runtime.h:30-37`, 16 B) ist `minX,minY,minZ,maxX,maxY,maxZ` (Pixel; min einschließlich, max ausschließlich), `condition` und `value` = Ausgangsart. minX -1 beendet die Tabelle.
   - Geprüft wird es von `Field_CheckExitRegions` (`step.c:135-186`), wann immer der Zellcode des Anführers von null verschieden ist.
   - Es gibt 14 Bereichstabellen mit 38 Zeilen; die meisten Szenen geben NULL zurück.

`Field_RunScene` gibt `work->exit` zurück. `Scene_TakeExit(kind)` (`src/object/object/scene.c:25-89`) dann:

- durchläuft die Ausgangstabelle des Overlays nach dem Kopfwort, das der aktuellen Szenen-ID entspricht;
- nimmt das erste Ausgangswort, dessen `kind == exitKind` gilt oder dessen Art `0xff` (beliebig) ist, **und** dessen Flag nicht gesetzt ist (`SCENE_EXIT_IF`: das Flag-Wort folgt; der Ausgang wird **übersprungen, solange das Flag gesetzt ist**);
- fällt auf die Szene des ersten Ausgangs mit Eingang 0 zurück, wenn es zuerst ein Wort mit Art 0 oder das Ende (0x1ff) erreicht.

### 2.3 Kodierung der Ausgangswörter (VERIFIZIERT)

`include/field_scene.h:72-77`:

```
SCENE_EXITS(scene)              = scene                         // header
SCENE_EXIT(kind, scene, ent)    = kind<<20 | ent<<12 | scene
SCENE_EXIT_IF(k, s, e, flag)    = SCENE_EXIT(k,s,e) | 0x10000000, flag   // two words
SCENE_EXITS_END                 = 0x1ff
```

| Feld | Bits |
|---|---|
| scene | 0..11 (der Rückfall maskiert nur 9 Bits, und 0x1ff ist das Ende, Szenen-IDs müssen also < 511 sein) |
| entrance | 12..19 (0..255) |
| kind | 20..27 (1..254 echt, 0xff beliebig, 0 = **Kopf**) |
| flag-follows | Bit 28 |

**`SCENE_EXIT(0, N, 0)` ist ein Szenenkopf, identisch mit `SCENE_EXITS(N)`.** Tabellen geteilter Overlays verwenden das: `gAltinPeak_Exits` (`altin_peak.c:2671-2722`) enthält die Ausgangslisten von 11 Szenen nach einem einzigen `SCENE_EXITS(77)`. Ein Skript fand Köpfe für 200 der 201 Overlay-Szenen; nur die unbenannte Szene 59 (Overlay 0x39d) hat keinen. TLA behandelt zusätzlich ein Flag-Wort -1 als „immer“ (`games/tla/src/field/common/take_exit.c`).

### 2.4 Tabellenkatalog in `src/scene/*.c` (+ `common/*.h`) (VERIFIZIERT per Skript)

| Art (am **Typ** erkennen, die Namen variieren: `gX_Exits`, `gXExits`, `gXExits1`…) | Tabellen | Zeilen | Tabellen mit `#if` darin | `const` |
|---|---|---|---|---|
| `struct SceneEntrance` | 189 | 1,520 | 0 | 5 |
| `u32`-Ausgangstabellen (`SCENE_EXITS`) | 99 | 1,479 Ausgangswörter | 1 | 5 |
| `struct ScenePlacement` | 274 | 2,321 | 4 | 18 |
| `struct SceneEvent` | 263 | 5,891 | 10 | 13 |
| `struct SceneRegion` | 14 | 38 | 3 | 1 |
| Tür-/Zellschritt-Arrays (`u16` `MAP_CELL_STEP`, `u32` gepackte Zellen, `struct MapCellAnim`) | ~10 | — | — | — |

Ereignisarten nach Zeilenzahl:

- `PSYNERGY_ON_ACTOR` 1585
- `EVENT_TALK` 1374
- `EVENT_EXIT` 903
- `EVENT_TOUCH` 531
- `SEARCH(..)` 506
- `TOUCH_WALKING_INTO` 493
- rohe Hex-Steuerwerte wie `0x31`/`0x21` (Ausgang mit Tonbits), `0xc4f3`, `0x8413`: etwa 220

Alle sind initialisierte Arrays auf Dateiebene, eine Klammerzeile pro Datensatz (Ausgänge: ein Makro pro Wort, unter clang-format manchmal zwei pro Zeile, z. B. `world_map.c:2802`). Die Getter geben sie zurück, möglicherweise nach Flag oder Szene ausgewählt (`vale_home.c:104-160`, `bilibin.c:106-114`). Platzierungstabellen sind meist **nicht const**, weil `Scene_AssignViewFlags` zur Laufzeit die `condition` der Zeilen schreibt, deren Bedingung 0 ist (`src/object/object/actors.c:325`).

---

## 3. Markierungen (Truhen, Psynergie-Steine)

- **Format** (VERIFIZIERT). `markers.tsv` hat den Kopf `x:u8	z:u8	event:u8`, Zeilen aus Zellspalte, Zellzeile und ID und endet mit der Zeile `0xff 0xff 0xff`. Sie wird roh kodiert (`markers.table`, **nicht** LZ) und als 6. Kopfblock per incbin eingebunden (`src/map/map_004/map.s:25`). Werte dürfen dezimal oder hexadezimal mit `0x` sein: `map_002/markers_es.tsv` unterscheidet sich von `markers.tsv` nur in der Zahlenformatierung.
  - Es gibt 118 Markierungsdateien: 106 Basisdateien und 12 Editionsvarianten (`*_ja/_de/_es.tsv`, ausgewählt über `.ifdef TBS_EDITION_*` in map.s).
  - 76 map.s-Dateien verweisen auf die leere `map_000/markers.table`.
- **Lader** (VERIFIZIERT). Die Markierungsliste wird nicht dekodiert: `work->script = header + header->markers` (`map_layers.c:258`). `Field_PlaceMapMarkers` (`src/object/object/markers.c:30-131`), aufgerufen von `run_scene.c:73`, tut Folgendes:
  - Nur die IDs **100..239** werden berücksichtigt.
  - Für jede nimmt es das erste Szenenereignis mit `trigger == id`:
    - `control & 0x1ff == 19` (`SEARCH(SEARCH_CHEST)`): Es erzeugt Objekt **20** (Truhe) in der Zellmitte `(col<<20)+0x80000`, auf das Gelände eingerastet. Ist das Bedingungsflag des Ereignisses gesetzt, wird die Truhe geöffnet angezeigt (Animation 2); ist das Flag gesetzt und der Wert ein Mimic (`0x5xxxxx`), wird sie gar nicht platziert.
    - anderes `SEARCH` mit Wert `0x300000` (`FIND_PSYNERGY_STONE`), dessen Flag nicht gesetzt ist: Es erzeugt Objekt **28** (Stein).
  - Höchstens `MARKER_MAX` = 10 werden platziert. Eine Markierung ohne passendes Ereignis platziert nichts.
- **ID = Kollisionscode** (VERIFIZIERT). Alle 417 Markierungszeilen in TBS haben `grid_collision[x,z] == id` (Arbeitsskript). Die Suche selbst ist auf den Kollisionscode der Zelle davor geschlüsselt (`Scene_FindEvent(EVENT_SEARCH, code)`, `events.c:111`, `Field_SearchTile` `events.c:429`). Eine Markierung ohne den passenden Kollisionscode würde eine Truhe zeigen, die sich nicht öffnen lässt. **Der Editor muss beides schreiben.**
- **Inhalt und Flags** (VERIFIZIERT). Der Inhalt steht in der Ereignistabelle der Szene: `{ SEARCH(SEARCH_CHEST), <id>, <opened-flag>, FIND_ITEM(ITEM_X) | FIND_COINS(n) | FIND_PSYNERGY_STONE | FIND_MESSAGE(m) | 0x5xxxxx mimic | EVENT_SCRIPT(fn) }` (`include/field_scene.h:118-217`).
  - Die Bedingung ist das „geöffnet“-Flag. Laut README sind die meisten Truhen-Flags ≥ 0xe00. Das Flag wird gesetzt, wenn die Truhe geleert wird (`events.c:500-560`).
  - Bit 16 des Werts bedeutet „die Gruppe kann sie nicht öffnen“.
  - Es gibt 135 Zeilen `SEARCH(SEARCH_CHEST)` und 17 Zeilen `FIND_PSYNERGY_STONE`. Manche Steine verwenden `SEARCH_FACING(...)`-Zeilen mit einer benannten Konstante `TRIGGER_STONE`, und manche Steine sind einfache Skripte (`Event_UsePsynergyStone` von ValeHome).
- Die Codes 242..247 sind feste „Suchstellen“-Meldungen, 250 ist Gefahrenboden, und 252..254 sind Kanten/Kletterstellen (`step.c:19-27`, `events.c:387-418`). 0xff ist eine Wand.

---

## 4. NPCs und Objekte

`struct ScenePlacement` (24 B, `include/field_scene.h:81-98`) (VERIFIZIERT):

| Feld | Typ | Bedeutung |
|---|---|---|
| sprite | s16 | Objekt-/Sprite-Art; 0-7 = Gruppenmitglieder (eigene Plätze), -1 beendet die Tabelle |
| condition | s16 | -1 immer; `flag\|0x1000` = Flag gesetzt; sonst Flag nicht gesetzt; 0 = „in Sicht“ (von `Scene_AssignViewFlags` neu geschrieben) |
| behavior | s32 | `ACTOR_STAND`=1, `ACTOR_WANDER`=2, kleine Ganzzahlen (z. B. 3) oder ein Zeiger auf ein SC_-Aktionsskript `s32 ...[]` |
| x, y, z | s32 | 16.16-Pixel über `PIXELS(n)` |
| facing | u16 | 1/65536 Umdrehung |
| talkFacing | u8 | TALK_FACE_PARTY 0, _AND_BACK 1, KEEP 2, 3 folgt dem Anführer |
| flags | u8 | Bit 0 `PLACEMENT_SHARE_PREVIOUS_SPRITE` |

**Erzeugen** (`src/object/object/actors.c:75-180`, `ObjectTable_ResetForObject` `:217`) (VERIFIZIERT):

- Der Anführer wird aus `gGameState` erzeugt, danach die Tabelle ab Platz 8.
- **`actorIndex = slot++` läuft vor der Bedingungsprüfung (`:105-107`)**, eine übersprungene Zeile belegt also trotzdem ihre Nummer: **Akteur = 8 + Zeilenindex** für Sprites > 7. Die Trigger von `EVENT_TALK` und `PSYNERGY_ON_ACTOR` nennen diese Nummern, Umordnen oder Einfügen von Zeilen nummeriert also jedes Gesprächsereignis neu.
- Höhe: Abseits der Weltkarte wird y zur Geländehöhe addiert.
- Höchstens 58 platzierte Akteure (Plätze 8..65).
- Zeilen mit Djinn-Flags (48..127) brauchen zusätzlich `condition+80`.

Zählung der Spalte behavior über 2,321 Zeilen: STAND 1,705, WANDER 132, Ganzzahl 306, Skriptsymbol 178.

- 396 Zeilen liegen bei x=z=0. Das sind Akteure, die der Initialize-Code positioniert oder bewegt.
- Positionierung inline ist häufig:
  - `Engine_ActorSetPosition`: 405 Aufrufe
  - `OBJ_POS_SET(no,x,z)` (Pixel, `include/event.h:13`): 119
  - `Engine_ObjectCreate(kind,x,y,z)`: 53, für Effekte und zusätzliche Objekte
  - `Engine_ActorWalkTo`: 36

Die statische Platzierung von NPCs sind also Daten, die Inszenierung von Zwischensequenzen aber Code.

---

## 5. TLA `scene_*.tsv` (Kartenblock, nicht Overlay)

`map.s` in TLA hat **7** Blöcke: metatiles, shapes, grid, shape_grid, animation, blend, scene (`games/tla/src/map/map_008/map.s`). Es gibt keinen markers-Block, und TLA hat keine `markers.tsv`.

Der scene-Block ist `scene.parts.lz`, LZ-gepackt. `scene.tsv` listet seine Teile der Reihe nach auf: `SCENE_HEADER, SCENE_POINTS, SCENE_ENTRANCES, SCENE_PATCHES, SCENE_BOUNDS`. Er ist in 286 Karten vorhanden.

| Datei | Spalten | Anmerkungen |
|---|---|---|
| `scene_header.tsv` | `entrances:u16 patches:u16 bounds:u16 none:u16` | Byte-Offsets ab Blockanfang; die Punkte beginnen bei 8. Für alle 286 geprüft: entrances = 8 + size(points), patches = entrances + size(entrances), bounds = patches + size(patches); `none` = überall 0 (VERIFIZIERT) |
| `scene_points.tsv` | `id:u8 x:u16 z:u16` | endet mit `0xff`; 579 Punkte, IDs meist 1..28, 99 ×10. Bedeutung unbekannt (ERSCHLOSSEN: Skript- oder Kamerapunkte; keine Truhen, die in TBS zellbasiert sind) |
| `scene_entrances.tsv` | `id:u8 x:u16 z:u16 flags:u8` | 1,970 Zeilen. ERSCHLOSSEN: entspricht TBS `SceneEntrance` (id, x, z). Das untere Nibble der Flags = facing>>12 (Werte 4=S 1105×, 12=N 685×, 0=O, 8=W, 2/6/14 Diagonalen), und Bit 4 (16) ist ein zusätzliches Flag (28, 20) |
| `scene_patches.tsv` | `key:u16 source_x:u8 source_y:u8 x:u8 y:u8 width:u8 height:u8` | endet mit `0xffff`; **in allen 286 leer** |
| `scene_bounds.tsv` | `left:s8 top:s8 right:s8 bottom:s8` | meist eine Zeile + `-1`. ERSCHLOSSEN: Kameragrenzen in 16-px-Zellen (map_008: 0,0,40,34) |

Auf der Overlay-Seite haben TLA-Szenen weiterhin Exits/Placements/Events in C (`games/tla/src/scene/<place>/data.c`). 86 von 97 `SceneEntrance`-Tabellen haben eine einzige Zeile, den Rückfall, was stark darauf hindeutet, dass die TLA-Engine die Positionen aus dem Kartenblock nimmt (ERSCHLOSSEN; der Leser ist nicht dekompiliert). Ein Skript, das versuchte, TLA-Ausgangspaare (Szene, Eingang) über einen festen Szene→Karte-Offset mit Eingangs-IDs der Karten abzugleichen, blieb ohne Ergebnis, weil die geschichtete Tabelle von TLA nicht als Quelle vorliegt.

**Wird TBS umziehen?** ERSCHLOSSEN **nein**, zumindest nicht in dieselben Dateien. TBS-ROM-Karten haben 6 Blöcke mit Markierungen, und seine Engine liest Eingänge aus Overlays, die Daten liegen also dort, wo das ROM sie hinlegt. Git-Verlauf:

- TLA-Kartendateien: „TLA: the four field maps still copied, from editable tables“ (a20313083f) und andere.
- Die jüngste Arbeit an TBS-Szenen ist C-Humanisierung („Align scene table getters with the engine contracts“, db7167f0b0).

Keiner davon erwähnt, Szenentabellen nach TSV zu verlegen.

---

## 6. Eine neue Karte oder Szene hinzufügen (Checkliste)

Überall **Anhängen** dem Einfügen vorziehen.

1. **Kartendaten.**
   - `src/map/map_180/` anlegen: `map.s` (`.global Field_Map180`, `map_header`, 3×`map_layer`, 6×`map_block`, incbins) und die TSVs.
   - Einen vorhandenen Kachelsatz wiederverwenden (keine neuen Bögen) oder Bögen und eine Palette dahinter hinzufügen.
   - Ungenutzte Blöcke sind `map_block Field_Map180` mit Offset 0. Für Markierungen auf `map_000/markers.table` oder eine eigene verweisen.
2. **objects.tsv.** `main rom_tail_02 games/tbs/src/map/map_180/map` **vor** der Zeile `system/overlay/overlays` hinzufügen (objects.tsv:631). Das ergibt die ROM-Reihenfolge; nach 0x08320000 ist keine Adresse fixiert.
3. **directory.s.** Ein `unused` in `resource , Field_Map180` umwandeln, und in Palette/Kacheln, falls neu; `unused 25` entsprechend verringern (`:307`). Die neuen IDs sind 0x3cf+, und vorhandene IDs verschieben sich nicht.
4. **layered.tsv.** Eine Zeile mit Offsets ab `ResourceId_Map001` anhängen: Karte, Palette, Kacheln ×3, Ebenendaten. Ihr Zeilenindex ist die `map` der Szene. Sie liegt in `rom_main_01`, mit freiem Platz vor dem festen Beginn von `rom_main_02`: EN 4,020 B, DE 1,204 B, ES/FR 1,972 B (12 B pro Zeile).
5. **Szenen-Overlay** (um der Szene eigenen Code zu geben):
   - `src/scene/<place>.c`, `entry/<place>.s` (6 Veneers), `import/<place>.s` (Importe in der Reihenfolge von `overlay.inc`);
   - Prototypen in `include/unit/scene/<place>.h` (91 existieren);
   - objects.tsv-Zeilen `3cf text .../entry/<place>`, `3cf text .../<place>`, `3cf text .../import/<place>`, dazu optional `3cf bss ...` mit einer Kopfzeile in `overlays.tsv`;
   - `src/system/overlay/overlays.s`: `Resource_Overlay3CF: .incbin "overlays/resource_3cf.lz"` + `.balign 4`;
   - Verzeichnis: Ein `unused`-Platz wird zu `resource , Resource_Overlay3CF`.
   - Alternativ ein vorhandenes Overlay als Variante wiederverwenden, wie die Räume von Altin Peak: eine Szenenzeile mit demselben Code hinzufügen und in den Gettern nach `SceneId_` verzweigen.
6. **scenes.s.** `scene NewPlace, 0x3cf, <group>, <variant>, <layered row>` am Ende **anhängen**. Die neue ID ist 201, alle vorhandenen numerischen IDs bleiben also gültig. Die Tabelle liegt in `rom_main_04`, 8 B pro Zeile; frei vor der festen Bank: EN 3,448 B, DE 1,040 B. `extern char SceneId_NewPlace;` zu `include/scene_ids.h` hinzufügen. Die Gruppe muss ≤ 0x7f sein („besucht“-Flag). Szenen-IDs müssen < 0x1ff sein (Rückfall des Ausgangsworts).
7. **Verbindungen.**
   - In der Ausgangstabelle jedes Nachbarn unter **dessen** Kopf ein Ausgangswort hinzufügen: `SCENE_EXIT(kind, 201, entrance)`.
   - In den Ereignissen des Nachbarn eine `EVENT_EXIT`-Zeile (oder ein Berührungsskript) für den Kollisionscode hinzufügen, den man auf die Ausgangszellen malt.
   - Diesen Code in die `grid_collision.tsv` des Nachbarn malen.
   - Dasselbe spiegelbildlich in der neuen Szene: Kopf `SCENE_EXITS(201)`, ihre Ausgänge, Eingänge, deren Nummern zu dem passen, was die Ausgangswörter der Nachbarn nennen, Platzierungen, Ereignisse.
8. **Regeln.** Musik (`scene_cue`/`group_cue`), Gebietsname (`scene_name`/`group_name`), Rückkehr nach Niederlage (`return_to`) und Kampfhintergrund in `src/object/scene_rules.s`; Begegnungen in `src/object/location_rules.s`. Ohne Zeilen bekommt man MUS_018, keinen Namen, keine Begegnungen und den zuletzt verwendeten Hintergrund.
9. **Text.** Meldungen zu `text/<lang>.po` hinzufügen, mit einem `msgctxt` pro Meldungssymbol.
10. **Budget** (VERIFIZIERT, `out/tbs-*/tbs-*.map`).
    - Das ROM ist bis 0x08800000 aufgefüllt (Makefile:134). Freier Platz am Ende: EN 11,076 B, IT 11,040, DE 10,108, ES 4,128, FR 3,584, JA 43,100.
    - Eine neue Karte samt Overlay wird das wahrscheinlich überschreiten, daher muss das 8-MB-`ROM_END_tbs` angehoben werden. `MEMORY ROM` erlaubt bereits 32M (`main.ld`). Damit stimmt das ROM nicht mehr überein. (ERSCHLOSSEN: sicher; ungetestet.)
    - Overlay-RAM ≤ 32 KB.

---

## 7. Machbarkeit der Codeerzeugung (pro Tabelle)

Allgemeine Regel: Werte werden zu festen Bytes kompiliert, Formatierung und Leerraum sind also frei. Die Byte-Genauigkeit hängt ab von:

- derselben Zeilenreihenfolge;
- denselben Werten, einschließlich symbolischer (`MSGNO(Msg…)` wird zu Meldungsnummern aufgelöst, `EVENT_SCRIPT(fn)` zu Relokationen, Flagnamen aus `flags.h`);
- demselben `const`, das über die Platzierung in `.rodata` vs. `.data` entscheidet;
- denselben editions- und patchabhängigen Blöcken `#if TBS_PATCH_n` / `LANGUAGE`;
- derselben Tabellenreihenfolge in der Datei.

| Tabelle | Sicher neu schreibbar? | Wie der Round-Trip geht |
|---|---|---|
| SceneEntrance | Ja, sehr regelmäßig: 12 Literalfelder, 21 symbolische Eingangsnamen | CST-erhaltende Bearbeitung einer `{...}`-Zeile; ein Symbol beibehalten, wenn der Wert unverändert ist |
| Exit `u32[]` | Ja, mit Vorsicht: nur Makros, aber szenenspezifische `#define`s (`ROOM_ENTRANCE(exit)`, `LUNPA_EXIT_TO_*`), Köpfe `SCENE_EXIT(0,N,0)`, `#if !TBS_PATCH_3` (vale_home.c) | Makroaufrufe parsen, zu Wörtern auswerten, nur die berührten Aufrufe neu ausgeben; `SCENE_EXIT(0,..)` und `SCENE_EXITS` nie zusammenlegen |
| ScenePlacement | Größtenteils: `PIXELS(n)`, `FACING_X + FACING_STEP`, Figurennamen (`GARET`), Skriptsymbole, 4 Tabellen mit `#if` | Felder an Ort und Stelle bearbeiten; Zeilenreihenfolge beibehalten (Akteurnummern) |
| SceneEvent | Am schwierigsten: Bitfeld-Makros plus ~220 rohe Hex-Steuerwerte, Meldungs- und Funktionssymbole, 10 `#if` | als undurchsichtige Tokens behandeln, außer den bearbeiteten Feldern (trigger, condition, FIND_-Wert) |
| SceneRegion | Ja, klein: 3 mit `#if` | an Ort und Stelle |
| markers.tsv | Ja, Datendatei | TSV neu schreiben; dezimal und hex werden beide akzeptiert |
| scenes.s / layered.tsv / directory.s | Ja, zeilenorientiert | nur anhängen |

Überprüfung:

- Neu bauen und `make compare` / `compare-tbs` ausführen (Makefile:48-51).
- Für schnelle Prüfungen die Abschnitte von `out/tbs-<ed>/overlays/resource_<id>.elf` vor und nach einem wirkungslosen Neuschreiben vergleichen. Eine reine Neuformatierung muss identische Overlay-Ausgaben `.bin` und `.lz` ergeben.
- Ganze Dateien nicht neu erzeugen: Sie enthalten Code, `// clang-format off`-Bereiche, Kommentare und `#ifdef UBFIX`-Blöcke.

---

## 8. Offene Fragen

- Was `EventWork.touchedTrigger` (`include/field/event_work.h:26`) schreibt, das von Skripten gelesen wird. Im Hauptcode hat es keinen benannten Schreiber (ERSCHLOSSEN: der berührte Code).
- Kleine Ganzzahlen in `ScenePlacement.behavior` außer 1 und 2 (3 ist häufig): Die Semantik von `ObjectMotion_SetActionCallback` wird hier nicht nachverfolgt.
- Die vollständige Tabelle der Sprite-Arten (die Objekt-IDs 20 = Truhe, 28 = Stein und 0x8000 = Kamera sind anhand von markers.c und actors.c VERIFIZIERT).
- TLA: die Bedeutung von `scene_points`, Bit 4 von `scene_entrances.flags`, die Einheiten der Grenzen, die Auflösung Szene→Karte und die 6. Spalte der Szenentabelle (auch XXX in `games/tla/src/field/README.md`).
- Ob `unused`-Plätze im Verzeichnis und ein ROM größer als 8 MB auf Hardware und Emulatoren funktionieren (ERSCHLOSSEN ja).
- Szene 59 (unbenannt, 0x39d) hat keinen Ausgangskopf. Ausgänge dort lassen die Szene unverändert (`Scene_TakeExit` behält den Zustand bei, wenn kein Kopf gefunden wird).

---

## 9. Vorgeschlagenes Datenmodell für den Editor

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

Bearbeitungsoperationen:

- **Eine Ausgangszelle verschieben:** grid_collision-Code plus die `EVENT_EXIT`-Zeile.
- **Neu ausrichten:** das Ausgangswort bearbeiten.
- **Eine Truhe hinzufügen:** Markierungszeile, Kollisionscode und ein `SEARCH(SEARCH_CHEST)`-Ereignis mit einem frischen Flag ≥ 0xe00.
- **Einen NPC verschieben:** x/z der Platzierung bearbeiten und warnen, wenn x=z=0 der Zeile bedeutet, dass der Code sie positioniert.

Über all diese hinweg prüfen:

- die von jedem Ausgangswort referenzierten Eingangsnummern existieren in den Entrances des Ziels (sonst greift der Rückfall auf Zeile 0);
- Verschiebungen der Akteurnummern, wenn Platzierungszeilen eingefügt werden;
- die Markierungsgrenze von 10;
- die Budgets von 32 KB für Overlays und für das ROM.

---
