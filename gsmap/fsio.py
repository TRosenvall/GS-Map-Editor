"""Saving that can't leave a half-written mod behind.

atomic_write replaces a file in one step, so a crash or a full disk leaves the
old file or the new one, never part of one. transaction makes one user action,
which may touch a map, its chests, the scene tables and the text, all or
nothing: the first time a file is written its old contents go to a journal
folder, and any failure puts them back. If the editor dies part way, recover
finds the journal next time it starts and does the same.

A finished action's journal can be kept as history, which is what makes Undo
possible even for actions that save the moment you make them. Undoing keeps
what it replaced under history/redo, so Redo can put it back; a new action
clears that, as any undo does.
"""

import contextlib
import json
import os
import shutil
import tempfile
import threading
import time

JOURNAL = ".gsmap-journal"
HISTORY_KEPT = 30
REDO = "redo"
_current = threading.local()


def _copy(source, target):
    """Contents and permissions, nothing else. The copy gets today's date, so a
    build sees a file put back as changed, and it doesn't inherit a Finder lock,
    which would leave the journal impossible to clear."""
    shutil.copyfile(source, target)
    shutil.copymode(source, target)


def _same(path, other):
    try:
        with open(path, "rb") as a, open(other, "rb") as b:
            return a.read() == b.read()
    except OSError:
        return False


def _remove_tree(folder):
    """Delete a journal or history folder, clearing locks older versions copied in."""
    shutil.rmtree(folder, ignore_errors=True)
    if not os.path.exists(folder):
        return
    for base, _, files in os.walk(folder):
        for name in files:
            with contextlib.suppress(OSError, AttributeError):
                os.chflags(os.path.join(base, name), 0)
    shutil.rmtree(folder, ignore_errors=True)


def _entries(history):
    """History folders, oldest first. Finder's .DS_Store and the like aren't ours."""
    try:
        return sorted((n for n in os.listdir(history) if n.isdigit()), key=int)
    except OSError:
        return []


def atomic_write(path, data):
    """Replace path with data (str or bytes), keeping its permissions."""
    txn = getattr(_current, "txn", None)
    if txn is not None:
        txn.keep(path)
    if isinstance(data, str):
        data = data.encode("utf-8")
    folder = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".tmp-", suffix=os.path.basename(path))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(path):
            shutil.copymode(path, tmp)
        else:
            os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise


def remove(path):
    """Delete a file, in a way a transaction can undo."""
    txn = getattr(_current, "txn", None)
    if txn is not None:
        txn.keep(path)
    with contextlib.suppress(FileNotFoundError):
        os.remove(path)


class _Transaction:
    def __init__(self, root):
        self.root = root
        self.dir = os.path.join(root, JOURNAL)
        self.kept = {}
        self.aborted = False

    def keep(self, path):
        path = os.path.abspath(path)
        if path in self.kept:
            return
        os.makedirs(self.dir, exist_ok=True)
        name = None
        if os.path.exists(path):
            name = str(len(self.kept))
            _copy(path, os.path.join(self.dir, name))
        self.kept[path] = name
        # The list goes down after its copy, so everything it names exists.
        tmp = os.path.join(self.dir, "list.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.kept, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, os.path.join(self.dir, "list.json"))

    def undo(self):
        _restore(self.dir, self.kept)

    def finish(self, history=None, label=None, where=None):
        if history and self.kept and not self.aborted:
            # The action has already happened. If its history can't be kept it
            # just can't be undone; that mustn't look like the save failed.
            try:
                os.makedirs(history, exist_ok=True)
                _remove_tree(os.path.join(history, REDO))  # a new change: nothing to redo
                with open(os.path.join(self.dir, "label.json"), "w", encoding="utf-8") as f:
                    json.dump({"label": label or "your last change", "when": time.time(), "where": where}, f)
                name = f"{time.time_ns()}"
                shutil.move(self.dir, os.path.join(history, name))
                for old in _entries(history)[:-HISTORY_KEPT]:
                    _remove_tree(os.path.join(history, old))
            except OSError:
                pass
        _remove_tree(self.dir)


def _restore(folder, kept):
    """Put files back. A file already right is left alone (it may be locked, and
    a build needn't redo it); every other file is tried before a failure is raised."""
    failure = None
    for path, name in kept.items():
        try:
            if name is None:
                with contextlib.suppress(FileNotFoundError):
                    os.remove(path)
            elif not _same(path, os.path.join(folder, name)):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                _copy(os.path.join(folder, name), path + ".restoring")
                os.replace(path + ".restoring", path)
        except OSError as e:
            failure = failure or e
            with contextlib.suppress(OSError):
                os.remove(path + ".restoring")
    if failure:
        raise failure


@contextlib.contextmanager
def transaction(root, history=None, label=None, where=None):
    """All the writes in this block land together, or none do. A failure means
    an exception leaving the block, or abort() from inside it. With `history`,
    a finished action's old contents are kept there for undo_last."""
    txn = _Transaction(root)
    _current.txn = txn
    try:
        yield txn
    except BaseException:
        txn.undo()
        txn.aborted = True
        txn.finish()
        raise
    else:
        if txn.aborted:
            txn.undo()
        txn.finish(history, label, where)
    finally:
        _current.txn = None


def last_saved(history):
    """{"label", "when"} of the newest undoable action, or None."""
    for name in reversed(_entries(history)):
        entry = _read_entry(os.path.join(history, name))
        if entry:
            return entry[1]
    return None


def _read_kept(folder):
    """A journal's list of files: {absolute path: copy's name, or None}. ValueError
    if it isn't one, since acting on a damaged list could overwrite anything."""
    with open(os.path.join(folder, "list.json"), encoding="utf-8") as f:
        kept = json.load(f)
    if not isinstance(kept, dict) or not all(
            os.path.isabs(path) and (name is None or (isinstance(name, str) and name.isdigit()))
            for path, name in kept.items()):
        raise ValueError("not a list of kept files")
    return kept


def _read_entry(folder):
    """(files kept, label) of a history entry, or None if it's incomplete."""
    try:
        kept = _read_kept(folder)
        with open(os.path.join(folder, "label.json"), encoding="utf-8") as f:
            label = json.load(f)
    except (OSError, ValueError):
        return None
    if not all(name is None or os.path.exists(os.path.join(folder, name)) for name in kept.values()):
        return None
    return (kept, label) if isinstance(label, dict) and isinstance(label.get("label"), str) else None


def _snapshot(paths, folder, label):
    """Keep the files at `paths` as they are now (None for a missing one) in
    `folder`, as a history entry with `label`, written whole or not at all."""
    tmp = folder + ".tmp"
    _remove_tree(tmp)
    os.makedirs(tmp)
    kept = {}
    for i, path in enumerate(paths):
        if os.path.exists(path):
            _copy(path, os.path.join(tmp, str(i)))
            kept[path] = str(i)
        else:
            kept[path] = None
    with open(os.path.join(tmp, "list.json"), "w", encoding="utf-8") as f:
        json.dump(kept, f)
    with open(os.path.join(tmp, "label.json"), "w", encoding="utf-8") as f:
        json.dump(label, f)
    os.replace(tmp, folder)


def _step(history, source, target, root):
    """Put back the newest entry of `source`, first keeping what it replaces as
    the newest entry of `target`. Its label, or None when there is none."""
    for name in reversed(_entries(source)):
        folder = os.path.join(source, name)
        entry = _read_entry(folder)
        if entry is None:  # cut short by a crash: nothing it could put back
            _remove_tree(folder)
            continue
        os.makedirs(target, exist_ok=True)
        _snapshot(list(entry[0]), os.path.join(target, f"{time.time_ns()}"), dict(entry[1], when=time.time()))
        journal = os.path.join(root, JOURNAL) if root else None
        if journal:
            # With root, a copy goes in the journal first, so a crash part way is
            # finished by recover the next time the editor starts, instead of
            # leaving mixed files.
            _remove_tree(journal)
            tmp = journal + ".tmp"
            _remove_tree(tmp)
            shutil.copytree(folder, tmp)
            os.replace(tmp, journal)  # all there, or not there
        _restore(folder, entry[0])
        _remove_tree(folder)
        if journal:
            _remove_tree(journal)
        for old in _entries(target)[:-HISTORY_KEPT]:
            _remove_tree(os.path.join(target, old))
        return entry[1]["label"]
    return None


def undo_last(history, root=None):
    """Put back the files as they were before the newest action, keeping what
    it replaces for redo_last. Its label, or None."""
    return _step(history, history, os.path.join(history, REDO), root)


def redo_last(history, root=None):
    """Do again the action undo_last last took back. Its label, or None."""
    return _step(history, os.path.join(history, REDO), history, root)


def next_redo(history):
    """{"label", "when", "where"} of what Redo would do, or None."""
    return last_saved(os.path.join(history, REDO))


def abort():
    """The action failed and is reporting it: undo the block's writes when it ends."""
    txn = getattr(_current, "txn", None)
    if txn is not None:
        txn.aborted = True


def recover(root):
    """Finish undoing an action the editor died in the middle of. True if it did."""
    folder = os.path.join(root, JOURNAL)
    listing = os.path.join(folder, "list.json")
    if not os.path.isdir(folder):
        return False
    kept = {}
    if os.path.exists(listing):
        try:
            kept = _read_kept(folder)
            _restore(folder, kept)
        except (OSError, ValueError):
            # Can't finish it. Starting anyway beats never starting, and the
            # journal is moved aside rather than lost.
            with contextlib.suppress(OSError):
                os.replace(folder, f"{folder}-unfinished-{time.time_ns()}")
            return False
    _remove_tree(folder)
    return bool(kept)
