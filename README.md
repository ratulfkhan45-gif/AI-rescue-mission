# AI Rescue Mission - Intelligent Disaster Response Simulator

A Python project for an AI Lab course with an HTML/CSS web interface.
It simulates flood response on a **real-world road network** - Old
Dhaka and Keraniganj on either side of the Buriganga River - and
implements and demonstrates five classic AI techniques:

1. **BFS** - Uninformed Search
2. **A\*** - Informed Search
3. **CSP** - Constraint Satisfaction Problem (resource assignment)
4. **AC-3** - Arc Consistency
5. **Backtracking** - Final resource assignment

None of the algorithms are faked or hard-coded: every route, every
metric (nodes explored, distance, cost, runtime) and every CSP domain
and assignment is computed live in Python each time you click a button.

---

## Project Purpose

A rescue vehicle based at the **Fire Service HQ** must reach injured
victims, then take them to **Dhaka Medical College Hospital**. Some
riverside roads are flooded and one is blocked, and the south bank
(Keraniganj) can only be reached over two bridges - **Babubazar Bridge**
and **Postogola Bridge**. At the same time, the command center must
assign a limited set of ambulances and medical teams to victims under
real constraints (type, side of the river, safe roads, one unit per
victim).

---

## Why a Road Map Instead of a Grid?

| | Grid version | Road-map version |
|---|---|---|
| State space | grid cells | real intersections (latitude / longitude) |
| Actions | move up / down / left / right | drive along a road |
| Step cost | 1 per cell, 3 per hazard cell | road length in km, ×3 if flooded |
| Heuristic h(n) | Manhattan distance | straight-line (haversine) distance in km |

The straight-line heuristic is **admissible**: no road can be shorter
than the straight line between its two ends, and the flood multiplier
is ≥ 1, so h(n) never overestimates. That's why A\* is still
guaranteed to find the cheapest route.

---

## Technologies

- **Backend:** Python 3.9+ (standard library only - no pip installs)
  - all search, CSP, AC-3 and backtracking logic
  - a small local HTTP server with a JSON API (`http.server`)
- **Frontend:** HTML + CSS, a small JavaScript file, and
  [Leaflet](https://leafletjs.com/) (bundled in `web/static/vendor`,
  so it works offline) for the map
- **Map background:** OpenStreetMap tiles (needs internet - see
  *Offline use* below)

---

## How It Works

```
 Browser (HTML / CSS / JS + Leaflet)      Python (web/server.py)
 -----------------------------------      ------------------------------------
 click "Find rescue route"   -- POST -->  /api/route  -> bfs / astar
 animate explored nodes      <-- JSON --  explored order, path, km, cost, time
 click "Start simulation"    -- POST -->  /api/sim/*  -> csp + ac3 + backtracking
 click a road / drag victim  -- POST -->  /api/road, /api/move_victim
```

The browser never computes a route itself; it only displays what the
Python algorithms return.

---

## Project Structure

```
AI_Rescue_Mission/
│
├── main.py                  Entry point - starts the server, opens the browser
├── run.bat                  Windows double-click launcher (uses python-embed)
├── requirements.txt         (no third-party packages needed)
├── README.md
│
├── environment/
│   ├── __init__.py
│   ├── road_network.py      RoadNetwork graph: nodes, roads, costs, haversine heuristic
│   └── scenario.py          The Dhaka map data (NODES, ROADS), victims, resources
│
├── algorithms/
│   ├── __init__.py
│   ├── search_result.py     Shared SearchResult data container
│   ├── utils.py             Path reconstruction, path cost / distance, heuristic
│   ├── bfs.py               Breadth-First Search
│   └── astar.py             A* Search
│
├── csp/
│   ├── __init__.py
│   ├── csp.py               CSP model: variables, domains, constraints
│   ├── ac3.py               AC-3 arc-consistency algorithm
│   ├── backtracking.py      Backtracking search for final assignment
│   └── simulation.py        Live resource-dispatch simulation
│
├── web/
│   ├── __init__.py
│   ├── server.py            Local HTTP server + JSON API
│   └── static/
│       ├── index.html       Page structure
│       ├── style.css        All styling
│       ├── app.js           Map drawing, animation, button wiring
│       └── vendor/leaflet/  Leaflet map library (bundled for offline use)
│
├── tests/
│   ├── __init__.py
│   └── test_all.py          Plain-assert test suite (no pytest needed)
│
└── python-embed/            Portable Python for Windows (used by run.bat)
```

---

## How to Run

**Windows (easiest):** double-click `run.bat`. It uses the bundled
`python-embed`, so Python doesn't even need to be installed.

**Any OS with Python 3.9+:**

```bash
cd AI_Rescue_Mission
python main.py
```

Your browser opens automatically at `http://127.0.0.1:8000/`. If it
doesn't, open the address printed in the terminal. Keep the terminal
open while you use the page; press **Ctrl+C** in it to stop.

To run the tests: `python -m tests.test_all`

### Offline use

The street-map background comes from OpenStreetMap and needs internet.
Without it, the app still works fully: roads, intersections, markers
and a schematic Buriganga River are drawn on a plain background, and a
note appears in the corner of the map. You can also switch the
background off with **Street map background**.

---

## How to Use the Interface

1. **Pick an algorithm** - BFS / A\*.
2. **Pick a victim** - click a V1-V5 card or a red triangle on the map.
3. **Find rescue route** - animates the search from the Fire Service
   HQ to the victim, then on to the hospital. The orange-ringed dot is
   the intersection being expanded; blue dots are explored. When it
   finishes you get nodes explored, km driven, route cost and the list
   of places the route passes through. **Space** / **Enter** or
   **Skip animation** jumps to the end.
4. **Compare all algorithms** - runs all four on the same trip and fills
   the table (lowest values in green).
5. **Start simulation** - unassigned ambulances and medical teams move
   to a random intersection on their side of the river every 3 seconds.
   Each victim takes its nearest compatible unit (by safe-road
   distance); conflicts are solved with AC-3 + backtracking, and the log
   shows every step.
6. **Edit the roads** - turn on **Edit mode**, pick **Flood**, **Block**
   or **Reopen**, then click a road (click again to reopen it). Drag a
   victim onto another intersection to move it. **Reopen all roads**
   and **Restore default scenario** reset things.

Hover any road to see its name and length, or any marker to see what it is.

### Legend

| Symbol | Meaning |
|---|---|
| Blue circle | Rescue vehicle (Fire Service HQ) |
| Green cross | Hospital (Dhaka Medical College Hospital) |
| Red / purple triangle | Victim (purple = currently selected) |
| Teal square (A1-A3) | Ambulance |
| Violet square (M1-M3) | Medical team |
| Grey line | Open road |
| Orange dashed line | Flooded road (vehicle pays ×3; resources can't use it) |
| Red dotted line | Blocked road (impassable) |
| Light-blue dot | Explored intersection |
| Yellow line | Final route |

---

## The Map Data

All map data lives in `environment/scenario.py`:

- `NODES` - 53 intersections / landmarks with latitude, longitude and
  which bank of the river they are on.
- `ROADS` - 100 two-way roads and their starting status
  (`OPEN` / `FLOODED` / `BLOCKED`).

Coordinates are hand-placed approximations of each landmark (good to
roughly a hundred metres). Each road is drawn along the real street
between its two intersections: `environment/road_shapes.py` holds
OpenStreetMap street geometry, found by routing between the intersections
over the OSM drivable network, and each road's length is measured along
that path. To use another area, edit `NODES` and `ROADS` - nothing else needs to change.

---

## Algorithm Explanations

### BFS (Breadth-First Search)
Expands intersections level by level using a FIFO queue, so it finds
the route with the **fewest road segments**. It ignores road lengths
and flooding, so its route is often not the shortest or cheapest.

### A\* Search
**f(n) = g(n) + h(n)**, where g(n) is the real road cost driven so far
(km, flooded roads ×3) and h(n) is the straight-line (haversine)
distance to the goal. Because h(n) never overestimates, A\* always
finds the cheapest route.

### CSP (Constraint Satisfaction Problem)
- **Variables** = victims
- **Domains** = the resources each victim could legally receive
- **Constraints**:
  1. Resource type must match the victim's need (ambulance / medical team).
  2. Dispatch area: dedicated units serve only their own bank of the
     river (north = Old Dhaka, south = Keraniganj); backup units (A3,
     M3) serve both.
  3. The unit must have a **safe route** to the victim using only open
     roads (no flooded or blocked roads), checked with Dijkstra's
     algorithm on the real road lengths.
  4. No resource may be assigned to two victims at once (all-different).

### AC-3 (Arc Consistency Algorithm #3)
Enforces arc consistency over the "no shared resource" constraint
between every pair of victims. Whenever one victim's domain is
reduced to a single resource, AC-3 removes that resource from every
other victim's domain that also contained it, and repeats until no
further pruning is possible (or a domain becomes empty, signalling no
solution exists). The simulation log on the page shows every AC-3 pruning step and
backtracking assignment as it happens.

### Backtracking
After AC-3, backtracking picks the most-constrained unassigned victim
(the one with the fewest remaining candidate resources), tries each
candidate resource, checks the all-different constraint, and recurses.
If a choice leads to a dead end, it undoes the assignment and tries
the next candidate, backtracking further if necessary, until either a
complete valid assignment is found or every option is exhausted.

---

## Performance Metrics

For every route search, the application measures, live:
- **Nodes Explored** - how many intersections the algorithm expanded.
- **Distance** - physical length of the route in km.
- **Cost** - the value the algorithms optimise: km, with flooded roads
  counted ×3.
- **Runtime** - wall-clock time of the search (`time.perf_counter()`).

---

## Example Demonstration Workflow (for the viva)

1. Double-click `run.bat` - the Dhaka map loads in the browser.
2. Select victim **V5** (Hasnabad, south bank). Run **BFS**, then
   **A\*** - BFS only counts road segments and can pay for the flooded
   Aganagar–Kalindi road; A\* goes via Jinjira and is clearly cheaper.
3. Click **Compare all algorithms** - show nodes, km, cost and runtime
   side by side.
4. Turn on **Edit mode**, choose **Block**, and click **Babubazar
   Bridge**. Compare again - every algorithm must now use Postogola
   Bridge, and A\* re-plans automatically.
5. Explain why A\* stays optimal: the straight-line distance never
   overestimates the real road distance.
6. Click **Start simulation** and walk through the log: direct
   allocations, and the AC-3 / backtracking hand-off when victims
   compete for the same unit.
7. Mention the automated test suite (`python -m tests.test_all`).

---

## Testing

Run:
```bash
python -m tests.test_all
```
This exercises: BFS / A\* on a small road network with a
blocked road (detour) and with the goal cut off (unreachable); A\*
choosing a dry detour over flooded roads while BFS doesn't; that the
haversine heuristic never overestimates a road's length; CSP domain
construction, including flooded bridges cutting the south bank off;
AC-3 pruning and empty-domain detection; and backtracking success and
failure.
