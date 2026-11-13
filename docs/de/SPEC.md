<!-- translated from docs/SPEC.md @ a658d8254020 -->
# gs-mapedit: Editor-Spezifikation und Bauplan

*Dies ist eine Übersetzung der englischen [SPEC.md](../SPEC.md). Wenn sich die beiden unterscheiden, ist die englische Fassung aktuell.*

Umfang: ein Karteneditor für **Golden Sun: The Broken Seal**, aufgebaut auf alchemys Quellbaum. Er deckt **lokale Karten** (Städte, Dungeons, Innenräume) und die **Oberwelt** ab. The Lost Age teilt das Format der lokalen Karten, kommt also später mit geringem Aufwand dazu. Seine Oberwelt-Engine ist in alchemy noch größtenteils Assembly.

Der Editor liest und schreibt nur alchemys Quelldateien: TSV, PNG und eng begrenzte Bereiche von C/asm-Tabellen. Er fasst nie ein ROM an. Ausführliche Belege mit file:line-Verweisen stehen in `docs/research/` (`rendering.md`, `local-connections.md`, `overworld.md`). Diese Datei hält die Entscheidungen fest.

## Grundregeln

1. **Byte-genauer Round Trip.** Alles Unbearbeitete zu laden und zu speichern muss die Datei Byte für Byte reproduzieren. Jede Dateiart bekommt einen Round-Trip-Test über den ganzen Baum. Ein unbearbeiteter Build muss weiterhin bei `compare` OK ergeben.
2. **An Ort und Stelle bearbeiten; anhängen, nicht einfügen.** Zeilenpositionen in Tabellen sind Identitäten. Akteursnummer = 8 + Platzierungszeile. Szenen-ID = Zeile in `scenes.s`. Ausgangstabellen benutzen einfache Szenennummern. Eine eingefügte Zeile nummeriert Dinge stillschweigend um, deshalb kommen neue Zeilen ans Ende.
3. **Vor dem Speichern prüfen.** Jede Operation hat Invarianten (unten). Der Editor weigert sich, einen Zustand zu speichern, der eine davon verletzt, oder markiert ihn deutlich.
4. **Der Build ist der Richter.** Nach dem Speichern `make tbs-en` ausführen. Der Editor zeigt Build-Fehler an. Ein Testspiel in mGBA ist die letzte Prüfung.
5. **alchemy festlegen.** Gegen einen bekannten Commit arbeiten. Vor dem Wechsel zu einem neuen `tests/roundtrip.py` und die Alles-rendern-Prüfung ausführen (etwa 2 Minuten). Sie haben die Pfad-Umstrukturierung vom 19. Okt. sofort bemerkt.

## Lokale Karten

### Darstellung (umgesetzt, auf allen 182 Karten überprüft)

- **Ressourcen:** Palette, Char-Blöcke 1–3 und Sheet D jeder Karte kommen aus ihrer `gMaps`-Zeile (`map/maps.c`), aufgelöst über das expandierte `gamepak/resource_directory.s`. Die Karten 001, 002, 108 und 110 haben alternative Zeilen.
- **Platzhalter:** Das k-te `0xfff`-Feld, zeilenweise über das ganze 128×128-Raster, ist Block k mit erhaltenem oberem Nibble (`field/map_grid_convert.s`). Die Anzahl der Platzhalter entspricht auf allen 182 Karten der Zeilenzahl von `metatiles.tsv`.
- **Fenster:** Das Fenster jeder Ebene beginnt am Ursprung der Ebene plus den Grenzen aus dem Header und läuft bei 128 um.
- **Noch zu tun:**
  - Überblendung (`blend.tsv`: BLDCNT/BLDALPHA/BLDY);
  - Kachelanimation (`animation.tsv`, Sheet D);
  - Parallax-Verankerung für die Karten 047, 103, 104, 147 und 148;
  - optionale Kameragrenzen aus den Szeneneingängen.

  Die Regeln stehen in `rendering.md`.

### Bearbeitbare Daten und Invarianten

| Ding | Datei | Bearbeitung | Invarianten / Hinweise |
|---|---|---|---|
| Blöcke pro Feld (3 Ebenen) | `map.txt`, das Bild jedes Felds | aufgelöste Block-IDs malen | Gespeichert mit dem **Platzhalter-Encoder**: zeilenweise mit Zähler k durchgehen. Ein Feld, dessen Block == k ist, wird als `0xfff` geschrieben (oberes Nibble erhalten) und k++; andere Felder werden explizit geschrieben. Auf allen 182 Karten als exakte Umkehrung überprüft. |
| Blockdefinitionen | `cell_pictures.tsv` | neue 2×2-Kachelkombinationen anhängen | Höchstens 4,095 Blöcke. Zeilennummer = Block-ID. |
| Kollisionscodes | `map.txt`, das Verhalten jedes Felds | malen | Pro Ebenenfenster. Die Codes 1–239 können Ereignisse tragen (Ausgänge, Truhen). |
| Höhe / Form | `map.txt`, die Form jedes Felds, + `shapes.tsv` | malen | Pro Ebenenfenster. |
| Truhen / Psynergie-Steine | `treasure_spot x, z, id`-Zeilen in `map.s` | hinzufügen/verschieben/entfernen | **id muss dem Kollisionscode bei (x, z) entsprechen**: überprüft 418/418. Höchstens 10 pro Karte. Endmarkierungszeile `ff ff ff`. Der Inhalt braucht ein `SEARCH(SEARCH_CHEST)`-Ereignis in der Szene mit einem neuen Flag. |
| Kachelanimation | `animation.tsv` | später | Höchstens 16 Kanäle. |

Geteilte Dateien: Blöcke können aus dem Ordner einer anderen Karte kommen, und Felder und Attribute aus `default/` werden ebenfalls geteilt. Der Editor zeigt, wenn eine Datei geteilt ist, und warnt vor dem Bearbeiten.

### Szenentabellen: ein Hook, Overrides im Besitz des Editors

**Entwurf (Vorgabe des Inhabers): minimale Änderungen an alchemys Dateien.**
- Die Engine liest jede Szenentabelle über `gOverlayArea`, die Einstiegstabelle des Szenen-Overlays im RAM. Overlays werden an genau einer Stelle geladen: `Scene_LoadOverlay` (`system/main_routine.c`).
- Der Editor fügt dort **eine Zeile** hinzu, `MOD_SCENE_LOADED(gMainRoutineWork.next, &gOverlayArea);`. Das ist ein Makro, das zu nichts expandiert, außer der Build definiert `GSMOD`, sodass der Original-Build weiterhin dem Retail-ROM entspricht.
- Mit `GSMOD` ruft das Makro vom Editor erzeugten Code in `games/tbs/src/mod/` auf. Dieser Code tauscht die Funktionszeiger der Einstiegstabelle (Eingänge, Ausgänge, Platzierungen, Ereignisse, Regionen) gegen Funktionen aus, die die Override-Tabellen des Editors für diese Szene zurückgeben, und lässt den Rest in Ruhe.
- Die Weltkarte ist ebenfalls ein Szenen-Overlay, also deckt derselbe Hook Oberwelt-Symbole, Ausgänge und Ereignisse ab.
- Die `.c`-Dateien der Szenen werden nie umgeschrieben. Override-Tabellen liegen im Mod-Ordner, im ROM. Reine Datendateien (Kartentabellen, Truhenzeilen) werden weiterhin direkt bearbeitet.

Die zugrunde liegenden Tabellen, zum Nachschlagen:

Szenen liegen in `games/tbs/src/scene/<place>.c`. Sie enthalten fünf Tabellenarten, alle C-Arrays auf Dateiebene aus Literalen und Makros:

| Tabelle | Anzahl | Zeilenfelder |
|---|---|---|
| Eingänge | 189 | entrance, required_flag, x, y, z, facing, Kameragrenzen |
| Ausgänge | 99 | kind → (scene, entrance), optionales Flag |
| Platzierungen | 274 | sprite, condition, behaviour, x, y, z, facing, talk facing, flags |
| Ereignisse | 263 | kind/control, trigger, condition, value |
| Regionen | 14 | Min/Max-Box, condition, exit kind |

Der Editor *liest* diese Arrays aus den `.c`-Dateien der Szenen, wobei er einen Override mit den ursprünglichen Zeilen einer Szene vorbelegt, und *schreibt* nur die Override-Kopien in `mod/`. Ereignisse: die bekannten Steuerwörter dekodieren und unbekannte wörtlich behalten (etwa 220 sind rohes Hex).

Prüfung:
- Der Zieleingang jedes Ausgangs existiert in der Zielszene.
- Platzierungszeilen werden nicht mitten in die Tabelle eingefügt (Verschiebung der Akteursnummern).
- Die Overlay-Größe bleibt unter 32 KB (das größte hat 120 B frei).
- Zeilen mit x=z=0 werden vom Code positioniert; der Editor markiert sie als schreibgeschützt.

Der Ausgangsgraph ist: Kollisionscode / Skript / Region → Ausgangsart → Ausgangstabelle → (Szene, Eingang) → Eingangszeile. Der Editor zeigt ihn als anklickbare Links zwischen Karten.

### Neue Karten (letzte Stufe)

Die Checkliste steht in `local-connections.md` §6:
- 25 freie Plätze im Ressourcenverzeichnis, festgelegt bei 0x08320000;
- Zeilen an `gMaps` (`map/maps.c`) und `scenes.s` anhängen;
- die Kartenzeile vor den Overlays zu `ld_script.ld` hinzufügen, plus Overlay, Musik, Gebietsname und Kampfregeln;
- Gruppe ≤ 0x7f, Szenen-IDs < 511.

**ROM-Platz ist die eigentliche Grenze:** 3.5–43 KB frei am 8-MB-Ende, je nach Edition. Eine echte neue Karte bedeutet wahrscheinlich, das ROM über 8 MB hinaus zu vergrößern, was ungetestet ist.

## Oberwelt

| Ding | Datei | Hinweise |
|---|---|---|
| Boden- + Overlay-Felder | `map/world/blocks.tsv` | 320×512 u32. Chunks sind 16×16 Felder, in der TSV 32 breit angeordnet und in der Welt 16×16. Boden = Chunk c, Overlay = c + 320. Alternativen 256–319 (Schneesatz, Story-Brücke). Feld-Bits: 0–15 Block, 16–23 Tritt-/Ereigniscode, 24–30 Geländeart (= Kampfregion), 31 Verhaltensbank. |
| Blöcke | `map/default/cells.tsv` | 4,386 × 4 Kachel-Bytes. **Mit lokalen Karten geteilt.** Lieber anhängen. |
| Begehbarkeit | `map/default/attributes.tsv` | Pro 8×8-Kachel, 4×4 Nibbles. Overlay gewinnt, dann Boden, sonst 7. Die Werte 5–12 sind begehbar. Ebenfalls geteilt. |
| Grafiken | `graphics/world_map/*.png` | 8bpp, 256 Kacheln pro Ebene, 224 Farben. Satz B ist der verschneite Norden. PNG-Modus und Indizes erhalten. |
| Stadtsymbole / Betreten | `scene/world_map.c` `gWorldMapPlacements`, `gWorldMapEvents`, `gWorldMapExits` | Symbol = Akteur 8 + Zeile. Berühren löst Trigger 100 + Akteur aus → `EVENT_EXIT` → Ausgang → (Szene, Eingang). Manche Einträge sind stattdessen Tritt-Codes. Muss mit `gWorldMap_PlaceMarkers` (Akteur 11 + i) übereinstimmen. |
| Hinaus in die Welt | `gWorldMapEntrances` | Das `SCENE_EXIT(n, 2, e)` einer Stadt setzt die Gruppe auf Zeile e. |
| Kämpfe | `object/zonedata.c`-Regeln → `object/encounter.tsv`-Zonen | Geländeart + Verhalten → Regel → Zone (104 feste Zeilen). |

Einschränkungen:
- Die Karte im Pausenmenü (`picture.png`) ist eigene Grafik und muss nach Änderungen an der Küste von Hand neu gemalt werden.
- In TBS gibt es keine sprachspezifischen Oberwelt-Varianten.
- Die Oberwelt von The Lost Age ist anders (2048 Chunks, 32×32), und ihre Engine ist größtenteils Assembly, also liegt sie außerhalb des Umfangs, bis alchemy sie matcht.

## Bauplan

| Stufe | Liefert | Überprüfung |
|---|---|---|
| **1. Betrachter** ✅ | Alle 182 lokalen Karten korrekt dargestellt; Overlays; Hover-Infos | Round Trip 895 Dateien; Alles rendern; Sichtprüfungen |
| **1b. Darstellungstreue** | Überblendung, animierte Kacheln (abspielen/Einzelbild), Parallax-Verankerung, Zuschnitt auf Kameragrenzen | Mit den validierten Darstellungen aus `rendering.md` vergleichen; idealerweise mGBA-Screenshots |
| **2. Lokales Malen** ✅ außer dem Editor für neue Blöcke | Blockpalette aus dem Atlas; Malen pro Ebene; Kollisions-/Höhenpinsel; Editor für neue Blöcke (4 Kacheln wählen); Rückgängig/Wiederholen; Speichern mit dem Platzhalter-Encoder | Unbearbeitetes Speichern byte-identisch; bearbeitetes Speichern baut (`make tbs-en`); startet in mGBA |
| **3. Markierungen + Szenentabellen** ✅ Truhen hinzufügen, füllen, verschieben und entfernen; Türen per Klick verknüpft (neu verknüpfen, hinzufügen, entfernen, Skript-Türen eingeschlossen); Ereignisse in Worten mit neuen Zeilen, Schildern, Tritt-Nachrichten, Personen und Bedingungen; Ausgangsbereiche; Steine verschieben; Eingänge, NPCs, Ausgänge | Platzierung von Truhen/Steinen (Markierung + Kollision + Ereignis); Bearbeitung von Eingängen/Ausgängen/Platzierungen; Navigation im Ausgangsgraphen zwischen Karten | Tabellen-Round-Trip byte-identisch über alle 201 Szenen; Build; Testspiel einer Ausgangsänderung |
| **4. Oberwelt-Betrachter** ✅ | Welt von oben mit Satz A/B, Overlay-Ebene, Begehbarkeit, Overlay für Geländeart/Kämpfe, Stadtsymbole und Ausgangslinks | Den Forschungsprototyp portieren; mit `world_mixed_small.png` vergleichen |
| **5. Oberwelt-Bearbeitung** ✅ Boden-/Overlay-Blöcke, Regionen, Verschieben und Verknüpfen von Symbolen; Tritt-Codes, Kampfzonen und neue Symbole noch offen | Felder malen (Block, Geländeart, Tritt-Code); Symbole, Ausgänge, Eingänge bearbeiten; Kampfzonen | Round Trip von `blocks.tsv` und Tabellen; Build; Testspiel |
| **6. Neue Karten / Szenen** | Assistent für die Checkliste neuer Karten; Anzeige des ROM-Budgets | Build; Testspiel |

Die Stufen 2–3 machen den lokalen Editor wirklich nützlich. 4–5 fügen die Oberwelt hinzu. 6 ist die riskanteste, weil sie vom ROM-Platz abhängt.

## Offene Fragen

- ~~Verlangt der Build Platzhalteranzahl = Blockanzahl?~~ **Nein.** Getestet: Eine Bearbeitung, die 56 Platzhalter für 441 Blöcke übrig lässt, baut und linkt. Der Encoder schreibt spätere Blöcke explizit, sobald ein erstes Vorkommen übermalt ist, also ist der Diff größer, aber gültig. Das Aussehen im Spiel braucht noch ein Testspiel.
- Karten, deren `blend.tsv` BLDCNT nie setzt (039, 042, 043, 114, 125): Die Überblendung kommt wahrscheinlich aus dem Szenencode.
- Was die `scene_points` von TLA sind; was `touched_trigger` schreibt; Werte für das Platzierungsverhalten über 2.
- Ob ein ROM über 8 MB auf den Ziel-Emulatoren und auf echter Hardware korrekt startet und speichert.
