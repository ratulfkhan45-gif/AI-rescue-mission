# Informed Search + AC-3 (Member 3)

## A* (algorithms/astar.py)
- Expands the node with the smallest f(n) = g(n) + h(n).
- g(n): real road cost so far (km, flooded roads cost more).
- h(n): straight-line (haversine) distance to the goal.
- Finds the cheapest route because h(n) never overestimates.

## Helpers (algorithms/utils.py)
- reconstruct_path, path_cost, path_length_km, straight_line.

## AC-3 (csp/ac3.py)
- Prunes resources from victims' domains before backtracking runs.
- Uses the "no two victims share a resource" (not-equal) constraint.
- Returns (success, domains, log). Fails only if a domain becomes empty.
