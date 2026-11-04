"""Saving that can't leave a half-written mod behind.

atomic_write replaces a file in one step, so a crash or a full disk leaves the
old file or the new one, never part of one. transaction makes one user action,
which may touch a map, its chests, the scene tables and the text, all or
nothing: the first time a file is written its old contents go to a journal
folder, and any failure puts them back. If the editor dies part way, recover
finds the journal next time it starts and does the same.

A finished action's journal can be kept as history, which is what makes "Undo
last save" possible even for actions that save the moment you make them.
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
_current = threading.local()


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
            shutil.copy2(path, os.path.join(self.dir, name))
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

    def finish(self, history=None, label=None):
        if history and self.kept and not self.aborted:
            os.makedirs(history, exist_ok=True)
            with open(os.path.join(self.dir, "label.json"), "w", encoding="utf-8") as f:
                json.dump({"label": label or "your last change", "when": time.time()}, f)
            name = f"{time.time_ns()}"
            shutil.move(self.dir, os.path.join(history, name))
            for old in sorted(os.listdir(history), key=int)[:-HISTORY_KEPT]:
                shutil.rmtree(os.path.join(history, old), ignore_errors=True)
        else:
            shutil.rmtree(self.dir, ignore_errors=True)


def _restore(folder, kept):
    for path, name in kept.items():
        if name is None:
            with contextlib.suppress(FileNotFoundError):
                os.remove(path)
        else:
            shutil.copy2(os.path.join(folder, name), path + ".restoring")
            os.replace(path + ".restoring", path)


@contextlib.contextmanager
def transaction(root, history=None, label=None):
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
        txn.finish(history, label)
    finally:
        _current.txn = None


def last_saved(history):
    """{"label", "when"} of the newest undoable action, or None."""
    if not os.path.isdir(history):
        return None
    for name in sorted(os.listdir(history), key=int, reverse=True):
        path = os.path.join(history, name, "label.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return None


def undo_last(history):
    """Put back the files as they were before the newest action. Its label, or None."""
    if not os.path.isdir(history):
        return None
    for name in sorted(os.listdir(history), key=int, reverse=True):
        folder = os.path.join(history, name)
        with open(os.path.join(folder, "list.json"), encoding="utf-8") as f:
            kept = json.load(f)
        with open(os.path.join(folder, "label.json"), encoding="utf-8") as f:
            label = json.load(f)["label"]
        _restore(folder, kept)
        shutil.rmtree(folder, ignore_errors=True)
        return label
    return None


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
        with open(listing, encoding="utf-8") as f:
            kept = json.load(f)
        _restore(folder, kept)
    shutil.rmtree(folder, ignore_errors=True)
    return bool(kept)
