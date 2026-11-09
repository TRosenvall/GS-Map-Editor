"""Wrap dist/GS Map Editor.app in a disk image players drag to Applications.

    python3 packaging/make_dmg.py   ->  dist/GS-Map-Editor-<version>-<chip>.dmg

<chip> is AppleSilicon or Mac-Intel, from the app's own binary, so players can
tell the two downloads apart.
"""

import os
import platform
import plistlib
import shutil
import subprocess
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP = os.path.join(ROOT, "dist", "GS Map Editor.app")


def main():
    version = plistlib.load(open(os.path.join(APP, "Contents", "Info.plist"), "rb"))["CFBundleShortVersionString"]
    stage = tempfile.mkdtemp()
    shutil.copytree(APP, os.path.join(stage, "GS Map Editor.app"), symlinks=True)
    os.symlink("/Applications", os.path.join(stage, "Applications"))
    binary = os.path.join(APP, "Contents", "MacOS", "GS Map Editor")
    archs = subprocess.run(["lipo", "-archs", binary], capture_output=True, text=True).stdout.split() \
        or [platform.machine()]
    chip = "Universal" if len(archs) > 1 else ("AppleSilicon" if archs[0] == "arm64" else "Mac-Intel")
    out = os.path.join(ROOT, "dist", f"GS-Map-Editor-{version}-{chip}.dmg")
    if os.path.exists(out):
        os.remove(out)
    subprocess.run(["hdiutil", "create", "-volname", "GS Map Editor", "-srcfolder", stage,
                    "-ov", "-format", "UDZO", out], check=True, stdout=subprocess.DEVNULL)
    shutil.rmtree(stage)
    print(out, f"{os.path.getsize(out) / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
