# PyInstaller recipe for "GS Map Editor.app" (macOS).
#   .venv/bin/pyinstaller --noconfirm packaging/gsmapedit.spec
# The app holds Python, the editor, its pages and (when packaging/toolchain
# exists, see build_toolchain.py) the GBA build tools. The game source is
# set up on first run (gsmap/setup.py), never bundled.
import os

from PyInstaller.utils.hooks import copy_metadata

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
TOOLCHAIN = os.path.join(SPECPATH, "toolchain")
# Licence files of the packages the app carries (THIRD_PARTY_NOTICES.md);
# Pillow's also lists those of the libraries its wheel carries.
LICENCES = [d for name in ("pillow", "pywebview", "bottle", "typing_extensions") for d in copy_metadata(name)]

a = Analysis(
    [os.path.join(ROOT, "desktop.py")],
    pathex=[ROOT],
    datas=[
        (os.path.join(ROOT, "static"), "static"),
        (os.path.join(ROOT, "gsmap", "data"), os.path.join("gsmap", "data")),
        (os.path.join(ROOT, "LICENSE"), "."),
        (os.path.join(ROOT, "THIRD_PARTY_NOTICES.md"), "."),
    ] + LICENCES + ([(TOOLCHAIN, "toolchain")] if os.path.isdir(TOOLCHAIN) else []),
    hiddenimports=["server", "webview.platforms.cocoa"],
    excludes=["tkinter"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="GS Map Editor", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="GS Map Editor")
app = BUNDLE(
    coll,
    name="GS Map Editor.app",
    icon=os.path.join(SPECPATH, "icon.icns"),
    bundle_identifier="io.github.gsmapedit",
    info_plist={
        "CFBundleShortVersionString": "0.3.0",
        "NSDocumentsFolderUsageDescription": "Your mod and the game's source are kept in Documents/GSMapEditor.",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
)
