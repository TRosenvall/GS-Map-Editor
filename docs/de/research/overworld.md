<!-- translated from docs/research/overworld.md @ 52c37110966a -->
# Recherche zur Oberwelt (Weltkarte): Golden Sun TBS, aus den alchemy-Quellen

_Dies ist eine Übersetzung der englischen Datei [overworld.md](../../research/overworld.md). Wenn sich die beiden unterscheiden, gilt die englische Fassung._

Quellbaum: `~/gs_project/alchemy` (nur lesend). Die Pfade unten sind relativ zu
`games/tbs/`, sofern sie nicht mit `games/` oder `tools/` beginnen. Markierungen: **[V]** = VERIFIZIERT (im Code oder in den Daten gelesen
oder durch das Prototyp-Rendering bestätigt), **[I]** = ERSCHLOSSEN.

Prototyp-Skripte und Renderings (Arbeitsdateien, nicht Teil dieses Repositorys):
`(a scratch folder)`
(`render_world.py`, `render_area.py`, `render_gameplay.py`, `world_mixed.png`, `world_annotated.png`, `collision.png`, `terrain_kind.png`, `north_compare.png`).

## Zusammenfassung

1. Der gesamte Boden der Oberwelt ist eine einzige Tabelle: `src/map/world/blocks.tsv`, 320 Zeilen x 512 Spalten hexadezimaler u32-**Zellwörter**, von `tools/ags-graphics` (Form `blocks`) zu `blocks.blocks` gebaut, das `src/map/map.s` als `Field_PerspectiveDataA` per incbin einbindet [V].
2. Die Tabelle enthält 640 **Chunks** aus 16x16 Zellen (der Code nennt einen Chunk „tile“). Die Chunks 0-319 sind Ebene 0 (BG3, Boden), 320-639 sind Ebene 1 (BG2, Überlagerung: Berge, Bäume, Küste), wobei Chunk der Ebene 1 = Chunk der Ebene 0 + 320 [V].
3. Die Welt besteht aus 16x16 Chunks = 256x256 Zellen; eine Zelle sind 32 Weltpixel (16 Bildschirm-/BG-Pixel), die Welt ist also 8192x8192 Welt-px groß und wiederholt sich an den Rändern [V]. Die Chunk-IDs 0-255 liegen am Welt-Chunk (id%16, id//16); 256-319 sind Alternativen, die vom Code eingewechselt werden [V].
4. Ein Zellwort: Bits 0-15 Block-ID, Bits 16-23 Schritt-/Ereigniscode, Bits 24-30 Geländeart (Begegnungsregion; 21 = Grafiksatz Schnee), Bit 31 Flag für die Verhaltensbank [V].
5. Eine Block-ID indiziert `src/map/default/cells.tsv` (4386 Blöcke zu je 4 Bytes: Kachelnummern 8x8 für TL, TR, BL, BR) [V]. Die Kacheln sind 8bpp, 256 pro Ebene: Satz A = `tiles_a+b` (Ebene 0) und `tiles_c+d` (Ebene 1), Palette `palette_a.png` (224 Farben); Satz B (Schnee) = `tiles_f..i`, `palette_b` [V].
6. Gerendert wird in Modus 2 (affine BG2+BG3) mit Matrizen pro Rasterzeile per HBlank-DMA für die „Mode 7“-Perspektive; ein flaches Rendering von oben braucht davon nichts. Der Prototyp rendert die vollständige Karte mit 4096x4096 BG-Pixeln korrekt [V].
7. Die Begehbarkeit gilt pro 8x8-Grafikkachel, nicht pro Zelle: `default/attributes.tsv` gibt jeder Kachel ein 4x4-Raster aus 4-Bit-Kollisionswerten (obere Ebene schlägt untere; 0 = keine; Standard 7); 5-12 sind begehbar [V].
8. Zufallsbegegnungen: Geländeart (Zellbits 24-30) + Geländeverhalten (aus dem Kollisionswert, Bank aus Bit 31 / Art 21) -> `gWorldMap_EncounterRules` (`src/object/zonedata.c`) -> Zonenzeile von `src/object/encounter.tsv` [V].
9. Städte/Dungeons sind platzierte Akteure (Symbol-Sprites) in `gWorldMapPlacements` (`src/scene/world_map.c`); das Berühren von Akteur N löst Trigger 100+N aus, dem ein `EVENT_EXIT` in `gWorldMapEvents` entspricht -> Ausgangsnummer -> `gWorldMapExits` -> (Szene, Eingang). Manche Eingänge sind stattdessen Schrittcodes in Zellen (Bits 16-23) [V]. Beim Verlassen einer Stadt wird deren Ausgangstabelle `SCENE_EXIT(n, 2, e)` -> Position `gWorldMapEntrances[e]` verwendet [V].
10. In TBS gibt es keine editionsabhängigen Varianten irgendwelcher Weltkartendaten; die Startadressen des ROM-Endbereichs unterscheiden sich je Edition, und jede Änderung bricht das byte-genaue „compare OK“ [V].

## Dateien und Formate

| Daten | Quelldatei(en) | Format | Gebaut als / verdrahtet durch |
| --- | --- | --- | --- |
| Bodenzellen, beide Ebenen | `src/map/world/blocks.tsv` | Kein Kopf. 320 Zeilen x 512 tabulatorgetrennte Tokens; jedes Token hexadezimal in Kleinbuchstaben ohne `0x`, ohne führende Nullen (`0`, `1b`, `9500014a`), LF-Zeilenenden, abschließendes LF [V]. Gelesen von `blocks()` in `tools/ags-graphics/tables.c:235-282`: Zeilenzahl muss ein Vielfaches von 16 sein, alle Zeilen gleich breit (Vielfaches von 16) [V]. Eine 16x16-Gruppe darf vollständig `-` sein (ausgelassen, Offset 0), aber nie nur teilweise [V; TBS hat keine, TLA hat 969]. | `blocks.blocks`: Offsettabelle aus 640 x u32, danach die 256 u32-Wörter jedes Chunks (1024 Bytes), einzeln mit LZ-Art `plz` gepackt (`tables.c:262-276`) [V]. `src/map/map.s:1-4` `.incbin` als `Field_PerspectiveDataA`, gefolgt von `.byte 0x01 @ PACKER` [V]. Verzeichniseintrag `group Field, PerspectiveDataA, ...` in `src/system/resource/directory.s:123` [V]. |
| Chunk-Nummerierung in der TSV | dieselbe | Chunk `i` belegt die TSV-Zeilen `(i//32)*16..+15`, Spalten `(i%32)*16..+15` (Chunks 32 breit, zeilenweise angeordnet) [V: `tables.c:257`]. Das ist NICHT die Weltanordnung: Die Welt ist 16 Chunks breit, eine TSV-Chunkzeile enthält also zwei Welt-Chunkzeilen nebeneinander [V durch Rendering]. | |
| Blöcke (Metakacheln) | `src/map/default/cells.tsv` | Kopf `cell0:u8 ... cell15:u8`; Werte `0x6b`; 1097 Zeilen, die letzte kurz (8 Werte) = 17544 Bytes = 4386 Blöcke x 4 Bytes [V]. Block b = Bytes `4b..4b+3` = Kachelnummer (u8) oben links, oben rechts, unten links, unten rechts [V: `src/field/field/world_map.c:71-91`, `444-451`]. Von beiden Ebenen gemeinsam genutzt; die Ebene wählt die Kachelbank. | `cells.table.lz`; `map.s:5-7` als `Field_DefaultMapCells` (+1 PACKER-Byte); nach `Ram_MapCellBuffer` (`gMapCellBuffer`, 0xc000 Bytes, `src/system/ewram.s:223-226`) dekodiert durch `world_map.c:158-160` [V]. Dieselbe Tabelle sind auch die „default cells“ der geschichteten Karten (README `src/map/README.md` Zeile `default/`). |
| Kachel-Kollision | `src/map/default/attributes.tsv` | Kopf `attr0:u8..attr15:u8`; 256 Zeilen = 4096 Bytes [V]. Bytes 0x000-0x7ff: Kacheln 0-255 der unteren Ebene (BG3), je 8 Bytes; 0x800-0xfff: Kacheln 0-255 der oberen Ebene (BG2) [V: `src/field/field/terrain.c:535-580`]. Pro Kachel: 4 Zeilen x 2 Bytes; jedes Byte enthält zwei 4-Bit-Werte, unteres Nibble = links; ein Wert = 2x2 BG-px (4x4 Welt-px). | `attributes.table.lz`, `map.s:11-13` `Field_DefaultMetatileAttributes`; nach `Ram_MapCollision` dekodiert (`world_map.c:161-163`) [V]. |
| Kachel-Animation | `src/map/default/animation.tsv` | Kopf `word0:u16..word7:u16`, 465 Halbwörter; Kanalskript (`0xfdNN` Kanal, Gruppen aus Quellkachel/Anzahl/Zielkachel/Frames, `0xfeNN` Sprung, `0xfeff` Stopp, `0xffff` Schleife) [V: `src/field/field/map_animation.c:7-13`]. Quellkacheln >= 0x600 stammen aus `gMapLayerData` (= `tiles_e`/`tiles_j`) [V: `map_animation.c:57-61`]. | `animation.table.lz`, `map.s:8-10`; nach `Ram_MapCollision+0x1000` dekodiert und gestartet (`world_map.c:149-152`) [V]. |
| Kachelgrafik | `src/graphics/world_map/tiles_{a..j}.png` | Indiziertes PNG, Pixelwert = roher 8bpp-Farbindex, PNG-Palette = `palette_*.png` [V]. a-d, f-i: 128x64 (je 128 Kacheln); e, j: 128x128 (256 Kacheln, Animationsquelle) [V]. | `tiles_X.8bpp.lz`, `src/graphics/world_map/worldmap.s` (jeweils gefolgt von PACKER-Bytes) [V]. Verzeichnis `directory.s:124-135` (`WorldMapPaletteA`, `WorldMapTilesA..J`) [V]. |
| Paletten | `palette_a.png`, `palette_b.png` | Indiziertes PNG 16x14 = 224 Farben [V]. In BG-Palette 0-223 geladen, Farbe 0 durch den aktuellen Hintergrund ersetzt (`world_map.c:331-335`) [V]. | `.gbapal.plz` (`worldmap.s:4`, `:26`) [V]. |
| Grafiksatz-Tabelle | `src/field/world_map_resources.c:11-28` | `gWorldMap_GraphicsResources[2][6]` = {Palette, Kacheln x5} für Satz A (A..E) und Satz B (F..J) [V]. | C. |
| Begegnungsregeln nach Gelände | `src/object/zonedata.c:7-15` | `gWorldMap_EncounterRules[132]` s16: 32 Regeln {Art, Verhalten (-1 beliebig), Flag (-1 keins / Regel aus, sobald gesetzt), Zone} + Abschluss Art -1 [V]. | C. |
| Begegnungszonen | `src/object/encounter.tsv` | Kopf `rate:u16 level:u16 group0..7:u16 weight0..7:u8 zone` (letzte Spalte ist eine Beschriftung, nicht kodiert); 104 Zonen [V]. | `encounter.table`, `src/object/arcspark.s:10-13` [V]. |
| Geländeverhalten | `src/field/mapdata.c:37-41` | `gWorldMap_TerrainBehaviorTable[48]` u8, Index = Kollisionswert + Bank (0x10 bei Zellbit 31, 0x20 bei Art 21) [V]. | C. |
| Szenentabellen | `src/scene/world_map.c` | `gWorldMapEntrances` (`:2717`), `gWorldMapExits` (`:2802`), `gWorldMapPlacements` (`:2863`) + Story-Varianten (`:2966-3058`), `gWorldMapEvents` (`:3060`) [V]. Formate in `include/field_scene.h:54-150` [V]. | Weltkarten-Overlay 0x371 (`objects.tsv:640-644`), gelinkt bei 0x2008000, Grenze 32 KB (`src/scene/README.md` Limits) [V]. |
| Kartenmarkierungen im Pausenbildschirm | `src/object/scripts.s:340-383` | `gWorldMap_PlaceMarkers`: Paare {tile<<16 \| flag, Ortsname}; Zeile i beschreibt Akteur 11+i; Nullzeilen reservieren einen Akteur; -1 beendet [V: `src/object/psynergy_effects/world_map.c:282-323`]. | asm `.4byte`. |
| Bild im Pausenbildschirm | `src/graphics/world_map/picture.png` | 240x160 8bpp, deckt Welt-x 4096-8192, z 0-4096 ab [V: `psynergy_effects/world_map.c:10-11, 318-322`]. Von Hand gezeichnet, nicht aus den Blöcken erzeugt [I]. | `src/graphics/title/title.s:68-71` `Field_WorldMapPicture` [V]. |
| Story-Bilder | `src/graphics/world_map/story.png`, `storymap.tsv`, `storypal.png` | Grafiken der Story-Einblendungen im Weltkarten-Overlay [V: `story.s`]. Keine Bodendaten. | `story.s`, Overlay-Objekt `objects.tsv:643` [V]. |

Szenen-ID der Weltkarte: `scene WorldMap, 0x371, 0x02, 1, 0x01` ist Szene 2 (`src/field/scenes.s:17`); Szenen-ID = Zeilenindex von `gField_SceneTable` (`scenes.s:1-5`) [V]. Ihr Kartenindex 1 ist gleich `SceneId_Clear`, und genau das wählt in `Field_RunScene` (`src/object/object/run_scene.c:45-49`) den Perspektivmodus [V].

## Rendering

Hierarchie (TBS) [V]:

```
world (wraps)  16 x 16 chunks                      8192 x 8192 world px, 4096 x 4096 BG px
chunk          16 x 16 cells   (code: "tile")      512 world px, 256 BG px; 1 KB decoded
cell           u32 word, low 16 bits = block id    32 world px, 16 BG px
block          2 x 2 tiles (4 bytes in cells.tsv)  
tile           8 x 8, 8bpp, from bank per layer    16 world px, 8 BG px
```

- **Anzeige**: `Map_InitializePerspectiveScene` (`world_map.c:112-264`) setzt BG3 = Zeichenbasis 2, Bildschirmbasis 8; BG2 = Zeichenbasis 3, Bildschirmbasis 10; beide 512x512 px affin, mit Wiederholung (`:164-174`); BG1 als Textebene für die Standansicht; `DISPCNT_MODE_2` (`:249`) [V]. BG2 wird über BG3 gezeichnet, Farbe 0 ist transparent (Kommentar `view.c:66-69`: wo BG2 transparent ist, scheint BG3 durch) [V].
- **Kachelbänke**: tiles[1] des Satzes (A) -> Zeichenblock 2, tiles[2] (B) -> Block 2 + 0x2000, tiles[3] (C) -> Zeichenblock 3, tiles[4] (D) -> Block 3 + 0x2000, tiles[5] (E) -> `gMapLayerData` (`world_map.c:336-352`) [V]. Die Kachelnummern 0-127 der Ebene 0 sind also `tiles_a`, 128-255 `tiles_b`; Ebene 1: `tiles_c`, `tiles_d` [V durch Rendering].
- **Streaming**: Die BG-Karten halten ein Fenster aus 2x2 Chunks um den Spieler. `perspective->tileIds[256]` ordnet jedem Welt-Chunk-Platz eine Chunk-ID zu, anfangs die Identität (`world_map.c:262-263`). `Map_WriteLayerCellTile` LZ-dekodiert Chunk `id` (Ebene 1 nutzt `id + 320`, `:298`, `:640`) in das Viertel `(x&1, y&1)` von `Ram_MapBlocks` und schreibt die Bytes der affinen Karte aus der Blocktabelle (`:38-95`) [V]. Der Fensterindex nutzt `& 15`, daher wiederholt sich die Welt alle 16 Chunks [V].
- **Perspektive**: `WorldMap_BuildScanlineTable` (`src/field/field/view.c`) + die ARM-Routine `Transform_UpdateVertices` bauen pro Rasterzeile ein affines Paar (BG2/BG3 PA..Y); `MapAnimation_ApplyAffineFrame` lädt Zeile 0 und überträgt den Rest per HBlank-DMA (`world_map.c:386-441`) [V]. Standardneigung 0xe000 (-1/8 Umdrehung), ferne Ebene 0x1fe0000, Mittelpunkt (120,96) (`:198-249`) [V]. Eine Editoransicht von oben ignoriert all das.
- **Grafiksatz B**: `WorldMap_LoadGraphics(x,z)` wählt Satz B, wenn die Zelle der Ebene 0 unter der Gruppe die Art 21 hat, nur beim Laden der Szene (`world_map.c:323-329`, aufgerufen von `run_scene.c:76-78`) [V]. Mit Satz B setzt es außerdem die Chunk-Plätze 10-12 und 26-28 auf die alternativen Chunks 0x10a-0x10c, 0x11a-0x11c (`:366-374`) [V]. Das Rendering bestätigt, dass Satz B der verschneite Norden ist (Gegend um Imil); in Satz A zeigen diese Plätze einen weißen Platzhalter [V: `north_compare.png`].
- **Story-Chunk-Tausch**: `FieldMap_SetWindowCellTile(128, 256, 176, 56)` (`src/scene/world_map.c:534`) setzt Chunk 264 in Platz 59 (Welt-Chunk (11,3)), solange `FLAG_LAMAKAN_SAND_MONSTER_BEATEN` nicht gesetzt ist; Arithmetik in `world_map.c:271-300` [V]. Optisch unterscheiden sich 264 und 59 durch eine Brücke [V Rendering; Bedeutung I]. Es ist der einzige Aufruf (grep) [V]. 57 der 64 alternativen Chunks (256-319 und ihre Zwillinge auf Ebene 1) werden vom TBS-Code nicht referenziert [I: grep fand keine weiteren Nutzer; alle 64 sind nicht leer und von 0-255 verschieden].
- **Animation**: Die Kachel-Animationskanäle kopieren aus `gMapLayerData` (Kacheln E/J) in den VRAM; für ein statisches Rendering irrelevant [V].

Algorithmus für das Rendering von oben (umgesetzt in `render_world.py`, 7 s in reinem Python) [V]:

```
for layer L in (0,1), world chunk (cx,cy) in 16x16:
    c = cy*16 + cx + 320*L                         # use tileIds overrides for set B / story swaps
    for cell (x,y) in 16x16: word = tsv[(c//32)*16 + y][(c%32)*16 + x]
        b = word & 0xffff; t[0..3] = cells_bytes[4b..4b+3]
        draw tile t[k] from bank L at BG px ((cx*16+x)*16 + (k&1)*8, (cy*16+y)*16 + (k>>1)*8)
        (layer 1: skip pixel value 0)
palette: palette_a.png (or palette_b.png for kind-21 cells / set B)
```

Ergebnis: `world_mixed.png` (Satz A, Zellen der Art 21 mit Satz B gezeichnet) zeigt Angara und Gondowan im oberen rechten Viertel (Chunks x 8-15, y 0-7), der Rest ist Ozean; flaches Fülland am Westrand des Kontinents; drei Inselchen [V]. Legt man `gWorldMapEntrances` und die Platzierungspositionen bei Welt/2 darüber, landet Vales Symbol (Akteur 11 bei 5678,1200) richtig, die Eingänge 0-2 knapp südlich davon und Schrittcode 90 (Flint) daneben [V: `world_annotated_zoom.png`].

## Spieldaten

### Zellwort (Ebene 0) [V]

| Bits | Bedeutung | Beleg |
| --- | --- | --- |
| 0-15 | Block-ID in `cells.tsv` (volle 16 Bits, keine 12-Bit-Maske auf der Weltkarte) | `world_map.c:82-86, 445` |
| 16-23 | Schrittcode (`struct MapCell.collisionCode`): 1-239 Schrittereignisse der Szene, 240-241 Begegnungsboden, 252-254 Warps, 0xff Wand (Bedeutung bei geschichteten Karten) | `include/map.h:13-22`, `src/object/object/step.c:20-25, 231-245` |
| 24-30 | Geländeart = Begegnungsregion (0 keine, 1-6, 21, 31 verwendet) | `terrain.c:619-624`, `zonedata.c` |
| 31 | wählt Verhaltensbank 0x10 | `terrain.c:615-617` |

Zellen der Ebene 1 nutzen nur die Bits 0-15; alle ihre oberen Bits sind in den Daten 0 [V: Statistik]. Nur die oberen Bits der Ebene 0 werden gelesen (der Code indiziert die Zeilen 0-31 von `Ram_MapBlocks`, also Ebene 0) [V]. Der Code-Kommentar `struct WorldMapCell {tile:24, kind:7, flag:1}` (`world_map.c:17-23`) fasst den Schrittcode mit unter „tile“; die lesenden Stellen verwenden die Bytes getrennt [V].

Werteerhebung (Ebene 0, alle 320 Chunks): Arten 0 74215, 1 915, 2 1542, 3 1001, 4 771, 5 494, 6 1304, 21 1334, 31 156; Bit 31 auf 188 Zellen gesetzt; vorhandene Schrittcodes: 13, 15, 18, 28, 29, 32, 42, 47, 50, 51, 55, 61, 74, 75, 90, 91, 92, 93, 95, 96, 100 [V].

### Begehbarkeit / Gelände [V]

- `GetWorldMapCollision` (`terrain.c:535-580`): Nimm das BG-Kartenbyte (die 8x8-Kachelnummer) in Bildschirmblock 10 (obere Ebene) an der Position, schlage sein Nibble in `Ram_MapCollision + 0x800` nach; ist es 0, dasselbe für Bildschirmblock 8 (untere) in `Ram_MapCollision`; ist es immer noch 0, gib 7 zurück. Nibble = Zeile `((y>>1)&3)`, Byte `((x>>2)&1)`, `(x>>1)&1` wählt das obere Nibble, in Einheiten von 2 Welt-px.
- `CheckWorldMapWalkable` (`terrain.c:586-592`): begehbar genau dann, wenn der Wert 5..12 ist.
- Verhalten = `gWorldMap_TerrainBehaviorTable[bank + value]` (`mapdata.c:37-41`): Bank 0: 5->1, 6->7, 7/8/10-13->1, 9->2; Bank 0x10 (Bit 31): 5->4, 9->6; Bank 0x20 (Art 21): 5-13->5 außer 9->6. Das Verhalten wählt auch den Kampfhintergrund (`encounter.c:118`, `Battle_SelectTerrainBackdrop` `encounter.c:404-429`): 1 Grasland, 2 Wald, 3 Wüste, 4 und 7 Strand, 5 und 6 Schneefeld, sonst Sol Sanctum [V].
- Erhebung der zusammengesetzten Kollisionskarte: Die Werte 1-4, 14, 15 (blockiert; Wasser/Berg/Klippe) und 5-10 (begehbar) kommen vor; 9 = Wald (Verhalten 2) laut den Begegnungsbeschriftungen [V Daten; Beschriftung „forest“ aus `encounter.tsv`].
- Höhe: auf der Weltkarte keine (Zellen haben kein Formbyte; Akteure werden mit y=0 und ohne Geländehöhe platziert, `src/object/object/actors.c:143-158`) [V].

### Zufallsbegegnungen [V]

Pro Schritt auf der Weltkarte: `Field_ProcessStep` -> `Encounter_RollWorldMap(&leader->x, speed)` (`step.c:261-263`) -> `Encounter_ResolveWorldMapZoneAndBackdrop` (`encounter.c:103-120`): Die erste Regel in `gWorldMap_EncounterRules` mit passender Art, passendem Verhalten (oder -1) und nicht gesetztem Flag liefert die Zone; danach verwendet `Encounter_SelectEnemyGroup` (`encounter.c:130-218`) die Zeile aus `encounter.tsv`: Rate (+5 pro Gruppenstufe über `level`, höchstens 5), Gewichtung, 8 gewichtete Gruppen (Zeilen von `src/battle/formatn.tsv`). Die Regeln der Feldszenen (`src/object/location_rules.s`) werden auf der Weltkarte nicht verwendet (`Encounter_SelectSceneZones(0)`, `run_scene.c:49`).

Regeln (Art: Verhalten -> Zone): 1: 4,7,1->7, 2->8; 2: 4,7,1->13, 2->14; 21: 5->29, 6->30; 31: 1->37, 2->38; 3: 3,4,7,1->45, 2->46; 4: ...->54, 2->55; 5: ...->64, 2->65; 6: ...->80, 2->81. Die Zonen sind in `encounter.tsv` beschriftet („World map: terrain kind 1, grassland and beach“, ...). Verhalten 3 (Wüste) steht in den Regeln, wird von der Verhaltenstabelle aber nie erzeugt, daher zählt Wüstenboden auf der TBS-Weltkarte als Grasland/Strand [V Tabelle gelesen; Auswirkung im Spiel I]. Djinn-Kämpfe: Zonen 100-103 über `gEncounter_AreaEntryTable` (`zonedata.c:19-29`).

`terrain_kind.png` zeigt zusammenhängende Regionen (Art 1 um Vale, 2 Bilibin, 21 verschneiter Norden, ...) [V Rendering; Ortsnamen I].

### Betreten von Städten/Dungeons [V]

Zwei Mechanismen, beide enden in `gWorldMapEvents` (`src/scene/world_map.c:3060-3125`):

1. **Ortssymbole (die meisten Städte)**: Die Zeilen von `gWorldMapPlacements` (`:2863-2964`) sind die Akteure 8, 9, ... in Zeilenreihenfolge; eine Zeile, deren Bedingung nicht erfüllt ist, belegt trotzdem ihren Platz (`actors.c:103-108`). `WorldMap_UpdateLocationContacts` (`world_map.c:416-466`) setzt `touchedTrigger = actor + 100`, wenn |dx|+|dz| des Anführers < Summe der skalierten Radien ist (und `FLAG_CONTACT_BLOCKED` 0x104 nicht gesetzt ist). Ein Ereignis `{ EVENT_EXIT, 100+actor, cond, exitNo }` ordnet dem einen Ausgang zu; z. B. Zeile 3 (Akteur 11, Sprite 0x105 bei 5678,1200) -> Trigger 111 -> Ausgang 1 -> `SCENE_EXIT(1, 5, 10)` = Szene 5 (Dorf Vale) Eingang 10. Manche Trigger führen stattdessen Skripte aus (die Durchgänge 116/125/130/150/151 wählen einen Ausgang nach der Annäherungsseite, `:367-410`).
2. **Schrittcodes in der Karte**: Zellbits 16-23 = Code; `{ EVENT_EXIT, code, cond, exitNo }` (Codes 13, 15, 18, 28, 29, 32, 42, 47, 50, 51, 55, 61, 75) oder Skripte mit `EVENT_TOUCH`/`SEARCH` (90-96 Djinn, Reise, Schiffswrack; 100 Suche nach den Turtle Boots; 112 Transferroute; 74 Ostrand).

Kodierung der Ausgänge `SCENE_EXIT(exit, scene, entrance) = exit<<20 | entrance<<12 | scene`, die Form mit Flag addiert 0x10000000 und ein Flag-Wort; die Tabelle beginnt mit `SCENE_EXITS(own scene)` und endet mit 0x1ff (`include/field_scene.h:72-77`).

### Verlassen von Städten [V]

Die eigene Ausgangstabelle der Stadt nennt Szene 2: z. B. `gValeHome_Exits` `SCENE_EXIT(10, 2, 1)` (`src/scene/vale_home.c:1903`); Bilibin `SCENE_EXIT(1, 2, 5)` (`bilibin.c:805`). Eingang `e` ist eine Zeile von `gWorldMapEntrances` (`struct SceneEntrance`, 24 Bytes: entrance, requiredFlag, x, y, z (s16 Pixel), facing, unused, Kamera L/T/R/B, unused; `field_scene.h:54-67`). Eingang 1 = (5680, 0, 1226) mit Blick nach Süden, knapp unter Vales Symbol. Besondere Eingänge (33, 49, 64-80, 90, 91, 99) wählen außerdem Platzierungstabellen und Zwischensequenzen (`world_map.c:308-342`, `496-560`).

## Grenzen und Einschränkungen

- Chunk-Anzahl und -Anordnung sind durch den Code festgelegt: 640 Chunks, Ebenen-Offset 320 (`0x140`, `world_map.c:298, 640`), Platzraster 16x16 (`& 15`), Alternativen an den festen IDs 0x10a-0x10c, 0x11a-0x11c, 264 [V]. `blocks.tsv` muss genau 320x512 bleiben.
- Jeder Chunk wird zu 1024 Bytes in einen Heap-Block von 0x400 dekodiert (`world_map.c:56-57`) [V].
- Kacheln: 256 pro Ebene (Einträge der affinen Karte sind Bytes) [V]; 224 Palettenfarben, Index 0 wird auf den Hintergrund gezwungen [V]. Die Kachelbänke E/J (256 Kacheln) speisen die Animation [V].
- Blöcke: Die Block-ID ist in der Zelle 16 Bit breit, aber `cells.tsv` wird in `gMapCellBuffer` dekodiert (0xc000 Bytes, `ewram.s:225`) -> höchstens 12288 Blöcke [I]; derselbe Puffer hält während Ereignissen das 240x160-Bild der Standansicht (`world_map.c:711-712`) und wird danach neu geladen (`:766-767`) [V].
- Kollisionstabelle fest 4096 Bytes (2 x 256 Kacheln x 8) [V]; das Animationsskript muss dahinter in `gMapCollision` passen (insgesamt 0x4000, beginnt bei +0x1000) [I].
- Platzierungen: Akteurplätze 8..65 (`actors.c:98`, `CONTACT_LAST_ACTOR = 65`); die Orts-Trigger 108..165 dürfen nicht mit Schrittcodes kollidieren, die für andere Ereignisse verwendet werden [V/I]. Zeile i von `gWorldMap_PlaceMarkers` muss auf Akteur 11+i ausgerichtet bleiben [V].
- Das Weltkarten-Overlay (Code + Tabellen + Story-Grafiken) muss bei 0x2008000 in 32 KB passen [V: Szenen-README]. Eingangskoordinaten sind s16 [V].
- Kompression: Jeder Chunk ist `plz`-LZ (`tools/common/lz.c`, `LZ_PALETTE_UNTAGGED`, Maschine `{4123, 485, 4126, 272}`); cells/attributes/animation `.table.lz`, Kacheln `.8bpp.lz`, Paletten `.gbapal.plz` [V]. Der Build kodiert aus TSV/PNG neu, ein Editor schreibt also nur Quellen; `.blocks`/`.lz` nie von Hand schreiben.
- Byte-Abgleich: Unveränderte Quellen reproduzieren das Original-ROM (PACKER-Literalbytes und der `_patch.tsv`-Mechanismus, `src/map/README.md` „How the build encodes a map“); jede Änderung lässt diese Edition abweichen, d. h. `make compare-editions` schlägt absichtlich fehl [V]. Die nachgestellten `PACKER:`-Bytes in `map.s`/`worldmap.s` sind nach einer Änderung harmlose veraltete Daten [I].
- ROM-Anordnung: `rom_tail_02` (enthält `map.s`, `objects.tsv:443`) beginnt an einer festen, editionsabhängigen Adresse (`main.ld:122-126`) und ist der letzte Bereich; Wachstum verschiebt nur nachfolgende Daten; TBS-Modulende 0x08800000 (`Makefile` `ROM_END_tbs`) [V]; ob ein Überschreiten geprüft wird, habe ich nicht untersucht [I].
- Editionen: keine `_ja/_de/...`-Varianten oder `.ifdef TBS_EDITION_*` in `map/world`, `map/default`, `graphics/world_map`, `zonedata.c`, `mapdata.c`, `world_map_resources.c` [V grep]. `scene/world_map.c` hat nur Codeunterschiede für `TBS_PATCH_3` (`:1657-1666`) [V]. Ortsnamen / Meldungen stehen in den PO-Katalogen der einzelnen Sprachen (`games/tbs/text/*.po`) [V Szenen-README].

### Unterschiede in TLA (kurz)

- `games/tla/src/map/world/blocks.tsv` hat 1024 Zeilen x 512 = 2048 Chunks; Ebenen-Offset 0x400 (`games/tla/src/field/common/map/perspective.c:42`) und ein Chunk-Fenster 32x32 (`tiles[32][32]`, `:8`) -> Welt aus 32x32 Chunks (16384 Welt-px) [V]. 969 Chunks sind ausgelassen (`-`) [V].
- Platziert durch `games/tla/src/map/world/blocks.s` (eigene Datei, `.balign 4, 0`) [V].
- Vier Grafiksätze A-D, jeweils Palette + 6 Kachelbögen (`tiles_a1..d6.png`), dazu Animations-/Attributtabellen pro Satz (`anim_b/d.tsv`, `attr_b/c/d.tsv`) in `games/tla/src/graphics/world_map/`; Verzeichnis `games/tla/src/system/resource/directory.s:420-458` [V]. `cells.tsv` ist größer (2745 Zeilen) [V].
- Der Großteil des TLA-Weltkarten-Engine-Codes ist noch Assembler (`object_dispatch_5.s`); es wird angenommen, dass die Semantik von Art und Flag gleich ist [I].

## Offene Fragen

Von alchemy markiert:
- XXX `world_map.c:569`: `WorldMap_UpdateView` liest die verfolgte Position ohne NULL-Prüfung.
- XXX `world_map.c:778`: ob es beabsichtigt ist, dass `Map_LoadDefaultCellsAndUpdateBlock` `animationActive` gesetzt lässt.
- XXX `src/scene/world_map.c:500-504`: Die Flags 0x161 und 0x85c (von den Eingängen 99 und 1 gesetzt) werden von keinem TBS-Code gelesen.
- XXX `actors.c:101-102`: die Sprite-Grenze 0x2705 beim Erzeugen der Platzierungen.
- Begegnungsflags 351/353 ohne Namen (`encounter.c:148-152`); Regel „Flag 5 / Einheit 5 Erfahrung > 130“.
- Die XXX der geschichteten Karten (Platzhalterblock 0xfff, Füllbytes im Kopf) gelten nicht: Die Weltkarte verwendet keine 12-Bit-Maske [V].

Durch diese Recherche nicht geklärt:
- Absicht der Designer hinter Zellbit 31: Mechanisch macht es aus Kollision 5 das Verhalten 4 (Strandhintergrund) und aus 9 das Verhalten 6 (Schneefeldhintergrund) [V]; warum gerade diese 188 Zellen es tragen, ist unbekannt [I].
- Warum Kollisionswert 6 auf Verhalten 7 abgebildet wird (eine zweite Strand-ID) [I].
- Zweck der 57 alternativen Chunks, die kein TBS-Code referenziert (Überbleibsel oder aus der TLA-Zeit) [I].
- Genaue Bedeutung jedes Kollisionswerts 1-4, 14, 15 (Wasser vs. Berg vs. Klippe) sowie von 6, 8, 10 [I].
- Ob `picture.png` (Pausenkarte) aus den Bodendaten abgeleitet wurde; ein Editor, der Küstenlinien ändert, muss es von Hand neu zeichnen [I].
- Welche Szene bzw. welchen Eingang jedes `EVENT_EXIT` in für Menschen verständlichen Begriffen erreicht, erfordert das Zusammenführen mit den Namen aus `gField_SceneTable` (manche Szenennamen in alchemy sind bekanntermaßen ungenau, z. B. ist Szene 5 `ValeHome` das Dorf Vale) [V für das Beispiel].

## Vorgeschlagenes Datenmodell für den Editor

Python-Schicht, alle Ein- und Ausgaben nur auf alchemy-Quelldateien. Die ursprüngliche Textformatierung bleibt erhalten, damit Diffs übersichtlich sind.

| Entität | Felder | Datei (lesen/schreiben) | Hinweise zum Round-Trip |
| --- | --- | --- | --- |
| `WorldGrid` | `chunks[640][16][16]: u32` plus abgeleitete Ansichten `cell(layer, gx, gy)` über die Platzzuordnung; `slot_map[256] = identity` | `src/map/world/blocks.tsv` | Genau 320x512 Tokens schreiben, `format(v, 'x')` (Kleinbuchstaben, keine Auffüllung, `0` für null), Tabulatoren als Trenner, `\n` als Zeilenende + abschließendes `\n`. In TBS nie `-` ausgeben. Ein byte-identisches Neuschreiben einer unveränderten Datei muss ein Test sein. |
| `Cell` | `block: u16`, `step_code: u8`, `kind: u7`, `bank_flag: bool` (Ebene 0); Ebene 1 nur `block` | gepackt in `WorldGrid` | Obere Bits der Ebene 1 (alle 0) und alle unbekannten Bits unverändert erhalten. |
| `Alternates` | `set_b_swaps {10:0x10a, 11:0x10b, 12:0x10c, 26:0x11a, 27:0x11b, 28:0x11c}`, `story_swaps {59:264}` | Konstanten aus `world_map.c:366-372`, `scene/world_map.c:534` (nur lesend) | Der Editor sollte Alternativen zusammen mit ihren Basis-Chunks bearbeiten und beide Ansichten zeigen. |
| `BlockTable` | `blocks[4386][4]: u8` | `src/map/default/cells.tsv` | Kopfzeile bleibt; 16 Werte pro Zeile, `0x%02x`, kurze letzte Zeile erlaubt. Mit den geschichteten Karten geteilt: Die Bearbeitung eines Blocks ändert jede Karte, die die Standardzellen nutzt; neue Blöcke besser anhängen. |
| `TileCollision` | `lower[256][4][4]`, `upper[256][4][4]` Nibbles | `src/map/default/attributes.tsv` | 16 Bytes pro Zeile, `0x%02x`, Kopfzeile bleibt. Wird auch mit den Standarddaten der geschichteten Karten geteilt [I]. |
| `Tileset` | pro Satz: Palette (224 RGB), Bänke L0 (A+B), L1 (C+D), Animationsbank (E/J) | `src/graphics/world_map/*.png` | PNG-Modus P, exakte Größen und die Palette identisch zu `palette_*.png` (Index = Farbe) beibehalten. Das Neuschreiben der PNGs ist für den Build in Ordnung, solange die Indizes erhalten bleiben; auf pixelgleich prüfen statt auf dateigleich. |
| `Animation` | Kanalskripte (u16-Liste) | `src/map/default/animation.tsv` | Anfangs als undurchsichtige Wörter behandeln. |
| `Entrance` | `id, required_flag, x, y, z, facing, camera[4]` | `gWorldMapEntrances` in `src/scene/world_map.c:2717-2800` | C-Quelle: nur den Initialisierungsblock zwischen bekannten Markierungen parsen/neu erzeugen; die Namen `CONDITION_ALWAYS`, `FACING_*` beibehalten. |
| `Exit` | `exit_no, scene, entrance, flag?` | `gWorldMapExits` (`:2802-2839`) und die `*_Exits` der Städte | Ebenso; die Makroform `SCENE_EXIT(...)` beibehalten. |
| `Placement` (Ortssymbol) | `row/actor, sprite, condition, behavior, x, z, facing, talk, flags` | `gWorldMapPlacements` (`:2863-2964`) | Akteurnummer = 8 + Zeile; Einfügen/Entfernen von Zeilen nummeriert die Trigger (100+actor) und die Ausrichtung von `gWorldMap_PlaceMarkers` (Akteur 11+i) neu. Besser an Ort und Stelle bearbeiten. |
| `Event` | `kind/control, trigger, condition, value` | `gWorldMapEvents` (`:3060-3125`) | Ausgänge: `{ EVENT_EXIT, trigger, cond, exit_no }`; Skripte verweisen auf C-Funktionen (im Editor nur lesend). |
| `EncounterRule` | `kind, behavior, flag, zone` | `src/object/zonedata.c:7-15` | 132 s16 inkl. Abschluss; das Literal der Arraygröße muss angepasst werden, wenn Regeln hinzukommen. |
| `EncounterZone` | `rate, level, groups[8], weights[8], label` | `src/object/encounter.tsv` | Tabellenform; 104 Zeilen, durch Referenzen festgelegt (Zonen-IDs in Code/Regeln). |
| `PlaceMarker` | `tile, flag, name_id` pro Akteur 11+i | `src/object/scripts.s:340-383` | asm-Zeilen `.4byte`. |

Empfohlene Editoransichten: (1) zusammengesetzte Ansicht von oben mit Satzwahl pro Zelle (Art 21 -> Satz B), (2) Kollisions-Überlagerung aus `TileCollision` über die Kachelnummern der Zellen (obere, dann untere, dann 7), (3) Überlagerungen für Art und Schrittcode, (4) Eingänge/Platzierungen bei Welt/2. Koordinatenhilfen: Welt-px = BG-px x 2; Zelle = Welt // 32; Chunk-Platz = Zelle // 16; TSV (Zeile, Spalte) für Ebene L = `((c//32)*16 + gy%16, (c%32)*16 + gx%16)` mit `c = slot_map[(gy//16)*16 + gx//16] + 320*L`.
