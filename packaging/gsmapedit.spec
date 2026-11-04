# PyInstaller recipe for "GS Map Editor.app" (macOS).
#   .venv/bin/pyinstaller --noconfirm packaging/gsmapedit.spec
# The app holds Python, the editor, its pages and (when packaging/toolchain
# exists, see build_toolchain.py) the GBA build tools. The game source is
# set up on first run (gsmap/setup.py), never bundled.
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
TOOLCHAIN = os.path.join(SPECPATH, "toolchain")

a = Analysis(
    [os.path.join(ROOT, "desktop.py")],
    pathex=[ROOT],
    datas=[
        (os.path.join(ROOT, "static"), "static"),
        (os.path.join(ROOT, "gsmap", "data"), os.path.join("gsmap", "data")),
    ] + ([(TOOLCHAIN, "toolchain")] if os.path.isdir(TOOLCHAIN) else []),
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
        "CFBundleShortVersionString": "0.1.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
)
