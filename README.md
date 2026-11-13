# GS Map Editor

**English** · [Español](README.es.md) · [Deutsch](README.de.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [日本語](README.ja.md)

Make your own version of **Golden Sun: The Broken Seal** without writing code. Repaint towns, hide chests, write new dialogue, add people and doors, reshape the world map, then press **▶ Play** and walk around in your change. When you're happy with it, export a small patch to share.

The editor works on [alchemy](https://github.com/PascalPixel/alchemy), a project that rebuilds the game from readable source files. It builds your game from that source on your own computer, so you don't need a ROM to make a mod.

> **Preview: testers wanted.** The editor covers the English edition of The Broken Seal, on macOS and, as an early test, Windows. It has mostly been tested on one Intel Mac, and the Windows version has never run on a real Windows PC, so every report helps, including "it worked": [download it](https://github.com/TRosenvall/GS-Map-Editor/releases), try it, and [tell us how it went](https://github.com/TRosenvall/GS-Map-Editor/issues/new?template=bug_report.md). Keep a backup of any mod you care about.

**Alchemy version:** this editor is tested with alchemy commit [`5ca23b1fe1`](https://github.com/PascalPixel/alchemy/commit/5ca23b1fe1774f954aacfbd7db35c8c9b9a59184) (2026-11-12). Setup downloads exactly that commit. Alchemy changes quickly, so a newer copy may not work until the editor catches up.

## Contents

- [Getting started](#getting-started)
- [Your first mod in two minutes](#your-first-mod-in-two-minutes)
- [The editor at a glance](#the-editor-at-a-glance)
- [Saving and undoing](#saving-and-undoing)
- [Looking around](#looking-around)
- [Paint: what the ground looks like](#paint-what-the-ground-looks-like)
- [Walkability: where you can walk](#walkability-where-you-can-walk)
- [Height: how high the ground is](#height-how-high-the-ground-is)
- [Chests](#chests)
- [Events: people, signs and messages](#events-people-signs-and-messages)
- [Doors](#doors)
- [Move people](#move-people)
- [Stamp: copy and paste](#stamp-copy-and-paste)
- [Importing your own pictures](#importing-your-own-pictures)
- [Story and scene tables](#story-and-scene-tables)
- [Connections](#connections)
- [The world map](#the-world-map)
- [Check: finding problems](#check-finding-problems)
- [Playing your game](#playing-your-game)
- [Sharing your mod](#sharing-your-mod)
- [Playing someone else's mod](#playing-someone-elses-mod)
- [Where your work lives](#where-your-work-lives)
- [Keyboard shortcuts](#keyboard-shortcuts)
- [What it can't do yet](#what-it-cant-do-yet)
- [Troubleshooting](#troubleshooting)
- [Reporting problems](#reporting-problems)
- [Legal](#legal)

## Getting started

### What you need

- A Mac with macOS 11 or later, or a PC with Windows 10 or 11.
- About 3 GB of free space for the game's source and its build.
- [mGBA](https://mgba.io/downloads.html), a free Game Boy Advance emulator, to play your game (on Windows, its Windows installer).
- An internet connection for the first setup.

### Get the app (Mac)

Download the newest `.dmg` from [Releases](https://github.com/TRosenvall/GS-Map-Editor/releases):

- **AppleSilicon** for Macs with an M1, M2, M3, M4 or later chip;
- **Mac-Intel** for Intel Macs.

Not sure which you have? Apple menu → **About This Mac**: "Chip: Apple M…" is Apple Silicon.

Open the `.dmg` and drag **GS Map Editor** into **Applications**.

### Opening it the first time (Mac)

The app isn't signed with an Apple developer certificate yet, so macOS warns about it the first time:

1. Open it from Applications. macOS says it can't check the app: press **Done** (or **Cancel**).
2. Open **System Settings → Privacy & Security**, scroll down, and press **Open Anyway** next to GS Map Editor. Confirm with your password.

On macOS 14 and earlier you can instead right-click the app, choose **Open**, then **Open** again. After the first time it opens normally.

If you'd rather build the app yourself, follow [Desktop app](docs/DEVELOPING.md#desktop-app-macos) in the developer notes. If you're comfortable with a terminal and already have a built alchemy checkout, you can skip the app and run `python3 server.py --root /path/to/alchemy`, then open http://127.0.0.1:8765/.

### Get the editor (Windows, early test)

The editor runs inside WSL, the Linux built into Windows, because that's the only way the game's source builds on Windows. It opens in your web browser.

1. Download `Install-GS-Map-Editor.cmd` from [Releases](https://github.com/TRosenvall/GS-Map-Editor/releases). If your browser says it isn't commonly downloaded, choose **Keep**.
2. Double-click it. Windows says it protected your PC because the installer isn't signed yet: press **More info**, then **Run anyway**.
3. The first time, it turns on WSL and installs Ubuntu. Windows asks for administrator permission and may ask you to restart; if it does, restart and double-click the installer again.
4. When Ubuntu asks, choose a username and a password. Typing the password shows nothing; that's normal. The next step asks for it.
5. The installer sets up the editor inside Ubuntu and adds **GS Map Editor** to your Start menu and desktop.

Open **GS Map Editor**. A small window appears; keep it open while you use the editor, since closing it stops the editor. The editor opens in your browser. Running the installer again updates the editor to the version it came with.

On Windows, keyboard shortcuts use Ctrl where this guide says ⌘, and Alt where it says ⌥. Exported patches and patched games go in **Documents\\GSMapEditor**, as on a Mac. The game source and its builds stay inside Ubuntu, in `GSMapEditor` in your Ubuntu home folder, because building there is much faster; File Explorer shows it under **Linux → Ubuntu → home**.

### First-run setup

The editor opens on a checklist the first time. It takes around 15 minutes, mostly waiting. Press the button on each step and the editor does the rest:

1. **Apple's developer tools** (Mac only): opens Apple's installer.
2. **The tools for building the game:** already included with the app on a Mac, and put in place by the installer on Windows.
3. **The game's source:** downloads alchemy into `~/Documents/GSMapEditor/` (on Windows, `GSMapEditor` in your Ubuntu home folder). If you already have a copy, choose **I already have a copy…** and pick its folder.
4. **Preparing the build:** sets up the game's compilers, once.
5. **A first build of the game:** builds the game once.

Then press **Open the editor**. After this, the app opens straight into the editor.

## Your first mod in two minutes

1. Pick a place from the list on the left. Type in the **Find a place** box to search.
2. Press **Chest** in the top bar, then click an empty bit of ground.
3. Type an item name, such as `Herb`, and press **Add chest**.
4. Press **▶ Play**. Your game opens in mGBA, in the place you were editing, a few seconds after the game boots.
5. Walk up to the chest and open it.

## The editor at a glance

| Area | What's there |
|---|---|
| **Left** | The list of places. The world map is at the top. |
| **Top bar** | Zoom, layers, overlays, tools, and buttons for saving, checking and playing. |
| **Middle** | The map. |
| **Right** | The panel for the tool you're using. |
| **Bottom line** | Status messages. As you hover, it says what the spot under your cursor does, such as "Chest: Herb" or where an exit leads. |

Tick **Advanced** in the top bar to show raw numbers and codes and a separate **Build** button. You won't need it for normal editing.

### Languages

The editor speaks English, Spanish (Español), German (Deutsch), French (Français), Italian (Italiano) and Japanese (日本語). It starts in your computer's language when it has it. Change it with the 🌐 menu, at the top right of the first setup screen and at the end of the top bar. Only the editor's own words change: the game you're modding is the English edition, so place names, people, items and the dialogue you write stay in English.

This guide is also translated: see the links at the top. The translations of the editor and of this guide were made with AI help and haven't all been checked by native speakers yet. Where a translated guide differs from this one, this English guide is the current one. If something reads oddly, please [say so](https://github.com/TRosenvall/GS-Map-Editor/issues/new?template=bug_report.md) with the wording you'd expect.

## Saving and undoing

Some changes wait for you to save, and others save straight away:

| Waits for **Save** (or ⌘S) | Saves immediately |
|---|---|
| Paint, Walkability, Height | Adding, changing or removing a chest |
| Stamp pastes | Events and doors |
| Dragging chests, stones and people | World map painting and town moves |

The editor also saves for you before you switch places, go to the world map or press Play, so moving on won't lose your work. If a save is refused, you stay where you are and the bottom line says why.

There are three ways back:

- **Undo** (⌘Z) takes back your last change, whatever it was: painting you haven't saved yet first, then saved actions, newest first, from any tool and any place. Adding a person, a chest, a door, an event, a world map stroke: all of them. The button's tooltip says what it will undo and where, and the editor opens that place to show you. The last 30 saved actions are kept, even after you close the editor.
- **Redo** (⇧⌘Z) puts back what Undo took, until you make a new change.
- **Reset place…** puts a place's maps, imported pictures and its own people, doors and events back as the original game has them. If you change your mind, **Undo** brings your version back. If a place shares its map with others, they go back too, and the editor warns you first. People and events that other places share are left alone unless you say otherwise: the editor asks.
- **Reset world map…**, on the world map page, does the same for the world map.

Text you've written stays in the game's text file while any event still uses some of it. It's only removed once nothing uses any of your lines. Undoing a saved action while you have unsaved changes throws those away too, and asks first.

Each save is all or nothing. If the editor stops part way through, it finishes undoing the half-done save the next time it starts. If a file can't be written, for example because it's locked in Finder, the save is refused and the rest of it is undone.

## Looking around

Press **View** (V) to look without changing anything.

- **Zoom:** 1× to 4×.
- **Layers:** each place has up to three, called **Ground**, **Middle** and **Overhead**. You can hide each one. Tick **Advanced** for sliders that fade them.
- **Overlays:** tick **Walkability**, **Height** to see ground height, or **Grid** to see the squares.
- **Chests** always show on the map. Doors, people and events show when you use their tools.

## Paint: what the ground looks like

Press **Paint** (B).

1. Choose a layer in the **on** menu in the top bar.
2. Pick a block from the **Blocks** panel on the right, or hold ⌥ and click the map to pick up the block under the cursor.
3. Click or drag on the map.
4. Save.

Tick **Fill** in the top bar (or press F) and a click fills the whole connected area that has the same block as the square you click, on that layer. Fill works in **Walkability** and **Height** too, matching walkability or height instead. Undo takes back a whole fill at once.

Each place has its own set of blocks, so the panel changes from place to place.

## Walkability: where you can walk

Press **Walkability** (C). Painting a block doesn't change where you can walk, so this is a separate step. Pick a brush and paint.

| Brush | What it does |
|---|---|
| **Floor** | Plain ground you can walk on. |
| **Wall** | Blocks walking, whatever the height. |
| **Ledge** | Hold Down against it for a moment and the leader jumps down. |
| **Climbable wall / ladder** | Hold Up or Down against it for a moment to climb. |
| **Jump gap** | Push against it for a moment and the leader jumps over it, if the far side allows landing. |
| **Encounter ground A / B** | Walkable. Random battles use the place's first or second encounter zone. |
| **Hazard ground** | Walkable, but hurts the party after enough steps, if the scene turns that on. |
| **Cloak shadow** | Walkable. The only ground where the Cloak Psynergy keeps the party hidden. |
| **Empty jar, barrel, box, grave, books, well** | Searching it finds nothing. Usually a wall too, through its height. |

The Chest, Doors and Events tools set the special codes they need themselves, so you don't have to paint those.

## Height: how high the ground is

Press **Height** (H). The panel lists the heights this place already uses, such as "Flat, 24 px" or "Slope or step". Pick one and paint.

Height affects walking as well as looks. People stand at the height of the ground they're on, and the game refuses a step of more than 8 pixels up or 12 pixels down, so a big difference in height acts as a wall.

## Chests

Press **Chest** (K).

- **Add one:** click an empty spot, choose an **Item** (start typing its name) or an amount of **Coins**, then press **Add chest**.
- **Change one:** click it, change what's inside, and confirm.
- **Remove one:** click it and press **Remove chest**.
- **Move one:** drag it, then save. Psynergy Stones can be dragged too. A chest can't go on a square that's already a door, sign or step message.

The editor handles the rest, including the flag that remembers a chest has been opened, so a chest stays empty when you come back. A place can hold at most **10 chests and stones**.

## Events: people, signs and messages

Press **Events** (E). The panel lists everything that happens in this place, in words: what people say, Mind Read thoughts, signs, step messages, searches and exit areas. People show on the map as themselves; hover over someone to see what they say.

**Story stage** at the top matters. Many places change as the story moves on, and each stage has its own people and events. Choose the stage you want to edit.

### Adding things

Click a spot on the map, then choose:

- **Add a sign (read with A)…** for a sign or something to examine.
- **Add a step message…** for a message that shows when you step there. It won't repeat while you stand there, so it can't trap the player, and it shows again if you step off and come back.
- **Add a person here…** to choose who it is with a picture preview, and whether they **walk around**. The editor checks the spot first (see below).

To take away someone you added, click them and press **Remove this person**: what they say goes too. The game's own people can't be removed, because the story moves them and talks to them, but you can move them.

### Where people can stand

Not every spot that looks open is a good place for someone to stand. Tick **Where people can stand** at the top, or just press **Add a person here…**, and the map is coloured by what a person there would mean:

| Colour | Means |
|---|---|
| Green | The party can walk up and talk to them. |
| Yellow | The party can't walk onto that square, but can talk to them from beside it, like a shopkeeper behind a counter. |
| Blue | Ice the party slides across, as in Imil. Someone standing there gets in the way of sliding. |
| Orange | A door, exit or step spot: someone there would be in the way. |
| Red | The party can't get near enough to talk by walking. |

It's worked out from the game's own walking rules, starting from every point where the party arrives in the place: you can step up 8 pixels and down 12, walls stop you, and you can talk to someone within two squares. Places that only Psynergy or the story open up show as red, so red there doesn't always mean wrong.

When a spot has a problem, the editor says what it is in plain words, for example "the ground here is 32 pixels higher than the nearest path", or that standing there would cut the party off from a door. Then it offers a way round:

- **Move to the nearest good spot** moves the person to the closest square with nothing wrong.
- **Level … squares to the path's height** changes the height of the ground from the nearest path up to the spot, so the party can walk there. The picture doesn't change, so use **Paint** if it should look like a path. It's ordinary unsaved painting: Save keeps it and Undo takes it back.
- **Add here anyway…** if you know better, for example when a story event opens the way.

Dragging a person with **Move people** gets the same check when you let go.

### Making people talk

Click a person. Press **Make them say something…**, or **Add a line for a story moment…** if they already talk.

### Changing what's there

Each event in the list has these buttons, where they apply:

- **Change words** opens the writer.
- **When…** decides when the event happens: **Always**, **Only once** a story flag is set, or **Only while** it isn't. Flags are listed by name.
- **Remove** deletes it.

### The writer

Type normally. A blank line starts a new dialogue box, and the preview shows how the boxes will look in the game. **+ hero's name** inserts whatever name the player chose. The game's font has plain letters, numbers and punctuation, with no accents. Curly quotes, long dashes and "…" become their plain forms by themselves, and anything else the font can't draw is refused when you save.

Your words are added as new lines, and the game's own text is never overwritten. If the same line is used somewhere else, it stays as it was.

### Shared scenes

Some places share their people and events with other places. The panel warns you when a change here will also show up there.

## Doors

Press **Doors** (D). Every door shows on the map with where it leads. **Blue** cells are doors, and **red** ones lead nowhere.

- **Change a door:** click it, press **Change where it leads…**, pick a place, then click where the party should arrive on that place's map.
- **Make a door:** click any other spot and press **Make a door here…**. It can lead anywhere in the game.
- **Remove a door:** click it and press **Remove door**. Its cells turn back into ground.
- **Follow a door:** click it and press **Go there →**. The place it leads to opens with its arrival point marked, and **← Back to …** returns you to the door.

A door changes in every story stage of the place. Doors opened by scene scripts are found too: you can change where they lead, but the script itself stays the same.

## Move people

Press **Move people** (P).

1. In the **Story and scene** panel, choose a scene and a table of people or arrival points.
2. Drag them on the map. Hold ⇧ as you let go to snap to the nearest 8 pixels.
3. Save.

Arrival points are where the party appears on entering a place.

## Stamp: copy and paste

Press **Stamp** (S).

1. Drag a rectangle on the map to copy it.
2. Click to paste, here or in another place that uses the same block set.
3. Press Esc to go back to copying.

- **Walkability & height** copies those along with the blocks, and is on by default.
- **Objects only** pastes just the trees and other objects, not the ground under them.
- A paste is one undo step, and your copy survives switching places and reloading.
- Places with a different block set refuse the paste, because every block would draw the wrong picture.

## Importing your own pictures

**Import image…** is in the Stamp panel. It works on places whose art isn't shared with any other place, which is 27 of the 182 in a fresh copy of the game. Elsewhere the editor refuses, because your picture would change how other places look.

1. Choose **Overlay** (drawn over the ground, with a transparent background) or **Ground**.
2. Press **Import image…** and pick a PNG, GIF or BMP. It can cover at most 256 squares of 16×16 pixels, for example 256×256 pixels, though a detailed picture can run out of room sooner. The editor says so if it does.
3. Check the preview. It shows the colours the game will really draw, and how much room is left.
4. Press **Add to tile set**. The new blocks land on the Stamp clipboard, ready to click into place.

The picture is fitted to this place's colours, and repeated pieces are reused to save room. When the sheets are full, the editor reuses art from blocks the place never uses, and those blocks then disappear from the palette.

## Story and scene tables

The **Story and scene** panel shows the scenes that use this map and the tables behind them, with friendly names such as "Arrival points: normal". Arrival points and people show on the map. Exits are edited as a list, with a check that the arrival point you pick exists. Most of the time the Doors, Events and Move people tools are easier.

## Connections

Press **Connections** to see any place in the middle, with every place that leads to it on the left and everywhere it leads on the right. Click a place to move there, or press **Open** to jump to that door in the editor. Use the search box to find a place.

## The world map

Choose the world map at the top of the place list. Press **← Places** to go back.

| Tool | Key | What it does |
|---|---|---|
| **View** | V | Hover to see a spot's region and what it does. Click a town, dungeon or blue step spot to see where it leads. |
| **Ground** | G | Paint ground blocks. ⌥-click picks up a block, and recent blocks stay at hand. |
| **Overlay** | O | Paint mountains, trees and coastline. Walking depends on the tiles of both layers. |
| **Regions** | R | Paint encounter regions. Each has its own random battles, and each is named after the towns inside it. |
| **Towns** | T | Drag a town or dungeon to move it. Click one to change where it leads. **Place a new icon…** adds one, with a picture the game's own towns use; icons you added can be removed. |
| **Step spots** | P | Blue squares lead somewhere when stepped on. Click one to change where it leads or remove it, or click any other square to make a new one. |

- Tick **Walkability**, **Encounter regions** or **Places** to show those on the map.
- When you move a town, **move its arrival points too** keeps you appearing next to it when you leave. It's on by default.
- Changes save as you paint. **Undo** takes back the last stroke, and **Redo** puts it back.
- The pause-screen map is a separate picture, so it won't follow your changes, and new icons get no marker on it.

## Check: finding problems

Press **Check** to look over every map for problems your changes would cause. Each one comes with a fix and a **Show** button that opens the spot. It looks for:

- doors that lead nowhere or to an arrival point that doesn't exist;
- chests that can't be opened, have nothing defined, fill up again, or share an "opened" flag;
- more than 10 chests and stones in a place;
- squares using a block or height the place doesn't have;
- lines you wrote that the game's font can't draw;
- places whose files have been damaged;
- edits that no longer fit after the game's source was updated.

The original game has quirks of its own, and those are hidden unless you tick **Also show the original game's own quirks**. On a place you've edited, a quirk the original already had can be listed as yours. On a place's page, Play, Export and **Build** run Check for you first and ask before carrying on with problems. On the world map page, Play and Build don't, so press Check from a place. If Check can't finish, it says so and asks before carrying on.

## Playing your game

Press **▶ Play**. It saves, checks, builds and opens your game in mGBA, starting at the place you're editing. From the world map page, it builds and starts on the world map, without the check.

- Each Play is a **fresh game**: Isaac alone, with no story progress, so a place can look like its early-game version.
- You appear at the place's first arrival point the party can walk on from, by the game's walking rules, not the spot you're viewing. Story scenes aren't followed, so a few places may still start you inside one. If that happens, choose another arrival point in **Start at**, next to ▶ Play, and press Play again.
- A build after a map change takes around 20 seconds.
- The start point only exists in a throwaway copy of the game, so your exported mod still boots normally from the title screen.

## Sharing your mod

Press **Export mod…**.

1. Fill in a **Name**, and optionally your name and what it changes.
2. Press **Export**.

You get a small `.bps` patch and a readme for players in `~/Documents/GSMapEditor/Exports/`. Press **Show in Finder** to see them. If you export again under the same name, the editor asks whether to replace the earlier patch or keep it and number the new one. Export runs Check first, and tests each patch once to confirm it reproduces your build exactly.

Tick **Also save an .ips** if your players use older patchers. It's much larger, because IPS can't record moved data.

**Share the patch, never the built game.** Players apply the patch to their own copy, so you never hand out the game itself. A `.bps` patch works with common patchers such as Rom Patcher JS and Floating IPS, as well as this editor.

## Playing someone else's mod

Press **Patcher…**.

1. Press **Choose a patch…** and pick a `.bps`, `.ips` or `.ups` file.
2. Choose the game to patch: **The unmodified game, built on this Mac** (no ROM needed), or **My own ROM file**.
3. Press **Patch**.

The patched game is saved in `~/Documents/GSMapEditor/Patched/`, and you can press **Play in mGBA** or **Show in Finder**. BPS and UPS patches refuse the wrong game. IPS patches can't check, and the patcher tells you so.

## Where your work lives

| What | Where |
|---|---|
| Your mod | Inside the game source folder, by default `~/Documents/GSMapEditor/alchemy/` |
| Exported patches | `~/Documents/GSMapEditor/Exports/` |
| Patched games | `~/Documents/GSMapEditor/Patched/` |
| Editor settings and your Undo history | `~/Library/Application Support/GS Map Editor/` |
| Temporary builds, safe to delete | `~/Library/Caches/GSMapEditor/` |

On Windows and Linux the first three are in `~/GSMapEditor/` in your Linux home folder, settings in `~/.config/gs-map-editor/` and temporary builds in `~/.cache/gs-map-editor/`.

To back up your mod, copy the game source folder somewhere safe. Your changes are ordinary files in that folder.

## Keyboard shortcuts

On Windows and Linux, use Ctrl for ⌘ and Alt for ⌥.

| Key | Places | World map |
|---|---|---|
| V | View | View |
| B | Paint | |
| C | Walkability | |
| H | Height | |
| K | Chest | |
| E | Events | |
| D | Doors | |
| P | Move people | |
| S | Stamp | |
| F | Fill on or off, in Paint, Walkability and Height | |
| G / O / R / T / P | | Ground / Overlay / Regions / Towns / Step spots |
| ⌘Z | Undo | Undo |
| ⇧⌘Z | Redo | Redo |
| ⌘S | Save | |
| ⌥-click | Pick up a block | Pick up a block or region |
| ⇧ while dropping | Snap people to the nearest 8 pixels | |
| Esc | Close a dialog, or go back to copying in Stamp | Close a dialog |

## What it can't do yet

- **The Lost Age**, and editions other than English.
- **Windows or Linux** as a packaged app.
- **Brand new places:** there's no button for adding one.
- **Battles and game data:** monsters, encounter tables, items, shops and music can't be edited, though you can paint which encounter region a world map spot belongs to.
- **Story scripts:** you can change what people say and when, and add simple events, but not write cutscenes.
- **The pause-screen map.**

## Troubleshooting

| You see | What to do |
|---|---|
| "Play needs mGBA" | Install it from [mgba.io](https://mgba.io) and press Play again. |
| The editor says the game source is a version it can't read | The source has changed in a way this editor doesn't understand yet. Move that folder aside, then use **Download** on the setup screen. Your mod stays in the folder you moved. |
| "Your changes couldn't be turned into a game" | Your files are safe. If it names a line you wrote, change its words. Otherwise use **Undo** until it builds, and press **Show details** to see the build's own message. |
| "This place's files can't be read" | One of its files is damaged. Use **Reset place…**, or **Undo** if a recent save caused it. |
| "The file that holds your people, door and event edits can't be read" | Use **Undo**. If that doesn't help, restore that file from your backup. |
| "This place has no room for more of these" | The place has run out of codes for signs and step messages. Remove one you've added. |
| "The game's font has no…" | Replace that character with plain letters and punctuation. |
| The setup screen says your folder has a space in its path | The build can't use paths with spaces. Choose a copy of the game source in a folder with no spaces in its path. |
| The app opens on the setup screen with an error | The message says what it couldn't read. Press **Check again** after fixing it. |
| "Something went wrong" | That action didn't finish. Try again, and if it keeps happening, restart the app. |
| "This map uses a different block set" | Stamp only pastes between places that share a block set. |
| "This place shares its art with other places" | Import only works on places with their own art. The message names some you can use. |
| "That block was retired" | Its art was reused for an imported picture. Pick another block. |
| "The game has no room for more chests" | The game has run out of free "opened" flags. Remove a chest you've added. |
| A chest is missing in the game | A place shows only its first 10 chests and stones. Run **Check**. |
| Check says an edit "no longer fits" | The game's source changed under that edit. It's kept but left out of your game. |
| A place looks different from what you edited | You may be on another **Story stage**, and Play starts a fresh game, which shows the early version. |
| Setup failed part way | Press **Check again**, then the step's button. The log under the checklist shows what happened. |
| Windows: the editor didn't open in your browser | The small GS Map Editor window shows its address: copy it into your browser. |
| Windows: the installer says Ubuntu isn't ready | Restart Windows if it asked you to, open **Ubuntu** from the Start menu once to choose a username and password, then run the installer again. |

## Reporting problems

Please [open an issue](https://github.com/TRosenvall/GS-Map-Editor/issues/new?template=bug_report.md) with what you were doing, what happened, and your Mac's chip and macOS version. When the editor offers **Show details** or a setup log, press **Copy** and paste it in. Please don't attach ROMs or game files.

## Legal

GS Map Editor's own code is under the [MIT licence](LICENSE). Bundled tools keep their own licences, listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

The editor contains no ROM or game art, and it doesn't ship the game's text. Names and pictures are read from your own copy of the game's source while it runs. Golden Sun belongs to Nintendo and Camelot, and this project isn't affiliated with them. Alchemy is a separate project with its own terms.

Please don't share built games. Share patches instead.

## Developers

Building the app, tests, how edits reach the game, and how to follow alchemy updates are all in [docs/DEVELOPING.md](docs/DEVELOPING.md).
