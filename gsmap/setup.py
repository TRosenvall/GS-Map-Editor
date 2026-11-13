"""First-run setup for the desktop app: what's needed to build the game, in
plain words, and jobs that put each piece in place.

Steps, in order (each is checked, never assumed):
  1. Apple's command line tools: clang, make, git (macOS only).
  2. Homebrew and the packages alchemy's INSTALL.md lists for macOS, or on
     Linux and WSL the apt packages it lists (which need sudo, so the page
     gives the command rather than running it).
  3. The game source: an existing alchemy checkout, or a fresh download at
     the commit this editor was tested with.
  4. alchemy's compilers (`make bootstrap`, once, a few minutes).
  5. A first build of the English Broken Seal (`make tbs-en`).

Long steps run as background jobs whose output the setup page shows live.
"""

import atexit
import contextlib
import json
import os
import shutil
import signal
import subprocess
import tempfile
import threading

from . import host, layout, preflight
from .fsio import atomic_write
from .i18n import tr

APP_NAME = host.APP_NAME
SUPPORT = host.SUPPORT
SETTINGS = os.path.join(SUPPORT, "settings.json")
# Build folders have no spaces: alchemy's compiler Makefile (like most
# Makefiles) breaks on paths with spaces.
DEFAULT_WORKSPACE = host.WORKSPACE
# Exports and patched games go where the person's own file browser shows them
# (on Windows, Documents rather than inside Ubuntu).
EXPORTS = os.path.join(host.SHARED, "Exports")
CACHE = host.CACHE
if " " in CACHE:  # builds run from here too; macOS's per-user temporary folder has no spaces
    CACHE = os.path.join(tempfile.gettempdir(), "GSMapEditorCache")
ALCHEMY_URL = "https://github.com/PascalPixel/alchemy"
# The alchemy commit this editor was last tested against (round trip,
# render-all, build). Newer commits usually work; this one is known to.
ALCHEMY_PIN = "5ca23b1fe1774f954aacfbd7db35c8c9b9a59184"
BREW_PACKAGES = ["arm-none-eabi-binutils", "libpng"]
BREW_DIRS = ["/opt/homebrew/bin", "/usr/local/bin"]
# alchemy's INSTALL.md for Debian and Ubuntu (WSL included).
APT_PACKAGES = ["build-essential", "binutils-arm-none-eabi", "git", "libpng-dev"]
APT_COMMAND = "sudo apt install " + " ".join(APT_PACKAGES)
# Give up on a stalled download rather than wait forever.
GIT_LIMITS = ["git", "-c", "http.lowSpeedLimit=1000", "-c", "http.lowSpeedTime=120"]


def GIT_PATIENT_ARGS(folder):
    return GIT_LIMITS + ["-C", folder]


_settings_cache = {}


def load_settings():
    """The settings, a fresh copy each call (callers change and save it). Kept
    while the file stays the same: every translated message in a background job
    asks which language was chosen, which once meant thousands of reads."""
    import copy
    try:
        st = os.stat(SETTINGS)
        key = (SETTINGS, st.st_mtime_ns, st.st_size)
        if _settings_cache.get("key") != key:
            with open(SETTINGS, encoding="utf-8") as f:
                settings = json.load(f)
            _settings_cache.update(key=key, value=settings if isinstance(settings, dict) else {})
    except (OSError, ValueError):
        _settings_cache.clear()
        return {}
    return copy.deepcopy(_settings_cache["value"])


def save_settings(s):
    os.makedirs(SUPPORT, exist_ok=True)
    atomic_write(SETTINGS, json.dumps(s, indent=1))


def bundled_toolchain():
    """The toolchain the app carries (packaging/build_toolchain.py), if any:
    inside the app bundle, or packaging/toolchain when running from source."""
    import sys
    for base in (getattr(sys, "_MEIPASS", None), os.path.join(os.path.dirname(__file__), "..", "packaging")):
        if base:
            tc = os.path.abspath(os.path.join(base, "toolchain"))
            if os.path.exists(os.path.join(tc, "bin", "arm-none-eabi-as")):
                return _no_spaces(tc)
    return None


def _no_spaces(path):
    """The build can't take a path with spaces, and the app is "GS Map Editor.app":
    reach the toolchain through a link in the cache folder."""
    if " " not in path:
        return path
    link = os.path.join(CACHE, "toolchain")
    os.makedirs(CACHE, exist_ok=True)
    if os.path.realpath(link) != os.path.realpath(path):
        try:
            if os.path.islink(link):
                os.remove(link)
            os.symlink(path, link)
        except OSError:  # something else is in the way: this copy of the link is only ours
            link = tempfile.mkdtemp(prefix="gsmapedit-") + "/toolchain"
            os.symlink(path, link)
    return link


def _brew_dirs():
    return [] if os.environ.get("GSMAP_NO_BREW") or host.KIND != "mac" else BREW_DIRS


def build_env():
    """The bundled toolchain first, then Homebrew: a libpng-config earlier on
    PATH (devkitPro's, say) may answer for a libpng the tools can't link.
    GSMAP_NO_BREW=1 leaves Homebrew out (to test the bundle)."""
    env = dict(os.environ)
    tc = bundled_toolchain()
    dirs = ([os.path.join(tc, "bin")] if tc else []) + _brew_dirs()
    rest = env.get("PATH", "") if not os.environ.get("GSMAP_NO_BREW") else ""
    env["PATH"] = ":".join(dirs + ["/usr/bin", "/bin", "/usr/sbin", "/sbin"] + ([rest] if rest else []))
    env.pop("LIBPNG_CONFIG", None)
    return env


def _run(cmd, cwd=None, timeout=60):
    try:
        p = subprocess.run(cmd, cwd=cwd, env=build_env(), capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.SubprocessError) as e:
        return 1, str(e)


def brew():
    return next((os.path.join(d, "brew") for d in _brew_dirs() if os.path.exists(os.path.join(d, "brew"))), None)


def path_problem(root):
    """Why a checkout path can't be built, in words, or None."""
    if " " in root:
        return tr("{folder} has a space in its path, which the game's build can't handle. "
                  "Choose or move a copy of the game source to a folder with no spaces in its path.", folder=root)
    return None


def is_alchemy(root):
    """A checkout in the layout this editor reads (map/maps.c arrived with it)."""
    return bool(root) and os.path.exists(os.path.join(root, "Makefile")) and \
        os.path.exists(os.path.join(root, layout.MAP_TABLE))


def has_compiler_source(root):
    """The submodule step finished: a dropped connection can leave it empty."""
    return os.path.exists(os.path.join(root, "alchemy-gcc", "Makefile"))


def linux_missing():
    """The apt packages whose job isn't done, judged by the commands and
    library the build uses."""
    env = build_env()
    missing = []
    for cmd, pkg in (("cc", "build-essential"), ("make", "build-essential"),
                     ("arm-none-eabi-as", "binutils-arm-none-eabi"), ("git", "git")):
        if not shutil.which(cmd, path=env["PATH"]) and pkg not in missing:
            missing.append(pkg)
    lc = shutil.which("libpng-config", path=env["PATH"])
    if not lc or _run([lc, "--cflags"])[0] != 0:
        missing.append("libpng-dev")
    return missing


def checks(root):
    """[{id, title, ok, detail, action}] in setup order."""
    if host.KIND != "mac":
        missing = linux_missing()
        return [{"id": "packages", "title": tr("The tools for building the game"), "ok": not missing,
                 "detail": tr("Installed.") if not missing else
                 tr("Missing: {packages}. Open a terminal (on Windows, the Ubuntu app), run "
                    "`{command}`, then press Check again.", packages=", ".join(missing), command=APT_COMMAND),
                 "action": None}] + _source_steps(root)
    out = []
    clt = _run(["xcode-select", "-p"])[0] == 0 and _run(["/usr/bin/clang", "--version"])[0] == 0
    out.append({"id": "clt", "title": tr("Apple's developer tools"), "ok": clt,
                "detail": tr("Installed.") if clt else tr("Needed to build the game. Apple installs them for free."),
                "action": None if clt else tr("Install")})
    tc = bundled_toolchain()
    if tc and not missing_packages():
        out.append({"id": "packages", "title": tr("The tools for building the game"), "ok": True,
                    "detail": tr("Included with the app."), "action": None})
        return out + _source_steps(root)
    b = brew()
    out.append({"id": "brew", "title": "Homebrew", "ok": bool(b),
                "detail": tr("Installed.") if b else tr("A free package manager for the remaining tools. Install it "
                                                        "from brew.sh (paste its one line into Terminal), then come "
                                                        "back and press Check again."),
                "action": None if b else tr("Open brew.sh")})
    missing = []
    if b:
        missing = missing_packages()
    out.append({"id": "packages", "title": tr("The tools for building the game"),
                "ok": bool(b) and not missing,
                "detail": tr("Installed.") if b and not missing else
                          (tr("Needs Homebrew first.") if not b else tr("Missing: {packages}.", packages=", ".join(missing))),
                "action": tr("Install") if b and missing else None})
    return out + _source_steps(root)


def _source_steps(root):
    out = []
    src = is_alchemy(root) and has_compiler_source(root)
    problems = preflight.check(root) if src else []
    if not problems and (not src or " " in (root or "")):
        spaced = path_problem(root or DEFAULT_WORKSPACE)
        problems = [spaced] if spaced else []
    if problems:
        damaged = isinstance(problems[0], preflight.Damage)
        out.append({"id": "source", "title": tr("The game's source"), "ok": False,
                    "detail": problems[0] if " " in (root or DEFAULT_WORKSPACE) or damaged else
                    tr("{folder} is a version this editor can't read yet: {problem} "
                       "Move this folder aside, then use a fresh download.", folder=root, problem=problems[0]),
                    "action": None})
        return out + [{"id": "bootstrap", "title": tr("Preparing the build"), "ok": False,
                       "detail": tr("Needs the game source first."), "action": None},
                      {"id": "build", "title": tr("A first build of the game"), "ok": False,
                       "detail": tr("Needs the compilers first."), "action": None}]
    out.append({"id": "source", "title": tr("The game's source"), "ok": src,
                "detail": tr("Using {folder}.", folder=root) if src else
                tr("Downloads about 1 GB. If you already have a copy, choose its folder instead."),
                "action": None if src else tr("Download")})
    boot = src and all(os.path.exists(os.path.join(root, p)) for p in
                       ("tools/out/compilers/xgcc", "tools/out/compilers/as", "tools/out/compiler-runtime/libgcc.a"))
    out.append({"id": "bootstrap", "title": tr("Preparing the build"), "ok": bool(boot),
                "detail": tr("Built.") if boot else
                tr("Done once. Takes several minutes and shows a lot of scrolling text; that's normal."),
                "action": None if boot or not src else tr("Build")})
    rom = src and os.path.exists(os.path.join(root, layout.ROM))
    out.append({"id": "build", "title": tr("A first build of the game"), "ok": bool(rom),
                "detail": tr("Done: the editor is ready.") if rom else tr("Makes the game once, to check everything works."),
                "action": None if rom or not boot else tr("Build")})
    return out


def missing_packages():
    """Homebrew packages whose job isn't done: checked by what the build uses
    (the GBA assembler, and libpng-config answering for libpng), not by
    formula names, which Homebrew renames."""
    env = build_env()
    missing = []
    if not shutil.which("arm-none-eabi-as", path=env["PATH"]):
        missing.append("arm-none-eabi-binutils")
    lc = shutil.which("libpng-config", path=env["PATH"])
    if not lc or _run([lc, "--cflags"])[0] != 0:
        missing.append("libpng")
    return missing


RUNNING = set()  # builds and downloads in progress


def stop_running():
    """Quitting the app takes its builds and downloads with it."""
    for p in list(RUNNING):
        with contextlib.suppress(OSError):
            os.killpg(p.pid, signal.SIGTERM)
    RUNNING.clear()


atexit.register(stop_running)


class Job:
    """One background command sequence with a live log."""

    def __init__(self, name, steps, cwd=None, on_done=None):
        self.name, self.steps, self.cwd, self.on_done = name, steps, cwd, on_done
        self.log, self.done, self.ok = [], False, None
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        ok = True
        for cmd in self.steps:
            self.log.append("$ " + " ".join(cmd))
            try:
                p = subprocess.Popen(cmd, cwd=self.cwd, env=build_env(), stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, errors="replace", bufsize=1,
                                     start_new_session=True)
                RUNNING.add(p)
                for line in p.stdout:
                    self.log.append(line.rstrip("\n"))
                    if len(self.log) > 4000:
                        del self.log[:1000]
                ok = p.wait() == 0
                RUNNING.discard(p)
            except Exception as e:  # noqa: BLE001  the page is waiting on this job: it must end
                self.log.append(str(e))
                ok = False
            if not ok:
                break
        self.ok, self.done = ok, True
        if ok and self.on_done:
            self.on_done()

    def status(self, since=0):
        return {"name": self.name, "done": self.done, "ok": self.ok,
                "log": self.log[since:], "next": len(self.log)}


def start(action, root, workspace=None):
    """Start the job for a setup step; returns (job, new root or None)."""
    b = brew()
    if action == "clt":
        # Apple's own installer dialog; the page asks to press Check when it's done.
        return Job(tr("Apple developer tools"), [["xcode-select", "--install"]]), None
    if action == "packages" and host.KIND != "mac":
        raise ValueError(tr("Installing these needs your password: in a terminal, run {command}", command=APT_COMMAND))
    if action == "packages":
        if not b:
            raise ValueError(tr("Install Homebrew first"))
        return Job(tr("Build tools"), [[b, "install"] + (missing_packages() or BREW_PACKAGES)]), None
    if action == "source":
        dest = os.path.join(workspace or DEFAULT_WORKSPACE, "alchemy")
        if os.path.exists(dest) and not [n for n in os.listdir(dest) if n != ".DS_Store"]:
            shutil.rmtree(dest)  # an empty folder: the download below couldn't land on it
        if os.path.exists(dest) and os.listdir(dest):
            if is_alchemy(dest):
                return Job(tr("Game source"), [GIT_PATIENT_ARGS(dest) + ["submodule", "update", "--init", "--recursive",
                                                                      "alchemy-gcc"]], on_done=None), dest
            raise ValueError(tr("{folder} already exists, but it isn't a version of alchemy this editor can read. "
                                "Move it aside (your mod's changes are in it) and press Download again.", folder=dest))
        spaced = path_problem(dest)
        if spaced:
            raise ValueError(spaced)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
        except OSError as e:
            raise ValueError(tr("Couldn't create {folder} ({error}). If macOS asked about your "
                                "Documents folder, allow it in System Settings, Privacy & Security, Files and "
                                "Folders, then try again.", folder=os.path.dirname(dest), error=e.strerror)) from e
        # Everything happens in a folder that's only named as the game once it's
        # whole, so a dropped connection just means pressing the button again.
        partial = dest + ".partial"
        return Job(tr("Game source"), [
            ["rm", "-rf", partial],
            GIT_LIMITS + ["clone", ALCHEMY_URL, partial],
            GIT_PATIENT_ARGS(partial) + ["checkout", "-q", ALCHEMY_PIN],
            GIT_PATIENT_ARGS(partial) + ["submodule", "update", "--init", "--recursive", "alchemy-gcc"],
            ["mv", partial, dest],
        ]), dest
    if action == "bootstrap":
        return Job(tr("Compilers"), [["make", "bootstrap"]], cwd=root), None
    if action == "build":
        return Job(tr("First build"), [["make", "-j4", "tbs-en"]], cwd=root), None
    raise ValueError(f"unknown step {action}")


def which(cmd):
    return shutil.which(cmd, path=build_env()["PATH"])
