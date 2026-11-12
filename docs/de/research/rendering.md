<!-- translated from docs/research/rendering.md @ 5cc75b0f23d8 -->
# Recherche zum Rendering: Ebenen, Überblendung, Kachel-Animation, Platzhalter

_Dies ist eine Übersetzung der englischen Datei [rendering.md](../../research/rendering.md). Wenn sich die beiden unterscheiden, gilt die englische Fassung._

Quelle: alchemy (`games/tbs/...`). Die Pfade sind relativ zu `games/tbs/`, sofern nicht anders angegeben.
VERIFIZIERT bedeutet, dass die Aussage im Engine-Code gelesen und durch Rendering bestätigt wurde. ERSCHLOSSEN bedeutet eine begründete Vermutung.
Arbeitsskripte und Renderings liegen in
`(a scratch folder)`
(`r2.py` ist der Referenz-Renderer, `dirmap.py` löst die Ressourcentabelle der Szenen auf).

## Zusammenfassung

Die „verwürfelten“ Karten werden nicht durch Parallaxe verursacht. Drei Fehler im Viewer verursachen sie, und zwei davon betreffen fast jede Karte:

1. **Platzhalterzellen (0xfff) sind echte Grafik.** Beim Laden wird die k-te 0xfff-Zelle, zeilenweise über das gesamte 128×128-Raster gezählt, zu Block k. In **allen 182 Karten** ist die Anzahl der Platzhalterzellen genau die Zeilenzahl von `metatiles.tsv`. Die Blocktabelle ist praktisch „eindeutige Blöcke in Lesereihenfolge“, und explizite Zellwerte verwenden sie wieder. Werden Platzhalter leer gezeichnet, fehlt der Großteil jeder Karte. (VERIFIZIERT)
2. **Der Kachelsatz kommt aus der falschen Tabelle.** Das Spiel lädt die Palette einer Karte, ihre drei VRAM-Bögen und ihren Bogen D aus `src/field/layered.tsv` (`gMap_LayeredScenes`), nicht in der Reihenfolge aus `directory.s`. **117 von 182 Karten** verwenden eine andere Paletten- oder Bogenkombination, als der Viewer annimmt. Beispiele: Zeichenblock 3 von Karte 034 ist `Set02TilesC` und ihr Bogen D ist `Set26TilesC`. VenusEntrance verwendet die Bögen von `Set07` mit `Palette49`. (VERIFIZIERT)
3. **Die Grenzen im Kopf sind nur die Standard-Kameragrenzen.** Die Eingangstabelle einer Szene kann sie überschreiben. Karte 034 (Szene Bilibin3) wird durch ihre Eingänge auf 16..400 px begrenzt. Außerhalb dieses Bereichs ist die Kopffläche aus 128×128 Kacheln Rasterfüllung (Block 3), die im Spiel nie zu sehen ist. (VERIFIZIERT)

Parallaxe und Drift gibt es nur auf 8 Karten (047, 103, 104, 147, 148; auf 090/091/092/169 haben die Masken keine Wirkung, weil die Geschwindigkeit 0 ist). Die Überblendung ist BLDCNT/BLDALPHA, gesetzt von einem kleinen Skript. Das erste Ziel ist fast immer Ebene 2 (BG1), manchmal Ebene 1 (BG2). Kachel-Animation sind DMA-Kachelkopien aus Bogen D in den VRAM. Alle vier wurden in `r2.py` umgesetzt und durch Rendering geprüft.

## (a) Ebenen, Fenster und Scrollen

**Strukturen.** `struct LayeredSceneLayer {u8 x, y; s8 scrollX, scrollY, speedX, speedY; u8 periodX, periodY;}` steht in `src/field/field/map_layers.c:172-181`. Die Reihenfolge des Makros `map_layer` ist dieselbe: x, y, rate_x, rate_y, drift_x, drift_y, period_x, period_y (`src/map/map.inc`).

**Laden** (`map_layers.c:274-303`, VERIFIZIERT):
- `offset = x<<19` und `y<<19`, der Ursprung ist also x×8 px in 16.16-Festkomma.
- `scale = scroll*4096`, also rate/16 der Ansicht.
- `speed = speed*4096`, also speed/16 px pro Frame.
- `mask = period`.
- `phase = 0`.

**Pro Frame** (`Map_UpdateLayerScroll`, `map_layers.c:474-566`; ebenso in `Map_SetCameraCenter` 572-630, VERIFIZIERT):
```
view   = followed point - focus, clamped to [min, max - 240x160]        (min/max = header bounds*8 px, or scene overrides)
base   = view * scale            (Q16 multiply → view * rate/16)
if speed: phase += speed; base = (base + phase) & ((period<<19) | 0x7ffff)   # wrap; only applied when speed != 0
pos    = base + offset           # layer's top-left in grid pixels
BG(3-li) scroll = pos
```
Beim Zeichnen werden die Zellen bei `((pos/16) & 0x7f)` in beiden Achsen gelesen (`Map_RenderMetatileRow/Column`, 411-462). **Ein Ebenenfenster wiederholt sich also modulo 128 Zellen (2048 px).** Fenstergröße = Bildschirm; eine Fenstergröße pro Ebene gibt es nicht.
Ebene li wird auf BG(3-li) angezeigt, mit BGCNT-Priorität = Prioritätsbyte im Kopf, Zeichenbasis = Zeichenbyte im Kopf und Bildschirmbasis 5+li (314-322).

**Kameragrenzen.** `work->min/max = header bounds << 19` (261-264). `Scene_ApplyEntrance` (`src/object/object/run_scene.c:488-499`) überschreibt jeweils minX/minY/maxX/maxY in Pixeln, wenn `cameraLeft/Top/Right/Bottom != -1` des Eingangs gilt (`struct SceneEntrance`, `include/field_scene.h`). Karte 034 = Szene `Bilibin3` (`src/field/scenes.s:50`, Kartenindex 0x24). Ihre Eingänge 1 und 2 verwenden die Grenzen 16,16,400,400 (`src/scene/bilibin.c:780-785`). Einige Szenen schreiben die Grenzen auch direkt (`tolbi_ship_deck.c:1062`, `vale_babi.c:418-421`, `psynergy_effects/view.c:16`).

**Karten mit vom Standard abweichenden Ebenenparametern** (alles andere ist `16,16,0,0,255,255`):

| Karte | Ebene | Parameter | Bedeutung |
|---|---|---|---|
| 047 | 0 | rate 8,8 | Parallaxe mit halber Geschwindigkeit |
| 103 | 0 | drift_y −25, period 255 | Hintergrund fließt mit 25/16 px/Frame nach oben, wiederholt sich bei 2048 px |
| 104 | 0 bei y=92 | rate 6,6 | Himmel/Meer-Parallaxe (Szene mit Schiffsmast) |
| 147, 148 | 2 | rate 20,20, drift −121/16, 35/16 px/f, period 31 | Sandsturm-Überlagerung, wiederholt sich alle 256 px |
| 090-092 (Ebene 0,1), 169 (Ebene 0) | | period 127/63, speed 0 | keine Wirkung (Maske nur bei speed ≠ 0 verwendet) |

**Prioritätsreihenfolge (GBA, VERIFIZIERT durch Rendering).** Von hinten nach vorn zeichnen, sortiert nach `(-priority, layer index)`. Bei gleicher Priorität liegt die niedrigere BG-Nummer oben, also Ebene 2 (BG1) über Ebene 0 (BG3). Das `sorted(key=-priority)` des aktuellen Viewers ist stabil und liefert daher bereits dasselbe Ergebnis. Priorität 0 = aus.

**Rendering-Regel für einen Python-Viewer:**
- *Feldebenen* (rate 16, speed 0): `grid_px = (origin_px + map_px) mod 2048`, wobei `map_px` ab (0,0) des Rasterraums gemessen wird, nicht ab bounds.left. Das ist für jede Kamera exakt. Das aktuelle `render_layer` verhält sich für left=top=0 so, wiederholt aber nicht modulo 128 Zellen und ignoriert ein von null verschiedenes bounds.left/top.
  - Korrekte Form: `gx = (x*8/16 + bounds.left/2 + i) % 128` für Bildschirmspalte i des Grenzfensters, für y ebenso.
- *Parallaxe-/Drift-Ebenen* haben kein einzelnes statisches Bild. Empfohlene Regel für die Kartenansicht: an der Mitte des Kamerabereichs verankern.
  - `V = ((min + max(min, max-240))/2, same for y)` und `pos = layer_pos(V) + (map_px - V)`.
  - Das ist für die Kamera bei V exakt und anderswo stetig. Drift-Phase = 0 (oder speed×Frames).
  - Zusätzlich eine 240×160-„Kameravorschau“ anbieten, die `layer_pos(view)` exakt verwendet.
- Auf die Kameragrenzen der Szene *zuschneiden*, wenn sie bekannt sind; sonst die Grenzen aus dem Kopf verwenden.

## (b) Überblendung

**Mechanismus** (`src/field/field/map_animation.c:163-255`, VERIFIZIERT):
- `blend.tsv` wird zu Halbwörtern kompiliert: `control v` → v (ein BLDCNT-Wert, erkannt am oberen Nibble 3); `level v wait` → v, wait; `jump n` → 0xfe00|n (Cursor = Skript + 2n Halbwörter); `stop` → 0xfeff; `end` → 0xffff (Schleife zum Anfang).
- Bei einem `level`:
  - wenn die Effektbits (7..6) des letzten BLDCNT 01 sind, dann `REG_BLDALPHA = v`;
  - sonst `REG_BLDY = v`;
  - danach `wait` Frames warten.
- Ein Skript, das nur aus `end` besteht, installiert nichts (`DisplayBlend_StartScript` 246).
- Der Lader setzt zuerst `REG_BLDCNT = 0` (`map_layers.c:365-367`).

**GBA-Semantik:**
- Die BLDCNT-Bits 0-5 sind das 1. Ziel (Bit0 BG0, Bit1 BG1 = Ebene 2, Bit2 BG2 = Ebene 1, Bit3 BG3 = Ebene 0, Bit4 OBJ, Bit5 Hintergrund).
- Die Bits 6-7 sind der Effekt (1 Alpha, 2 Aufhellen, 3 Abdunkeln).
- Die Bits 8-13 sind das 2. Ziel.
- BLDALPHA: EVA = Bits 0-4 (Gewicht der Ebene von Ziel 1), EVB = Bits 8-12 (Gewicht dessen, was darunter liegt), jeweils auf 16 begrenzt.
- `out = min(31, (top*EVA + below*EVB) >> 4)` pro 5-Bit-Kanal.
- BLDY: `I + (31-I)*Y/16` (Aufhellen) oder `I - I*Y/16` (Abdunkeln).

**In den TBS-Karten gefundene Werte** (erstes `level` nach `control`):

| BLDCNT | Zielebene | Effekt | Karten (Beispiele) |
|---|---|---|---|
| 0x3f42 | Ebene 2 (BG1) über allem | Alpha | 005-007/032/076 (0x1006: 6/16 + 16/16 additiv), 021, 022-024/136/137, 025-027/077-085 (0xa09: 9/16 + 10/16 = das Wasser von 080), 029, 033/040/062/115/144 (0x1003 Glühen, animiert 3-4), 047 (0xc04), 053, 054-058/109/155/156/163, 063-067/100, 073, 075, 108, 113, 133, 139-142 (0xb0e), 154, 164-167 |
| 0x3f44 | Ebene 1 (BG2) | Alpha | 009/145/146, 010/019, 012/013/016, 014/015, 018/038/052/094/095/099/102/120/121/151/160/161 (0x1008), 061, 086, 105, 124 |
| 0x3fc8 | Ebene 0 (BG3) | Abdunkeln, BLDY 3-6 | 046 |
| (keiner) | — | nur BLDY, kein Effekt | 039/042/043, 114, 125: Das Skript schreibt Stufen bei BLDCNT=0. Eine Szene muss BLDCNT setzen (ERSCHLOSSEN) |
| nur `end` | — | — | 36 Karten (020, 028, 031, 036, 037, 048, 051, 060, 072, 074, 089, 093, … inkl. 134 über `map_020/blend`) |

Die meisten Stufen mit EVB=16 sind **additives Glühen** (Lichtstrahlen, Fackeln). Eine Wartezeit von 43210 bedeutet, dass die Stufe konstant ist.

**Von Szenen gesetzte Überblendungen** (nicht in `blend.tsv`; im Code VERIFIZIERT):
- `src/scene/altmiller_cave.c:195-222, 313-320`: BLDCNT 0x3f42 mit BLDALPHA 0x1000..0x600 oder 0xc04. Bei Karte 134 = Szene AltmillerCave5 (`scenes.s:165`) wird die Dunkelheitsebene auf diese Weise überblendet.
- Außerdem `tret_tree_branch.c:163` (BG1 4/12), `tolbi_spring.c`, `vale_babi.c`, `mercury_lighthouse*.c`, `crossbone_isle_platform_rooms.c`, `lemurian_ship.c`.

**Rendering-Regel:**
- Das Überblendungsskript parsen und BLDCNT und die erste Stufe nehmen, oder es bis Frame t simulieren.
- Für jede von hinten nach vorn gezeichnete Ebene: Wenn ihr BG-Bit in Ziel 1 liegt und effect==1, dann `rgb = min(31,(layer*EVA + below*EVB)>>4)`, wo die Ebene deckend ist. „Darunter“ ist die bereits zusammengesetzte Farbe (oder der Hintergrund); alle TBS-Steuerwerte verwenden als 2. Ziel 0x3f.
- Bei Effekt 2/3 BLDY auf die Pixel dieser Ebene anwenden.
- Für exakte Ergebnisse 5-Bit-Farben verwenden (PNG-Wert >> 3).
- Optional eine kleine Überschreibungstabelle pro Karte für von Szenen gesetzte Überblendungen führen (134 → 0x3f42/0xc04).

## (c) Kachel-Animation

**Mechanismus** (`src/field/field/map_animation.c:7-145`, VERIFIZIERT):
- `animation.tsv` wird zu Halbwörtern kompiliert: `channel n` → 0xfd00|n, `frame src cnt dst wait` → 4 Halbwörter, `jump n` → 0xfe00|n, `stop` → 0xfeff, `end` → 0xffff.
- `MapAnimation_StartChannels` durchsucht den Datenstrom. Jedes 0xfdNN startet Kanal NN&15 beim nächsten Halbwort, pausiert, wenn Bit 7 gesetzt ist (`channel 0x8N`; eine Szene setzt ihn über `Map_ClearLayerEntryFlag` fort).
- In jedem Frame, für jeden nicht pausierten Kanal:
  - wenn timer>0: timer−− und weiter zum nächsten Kanal.
  - sonst am Cursor ausführen:
    - 0xffff → Cursor = Start
    - 0xfeNN → Cursor = Start + 2·NN Halbwörter
    - 0xfeff → angehalten bleiben
    - sonst `cnt` Kacheln kopieren, timer = wait setzen, Cursor += 4 und im selben Frame erneut durchlaufen.
  - **Eine Kopie mit Wartezeit W bleibt also W Frames lang auf dem Bildschirm**, und W=0 verkettet im selben Frame zur nächsten Kopie.
- Kopie (4bpp, `wideTiles==0`), in 32-Byte-Kacheln, gezählt ab **Zeichenblock 1**:
  - `src >= 0x600`: aus `Ram_DecodeBuffer (0x0201c000) + src*32`, das ist `gMapLayerData` (0x02028000, `src/system/ewram.s:236-244`, `include/ram_buffer.h`) + (src−0x600)*32. Das ist **Kachel src−0x600 von Bogen D** (Bogen D = Spalte 5 von `layered.tsv`, in `map_layers.c:357-359` nach gMapLayerData dekodiert).
  - `src < 0x600`: aus VRAM-Kachel `512+src` (absolut, ab Block 0).
  - Ziel: absolute VRAM-Kachel `512+dst`.
- Die absolute Kachel eines Karteneintrags ist `charBase*512 + (entry & 0x3ff)`.

**So erzeugt man Frame t:**
1. VRAM vorbereiten: Blöcke 1/2/3 aus den Spalten 2/3/4 von `layered.tsv` und Bogen D aus Spalte 5.
2. Die Kanäle wie oben aufbauen; pausierte Kanäle (`channel 0x8N`) überspringen.
3. Das Update t+1 Mal ausführen und dabei ein Array von VRAM-Kacheln verändern.
4. Danach normal mit den veränderten Kacheln rendern.

Die Schleifen sind kurz (der Wasserzyklus von 34 dauert 24 Frames; 127 springt nach 10+10 Frames). Ein GIF bzw. eine Vorschau kann 1..N Frames weiterschalten. Der Metakachel-Atlas muss pro Frame neu aufgebaut oder, besser, pro Kachel zwischengespeichert werden.

## (d) Platzhalter 0xfff

**Mechanismus** (VERIFIZIERT):
- `Tilemap_ConvertBuffer` (`src/field/field/map_layers.c:110-122`) führt `Tile_ConvertMap` (`src/graphics/tile/convert_map.s:8-50`) auf der Blockebene aus.
- r5 = 0xFFF00000 prüft `(cell<<20) == 0xfff<<20`.
- r4 beginnt bei 0xFFFFF001; `cell + r4` (auf 16 Bit gekürzt) = `(cell & 0xf000) | k`, und r4 wird pro Platzhalter erhöht.
- Der ungenutzte C-Zwilling `Tilemap_NumberPlaceholderBlocks` (84-103) tut dasselbe.
- Ergebnis: **Die k-te Zelle (ab 0, zeilenweise über alle 128×128 Zellen, alle Ebenen zusammen), deren untere 12 Bits 0xfff sind, wird zu Block k. Ihr oberes Nibble bleibt erhalten.**
- Beim Zeichnen wird dann `Ram_MapBlocks[(cell<<20)>>19]` verwendet (nur die unteren 12 Bits, 411-437).

**Überprüfung.** Für jede der 182 Karten ist die Anzahl der Platzhalter gleich der Zeilenzahl von `metatiles.tsv` (`allph.py`). Die Renderings von 034 und VenusEntrance werden zu zusammenhängender Grafik (siehe unten). Platzhalter werden also nicht von unbekanntem Code gefüllt: Sie sind die eindeutigen Blöcke der Karte in Lesereihenfolge. Das `XXX` in `src/map/README.md` lässt sich damit beantworten. (Gezählt werden nur Zellen, die beim Laden genau 0xfff enthalten; Zellkopien zur Laufzeit mit `Map_CopyMetatileIndicesRect` geschehen später.)

**Regel:** vor dem Rendering `n=0; for y in 0..127: for x in 0..127: if cell&0xfff==0xfff: cell=(cell&0xf000)|n; n+=1`.
Für einen Editor hat das Folgen:
- Wird eine Zelle zu 0xfff gemalt oder von 0xfff weg, werden alle späteren Platzhalter neu nummeriert.
- Beim Bearbeiten muss die Anzahl der Platzhalter gleich der Blockanzahl bleiben, sonst verschieben sich die gespeicherten Blöcke.
- Die aufgelöste Blocknummer anzeigen und beim Speichern 0xfff nur dort ablegen, wo `resolved == running count` gilt. Alternativ die Zellen unverändert lassen und 0xfff als „nächster eindeutiger Block“ behandeln.

## Überprüfte Renderings

Alle in `(a scratch folder)`:
- `cur_034.png`, `cur_VenusEntrance.png`: der aktuelle Viewer (fehlerhaft).
- `ph_034.png`, `ph_VenusEntrance.png`: nur die Platzhalter-Korrektur (034 zusammenhängend; Venus noch mit falschem Kachelsatz).
- `new_034.png`: alle Korrekturen. Zusammenhängender Fluss/Wald in den Zellen 1..25. Der Rest ist Füllung außerhalb der Kamera.
- `new_VenusEntrance.png`: alle Korrekturen. Korrekter Wald und Eingang zum Venus Lighthouse.
- `new_040.png` vs. `new_040_noblend.png`: additives Fackelglühen (0x3f42, 0x1003).
- `new_080.png` vs. `_noblend`: Wasser überblendet mit 9/16 + 10/16.
- `new_016.png`: Räume des Sol Sanctum, 0x3f44 auf Ebene 1.
- `new_134.png`: deckende Dunkelheit. `new_134_sceneblend.png`: mit Altmillers 0x3f42/0xc04, Dunkelheit bei 4/16.
- `new_104.png` (Anker in der Kameramitte), `cam_104_0_0.png`, `cam_104_128_208.png`: Parallaxe-Himmel.
- `new_147.png`: treibende Sand-Überlagerung.
- `new_047.png`, `new_103.png`.
- `anim_034_f00..f40.png`, `anim_034.gif`, `anim_034_compare.png`: Die Wasser-Animationsframes 0 und 24 unterscheiden sich.

## Empfohlene genaue Änderungen an gsmap/project.py

1. **Szenenressourcen** (ersetzt die Zuordnung in `_read_directory`):
   - `directory.s` zu einer geordneten Eintragsliste expandieren. Die Makros genau anwenden: `group K, a,b` → `K_a, K_b`; `area S, L, maps` → `Field_MapNN…, Tileset_SPalette, Tileset_STiles<L…>`; `recolor P, maps` → `Field_MapNN…, Tileset_PaletteP`; `overlays`; `unused N` → N Einträge; `resource , X` → X.
   - `base = index('Field_Map001')` setzen.
   - Jede Zeile von `src/field/layered.tsv` ist `[header, palette, blk1, blk2, blk3, sheetD]`; jede davon auf `entries[base+v]` abbilden.
   - Nach der Kopfbeschriftung schlüsseln (`Field_MapNNN` / `Field_<Name>`) und die erste Zeile verwenden. Die Karten 108 und 110 haben zwei Zeilen mit unterschiedlichen Paletten (45/58 und 15/18). Die Alternative zugänglich machen.
   - Beschriftungen über das vorhandene `self.symbols` auflösen. Referenzimplementierung: `dirmap.py`.
2. **Atlas:** absolute Kachel `a = char_base*512 + (e&0x3ff)`.
   - Block `a//512` 1..3 → `[blk1, blk2, blk3][a//512-1]`. Block 0 = Fensterkacheln, also überspringen. 4+ ist ungültig.
   - Die Palettenzeilen 14/15 gehören nicht zur Karte (UI). Transparent oder in einer Debug-Farbe anzeigen.
3. **Platzhalter:** 0xfff in `load_grid` für das Rendering zur laufenden Ordnungszahl auflösen (Regel in d). Den Test `== EMPTY → skip` entfernen. Das rohe Raster zum Speichern behalten.
4. **Fenster:** `gx = (layer.x//2 + bounds.left//2 + i) % 128`, für y ebenso (wiederholen, nicht überspringen). Für Ebenen mit rate≠16 oder drift≠0 die Ankerregel für die Kameramitte aus (a) verwenden.
5. **Überblendung:** blend.tsv parsen (`control`/`level`/`jump`/`stop`/`end`). Von hinten nach vorn mit den BLDCNT/BLDALPHA/BLDY-Formeln aus (b) zusammensetzen. Den Schieberegler für die Ebenendeckkraft nur näherungsweise auf EVA/16 voreinstellen (das exakte Ergebnis ist additiv: `top*EVA + below*EVB`).
6. **Animation:** ein veränderbares Kachel-Array `vram[2048]` plus `sheetD[512]` führen. Die Kanäle gemäß (c) weiterschalten. Eine Framenummer oder eine Wiedergabesteuerung anbieten.
7. **Kameragrenzen (optional):** standardmäßig die Grenzen aus dem Kopf. „Auf Inhalt zuschneiden“ oder die Grenzen der Szeneneingänge anbieten. Szene → Kartenindex kommt aus `src/field/scenes.s` (`scene name, code, area, kind, map`, wobei map = die Zeile in `layered.tsv`). Die Grenzen stehen in den `struct SceneEntrance`-Tabellen in `src/scene/*.c`.

## Offene Fragen

- Wie Überblendungen bei Karten funktionieren, deren Skript kein `control` hat (039/042/043/114/125). ERSCHLOSSEN: Eine Szene setzt BLDCNT; nicht nachverfolgt.
- Von Szenen gesetzte Überblendungen und Fortsetzungen von Animationen (`channel 0x8N`) pro Karte: Nur Altmiller (134) wurde nachverfolgt.
- Welche Zeile von `layered.tsv` eine Szene verwendet, wenn eine Karte zwei hat (108, 110). Beide Paletten sind gültig.
- Warum nur vertikale Drift alle 32 BG-Zeilen füllt (`map_layers.c:600-604`, ein XXX in alchemy). Für ein statisches Rendering spielt das keine Rolle.
- Kameragrenzen für andere Karten als 034 wurden nicht tabelliert. `scenes.s` + Eingangstabellen würden sie liefern.
- Geprüft wurde nur der Zweig der EN-Edition; `layered.tsv` hat keine Editionsvarianten.
