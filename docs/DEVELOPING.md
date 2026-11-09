# Developing GS Map Editor

How to run, build, test and update the editor, and how its features work inside. To learn how to use it, read the [README](../README.md).

## Running from source

Needs Python 3 with Pillow, and an alchemy checkout that has been built.

```sh
python3 server.py                  # alchemy at ~/gs_project/alchemy-port
python3 server.py --root /path/to/alchemy --port 8765
# open http://127.0.0.1:8765/
```

### Desktop app (macOS)

`GS Map Editor.app` is the editor in its own window, for players who never open a terminal.

```sh
python3 -m venv .venv && .venv/bin/pip install pywebview pyinstaller pillow
python3 packaging/build_toolchain.py                          # GBA binutils + libpng, ~10 min, once
.venv/bin/python packaging/make_icon.py                       # packaging/icon.icns
.venv/bin/pyinstaller --noconfirm packaging/gsmapedit.spec    # -> dist/GS Map Editor.app
python3 packaging/make_dmg.py                                 # -> dist/GS-Map-Editor-<version>.dmg
python3 packaging/sign_and_notarize.py --identity "Developer ID Application: …"   # needs an Apple Developer account
.venv/bin/python desktop.py                                   # or run it without packaging
```

The app carries its own build tools (`packaging/toolchain`, 15 MB): GNU binutils for the GBA, a static libpng, and a small `libpng-config` stand-in that answers alchemy's `tools/Makefile`. They're built from pinned, checksummed sources and need nothing but macOS. With them, players need only Apple's free developer tools; Homebrew is used only by a build without the toolchain. `GSMAP_NO_BREW=1` hides Homebrew, to prove a build doesn't need it.

On first run it shows a setup checklist (`static/setup.html`, `gsmap/setup.py`). Each step is checked, never assumed, and long steps show their log live:
1. Apple's developer tools (opens Apple's installer).
2. The build tools: included with the app. A build without them falls back to Homebrew and the packages from alchemy's INSTALL.md, checked by what the build uses rather than by formula names.
3. The game source: download alchemy (pinned to the commit this editor was tested with) into `~/Documents/GSMapEditor/` (no spaces: the build can't handle them), or choose an existing checkout.
4. `make bootstrap` (the game's compilers, built once from the sources in alchemy's `alchemy-gcc` submodule, with no download), then a first `make tbs-en`.

After that, the app opens straight into the editor. Settings live in `~/Library/Application Support/GS Map Editor/`. The app holds no game data: the game is built from alchemy's source on the player's Mac. Both of its servers listen on this machine only, behind a random token. `desktop.py --no-window` prints their addresses, for testing.

### Releasing

Releases are built by GitHub, on its Macs, by `.github/workflows/release.yml`: one disk image for Apple Silicon (`macos-15`) and one for Intel (`macos-15-intel`). Each job builds the toolchain and the app, checks both are for its chip, runs `packaging/smoke_test.py` (the app starts, finds its tools and names the pin) and makes the `.dmg`.

1. Set the version in `packaging/gsmapedit.spec` (`CFBundleShortVersionString`).
2. Write the notes players read in `docs/releases/v<version>.md`.
3. Commit, then `git tag v<version> && git push origin v<version>`. The workflow publishes a pre-release with both images, even if one chip's job fails.

**Run workflow** on the Actions page builds the images without releasing. The images aren't signed: the README's "Opening it the first time" says how players get past Gatekeeper, and `packaging/sign_and_notarize.py` takes over once there's a Developer ID.

## How each feature works

Local maps, The Broken Seal, English edition. For how to use these, see the [README](../README.md).

- **View:** all 182 maps, with correct tilesets and placeholders, per-layer toggles and opacity, collision and height overlays.
- **Paint:** blocks, collision and height, with ⌥-click eyedropper and undo/redo. Saves are byte-exact for anything unedited.
- **Stamp** (S): drag a rectangle to copy an area, then click to paste it, here or in another map with the same block set (Vale ↔ Debug · Sandbox).
  - The copy carries all three layers plus walkability and height.
  - **Objects only** pastes just the trees and other objects, not the ground under them (a colour test against each layer's background block).
  - A paste is one undo step. The clipboard survives switching maps and reloading the page. Esc goes back to copying.
  - Maps with a different block set refuse the paste, since every block number would draw the wrong tile.
- **Import image** (maps with their own tile set; today the Debug · Sandbox): pick a PNG and a layer and see a preview, then **Add to tile set**. The new blocks land on the Stamp clipboard, ready to click into place.
  - The importer cuts the image into 8×8 tiles and matches its colours to one of the map's 14 palette rows (each tile picks its own row only if no single row fits). Index 0 is transparent.
  - Tiles already in the sheets, mirrored ones included, are reused.
  - New tiles go into blank space first. Then come tiles used only by blocks the map never places. Those blocks are *retired* (hidden from the palette, refused by Stamp) and listed in alchemy's `games/tbs/src/mod/tilesets.json`.
  - The preview shows the colours the game will draw, plus how much room is left.
- **Events** (E): everything that happens in a scene, in words, for the story stage you pick:
  - **People:** "🗨 Garet: “Ever since the tremors started…”", Mind Read thoughts, and scripts with their own description ("Asks about the mayor before departure, or the tremors after returning").
  - **Spots:** signs (read with A), step messages, searches and what they find.
  - **Exit areas:** boxes that act as doors, drawn on the map. Change where they lead, or remove them.
  - Click a person to see their events and **make them say something** (or add a line for a story moment). Click any spot to **add a sign**, **a step message** or **a person**.
  - **Change words** opens a writer with live dialogue-box previews: type normally, and a blank line starts a new box. **When…** sets "always", "only once <story flag> is set" or "only while it isn't", with flags by name.
  - New lines are added to `en.po` in an editor-owned block. The game's own lines are never rewritten: changing what someone says points them at a new line. Text the game's font can't draw is refused before the build.
  - When a scene shares its people and events with others (the sandbox and the debug hub do), the panel says so.
- **Doors** (D): every door shows on the map with where it leads ("→ Vale Home"); ones that lead nowhere show red.
  - Click a door, then **Change where it leads…**: pick a place, then click an arrival point on its map.
  - Click any other spot and **Make a door here…** to add a door to anywhere in the game. **Remove door** turns all of a door's cells back into ground.
  - Doors opened by scene scripts (most of Vale's) are found too, by reading which exit the script asks for. Their destination can change; the script stays.
  - A door changes in every story stage of the scene, through exit and event overrides. Scene `.c` files are untouched.
- **Chests** (K): click an empty spot, pick an item (with its icon) or an amount of coins, and **Add chest**. Click a chest to change what's inside or remove it.
  - One action writes everything a chest needs: the marker, the cell's collision code, a `SEARCH(SEARCH_CHEST)` event in the scene's event table (as an override, so scene `.c` files stay untouched) and a fresh "opened" flag from the free chest range.
  - The code is one no event table of the map's scenes uses, and no map sharing those tables has in its collision, so nothing else becomes searchable. At most 10 chests and stones per map.
  - A chest is a `treasure_spot` line in the map's `map.s`, in the English edition's part of the file.
- **Chests and Psynergy stones:** drag to move. The marker row and both cells' collision codes update together, and saves that break the marker/collision rule are refused.
- **Scene tables:** for every scene using the map, pick a table.
  - Entrances and NPCs show on the map; drag them with the Points tool.
  - Exits are edited as a list (kind, target scene, entrance, flag), with a check that the target entrance exists.
- **Connections:** any place in the middle, with every place that leads to it on the left and everywhere it leads on the right (door, scripted door or scene event, and the arrival point). Click a place to move there; **Open** jumps to the door in the editor.
- **Check:** looks over every map for problems your changes would cause in the game and says them in plain words, each with a fix and a **Show** button that opens the spot:
  - doors that lead nowhere, or to an arrival point that doesn't exist;
  - chests that can't be opened, have nothing defined, refill because of a temporary flag, or share an "opened" flag;
  - more than 10 chests and stones on a map; cells using missing or retired blocks;
  - edits to scene tables that no longer match the game source (after an alchemy update).
  - The original game has quirks of its own (115 today, e.g. 83 leftover doors). Each issue is also looked for in the unmodified game, and those are hidden unless you ask for them.
  - **Build** runs the check first and asks before building with problems.
- **World map** (top of the place list): the whole overworld, loaded as you scroll, with town and dungeon icons labelled by where they lead.
  - Overlays: walkability (blocked ground in red) and encounter regions, each named after the towns inside it ("Region 1 (Vale, Lunpa…)").
  - **Ground** / **Overlay**: paint blocks (⌥-click picks one up; recently used blocks stay at hand). **Regions**: paint encounter regions. Changes save as you paint; Undo takes the last stroke back. Cells are written into `map/world/blocks.tsv`, keeping each word's other fields.
  - **Towns**: drag an icon to move it. Its arrival points (where you appear on leaving the town) move with it, in every story stage that has the icon there. Click an icon or a blue step spot to change where it leads.
  - The snowy north is drawn with its own graphics set. The pause-screen map is a separate picture and doesn't follow edits.
- **Export mod…:** saves your mod as a small `.bps` patch, plus a readme for players, in `~/Documents/GSMapEditor/Exports/`.
  - The patch goes from the unmodified game to your build. The unmodified game is built once from the commit your mod starts from: in a separate folder via `git archive`, so your checkout is untouched. It's checked against alchemy's `rom.sha1`, so it equals the retail cartridge, and the patch applies to anyone's own dump.
  - Patches are BPS (Rom Patcher JS, Floating IPS, emulator soft-patching). Moved data becomes copies rather than new bytes. Every patch is applied once after writing, to check it reproduces your build exactly.
  - Export runs Check first. You share your changes, never the game.
- **Patcher…:** applies a mod's `.bps`, `.ips` or `.ups` patch and saves the game in `~/Documents/GSMapEditor/Patched/`, with **Play in mGBA** and **Show in Finder**.
  - Patch either the unmodified game this Mac built from source (no ROM needed) or your own ROM file. Your file is named from alchemy's `rom.sha1` ("Golden Sun (English)"), with a warning when it isn't an unmodified game.
  - BPS and UPS refuse the wrong game. IPS can't check, so the patcher says so.
  - Export can also write an `.ips` for older patchers. It's larger, because IPS can't record moved data (4.2 MB against 383 KB for the debug-room mod), and is checked the same way.
- **▶ Play:** one button: saves what's unsaved, runs Check, builds, and opens your game in mGBA, starting a fresh game at the place you're editing (from the world map page, on the world map). The start is written into a throwaway copy of the game; what you export has no trace of it. If the build fails you get a plain explanation, with the technical details folded away and a Copy button for bug reports. Build on its own is under Advanced.
- **Undo last save:** steps back through saved actions whichever tool made them, including chests, doors and events, which save immediately. The last 30 are kept.
- **Reset place…:** puts a place back as the original game has it (Undo last save brings your version back). Scene tables other places share are left alone, and it says so.
- **Saving is all or nothing:** one action's files land together or not at all, every file is replaced in one step, and if the editor dies part way it finishes undoing on the next start.
- **Names:** places are listed by their in-game names ("Vale · Vale Home").
- **Walkability brushes:** named and colour-coded (Floor, Wall, Ledge, Ladder, Jump gap, Hazard, search spots, …).
- **Hover:** says what a cell does ("Exit → Vale", "Chest: Herb", "Scripted (probably a door to …)").
- **NPCs:** drawn as their sprites, listed by name.
- **Scene tables:** friendly names ("Arrival points: normal", "People: After Kalay").
- **Advanced checkbox:** brings back raw codes.
- **Links:** `?map=003&tool=points&kind=placements` opens straight to a place.
- **No shipped art or text:** item, place, character, sprite and flag names, item icons and sprite previews are all read at runtime from the player's own alchemy checkout. `gsmap/data` holds only the editor's own findings: preview frames, free chest flags, and what each walkability code does.

**How scene edits reach the game:** through one hook, without rewriting alchemy's scene files. See `docs/SPEC.md` and alchemy's `games/tbs/src/mod/README.md`.
- The editor stores edited copies of tables in alchemy's `games/tbs/src/mod/overrides.json` and generates `mod.c` from it.
- `MOD_SCENE_LOADED` in `Scene_LoadOverlay` (`system/main_routine.c`), which the editor adds to a plain checkout the first time it writes a scene edit, swaps in a wrapper that still runs each scene's own table-choosing logic.
- With no overrides, GSMOD is off and all six editions still build byte-identical.

Next stages are in the build plan in [`SPEC.md`](SPEC.md).

### Keeping up with alchemy

Everything the editor knows about alchemy's layout is in `gsmap/layout.py`. The commit it's tested with is `ALCHEMY_PIN` in `gsmap/setup.py`. When you change it, update the version line in the README too, or the safety test fails. To try a new version:

1. `python3 -m gsmap.preflight path/to/alchemy` says in plain words what no longer matches. It runs at every start too, and stops there rather than drawing maps with the wrong tiles.
2. Build it, then `python3 tools/snapshot.py path/to/alchemy new.json` and `python3 tools/snapshot.py --compare old.json new.json` show every difference in what the editor reads. The two versions build the same game, so results should only change where you expect.
3. Run the tests below.

Moving an existing checkout to a new alchemy by hand is ordinary git: merge or check out the new commit, then `git submodule update --init --recursive alchemy-gcc`. Since `alchemy-gcc` 3a12774 (alchemy 2026-11-08), agbcc is plain files instead of a nested submodule, and in a checkout from before that the update stops with "untracked working tree files would be overwritten". Inside `alchemy-gcc`, run `git submodule deinit -f agbcc`, delete the `agbcc` folder and `.git/modules/agbcc` under alchemy-gcc's git folder, then update again. Delete `out/*/deps.mk` and `out/*/objects.mk` before the first build. Setup's **Download** always makes a fresh clone, so players don't meet this.

Saved scene edits carry a fingerprint of the table they were made for. A table renamed upstream follows it. An edit to a table whose original contents changed is kept but left out of the game, and Check reports it.

### Tests

- `python3 tests/safety.py`: what must never go wrong: failures and crashes leave no half-saved files, chests stay in their own rooms, bad values and hostile patches are refused, renamed or changed tables are handled, an unknown layout is reported rather than guessed at.
- `python3 tests/edits.py`: saves block, walkability and height edits on a copy of real maps and checks they read back, with nothing else changed.
- `python3 tests/roundtrip.py`: loads and re-saves every map grid, cell-picture and shape table, and chest list (727 files with the debug-room mod, 721 on a plain checkout). All must come out byte-identical. This guarantees that saving a map only changes what you edited.

## Docs

- [`SPEC.md`](SPEC.md): the editor spec, invariants and staged build plan.
- [`research/`](research/): evidence with file:line references.
  - `rendering.md`: placeholders, tilesets, windows, blending, animation.
  - `local-connections.md`: scenes, exits, markers, NPCs, new maps.
  - `overworld.md`: the world map.
