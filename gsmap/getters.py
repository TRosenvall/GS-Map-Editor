"""Which scene tables a scene can actually load.

One overlay can serve many rooms, and its tables reuse cell codes: chest code
100 is a different chest in each of Fuchin Falls Cave's rooms. Each overlay's
getter function (ImilFuchinFalls_GetTriggers) picks the table, in C:

    if (sceneId == (s32)&SceneId_FuchinFallsCaveZephyr) {
      return gImilFuchinFalls_ZephyrRoomTriggers;
    }
    if (GameFlag_Get(FLAG_KALAY_REACHED) != 0) {
      return gVale_TriggersAfterKalay;
    }
    return gVale_Triggers;

This walks that source for one scene. A test of the scene id is decided; any
other test (a story flag, the entrance) could go either way, so both sides
count, which is what makes them that scene's story stages. A getter this can't
follow gets every table it names; with no source, every table of the kind.
"""

import re

from .doors import _scan, _scene_files, _source_text

_SCENE_TEST = re.compile(r"^\(*\s*(?:\w+|gMainRoutineWork\.next)\s*(==|!=)\s*\(s32\)\s*&\s*SceneId_(\w+)\s*\)*$")


def _matching(text, start, opening, closing):
    """Index just past the bracket matching text[start]."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == opening:
            depth += 1
        elif text[i] == closing:
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError("unbalanced source")


def _strip_comments(text):
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


def _decide(condition, scene_name):
    """True or False when a condition depends only on the scene, else None."""
    condition = condition.strip()
    parts = [p for p in re.split(r"\|\|", condition)]
    if len(parts) > 1:
        results = [_decide(p, scene_name) for p in parts]
        if True in results:
            return True
        return False if all(r is False for r in results) else None
    parts = [p for p in re.split(r"&&", condition)]
    if len(parts) > 1:
        results = [_decide(p, scene_name) for p in parts]
        if False in results:
            return False
        return True if all(r is True for r in results) else None
    m = _SCENE_TEST.match(condition)
    if not m:
        return None
    same = m.group(2) == scene_name
    return same if m.group(1) == "==" else not same


class _CantFollow(Exception):
    pass


def _walk(text, pos, end, scene_name, out):
    """Follow statements in text[pos:end]; True once control can't get past them."""
    while True:
        while pos < end and text[pos] in " \t\r\n;":
            pos += 1
        if pos >= end:
            return False
        done, pos = _statement(text, pos, scene_name, out)
        if done:
            return True


def _statement(text, pos, scene_name, out):
    """Follow one statement: (does it always return?, position after it)."""
    if text[pos] == "{":
        close = _matching(text, pos, "{", "}")
        return _walk(text, pos + 1, close - 1, scene_name, out), close
    m = re.compile(r"(if|return|switch|for|while|do)\b").match(text, pos)
    if not m:
        return False, text.index(";", pos) + 1
    word = m.group(1)
    if word == "return":
        semi = text.index(";", pos)
        names = re.findall(r"\bg\w+", text[pos + 6:semi])
        if len(names) != 1:
            raise _CantFollow()
        out.append(names[0])
        return True, semi + 1
    if word != "if":
        raise _CantFollow()
    open_paren = text.index("(", pos)
    close = _matching(text, open_paren, "(", ")")
    verdict = _decide(text[open_paren + 1:close - 1], scene_name)
    pos = close
    while text[pos] in " \t\r\n":
        pos += 1
    taken = [] if verdict is False else out
    done_then, pos = _statement(text, pos, scene_name, taken)
    after = pos
    while after < len(text) and text[after] in " \t\r\n":
        after += 1
    done_else = False
    if text.startswith("else", after) and not re.match(r"\w", text[after + 4:after + 5]):
        pos = after + 4
        while text[pos] in " \t\r\n":
            pos += 1
        taken_else = [] if verdict is True else out
        done_else, pos = _statement(text, pos, scene_name, taken_else)
    if verdict is True:
        return done_then, pos
    if verdict is False:
        return done_else, pos
    return done_then and done_else, pos


def tables_for_scene(tbs, overlay, kind, scene_name):
    """Table names of `kind` the scene can load, or None when that can't be told."""
    getter = overlay.getter_name(kind)
    if not getter:
        return None
    wanted = {n for n, t in overlay.tables.items() if t["kind"] == kind}
    for path in _scene_files(tbs, overlay.tables):
        text = _source_text(path)
        m = re.search(rf"^[\w \*]*\b{re.escape(getter)}\(void\)\s*\{{", text, re.M)
        if not m:
            continue
        start = m.end() - 1
        body_end = _matching(text, start, "{", "}")
        body = _strip_comments(text[start:body_end])
        out = []
        try:
            _walk(body, 1, len(body) - 1, scene_name or "", out)
        except (_CantFollow, ValueError):
            out = re.findall(r"\bg\w+", body)
        found = [n for n in out if n in wanted]
        if found:
            return sorted(set(found), key=lambda n: overlay.tables[n]["addr"])
        return None
    return None
