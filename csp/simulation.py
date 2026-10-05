"""
simulation.py
-------------
A live variant of the CSP resource-assignment story: instead of
resources sitting at fixed positions, every rescue-resource car
(A1-A3, M1-M3) that isn't yet allocated to a victim moves to a random
intersection inside its own dispatch area once per tick, then victims still
waiting for a resource each greedily reach for their nearest reachable,
type-compatible resource.

That greedy reach is what creates a genuine CSP conflict: if two
victims independently reach for the very same resource in one tick,
neither can simply take it (the existing all-different constraint
forbids one resource serving two victims) - so that resource, and only
that resource's competing victims, get handed to the same AC-3 +
backtracking pipeline csp.py's static demo uses. Victims with no
competition for their pick are assigned immediately; no conflict, no
need for the constraint solver.
"""

import random
from typing import Dict, List, Optional, Set, Tuple

from environment.road_network import RoadNetwork
from environment.scenario import Resource, Victim
from csp.csp import build_initial_domains, safe_distance_km
from csp.ac3 import run_ac3
from csp.backtracking import run_backtracking

Position = str   # node id
Assignment = Dict[str, str]


def random_open_position(network: RoadNetwork, zone: Tuple[str, ...],
                          forbidden: Set[Position]) -> Optional[Position]:
    """Picks a uniformly random intersection inside the given dispatch
    areas that has at least one OPEN road and isn't one of the forbidden
    positions (other cars, the vehicle, the hospital, a victim). Returns
    None if there is no free node, in which case the resource stays put."""
    candidates = [
        node_id for node_id, node in network.nodes.items()
        if node.area in zone
        and node_id not in forbidden
        and network.safe_neighbors(node_id)
    ]
    if not candidates:
        return None
    return random.choice(candidates)


def _domain_sorted_by_distance(grid: RoadNetwork, victim: Victim, domain: List[str],
                                resources_by_id: Dict[str, Resource]) -> List[str]:
    """The victim's domain, nearest resource first. Backtracking tries
    domain values in order, so feeding it distance order (instead of
    resources.py's fixed declaration order) means a victim's actual
    physical proximity - not which resource id happens to be declared
    first - decides which one it's tried against first."""
    scored = [
        (safe_distance_km(grid, resources_by_id[rid].pos, victim.pos), rid)
        for rid in domain
    ]
    scored = [pair for pair in scored if pair[0] is not None]
    scored.sort(key=lambda pair: pair[0])
    return [rid for _, rid in scored]


def _nearest_resource_id(grid: RoadNetwork, victim: Victim, domain: List[str],
                          resources_by_id: Dict[str, Resource]):
    """Of a victim's current (already type/zone/reachability filtered)
    domain, returns the id of the physically closest resource
    right now, or None if the domain is empty."""
    ordered = _domain_sorted_by_distance(grid, victim, domain, resources_by_id)
    return ordered[0] if ordered else None


def reposition_unallocated(grid: RoadNetwork, vehicle_pos: Position, hospital_pos: Position,
                            victims: List[Victim], resources: List[Resource],
                            assignment: Assignment, log: List[str]) -> None:
    """Every resource not already locked into `assignment` re-rolls a
    fresh random position inside its own zone. Allocated resources hold
    their position (they've found their victim and stop roaming)."""
    assigned_resource_ids = set(assignment.values())
    protected = {vehicle_pos, hospital_pos} | {v.pos for v in victims}

    for resource in resources:
        if resource.id in assigned_resource_ids:
            continue
        other_car_positions = {r.pos for r in resources if r.id != resource.id}
        new_pos = random_open_position(grid, resource.zone, protected | other_car_positions)
        if new_pos is not None:
            resource.pos = new_pos
            log.append(f"{resource.id} moved to {grid.name(new_pos)} (still unallocated).")


def simulation_tick(grid: RoadNetwork, vehicle_pos: Position, hospital_pos: Position,
                     victims: List[Victim], resources: List[Resource],
                     assignment: Assignment) -> List[str]:
    """Runs one simulation step, mutating `assignment` in place with any
    newly resolved victim -> resource pairs. Returns a human-readable
    log of what happened this tick, for the GUI to display."""
    log: List[str] = []
    reposition_unallocated(grid, vehicle_pos, hospital_pos, victims, resources, assignment, log)

    pending_victims = [v for v in victims if v.id not in assignment]
    if not pending_victims:
        return log

    resources_by_id = {r.id: r for r in resources}
    victims_by_id = {v.id: v for v in pending_victims}
    available_resources = [r for r in resources if r.id not in assignment.values()]
    domains = build_initial_domains(grid, pending_victims, available_resources)

    # Group pending victims whose domains share at least one resource -
    # not just the ones that happen to reach for the identical top pick
    # this instant. Two victims can share a resource in their domain
    # while each currently prefers something else closer; if we let the
    # one with more alternatives grab its pick immediately, it can
    # permanently starve the other, which then has no alternative left
    # and deadlocks forever (e.g. a flexible backup unit grabbed by a
    # victim who could also use a dedicated unit, leaving two
    # dedicated-only victims stuck fighting over one dedicated unit on
    # every future tick). Solving every such group together via AC-3 +
    # backtracking - which already picks the most-constrained victim
    # first - avoids that trap.
    parent = {vid: vid for vid in victims_by_id}

    def find(vid):
        while parent[vid] != vid:
            parent[vid] = parent[parent[vid]]
            vid = parent[vid]
        return vid

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    resource_first_seen_by: Dict[str, str] = {}
    for victim in pending_victims:
        for resource_id in domains[victim.id]:
            if resource_id in resource_first_seen_by:
                union(victim.id, resource_first_seen_by[resource_id])
            else:
                resource_first_seen_by[resource_id] = victim.id

    groups: Dict[str, List[str]] = {}
    for victim in pending_victims:
        groups.setdefault(find(victim.id), []).append(victim.id)

    for group_victim_ids in groups.values():
        if len(group_victim_ids) == 1:
            victim_id = group_victim_ids[0]
            pick = _nearest_resource_id(grid, victims_by_id[victim_id], domains[victim_id], resources_by_id)
            if pick is not None:
                assignment[victim_id] = pick
                log.append(f"{victim_id} reaches {pick} - no other victim can ever want it, allocated directly.")
            else:
                log.append(f"{victim_id}: no reachable matching resource this tick - will retry.")
            continue

        log.append(
            f"Conflict group {', '.join(group_victim_ids)} share overlapping resource options "
            "- handing off to AC-3 / backtracking."
        )
        # Backtracking's most-constrained-variable heuristic breaks ties
        # by iteration order, and tries each domain in the order given -
        # shuffling victim order and sorting each domain nearest-first
        # means a tie is broken by chance/proximity each tick, not by
        # whichever victim or resource id was declared first in code.
        random.shuffle(group_victim_ids)
        sub_domains = {
            vid: _domain_sorted_by_distance(grid, victims_by_id[vid], domains[vid], resources_by_id)
            for vid in group_victim_ids
        }
        ok, pruned, ac3_log = run_ac3(sub_domains, group_victim_ids)
        log.extend(f"  {line}" for line in ac3_log)
        if ok:
            success, sub_assignment = run_backtracking(pruned)
            if success:
                assignment.update(sub_assignment)
                for victim_id, resource_id in sub_assignment.items():
                    log.append(f"  Backtracking assigned {victim_id} -> {resource_id}.")
            else:
                log.append("  Backtracking could not resolve this group yet - retrying next tick.")
        else:
            log.append("  AC-3 hit an empty domain in this group - retrying next tick.")

    return log
