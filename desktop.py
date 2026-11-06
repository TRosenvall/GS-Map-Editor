"""GS Map Editor as a desktop app: a native window around the editor.

On first run (or whenever something is missing) the window shows the setup
checklist (static/setup.html, gsmap/setup.py); once the game source builds,
it opens the editor itself. Both servers listen on this machine only, behind
a random token, and only accept writes from their own pages.

    python3 desktop.py                # the app (needs pywebview)
    python3 desktop.py --no-window    # same servers, URL printed (for testing)
"""

import argparse
import hmac
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
from contextlib import suppress
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from gsmap import setup as setupmod  # noqa: E402

STATIC = os.path.join(HERE, "static")
TOKEN = secrets.token_urlsafe(16)
START = threading.Lock()  # two presses of a step's button start one job
APP = {"root": None, "job": None, "editor_url": None, "window": None, "workspace": setupmod.DEFAULT_WORKSPACE,
       "problem": None}


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_editor():
    """Start the editor's server on the configured checkout; returns its URL."""
    if APP["editor_url"]:
        return APP["editor_url"]
    import server  # noqa: E402  (imports the project code only when it's needed)
    from gsmap.project import Project
    project = Project(APP["root"])
    port = free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), server.make_handler(project, TOKEN))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    APP["editor_url"] = f"http://127.0.0.1:{port}/?token={TOKEN}"
    return APP["editor_url"]


def safe_checks():
    """The setup checklist, whatever state the checkout is in. An error here must
    reach the page: before the window opens, it's the only place to say anything."""
    try:
        return setupmod.checks(APP["root"])
    except Exception as e:  # noqa: BLE001
        APP["problem"] = f"Couldn't check the setup ({type(e).__name__}: {e})."
        return [{"id": "source", "title": "The game's source", "ok": False,
                 "detail": "Couldn't be read. Move its folder aside, then use a fresh download.", "action": None}]


def server_host_ok(headers):
    """As server.host_allowed: the setup page answers only to this Mac's own names."""
    return headers.get("Host", "").rsplit(":", 1)[0] in ("127.0.0.1", "localhost", "[::1]")


class SetupHandler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=STATIC, **kw)

    def log_message(self, fmt, *args):
        pass

    def end_headers(self):
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                         "script-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        q = parse_qs(urlsplit(self.path).query).get("token", [""])[0]
        if q and hmac.compare_digest(q, TOKEN):
            return "query"
        c = SimpleCookie(self.headers.get("Cookie", "")).get("gsmap_token")
        return c is not None and hmac.compare_digest(c.value, TOKEN)

    def do_GET(self):
        if not server_host_ok(self.headers):
            return self.send_json({"error": "forbidden"}, 403)
        path = urlsplit(self.path).path
        auth = self.authorized()
        if not auth:
            return self.send_json({"error": "forbidden"}, 403)
        if auth == "query":  # swap the token in the URL for a cookie
            self.send_response(302)
            self.send_header("Set-Cookie", f"gsmap_token={TOKEN}; HttpOnly; SameSite=Strict; Path=/")
            self.send_header("Location", path)
            self.end_headers()
            return
        if path in ("/", "/setup.html"):
            self.path = "/setup.html"
            return super().do_GET()
        if path in ("/setup.js",):
            self.path = path
            return super().do_GET()
        if path == "/api/setup/checks":
            checks = safe_checks()
            return self.send_json({"root": APP["root"], "workspace": APP["workspace"], "checks": checks,
                                   "problem": APP["problem"], "pin": setupmod.ALCHEMY_PIN[:10]})
        if path == "/api/setup/job":
            since = int(parse_qs(urlsplit(self.path).query).get("since", ["0"])[0])
            return self.send_json(APP["job"].status(since) if APP["job"] else {"done": True, "ok": None, "log": [], "next": 0})
        return self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        if not server_host_ok(self.headers):
            return self.send_json({"error": "forbidden"}, 403)
        path = urlsplit(self.path).path
        origin, host = self.headers.get("Origin"), self.headers.get("Host", "")
        if not self.authorized() or self.headers.get("X-GSMap") != "1" or (origin and urlsplit(origin).netloc != host):
            return self.send_json({"error": "forbidden"}, 403)
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
        try:
            if path == "/api/setup/run":
                step = body.get("step")
                if step == "brew":
                    subprocess.Popen(["open", "https://brew.sh"])
                    return self.send_json({"ok": True})
                with START:
                    if APP["job"] and not APP["job"].done:
                        return self.send_json({"error": "Another step is still running."}, 409)
                    job, root = setupmod.start(step, APP["root"], APP["workspace"])
                    APP["job"] = job
                if root:
                    APP["root"] = root
                    remember_root(root)
                return self.send_json({"ok": True})
            if path == "/api/setup/choose":
                folder = choose_folder()
                if not folder:
                    return self.send_json({"ok": False})
                if setupmod.path_problem(folder):
                    return self.send_json({"error": setupmod.path_problem(folder)}, 409)
                if not setupmod.is_alchemy(folder):
                    return self.send_json({"error": f"{folder} doesn't look like a copy of the game source this "
                                                    "editor can read."}, 409)
                APP["root"] = folder
                remember_root(folder)
                return self.send_json({"ok": True, "root": folder})
            if path == "/api/setup/launch":
                if not all(c["ok"] for c in safe_checks()):
                    return self.send_json({"error": "Some steps aren't done yet."}, 409)
                return self.send_json({"url": start_editor()})
        except ValueError as e:
            return self.send_json({"error": str(e)}, 409)
        except Exception as e:  # noqa: BLE001  the page can show this; a dropped connection shows nothing
            return self.send_json({"error": f"That didn't work ({type(e).__name__}: {e})."}, 500)
        return self.send_json({"error": "not found"}, 404)


def remember_root(root):
    """For next time. If settings can't be written, this run still carries on."""
    with suppress(OSError):
        s = setupmod.load_settings(); s["alchemy_root"] = root; setupmod.save_settings(s)


def choose_folder():
    w = APP["window"]
    if w is None:
        return None
    import webview
    r = w.create_file_dialog(webview.FOLDER_DIALOG, directory=os.path.expanduser("~"))
    return r[0] if r else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", help="alchemy checkout (default: the one chosen at setup)")
    ap.add_argument("--no-window", action="store_true", help="serve only and print the URL")
    ap.add_argument("--port", type=int, default=0, help="setup server port (default: any free)")
    args = ap.parse_args()
    saved = setupmod.load_settings().get("alchemy_root")
    APP["root"] = args.root or (saved if isinstance(saved, str) else None)
    port = args.port or free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), SetupHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/?token={TOKEN}"
    if all(c["ok"] for c in safe_checks()):
        try:
            url = start_editor()
        except Exception as e:  # noqa: BLE001  say why in the window, rather than never open one
            APP["problem"] = f"The editor couldn't start ({type(e).__name__}: {e})."
    if args.no_window:
        print("setup:", f"http://127.0.0.1:{port}/?token={TOKEN}", flush=True)
        print("open:", url, flush=True)
        threading.Event().wait()
        return
    import webview
    APP["window"] = webview.create_window(setupmod.APP_NAME, url, width=1440, height=900, min_size=(1000, 640))
    webview.start()
    setupmod.stop_running()


if __name__ == "__main__":
    main()
