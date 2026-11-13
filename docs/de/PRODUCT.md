<!-- translated from docs/PRODUCT.md @ 34e70fd313ab -->
# gs-mapedit für Spieler: Produktplan

*Dies ist eine Übersetzung der englischen [PRODUCT.md](../PRODUCT.md). Wenn sich die beiden unterscheiden, ist die englische Fassung aktuell.*

**Zielgruppe:** Fans und Modder ohne technischen Hintergrund, also ohne Terminal, Hex, C, git oder Build-Systeme.
**Auslieferung:** eine paketierte Desktop-App mit Installationsprogramm.
*(Vom Projektinhaber entschieden, 2026-10-20.)*

Die Engine-Schicht, die es heute gibt, bleibt das Fundament. Dazu gehören die Dateiformate, byte-genaues Speichern, die Invarianten, der Szenentabellen-Hook und der Build. Dieser Plan handelt von der Schicht, die Spieler sehen.

## Grundsätze

1. **Namen, Bilder und Orte, nie Codes.** Jeder Wert, den ein Spieler sieht, ist benannt, in einer Vorschau gezeigt oder auf einer Karte dargestellt. Rohe Zahlen liegen hinter einem Schalter „Erweitert“.
2. **Eine Absicht, eine Aktion.** „Eine Truhe mit einem Herb hinzufügen“ wird eine einzige Aktion, obwohl sie die Markierungsliste, die Kollision, ein Szenenereignis und ein neues Flag berührt.
3. **Das Spiel lässt sich nicht unbemerkt kaputtmachen.** Invarianten werden wie heute durchgesetzt und in einfacher Sprache erklärt: „Diese Tür führt noch nirgendwohin.“ (✅ der Knopf Prüfen, der auch vor jedem Bauen läuft.)
4. **Immer einen Klick vom Spielen entfernt.** Bearbeiten, dann Spielen. Der Build ist unsichtbar, außer er schlägt fehl, und Fehler lesen sich als Anleitung, nicht als Compiler-Ausgabe.
5. **Keine Weitergabe von ROMs.** Mods werden als Patch-Dateien geteilt, die Spieler auf ihren eigenen Dump des Moduls anwenden.

## Was Spieler tun (Abläufe → Bildschirme)

| Ablauf | Bildschirm / Interaktion | Engine-Teile (vorhanden?) |
|---|---|---|
| Die Orte des Spiels erkunden | **Weltansicht:** Oberwelt plus jede Stadt und jeder Dungeon, mit eingezeichneten Verbindungen | Renderer ✅, Ansicht Verbindungen ✅ (Ort für Ort), Atlas ✅ (alle Orte auf einmal), Dorthin gehen ✅ (einer Tür folgen), Oberwelt ✅ |
| Einen Teil einer Karte neu malen | **Malen:** Kachelpalette nach Thema, Pinsel, Füllen, Bereiche kopieren/einfügen | Blöcke malen ✅; Füllen ✅; Kopieren und Einfügen (Stempel) ✅ |
| Ändern, wo man laufen kann | **Begehbarkeits-Pinsel:** begehbar / gesperrt / Absatz / Leiter / Wasser, als klares Overlay gezeigt | Kollision malen ✅; **benannte Codes ❌ (Forschung)** |
| Eine Tür verschieben / ändern, wohin sie führt | Auf eine Tür klicken, dann das Ziel durch Klick auf die Zielkarte wählen | ✅ Werkzeug Türen |
| Eine Truhe oder einen Psynergie-Stein hinzufügen/verschieben | Eine Truhe absetzen; Inhalt wählen (Gegenstandsauswahl mit Symbolen, Münzen, Mimic) | ✅ Werkzeug Truhe (Gegenstände, Münzen); Steine nur verschieben |
| Personen platzieren/verschieben | NPCs mit Sprite-Vorschauen ziehen; sehen und bearbeiten, was sie sagen | Positionen ✅; Sprite-Vorschauen ✅; was sie sagen, beim Überfahren mit der Maus ✅; Hinzufügen und Entfernen ✅ |
| Ausprobieren | **Spielen:** Build plus Emulator an dieser Karte öffnen | Spielen mit einem Klick ✅ (speichert, prüft, baut, öffnet am gerade bearbeiteten Ort) |
| Teilen | **Mod exportieren:** eine Patch-Datei plus eine Beschreibung | ✅ BPS vom Original-Build zum Mod-Build |
| Fehler rückgängig machen / neu anfangen | Verlaufsbereich; „diese Karte zurücksetzen“ | Rückgängig und Wiederholen ✅ (die letzten 30 gespeicherten Aktionen, über Sitzungen hinweg erhalten); Ort zurücksetzen ✅ |

## Namensschicht (Forschung nötig, meist Nachschlagen)

- **Kollisionscodes:** Wand, Boden, Absätze, Kletterstellen, Untersuchungsstellen, Gefahr, Ausgänge, Truhen. Quellen: `step.c`, `events.c`, die Forschungsdokumente.
- **Szenen:** Namen aus `scenes.s` plus Gebietsnamen (die eigenen Ortsnamen des Spiels) zur Anzeige.
- **Gegenstände:** Namen aus `include/item_ids.h`, plus Gegenstandssymbole aus den Grafiken des Spiels.
- **Sprites:** Sprite-ID → Name und ein Vorschaubild aus den Objektgrafiken.
- **Dialoge:** Nachrichten-ID → Text aus `text/en.po` (10,724 Einträge).
- **Flags:** Namen aus `include/flags.h`, plus ein Verteiler für neue Truhen-Flags (≥ 0xe00, unbenutzt).

## Paketierungsarchitektur (Empfehlung)

- **Hülle:** pywebview (das native WKWebView) in einem PyInstaller-Bundle: eine 30 MB große `.app` mit Python, dem Server und den Seiten. *(Von Tauri geändert, 2026-10-22: Das Backend ist schon Python, und Tauri würde eine Rust-Toolchain ohne Gewinn hinzufügen. Tauri bleibt eine Option, falls das Backend zu Rust wechselt.)*
- **Backend:** der heutige Python-Server, im selben Prozess.
- **Spielquellcode:** Die App lädt alchemy bei einem festgelegten Commit herunter, den wir geprüft haben. Spieler sehen nie git. Updates sind ausdrücklich: „Neue alchemy-Version verfügbar; getestet ✓“.
- **Toolchain:** der schwierigste Teil.
  - alchemy braucht seine festgelegten Compiler (aus dem Quellcode gebaut), binutils und seine eigenen C-Werkzeuge (libpng).
  - Plan: diese pro Plattform in der CI bauen und als vorgefertigte Binärdateien ausliefern. Die Compiler stehen unter der GPL; wir veröffentlichen ihre Quellen.
  - Plattformen: zuerst macOS (Intel + Apple Silicon), dann Windows (alchemy unterstützt Windows offiziell nur über WSL, daher ist eine native Portierung der Werkzeuge das Risiko), dann Linux.
- **Patches:**
  - Weil der Original-Build byte-identisch mit dem Retail-ROM ist, gilt: Patch = diff(Original-Build, Mod-Build), lokal berechnet, ohne je ein Retail-ROM anzufassen.
  - Spieler wenden ihn mit einem beliebigen BPS-Patcher oder mit unserer App auf ihren eigenen Dump an.
- **Testspielen:** mGBA (MPL-2.0) mitliefern oder ein installiertes erkennen; an der bearbeiteten Karte starten, falls ein Debug-Einstiegspunkt das erlaubt.

## Meilensteine

1. **Spieleroberfläche in der aktuellen App.** Alles hier geht direkt in die Desktop-Hülle über. Es umfasst:
   - die Namensschicht;
   - Begehbarkeits-Pinsel;
   - Türen per Klick verknüpfen;
   - Gegenstands-/Sprite-Auswahl;
   - eine Aktion zum Hinzufügen von Truhen;
   - Prüfung in einfacher Sprache;
   - die Welt-/Verbindungsansicht.
2. **Paketierungs-Spike (macOS):** ✅ App-Bundle und Ersteinrichtung (lädt alchemy herunter, baut einmal). ✅ mitgelieferte Toolchain (kein Homebrew). Offen: Signieren/Notarisieren (braucht eine Developer ID), nativer Build für Apple Silicon, ein Test auf einem wirklich frischen Mac. Erfolg = ein frischer Mac kommt ohne Terminal von null bis „Spielen“.
3. **Patch-Export** ✅ (BPS, gegen rom.sha1 geprüft). Patches anderer anwenden ✅ (der Patcher).
4. **Oberwelt-Bearbeitung** ✅ (Stufen 4–5 von SPEC.md): Boden, Overlay, Regionen und ihre Kämpfe, Stadtsymbole (verschoben, verknüpft, hinzugefügt), Trittstellen.
5. **Paketierung für Windows und Linux.** Windows läuft über WSL mit einem Installationsskript (früher Test); Linux läuft aus dem Quellcode.

## Risiken

- **Portierbarkeit der Toolchain (Windows).** alchemys Build setzt eine Unix-Shell voraus. Das könnte eine WSL-Integration oder eine native Portierung seiner kleinen C-Werkzeuge erfordern.
- **Änderungen upstream.** alchemy ändert sich täglich. Einen Commit festlegen und Updates von unseren Round-Trip- und Alles-rendern-Prüfungen plus einem Test-Build abhängig machen.
- **Umfang der „Bedeutung“.** Manche Kollisionscodes und Ereignisarten sind selbst alchemy noch unbekannt. Unbekanntes bleibt sichtbar, aber als „unbekannt (erweitert)“ beschriftet.
- **Rechtliche Haltung:** Wir liefern nie ROMs, extrahierte Assets oder gebaute Spiele aus. Spieler liefern nichts (The Broken Seal wird aus dem Quellcode gebaut), und die App lädt alchemy selbst herunter.
