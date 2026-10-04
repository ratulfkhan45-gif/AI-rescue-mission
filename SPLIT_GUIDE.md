# AI Rescue Mission – Final Update: Work Split

Algorithms in the final version: **BFS** (uninformed), **A\*** (informed),
**CSP**, **AC-3** and **Backtracking**. DFS and GBFS are not included.

Each folder below holds exactly the files that member owns, in the same
paths they have in the project. Copying all four folders into one place
gives the complete, working project.

| Member | Role | Owns |
|---|---|---|
| **Member 1 – Ratul F. Khan** | Environment + CSP model | `environment/` (road_network.py, road_shapes.py, scenario.py), `csp/csp.py`, `main.py`, `run.bat`, `requirements.txt`, `README.md`, `tests/` |
| **Member 2 – Esha** | Uninformed Search + Backtracking | `algorithms/bfs.py`, `algorithms/search_result.py`, `csp/backtracking.py` |
| **Member 3 – Tanisha** | Informed Search + AC-3 | `algorithms/astar.py`, `algorithms/utils.py` (straight-line heuristic), `csp/ac3.py` |
| **Member 4 – Proma** | GUI Core + Live Simulation | `web/` (server.py, index.html, style.css, app.js, Leaflet), `csp/simulation.py` |

## What each part does

**Member 1 – Environment + CSP model.**
Builds the road network of Old Dhaka and Keraniganj: intersections with
real coordinates, roads with lengths, real OpenStreetMap street shapes,
and OPEN / FLOODED / BLOCKED road status. Defines the scenario (rescue
vehicle, hospital, victims, ambulances, medical teams) and the CSP model
itself: variables (victims), domains (eligible resources) and the
constraints (type match, dispatch zone, safe-road reachability,
all-different).

**Member 2 – Uninformed Search + Backtracking.**
BFS explores the road network level by level and finds the route with
the fewest road segments. Backtracking is the depth-first search that
gives each victim a resource, undoing choices when a constraint fails.

**Member 3 – Informed Search + AC-3.**
A* uses f(n) = g(n) + h(n), with real road cost as g and straight-line
(haversine) distance as h, so it always finds the cheapest route. AC-3
prunes resources from victims' domains before backtracking runs.

**Member 4 – GUI Core + Live Simulation.**
The web interface: Leaflet map, animated search, results and comparison
table, road editing, victim dragging, and the local Python server that
connects the page to the algorithms. Also owns the live dispatch
simulation that moves resources every 3 seconds and hands conflicts to
AC-3 and backtracking.

## Pushing to GitHub (one branch per member)

Repo: `github.com/ratulfkhan45-gif/AI-lab-Project`

Each member, in Git Bash:

```bash
git clone https://github.com/ratulfkhan45-gif/AI-lab-Project.git
cd AI-lab-Project
git checkout -b final/<your-part>          # e.g. final/environment
# copy the CONTENTS of your member folder into the repo folder
git add .
git commit -m "Final update: <your part>"
git push -u origin final/<your-part>
```

Suggested branch names: `final/environment`, `final/uninformed-search`,
`final/informed-search`, `final/gui`.

**Merge order into main:** environment → uninformed-search →
informed-search → gui. Every part imports the others, so the project
only runs once all four are merged.

The `python-embed/` folder (portable Python for `run.bat`) is not in
any member folder because it is about 60 MB. Add it once on main after
merging, or have everyone run `python main.py` with their own Python.
