"""Overrides for scene tables, and the C that applies them.

overrides.json (in alchemy's games/tbs/src/mod/, owned by gs-mapedit) holds
edited copies of scene overlay tables, keyed "<overlay hex>:<symbol>". mod.c
is generated from it. For each overlay with overrides it has, per table kind,
a wrapper that calls the overlay's original getter (by its address in the
English build) and, when that returns an overridden table (by address),
returns the edited copy instead. All of a scene's own logic for choosing
tables (story flags, scene variants) still runs. The hook
(MOD_SCENE_LOADED in Scene_LoadOverlay, system/main_routine.c) points gOverlayArea's getters at
the wrappers for every scene using that overlay.

Addresses come from out/tbs-en, so mod.c applies to the English edition only;
other editions build with the hook doing nothing.
"""

import hashlib
import json
import os
import re
import struct

from . import layout
from .fsio import atomic_write
from .i18n import tr
from .scenes import KINDS, encode_rows

STEP_TRIGGER = 2

HEADER_TYPES = {
    "entrances": "const struct SceneEntrance *",
    "exits": "const u32 *",
    "placements": "const struct ActorPlacement *",
    "events": "const struct Trigger *",
    "regions": "const struct SceneExitRegion *",
}
# struct SceneEntryPoints' member for each of the editor's kinds.
ENTRY_FIELDS = {"entrances": "entrances", "exits": "exits", "placements": "actorPlacements",
                "events": "triggers", "regions": "regions"}


_PARSED = {}  # overrides.json path -> (mtime, parsed)


class DamagedFile(ValueError):
    """A file the editor saves can't be read; the message says what to do."""


class Overrides:
    def __init__(self, root):
        self.dir = os.path.join(root, layout.MOD)
        self.path = os.path.join(self.dir, "overrides.json")
        self.data = {"version": 1, "tables": {}}
        if os.path.exists(self.path):
            # Parsed once per version of the file. The tables' rows are shared:
            # readers copy them (sceneedit.copy_rows) and set() replaces them.
            stamp = os.stat(self.path).st_mtime_ns
            cached = _PARSED.get(self.path)
            if not cached or cached[0] != stamp:
                try:
                    with open(self.path, encoding="utf-8") as f:
                        parsed = json.load(f)
                    tables = parsed.get("tables", {}) if isinstance(parsed, dict) else None
                    if not isinstance(tables, dict) or not all(
                            isinstance(t, dict) and isinstance(t.get("rows"), list) and "kind" in t and "symbol" in t
                            for t in tables.values()):
                        raise ValueError("not an edits file")
                except ValueError as e:
                    raise DamagedFile(tr("The file that holds your people, door and event edits can't be read "
                                         "({file}). Use Undo if a recent save caused "
                                         "this, or restore it from your backup.",
                                         file=f"{layout.MOD}/overrides.json")) from e
                cached = _PARSED[self.path] = (stamp, parsed)
            self.data = {**cached[1], "tables": dict(cached[1].get("tables", {}))}

    @staticmethod
    def key(overlay, symbol):
        return f"{overlay:x}:{symbol}"

    def get(self, overlay, symbol):
        return self.data["tables"].get(self.key(overlay, symbol))

    def set(self, overlay, symbol, kind, rows):
        self.data["tables"][self.key(overlay, symbol)] = {
            "overlay": overlay, "symbol": symbol, "kind": kind, "rows": rows,
        }

    def remove(self, overlay, symbol):
        self.data["tables"].pop(self.key(overlay, symbol), None)

    def save(self):
        os.makedirs(self.dir, exist_ok=True)
        atomic_write(self.path, json.dumps(self.data, indent=1, sort_keys=True) + "\n")
        _PARSED.pop(self.path, None)


def validate_rows(kind, rows):
    """Raise ValueError unless the table ends the way the engine expects and
    every value fits, so a bad row can't reach overrides.json and stop every
    later save."""
    try:
        encode_rows(kind, rows)
    except (struct.error, KeyError, TypeError, ValueError) as e:
        raise ValueError(tr("a {kind} row holds a value the game can't store ({error})", kind=kind, error=e)) from None
    if kind == "exits":
        if not any(seg.get("scene") == 0x1FF for seg in rows if "raw" not in seg):
            raise ValueError(tr("exit table must end with the 0x1ff end marker"))
        for seg in rows:
            for ex in seg.get("exits", []):
                if not (1 <= ex["kind"] <= 0xFF and 0 <= ex["entrance"] <= 0xFF and 0 <= ex["scene"] <= 0x1FE):
                    raise ValueError(tr("bad exit {exit}", exit=ex))
        return
    end = {"entrances": ("entrance", -1), "placements": ("sprite", -1),
           "events": ("control", 0xFFFFFFFF), "regions": ("minX", -1)}.get(kind)
    if end and not any(int(r[end[0]]) == end[1] for r in rows):
        raise ValueError(tr("{kind} table must keep its end row ({field} = {value})",
                            kind=kind, field=end[0], value=end[1]))


# The hook, as ensure_hook adds it to a plain alchemy checkout. Off (no GSMOD)
# it compiles to nothing, so the game still builds byte-identical.
HOOK_H = """/* gs-mapedit's single hook into the engine.
   Without GSMOD the hook compiles to nothing, so the build still matches. */
#ifndef GSMOD_HOOK_H
#define GSMOD_HOOK_H
#include "mod_config.h"
#ifdef GSMOD
struct SceneEntryPoints;
void Mod_SceneLoaded(int scene, struct SceneEntryPoints *entries);
#define MOD_SCENE_LOADED(scene, entries) Mod_SceneLoaded((scene), (entries))
#else
#define MOD_SCENE_LOADED(scene, entries) ((void)0)
#endif
#endif
"""
HOOK_INCLUDE = '#include "../mod/mod_hook.h"\n'


def ensure_hook(root):
    """Put the mod's hook into the checkout if it isn't there: without it, the
    scene edits in mod.c are never linked or called. Does nothing when it is."""
    def hook(text):
        if layout.HOOK_CALL in text:
            return text
        if layout.HOOK_AFTER not in text:
            raise ValueError(tr("this version of the game source loads scenes differently; the editor needs updating for it"))
        text = text.replace(layout.HOOK_AFTER, layout.HOOK_AFTER + layout.HOOK_CALL, 1)
        last = list(re.finditer(r"^#include .*\n", text, re.M))[-1]
        return text[:last.end()] + HOOK_INCLUDE + text[last.end():]

    def objects(text):
        if layout.OBJECTS_ROWS in text:
            return text
        if layout.OBJECTS_AFTER not in text:
            raise ValueError(tr("this version of the game source lists its objects differently; the editor needs updating for it"))
        return text.replace(layout.OBJECTS_AFTER, layout.OBJECTS_AFTER + layout.OBJECTS_ROWS, 1)

    # Both are worked out before either is written, so a source this editor
    # can't hook is reported with nothing changed.
    changes = {}
    for rel, change in ((layout.HOOK_FILE, hook), (layout.OBJECTS, objects)):
        path = os.path.join(root, rel)
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
        new = change(text)
        if new != text:
            changes[path] = new
    for path, new in changes.items():
        atomic_write(path, new)
    mod_dir = os.path.join(root, layout.MOD)
    os.makedirs(mod_dir, exist_ok=True)
    path = os.path.join(mod_dir, "mod_hook.h")
    if not os.path.exists(path):
        atomic_write(path, HOOK_H)


def fingerprint(overlay, symbol):
    """What identifies a scene table across game-source versions: where it is
    and what the unmodified game holds there. Names change; these say whether
    an edit made to the old table still applies to the one found now."""
    return {"addr": overlay.tables[symbol]["addr"],
            "stock": hashlib.sha1(overlay.table_bytes(symbol)).hexdigest()[:16]}


def reconcile(overrides, scenes):
    """Match saved edits to the tables of the game as built now. A table renamed
    upstream follows its fingerprint; an edit whose table is gone, or whose
    original contents changed, is stale: it stays saved but isn't built into the
    game, since its rows hold script addresses from the old source. Returns
    the stale entries; changes `overrides` in memory only."""
    stale = []
    for key, t in list(overrides.data["tables"].items()):
        try:
            o = scenes.overlay(t["overlay"])
        except FileNotFoundError:
            stale.append(t)
            continue
        symbol, known = t["symbol"], t.get("fingerprint")
        if symbol not in o.tables and known:
            symbol = next((n for n, x in o.tables.items() if x["editable"] and x["kind"] == t["kind"]
                           and fingerprint(o, n)["stock"] == known["stock"] and x["addr"] == known["addr"]), None)
            if symbol:
                del overrides.data["tables"][key]
                t = dict(t, symbol=symbol)
                overrides.data["tables"][overrides.key(t["overlay"], symbol)] = t
                overrides.renamed = True
        if symbol not in o.tables or not o.tables[symbol]["editable"]:
            stale.append(t)
            continue
        now = fingerprint(o, symbol)
        if known and known["stock"] != now["stock"]:
            stale.append(t)
    return stale


# Play's "start at the place you're editing". The word below stays at its "none"
# value in every build: Play writes the place into a throwaway copy of the ROM
# (gsmap/playtest.py), and Export turns this code off altogether. When the Title
# scene loads in such a copy, its setup is swapped for one that starts a fresh game
# and leaves for that place by the game's own route, as the file screen does.
PLAYTEST_SYMBOL = "gModPlaytestTarget"
PLAYTEST_C = [
    "#define PLAYTEST_NONE 0xffffffff",
    f"volatile const u32 {PLAYTEST_SYMBOL} = PLAYTEST_NONE; /* scene | entrance << 16 */",
    "",
    "static s32 Mod_PlaytestStart(void) {",
    f"  u32 target = {PLAYTEST_SYMBOL};",
    "  MainRoutineWork_InitializeDefaults();",
    "  WindowColor_Apply(gMainRoutineWork.windowColor[0], gMainRoutineWork.windowColor[1]);",
    "  gMainRoutineWork.next = target & 0xffff;",
    "  gMainRoutineWork.entrance = target >> 16;",
    "  gFieldWork->exit = EXIT_KEEP_DESTINATION;",
    "  return 0;",
    "}",
    "",
]


def is_step_message(row):
    """A step trigger that shows a message rather than running a scene script."""
    return row["control"] & 0xF == STEP_TRIGGER and row["control"] != 0xFFFFFFFF and 0 < row["value"] < 0x10000


def step_message_functions(messages):
    """C for step messages. The game re-raises a step trigger on every frame the
    leader stands on the cell, and every step trigger of its own runs a script
    that deals with that; a bare message would show again the moment it closed,
    and the player could never walk off. So each runs through one function that
    stays quiet until the trigger has gone unraised for half a second. It keeps
    its frame count in gMainRoutineWork.unused, which no game code reads, because
    the mod's object is placed with no RAM of its own."""
    if not messages:
        return []
    lines = [
        "static void Mod_StepMessage(s32 message) {",
        "  u32 *lastSeen = (u32 *)gMainRoutineWork.unused;",
        "  u32 now = gVBlankCount;",
        "  u32 last = *lastSeen;",
        "  *lastSeen = now;",
        "  if (now - last < 30)",
        "    return;",
        "  Event_Start();",
        "  Event_SetMessageId(message);",
        "  Event_ShowMessageAndWait(-1, 0);",
        "  Event_End();",
        "  *lastSeen = gVBlankCount;",
        "}",
        "",
    ]
    for m in messages:
        lines.append(f"static void Mod_Step_{m}(s32 cell) {{ (void)cell; Mod_StepMessage({m}); }}")
    return lines + [""]


def generate(root, scenes, overrides):
    """Write mod.c and mod_config.h (and the hook, if the checkout hasn't got
    it yet). Returns a summary dict."""
    ensure_hook(root)
    stale = reconcile(overrides, scenes)
    tables = [t for t in overrides.data["tables"].values() if not any(t is x for x in stale)]
    # Note each table's fingerprint the first time it's seen.
    noted = getattr(overrides, "renamed", False)
    for t in tables:
        if "fingerprint" not in t:
            t["fingerprint"] = fingerprint(scenes.overlay(t["overlay"]), t["symbol"])
            noted = True
    if noted:
        overrides.save()
    by_overlay = {}
    for t in tables:
        by_overlay.setdefault(t["overlay"], []).append(t)

    lines = [
        "/* Generated by gs-mapedit from overrides.json. Do not edit by hand. */",
        '#include "mod_config.h"',
        "#ifdef GSMOD",
        *[f'#include "{name}"' for name in layout.MOD_INCLUDES],
        "",
        "typedef const void *(*ModGetter)(void);",
        "",
    ]
    step_messages = sorted({r["value"] for t in tables if t["kind"] == "events" for r in t["rows"] if is_step_message(r)})
    cases = []
    if by_overlay:
        lines.append("#ifdef TBS_EDITION_EN")
        lines += step_message_functions(step_messages)
    for ovl, ts in sorted(by_overlay.items()):
        o = scenes.overlay(ovl)
        for t in ts:
            data = encode_rows(t["kind"], t["rows"])
            words = [f"0x{w:08x}" for w in struct.unpack(f"<{len(data) // 4}I", data)]
            if t["kind"] == "events":
                for i, r in enumerate(t["rows"]):
                    if is_step_message(r):
                        words[i * 3 + 2] = f"(u32)Mod_Step_{r['value']}"
            lines.append(f"/* {t['symbol']} (overlay {ovl:#x}), {len(data)} bytes */")
            lines.append(f"static const u32 Mod_{ovl:x}_{t['symbol']}[] = {{")
            for i in range(0, len(words), 6):
                lines.append("  " + ", ".join(words[i:i + 6]) + ",")
            lines.append("};")
            lines.append("")
        assigns = []
        for kind in KINDS:
            kts = [t for t in ts if t["kind"] == kind]
            if not kts:
                continue
            getter = o.getters[kind]
            fn = f"Mod_{ovl:x}_Get_{kind}"
            lines.append(f"/* wraps {o.getter_name(kind) or hex(getter)} */")
            lines.append(f"static {HEADER_TYPES[kind]}{fn}(void) {{")
            lines.append(f"  const void *t = ((ModGetter)0x{getter:08x})();")
            for t in kts:
                addr = o.tables[t["symbol"]]["addr"]
                lines.append(f"  if (t == (const void *)0x{addr:08x}) /* {t['symbol']} */")
                lines.append(f"    return ({HEADER_TYPES[kind]})Mod_{ovl:x}_{t['symbol']};")
            lines.append(f"  return ({HEADER_TYPES[kind]})t;")
            lines.append("}")
            lines.append("")
            assigns.append(f"    entries->{ENTRY_FIELDS[kind]} = {fn};")
        ids = [s["id"] for s in scenes.scenes if s["overlay"] == ovl]
        cases.append((ovl, ids, assigns))

    playable = bool(overrides.data.get("playable"))
    if playable:
        if not by_overlay:
            lines.append("#ifdef TBS_EDITION_EN")
        lines += PLAYTEST_C
    lines.append("void Mod_SceneLoaded(int scene, struct SceneEntryPoints *entries) {")
    if playable:
        lines.append("  if (scene == (s32)&SceneId_Title && gModPlaytestTarget != PLAYTEST_NONE &&")
        lines.append("      gMainRoutineWork.entrance == TITLE_AFTER_RUN) /* as at power-on */")
        lines.append("    entries->initialize = Mod_PlaytestStart;")
    if cases:
        lines.append("  switch (scene) {")
        for ovl, ids, assigns in cases:
            for i in ids:
                lines.append(f"  case {i}:")
            lines.append(f"    /* overlay {ovl:#x} */")
            lines += assigns
            lines.append("    break;")
        lines.append("  }")
    lines.append("  (void)scene;")
    lines.append("  (void)entries;")
    lines.append("}")
    if by_overlay or playable:
        lines.append("#endif /* TBS_EDITION_EN */")
    lines.append("#endif /* GSMOD */")
    text = "\n".join(lines) + "\n"
    if by_overlay or playable:
        # Mod_SceneLoaded must exist in every edition; the EN-only block above
        # holds it, so give the other editions an empty one.
        text = text.replace(
            "#endif /* TBS_EDITION_EN */\n",
            "#else\nvoid Mod_SceneLoaded(int scene, struct SceneEntryPoints *entries) {\n"
            "  (void)scene;\n  (void)entries;\n}\n#endif /* TBS_EDITION_EN */\n",
        )
    mod_dir = overrides.dir
    atomic_write(os.path.join(mod_dir, "mod.c"), text)
    enabled = bool(tables) or playable
    atomic_write(os.path.join(mod_dir, "mod_config.h"),
                 "/* Generated by gs-mapedit. Defining GSMOD builds the editor's overrides into\n"
                 "   the ROM; leave it undefined for the build that matches the original. */\n"
                 "#ifndef GSMOD_CONFIG_H\n#define GSMOD_CONFIG_H\n"
                 + ("#define GSMOD 1\n" if enabled else "/* #define GSMOD 1 */\n")
                 + "#endif\n")
    return {"tables": len(tables), "overlays": len(by_overlay), "enabled": enabled,
            "stale": [t["symbol"] for t in stale]}
