"""What kind of computer the editor runs on, and how to open things there.

Three kinds:
  mac    the desktop app (or server.py) on macOS: `open`, mGBA.app.
  wsl    Linux inside Windows (WSL), which is how the editor runs on
         Windows: the browser and mGBA are Windows programs, reached through
         WSL's interop, and paths are handed over in Windows form.
  linux  any other Linux: xdg-open and the mgba-qt command.
"""

import os
import shutil
import subprocess
import sys

from .i18n import N_


def _kind():
    if sys.platform == "darwin":
        return "mac"
    try:
        with open("/proc/version") as f:
            if "microsoft" in f.read().lower():
                return "wsl"
    except OSError:
        pass
    return "linux"


KIND = _kind()
APP_NAME = "GS Map Editor"
HOME = os.path.expanduser("~")

if KIND == "mac":
    SUPPORT = os.path.join(HOME, "Library", "Application Support", APP_NAME)
    CACHE = os.path.join(HOME, "Library", "Caches", "GSMapEditor")
    WORKSPACE = os.path.join(HOME, "Documents", "GSMapEditor")
else:
    # Linux keeps settings and caches where its XDG convention says. The work
    # stays in the Linux home: a build on WSL's view of the Windows drive
    # (/mnt/c) is many times slower.
    SUPPORT = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config"), "gs-map-editor")
    CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(HOME, ".cache"), "gs-map-editor")
    WORKSPACE = os.path.join(HOME, "GSMapEditor")


POWERSHELL = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"


def _powershell(script, timeout=None):
    """Runs a PowerShell script on the Windows side of WSL; its output, or None."""
    exe = shutil.which("powershell.exe") or (POWERSHELL if os.path.exists(POWERSHELL) else None)
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "-NoProfile", "-NonInteractive", "-STA", "-Command",
                            "[Console]::OutputEncoding = [Text.Encoding]::UTF8; " + script],
                           capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.decode("utf-8", "replace").strip() if r.returncode == 0 else None


def linux_path(path):
    """A Windows path (C:\\... or \\\\wsl.localhost\\...) as WSL names it."""
    try:
        return subprocess.run(["wslpath", "-u", path], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _shared_folder():
    """Where exports and patched games go: somewhere the person's own file
    browser shows plainly. On Windows that's Documents\\GSMapEditor, not the
    Ubuntu home the build uses."""
    if KIND == "wsl":
        docs = _powershell("[Environment]::GetFolderPath('MyDocuments')", timeout=20)
        docs = linux_path(docs) if docs else None
        if docs and os.path.isdir(docs):
            return os.path.join(docs, "GSMapEditor")
    return WORKSPACE


SHARED = _shared_folder()


def choose_folder(title):
    """Asks for a folder with the system's own dialog, outside the Mac app
    (which has its own). The chosen path; "" when cancelled; None when there's
    no dialog to show, so the page asks for the path instead."""
    if KIND == "wsl":
        # A topmost owner keeps the dialog in front of the browser.
        quoted = "'" + title.replace("'", "''") + "'"  # a PowerShell string: a quote is doubled
        out = _powershell(
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$o = New-Object System.Windows.Forms.Form -Property @{TopMost = $true}; "
            "$d = New-Object System.Windows.Forms.FolderBrowserDialog; "
            f"$d.Description = {quoted}; $d.ShowNewFolderButton = $false; "
            "if ($d.ShowDialog($o) -eq 'OK') { [Console]::Out.Write($d.SelectedPath) } else { [Console]::Out.Write('?') }")
        if out is None:
            return None
        return "" if out == "?" else (linux_path(out) or "")
    if KIND == "linux" and shutil.which("zenity"):
        try:
            r = subprocess.run(["zenity", "--file-selection", "--directory", "--title", title],
                               capture_output=True, text=True)
        except OSError:
            return None
        return r.stdout.strip() if r.returncode == 0 else ""
    return None


def _quiet(cmd):
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return True
    except OSError:
        return False


def windows_path(path):
    """A WSL path as Windows programs name it (\\\\wsl.localhost\\Ubuntu\\...)."""
    try:
        return subprocess.run(["wslpath", "-w", path], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return path


def _windows_programs():
    """Where Windows keeps programs, seen from WSL."""
    return [p for p in ("/mnt/c/Program Files", "/mnt/c/Program Files (x86)") if os.path.isdir(p)]


def open_url(url):
    """Opens a web address in the person's browser."""
    if KIND == "mac":
        return _quiet(["open", url])
    if KIND == "wsl":
        # cmd's start treats & as a command separator unless it is escaped.
        return _quiet(["cmd.exe", "/c", "start", "", url.replace("&", "^&")]) or _quiet(["wslview", url])
    return _quiet(["xdg-open", url])


def _mgba_windows():
    for base in _windows_programs():
        exe = os.path.join(base, "mGBA", "mGBA.exe")
        if os.path.exists(exe):
            return exe
    return None


def mgba_available():
    if KIND == "mac":
        return subprocess.run(["open", "-Ra", "mGBA"], capture_output=True).returncode == 0
    if KIND == "wsl":
        return bool(_mgba_windows() or shutil.which("mgba-qt"))
    return bool(shutil.which("mgba-qt") or shutil.which("mgba"))


def play(rom):
    """Opens a built game in mGBA. Returns False when mGBA isn't installed."""
    if KIND == "mac":
        return mgba_available() and _quiet(["open", "-a", "mGBA", rom])
    if KIND == "wsl":
        exe = _mgba_windows()
        if exe:
            return _quiet([exe, windows_path(rom)])
    cmd = shutil.which("mgba-qt") or shutil.which("mgba")
    return bool(cmd) and _quiet([cmd, rom])


def reveal(path):
    """Shows a file in the system's file browser."""
    if KIND == "mac":
        return _quiet(["open", "-R", path])
    if KIND == "wsl":
        return _quiet(["explorer.exe", "/select," + windows_path(path)])
    return _quiet(["xdg-open", os.path.dirname(path)])


# Kept in English; tr() translates it where it's shown.
MGBA_HINT = {
    "mac": N_("install it from mgba.io"),
    "wsl": N_("install the Windows version from mgba.io (the installer puts it in Program Files)"),
    "linux": N_("install it from mgba.io or your system's packages (it provides mgba-qt)"),
}[KIND]
