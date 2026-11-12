<!-- translated from README.md @ b21e30165e76 -->
# GS Map Editor

[English](README.md) · [Español](README.es.md) · **Deutsch** · [Français](README.fr.md) · [Italiano](README.it.md) · [日本語](README.ja.md)

*Dies ist eine Übersetzung der englischen [README.md](README.md). Wenn die beiden voneinander abweichen, gilt die englische Fassung.*

Mach deine eigene Version von **Golden Sun: The Broken Seal**, ohne Code zu schreiben. Male Städte neu, versteck Truhen, schreib neue Dialoge, füge Personen und Türen hinzu, gestalte die Weltkarte um, drück dann auf **▶ Spielen** und lauf in deiner Änderung herum. Wenn du zufrieden bist, exportierst du einen kleinen Patch zum Weitergeben.

Der Editor arbeitet mit [alchemy](https://github.com/PascalPixel/alchemy), einem Projekt, das das Spiel aus lesbaren Quelldateien neu aufbaut. Er baut dein Spiel aus diesem Quellcode auf deinem eigenen Computer, du brauchst also keine ROM, um eine Mod zu machen.

> **Vorschau: Tester gesucht.** Der Editor deckt die englische Ausgabe von The Broken Seal ab, auf macOS und, als früher Test, auf Windows. Er wurde bisher hauptsächlich auf einem einzigen Intel-Mac getestet, und die Windows-Version lief noch nie auf einem echten Windows-PC, deshalb hilft jede Rückmeldung, auch „hat funktioniert“: [lade ihn herunter](https://github.com/TRosenvall/GS-Map-Editor/releases), probier ihn aus und [erzähl uns, wie es lief](https://github.com/TRosenvall/GS-Map-Editor/issues/new?template=bug_report.md). Mach eine Sicherungskopie von jeder Mod, die dir wichtig ist.

**Alchemy-Version:** Dieser Editor ist mit dem alchemy-Commit [`0c937e7df0`](https://github.com/PascalPixel/alchemy/commit/0c937e7df0b71b23760fbd19d048e99dd3969490) (2026-11-11) getestet. Die Einrichtung lädt genau diesen Commit herunter. Alchemy ändert sich schnell, daher funktioniert eine neuere Kopie vielleicht erst, wenn der Editor nachgezogen hat.

## Inhalt

- [Erste Schritte](#erste-schritte)
- [Deine erste Mod in zwei Minuten](#deine-erste-mod-in-zwei-minuten)
- [Der Editor auf einen Blick](#der-editor-auf-einen-blick)
- [Speichern und Rückgängigmachen](#speichern-und-rückgängigmachen)
- [Umsehen](#umsehen)
- [Malen: wie der Boden aussieht](#malen-wie-der-boden-aussieht)
- [Begehbarkeit: wo man laufen kann](#begehbarkeit-wo-man-laufen-kann)
- [Höhe: wie hoch der Boden ist](#höhe-wie-hoch-der-boden-ist)
- [Truhen](#truhen)
- [Ereignisse: Personen, Schilder und Nachrichten](#ereignisse-personen-schilder-und-nachrichten)
- [Türen](#türen)
- [Personen verschieben](#personen-verschieben)
- [Stempel: kopieren und einfügen](#stempel-kopieren-und-einfügen)
- [Eigene Bilder importieren](#eigene-bilder-importieren)
- [Tabellen für Story und Szene](#tabellen-für-story-und-szene)
- [Verbindungen](#verbindungen)
- [Die Weltkarte](#die-weltkarte)
- [Prüfen: Probleme finden](#prüfen-probleme-finden)
- [Dein Spiel spielen](#dein-spiel-spielen)
- [Deine Mod teilen](#deine-mod-teilen)
- [Mods von anderen spielen](#mods-von-anderen-spielen)
- [Wo deine Arbeit liegt](#wo-deine-arbeit-liegt)
- [Tastenkürzel](#tastenkürzel)
- [Was er noch nicht kann](#was-er-noch-nicht-kann)
- [Fehlerbehebung](#fehlerbehebung)
- [Probleme melden](#probleme-melden)
- [Rechtliches](#rechtliches)

## Erste Schritte

### Was du brauchst

- Einen Mac mit macOS 11 oder neuer oder einen PC mit Windows 10 oder 11.
- Etwa 3 GB freien Speicherplatz für den Quellcode des Spiels und seinen Build.
- [mGBA](https://mgba.io/downloads.html), einen kostenlosen Game-Boy-Advance-Emulator, um dein Spiel zu spielen (unter Windows dessen Windows-Installationsprogramm).
- Eine Internetverbindung für die erste Einrichtung.

### Die App holen (Mac)

Lade die neueste `.dmg` von [Releases](https://github.com/TRosenvall/GS-Map-Editor/releases) herunter:

- **AppleSilicon** für Macs mit einem M1-, M2-, M3-, M4- oder neueren Chip;
- **Mac-Intel** für Intel-Macs.

Du weißt nicht, welchen du hast? Apple-Menü → **Über diesen Mac**: „Chip: Apple M…“ bedeutet Apple Silicon.

Öffne die `.dmg` und zieh **GS Map Editor** in **Programme**.

### Beim ersten Mal öffnen (Mac)

Die App ist noch nicht mit einem Apple-Entwicklerzertifikat signiert, deshalb warnt macOS beim ersten Mal davor:

1. Öffne sie aus dem Ordner „Programme“. macOS sagt, dass es die App nicht überprüfen kann: Drück auf **Fertig** (oder **Abbrechen**).
2. Öffne **Systemeinstellungen → Datenschutz & Sicherheit**, scroll nach unten und drück neben GS Map Editor auf **Dennoch öffnen**. Bestätige mit deinem Passwort.

Unter macOS 14 und früher kannst du stattdessen mit der rechten Maustaste auf die App klicken, **Öffnen** wählen und dann noch einmal **Öffnen**. Nach dem ersten Mal öffnet sie sich normal.

Wenn du die App lieber selbst baust, folge [Desktop-App](docs/de/DEVELOPING.md#desktop-app-macos) in den Entwicklerhinweisen. Wenn du dich mit einem Terminal auskennst und schon eine gebaute alchemy-Kopie hast, kannst du die App überspringen und `python3 server.py --root /path/to/alchemy` ausführen und dann diese Adresse öffnen: http://127.0.0.1:8765/.

### Den Editor holen (Windows, früher Test)

Der Editor läuft in WSL, dem in Windows eingebauten Linux, weil sich der Quellcode des Spiels unter Windows nur so bauen lässt. Er öffnet sich in deinem Webbrowser.

1. Lade `Install-GS-Map-Editor.cmd` von [Releases](https://github.com/TRosenvall/GS-Map-Editor/releases) herunter. Wenn dein Browser meldet, dass die Datei nicht häufig heruntergeladen wird, wähl **Behalten**.
2. Doppelklick darauf. Windows sagt, dass es deinen PC geschützt hat, weil das Installationsprogramm noch nicht signiert ist: Drück auf **Weitere Informationen** und dann auf **Trotzdem ausführen**.
3. Beim ersten Mal schaltet es WSL ein und installiert Ubuntu. Windows fragt nach Administratorrechten und bittet dich vielleicht um einen Neustart; wenn ja, starte neu und doppelklick das Installationsprogramm noch einmal.
4. Wenn Ubuntu danach fragt, wähl einen Benutzernamen und ein Passwort. Beim Eintippen des Passworts wird nichts angezeigt; das ist normal. Der nächste Schritt fragt danach.
5. Das Installationsprogramm richtet den Editor in Ubuntu ein und fügt **GS Map Editor** zu deinem Startmenü und Desktop hinzu.

Öffne **GS Map Editor**. Ein kleines Fenster erscheint; lass es offen, solange du den Editor benutzt, denn wenn du es schließt, wird der Editor beendet. Der Editor öffnet sich in deinem Browser. Wenn du das Installationsprogramm erneut ausführst, wird der Editor auf die Version aktualisiert, die es mitgebracht hat.

Unter Windows verwenden Tastenkürzel Strg, wo diese Anleitung ⌘ sagt, und Alt, wo sie ⌥ sagt. Deine Arbeit liegt in Ubuntu, in `GSMapEditor` in deinem Ubuntu-Benutzerordner; der Datei-Explorer zeigt sie unter **Linux → Ubuntu → home**.

### Einrichtung beim ersten Start

Der Editor öffnet sich beim ersten Mal mit einer Checkliste. Das dauert etwa 15 Minuten, meistens Warten. Drück bei jedem Schritt auf den Knopf, und der Editor erledigt den Rest:

1. **Apples Entwicklerwerkzeuge** (nur Mac): öffnet Apples Installationsprogramm.
2. **Die Werkzeuge zum Bauen des Spiels:** auf dem Mac schon in der App enthalten, unter Windows vom Installationsprogramm bereitgestellt.
3. **Der Quellcode des Spiels:** lädt alchemy nach `~/Documents/GSMapEditor/` herunter (unter Windows nach `GSMapEditor` in deinem Ubuntu-Benutzerordner). Wenn du schon eine Kopie hast, wähl **Ich habe schon eine Kopie …** (unter Windows gib ihren Pfad ein).
4. **Build wird vorbereitet:** richtet einmalig die Compiler des Spiels ein.
5. **Ein erster Build des Spiels:** baut das Spiel einmal.

Drück dann auf **Editor öffnen**. Danach öffnet sich die App direkt im Editor.

## Deine erste Mod in zwei Minuten

1. Wähl links einen Ort aus der Liste. Tipp in das Feld **Ort suchen**, um zu suchen.
2. Drück in der oberen Leiste auf **Truhe** und klick dann auf ein leeres Stück Boden.
3. Gib einen Gegenstandsnamen ein, zum Beispiel `Herb`, und drück auf **Truhe hinzufügen**.
4. Drück auf **▶ Spielen**. Dein Spiel öffnet sich in mGBA, an dem Ort, den du bearbeitet hast, ein paar Sekunden nachdem das Spiel gestartet ist.
5. Geh zur Truhe und öffne sie.

## Der Editor auf einen Blick

| Bereich | Was dort ist |
|---|---|
| **Links** | Die Liste der Orte. Die Weltkarte steht ganz oben. |
| **Obere Leiste** | Zoom, Ebenen, Overlays, Werkzeuge und Knöpfe zum Speichern, Prüfen und Spielen. |
| **Mitte** | Die Karte. |
| **Rechts** | Der Bereich für das Werkzeug, das du gerade benutzt. |
| **Untere Zeile** | Statusmeldungen. Wenn du mit der Maus darüberfährst, sagt sie, was die Stelle unter deinem Mauszeiger tut, etwa „Truhe: Herb“ oder wohin ein Ausgang führt. |

Setz in der oberen Leiste das Häkchen bei **Erweitert**, um rohe Zahlen und Codes und einen eigenen Knopf **Bauen** anzuzeigen. Fürs normale Bearbeiten brauchst du das nicht.

### Sprachen

Der Editor spricht Englisch, Spanisch (Español), Deutsch, Französisch (Français), Italienisch (Italiano) und Japanisch (日本語). Er startet in der Sprache deines Computers, wenn er sie kennt. Du änderst sie im Menü 🌐, oben rechts auf dem ersten Einrichtungsbildschirm und am Ende der oberen Leiste. Nur die eigenen Wörter des Editors ändern sich: Das Spiel, das du moddest, ist die englische Ausgabe, deshalb bleiben Ortsnamen, Personen, Gegenstände und die Dialoge, die du schreibst, auf Englisch.

Auch diese Anleitung ist übersetzt: Die Links findest du oben. Die Übersetzungen des Editors und dieser Anleitung wurden mit KI-Hilfe erstellt und noch nicht alle von Muttersprachlern geprüft. Wo eine übersetzte Anleitung von dieser abweicht, gilt diese englische Anleitung. Wenn dir etwas seltsam vorkommt, [sag es uns bitte](https://github.com/TRosenvall/GS-Map-Editor/issues/new?template=bug_report.md), zusammen mit der Formulierung, die du erwarten würdest.

## Speichern und Rückgängigmachen

Manche Änderungen warten darauf, dass du speicherst, andere werden sofort gespeichert:

| Wartet auf **Speichern** (oder ⌘S) | Wird sofort gespeichert |
|---|---|
| Malen, Begehbarkeit, Höhe | Eine Truhe hinzufügen, ändern oder entfernen |
| Mit dem Stempel Eingefügtes | Ereignisse und Türen |
| Truhen, Steine und Personen ziehen | Malen auf der Weltkarte und Verschieben von Städten |

Der Editor speichert auch für dich, bevor du den Ort wechselst, zur Weltkarte gehst oder auf Spielen drückst, so verlierst du beim Weitermachen nichts. Wenn ein Speichern abgelehnt wird, bleibst du, wo du bist, und die untere Zeile sagt dir, warum.

Es gibt drei Wege zurück:

- **Rückgängig** (⌘Z) nimmt deine letzte Änderung zurück, egal welche: zuerst noch nicht gespeichertes Malen, dann gespeicherte Aktionen, die neueste zuerst, aus jedem Werkzeug und an jedem Ort. Eine Person, eine Truhe, eine Tür, ein Ereignis, ein Pinselstrich auf der Weltkarte hinzugefügt: alles. Der Tooltip des Knopfs sagt, was er rückgängig machen wird und wo, und der Editor öffnet diesen Ort, um es dir zu zeigen. Die letzten 30 gespeicherten Aktionen bleiben erhalten, auch nachdem du den Editor geschlossen hast.
- **Wiederholen** (⇧⌘Z) stellt wieder her, was Rückgängig zurückgenommen hat, bis du eine neue Änderung machst.
- **Ort zurücksetzen …** setzt die Karten eines Orts, seine importierten Bilder und seine eigenen Personen, Türen und Ereignisse auf den Stand des Originalspiels zurück. Wenn du es dir anders überlegst, holt **Rückgängig** deine Version zurück. Wenn ein Ort seine Karte mit anderen teilt, werden diese auch zurückgesetzt, und der Editor warnt dich vorher. Personen und Ereignisse, die andere Orte mitbenutzen, bleiben unberührt, außer du sagst etwas anderes: Der Editor fragt nach.
- **Weltkarte zurücksetzen …** auf der Weltkartenseite macht dasselbe für die Weltkarte.

Text, den du geschrieben hast, bleibt in der Textdatei des Spiels, solange irgendein Ereignis noch einen Teil davon benutzt. Er wird erst entfernt, wenn keine deiner Zeilen mehr benutzt wird. Wenn du eine gespeicherte Aktion rückgängig machst, während du ungespeicherte Änderungen hast, werden diese ebenfalls verworfen, und der Editor fragt vorher.

Jedes Speichern geschieht ganz oder gar nicht. Wenn der Editor mittendrin stoppt, macht er das halb fertige Speichern beim nächsten Start vollständig rückgängig. Wenn sich eine Datei nicht schreiben lässt, zum Beispiel weil sie im Finder gesperrt ist, wird das Speichern abgelehnt und der Rest davon rückgängig gemacht.

## Umsehen

Drück auf **Ansicht** (V), um dich umzusehen, ohne etwas zu ändern.

- **Zoom:** 1× bis 4×.
- **Ebenen:** Jeder Ort hat bis zu drei, genannt **Boden**, **Mitte** und **Oben**. Du kannst jede einzeln ausblenden. Setz das Häkchen bei **Erweitert** für Schieberegler, mit denen du sie ausblendest.
- **Overlays:** Setz das Häkchen bei **Begehbarkeit**, bei **Höhe**, um die Bodenhöhe zu sehen, oder bei **Raster**, um die Felder zu sehen.
- **Truhen** sind immer auf der Karte zu sehen. Türen, Personen und Ereignisse erscheinen, wenn du ihre Werkzeuge benutzt.

## Malen: wie der Boden aussieht

Drück auf **Malen** (B).

1. Wähl im Menü **auf** in der oberen Leiste eine Ebene.
2. Wähl rechts im Bereich **Blöcke** einen Block, oder halte ⌥ gedrückt und klick auf die Karte, um den Block unter dem Mauszeiger aufzunehmen.
3. Klick oder zieh auf der Karte.
4. Speichere.

Jeder Ort hat seinen eigenen Satz Blöcke, deshalb ändert sich der Bereich von Ort zu Ort.

## Begehbarkeit: wo man laufen kann

Drück auf **Begehbarkeit** (C). Einen Block zu malen ändert nicht, wo man laufen kann, deshalb ist das ein eigener Schritt. Wähl einen Pinsel und male.

| Pinsel | Was er tut |
|---|---|
| **Fußboden** | Normaler Boden, auf dem man laufen kann. |
| **Wand** | Versperrt den Weg, egal wie hoch. |
| **Kante (hinunterspringen)** | Drück eine Weile nach unten dagegen, und der Anführer springt hinunter. |
| **Kletterwand / Leiter** | Drück eine Weile nach oben oder unten dagegen, um zu klettern. |
| **Sprunglücke (Sprung nach vorn)** | Drück eine Weile dagegen, und der Anführer springt hinüber, wenn man auf der anderen Seite landen kann. |
| **Kampfboden A / B** | Begehbar. Zufallskämpfe nutzen die erste oder zweite Kampfzone des Orts. |
| **Schadensboden** | Begehbar, schadet der Gruppe aber nach genügend Schritten, wenn die Szene das einschaltet. |
| **Cloak-Schatten** | Begehbar. Der einzige Boden, auf dem die Psynergie Cloak die Gruppe versteckt hält. |
| **Leerer Krug, Fass, Kiste, Grab, Bücher, Brunnen** | Beim Untersuchen findet man nichts. Durch seine Höhe meist auch eine Wand. |

Die Werkzeuge Truhe, Türen und Ereignisse setzen die besonderen Codes, die sie brauchen, selbst, du musst sie also nicht malen.

## Höhe: wie hoch der Boden ist

Drück auf **Höhe** (H). Der Bereich listet die Höhen auf, die dieser Ort schon nutzt, etwa „Flach, 24 px“ oder „Hang oder Stufe“. Wähl eine aus und male.

Die Höhe beeinflusst nicht nur das Aussehen, sondern auch das Laufen. Personen stehen auf der Höhe des Bodens unter ihnen, und das Spiel lässt keinen Schritt von mehr als 8 Pixeln nach oben oder 12 Pixeln nach unten zu, deshalb wirkt ein großer Höhenunterschied wie eine Wand.

## Truhen

Drück auf **Truhe** (K).

- **Eine hinzufügen:** Klick auf eine leere Stelle, wähl einen **Gegenstand** (fang an, seinen Namen zu tippen) oder eine Menge **Münzen** und drück dann auf **Truhe hinzufügen**.
- **Eine ändern:** Klick darauf, ändere den Inhalt und bestätige.
- **Eine entfernen:** Klick darauf und drück auf **Truhe entfernen**.
- **Eine verschieben:** Zieh sie und speichere dann. Auch Psynergie-Steine lassen sich ziehen. Eine Truhe kann nicht auf ein Feld, das schon eine Tür, ein Schild oder eine Tritt-Nachricht ist.

Den Rest erledigt der Editor, auch das Flag, das sich merkt, dass eine Truhe geöffnet wurde, sodass eine Truhe leer bleibt, wenn du zurückkommst. Ein Ort kann höchstens **10 Truhen und Steine** haben.

## Ereignisse: Personen, Schilder und Nachrichten

Drück auf **Ereignisse** (E). Der Bereich listet in Worten alles auf, was an diesem Ort passiert: was Personen sagen, Gedanken für Mind Read, Schilder, Tritt-Nachrichten, Dinge zum Untersuchen und Ausgangsbereiche.

Der **Story-Abschnitt** oben ist wichtig. Viele Orte verändern sich im Lauf der Story, und jeder Abschnitt hat seine eigenen Personen und Ereignisse. Wähl den Abschnitt, den du bearbeiten willst.

### Dinge hinzufügen

Klick auf eine Stelle auf der Karte und wähl dann:

- **Schild hinzufügen (mit A lesen) …** für ein Schild oder etwas zum Untersuchen.
- **Tritt-Nachricht hinzufügen …** für eine Nachricht, die erscheint, wenn du auf die Stelle trittst. Sie wiederholt sich nicht, solange du dort stehst, kann den Spieler also nicht festhalten, und sie erscheint wieder, wenn du heruntergehst und zurückkommst.
- **Hier eine Person hinzufügen …**, um mit einer Bildvorschau auszuwählen, wer es ist und ob die Person herumläuft (**Läuft herum**). Der Editor prüft die Stelle vorher (siehe unten).

### Wo Personen stehen können

Nicht jede Stelle, die frei aussieht, ist ein guter Platz für eine Person. Setz oben das Häkchen bei **Wo Personen stehen können** oder drück einfach auf **Hier eine Person hinzufügen …**, und die Karte wird danach eingefärbt, was eine Person an dieser Stelle bedeuten würde:

| Farbe | Bedeutet |
|---|---|
| Grün | Die Gruppe kann hingehen und mit der Person reden. |
| Gelb | Die Gruppe kann dieses Feld nicht betreten, aber von daneben mit der Person reden, wie mit einem Verkäufer hinter einer Theke. |
| Blau | Eis, über das die Gruppe rutscht, wie in Imil. Wer dort steht, ist beim Rutschen im Weg. |
| Orange | Eine Tür, ein Ausgang oder eine Trittstelle: Eine Person dort wäre im Weg. |
| Rot | Die Gruppe kommt zu Fuß nicht nah genug heran, um zu reden. |

Das wird aus den Laufregeln des Spiels selbst ermittelt, ausgehend von jedem Punkt, an dem die Gruppe an diesem Ort ankommt: Man kann 8 Pixel hinauf- und 12 hinuntersteigen, Wände halten einen auf, und man kann mit jemandem reden, der höchstens zwei Felder entfernt ist. Stellen, die erst durch Psynergie oder die Story zugänglich werden, erscheinen rot, Rot bedeutet dort also nicht immer einen Fehler.

Wenn eine Stelle ein Problem hat, sagt der Editor in einfachen Worten, welches, zum Beispiel „der Boden hier ist 32 Pixel höher als der nächste Weg“, oder dass eine Person dort die Gruppe von einer Tür abschneiden würde. Dann bietet er einen Ausweg an:

- **Zur nächsten guten Stelle verschieben** verschiebt die Person auf das nächstgelegene Feld ohne Probleme.
- **… Felder auf die Höhe des Wegs angleichen** ändert die Bodenhöhe vom nächsten Weg bis zur Stelle, sodass die Gruppe dorthin laufen kann. Das Bild ändert sich nicht, nutze also **Malen**, wenn es wie ein Weg aussehen soll. Es ist ganz normales ungespeichertes Malen: Speichern behält es, und Rückgängig nimmt es zurück.
- **Trotzdem hier hinzufügen …**, wenn du es besser weißt, zum Beispiel wenn ein Story-Ereignis den Weg öffnet.

Wenn du eine Person mit **Personen verschieben** ziehst, wird sie beim Loslassen genauso geprüft.

### Personen sprechen lassen

Klick auf eine Person. Drück auf **Lass sie etwas sagen …** oder, wenn sie schon spricht, auf **Zeile für einen Story-Moment hinzufügen …**.

### Ändern, was da ist

Jedes Ereignis in der Liste hat diese Knöpfe, wo sie passen:

- **Text ändern** öffnet den Texteditor.
- **Wann …** legt fest, wann das Ereignis passiert: **Immer**, **Erst sobald** ein Story-Flag gesetzt ist, oder **Nur solange** es nicht gesetzt ist. Flags werden mit Namen aufgelistet.
- **Entfernen** löscht es.

### Der Texteditor

Tipp ganz normal. Eine Leerzeile beginnt ein neues Textfenster, und die Vorschau zeigt, wie die Textfenster im Spiel aussehen werden. **+ Name des Helden** fügt den Namen ein, den der Spieler gewählt hat. Die Schrift des Spiels hat einfache Buchstaben, Ziffern und Satzzeichen, ohne Akzente (also auch ohne Umlaute). Typografische Anführungszeichen, lange Gedankenstriche und „…“ werden von selbst zu ihren einfachen Formen, und alles andere, was die Schrift nicht darstellen kann, wird beim Speichern abgelehnt.

Deine Worte werden als neue Zeilen hinzugefügt, und der eigene Text des Spiels wird nie überschrieben. Wenn dieselbe Zeile woanders benutzt wird, bleibt sie dort, wie sie war.

### Geteilte Szenen

Manche Orte teilen ihre Personen und Ereignisse mit anderen Orten. Der Bereich warnt dich, wenn eine Änderung hier auch dort auftaucht.

## Türen

Drück auf **Türen** (D). Jede Tür wird auf der Karte mit ihrem Ziel angezeigt. **Blaue** Zellen sind Türen, **rote** führen nirgendwohin.

- **Eine Tür ändern:** Klick darauf, drück auf **Ändern, wohin es führt …**, wähl einen Ort und klick dann auf der Karte dieses Orts dorthin, wo die Gruppe ankommen soll.
- **Eine Tür machen:** Klick auf irgendeine andere Stelle und drück auf **Hier eine Tür machen …**. Sie kann überallhin im Spiel führen.
- **Eine Tür entfernen:** Klick darauf und drück auf **Tür entfernen**. Ihre Zellen werden wieder zu Boden.

Eine Tür ändert sich in jedem Story-Abschnitt des Orts. Auch Türen, die von Szenenskripten geöffnet werden, werden gefunden: Du kannst ändern, wohin sie führen, aber das Skript selbst bleibt gleich.

## Personen verschieben

Drück auf **Personen verschieben** (P).

1. Wähl im Bereich **Story und Szene** eine Szene und eine Tabelle mit Personen oder Ankunftspunkten.
2. Zieh sie auf der Karte. Halte beim Loslassen ⇧ gedrückt, um sie auf die nächsten 8 Pixel einrasten zu lassen.
3. Speichere.

Ankunftspunkte sind die Stellen, an denen die Gruppe erscheint, wenn sie einen Ort betritt.

## Stempel: kopieren und einfügen

Drück auf **Stempel** (S).

1. Zieh ein Rechteck auf der Karte, um es zu kopieren.
2. Klick, um es einzufügen, hier oder an einem anderen Ort, der denselben Blocksatz nutzt.
3. Drück Esc, um wieder zum Kopieren zurückzukehren.

- **Begehbarkeit & Höhe** kopiert diese zusammen mit den Blöcken und ist standardmäßig eingeschaltet.
- **Nur Objekte** fügt nur die Bäume und anderen Objekte ein, nicht den Boden darunter.
- Ein Einfügen ist ein einziger Rückgängig-Schritt, und deine Kopie übersteht Ortswechsel und Neuladen.
- Orte mit einem anderen Blocksatz lehnen das Einfügen ab, weil jeder Block das falsche Bild zeichnen würde.

## Eigene Bilder importieren

**Bild importieren …** findest du im Stempel-Bereich. Es funktioniert an Orten, deren Grafiken mit keinem anderen Ort geteilt werden, das sind 27 der 182 in einer frischen Kopie des Spiels. Anderswo lehnt der Editor ab, weil dein Bild verändern würde, wie andere Orte aussehen.

1. Wähl **Overlay** (über den Boden gezeichnet, mit transparentem Hintergrund) oder **Boden**.
2. Drück auf **Bild importieren …** und wähl ein PNG, GIF oder BMP. Es darf höchstens 256 Felder zu 16×16 Pixeln abdecken, zum Beispiel 256×256 Pixel, wobei einem detailreichen Bild der Platz auch früher ausgehen kann. Der Editor sagt es dir, wenn das passiert.
3. Prüf die Vorschau. Sie zeigt die Farben, die das Spiel wirklich zeichnen wird, und wie viel Platz noch übrig ist.
4. Drück auf **Zum Tileset hinzufügen**. Die neuen Blöcke landen in der Stempel-Zwischenablage, bereit, per Klick platziert zu werden.

Das Bild wird an die Farben dieses Orts angepasst, und wiederholte Teile werden wiederverwendet, um Platz zu sparen. Wenn die Grafikblätter voll sind, verwendet der Editor Grafiken von Blöcken wieder, die der Ort nie nutzt, und diese Blöcke verschwinden dann aus der Palette.

## Tabellen für Story und Szene

Der Bereich **Story und Szene** zeigt die Szenen, die diese Karte nutzen, und die Tabellen dahinter, mit verständlichen Namen wie „Ankunftspunkte: Standard“. Ankunftspunkte und Personen werden auf der Karte angezeigt. Ausgänge werden als Liste bearbeitet, mit einer Prüfung, ob der Ankunftspunkt, den du wählst, existiert. Meistens sind die Werkzeuge Türen, Ereignisse und Personen verschieben einfacher.

## Verbindungen

Drück auf **Verbindungen**, um einen beliebigen Ort in der Mitte zu sehen, mit allen Orten, die zu ihm führen, links und allen, zu denen er führt, rechts. Klick auf einen Ort, um dorthin zu wechseln, oder drück auf **Öffnen**, um im Editor zu dieser Tür zu springen. Nutze das Suchfeld, um einen Ort zu finden.

## Die Weltkarte

Wähl die Weltkarte ganz oben in der Ortsliste. Drück auf **← Orte**, um zurückzugehen.

| Werkzeug | Taste | Was es tut |
|---|---|---|
| **Ansicht** | V | Fahr mit der Maus über eine Stelle, um ihre Region zu sehen und was sie tut. Klick auf eine Stadt, einen Dungeon oder eine blaue Trittstelle, um zu sehen, wohin sie führt. |
| **Boden** | G | Bodenblöcke malen. ⌥-Klick nimmt einen Block auf, und zuletzt benutzte Blöcke bleiben griffbereit. |
| **Overlay** | O | Berge, Bäume und Küsten malen. Ob man laufen kann, hängt von den Kacheln beider Ebenen ab. |
| **Regionen** | R | Kampfregionen malen. Jede hat ihre eigenen Zufallskämpfe und ist nach den Städten in ihr benannt. |
| **Städte** | T | Eine Stadt oder einen Dungeon ziehen, um sie zu verschieben. Auf eine klicken, um zu ändern, wohin sie führt. |

- Setz das Häkchen bei **Begehbarkeit**, **Kampfregionen** oder **Orte**, um diese auf der Karte anzuzeigen.
- Wenn du eine Stadt verschiebst, sorgt **auch die Ankunftspunkte mitnehmen** dafür, dass du beim Verlassen neben ihr erscheinst. Es ist standardmäßig eingeschaltet.
- Änderungen werden beim Malen gespeichert. **Rückgängig** nimmt den letzten Pinselstrich zurück, und **Wiederholen** stellt ihn wieder her.
- Die Karte im Pausenbildschirm ist ein eigenes Bild und folgt deinen Änderungen deshalb nicht.

## Prüfen: Probleme finden

Drück auf **Prüfen**, um alle Karten auf Probleme zu untersuchen, die deine Änderungen verursachen würden. Zu jedem gibt es eine Lösung und einen Knopf **Anzeigen**, der die Stelle öffnet. Es sucht nach:

- Türen, die nirgendwohin führen oder zu einem Ankunftspunkt, den es nicht gibt;
- Truhen, die sich nicht öffnen lassen, für die nichts festgelegt ist, die sich wieder füllen oder die sich ein „Geöffnet“-Flag teilen;
- mehr als 10 Truhen und Steinen an einem Ort;
- Feldern, die einen Block oder eine Höhe nutzen, die der Ort nicht hat;
- Zeilen, die du geschrieben hast und die die Schrift des Spiels nicht darstellen kann;
- Orten, deren Dateien beschädigt sind;
- Änderungen, die nicht mehr passen, nachdem der Quellcode des Spiels aktualisiert wurde.

Das Originalspiel hat seine eigenen Eigenheiten, und die bleiben verborgen, außer du setzt das Häkchen bei **Auch die Eigenheiten des Originalspiels zeigen**. An einem Ort, den du bearbeitet hast, kann eine Eigenheit, die schon das Original hatte, als deine aufgeführt werden. Auf der Seite eines Orts führen Spielen, Exportieren und **Bauen** vorher automatisch Prüfen aus und fragen nach, bevor sie trotz Problemen weitermachen. Auf der Weltkartenseite tun Spielen und Bauen das nicht, drück also an einem Ort auf Prüfen. Wenn Prüfen nicht abschließen kann, sagt es das und fragt, bevor es weitergeht.

## Dein Spiel spielen

Drück auf **▶ Spielen**. Das speichert, prüft, baut und öffnet dein Spiel in mGBA, beginnend an dem Ort, den du bearbeitest. Von der Weltkartenseite aus baut es das Spiel und startet auf der Weltkarte, ohne die Prüfung.

- Jedes Spielen ist ein **neues Spiel**: Isaac allein, ohne Story-Fortschritt, deshalb kann ein Ort wie seine Version vom Anfang des Spiels aussehen.
- Du erscheinst am ersten Ankunftspunkt des Orts, der nicht eingemauert wirkt, nicht an der Stelle, die du gerade ansiehst. Das ist eine bestmögliche Schätzung: Bei ein paar Orten steckst du trotzdem fest oder landest mitten in einer Story-Szene. Wenn das passiert, wähl bei **Starten bei** neben ▶ Spielen einen anderen Ankunftspunkt und drück noch einmal auf Spielen.
- Ein Build nach einer Kartenänderung dauert etwa 20 Sekunden.
- Den Startpunkt gibt es nur in einer Wegwerfkopie des Spiels, deine exportierte Mod startet also ganz normal vom Titelbildschirm.

## Deine Mod teilen

Drück auf **Mod exportieren …**.

1. Füll einen **Namen** aus und, wenn du willst, deinen Namen und was die Mod ändert.
2. Drück auf **Exportieren**.

Du bekommst einen kleinen `.bps`-Patch und eine Anleitung für Spieler in `~/Documents/GSMapEditor/Exports/`. Drück auf **Im Finder zeigen**, um sie zu sehen. Exportieren führt vorher Prüfen aus und testet jeden Patch einmal, um zu bestätigen, dass er deinen Build genau nachbildet.

Setz das Häkchen bei **Zusätzlich eine .ips für ältere Patcher speichern**, wenn deine Spieler ältere Patcher benutzen. Sie ist viel größer, weil IPS verschobene Daten nicht erfassen kann.

**Teile den Patch, nie das gebaute Spiel.** Spieler wenden den Patch auf ihre eigene Kopie an, so gibst du das Spiel selbst nie weiter. Ein `.bps`-Patch funktioniert mit gängigen Patchern wie Rom Patcher JS und Floating IPS, und natürlich mit diesem Editor.

## Mods von anderen spielen

Drück auf **Patcher …**.

1. Drück auf **Patch auswählen …** und wähl eine `.bps`-, `.ips`- oder `.ups`-Datei.
2. Wähl das Spiel, das gepatcht werden soll: **Das unveränderte Spiel, auf diesem Mac aus dem Quellcode gebaut** (keine ROM nötig) oder **Meine eigene ROM-Datei**.
3. Drück auf **Patchen**.

Das gepatchte Spiel wird in `~/Documents/GSMapEditor/Patched/` gespeichert, und du kannst auf **In mGBA spielen** oder **Im Finder zeigen** drücken. BPS- und UPS-Patches lehnen das falsche Spiel ab. IPS-Patches können das nicht prüfen, und der Patcher sagt dir das.

## Wo deine Arbeit liegt

| Was | Wo |
|---|---|
| Deine Mod | Im Quellcode-Ordner des Spiels, standardmäßig `~/Documents/GSMapEditor/alchemy/` |
| Exportierte Patches | `~/Documents/GSMapEditor/Exports/` |
| Gepatchte Spiele | `~/Documents/GSMapEditor/Patched/` |
| Editor-Einstellungen und dein Rückgängig-Verlauf | `~/Library/Application Support/GS Map Editor/` |
| Temporäre Builds, können gefahrlos gelöscht werden | `~/Library/Caches/GSMapEditor/` |

Unter Windows und Linux liegen die ersten drei in `~/GSMapEditor/` in deinem Linux-Benutzerordner, die Einstellungen in `~/.config/gs-map-editor/` und die temporären Builds in `~/.cache/gs-map-editor/`.

Um deine Mod zu sichern, kopier den Quellcode-Ordner des Spiels an einen sicheren Ort. Deine Änderungen sind ganz normale Dateien in diesem Ordner.

## Tastenkürzel

Unter Windows und Linux nimmst du Strg statt ⌘ und Alt statt ⌥.

| Taste | Orte | Weltkarte |
|---|---|---|
| V | Ansicht | Ansicht |
| B | Malen | |
| C | Begehbarkeit | |
| H | Höhe | |
| K | Truhe | |
| E | Ereignisse | |
| D | Türen | |
| P | Personen verschieben | |
| S | Stempel | |
| G / O / R / T | | Boden / Overlay / Regionen / Städte |
| ⌘Z | Rückgängig | Rückgängig |
| ⇧⌘Z | Wiederholen | Wiederholen |
| ⌘S | Speichern | |
| ⌥-Klick | Einen Block aufnehmen | Einen Block oder eine Region aufnehmen |
| ⇧ beim Ablegen | Personen auf die nächsten 8 Pixel einrasten | |
| Esc | Einen Dialog schließen oder im Stempel zurück zum Kopieren | Einen Dialog schließen |

## Was er noch nicht kann

- **The Lost Age** und andere Ausgaben als die englische.
- **Windows oder Linux** als fertig gepackte App.
- **Ganz neue Orte:** Es gibt keinen Knopf, um einen hinzuzufügen.
- **Kämpfe und Spieldaten:** Monster, Kampftabellen, Gegenstände, Läden und Musik lassen sich nicht bearbeiten, du kannst aber malen, zu welcher Kampfregion eine Stelle auf der Weltkarte gehört.
- **Story-Skripte:** Du kannst ändern, was Personen sagen und wann, und einfache Ereignisse hinzufügen, aber keine Zwischensequenzen schreiben.
- **Die Karte im Pausenbildschirm.**

## Fehlerbehebung

| Du siehst | Was du tun kannst |
|---|---|
| „Zum Spielen brauchst du mGBA“ | Installier es von [mgba.io](https://mgba.io) und drück noch mal auf Spielen. |
| Der Editor sagt, der Quellcode des Spiels sei eine Version, die er nicht lesen kann | Der Quellcode hat sich auf eine Weise geändert, die dieser Editor noch nicht versteht. Verschieb diesen Ordner beiseite und nutze dann **Herunterladen** auf dem Einrichtungsbildschirm. Deine Mod bleibt in dem Ordner, den du verschoben hast. |
| „Aus deinen Änderungen ließ sich kein Spiel machen“ | Deine Dateien sind sicher. Wenn eine Zeile genannt wird, die du geschrieben hast, ändere ihren Text. Sonst nutze **Rückgängig**, bis es sich bauen lässt, und drück auf **Details anzeigen**, um die eigene Meldung des Builds zu sehen. |
| „Die Dateien dieses Orts lassen sich nicht lesen“ | Eine seiner Dateien ist beschädigt. Nutze **Ort zurücksetzen …** oder **Rückgängig**, wenn ein kürzliches Speichern das verursacht hat. |
| „Die Datei mit deinen Änderungen an Personen, Türen und Ereignissen lässt sich nicht lesen“ | Nutze **Rückgängig**. Wenn das nicht hilft, stell diese Datei aus deiner Sicherung wieder her. |
| „An diesem Ort ist kein Platz für mehr davon“ | Dem Ort sind die Codes für Schilder und Tritt-Nachrichten ausgegangen. Entfern eins, das du hinzugefügt hast. |
| „Die Schrift des Spiels hat kein …“ | Ersetz dieses Zeichen durch einfache Buchstaben und Satzzeichen. |
| Der Einrichtungsbildschirm sagt, dein Ordner hat ein Leerzeichen im Pfad | Der Build kann keine Pfade mit Leerzeichen verwenden. Wähl eine Kopie des Spielquellcodes in einem Ordner ohne Leerzeichen im Pfad. |
| Die App öffnet sich mit einem Fehler auf dem Einrichtungsbildschirm | Die Meldung sagt, was sie nicht lesen konnte. Drück auf **Noch mal prüfen**, nachdem du es behoben hast. |
| „Etwas ist schiefgelaufen“ | Diese Aktion wurde nicht abgeschlossen. Versuch es noch einmal, und wenn es immer wieder passiert, starte die App neu. |
| „Diese Karte nutzt einen anderen Blocksatz“ | Der Stempel fügt nur zwischen Orten ein, die einen Blocksatz teilen. |
| „Dieser Ort teilt seine Grafiken mit anderen Orten“ | Importieren funktioniert nur an Orten mit eigenen Grafiken. Die Meldung nennt einige, die du nutzen kannst. |
| „Dieser Block wurde ausgemustert“ | Seine Grafik wurde für ein importiertes Bild wiederverwendet. Wähl einen anderen Block. |
| „Im Spiel ist kein Platz für weitere Truhen“ | Dem Spiel sind die freien „Geöffnet“-Flags ausgegangen. Entfern eine Truhe, die du hinzugefügt hast. |
| Eine Truhe fehlt im Spiel | Ein Ort zeigt nur seine ersten 10 Truhen und Steine. Führ **Prüfen** aus. |
| Prüfen sagt, eine Änderung „passt nicht mehr“ | Der Quellcode des Spiels hat sich unter dieser Änderung geändert. Sie wird aufbewahrt, bleibt aber aus deinem Spiel draußen. |
| Ein Ort sieht anders aus, als du ihn bearbeitet hast | Vielleicht bist du in einem anderen **Story-Abschnitt**, und Spielen startet ein neues Spiel, das die frühe Version zeigt. |
| Die Einrichtung ist mittendrin fehlgeschlagen | Drück auf **Noch mal prüfen** und dann auf den Knopf des Schritts. Das Protokoll unter der Checkliste zeigt, was passiert ist. |
| Windows: Der Editor hat sich nicht in deinem Browser geöffnet | Das kleine Fenster von GS Map Editor zeigt seine Adresse: Kopier sie in deinen Browser. |
| Windows: Das Installationsprogramm sagt, Ubuntu sei nicht bereit | Starte Windows neu, falls es dich darum gebeten hat, öffne **Ubuntu** einmal aus dem Startmenü, um einen Benutzernamen und ein Passwort zu wählen, und führ dann das Installationsprogramm noch einmal aus. |

## Probleme melden

Bitte [eröffne ein Issue](https://github.com/TRosenvall/GS-Map-Editor/issues/new?template=bug_report.md) und schreib dazu, was du gemacht hast, was passiert ist und welchen Chip und welche macOS-Version dein Mac hat. Wenn der Editor **Details anzeigen** oder ein Einrichtungsprotokoll anbietet, drück auf **Details für einen Fehlerbericht kopieren** und füg es ein. Bitte häng keine ROMs oder Spieldateien an.

## Rechtliches

Der eigene Code von GS Map Editor steht unter der [MIT-Lizenz](LICENSE). Mitgelieferte Werkzeuge behalten ihre eigenen Lizenzen, aufgeführt in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Der Editor enthält keine ROM und keine Spielgrafiken, und er liefert den Text des Spiels nicht mit. Namen und Bilder werden während der Laufzeit aus deiner eigenen Kopie des Spielquellcodes gelesen. Golden Sun gehört Nintendo und Camelot, und dieses Projekt ist nicht mit ihnen verbunden. Alchemy ist ein eigenständiges Projekt mit eigenen Bedingungen.

Bitte teile keine gebauten Spiele. Teile stattdessen Patches.

## Für Entwickler

Wie man die App baut, die Tests, wie Änderungen ins Spiel gelangen und wie man alchemy-Updates folgt, steht alles in [docs/de/DEVELOPING.md](docs/de/DEVELOPING.md).
