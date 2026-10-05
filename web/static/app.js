/* AI Rescue Mission - browser side (road-network map version).
   The browser only draws and animates. Every search, CSP domain, AC-3
   pass and backtracking assignment is computed by the Python modules
   through the small JSON API in web/server.py. */

const ALGORITHMS = ["BFS", "A*"];
const ALG_HINTS = {
  "BFS": "Uninformed. Expands intersections level by level with a queue, so it finds the fewest road segments but ignores road length and flooding.",
  "A*": "Informed, f(n) = g(n) + h(n): real road cost so far plus straight-line distance to the goal. Finds the cheapest route."
};
const SIM_TICK_MS = 3000;
const COLORS = {
  road: "#48525c", flooded: "#1677ff", blocked: "#b42318",
  route: "#f2c12e", explored: "#a9c8e8", vehicle: "#2459a8", orange: "#e4572e",
};

const ui = {
  status: document.getElementById("status"),
  map: document.getElementById("map"),
  mapNote: document.getElementById("mapNote"),
  tilesToggle: document.getElementById("tilesToggle"),
  btnSat: document.getElementById("btnSat"),
  btnFit: document.getElementById("btnFit"),
  algGroup: document.getElementById("algGroup"),
  algHint: document.getElementById("algHint"),
  victimGroup: document.getElementById("victimGroup"),
  btnRoute: document.getElementById("btnRoute"),
  btnCompare: document.getElementById("btnCompare"),
  btnSkip: document.getElementById("btnSkip"),
  btnClearView: document.getElementById("btnClearView"),
  speed: document.getElementById("speed"),
  lastRun: document.getElementById("lastRun"),
  compareBody: document.getElementById("compareBody"),
  compareNote: document.getElementById("compareNote"),
  btnSim: document.getElementById("btnSim"),
  assignments: document.getElementById("assignments"),
  simLog: document.getElementById("simLog"),
  editToggle: document.getElementById("editToggle"),
  toolGroup: document.getElementById("toolGroup"),
  btnClearObs: document.getElementById("btnClearObs"),
  btnRestore: document.getElementById("btnRestore"),
};

const app = {
  data: null,
  nodes: new Map(),         // id -> node
  alg: "A*",
  victimId: null,
  editMode: false,
  tool: "FLOODED",
  explored: new Set(),      // node ids
  frontier: null,
  path: [],                 // ordered node ids
  results: {},
  resultsVictim: null,
  animating: false,
  skip: false,
  simTimer: null,
};

const sleep = (ms) => new Promise((res) => setTimeout(res, ms));
const ll = (id) => { const n = app.nodes.get(id); return [n.lat, n.lon]; };
const nodeName = (id) => app.nodes.get(id).name;

/* ---------------- Leaflet map ---------------- */
const map = L.map("map", { zoomSnap: 0.25, zoomDelta: 0.5, keyboard: false });
map.attributionControl.setPrefix(false);   // hide the optional "Leaflet" flag; data credits stay
map.createPane("river").style.zIndex = 405;
map.createPane("roads").style.zIndex = 410;
map.createPane("route").style.zIndex = 420;
map.createPane("nodes").style.zIndex = 430;
map.createPane("roadHits").style.zIndex = 440;

const tiles = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
});
/* Satellite imagery (Esri World Imagery) with a place-name overlay. */
const satTiles = L.layerGroup([
  L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 19,
    attribution: "Imagery &copy; Esri, Maxar, Earthstar Geographics",
  }),
  L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 19, opacity: 0.9,
  }),
]);
let satellite = false;
const baseLayer = () => (satellite ? satTiles : tiles);

/* Schematic Buriganga River, drawn only when the real street map isn't
   showing (tiles switched off or offline), so the bridges still make
   sense. With tiles on, the real river on the map is used instead. */
const river = L.polyline(
  [[23.7085, 90.372], [23.7075, 90.385], [23.7072, 90.398], [23.7048, 90.408],
   [23.7005, 90.416], [23.6925, 90.4235], [23.6885, 90.432], [23.6880, 90.440]],
  { pane: "river", color: "#9cc3e0", weight: 22, opacity: 0.9, lineCap: "round", interactive: false }
).bindTooltip("Buriganga River (schematic)", { permanent: true, direction: "center", className: "river-tip", interactive: false });

function showRiver(on) {
  if (on && !map.hasLayer(river)) river.addTo(map);
  if (!on && map.hasLayer(river)) map.removeLayer(river);
}

let tileLoaded = false, tileErrors = 0;
tiles.on("tileload", () => { tileLoaded = true; ui.mapNote.hidden = true; showRiver(false); });
tiles.on("tileerror", () => {
  tileErrors += 1;
  if (!tileLoaded && tileErrors >= 4) {
    ui.mapNote.textContent = "The street map couldn't load (no internet?). Roads and intersections are still drawn and everything works.";
    ui.mapNote.hidden = false;
    showRiver(true);
  }
});
tiles.addTo(map);

const layers = {
  roads: L.layerGroup().addTo(map),
  route: L.layerGroup().addTo(map),
  nodes: L.layerGroup().addTo(map),
  hits: L.layerGroup().addTo(map),
  icons: L.layerGroup().addTo(map),
};
const nodeMarkers = new Map();   // id -> circleMarker

function fitMap() {
  const pts = app.data.nodes.map((n) => [n.lat, n.lon]);
  const wide = window.innerWidth > 760;
  const panelOpen = wide && !document.body.classList.contains("panel-hidden");
  map.fitBounds(L.latLngBounds(pts), {
    paddingTopLeft: [wide ? 40 : 16, wide ? 130 : 90],
    paddingBottomRight: [panelOpen ? 440 : 40, wide ? 70 : window.innerHeight * 0.46 + 20],
  });
}

/* ---------------- server calls ---------------- */
async function api(path, body) {
  const opts = body === undefined
    ? {}
    : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  let res;
  try {
    res = await fetch(path, opts);
  } catch (e) {
    setStatus("Lost connection to the Python server. Check the terminal window is still running.", true);
    throw e;
  }
  const json = await res.json();
  if (json.state) setData(json.state);
  else if (body === undefined) setData(json);
  return json;
}

function setData(d) {
  app.data = d;
  app.nodes = new Map(d.nodes.map((n) => [n.id, n]));
}

/* ---------------- status ---------------- */
function setStatus(msg, isError = false) {
  ui.status.textContent = msg;
  ui.status.classList.toggle("error", isError);
}

/* ---------------- rendering: map ---------------- */
function roadStyle(status) {
  if (satellite) {   // brighter lines so they stand out on aerial imagery
    if (status === "FLOODED") return { color: "#38c8ff", weight: 5, opacity: 1, dashArray: "8 6" };
    if (status === "BLOCKED") return { color: "#ff4d4d", weight: 4, opacity: 1, dashArray: "2 7", lineCap: "round" };
    return { color: "#ffffff", weight: 4, opacity: 0.95 };
  }
  if (status === "FLOODED") return { color: COLORS.flooded, weight: 5, opacity: 0.95, dashArray: "8 6" };
  if (status === "BLOCKED") return { color: COLORS.blocked, weight: 4, opacity: 0.9, dashArray: "2 7", lineCap: "round" };
  return { color: COLORS.road, weight: 4, opacity: 0.85 };
}

function renderRoads() {
  layers.roads.clearLayers();
  layers.hits.clearLayers();
  for (const r of app.data.roads) {
    const coords = [ll(r.u), ...(r.shape || []), ll(r.v)];
    if (satellite) L.polyline(coords, { pane: "roads", interactive: false, color: "#000", weight: 8, opacity: 0.55 }).addTo(layers.roads);
    L.polyline(coords, { pane: "roads", interactive: false, ...roadStyle(r.status) }).addTo(layers.roads);

    const label = { OPEN: "open", FLOODED: `flooded, cost ×${app.data.flood_multiplier}`, BLOCKED: "blocked" }[r.status];
    const hit = L.polyline(coords, { pane: "roadHits", weight: 18, opacity: 0, className: "road-hit" })
      .bindTooltip(`${nodeName(r.u)} to ${nodeName(r.v)}<br>${r.length_km.toFixed(2)} km, ${label}`,
                   { sticky: true, className: "node-tip" })
      .on("click", () => { if (app.editMode && !app.animating) setRoad(r.u, r.v); });
    hit.addTo(layers.hits);
  }
}

function nodeStyle(id) {
  if (id === app.frontier) return { radius: 8, color: COLORS.orange, weight: 3, fillColor: COLORS.explored, fillOpacity: 1 };
  if (app.explored.has(id)) return { radius: 6.5, color: COLORS.vehicle, weight: 1.5, fillColor: COLORS.explored, fillOpacity: 1 };
  return { radius: 4, color: COLORS.road, weight: 1.5, fillColor: "#ffffff", fillOpacity: 1 };
}

function renderNodes() {
  layers.nodes.clearLayers();
  nodeMarkers.clear();
  for (const n of app.data.nodes) {
    const m = L.circleMarker([n.lat, n.lon], { pane: "nodes", ...nodeStyle(n.id) })
      .bindTooltip(n.name, { className: "node-tip", direction: "top", offset: [0, -6] });
    m.addTo(layers.nodes);
    nodeMarkers.set(n.id, m);
  }
}

function restyleNode(id) {
  const m = nodeMarkers.get(id);
  if (m) m.setStyle(nodeStyle(id)).setRadius(nodeStyle(id).radius);
}

function restyleAllNodes() {
  for (const id of nodeMarkers.keys()) restyleNode(id);
}

function renderRoute() {
  layers.route.clearLayers();
  if (app.path.length < 2) return;
  const coords = [ll(app.path[0])];
  for (let i = 1; i < app.path.length; i++) {
    const a = app.path[i - 1], b = app.path[i];
    const r = app.data.roads.find(x => (x.u === a && x.v === b) || (x.u === b && x.v === a));
    const bends = r && r.shape ? (r.u === a ? r.shape : [...r.shape].reverse()) : [];
    coords.push(...bends, ll(b));
  }
  L.polyline(coords, { pane: "route", color: "#1c2733", weight: 11, opacity: 0.35, interactive: false }).addTo(layers.route);
  L.polyline(coords, { pane: "route", color: COLORS.route, weight: 7, opacity: 1, interactive: false }).addTo(layers.route);
}

function divIcon(html, size) {
  return L.divIcon({ className: "mk-wrap", html, iconSize: [size, size], iconAnchor: [size / 2, size / 2] });
}

function renderIcons() {
  layers.icons.clearLayers();
  const d = app.data;
  const assignedRes = new Set(Object.values(d.sim.assignment));

  L.marker(ll(d.vehicle), { icon: divIcon('<span class="mk mk-vehicle"></span>', 20), keyboard: false })
    .bindTooltip(`Rescue vehicle at ${nodeName(d.vehicle)}`, { className: "node-tip", direction: "top", offset: [0, -10] })
    .addTo(layers.icons);
  L.marker(ll(d.hospital), { icon: divIcon('<span class="mk mk-hospital"></span>', 24), keyboard: false })
    .bindTooltip(nodeName(d.hospital), { className: "node-tip", direction: "top", offset: [0, -12] })
    .addTo(layers.icons);

  for (const r of d.resources) {
    const cls = `mk mk-res ${r.type}${assignedRes.has(r.id) ? " assigned" : ""}`;
    const kind = r.type === "ambulance" ? "Ambulance" : "Medical team";
    const zone = r.backup ? "backup, both banks" : `${r.zone[0]} bank only`;
    L.marker(ll(r.pos), { icon: divIcon(`<span class="${cls}">${r.id}</span>`, 26), keyboard: false, zIndexOffset: 100 })
      .bindTooltip(`${kind} ${r.id} at ${nodeName(r.pos)} (${zone})`, { className: "node-tip", direction: "top", offset: [0, -13] })
      .addTo(layers.icons);
  }

  for (const v of d.victims) {
    const sel = v.id === app.victimId ? " selected" : "";
    const m = L.marker(ll(v.pos), {
      icon: divIcon(`<span class="mk-victim-outline"><span class="mk mk-victim${sel}" style="width:28px;height:26px">${v.id.slice(1)}</span></span>`, 28),
      draggable: app.editMode && !app.animating,
      keyboard: false,
      zIndexOffset: 200,
    });
    m.bindTooltip(`${v.id} at ${nodeName(v.pos)}: needs ${v.requirement === "ambulance" ? "an ambulance" : "a medical team"}`,
                  { className: "node-tip", direction: "top", offset: [0, -14] });
    m.on("click", () => selectVictim(v.id));
    m.on("dragend", (e) => dropVictim(v.id, e.target.getLatLng()));
    m.addTo(layers.icons);
  }
}

function renderMap() {
  renderRoads();
  renderRoute();
  renderNodes();
  renderIcons();
  ui.map.classList.toggle("editing", app.editMode);
}

/* ---------------- rendering: panel ---------------- */
function buildVictimButtons() {
  ui.victimGroup.innerHTML = "";
  for (const v of app.data.victims) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "victim-btn";
    b.setAttribute("role", "radio");
    b.dataset.victim = v.id;
    onPress(b, () => selectVictim(v.id));
    ui.victimGroup.appendChild(b);
  }
  updateVictimButtons();
}

function updateVictimButtons() {
  for (const b of ui.victimGroup.querySelectorAll("button")) {
    const v = app.data.victims.find((x) => x.id === b.dataset.victim);
    const need = v.requirement === "ambulance" ? "ambulance" : "medical team";
    b.innerHTML =
      `<strong>${v.id}</strong>` +
      `<small>${escapeHtml(nodeName(v.pos))}</small>` +
      `<small>Needs ${need}</small>`;
  }
}

function renderControls() {
  for (const b of ui.algGroup.querySelectorAll("button")) {
    b.setAttribute("aria-checked", String(b.dataset.alg === app.alg));
  }
  ui.algHint.textContent = ALG_HINTS[app.alg];

  for (const b of ui.victimGroup.querySelectorAll("button")) {
    b.setAttribute("aria-checked", String(b.dataset.victim === app.victimId));
  }

  for (const b of ui.toolGroup.querySelectorAll("button")) {
    b.setAttribute("aria-checked", String(b.dataset.tool === app.tool));
    b.disabled = !app.editMode;
  }

  const busy = app.animating;
  for (const el of [ui.btnRoute, ui.btnCompare, ui.btnClearView, ui.btnClearObs, ui.btnRestore,
                    ui.editToggle]) {
    el.disabled = busy;
  }
  ui.btnSkip.hidden = !busy;

  const simOn = app.simTimer !== null;
  ui.btnSim.textContent = simOn ? "Stop simulation" : "Start simulation";
  ui.btnSim.classList.toggle("running", simOn);
  ui.btnSim.disabled = busy;
}

function km(n) { return `${n.toFixed(2)} km`; }

function renderResults(last) {
  if (last) {
    const failNote = last.found ? "" :
      (last.failed_leg === 1 ? " (no route to the victim)" : " (no route on to the hospital)");
    const stops = last.found ? last.legs[0].path.concat(last.legs[1].path.slice(1)).map(nodeName) : [];
    ui.lastRun.className = "last-run";
    ui.lastRun.innerHTML =
      `<p class="title">${last.algorithm}: vehicle to ${last.victim} to hospital${failNote}</p>` +
      `<div class="metric"><b>${last.nodes}</b><span>nodes explored</span></div>` +
      `<div class="metric"><b>${last.found ? last.distance_km.toFixed(2) : "–"}</b><span>km driven</span></div>` +
      `<div class="metric"><b>${last.found ? last.cost.toFixed(2) : "–"}</b><span>route cost</span></div>` +
      (last.found ? `<p class="route-stops">${stops.map(escapeHtml).join(" › ")}</p>` : "");
  }

  const found = ALGORITHMS.map((a) => app.results[a]).filter((x) => x && x.found);
  const best = (f) => (found.length ? Math.min(...found.map(f)) : null);
  const bestNodes = best((x) => x.nodes);
  const bestCost = best((x) => x.cost);
  const bestDist = best((x) => x.distance_km);
  const mark = (val, b) => (found.length > 1 && Math.abs(val - b) < 1e-9 ? ' class="best"' : "");

  ui.compareBody.innerHTML = ALGORITHMS.map((a) => {
    const r = app.results[a];
    const current = a === app.alg ? ' class="current"' : "";
    if (!r) return `<tr${current}><td>${a}</td><td class="none">–</td><td class="none">–</td><td class="none">–</td><td class="none">–</td></tr>`;
    if (!r.found) return `<tr${current}><td>${a}</td><td>${r.nodes}</td><td class="none">no route</td><td class="none">–</td><td>${r.runtime_ms.toFixed(2)} ms</td></tr>`;
    return `<tr${current}><td>${a}</td><td${mark(r.nodes, bestNodes)}>${r.nodes}</td>` +
      `<td${mark(r.distance_km, bestDist)}>${km(r.distance_km)}</td>` +
      `<td${mark(r.cost, bestCost)}>${r.cost.toFixed(2)}</td><td>${r.runtime_ms.toFixed(2)} ms</td></tr>`;
  }).join("");

  ui.compareNote.textContent = app.resultsVictim
    ? `All rows are for vehicle to ${app.resultsVictim} to hospital. Cost is km with flooded roads counted ×${app.data.flood_multiplier}. Green marks the lowest value.`
    : "";
}

function renderSim() {
  const { assignment, log } = app.data.sim;
  const hasSim = app.simTimer !== null || Object.keys(assignment).length || log.length;
  ui.assignments.innerHTML = hasSim
    ? app.data.victims.map((v) => {
        const r = assignment[v.id];
        return `<li class="${r ? "done" : ""}"><b>${v.id}</b>${r || "waiting"}</li>`;
      }).join("")
    : "";

  ui.simLog.innerHTML = log.slice(-24).map((line) => {
    const cls = [];
    if (line.startsWith("  ")) cls.push("indent");
    if (line.includes("Conflict")) cls.push("conflict");
    else if (line.includes("assigned") || line.includes("allocated directly")) cls.push("assigned");
    return `<li class="${cls.join(" ")}">${escapeHtml(line.trim())}</li>`;
  }).join("");
  ui.simLog.scrollTop = ui.simLog.scrollHeight;
}

function renderAll(last) {
  renderMap();
  updateVictimButtons();
  renderControls();
  renderResults(last);
  renderSim();
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

/* ---------------- actions ---------------- */
/* Picking another algorithm or victim mid-animation cancels the run, so those
   buttons never need to be disabled (a disabled button just swallows the click). */
function interruptRun() {
  if (app.animating) { app.skip = true; app.abort = true; }
}

function selectVictim(id) {
  interruptRun();
  app.victimId = id;
  const v = app.data.victims.find((x) => x.id === id);
  setStatus(`Selected ${id} at ${nodeName(v.pos)} as the rescue target.`);
  renderIcons();
  renderControls();
}

function clearView() {
  app.explored = new Set();
  app.frontier = null;
  app.path = [];
}

function invalidateResults() {
  clearView();
  app.results = {};
  app.resultsVictim = null;
  ui.lastRun.className = "last-run empty";
  ui.lastRun.textContent = "Run a search to see nodes explored, distance, cost and runtime.";
  stopSim(false);
}

function rememberResult(r) {
  if (app.resultsVictim !== r.victim) {
    app.results = {};
    app.resultsVictim = r.victim;
  }
  app.results[r.algorithm] = {
    found: r.found, nodes: r.nodes, cost: r.cost, distance_km: r.distance_km, runtime_ms: r.runtime_ms,
  };
}

async function animateLeg(leg, keepPath) {
  // Each intersection is held a bit longer than a grid cell was, since
  // there are far fewer of them.
  const delay = Number(ui.speed.value) * 6;
  app.explored = new Set();
  app.frontier = null;
  app.path = keepPath.slice();
  renderRoute();
  restyleAllNodes();
  for (const id of leg.explored) {
    if (app.skip) break;
    const prev = app.frontier;
    app.explored.add(id);
    app.frontier = id;
    if (prev) restyleNode(prev);
    restyleNode(id);
    await sleep(delay);
  }
  const prev = app.frontier;
  app.frontier = null;
  if (prev) restyleNode(prev);
  for (const id of leg.explored) app.explored.add(id);
  app.path = keepPath.length ? keepPath.concat(leg.path.slice(1)) : leg.path.slice();
  restyleAllNodes();
  renderRoute();
  if (!app.skip) await sleep(Math.max(delay * 3, 200));
}

function showRouteInstantly(result) {
  app.explored = new Set();
  app.frontier = null;
  app.path = [];
  for (const leg of result.legs) {
    for (const id of leg.explored) app.explored.add(id);
  }
  if (result.found) app.path = result.legs[0].path.concat(result.legs[1].path.slice(1));
  else if (result.legs[0].found) app.path = result.legs[0].path.slice();
}

function routeStatus(r) {
  if (r.found) {
    return [`${r.algorithm}: route found, vehicle to ${r.victim} to hospital. ` +
      `${r.nodes} intersections explored, ${km(r.distance_km)} driven, route cost ${r.cost.toFixed(2)}, runtime ${r.runtime_ms.toFixed(2)} ms.`, false];
  }
  if (r.failed_leg === 1) return [`${r.algorithm}: no open route from the rescue vehicle to ${r.victim}. Reopen a road and try again.`, true];
  return [`${r.algorithm}: reached ${r.victim} but there's no open route on to the hospital.`, true];
}

const NEED_VICTIM = "Select a victim first, using the cards or by clicking a triangle on the map.";

async function findRoute() {
  if (!app.victimId) return setStatus(NEED_VICTIM, true);
  const r = await api("/api/route", { algorithm: app.alg, victim: app.victimId });
  if (r.error) return setStatus(r.error, true);

  app.animating = true;
  app.skip = false;
  app.abort = false;
  renderControls();
  renderIcons();
  setStatus(`${app.alg} is searching… press Space or Enter to skip the animation.`);

  let keep = [];
  try {
    for (const leg of r.legs) {
      await animateLeg(leg, keep);
      if (app.abort) break;
      if (!leg.found) break;
      keep = keep.length ? keep.concat(leg.path.slice(1)) : leg.path.slice();
    }
  } finally {
    app.animating = false;
  }
  if (app.abort) {            // the user picked something else; drop this run
    app.abort = false;
    clearView();
    renderAll();
    return;
  }
  showRouteInstantly(r);
  rememberResult(r);
  renderAll(r);
  setStatus(...routeStatus(r));
}

async function compareAll() {
  if (!app.victimId) return setStatus(NEED_VICTIM, true);
  const cmp = await api("/api/compare", { victim: app.victimId });
  if (cmp.error) return setStatus(cmp.error, true);
  app.results = {};
  app.resultsVictim = cmp.victim;
  for (const row of cmp.rows) {
    app.results[row.algorithm] = {
      found: row.found, nodes: row.nodes, cost: row.cost, distance_km: row.distance_km, runtime_ms: row.runtime_ms,
    };
  }
  const r = await api("/api/route", { algorithm: app.alg, victim: app.victimId });
  if (!r.error) showRouteInstantly(r);
  renderAll(r.error ? null : r);
  setStatus(`Compared BFS and A* on the same trip (vehicle to ${cmp.victim} to hospital). ` +
    `The map shows ${app.alg}; see the table for both.`);
}

/* ---------------- simulation ---------------- */
async function startSim() {
  const r = await api("/api/sim/start", {});
  app.simTimer = setInterval(simTick, SIM_TICK_MS);
  setStatus("Simulation running. Unassigned units move every 3 s; AC-3 and backtracking only step in on a conflict.");
  afterSimStep(r);
}

async function simTick() {
  if (app.simTimer === null) return;
  const r = await api("/api/sim/tick", {});
  afterSimStep(r);
}

function afterSimStep(r) {
  if (r.done) {
    stopSim(false);
    setStatus("Simulation complete: every victim has been allocated a resource.");
  }
  renderIcons();
  renderControls();
  renderSim();
}

function stopSim(announce = true) {
  if (app.simTimer !== null) {
    clearInterval(app.simTimer);
    app.simTimer = null;
    if (announce) setStatus("Simulation stopped. Positions and assignments are frozen.");
  }
}

/* ---------------- editing ---------------- */
async function setRoad(u, v) {
  const res = await api("/api/road", { u, v, tool: app.tool });
  if (res.error) { renderAll(); return setStatus(res.error, true); }
  invalidateResults();
  renderAll();
  const words = { OPEN: "reopened", FLOODED: "flooded", BLOCKED: "blocked" };
  setStatus(`Road ${res.name} is now ${words[res.status]}. Results cleared, so run the algorithms again.`);
}

async function dropVictim(victimId, latlng) {
  const p = map.latLngToContainerPoint(latlng);
  let bestId = null, bestDist = Infinity;
  for (const n of app.data.nodes) {
    const q = map.latLngToContainerPoint([n.lat, n.lon]);
    const d = Math.hypot(p.x - q.x, p.y - q.y);
    if (d < bestDist) { bestDist = d; bestId = n.id; }
  }
  const current = app.data.victims.find((v) => v.id === victimId).pos;
  if (bestDist > 40 || bestId === current) {
    renderIcons();
    if (bestDist > 40) setStatus("Drop the victim onto an intersection (a dot on a road).", true);
    return;
  }
  const res = await api("/api/move_victim", { id: victimId, node: bestId });
  if (res.error) { renderAll(); return setStatus(res.error, true); }
  invalidateResults();
  renderAll();
  setStatus(`${victimId} moved to ${res.name}. Results cleared, so run the algorithms again.`);
}

/* Act on the press itself rather than waiting for a full click: a click is
   dropped if the pointer drifts off the button between press and release,
   which made these buttons feel like they "missed". Keyboard activation
   (Enter/Space, which has detail === 0) still comes through "click". */
function onPress(el, handler) {
  el.addEventListener("pointerdown", (e) => { if (e.button === 0) handler(e); });
  el.addEventListener("click", (e) => { if (e.detail === 0) handler(e); });
}

/* ---------------- wiring ---------------- */
onPress(ui.algGroup, (e) => {
  const b = e.target.closest("button[data-alg]");
  if (!b) return;
  interruptRun();
  app.alg = b.dataset.alg;
  setStatus(`Algorithm set to ${app.alg}.`);
  renderControls();
  renderResults();
});

onPress(ui.toolGroup, (e) => {
  const b = e.target.closest("button[data-tool]");
  if (!b || b.disabled) return;
  app.tool = b.dataset.tool;
  setStatus(`Road tool: ${b.textContent.trim()}. Click a road on the map to apply it.`);
  renderControls();
});

ui.editToggle.addEventListener("change", () => {
  app.editMode = ui.editToggle.checked;
  setStatus(app.editMode
    ? "Edit mode on. Click a road to flood, block or reopen it, or drag a victim onto another intersection."
    : "Edit mode off. Clicking a victim on the map selects it.");
  renderIcons();
  ui.map.classList.toggle("editing", app.editMode);
  renderControls();
});

ui.tilesToggle.addEventListener("change", () => {
  if (ui.tilesToggle.checked) {
    baseLayer().addTo(map);
    ui.map.classList.remove("no-tiles");
    showRiver(!satellite && !tileLoaded);
  } else {
    map.removeLayer(baseLayer());
    ui.map.classList.add("no-tiles");
    ui.mapNote.hidden = true;
    showRiver(true);
  }
});

ui.btnSat.addEventListener("click", () => {
  const on = ui.tilesToggle.checked;
  if (on) map.removeLayer(baseLayer());
  satellite = !satellite;
  document.body.classList.toggle("satellite", satellite);
  ui.btnSat.textContent = satellite ? "Street view" : "Satellite view";
  ui.btnSat.setAttribute("aria-pressed", String(satellite));
  if (on) {
    baseLayer().addTo(map);
    showRiver(!satellite && !tileLoaded);
    if (satellite) { ui.mapNote.hidden = true; showRiver(false); }
  }
  renderRoads();
});

ui.btnFit.addEventListener("click", fitMap);
ui.btnRoute.addEventListener("click", findRoute);
ui.btnCompare.addEventListener("click", compareAll);
ui.btnSkip.addEventListener("click", () => { app.skip = true; });
ui.btnClearView.addEventListener("click", () => {
  clearView();
  renderRoute();
  restyleAllNodes();
  setStatus("Route cleared from the map. The scenario itself is unchanged.");
});

ui.btnSim.addEventListener("click", () => {
  if (app.simTimer !== null) { stopSim(); renderControls(); renderSim(); }
  else startSim();
});

ui.btnClearObs.addEventListener("click", async () => {
  await api("/api/reopen_all", {});
  invalidateResults();
  renderAll();
  setStatus("Every road is open again. Run the algorithms again to see the new routes.");
});

ui.btnRestore.addEventListener("click", async () => {
  await api("/api/reset_scenario", {});
  invalidateResults();
  buildVictimButtons();
  renderAll();
  setStatus("Default disaster scenario restored.");
});

document.addEventListener("keydown", (e) => {
  if (app.animating && (e.key === " " || e.key === "Enter")) {
    e.preventDefault();
    app.skip = true;
  }
});

/* ---------------- start ---------------- */
(async function init() {
  await api("/api/state");
  fitMap();
  buildVictimButtons();
  renderAll();
  setStatus("Pick an algorithm and a victim, then find the rescue route.");
})();
