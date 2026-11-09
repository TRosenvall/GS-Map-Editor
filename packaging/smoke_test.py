"""Start the built app without its window and check its setup page answers:
the build tools it carries are found, and it names the pinned alchemy commit.

    python3 packaging/smoke_test.py   (after pyinstaller; exits non-zero on a problem)
"""

import http.cookiejar
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BINARY = os.path.join(ROOT, "dist", "GS Map Editor.app", "Contents", "MacOS", "GS Map Editor")
sys.path.insert(0, ROOT)
from gsmap.setup import ALCHEMY_PIN  # noqa: E402


def main():
    app = subprocess.Popen([BINARY, "--no-window"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        url, start = None, time.time()
        while url is None and time.time() - start < 120:
            line = app.stdout.readline()
            if not line and app.poll() is not None:
                raise SystemExit(f"the app quit before serving (exit {app.returncode})")
            m = re.search(r"open: (http://127\.0\.0\.1:\d+/\?token=\S+)", line)
            url = m and m.group(1)
        if not url:
            raise SystemExit("the app printed no address within two minutes")
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        opener.open(url, timeout=30).read()
        base = url.split("/?")[0]
        answer = json.load(opener.open(base + "/api/setup/checks", timeout=60))
        checks = {c["id"]: c for c in answer["checks"]}
        problems = []
        if not checks.get("packages", {}).get("ok"):
            problems.append(f"build tools not found: {checks.get('packages')}")
        if answer.get("pin") != ALCHEMY_PIN[:10]:
            problems.append(f"pin {answer.get('pin')}, expected {ALCHEMY_PIN[:10]}")
        if answer.get("problem"):
            problems.append(f"setup problem: {answer['problem']}")
        for page in ("/setup.js", "/"):
            opener.open(base + page, timeout=30).read()
        print("\n".join(problems) or "smoke test ok: tools included, pin " + answer["pin"])
        sys.exit(1 if problems else 0)
    finally:
        app.terminate()
        app.wait(timeout=30)


if __name__ == "__main__":
    main()
