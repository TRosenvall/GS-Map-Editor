"""gs-mapedit: a local map viewer for alchemy's Golden Sun: The Broken Seal.

    python3 server.py [--root ~/gs_project/alchemy-port] [--port 8765]

then open http://127.0.0.1:8765/
"""

import argparse
import base64
import contextlib
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import signal
import subprocess
import threading
import traceback
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from gsmap import fsio, layout, playtest, preflight
from gsmap.reset import reset_map
from gsmap.doors import script_exit_kinds as script_kinds
from gsmap.modgen import Overrides, generate, validate_rows
from gsmap.names import Names
from gsmap.project import Project
from gsmap.scenes import Scenes
from gsmap.chests import ChestEditor
from gsmap.doors import DoorEditor
from gsmap.checks import Checker
from gsmap.events import EventEditor, flag_names, flag_label, SEARCH_TARGETS
from gsmap.connections import Connections
from gsmap import world as worldmod
from gsmap import patch as patchmod
from gsmap import setup as setupmod
from gsmap import tileset as tilesetmod

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")


# Terrain kinds (encounter regions) as overlay tints.
KIND_COLOURS = {1: (255, 214, 10, 90), 2: (255, 120, 40, 90), 3: (80, 200, 255, 90), 4: (190, 90, 255, 90),
                5: (60, 230, 120, 90), 6: (255, 80, 160, 90), 21: (240, 240, 255, 110), 31: (255, 50, 50, 90)}


EXPORTS = setupmod.EXPORTS
PATCHED = os.path.join(setupmod.DEFAULT_WORKSPACE, "Patched")


class Cache:
    """Computed images by key. A slow image holds up only requests for itself,
    and one that a save outdated while it was being made isn't kept."""

    def __init__(self):
        self.lock = threading.Lock()
        self.items = {}
        self.making = {}
        self.drops = 0

    def get(self, key, make):
        with self.lock:
            if key in self.items:
                return self.items[key]
            one = self.making.setdefault(key, threading.Lock())
        with one:
            with self.lock:
                if key in self.items:
                    return self.items[key]
                drops = self.drops
            value = make()
            with self.lock:
                if self.drops == drops:
                    self.items[key] = value
                self.making.pop(key, None)
            return value

    def drop(self, pred):
        with self.lock:
            self.drops += 1
            for k in [k for k in self.items if pred(k)]:
                del self.items[k]


MAX_REQUEST = 256 * 1024 * 1024  # room for a ROM and a patch, base64-encoded
LOCAL_HOSTS = ("127.0.0.1", "localhost", "[::1]")
# Pages talk only to this server: a script slipped in by a patch file or a name
# has nowhere to send anything.
CSP = ("default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
       "script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


def host_allowed(headers, local_only=True):
    """A website can point its own name at 127.0.0.1 (DNS rebinding); the Host
    header it must then send gives it away."""
    if not local_only:
        return True
    return headers.get("Host", "").rsplit(":", 1)[0] in LOCAL_HOSTS


def make_handler(project, token=None, local_only=True):
    cache = Cache()
    state = {"scenes": None}
    names = Names(project.root)

    def scenes():
        if state["scenes"] is None:
            state["scenes"] = Scenes(project.root)
        return state["scenes"]

    fsio.recover(project.root)  # an action the editor died during

    history = os.path.join(setupmod.SUPPORT, "history", hashlib.sha1(os.path.abspath(project.root).encode()).hexdigest()[:12])

    def forget_loaded():
        """Files went back to an earlier state: drop what was read from them."""
        project.reload()
        state["world"] = None
        state["conn"] = None
        cache.drop(lambda k: True)

    @contextlib.contextmanager
    def writing(label="your last change"):
        """One user action: serialised, all its files land or none do, and it
        can be undone afterwards."""
        with write_lock:
            with fsio.transaction(project.root, history, label) as txn:
                try:
                    yield txn
                except BaseException:
                    project._sheet_cache.clear()
                    state["world"] = None
                    raise
                if txn.aborted:
                    project._sheet_cache.clear()
                    state["world"] = None

    def warm_up():
        """Do the slow first-time reads now, so the first click needn't wait."""
        try:
            sc = scenes()
            for s in sc.scenes:
                try:
                    o = sc.overlay(s["overlay"])
                except FileNotFoundError:
                    continue
                script_kinds(project.tbs, o)
        except Exception:
            pass  # the same read happens, and reports itself, when it's needed

    threading.Thread(target=warm_up, daemon=True).start()

    def row_to_map():
        out = {}
        for n, info in project.maps.items():
            for r in [info.resources] + info.alternates:
                if r:
                    out.setdefault(r["row"], n)
        return out

    def scene_summary():
        rm = row_to_map()
        return [dict(s, map=rm.get(s["layered_row"])) for s in scenes().scenes]

    def entrance_numbers(ovl_id):
        try:
            o = scenes().overlay(ovl_id)
        except FileNotFoundError:
            return []
        nums = set()
        for name, t in o.tables.items():
            if t["kind"] == "entrances" and t["editable"]:
                nums |= {r["entrance"] for r in o.rows(name) if r["entrance"] >= 0}
        return sorted(nums)

    def world():
        if state.get("world") is None:
            state["world"] = worldmod.World(project.root)
        return state["world"]

    def map_scenes(n):
        info = project.maps[n]
        rows = {r["row"] for r in [info.resources] + info.alternates if r}
        ov = Overrides(project.root)
        out = []
        for sc in scenes().for_rows(rows):
            o = scenes().overlay(sc["overlay"])
            tables = []
            for name, t in sorted(o.tables.items(), key=lambda kv: (kv[1]["kind"], kv[0])):
                if not t["editable"]:
                    continue  # named like a table, but its bytes aren't one
                over = ov.get(o.id, name)
                tables.append({
                    "symbol": name, "kind": t["kind"], "editable": t["editable"],
                    "overridden": over is not None,
                    "rows": over["rows"] if over else o.rows(name),
                })
            out.append(dict(sc, getters={k: o.getter_name(k) for k in o.getters}, tables=tables))
        return out
    write_lock = threading.Lock()
    # Bundled toolchain first (the app), then Homebrew; see gsmap/setup.py.
    build_env = setupmod.build_env()

    def make(target):
        p = subprocess.Popen(["make", f"-j{os.cpu_count() or 4}", target], cwd=project.root, env=build_env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        setupmod.RUNNING.add(p)
        try:
            out, _ = p.communicate(timeout=1800)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGTERM)
            out = p.communicate()[0] + "\nThe build took too long and was stopped."
        finally:
            setupmod.RUNNING.discard(p)
        return p.returncode, out.strip().split("\n")

    def refresh_mod(playable=None):
        """mod.c names addresses in the built scene code: bring it up to date
        with what was just built. playable switches Play's start-at-a-place code
        on or off. True if that changed mod.c."""
        path = os.path.join(project.root, layout.MOD, "mod.c")
        before = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        ov = Overrides(project.root)
        if playable is not None and bool(ov.data.get("playable")) != playable:
            ov.data["playable"] = playable
            ov.save()
        generate(project.root, scenes(), ov)
        return open(path, encoding="utf-8").read() != before

    def run_build(target, playable=None):
        if playable is not None:
            refresh_mod(playable)
        code, out = make(target)
        if code == 0 and refresh_mod():
            code, out = make(target)
        return {"target": target, "exit": code, "tail": out[-40:]}

    def map_json(n):
        info = project.maps[n]
        planes = {}
        for plane in ("metatile", "collision", "shape"):
            try:
                g = project.load_grid(info, plane)
                planes[plane] = g.cells
            except FileNotFoundError:
                planes[plane] = None
        w, h = info.size
        return {
            "number": n,
            "folder": os.path.relpath(info.folder, project.root),
            "tileset": info.tileset,
            "palette": info.palette,
            "resources": info.resources,
            "alternates": info.alternates,
            "size": [w, h],
            "bounds": info.bounds,
            "layers": [
                {
                    "index": i,
                    "origin": list(project.layer_origin(info, i)),
                    "priority": info.priority[i],
                    "char_base": info.char_base[i],
                    "raw": info.layers[i],
                }
                for i in range(len(info.layers))
            ],
            "metatile_count": len(project.load_metatiles(info).rows),
            # Stamps paste between maps of one block family (the same table,
            # or one copied from it and extended); retired blocks never.
            "metatiles_hash": hashlib.sha1(
                open(info.source("CELL_PICTURES", "cell_pictures.tsv"), "rb").read()
            ).hexdigest()[:16],
            "shares_grid": sorted(o.number for o in project.maps.values()
                                  if o is not info and o.grid_path() == info.grid_path()),
            "family": tilesetmod.block_family(project, info)[0],
            "family_size": tilesetmod.block_family(project, info)[1],
            "retired": sorted(tilesetmod.retired_blocks(project, info)),
            "own_tileset": tilesetmod.own_tileset(project, info),
            "markers": [
                {"index": i, "x": r[0], "z": r[1], "id": r[2]}
                for i, r in enumerate((project.load_markers(info)[1] or type("T", (), {"rows": []})).rows)
                if tuple(r[:3]) != (0xFF, 0xFF, 0xFF)
            ],
            "markers_editable": (lambda p, t: t is not None and len(project.marker_users(p)) == 1)(
                *project.load_markers(info)
            ),
            "grids": planes,
            # heights for drawing ground-level things where the game shows them
            "shapes": project.shape_rows(info) if os.path.exists(info.source("SHAPES", "shapes.tsv")) else [],
            # 0xfff cells numbered as the game numbers them at load
            "blocks": project.resolve_placeholders(planes["metatile"]) if planes["metatile"] else None,
        }

    def png(img):
        buf = io.BytesIO()
        img.save(buf, "PNG", compress_level=1)  # served locally: speed over size
        return buf.getvalue()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=STATIC, **kw)

        def log_message(self, fmt, *args):
            pass

        def end_headers(self):
            # The pages too, so an updated editor isn't hidden by a cached copy.
            if not self.path.startswith("/api/"):
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Security-Policy", CSP)
            self.send_header("X-Content-Type-Options", "nosniff")
            super().end_headers()

        def send_bytes(self, body, ctype, status=200):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, obj, status=200):
            self.send_bytes(json.dumps(obj).encode(), "application/json", status)

        def authorized(self):
            """With a token set, accept ?token=… (then a cookie) or the cookie."""
            if not token:
                return True
            query = parse_qs(urlsplit(self.path).query)
            if hmac.compare_digest(query.get("token", [""])[0], token):
                return "query"
            cookies = SimpleCookie(self.headers.get("Cookie", ""))
            c = cookies.get("gsmap_token")
            return c is not None and hmac.compare_digest(c.value, token)

        def do_GET(self):
            if not host_allowed(self.headers, local_only):
                return self.send_json({"error": "forbidden"}, 403)
            path = self.path.split("?")[0]
            auth = self.authorized()
            if not auth:
                return self.send_bytes(
                    b"Forbidden: open the URL with ?token=... printed by the server.\n",
                    "text/plain", 403,
                )
            if auth == "query":
                # Remember the token in a cookie, then drop it from the address bar.
                self.send_response(303)
                self.send_header("Set-Cookie", f"gsmap_token={token}; Path=/; HttpOnly; SameSite=Strict")
                self.send_header("Location", path)
                self.end_headers()
                return
            try:
                if path == "/api/history":
                    return self.send_json({"last": fsio.last_saved(history)})
                if path == "/api/maps/own-tileset":
                    return self.send_json(tilesetmod.own_tileset_maps(project))
                if path == "/api/maps":
                    out = []
                    rm = {}
                    for sc in scenes().scenes:
                        rm.setdefault(sc["layered_row"], sc["id"])
                    for n, m in sorted(project.maps.items()):
                        first = next((rm[r["row"]] for r in [m.resources] + m.alternates if r and r["row"] in rm), None)
                        out.append({
                            "label": names.scene_label(first) if first is not None else None,
                            "number": n,
                            "folder": os.path.basename(m.folder),
                            "tileset": m.tileset,
                            "palette": m.palette,
                            "size": list(m.size),
                        })
                    return self.send_json(out)
                m = re.fullmatch(r"/api/map/(\w+)", path)
                if m and m.group(1) in project.maps:
                    return self.send_json(map_json(m.group(1)))
                if path == "/api/names":
                    return self.send_json(names.client_tables())
                m = re.fullmatch(r"/api/asset/item/(\d+)\.png", path)
                if m:
                    return self.send_bytes(names.item_icon_png(int(m.group(1))), "image/png")
                m = re.fullmatch(r"/api/asset/sprite/(\d+)\.png", path)
                if m:
                    body = names.sprite_png(int(m.group(1)))
                    if body is None:
                        return self.send_json({"error": "no preview"}, 404)
                    return self.send_bytes(body, "image/png")
                m = re.fullmatch(r"/api/map/(\w+)/legend", path)
                if m and m.group(1) in project.maps:
                    info = project.maps[m.group(1)]
                    rows = {r["row"] for r in [info.resources] + info.alternates if r}
                    lg = names.map_legend(scenes().for_rows(rows), scenes())
                    # only codes this map actually uses (overlays share event tables)
                    present = {v for row in project.load_grid(info, "collision").cells for v in row}
                    return self.send_json({str(k): v for k, v in lg.items() if k in present})
                if path == "/api/scenes":
                    return self.send_json(scene_summary())
                m = re.fullmatch(r"/api/scene-overlay/([0-9a-f]+)/entrances", path)
                if m:
                    return self.send_json(entrance_numbers(int(m.group(1), 16)))
                if path == "/api/world":
                    w = world()
                    places = worldmod.world_places(w, project, scenes(), names)
                    return self.send_json({"places": places,
                                           "regions": worldmod.region_names(w, places, names),
                                           "blocks": len(w.block_tiles)})
                m = re.fullmatch(r"/api/world/(chunk|walk|kind)/(\d+)/(\d+)\.png", path)
                if m:
                    what, cx, cy = m.group(1), int(m.group(2)), int(m.group(3))
                    if not (0 <= cx < 16 and 0 <= cy < 16):
                        return self.send_json({"error": "no such chunk"}, 404)
                    w = world()
                    make = {"chunk": lambda: w.render_chunk(cx, cy), "walk": lambda: w.render_walk(cx, cy),
                            "kind": lambda: w.render_kind(cx, cy, KIND_COLOURS)}[what]
                    return self.send_bytes(cache.get(("world", what, cx, cy), lambda: png(make())), "image/png")
                m = re.fullmatch(r"/api/world/cells/(\d+)/(\d+)", path)
                if m:
                    return self.send_json(world().chunk_cells(int(m.group(1)), int(m.group(2))))
                m = re.fullmatch(r"/api/world/atlas/([01])\.png", path)
                if m:
                    li = int(m.group(1))
                    cols = max(8, min(64, int(parse_qs(urlsplit(self.path).query).get("cols", ["64"])[0])))
                    return self.send_bytes(cache.get(("world", "atlas", li, cols),
                                                     lambda: png(worldmod.block_atlas(world(), li, cols))), "image/png")
                m = re.fullmatch(r"/api/connections/(\d+)", path)
                if m:
                    # The index reads every exit table; rebuild it only after writes.
                    if state.get("conn") is None:
                        state["conn"] = Connections(project, scenes(), names)
                    return self.send_json(state["conn"].around(int(m.group(1)), row_to_map()))
                m = re.fullmatch(r"/api/map/(\w+)/events", path)
                if m and m.group(1) in project.maps:
                    q = parse_qs(urlsplit(self.path).query)
                    ee = EventEditor(project, scenes(), names)
                    try:
                        d = ee.describe(project.maps[m.group(1)], int(q["scene"][0]), q.get("table", [None])[0])
                    except ValueError as e:
                        return self.send_json({"error": str(e)}, 409)
                    sc_ = next(s_ for s_ in scenes().scenes if s_["id"] == int(q["scene"][0]))
                    d["shared_with"] = [names.scene_label(s_["id"]) for s_ in scenes().scenes
                                        if s_["overlay"] == sc_["overlay"] and s_["id"] != sc_["id"]]
                    d["regions"] = ee.regions(int(q["scene"][0]))
                    return self.send_json(d)
                if path == "/api/flags":
                    fn = flag_names(project.root)
                    return self.send_json({"flags": [{"flag": k, "label": flag_label(k, fn)} for k in sorted(fn)],
                                           "search_targets": SEARCH_TARGETS})
                if path == "/api/export/status":
                    job = state.get("export")
                    if not job:
                        return self.send_json({"done": True, "ok": None, "log": [], "next": 0})
                    since = int(parse_qs(urlsplit(self.path).query).get("since", ["0"])[0])
                    return self.send_json({"done": job["done"], "ok": job["ok"], "error": job["error"],
                                           "result": job["result"], "log": job["log"][since:], "next": len(job["log"])})
                if path == "/api/check":
                    with write_lock:  # a consistent view, not half a save
                        return self.send_json(Checker(project, scenes(), names).run())
                m = re.fullmatch(r"/api/map/(\w+)/doors", path)
                if m and m.group(1) in project.maps:
                    doors = DoorEditor(project, scenes(), names).list(project.maps[m.group(1)])
                    return self.send_json({str(k): v for k, v in doors.items()})
                m = re.fullmatch(r"/api/scene/(\d+)/arrivals", path)
                if m:
                    sid = int(m.group(1))
                    rm = row_to_map()
                    sc = next((s for s in scenes().scenes if s["id"] == sid), None)
                    if sc is None:
                        return self.send_json({"error": "no such scene"}, 404)
                    info = project.maps.get(rm.get(sc["layered_row"]))
                    return self.send_json({
                        "scene": sid, "label": names.scene_label(sid),
                        "map": info.number if info else None,
                        "bounds": info.bounds if info else None,
                        "arrivals": [dict(a, sz=a["z"] - project.ground_height(info, a["x"], a["z"]) if info else a["z"])
                                     for a in DoorEditor(project, scenes(), names).entrances(sid)],
                    })
                m = re.fullmatch(r"/api/map/(\w+)/render\.png", path)
                if m and m.group(1) in project.maps:
                    n = m.group(1)
                    body = cache.get(("render", n), lambda: png(project.render(project.maps[n])))
                    return self.send_bytes(body, "image/png")
                m = re.fullmatch(r"/api/map/(\w+)/chests", path)
                if m and m.group(1) in project.maps:
                    return self.send_json(ChestEditor(project, scenes(), names).list(project.maps[m.group(1)]))
                m = re.fullmatch(r"/api/map/(\w+)/scenes", path)
                if m and m.group(1) in project.maps:
                    return self.send_json(map_scenes(m.group(1)))
                m = re.fullmatch(r"/api/map/(\w+)/layer/(\d)\.png", path)
                if m and m.group(1) in project.maps:
                    n, li = m.group(1), int(m.group(2))
                    info = project.maps[n]
                    if not info.tileset:
                        return self.send_json({"error": "no tileset known for this map"}, 404)
                    body = cache.get(("layer", n, li), lambda: png(project.render_layer(info, li)))
                    return self.send_bytes(body, "image/png")
                m = re.fullmatch(r"/api/map/(\w+)/atlas/(\d)\.png", path)
                if m and m.group(1) in project.maps:
                    n, base = m.group(1), int(m.group(2))
                    info = project.maps[n]
                    body = cache.get(("atlas", n, base), lambda: png(project.metatile_atlas(info, base)))
                    return self.send_bytes(body, "image/png")
                if path.startswith("/api/"):
                    return self.send_json({"error": "not found"}, 404)
            except Exception as e:  # report, don't kill the server
                traceback.print_exc()
                return self.send_json({"error": "Something went wrong in the editor. Your files are unchanged.",
                                       "detail": f"{type(e).__name__}: {e}"}, 500)
            return super().do_GET()

        def do_POST(self):
            if not host_allowed(self.headers, local_only):
                return self.send_json({"error": "forbidden"}, 403)
            path = self.path.split("?")[0]
            if not self.authorized() or self.authorized() == "query":
                return self.send_json({"error": "forbidden"}, 403)
            # Writes must come from the editor page itself: a custom header
            # (cross-site pages cannot send one without CORS, which we never
            # allow) and, when the browser sends it, a same-host Origin.
            origin = self.headers.get("Origin")
            host = self.headers.get("Host", "")
            if self.headers.get("X-GSMap") != "1" or (origin and urlsplit(origin).netloc != host):
                return self.send_json({"error": "cross-site write refused"}, 403)
            state["conn"] = None  # links may change
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > MAX_REQUEST:
                    return self.send_json({"error": "That file is too big."}, 413)
                body = json.loads(self.rfile.read(length) or b"{}")
                m = re.fullmatch(r"/api/map/(\w+)/edits", path)
                if m and m.group(1) in project.maps:
                    n = m.group(1)
                    with writing("your painting"):
                        try:
                            result = project.apply_edits(
                                project.maps[n], body.get("edits", []), body.get("markers", [])
                            )
                        except ValueError as e:
                            fsio.abort()
                            return self.send_json({"error": str(e)}, 409)
                        same = {o.number for o in project.maps.values()
                                if o.grid_path() == project.maps[n].grid_path()}
                        cache.drop(lambda k: k[1] in same and k[0] != "atlas")  # tiles are unchanged
                    result["saved"] = [os.path.relpath(s, project.root) for s in result["saved"]]
                    return self.send_json(result)
                if path in ("/api/scene-table", "/api/scene-table/revert"):
                    ovl, sym = int(body["overlay"]), body["symbol"]
                    o = scenes().overlay(ovl)
                    t = o.tables.get(sym)
                    forgetting = path.endswith("/revert") and Overrides(project.root).get(ovl, sym) is not None
                    if not forgetting and (t is None or not t["editable"]):
                        return self.send_json({"error": f"{sym} is not an editable table"}, 409)
                    with writing("a scene table change"):
                        ov = Overrides(project.root)
                        if path.endswith("/revert"):
                            ov.remove(ovl, sym)
                        else:
                            try:
                                validate_rows(t["kind"], body["rows"])
                            except (ValueError, KeyError, TypeError) as e:
                                fsio.abort()
                                return self.send_json({"error": str(e)}, 409)
                            ov.set(ovl, sym, t["kind"], body["rows"])
                        ov.save()
                        summary = generate(project.root, scenes(), ov)
                    return self.send_json({"ok": True, **summary})
                m = re.fullmatch(r"/api/map/(\w+)/chest", path)
                if m and m.group(1) in project.maps:
                    n = m.group(1)
                    ce = ChestEditor(project, scenes(), names)
                    x, z, action = int(body["x"]), int(body["z"]), body.get("action")
                    with writing("a chest change"):
                        try:
                            if action == "add":
                                r = ce.add(project.maps[n], x, z, body.get("contents", {}))
                            elif action == "contents":
                                r = ce.set_contents(project.maps[n], x, z, body.get("contents", {}))
                            elif action == "remove":
                                r = ce.remove(project.maps[n], x, z)
                            else:
                                return self.send_json({"error": "unknown chest action"}, 400)
                        except ValueError as e:
                            fsio.abort()
                            return self.send_json({"error": str(e)}, 409)
                        cache.drop(lambda k: k[1] == n and k[0] != "atlas")  # tiles are unchanged
                    return self.send_json({"ok": True, **r})
                if path == "/api/history/undo":
                    with write_lock:
                        label = fsio.undo_last(history)
                        forget_loaded()
                    return self.send_json({"ok": True, "label": label, "next": fsio.last_saved(history)})
                m = re.fullmatch(r"/api/map/(\w+)/reset", path)
                if m and m.group(1) in project.maps:
                    with writing("resetting a place"):
                        try:
                            r = reset_map(project, scenes(), names, project.maps[m.group(1)], setupmod.load_settings())
                        except ValueError as e:
                            fsio.abort()
                            return self.send_json({"error": str(e)}, 409)
                        forget_loaded()
                    return self.send_json({"ok": True, **r})
                if path == "/api/world/edits":
                    with writing("world map painting"):
                        w = world()
                        try:
                            before = worldmod.apply_world_edits(w, body.get("edits", []))
                        except ValueError as e:
                            fsio.abort()
                            state["world"] = None  # drop the half-applied copy
                            return self.send_json({"error": str(e)}, 409)
                        touched = {(int(e["gx"]) // 16, int(e["gy"]) // 16) for e in body.get("edits", [])}
                        cache.drop(lambda k: k[0] == "world" and k[1] in ("chunk", "walk", "kind") and (k[2], k[3]) in touched)
                    return self.send_json({"ok": True, "saved": len(body.get("edits", [])), "before": before})
                if path == "/api/world/icon":
                    de = DoorEditor(project, scenes(), names)
                    actor = int(body.get("actor", 0))
                    with writing("a town icon change"):
                        try:
                            if body.get("action") == "move":
                                r = worldmod.move_icon(project, scenes(), names, actor, int(body["x"]), int(body["z"]),
                                                       bool(body.get("move_arrivals", True)))
                                return self.send_json({"ok": True, **r})
                            trigger = int(body["trigger"]) if "trigger" in body else worldmod.ICON_TRIGGER + actor
                            r = de.relink_scene(worldmod.WORLD_SCENE, trigger,
                                                int(body["target_scene"]), int(body["target_entrance"]))
                        except ValueError as e:
                            fsio.abort()
                            return self.send_json({"error": str(e)}, 409)
                    return self.send_json({"ok": True, **r})
                m = re.fullmatch(r"/api/map/(\w+)/event", path)
                if m and m.group(1) in project.maps:
                    n = m.group(1)
                    ee = EventEditor(project, scenes(), names)
                    a, sid, tbl = body.get("action"), int(body["scene"]), body.get("table")
                    with writing("an event change"):
                        try:
                            if a == "text":
                                r = ee.set_text(sid, tbl, int(body["index"]), body["text"], bool(body.get("raw")))
                            elif a == "when":
                                r = ee.set_when(sid, tbl, int(body["index"]), body.get("when"))
                            elif a == "talk":
                                r = ee.add_talk(sid, tbl, int(body["actor"]), body["text"], body.get("when"))
                            elif a == "spot":
                                r = ee.add_spot(project.maps[n], sid, tbl, int(body["x"]), int(body["z"]), body["how"],
                                                body["text"], int(body.get("target", 0)), body.get("when"))
                            elif a == "remove":
                                r = ee.remove(project.maps[n], sid, tbl, int(body["index"]))
                            elif a == "person":
                                r = ee.add_person(sid, tbl, int(body["sprite"]), int(body["x"]), int(body["z"]),
                                                  body.get("text"), bool(body.get("wander")), body.get("when"))
                            elif a == "region":
                                r = ee.edit_region(sid, body["region_table"], int(body["index"]), body.get("box"),
                                                   body.get("target"), body.get("when"), bool(body.get("remove")))
                            else:
                                return self.send_json({"error": "unknown event action"}, 400)
                        except (ValueError, KeyError) as e:
                            fsio.abort()
                            return self.send_json({"error": str(e)}, 409)
                        cache.drop(lambda k: k[1] == n and k[0] != "atlas")  # tiles are unchanged
                    return self.send_json({"ok": True, **r})
                m = re.fullmatch(r"/api/map/(\w+)/door", path)
                if m and m.group(1) in project.maps:
                    n = m.group(1)
                    de = DoorEditor(project, scenes(), names)
                    action, sid = body.get("action"), int(body["scene"])
                    with writing("a door change"):
                        try:
                            if action == "relink":
                                r = de.relink(project.maps[n], sid, int(body["code"]),
                                              int(body["target_scene"]), int(body["target_entrance"]))
                            elif action == "add":
                                r = de.add(project.maps[n], sid, int(body["x"]), int(body["z"]),
                                           int(body["target_scene"]), int(body["target_entrance"]))
                            elif action == "remove":
                                r = de.remove(project.maps[n], sid, int(body["x"]), int(body["z"]))
                            else:
                                return self.send_json({"error": "unknown door action"}, 400)
                        except ValueError as e:
                            fsio.abort()
                            return self.send_json({"error": str(e)}, 409)
                        cache.drop(lambda k: k[1] == n and k[0] != "atlas")  # tiles are unchanged
                    return self.send_json({"ok": True, **r})
                m = re.fullmatch(r"/api/map/(\w+)/import-image", path)
                if m and m.group(1) in project.maps:
                    n = m.group(1)
                    data = body.get("png", "")
                    png = base64.b64decode(data.split(",", 1)[-1])
                    with writing("an imported image"):
                        try:
                            report = tilesetmod.import_image(
                                project, project.maps[n], png, int(body.get("layer", 1)),
                                dry_run=not body.get("apply"))
                        except ValueError as e:
                            fsio.abort()
                            return self.send_json({"error": str(e)}, 409)
                        if body.get("apply"):
                            cache.drop(lambda k: k[1] == n)
                    return self.send_json(report)
                if path == "/api/export":
                    job = state.get("export")
                    if job and not job["done"]:
                        return self.send_json({"error": "an export is already running"}, 409)
                    name = (body.get("name") or "").strip()
                    if not name:
                        return self.send_json({"error": "give your mod a name"}, 400)
                    job = {"done": False, "ok": None, "log": [], "result": None, "error": None}
                    state["export"] = job

                    def work():
                        try:
                            with write_lock:
                                refresh_mod(playable=False)  # what's shared has no test code in it
                                job["result"] = patchmod.export(
                                    project.root, EXPORTS, os.path.join(setupmod.CACHE, "stock"),
                                    setupmod.build_env(), job["log"].append, name,
                                    body.get("author", ""), body.get("description", ""),
                                    settings=setupmod.load_settings(), ips=bool(body.get("ips")))
                            job["ok"] = True
                        except Exception as e:  # shown to the player, in words
                            job["error"], job["ok"] = str(e), False
                        job["done"] = True
                    threading.Thread(target=work, daemon=True).start()
                    return self.send_json({"ok": True})
                if path == "/api/patcher":
                    job = state.get("export")
                    if job and not job["done"]:
                        return self.send_json({"error": "an export or patch is still running"}, 409)
                    data = base64.b64decode(body.get("patch", "").split(",", 1)[-1])
                    rom = body.get("rom")
                    rom = base64.b64decode(rom.split(",", 1)[-1]) if rom else None
                    name = os.path.splitext(os.path.basename(body.get("name", "mod")))[0]
                    job = {"done": False, "ok": None, "log": [], "result": None, "error": None}
                    state["export"] = job

                    def work():
                        try:
                            job["result"] = patchmod.patch_game(
                                project.root, os.path.join(setupmod.CACHE, "stock"), PATCHED,
                                setupmod.build_env(), job["log"].append, data, name, rom,
                                settings=setupmod.load_settings())
                            job["ok"] = True
                        except Exception as e:
                            job["error"], job["ok"] = str(e), False
                        job["done"] = True
                    threading.Thread(target=work, daemon=True).start()
                    return self.send_json({"ok": True})
                if path == "/api/play-file":
                    target = os.path.realpath(body.get("path", ""))
                    if not target.startswith(os.path.realpath(PATCHED) + os.sep) or not os.path.exists(target):
                        return self.send_json({"error": "not a patched game"}, 400)
                    if subprocess.run(["open", "-Ra", "mGBA"], capture_output=True).returncode != 0:
                        return self.send_json({"error": "Play needs mGBA, a free GBA emulator: install it from mgba.io."}, 404)
                    subprocess.Popen(["open", "-a", "mGBA", target])
                    return self.send_json({"ok": True})
                if path == "/api/reveal":
                    target = os.path.realpath(body.get("path", ""))
                    if not any(target.startswith(os.path.realpath(d) + os.sep) for d in (EXPORTS, PATCHED)) \
                            or not os.path.exists(target):
                        return self.send_json({"error": "not an exported file"}, 400)
                    subprocess.Popen(["open", "-R", target])
                    return self.send_json({"ok": True})
                if path == "/api/build":
                    target = body.get("target", "tbs-en")
                    if not re.fullmatch(r"(compare-)?tbs-(en|ja|de|es|fr|it)", target):
                        return self.send_json({"error": "unknown build target"}, 400)
                    with write_lock:
                        return self.send_json(run_build(target, True if body.get("playable") else None))
                if path == "/api/play":
                    rom = os.path.join(project.root, layout.ROM)
                    if not os.path.exists(rom):
                        return self.send_json({"error": "Your game hasn't been built yet."}, 404)
                    if subprocess.run(["open", "-Ra", "mGBA"], capture_output=True).returncode != 0:
                        return self.send_json({"error": "Play needs mGBA, a free GBA emulator: install it from "
                                                        "mgba.io, then press Play again."}, 404)
                    note = "Your game is open in mGBA."
                    if body.get("scene") is not None:
                        sid = int(body["scene"])
                        de = DoorEditor(project, scenes(), names)
                        arrivals = de.entrances(sid)
                        # Scene 0 is the title screen, where a game starts anyway.
                        if sid != 0 and arrivals:
                            rom = playtest.make_copy(project.root, os.path.join(setupmod.CACHE, "playing"),
                                                     sid, arrivals[0]["entrance"])
                            note = f"Your game is open in mGBA, at {names.scene_label(sid)}."
                    subprocess.Popen(["open", "-a", "mGBA", rom])
                    return self.send_json({"ok": True, "note": note})
                return self.send_json({"error": "not found"}, 404)
            except Exception as e:
                traceback.print_exc()
                return self.send_json({"error": "Something went wrong in the editor. Your files are unchanged.",
                                       "detail": f"{type(e).__name__}: {e}"}, 500)

    return Handler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser("~/gs_project/alchemy-port"))
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument(
        "--host", default="127.0.0.1",
        help="address to listen on; 0.0.0.0 for every network interface",
    )
    ap.add_argument(
        "--token",
        help="access token; generated automatically when --host is not loopback",
    )
    args = ap.parse_args()
    local = args.host in ("127.0.0.1", "localhost", "::1")
    token = args.token or (None if local else secrets.token_urlsafe(16))
    problems = preflight.check(args.root)
    if problems:
        print(f"{args.root} doesn't match what this editor expects:", *problems, sep="\n  ")
        raise SystemExit(1)
    project = Project(args.root)
    print(f"{len(project.maps)} maps from {args.root}", flush=True)
    shown = "127.0.0.1" if args.host in ("0.0.0.0", "::") else args.host
    suffix = f"/?token={token}" if token else "/"
    print(f"open http://{shown}:{args.port}{suffix}", flush=True)
    if not local:
        print("listening beyond this machine: anyone with the token can use the editor")
    ThreadingHTTPServer((args.host, args.port), make_handler(project, token, local_only=local)).serve_forever()


if __name__ == "__main__":
    main()
