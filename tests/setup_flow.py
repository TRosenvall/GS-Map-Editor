"""Goes through first-run setup the way a new player does, then opens the
editor and lists the maps: the whole path from nothing to editing.

    python3 tests/setup_flow.py HOME_DIR [APP_BINARY]

HOME_DIR stands in for the player's home folder, so settings, the download
and the build all land there and nothing of yours is touched. APP_BINARY is a
packaged app's executable; without it, desktop.py runs from this checkout.
It takes about 15 minutes and needs the build tools setup checks for.
"""

import http.cookiejar
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def main():
    home = os.path.abspath(sys.argv[1])
    os.makedirs(home, exist_ok=True)
    cmd = [sys.argv[2]] if len(sys.argv) > 2 else [sys.executable, os.path.join(ROOT, "desktop.py")]
    env = dict(os.environ, HOME=home)
    env.pop("XDG_CONFIG_HOME", None)
    env.pop("XDG_CACHE_HOME", None)
    app = subprocess.Popen(cmd + ["--no-window"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        url = None
        while not url:
            line = app.stdout.readline()
            if not line and app.poll() is not None:
                raise SystemExit(f"the app quit before serving (exit {app.returncode})")
            m = re.search(r"open: (\S+)", line)
            url = m and m.group(1)
        base = url.split("/?")[0]
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        opener.open(url, timeout=60).read()

        def get(path):
            return json.load(opener.open(base + path, timeout=120))

        def post(path, body):
            req = urllib.request.Request(base + path, json.dumps(body).encode(),
                                         {"X-GSMap": "1", "Content-Type": "application/json"})
            try:
                return json.load(opener.open(req, timeout=600))
            except urllib.error.HTTPError as e:
                return json.load(e)

        started = time.time()
        first = get("/api/setup/checks")
        print("checks:", [(c["id"], c["ok"]) for c in first["checks"]], "pin", first["pin"], flush=True)
        tools = next(c for c in first["checks"] if c["id"] == "packages")
        if not tools["ok"]:
            raise SystemExit(f"build tools missing: {tools['detail']}")
        for step in ("source", "bootstrap", "build"):
            answer = post("/api/setup/run", {"step": step})
            if answer.get("error"):
                raise SystemExit(f"{step}: {answer['error']}")
            while True:
                job = get("/api/setup/job?since=0")
                if job["done"]:
                    break
                time.sleep(10)
            print(step, "ok" if job["ok"] else "FAILED", f"{time.time() - started:.0f} s", flush=True)
            if not job["ok"]:
                print("\n".join(job["log"][-40:]))
                raise SystemExit(1)
        after = get("/api/setup/checks")
        if not all(c["ok"] for c in after["checks"]):
            raise SystemExit(f"setup isn't complete: {after['checks']}")
        editor = post("/api/setup/launch", {})
        if editor.get("error"):
            raise SystemExit(f"launch: {editor['error']}")
        opener.open(editor["url"], timeout=120).read()
        maps = json.load(opener.open(editor["url"].split("/?")[0] + "/api/maps", timeout=300))
        print(f"editor open, {len(maps)} maps listed; game at {after['root']}", flush=True)
        if len(maps) < 100:
            raise SystemExit("too few maps")
    finally:
        app.terminate()
        app.wait(timeout=30)


if __name__ == "__main__":
    main()
