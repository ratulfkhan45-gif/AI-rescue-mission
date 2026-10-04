"""
test_all.py
-----------
Lightweight, dependency-free test suite (plain asserts - no pytest
required) covering the checks listed in the SRS "Testing" section:

    BFS: reachable target, obstacle handling, unreachable target
    A*: uses g(n)+h(n), finds the least-cost route
    CSP: variables/domains, constraint enforcement
    AC-3: removes inconsistent values, detects empty domains
    Backtracking: finds a valid assignment, reports failure correctly

Run with:  python -m tests.test_all
"""

from environment.road_network import RoadNetwork, OPEN, FLOODED, BLOCKED, haversine_km
from environment.scenario import build_default_scenario, Victim, Resource
from algorithms import bfs, astar
from csp.csp import build_initial_domains
from csp.ac3 import run_ac3
from csp.backtracking import run_backtracking

passed = 0
failed = 0


def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}")


def make_small_network():
    """A small road network shaped like a square with a diagonal:

        A ---- B ---- C
        |             |
        D ----------- E

    Coordinates are a few hundred metres apart so road lengths are
    realistic. The direct A-B-C road is the shortest.
    """
    n = RoadNetwork()
    n.add_node("A", "A", 23.7000, 90.4000, "north")
    n.add_node("B", "B", 23.7000, 90.4050, "north")
    n.add_node("C", "C", 23.7000, 90.4100, "north")
    n.add_node("D", "D", 23.6950, 90.4000, "north")
    n.add_node("E", "E", 23.6950, 90.4100, "north")
    n.add_road("A", "B")
    n.add_road("B", "C")
    n.add_road("A", "D")
    n.add_road("D", "E")
    n.add_road("E", "C")
    return n


def test_search_algorithms():
    print("Search algorithms:")
    algs = [("BFS", bfs), ("A*", astar)]

    # Detour: block the direct road, a route still exists via D-E.
    net = make_small_network()
    net.set_status("A", "B", BLOCKED)
    for name, module in algs:
        result = module.search(net, "A", "C")
        check(f"{name} finds a route around the blocked road", result.found)
        check(f"{name} path starts at the start node", result.path[0] == "A")
        check(f"{name} path ends at the goal node", result.path[-1] == "C")
        check(f"{name} never uses the blocked road",
              all({u, v} != {"A", "B"} for u, v in zip(result.path, result.path[1:])))
        check(f"{name} records a positive number of explored nodes", result.nodes_explored > 0)

    # Unreachable target: block both ways into C.
    un = make_small_network()
    un.set_status("B", "C", BLOCKED)
    un.set_status("E", "C", BLOCKED)
    for name, module in algs:
        result = module.search(un, "A", "C")
        check(f"{name} correctly reports an unreachable target", not result.found)

    # A* must account for real cost: flood the short route so the longer
    # dry detour becomes cheaper. BFS (fewest roads) still takes the flood.
    fl = make_small_network()
    fl.set_status("A", "B", FLOODED)
    fl.set_status("B", "C", FLOODED)
    a_result = astar.search(fl, "A", "C")
    b_result = bfs.search(fl, "A", "C")
    check("A* path cost is never worse than BFS path cost", a_result.path_cost <= b_result.path_cost)
    check("A* avoids the flooded road when the dry detour is cheaper", "B" not in a_result.path)

    # Heuristic must be admissible: never more than any road's real length.
    net2 = make_small_network()
    check("Straight-line heuristic never overestimates a road's length",
          all(net2.heuristic(r.u, r.v) <= r.length_km + 1e-9 for r in net2.roads.values()))
    check("Haversine distance is ~0.51 km for 0.005 deg of longitude here",
          abs(haversine_km((23.7, 90.40), (23.7, 90.405)) - 0.509) < 0.01)


def test_csp_and_ac3_and_backtracking():
    print("CSP / AC-3 / Backtracking:")
    scenario = build_default_scenario()
    victim_ids = [v.id for v in scenario.victims]

    domains = build_initial_domains(scenario.grid, scenario.victims, scenario.resources)
    check("Every victim has a domain entry (CSP variables = victims)",
          set(domains.keys()) == set(victim_ids))
    check("Domains only contain resources of the matching type",
          all(
              all(
                  next(r for r in scenario.resources if r.id == rid).type == v.requirement
                  for rid in domains[v.id]
              )
              for v in scenario.victims
          ))

    ok, pruned, log = run_ac3(domains, victim_ids)
    check("AC-3 succeeds on the default (solvable) scenario", ok)
    check("No pruned domain is ever larger than its original domain",
          all(len(pruned[vid]) <= len(domains[vid]) for vid in victim_ids))

    # --- Genuine pruning case: no unit (dedicated or backup, ambulance or
    # medical team) is given priority any more, so the balanced default
    # scenario has no forced singleton domains for AC-3 to prune against.
    # This synthetic pair still proves AC-3 actually removes an
    # inconsistent value (not just detects a total failure): Y1's sole
    # option R1 must be pruned out of Y2's domain, leaving Y2 with R2.
    pruning_domains = {"Y1": ["R1"], "Y2": ["R1", "R2"]}
    ok_p, pruned_p, log_p = run_ac3(pruning_domains, ["Y1", "Y2"])
    check("AC-3 succeeds and prunes the shared value from the other domain",
          ok_p and pruned_p["Y2"] == ["R2"])

    success, assignment = run_backtracking(pruned)
    check("Backtracking finds a complete valid assignment", success)
    check("Every victim is assigned exactly one resource",
          set(assignment.keys()) == set(victim_ids))
    check("No resource is assigned to more than one victim",
          len(set(assignment.values())) == len(assignment.values()))

    # Flooding both bridges cuts the south bank off from north-bank and
    # backup units on safe roads, so the south victims lose those options.
    cut = build_default_scenario()
    cut.grid.set_status("MTF", "BBS", FLOODED)
    cut.grid.set_status("PTG", "PSS", FLOODED)
    cut_domains = build_initial_domains(cut.grid, cut.victims, cut.resources)
    check("Flooded bridges remove unreachable units from south-bank domains",
          cut_domains["V3"] == ["A2"] and cut_domains["V5"] == ["M2"])

    # --- Failure case: force two high-urgency victims to need the
    # same single dedicated resource with no backup allowed, and no
    # alternative resource available -> AC-3 should detect an empty
    # domain, OR backtracking should correctly report failure.
    conflict_domains = {"X1": ["R1"], "X2": ["R1"]}
    ok2, pruned2, log2 = run_ac3(conflict_domains, ["X1", "X2"])
    check("AC-3 detects an empty domain when two victims need the same sole resource",
          not ok2)

    success3, assignment3 = run_backtracking({"X1": ["R1"], "X2": ["R1"]})
    check("Backtracking correctly reports failure when no valid assignment exists",
          not success3)


def main():
    test_search_algorithms()
    test_csp_and_ac3_and_backtracking()
    print()
    print(f"TOTAL: {passed} passed, {failed} failed")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
