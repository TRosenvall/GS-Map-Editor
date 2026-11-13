# gs-mapedit for players: product plan

**Audience:** fans and modders with no technical background, i.e. no terminal, hex, C, git or build systems.
**Delivery:** a packaged desktop app with an installer.
*(Decided by the project owner, 2026-10-20.)*

The engine layer that exists today stays the foundation. That covers the file formats, byte-exact saves, invariants, the scene-table hook and the build. This plan is about the layer players see.

## Principles

1. **Names, pictures and places, never codes.** Every value a player sees is named, previewed or shown on a map. Raw numbers live behind an "Advanced" toggle.
2. **One intent, one action.** "Add a chest with a Herb" becomes one action, even though it touches the marker list, collision, a scene event and a fresh flag.
3. **Impossible to break the game silently.** Invariants are enforced as today, and explained in plain language: "This door doesn't lead anywhere yet." (✅ the Check button, also run before every Build.)
4. **Always one click from playing.** Edit, then Play. The build is invisible unless it fails, and failures read as guidance, not compiler output.
5. **No ROM distribution.** Mods are shared as patch files that players apply to their own cartridge dump.

## What players do (journeys → screens)

| Journey | Screen / interaction | Engine pieces (exist?) |
|---|---|---|
| Explore the game's places | **World view:** overworld plus every town/dungeon, with connections drawn | Renderer ✅, Connections view ✅ (place by place), Atlas ✅ (every place at once), Go there ✅ (follow a door), overworld ✅ |
| Repaint part of a map | **Paint:** tile palette by theme, brushes, fill, copy/paste regions | Block painting ✅; Fill ✅; copy and paste (Stamp) ✅ |
| Change where you can walk | **Walkability brush:** walkable / blocked / ledge / ladder / water, shown as a clean overlay | Collision painting ✅; **named codes ❌ (research)** |
| Move a door / change where it leads | Click a door, then pick the destination by clicking on the target map | ✅ Doors tool |
| Add/move a chest or Psynergy stone | Drop a chest; pick contents (item picker with icons, coins, mimic) | ✅ Chest tool (items, coins); stones move only |
| Place/move people | Drag NPCs with sprite previews; see and edit what they say | Positions ✅; sprite previews ✅; what they say on hover ✅; add and remove ✅ |
| Try it | **Play:** build plus open the emulator at that map | One-click Play ✅ (saves, checks, builds, opens at the place being edited) |
| Share it | **Export mod:** a patch file plus a description | ✅ BPS from stock build to mod build |
| Undo mistakes / start over | History panel; "reset this map" | Undo and Redo ✅ (last 30 saved actions, kept between sessions); Reset place ✅ |

## Naming layer (research needed, mostly lookups)

- **Collision codes:** wall, floor, ledges, climb spots, search spots, hazard, exits, chests. Sources: `step.c`, `events.c`, the research docs.
- **Scenes:** `scenes.s` names plus area names (the game's own location names) for display.
- **Items:** `include/item_ids.h` names, plus item icons from the game's graphics.
- **Sprites:** sprite id → name and a preview image from the object graphics.
- **Dialogue:** message id → text from `text/en.po` (10,724 entries).
- **Flags:** `include/flags.h` names, plus an allocator for fresh chest flags (≥ 0xe00, unused).

## Packaging architecture (recommendation)

- **Shell:** pywebview (the native WKWebView) in a PyInstaller bundle: one 30 MB `.app` holding Python, the server and the pages. *(Changed from Tauri, 2026-10-22: the backend is Python already, and Tauri would add a Rust toolchain for no gain yet. Tauri stays an option if the backend moves to Rust.)*
- **Backend:** today's Python server, in the same process.
- **Game source:** the app downloads alchemy at a pinned commit that we have verified. Players never see git. Updates are explicit: "New alchemy version available; tested ✓".
- **Toolchain:** the hardest part.
  - alchemy needs its pinned compilers (built from source), binutils, and its own C tools (libpng).
  - Plan: build these per platform in CI and ship them as prebuilt binaries. The compilers are GPL; we publish their sources.
  - Platforms: macOS first (Intel + Apple Silicon), then Windows (alchemy officially supports Windows only through WSL, so a native port of the tools is the risk), then Linux.
- **Patches:**
  - Because the stock build is byte-identical to the retail ROM, a patch = diff(stock build, mod build), computed locally without ever touching a retail ROM.
  - Players apply it to their own dump with any BPS patcher, or with our app.
- **Playtest:** bundle mGBA (MPL-2.0) or detect an installed one; launch at the edited map if a debug entry point allows it.

## Milestones

1. **Player-facing UI in the current app.** Everything here carries straight into the desktop shell. It covers:
   - the naming layer;
   - walkability brushes;
   - click-to-link doors;
   - item/sprite pickers;
   - an add-chest action;
   - plain-language validation;
   - the world/connections view.
2. **Packaging spike (macOS):** ✅ app bundle and first-run setup (downloads alchemy, builds once). ✅ bundled toolchain (no Homebrew). Remaining: signing/notarizing (needs a Developer ID), Apple Silicon native build, a test on a truly fresh Mac. Success = a fresh Mac goes from zero to "Play" without a terminal.
3. **Patch export** ✅ (BPS, checked against rom.sha1). Applying others' patches ✅ (the Patcher).
4. **Overworld editing** ✅ (stages 4–5 of SPEC.md): ground, overlay, regions and their battles, town icons (moved, linked, added), step spots.
5. **Windows and Linux packaging.** Windows runs through WSL from an installer script (early test); Linux runs from source.

## Risks

- **Toolchain portability (Windows).** alchemy's build assumes a Unix shell. This may need WSL integration or a native port of its small C tools.
- **Upstream churn.** alchemy changes daily. Pin a commit, and gate updates on our round-trip and render-all checks plus a test build.
- **Scope of "meaning".** Some collision codes and event kinds are still unknown even to alchemy. Unknowns stay visible but labelled "unknown (advanced)".
- **Legal posture:** we never ship ROMs, extracted assets or built games. Players supply nothing (The Broken Seal builds from source), and the app downloads alchemy itself.
