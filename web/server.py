"""
server.py
---------
A small local web server that replaces the Pygame window with an
HTML/CSS/JS front end. It uses ONLY the Python standard library (no
Flask needed), so the bundled python-embed works as-is.

All the real work - BFS / A*, the CSP domains, AC-3 and
backtracking - still runs in the existing Python modules. The browser
only draws the results and sends user actions back as JSON.

Run from the project root:
    python web_main.py
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from environment.scenario import build_default_scenario
from environment.road_network import OPEN, FLOODED, BLOCKED, FLOOD_MULTIPLIER
from algorithms import bfs, astar
from algorithms.utils import path_length_km
from csp.simulation import simulation_tick

ALG_MODULES = {"BFS": bfs, "A*": astar}
ALGORITHMS = ["BFS", "A*"]
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


class AppState:
    """Holds the one live scenario that the browser is looking at."""

    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        self.scenario = build_default_scenario()
        self.sim_assignment = {}
        self.sim_log = []

    @property
    def grid(self):
        return self.scenario.grid

    # ---------------- serialisation ---------------- #
    def snapshot(self):
        s = self.scenario
        net = s.grid
        return {
            "nodes": [
                {"id": n.id, "name": n.name, "lat": n.lat, "lon": n.lon, "area": n.area}
                for n in net.nodes.values()
            ],
            "roads": [
                {"u": r.u, "v": r.v, "length_km": r.length_km, "status": r.status,
                 "shape": [list(p) for p in r.shape]}
                for r in net.roads.values()
            ],
            "flood_multiplier": FLOOD_MULTIPLIER,
            "vehicle": s.vehicle_pos,
            "hospital": s.hospital_pos,
            "victims": [
                {"id": v.id, "pos": v.pos, "urgency": v.urgency,
                 "requirement": v.requirement}
                for v in s.victims
            ],
            "resources": [
                {"id": r.id, "type": r.type, "pos": r.pos,
                 "zone": list(r.zone), "backup": r.backup}
                for r in s.resources
            ],
            "sim": {"assignment": self.sim_assignment, "log": self.sim_log[-40:]},
        }

    def _victim(self, victim_id):
        for v in self.scenario.victims:
            if v.id == victim_id:
                return v
        return None

    # ---------------- search ---------------- #
    def route(self, algorithm, victim_id):
        if algorithm not in ALG_MODULES:
            return {"error": f"Unknown algorithm '{algorithm}'."}
        victim = self._victim(victim_id)
        if victim is None:
            return {"error": "Select a victim first."}

        module = ALG_MODULES[algorithm]
        s = self.scenario
        leg1 = module.search(s.grid, s.vehicle_pos, victim.pos)
        legs = [leg1]
        if leg1.found:
            legs.append(module.search(s.grid, victim.pos, s.hospital_pos))

        found = all(l.found for l in legs) and len(legs) == 2
        return {
            "algorithm": algorithm,
            "victim": victim_id,
            "found": found,
            "failed_leg": None if found else len(legs),
            "legs": [
                {
                    "found": l.found,
                    "explored": list(l.explored_order),
                    "path": list(l.path),
                    "distance_km": path_length_km(s.grid, l.path),
                    "nodes": l.nodes_explored,
                    "cost": l.path_cost,
                    "runtime_ms": l.runtime_ms,
                }
                for l in legs
            ],
            "nodes": sum(l.nodes_explored for l in legs),
            "cost": sum(l.path_cost for l in legs),
            "runtime_ms": sum(l.runtime_ms for l in legs),
            "distance_km": sum(path_length_km(s.grid, l.path) for l in legs),
        }

    def compare(self, victim_id):
        if self._victim(victim_id) is None:
            return {"error": "Select a victim first."}
        rows = []
        for alg in ALGORITHMS:
            r = self.route(alg, victim_id)
            rows.append({"algorithm": alg, "found": r["found"], "nodes": r["nodes"],
                         "cost": r["cost"], "distance_km": r["distance_km"],
                         "runtime_ms": r["runtime_ms"]})
        return {"victim": victim_id, "rows": rows}

    # ---------------- map editing ---------------- #
    def _protected(self):
        s = self.scenario
        return {s.vehicle_pos, s.hospital_pos} | {v.pos for v in s.victims}

    def _invalidate_sim(self):
        self.sim_assignment = {}
        self.sim_log = []

    def set_road(self, u, v, tool):
        if tool not in (OPEN, FLOODED, BLOCKED):
            return {"error": "Unknown road tool."}
        road = self.grid.road(u, v)
        if road is None:
            return {"error": "That road doesn't exist."}
        new_status = OPEN if road.status == tool else tool
        self.grid.set_status(u, v, new_status)
        self._invalidate_sim()
        return {"ok": True, "status": new_status,
                "name": f"{self.grid.name(road.u)} – {self.grid.name(road.v)}"}

    def move_victim(self, victim_id, node_id):
        victim = self._victim(victim_id)
        if victim is None:
            return {"error": "Unknown victim."}
        if not self.grid.has_node(node_id):
            return {"error": "Drop the victim on an intersection."}
        if node_id in self._protected() or any(r.pos == node_id for r in self.scenario.resources):
            return {"error": f"Can't move {victim_id} there - that spot is already occupied."}
        victim.pos = node_id
        self._invalidate_sim()
        return {"ok": True, "name": self.grid.name(node_id)}

    def reopen_all(self):
        for road in self.grid.roads.values():
            road.status = OPEN
        self._invalidate_sim()
        return {"ok": True}

    # ---------------- live CSP simulation ---------------- #
    def sim_start(self):
        self._invalidate_sim()
        return self.sim_tick()

    def sim_tick(self):
        s = self.scenario
        step_log = simulation_tick(s.grid, s.vehicle_pos, s.hospital_pos,
                                   s.victims, s.resources, self.sim_assignment)
        self.sim_log = (self.sim_log + step_log)[-40:]
        done = len(self.sim_assignment) == len(s.victims)
        return {"ok": True, "done": done, "step_log": step_log}


STATE = AppState()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            return {}

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/state":
            with STATE.lock:
                return self._send_json(STATE.snapshot())
        if path == "/":
            path = "/index.html"
        file_path = os.path.normpath(os.path.join(STATIC_DIR, path.lstrip("/")))
        if not file_path.startswith(STATIC_DIR + os.sep) or not os.path.isfile(file_path):
            self.send_error(404)
            return
        ext = os.path.splitext(file_path)[1]
        with open(file_path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        data = self._read_json()
        path = self.path.split("?")[0]
        with STATE.lock:
            try:
                if path == "/api/route":
                    result = STATE.route(data.get("algorithm"), data.get("victim"))
                elif path == "/api/compare":
                    result = STATE.compare(data.get("victim"))
                elif path == "/api/road":
                    result = STATE.set_road(data["u"], data["v"], data.get("tool"))
                elif path == "/api/move_victim":
                    result = STATE.move_victim(data.get("id"), data["node"])
                elif path == "/api/reopen_all":
                    result = STATE.reopen_all()
                elif path == "/api/reset_scenario":
                    STATE.reset()
                    result = {"ok": True}
                elif path == "/api/sim/start":
                    result = STATE.sim_start()
                elif path == "/api/sim/tick":
                    result = STATE.sim_tick()
                else:
                    return self.send_error(404)
            except (KeyError, ValueError, TypeError):
                result = {"error": "Bad request."}
            result["state"] = STATE.snapshot()
        self._send_json(result, 400 if "error" in result else 200)


def run(host="127.0.0.1", port=8000, open_browser=True):
    server = None
    for p in range(port, port + 20):  # fall back if 8000 is busy
        try:
            server = ThreadingHTTPServer((host, p), Handler)
            port = p
            break
        except OSError:
            continue
    if server is None:
        raise SystemExit("Could not find a free port between 8000 and 8019.")
    url = f"http://{host}:{port}/"
    print(f"AI Rescue Mission is running at {url}")
    print("Press Ctrl+C in this window to stop the server.")
    if open_browser:
        import webbrowser
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
