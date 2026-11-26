"""Bringing a player's copy of the game source (alchemy) to the version this
editor was tested with (setup.ALCHEMY_PIN), with their mod.

A copy the editor downloaded is a git clone sitting on the pinned commit, and
everything the player made is uncommitted changes in it. The update:

  1. saves all of it as one commit, under a backup ref
     (refs/gs-map-editor/before-update-<time>), without touching the
     player's files or index;
  2. fetches the new commit and moves the copy to it;
  3. applies the saved changes there with git's three-way merge (cherry-pick),
     which follows files upstream moved or renamed. The two lines the editor's
     hook adds to alchemy's own files are left out and put back afterwards
     (modgen.ensure_hook), and mod.c is written afresh (modgen.generate).
     A place's chests and stones (the `treasure_spot` rows of its map file)
     are carried by the editor itself: upstream renames those files and the
     labels in them, which git can't follow, so the rows are merged into the
     same place's file in the new version, found by its row in the map table.
     A copy from before alchemy's table-file maps (0240eeebad and older) has
     its changed map files converted instead (gsmap/legacy_maps.py), into the
     place's folder in the new version, again found by its map table row;
  4. builds the game and checks the editor can read the copy.

If any step fails (a change that can't be carried, a build that breaks), the
copy goes back exactly as it was, uncommitted changes and all, and the reason
is shown. The backup ref stays either way.

Only copies the editor could have made are offered an update: alchemy's own
repository, on no branch of its own, with no merge in progress, and older than
the pinned commit. Someone's own checkout, on a branch, is never moved.
"""

import glob
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time

from . import layout, legacy_maps, preflight
from .i18n import tr
from .setup import ALCHEMY_PIN, ALCHEMY_URL, GIT_LIMITS, RUNNING, SUPPORT, build_env

BACKUP_REFS = "refs/gs-map-editor/"
# The editor's own commits stay in this copy; they never go anywhere.
IDENTITY = {"GIT_AUTHOR_NAME": "GS Map Editor", "GIT_AUTHOR_EMAIL": "gs-map-editor@localhost",
            "GIT_COMMITTER_NAME": "GS Map Editor", "GIT_COMMITTER_EMAIL": "gs-map-editor@localhost"}


class Stop(Exception):
    """The update can't go on; the message says why, in plain words."""


def _git(root, *args, env=None, check=True, limits=False):
    cmd = (GIT_LIMITS if limits else ["git"]) + ["-C", root, *args]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace", env={**build_env(), **(env or {})})
    if check and p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, cmd, p.stdout, p.stderr)
    return p


def _out(root, *args, **kw):
    return _git(root, *args, **kw).stdout.strip()


def _known(root, sha):
    return _git(root, "cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode == 0


def _older(root, head, pin):
    """True when head is an ancestor of pin, False when not, None when pin
    isn't here yet (merge-base answers 128)."""
    code = _git(root, "merge-base", "--is-ancestor", head, pin, check=False).returncode
    return {0: True, 1: False}.get(code)


def _busy(git_dir):
    """A merge, cherry-pick or rebase someone left unfinished."""
    return any(os.path.exists(os.path.join(git_dir, n))
               for n in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply"))


def offer(root):
    """{"from", "to"} (short commits) when this copy can be brought to the
    pinned version; None when it's there already or isn't the editor's to move."""
    try:
        if not root:
            return None
        # The git folder, the commit, and "HEAD" when no branch is checked out.
        p = _git(root, "rev-parse", "--absolute-git-dir", "HEAD", "--symbolic-full-name", "HEAD", check=False)
        if p.returncode != 0:
            return None
        git_dir, head, branch = p.stdout.split("\n")[:3]
        if head == ALCHEMY_PIN or branch != "HEAD":
            return None
        url = _out(root, "remote", "get-url", "origin", check=False).rstrip("/")
        if url.removesuffix(".git") != ALCHEMY_URL or _busy(git_dir):
            return None
        # Once the pinned commit is here, whether it's newer is known; before
        # the first fetch it isn't, and the update finds out (and stops
        # harmlessly) if this copy is already past it.
        if _older(root, head, ALCHEMY_PIN) is False:
            return None
        return {"from": head[:10], "to": ALCHEMY_PIN[:10]}
    except (OSError, subprocess.CalledProcessError):
        return None


def _table_folders(text):
    """Each map table row's folder, in row order, from its comment: map/
    resources.s's `map ...  @ folder` rows, or resources.c's `{...}, // folder`."""
    rows = re.findall(r"^\tmap \w+,[^\n@]*@ ([a-z0-9_]+)", text, re.M)
    return rows or re.findall(r"^\s*\{[^\n]*\}, // ([a-z0-9_]+)", text, re.M)


def _new_folder(folder, old_rows, new_rows, maps_dir):
    """The folder in the new version holding the place the old version kept
    in `folder`: the one its map table rows name now (the rows keep their
    order: alchemy builds the same game), else one of the same name."""
    found = {new_rows[i] for i, f in enumerate(old_rows) if f == folder and i < len(new_rows)}
    if len(found) == 1:
        return found.pop()
    return folder if os.path.isdir(os.path.join(maps_dir, folder)) else None


def merge_rows(base, mine, theirs, end):
    """Theirs (the new version's rows), less what mine removed from base, plus
    what mine added, in order, ending with `end`."""
    kept = [r for r in theirs if r != end and (r in mine or r not in base)]
    return kept + [r for r in mine if r != end and r not in base and r not in kept] + [list(end)]


class Update:
    """The update as a background job, with the setup jobs' status()."""

    def __init__(self, root, on_done=None):
        """on_done: called when the job ends having changed files (moved to
        the new version, or there and back), so what was read can be dropped."""
        self.root, self.on_done = root, on_done
        self.name = tr("Updating the game source")
        self.log, self.done, self.ok, self.error, self.result = [], False, None, None, None
        self.dropped = 0  # log lines let go of; status()'s `since` counts them
        self.moved = self.cleared = self.bootstrapped = False
        self.lock = threading.Lock()
        threading.Thread(target=self._run, daemon=True).start()

    def say(self, line):
        with self.lock:
            self.log.append(line)
            if len(self.log) > 4000:
                del self.log[:1000]
                self.dropped += 1000

    def status(self, since=0):
        with self.lock:
            log = self.log[max(0, since - self.dropped):]
            end = self.dropped + len(self.log)
        return {"name": self.name, "done": self.done, "ok": self.ok, "error": self.error, "result": self.result,
                "log": log, "next": end}

    # ---- the steps ------------------------------------------------------------

    def _run(self):
        root = self.root
        try:
            if offer(root) is None:
                raise Stop(tr("This copy of the game source isn't one the editor can update."))
            self.old = _out(root, "rev-parse", "HEAD")
            self.old_compilers = self._compilers(self.old)
            self.gcc_head = _out(os.path.join(root, "alchemy-gcc"), "rev-parse", "HEAD", check=False)
            self.maps = self._read_maps()
            self.markers = {} if self.maps is not None else self._read_markers()
            self.tilesets = self._read_tilesets()
            self.saved, self.carried = self._save()
        except Stop as e:
            return self._finish(False, str(e))
        except Exception as e:  # noqa: BLE001  nothing has changed yet: just say so
            return self._finish(False, tr("Couldn't start the update ({detail}). Nothing was changed.",
                                          detail=f"{type(e).__name__}: {e}"))
        try:
            self._fetch()
            self._move()
            self._rebuild()
        except Exception as e:  # noqa: BLE001  whatever it was, the copy goes back as it was
            reason = str(e) if isinstance(e, Stop) else f"{type(e).__name__}: {e}"
            if self.moved:
                self.say(tr("Putting your copy back as it was…"))
                try:
                    self._put_back()
                except Exception as e2:  # noqa: BLE001
                    return self._finish(False, tr(
                        "The update stopped ({reason}), and putting your copy back failed too ({detail}). "
                        "Your changes are safe in the backup {ref}; ask for help before editing.",
                        reason=reason, detail=f"{type(e2).__name__}: {e2}", ref=self.ref))
            return self._finish(False, tr("The update stopped, and your copy is as it was: {reason}", reason=reason))
        self._retire_history()
        self.result = {"from": self.old[:10], "to": ALCHEMY_PIN[:10], "backup": self.ref}
        self._finish(True, None)

    def _finish(self, ok, error):
        if error:
            self.say(error)
        if self.moved and self.on_done:
            try:
                self.on_done()
            except Exception as e:  # noqa: BLE001  the outcome stands; the editor reads afresh when reopened
                self.say(f"{type(e).__name__}: {e}")
        self.ok, self.error, self.done = ok, error, True

    def _run_cmd(self, cmd, cwd=None):
        """A long command, its output in the log; raises on failure."""
        self.say("$ " + " ".join(cmd))
        p = subprocess.Popen(cmd, cwd=cwd or self.root, env=build_env(), stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, errors="replace", bufsize=1, start_new_session=True)
        RUNNING.add(p)
        try:
            for line in p.stdout:
                self.say(line.rstrip("\n"))
            if p.wait() != 0:
                raise Stop(tr("{command} failed.", command=" ".join(cmd[:3])))
        finally:
            RUNNING.discard(p)

    def _compilers(self, commit):
        """The compiler submodule's commit at `commit`, or None."""
        line = _out(self.root, "ls-tree", commit, "alchemy-gcc", check=False)
        return line.split()[2] if line else None

    def _save(self):
        """Commit everything the player has (their files and index untouched):
        (the whole saved state, the same less what the editor redoes)."""
        root = self.root
        self.say(tr("Saving your changes as a backup…"))
        fd, index = tempfile.mkstemp(prefix="gsmap-index-")
        os.close(fd)
        try:
            env = {"GIT_INDEX_FILE": index, **IDENTITY}
            _git(root, "read-tree", "HEAD", env=env)
            _git(root, "add", "-A", env=env)
            tree = _out(root, "write-tree", env=env)
            saved = _out(root, "commit-tree", tree, "-p", "HEAD", "-m", "Your changes, saved before updating", env=env)
            # The hook's two lines go back by the editor, into wherever the new
            # version keeps those files.
            # The compilers are the new version's own, never carried over.
            redone = [p for p in (layout.HOOK_FILE, layout.object_list(root)[0], "alchemy-gcc") if p]
            redone += [rel for rel, _, _ in self.markers.values()]  # carried by _carry_markers
            redone += [f"{layout.MAPS}/{folder}/{name}" for folder, files in (self.maps or {}).items()
                       for name in files]  # carried by _carry_maps
            _git(root, "reset", "-q", "HEAD", "--", *redone, env=env, check=False)
            carried = _out(root, "commit-tree", _out(root, "write-tree", env=env), "-p", "HEAD",
                           "-m", "Your changes, to carry to the new version", env=env)
        finally:
            os.unlink(index)
        self.ref = BACKUP_REFS + "before-update-" + time.strftime("%Y%m%d-%H%M%S")
        _git(root, "update-ref", self.ref, saved)
        self.say(tr("Saved as {ref}.", ref=self.ref))
        return saved, carried

    def _read_markers(self):
        """{map table row: (map file, rows as the old version has them, rows
        as the player has them)} for each place whose chests or stones changed."""
        from .project import Markers, Project
        root, out = self.root, {}
        changed = set(_out(root, "diff", "--name-only", "HEAD").split("\n"))
        if not any(os.path.basename(rel) in layout.MAP_FILES for rel in changed):
            return out
        project = Project(root)
        for info in project.maps.values():
            rel = os.path.relpath(info.path, root)
            if rel not in changed or not info.resources:
                continue
            fd, base = tempfile.mkstemp(suffix=".s")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(_git(root, "show", f"HEAD:{rel}").stdout)
                out[info.resources["row"]] = (rel, Markers(base).rows, Markers(info.path).rows)
            finally:
                os.unlink(base)
        return out

    def _carry_markers(self):
        """Each place's chests and stones into its file in the new version:
        the new version's rows, less the ones the player removed, plus the
        ones they added."""
        if not self.markers:
            return
        from .project import Markers, Project
        self.say(tr("Carrying your chests and stones over…"))
        by_row = {info.resources["row"]: info for info in Project(self.root).maps.values() if info.resources}
        for row, (rel, base, mine) in self.markers.items():
            info = by_row.get(row)
            if info is None:
                raise Stop(tr("the place in {file} isn't in the new version.", file=rel))
            mt = Markers(info.path)
            mt.rows = merge_rows(base, mine, mt.rows, Markers.END)
            mt.save()

    def _read_tilesets(self):
        """The notes on places with a tile set of their own (mod/tilesets.json,
        gsmap/tileset.py), by gMaps row: each is keyed by its place's name and
        names its block family by a fingerprint of a cell table, and both can
        change in a new version (places were numbers before 2026-11-13; the
        table is cell_tiles.tsv since 2026-11-25). [(row, key, note, family's
        row)]; a note on no place keeps its key, as it was."""
        from . import tileset
        from .project import Project
        meta = tileset.load_meta(self.root)
        if not meta:
            return []
        project = Project(self.root)
        rows_by_hash = {}
        for info in project.maps.values():
            if info.resources and os.path.exists(info.cells_path()):
                rows_by_hash.setdefault(tileset.table_hash(info.cells_path()), info.resources["row"])
        out = []
        for key, note in meta.items():
            info = project.maps.get(key)
            known = info is not None and info.resources and isinstance(note, dict)
            out.append((info.resources["row"] if known else None, key, note,
                        rows_by_hash.get(note.get("family")) if known else None))
        return out

    def _carry_tilesets(self):
        """Each note under its place's name in the new version, its family's
        fingerprint taken from the same table there."""
        if not self.tilesets:
            return
        from . import tileset
        from .project import Project
        by_row = {info.resources["row"]: info for info in Project(self.root).maps.values() if info.resources}
        meta = {}
        for row, key, note, family_row in self.tilesets:
            info, family = by_row.get(row), by_row.get(family_row)
            if info is None:
                meta[key] = note
                continue
            note = dict(note)
            if family is not None and "family" in note:
                note["family"] = tileset.table_hash(family.cells_path())
            meta[info.number] = note
        tileset.save_meta(self.root, meta)

    def _read_maps(self):
        """None for a copy whose maps are table files already. Otherwise
        {folder: {file name: (the old version's text, the player's)}} for each
        map file in the old layout that the player changed, with
        self.old_rows, each map table row's folder, to find the place again."""
        root = self.root
        tracked = _out(root, "ls-files", "-z", "--", layout.MAPS).split("\0")
        if not any(legacy_maps.OLD_GRID.match(os.path.basename(rel)) for rel in tracked):
            return None
        self.old_rows = _table_folders(_git(root, "show", f"HEAD:{layout.map_table(root)}", check=False).stdout)
        if not self.old_rows:
            self.old_rows = self._rows_by_project()
        out = {}
        changed = _out(root, "diff", "--name-only", "-z", "HEAD", "--", layout.MAPS).split("\0")
        changed += _out(root, "ls-files", "--others", "--exclude-standard", "-z", "--", layout.MAPS).split("\0")
        for rel in changed:
            parts = os.path.relpath(rel, layout.MAPS).split(os.sep) if rel else []
            if len(parts) != 2 or not legacy_maps.is_old_file(parts[1]):
                continue
            base = _git(root, "show", f"HEAD:{rel}", check=False)
            path = os.path.join(root, rel)
            mine = open(path, encoding="utf-8").read() if os.path.exists(path) else None
            out.setdefault(parts[0], {})[parts[1]] = (base.stdout if base.returncode == 0 else None, mine)
        return out

    def _rows_by_project(self):
        """Each map table row's folder as the editor reads the copy: for a
        table whose rows don't name their folders (map/maps.c in copies as
        old as 5ca23b1fe1, whose folders are numbered)."""
        from .project import Project
        by_row = {}
        for info in Project(self.root).maps.values():
            for res in filter(None, [info.resources] + info.alternates):
                by_row[res["row"]] = os.path.basename(info.folder)
        return [by_row.get(i) for i in range(max(by_row) + 1)] if by_row else []

    def _carry_maps(self):
        """Each changed old-layout map file into its place's table files in the
        new version: only the tables the player's change touches, and only
        where the new version still has what the old one had there, else the
        update stops. Chests are merged row by row, as _carry_markers does."""
        if not self.maps:
            return
        root = self.root
        self.say(tr("Carrying your map changes over to the new map files…"))
        with open(os.path.join(root, layout.map_table(root)), encoding="utf-8") as f:
            new_rows = _table_folders(f.read())
        for folder, files in self.maps.items():
            target = _new_folder(folder, self.old_rows, new_rows, os.path.join(root, layout.MAPS))
            if target is None:
                raise Stop(tr("the place in {file} isn't in the new version.", file=f"{layout.MAPS}/{folder}"))
            here = os.path.join(root, layout.MAPS, target)
            for name, (base, mine) in files.items():
                rel = f"{layout.MAPS}/{folder}/{name}"
                if base is None or mine is None:
                    raise Stop(tr("your mod adds or removes {file}, which the new version keeps differently.", file=rel))
                try:
                    before, after = legacy_maps.convert(name, base), legacy_maps.convert(name, mine)
                except ValueError:
                    raise Stop(tr("{file} differs by language edition, so your changes to it can't be carried "
                                  "over automatically.", file=rel)) from None
                for table, text in after.items():
                    path = os.path.join(here, table)
                    have = open(path, encoding="utf-8").read() if os.path.exists(path) else None
                    if table == "spots.tsv":  # each edition's chests merged, as _carry_markers does
                        theirs, base_rows = legacy_maps.read_spots(have), legacy_maps.read_spots(before[table])
                        mine_rows = legacy_maps.read_spots(text)
                        text = legacy_maps.spots_table({e: merge_rows(base_rows[e], mine_rows[e], theirs[e], [])[:-1]
                                                        for e in legacy_maps.EDITIONS})
                    elif text == before.get(table):
                        continue  # a table this change didn't touch
                    elif have != before.get(table):
                        raise Stop(tr("the new version changed the same parts of {files} that your mod changed, so "
                                      "they can't be combined automatically.", files=rel))
                    if text is None:
                        if have is not None:
                            os.remove(path)
                    elif text != have:
                        with open(path, "w", encoding="utf-8", newline="") as f:
                            f.write(text)

    def _fetch(self):
        root = self.root
        if not _known(root, ALCHEMY_PIN):
            self.say(tr("Downloading the new version…"))
            p = _git(root, "fetch", "-q", "origin", ALCHEMY_PIN, check=False, limits=True)
            if p.returncode != 0 or not _known(root, ALCHEMY_PIN):
                p = _git(root, "fetch", "-q", "origin", check=False, limits=True)
            if not _known(root, ALCHEMY_PIN):
                raise Stop(tr("Couldn't download the new version. Check your internet connection and try again."))
        if not _older(root, self.old, ALCHEMY_PIN):
            raise Stop(tr("Your copy is already newer than the version this editor was tested with."))

    def _move(self):
        root = self.root
        # Every file the player has is in the saved commit (checked here), so
        # the working tree can be made the old version's.
        saved = set(_out(root, "ls-tree", "-r", "-z", "--name-only", self.saved).split("\0"))
        for rel in _out(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0"):
            if rel and rel not in saved:
                raise Stop(tr("{file} couldn't be saved in the backup.", file=rel))
        self.say(tr("Moving to the new version…"))
        self.moved = True  # from here on, a stop puts the copy back
        _git(root, "reset", "-q", "--hard")
        _git(root, "clean", "-fdq")
        _git(root, "checkout", "-q", "--detach", ALCHEMY_PIN)
        self._run_cmd(GIT_LIMITS + ["-C", root, "submodule", "update", "--init", "--recursive", "alchemy-gcc"])
        self.say(tr("Carrying your changes over…"))
        p = _git(root, "cherry-pick", "--no-commit", self.carried, env=IDENTITY, check=False)
        if p.returncode != 0:
            clashes = _out(root, "diff", "--name-only", "--diff-filter=U", check=False).split()
            _git(root, "cherry-pick", "--abort", check=False)
            if clashes:
                raise Stop(tr("the new version changed the same parts of {files} that your mod changed, so "
                              "they can't be combined automatically.", files=", ".join(clashes[:5])))
            raise Stop(tr("your changes couldn't be applied to the new version ({detail}).",
                          detail=(p.stderr or p.stdout).strip()[-300:]))
        _git(root, "reset", "-q")  # as before: the changes uncommitted, nothing staged
        self._carry_markers()
        self._carry_maps()
        self._carry_tilesets()

    def _rebuild(self):
        root = self.root
        from .modgen import Overrides, ensure_hook, generate
        from .scenes import Scenes
        mod = os.path.join(root, layout.MOD)
        if os.path.exists(os.path.join(mod, "overrides.json")) or os.path.exists(os.path.join(mod, "mod.c")):
            self.say(tr("Putting the editor's hook back and writing mod.c…"))
            ensure_hook(root)
            # The scene overlays' tables keep their places and contents across
            # versions (alchemy builds the same game), so the last build's
            # overlays still say where they are; generate() matches renamed ones.
            generate(root, Scenes(root), Overrides(root))
        # Build state from the old version that would confuse the new one.
        self.cleared = True
        self._clear_build_state()
        if self._compilers(ALCHEMY_PIN) != self.old_compilers:
            self.say(tr("The new version has new compilers: building them (several minutes)…"))
            self.bootstrapped = True
            self._run_cmd(["make", "bootstrap"])
        self.say(tr("Building the game with your mod…"))
        self._run_cmd(["make", "-j4", "tbs-en"])
        problems = preflight.check(root)
        if problems:
            raise Stop(str(problems[0]))

    def _put_back(self):
        """The copy exactly as it was: the old commit, every file as the player
        had it, nothing staged, and a build that works."""
        root = self.root
        _git(root, "cherry-pick", "--abort", check=False)
        _git(root, "reset", "-q", "--hard")
        _git(root, "clean", "-fdq")
        _git(root, "checkout", "-q", "--detach", self.old)
        _git(root, "read-tree", "-u", "--reset", self.saved)
        _git(root, "reset", "-q", self.old)
        self._run_cmd(GIT_LIMITS + ["-C", root, "submodule", "update", "--init", "--recursive", "alchemy-gcc"])
        if self.gcc_head:  # where the player's compiler source was, if not where the old version says
            _git(os.path.join(root, "alchemy-gcc"), "checkout", "-q", "--detach", self.gcc_head, check=False)
        # Only what the update built for the new version needs building again.
        if self.cleared:
            self._clear_build_state()
        if self.bootstrapped:
            self._run_cmd(["make", "bootstrap"])
        self._run_cmd(["make", "-j4", "tbs-en"])

    def _clear_build_state(self):
        root = self.root
        for path in glob.glob(os.path.join(root, "out", "*", "deps.mk")) + glob.glob(os.path.join(root, "out", "*", "objects.mk")):
            os.remove(path)
        shutil.rmtree(os.path.join(root, "tools", "out", "obj"), ignore_errors=True)
        for path in glob.glob(os.path.join(root, "tools", "out", "ags-*")):
            os.remove(path)

    def _retire_history(self):
        """Undo history names files as the old version laid them out: undoing
        one now would put an old file back. It's moved aside, not deleted."""
        import hashlib
        key = hashlib.sha1(os.path.abspath(self.root).encode()).hexdigest()[:12]
        history = os.path.join(SUPPORT, "history", key)
        if os.path.isdir(history):
            os.replace(history, history + "-before-update-" + time.strftime("%Y%m%d-%H%M%S"))
