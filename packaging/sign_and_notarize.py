"""Sign the app with a Developer ID and have Apple notarize it, so players
open it with a double-click instead of right-click > Open. Needs an Apple
Developer account (paid) and, once:

    xcrun notarytool store-credentials gsmapedit --apple-id YOU --team-id TEAM

then:

    python3 packaging/sign_and_notarize.py --identity "Developer ID Application: NAME (TEAM)"

Signs every binary inside out (the bundled toolchain included), the app
with the hardened runtime, notarizes the disk image, and staples the ticket.
"""

import argparse
import os
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP = os.path.join(ROOT, "dist", "GS Map Editor.app")
ENTITLEMENTS = os.path.join(os.path.dirname(__file__), "entitlements.plist")


def macho(path):
    with open(path, "rb") as f:
        return f.read(4) in (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xce\xfa\xed\xfe")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--identity", required=True)
    ap.add_argument("--profile", default="gsmapedit", help="notarytool keychain profile")
    a = ap.parse_args()
    sign = ["codesign", "--force", "--timestamp", "--options", "runtime", "--sign", a.identity]
    # Inside out: a bundle's signature covers what's in it, so the deepest code goes first.
    code = [os.path.join(d, f) for d, _, files in os.walk(APP) for f in files]
    code = [p for p in code if not os.path.islink(p) and os.path.isfile(p) and macho(p)]
    for p in sorted(code, key=lambda p: -p.count(os.sep)):
        subprocess.run(sign + [p], check=True)
    bundles = [os.path.join(d, x) for d, dirs, _ in os.walk(APP) for x in dirs if x.endswith(".framework")]
    for b in sorted(bundles, key=lambda p: -p.count(os.sep)):
        subprocess.run(sign + [b], check=True)
    subprocess.run(sign + ["--entitlements", ENTITLEMENTS, APP], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", APP], check=True)
    subprocess.run(["python3", os.path.join(os.path.dirname(__file__), "make_dmg.py")], check=True)
    dmgs = [os.path.join(ROOT, "dist", f) for f in os.listdir(os.path.join(ROOT, "dist")) if f.endswith(".dmg")]
    dmg = max(dmgs, key=os.path.getmtime)  # the one just made
    subprocess.run(["codesign", "--sign", a.identity, "--timestamp", dmg], check=True)
    subprocess.run(["xcrun", "notarytool", "submit", dmg, "--keychain-profile", a.profile, "--wait"], check=True)
    subprocess.run(["xcrun", "stapler", "staple", dmg], check=True)
    subprocess.run(["spctl", "--assess", "--type", "open", "--context", "context:primary-signature", dmg], check=True)
    print("signed, notarized and stapled:", dmg)


if __name__ == "__main__":
    main()
