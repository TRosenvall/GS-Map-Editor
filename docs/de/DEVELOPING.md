<!-- translated from docs/DEVELOPING.md @ 0055eb8d2996 -->
# GS Map Editor entwickeln

*Dies ist eine Übersetzung der englischen [DEVELOPING.md](../DEVELOPING.md). Wenn sich die beiden unterscheiden, ist die englische Fassung aktuell.*

Wie du den Editor startest, baust, testest und aktualisierst, und wie seine Funktionen intern arbeiten. Wie man ihn benutzt, steht in der [README](../../README.de.md).

## Aus dem Quellcode starten

Braucht Python 3 mit Pillow und einen alchemy-Checkout, der schon gebaut wurde.

```sh
python3 server.py                  # alchemy unter ~/gs_project/alchemy-port
python3 server.py --root /path/to/alchemy --port 8765
# http://127.0.0.1:8765/ öffnen
```

### Desktop-App (macOS)

`GS Map Editor.app` ist der Editor in einem eigenen Fenster, für Spieler, die nie ein Terminal öffnen.

```sh
python3 -m venv .venv && .venv/bin/pip install pywebview pyinstaller pillow
python3 packaging/build_toolchain.py                          # GBA-binutils + libpng, ~10 Min., einmalig
.venv/bin/python packaging/make_icon.py                       # packaging/icon.icns
.venv/bin/pyinstaller --noconfirm packaging/gsmapedit.spec    # -> dist/GS Map Editor.app
python3 packaging/make_dmg.py                                 # -> dist/GS-Map-Editor-<version>.dmg
python3 packaging/sign_and_notarize.py --identity "Developer ID Application: …"   # braucht ein Apple-Developer-Konto
.venv/bin/python desktop.py                                   # oder ohne Paketierung starten
```

Die App bringt ihre eigenen Build-Werkzeuge mit (`packaging/toolchain`, 15 MB): GNU binutils für den GBA, ein statisches libpng und einen kleinen `libpng-config`-Ersatz, der alchemys `tools/Makefile` antwortet. Sie werden aus festgelegten Quellen mit geprüften Prüfsummen gebaut und brauchen nichts außer macOS. Damit brauchen Spieler nur Apples kostenlose Entwicklerwerkzeuge; Homebrew nutzt nur ein Build ohne die Toolchain. `GSMAP_NO_BREW=1` blendet Homebrew aus, um zu beweisen, dass ein Build es nicht braucht.

Beim ersten Start zeigt sie eine Einrichtungs-Checkliste (`static/setup.html`, `gsmap/setup.py`). Jeder Schritt wird geprüft, nie angenommen, und lange Schritte zeigen ihr Protokoll live:
1. Apples Entwicklerwerkzeuge (öffnet Apples Installationsprogramm).
2. Die Build-Werkzeuge: in der App enthalten. Ein Build ohne sie greift auf Homebrew und die Pakete aus alchemys INSTALL.md zurück, geprüft danach, was der Build benutzt, nicht nach Formelnamen.
3. Der Spielquellcode: alchemy herunterladen (festgelegt auf den Commit, mit dem dieser Editor getestet wurde) nach `~/Documents/GSMapEditor/` (ohne Leerzeichen: der Build kommt damit nicht zurecht), oder einen vorhandenen Checkout wählen.
4. `make bootstrap` (die Compiler des Spiels, einmalig aus den Quellen in alchemys Submodul `alchemy-gcc` gebaut, ohne Download), dann ein erstes `make tbs-en`.

Danach öffnet die App direkt den Editor. Die Einstellungen liegen in `~/Library/Application Support/GS Map Editor/`. Die App enthält keine Spieldaten: Das Spiel wird auf dem Mac des Spielers aus alchemys Quellcode gebaut. Ihre beiden Server lauschen nur auf diesem Rechner, hinter einem zufälligen Token. `desktop.py --no-window` gibt ihre Adressen aus, zum Testen.

### Linux und Windows (WSL)

Unter Linux läuft der Editor aus dem Quellcode und öffnet sich im Browser: `python3 desktop.py` (braucht `python3-pil`) zeigt dieselbe Einrichtungs-Checkliste, mit den apt-Paketen aus alchemys INSTALL.md statt Homebrew. Ihre Installation braucht `sudo`, deshalb zeigt die Checkliste den Befehl, statt ihn auszuführen. Die Einstellungen kommen nach `~/.config/gs-map-editor`, der Build-Cache nach `~/.cache/gs-map-editor`, Spielquellcode und Exporte nach `~/GSMapEditor`. Was sich je nach System unterscheidet (Ordner, einen Link öffnen, mGBA, eine Datei anzeigen), steht in `gsmap/host.py`.

Windows führt denselben Linux-Editor in WSL aus, was auch der einzige Weg ist, wie alchemy unter Windows baut:
- `windows/Install-GS-Map-Editor.cmd`, das ein Release mit eingetragenem Tag mitbringt, schaltet WSL ein und installiert bei Bedarf Ubuntu (Administratorrechte, eventuell ein Neustart), führt `windows/setup-in-wsl.sh` in Ubuntu bei diesem Tag aus und legt Verknüpfungen im Startmenü und auf dem Desktop zu `wsl.exe … gs-map-editor` an.
- Der Editor öffnet sich im Windows-Browser über die localhost-Weiterleitung von WSL. Spielen startet das Windows-mGBA aus `Program Files\mGBA` mit dem Pfad `\\wsl.localhost\…` des Spiels. Das Spiel wird auf Ubuntus eigener Festplatte gebaut, da ein Build auf `/mnt/c` um ein Vielfaches langsamer ist.
- Die Seiten zeigen auf jedem System außer einem Mac Ctrl und Alt statt ⌘ und ⌥ (`localWords` in `static/common.js`).

`.github/workflows/linux.yml` prüft das bei jedem Push auf GitHubs Ubuntu-Maschinen: `setup-in-wsl.sh` installiert den Editor, `tests/setup_flow.py` geht die Ersteinrichtung über den installierten Befehl durch, der Build muss `rom.sha1` entsprechen, und die Round-Trip-, Bearbeitungs- und Platzierungstests laufen auf diesem Checkout. Die Windows-Hälfte (die `.cmd`, die WSL-Installation, die Verknüpfung, Windows-mGBA) hat keinen automatischen Test: Dafür braucht es einen Windows-PC.

### Releases

Releases baut GitHub auf seinen Macs mit `.github/workflows/release.yml`: ein Disk-Image für Apple Silicon (`macos-15`) und eines für Intel (`macos-15-intel`). Jeder Job baut die Toolchain und die App, prüft, dass beide für seinen Chip sind, führt `packaging/smoke_test.py` aus (die App startet, findet ihre Werkzeuge und nennt den festgelegten Commit) und erstellt die `.dmg`.

1. Die Version in `packaging/gsmapedit.spec` setzen (`CFBundleShortVersionString`).
2. Die Hinweise, die Spieler lesen, in `docs/releases/v<version>.md` schreiben.
3. Committen, dann `git tag v<version> && git push origin v<version>`. Der Workflow veröffentlicht ein Pre-Release mit beiden Images, selbst wenn der Job für einen Chip fehlschlägt.

**Run workflow** auf der Actions-Seite baut die Images, ohne ein Release zu veröffentlichen. Die Images sind nicht signiert: Der README-Abschnitt „Beim ersten Mal öffnen“ erklärt, wie Spieler an Gatekeeper vorbeikommen, und `packaging/sign_and_notarize.py` übernimmt, sobald es eine Developer ID gibt.

## Wie die einzelnen Funktionen arbeiten

Lokale Karten, The Broken Seal, englische Edition. Wie man sie benutzt, steht in der [README](../../README.de.md).

- **Ansicht:** alle 182 Karten, mit korrekten Tilesets und Platzhaltern, Ein-/Ausschalter und Deckkraft pro Ebene, Overlays für Begehbarkeit und Höhe.
- **Malen:** Blöcke, Begehbarkeit und Höhe, mit ⌥-Klick-Pipette und Rückgängig/Wiederholen. Gespeichert wird alles Unbearbeitete Byte für Byte gleich.
- **Stempel** (S): Zieh ein Rechteck auf, um einen Bereich zu kopieren, dann klick, um ihn einzufügen, hier oder in einer anderen Karte mit demselben Blocksatz (Vale ↔ Debug · Sandbox).
  - Die Kopie enthält alle drei Ebenen plus Begehbarkeit und Höhe.
  - **Nur Objekte** fügt nur die Bäume und anderen Objekte ein, nicht den Boden darunter (ein Farbtest gegen den Hintergrundblock jeder Ebene).
  - Ein Einfügen ist ein Rückgängig-Schritt. Die Zwischenablage übersteht das Wechseln von Karten und das Neuladen der Seite. Esc kehrt zum Kopieren zurück.
  - Karten mit einem anderen Blocksatz verweigern das Einfügen, da jede Blocknummer die falsche Kachel zeichnen würde.
- **Bild importieren** (Karten mit eigenem Tileset; heute die Debug · Sandbox): Wähl ein PNG und eine Ebene und sieh dir eine Vorschau an, dann **Zum Tileset hinzufügen**. Die neuen Blöcke landen in der Stempel-Zwischenablage, bereit, an ihren Platz geklickt zu werden.
  - Der Importer zerlegt das Bild in 8×8-Kacheln und passt seine Farben an eine der 14 Palettenzeilen der Karte an (jede Kachel wählt nur dann ihre eigene Zeile, wenn keine einzelne Zeile passt). Index 0 ist transparent.
  - Kacheln, die schon in den Sheets sind, gespiegelte eingeschlossen, werden wiederverwendet.
  - Neue Kacheln kommen zuerst in leeren Platz. Danach kommen Kacheln, die nur von Blöcken benutzt werden, die die Karte nie platziert. Diese Blöcke werden *ausgemustert* (in der Palette ausgeblendet, vom Stempel verweigert) und in alchemys `games/tbs/src/mod/tilesets.json` aufgeführt.
  - Die Vorschau zeigt die Farben, die das Spiel zeichnen wird, und wie viel Platz noch übrig ist.
- **Ereignisse** (E): alles, was in einer Szene passiert, in Worten, für den Story-Abschnitt, den du wählst:
  - **Personen:** „🗨 Garet: “Ever since the tremors started…”“, Mind-Read-Gedanken und Skripte mit eigener Beschreibung („Fragt vor der Abreise nach dem Bürgermeister, nach der Rückkehr nach den Beben“).
  - **Stellen:** Schilder (mit A lesen), Tritt-Nachrichten, Untersuchungen und was sie finden.
  - **Ausgangsbereiche:** Felder, die als Türen wirken, auf der Karte eingezeichnet. Ändere, wohin sie führen, oder entferne sie.
  - Klick auf eine Person, um ihre Ereignisse zu sehen und **sie etwas sagen zu lassen** (oder eine Zeile für einen Story-Moment hinzuzufügen). Klick auf eine beliebige Stelle, um **ein Schild**, **eine Tritt-Nachricht** oder **eine Person hinzuzufügen**.
  - **Text ändern** öffnet einen Schreibbereich mit Live-Vorschauen der Textfenster: Schreib ganz normal, eine Leerzeile beginnt ein neues Textfenster. **Wann …** legt „Immer“, „Erst sobald <Story-Flag> gesetzt ist“ oder „Nur solange es nicht gesetzt ist“ fest, mit Flags nach Namen.
  - Neue Zeilen werden in einem Block, der dem Editor gehört, zu `en.po` hinzugefügt. Die eigenen Zeilen des Spiels werden nie umgeschrieben: Zu ändern, was jemand sagt, verweist ihn auf eine neue Zeile. Text, den die Schrift des Spiels nicht zeichnen kann, wird vor dem Build abgelehnt.
  - Wenn eine Szene ihre Personen und Ereignisse mit anderen teilt (die Sandbox und der Debug-Hub tun das), sagt der Bereich das.
- **Türen** (D): Jede Tür erscheint auf der Karte mit ihrem Ziel („→ Vale Home“); solche, die nirgendwohin führen, erscheinen rot.
  - Klick auf eine Tür, dann **Ändern, wohin es führt …**: Wähl einen Ort, dann klick auf einen Ankunftspunkt auf seiner Karte.
  - Klick auf eine beliebige andere Stelle und **Hier eine Tür machen …**, um eine Tür zu irgendeinem Ort im Spiel hinzuzufügen. **Tür entfernen** macht alle Felder einer Tür wieder zu Boden.
  - Türen, die Szenenskripte öffnen (die meisten in Vale), werden auch gefunden, indem gelesen wird, welchen Ausgang das Skript anfordert. Ihr Ziel lässt sich ändern; das Skript bleibt.
  - Eine Tür ändert sich in jedem Story-Abschnitt der Szene, über Ausgangs- und Ereignis-Overrides. Die `.c`-Dateien der Szenen bleiben unberührt.
- **Truhen** (K): Klick auf eine freie Stelle, wähl einen Gegenstand (mit seinem Symbol) oder eine Menge Münzen und **Truhe hinzufügen**. Klick auf eine Truhe, um ihren Inhalt zu ändern oder sie zu entfernen.
  - Eine Aktion schreibt alles, was eine Truhe braucht: die Markierung, den Kollisionscode des Felds, ein `SEARCH(SEARCH_CHEST)`-Ereignis in der Ereignistabelle der Szene (als Override, sodass die `.c`-Dateien der Szenen unberührt bleiben) und ein neues „Geöffnet“-Flag aus dem freien Truhenbereich.
  - Der Code ist einer, den keine Ereignistabelle der Szenen dieser Karte benutzt und den keine Karte, die diese Tabellen teilt, in ihrer Kollision hat, sodass nichts anderes untersuchbar wird. Höchstens 10 Truhen und Steine pro Karte.
  - Eine Truhe ist eine `treasure_spot`-Zeile in der `map.s` der Karte, im Teil der Datei für die englische Edition.
- **Truhen und Psynergie-Steine:** zum Verschieben ziehen. Die Markierungszeile und die Kollisionscodes beider Felder werden zusammen aktualisiert, und Speichervorgänge, die die Regel Markierung/Kollision verletzen, werden abgelehnt.
- **Szenentabellen:** Wähl für jede Szene, die die Karte nutzt, eine Tabelle.
  - Eingänge und NPCs erscheinen auf der Karte; zieh sie mit dem Werkzeug „Personen verschieben“ (P).
  - Ausgänge werden als Liste bearbeitet (Art, Zielszene, Eingang, Flag), mit einer Prüfung, dass der Zieleingang existiert.
- **Verbindungen:** ein beliebiger Ort in der Mitte, links jeder Ort, der zu ihm führt, rechts alles, wohin er führt (Tür, geskriptete Tür oder Szenenereignis, und der Ankunftspunkt). Klick auf einen Ort, um dorthin zu wechseln; **Öffnen** springt im Editor zur Tür.
- **Prüfen:** sieht sich jede Karte nach Problemen an, die deine Änderungen im Spiel verursachen würden, und benennt sie in einfachen Worten, jeweils mit einer Lösung und einem Knopf **Anzeigen**, der die Stelle öffnet:
  - Türen, die nirgendwohin führen oder zu einem Ankunftspunkt, den es nicht gibt;
  - Truhen, die sich nicht öffnen lassen, keinen Inhalt haben, sich wegen eines temporären Flags wieder füllen oder sich ein „Geöffnet“-Flag teilen;
  - mehr als 10 Truhen und Steine auf einer Karte; Felder, die fehlende oder ausgemusterte Blöcke benutzen;
  - Änderungen an Szenentabellen, die nicht mehr zum Spielquellcode passen (nach einem alchemy-Update).
  - Das Originalspiel hat eigene Eigenheiten (heute 115, z. B. 83 übrig gebliebene Türen). Jedes Problem wird auch im unveränderten Spiel gesucht, und diese werden ausgeblendet, außer du fragst danach.
  - **Bauen** führt zuerst die Prüfung aus und fragt nach, bevor mit Problemen gebaut wird.
- **Weltkarte** (oben in der Ortsliste): die ganze Oberwelt, beim Scrollen nachgeladen, mit Stadt- und Dungeon-Symbolen, beschriftet mit ihrem Ziel.
  - Overlays: Begehbarkeit (gesperrter Boden in Rot) und Kampfregionen, jeweils benannt nach den Städten darin („Region 1 (Vale, Lunpa…)“).
  - **Boden** / **Overlay**: Blöcke malen (⌥-Klick nimmt einen auf; zuletzt benutzte Blöcke bleiben griffbereit). **Regionen**: Kampfregionen malen. Änderungen werden beim Malen gespeichert; Rückgängig nimmt den letzten Strich zurück, Wiederholen bringt ihn zurück. Felder werden in `map/world/blocks.tsv` geschrieben, wobei die anderen Felder jedes Worts erhalten bleiben.
  - **Städte**: Zieh ein Symbol, um es zu verschieben. Seine Ankunftspunkte (wo du beim Verlassen der Stadt erscheinst) wandern mit, in jedem Story-Abschnitt, der das Symbol dort hat. Klick auf ein Symbol oder eine blaue Trittstelle, um zu ändern, wohin es führt.
  - Der verschneite Norden wird mit einem eigenen Grafiksatz gezeichnet. Die Karte im Pausenmenü ist ein eigenes Bild und folgt Änderungen nicht.
- **Mod exportieren …:** speichert deine Mod als kleinen `.bps`-Patch plus eine Readme für Spieler in `~/Documents/GSMapEditor/Exports/`.
  - Der Patch führt vom unveränderten Spiel zu deinem Build. Das unveränderte Spiel wird einmal aus dem Commit gebaut, von dem deine Mod ausgeht: in einem separaten Ordner über `git archive`, sodass dein Checkout unberührt bleibt. Es wird gegen alchemys `rom.sha1` geprüft, ist also gleich dem Original-Modul, und der Patch lässt sich auf den eigenen Dump jedes Spielers anwenden.
  - Patches sind BPS (Rom Patcher JS, Floating IPS, Soft-Patching im Emulator). Verschobene Daten werden zu Kopien statt zu neuen Bytes. Jeder Patch wird nach dem Schreiben einmal angewendet, um zu prüfen, dass er deinen Build genau reproduziert.
  - Der Export führt zuerst die Prüfung aus. Du teilst deine Änderungen, nie das Spiel.
- **Patcher …:** wendet den `.bps`-, `.ips`- oder `.ups`-Patch einer Mod an und speichert das Spiel in `~/Documents/GSMapEditor/Patched/`, mit **In mGBA spielen** und **Im Finder zeigen**.
  - Patche entweder das unveränderte Spiel, das dieser Mac aus dem Quellcode gebaut hat (kein ROM nötig), oder deine eigene ROM-Datei. Deine Datei wird nach alchemys `rom.sha1` benannt („Golden Sun (English)“), mit einer Warnung, wenn sie kein unverändertes Spiel ist.
  - BPS und UPS verweigern das falsche Spiel. IPS kann das nicht prüfen, und der Patcher sagt das.
  - Der Export kann für ältere Patcher auch eine `.ips` schreiben. Sie ist größer, weil IPS verschobene Daten nicht festhalten kann (4.2 MB gegenüber 383 KB bei der Debug-Raum-Mod), und wird genauso geprüft.
- **▶ Spielen:** ein Knopf: speichert Ungespeichertes, führt die Prüfung aus, baut und öffnet dein Spiel in mGBA, mit einem neuen Spielstand an dem Ort, den du gerade bearbeitest (von der Weltkarten-Seite aus auf der Weltkarte). Der Start wird in eine Wegwerfkopie des Spiels geschrieben; was du exportierst, enthält keine Spur davon. Wenn der Build fehlschlägt, bekommst du eine verständliche Erklärung, mit eingeklappten technischen Details und einem Kopieren-Knopf für Fehlerberichte. Bauen allein liegt unter Erweitert.
- **Rückgängig / Wiederholen:** ein Knopfpaar für alles. Rückgängig nimmt zuerst ungespeichertes Malen zurück (der eigene Stapel der Seite), dann gespeicherte Aktionen, die neuesten zuerst, egal welches Werkzeug und welcher Ort sie gemacht haben; ein Speichern macht den Stapel der Seite zu einer gespeicherten Aktion. Jeder Schreibvorgang geht durch `writing(label, where)` in `server.py`, eine Transaktion aus `gsmap/fsio.py`, die die alten Inhalte der Dateien als Verlaufseintrag behält, beschriftet mit was und wo („eine Person hinzufügen“, Karte `051`). `undo_last` stellt einen Eintrag wieder her und behält, was er ersetzt hat, unter `history/redo`; `redo_last` macht das Umgekehrte; eine neue Aktion leert `history/redo`. Beide gehen durch das Journal, sodass ein Absturz mittendrin beim nächsten Start zu Ende geführt wird. Die letzten 30 von jedem werden behalten, unter `history/` im Support-Ordner.
- **Wo Personen stehen können** (`gsmap/walk.py`): die Laufregeln des Spiels, aus alchemys Feldcode: 8-Pixel-Schritte, bei denen fünf Proben frei sein müssen, höchstens 8 Pixel hoch und 12 hinunter (`terrain.c`, `MapGrid_CheckCollision`), Höhen aus der Form jedes Felds über die sechzehn Geländefunktionen und `terrain_tables.c`, Absätze, Kletterstellen und Lücken, und Ansprechen innerhalb von 32 Pixeln und 48 nach oben oder unten. Rutschpartien werden so verfolgt, wie `Imil_RunIceSlide` es tut, für jeden Tritt-Auslöser, dessen Skript rutscht. Die Gruppe wird auf einem 8-Pixel-Raster von jedem Ankunftspunkt der Szene aus verfolgt; eine Person blockiert innerhalb von 12 Pixeln (zwei Radien von 8, abzüglich je 2). `POST /api/map/<n>/walk` färbt jedes Feld; `/walk/check` liefert die Probleme an einer Stelle, die nächste Stelle ohne Probleme und die Formänderungen, die einen Weg dorthin ebnen (flache Formen, die die Karte schon hat). Ungespeicherte Form- und Begehbarkeitsänderungen werden mitgeschickt. Psynergie und Story-Ereignisse werden nicht verfolgt, und andere Personen als die geprüfte sind keine Hindernisse. Gegen das Spiel geprüft: Etwa 92 % der Personen, die Camelot platziert hat, sind nach diesen Regeln ansprechbar; der Rest sind Zwischensequenz-Räume und Orte, die Psynergie öffnet.
- **Ort zurücksetzen …:** stellt einen Ort so wieder her, wie das Originalspiel ihn hat (Rückgängig bringt deine Fassung zurück). Szenentabellen, die andere Orte teilen, bleiben unverändert, und das wird gesagt.
- **Speichern ist alles oder nichts:** Die Dateien einer Aktion landen zusammen oder gar nicht, jede Datei wird in einem Schritt ersetzt, und wenn der Editor mittendrin abstürzt, schließt er das Rückgängigmachen beim nächsten Start ab.
- **Namen:** Orte werden mit ihren Namen im Spiel aufgeführt („Vale · Vale Home“).
- **Begehbarkeits-Pinsel:** benannt und farbcodiert (Fußboden, Wand, Kante, Kletterwand / Leiter, Sprunglücke, Schadensboden, Suchstellen, …).
- **Hover:** sagt, was ein Feld tut („Ausgang → Vale“, „Truhe: Herb“, „Scripted (probably a door to …)“).
- **NPCs:** als ihre Sprites gezeichnet, nach Namen aufgeführt.
- **Szenentabellen:** freundliche Namen („Ankunftspunkte: Standard“, „Personen: After Kalay“).
- **Kontrollkästchen „Erweitert“:** bringt die rohen Codes zurück.
- **Links:** `?map=003&tool=points&kind=placements` öffnet direkt einen Ort.
- **Keine mitgelieferten Grafiken oder Texte:** Namen von Gegenständen, Orten, Figuren, Sprites und Flags, Gegenstandssymbole und Sprite-Vorschauen werden alle zur Laufzeit aus dem eigenen alchemy-Checkout des Spielers gelesen. `gsmap/data` enthält nur die eigenen Erkenntnisse des Editors: Vorschaubilder, freie Truhen-Flags und was jeder Begehbarkeitscode tut.

**Wie Szenenänderungen ins Spiel kommen:** über einen einzigen Hook, ohne alchemys Szenendateien umzuschreiben. Siehe `docs/SPEC.md` und alchemys `games/tbs/src/mod/README.md`.
- Der Editor speichert bearbeitete Kopien von Tabellen in alchemys `games/tbs/src/mod/overrides.json` und erzeugt daraus `mod.c`.
- `MOD_SCENE_LOADED` in `Scene_LoadOverlay` (`system/main_routine.c`), das der Editor einem unveränderten Checkout hinzufügt, wenn er zum ersten Mal eine Szenenänderung schreibt, setzt einen Wrapper ein, der weiterhin die eigene Tabellenauswahl-Logik jeder Szene ausführt.
- Ohne Overrides ist GSMOD aus, und alle sechs Editionen bauen weiterhin byte-identisch.

Die nächsten Stufen stehen im Bauplan in [`SPEC.md`](SPEC.md).

### Mit alchemy Schritt halten

Alles, was der Editor über den Aufbau von alchemy weiß, steht in `gsmap/layout.py`. Der Commit, mit dem er getestet ist, ist `ALCHEMY_PIN` in `gsmap/setup.py`. Wenn du ihn änderst, aktualisiere auch die Versionszeile in der README, sonst schlägt der Sicherheitstest fehl. Um eine neue Version auszuprobieren:

1. `python3 -m gsmap.preflight path/to/alchemy` sagt in einfachen Worten, was nicht mehr passt. Das läuft auch bei jedem Start und hält dort an, statt Karten mit den falschen Kacheln zu zeichnen.
2. Bau sie, dann zeigen `python3 tools/snapshot.py path/to/alchemy new.json` und `python3 tools/snapshot.py --compare old.json new.json` jeden Unterschied in dem, was der Editor liest. Die beiden Versionen bauen dasselbe Spiel, also sollten sich Ergebnisse nur dort ändern, wo du es erwartest.
3. Führ die Tests unten aus.

Einen vorhandenen Checkout von Hand auf ein neues alchemy zu bringen ist gewöhnliches git: den neuen Commit mergen oder auschecken, dann `git submodule update --init --recursive alchemy-gcc`. Seit `alchemy-gcc` 3a12774 (alchemy 2026-11-08) ist agbcc normale Dateien statt eines verschachtelten Submoduls, und in einem Checkout von davor bricht das Update mit „untracked working tree files would be overwritten“ ab. Führ innerhalb von `alchemy-gcc` `git submodule deinit -f agbcc` aus, lösch den Ordner `agbcc` und `.git/modules/agbcc` unter dem git-Ordner von alchemy-gcc, dann aktualisiere erneut. Lösch `out/*/deps.mk` und `out/*/objects.mk` vor dem ersten Build. Am 2026-11-10 wurden die neuesten Commits von alchemy-gcc umformuliert und neu festgelegt, sodass ein `git fetch` in einem älteren Checkout mit „Errors during submodule fetch: alchemy-gcc“ („not our ref 8b1b6b4…“) enden kann; der Haupt-Fetch hat trotzdem funktioniert, und `git submodule update` checkt dann den neuen festgelegten Commit aus. **Herunterladen** in der Einrichtung macht immer einen frischen Klon, sodass Spieler das nicht erleben.

Gespeicherte Szenenänderungen tragen einen Fingerabdruck der Tabelle, für die sie gemacht wurden. Einer Tabelle, die upstream umbenannt wurde, folgen sie. Eine Änderung an einer Tabelle, deren ursprünglicher Inhalt sich geändert hat, wird behalten, aber aus dem Spiel herausgelassen, und die Prüfung meldet sie.

### Tests

- `python3 tests/safety.py`: was nie schiefgehen darf: Fehler und Abstürze hinterlassen keine halb gespeicherten Dateien, Rückgängig und Wiederholen gehen gespeicherte Aktionen der Reihe nach durch und eine neue Änderung leert Wiederholen, Truhen bleiben in ihren eigenen Räumen, schlechte Werte und feindselige Patches werden abgelehnt, umbenannte oder geänderte Tabellen werden behandelt, ein unbekannter Aufbau wird gemeldet statt erraten.
- `python3 tests/placement.py`: die Laufregeln gegen das Spiel: Die in acht Städten platzierten Personen sind ansprechbar und ihre Auswege erreichbar, und in Imil wird jeweils vor dem Eis, einer unerreichbaren verschneiten Stelle (mit ihrer Einebnungs-Lösung), einer schmalen Gasse, einer Türschwelle und einer Wand gewarnt.
- `python3 tests/edits.py`: speichert Block-, Begehbarkeits- und Höhenänderungen auf einer Kopie echter Karten und prüft, dass sie sich zurücklesen lassen, ohne dass sich sonst etwas geändert hat.
- `python3 tests/i18n.py`: Jede Meldung, die der Code zeigt, ist in jeder Sprache übersetzt, und jede Übersetzung behält ihre `{placeholders}`, HTML-Tags und Tasten (⌘ ⇧ ⌥ ▶).
- `python3 tests/roundtrip.py`: lädt und speichert jedes Kartenraster, jede Feldbild- und Formtabelle und jede Truhenliste neu (727 Dateien mit der Debug-Raum-Mod, 721 bei einem unveränderten Checkout). Alle müssen byte-identisch herauskommen. Das garantiert, dass das Speichern einer Karte nur ändert, was du bearbeitet hast.

### Sprachen

Die eigenen Wörter des Editors sind übersetzt; das Spiel bleibt englisch. Schreib jede Meldung auf Englisch, so eingepackt, dass sie gefunden werden kann: `tr("…")` in Python (`gsmap/i18n.py`), `T('…')` in den Seiten (`static/i18n.js`). Das erste Argument ist immer eine einzelne einfache Zeichenkette; veränderliche Teile sind `{name}`-Platzhalter (`tr("Map {n} has {k} chests", n=n, k=k)`), und Pluralformen sind zwei ganze Vorlagen. Text in den HTML-Seiten und ganze Texte oder Titel, die Skripte in die Seite setzen, werden so übersetzt, wie sie erscheinen, wenn sie genau einer Meldung entsprechen; alles innerhalb eines `data-notr`-Elements (die Namen und Dialoge des Spiels) bleibt unverändert. Übersetze nicht, was in Dateien geschrieben wird (mod.c, en.po, die exportierte Readme) oder vom Code verglichen wird.

`python3 tools/extract_strings.py` sammelt jede Meldung in `static/i18n/<lang>.json` (Englisch → Übersetzung), fügt neue leer hinzu und entfernt solche, die der Code nicht mehr hat; `--check` schlägt fehl, wenn welche nicht im Gleichschritt oder unübersetzt sind. Die im 🌐-Menü gewählte Sprache wird in den Einstellungen des Editors gespeichert (`language`); bis eine gewählt ist, entscheiden die bevorzugten Sprachen des Browsers. Die Meldungen jeder Anfrage verwenden sie (`i18n.begin` in beiden Servern), und die Seiten bekommen ihren Katalog von `/i18n-strings.js`. Um eine Sprache hinzuzufügen, füg sie zu `LANGS` in `gsmap/i18n.py` hinzu, führ den Extraktor aus und füll die neue Datei aus.

Auch die README und diese Dokumentation sind übersetzt: `README.<lang>.md` neben der README und `docs/<lang>/` für `DEVELOPING.md`, `PRODUCT.md`, `SPEC.md` und `research/`. `docs/upstream-issues.md` (für alchemys englischen Issue-Tracker), `docs/releases/` und `THIRD_PARTY_NOTICES.md` bleiben englisch. Die englischen Dateien sind die Originale: Ändere zuerst sie, dann die Übersetzungen, und führe `python3 tools/doc_translations.py --stamp` aus, um festzuhalten, welchem englischen Text jede Übersetzung nun folgt. Ohne `--stamp` prüft es Links, Überschriften, Webadressen und `code`-Abschnitte jeder Übersetzung und listet die auf, deren Englisch sich seitdem geändert hat. Die Namen und Beschreibungen der Begehbarkeits-Pinsel in `gsmap/data/collision.json` sammelt der Extraktor ebenfalls.

## Dokumentation

- [`SPEC.md`](SPEC.md): die Editor-Spezifikation, Invarianten und der stufenweise Bauplan.
- [`research/`](research/): Belege mit file:line-Verweisen.
  - `rendering.md`: Platzhalter, Tilesets, Fenster, Überblendung, Animation.
  - `local-connections.md`: Szenen, Ausgänge, Markierungen, NPCs, neue Karten.
  - `overworld.md`: die Weltkarte.
