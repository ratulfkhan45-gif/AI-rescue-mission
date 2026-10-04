"""
csp.py
------
Defines the rescue-resource assignment problem as a genuine Constraint
Satisfaction Problem:

    Variables = victims
    Domains   = compatible, dispatchable resources for each victim
    Constraints:
      1. Type compatibility  - a resource can only serve its own type
         (ambulance / medical_team) of requirement. Ambulances and
         medical teams are otherwise treated identically - neither type
         gets priority, and a dedicated unit is no more preferred than
         a "backup" one.
      2. Dispatch zone        - a resource may only serve victims inside
         its declared area (dedicated north-bank / south-bank units),
         except flexible "backup" units which cover both banks.
      3. Reachability         - a resource must have an actual safe
         route (OPEN roads only - no flooded or blocked roads) to the
         victim on the road network.
      4. All-different        - no resource may be assigned to more
         than one victim at the same time.

Constraints 1-3 are unary and are applied once, up front, to build the
initial domains. Constraint 4 is the binary constraint AC-3 enforces
arc consistency on, and that backtracking.py finally satisfies with a
complete assignment.
"""

import heapq
from itertools import count
from typing import Dict, List, Optional

from environment.road_network import RoadNetwork
from environment.scenario import Victim, Resource

Position = str   # node id


def safe_distance_km(network: RoadNetwork, start: Position, goal: Position) -> Optional[float]:
    """Shortest driving distance (km) from start to goal using only OPEN
    roads (Dijkstra), or None if no safe route exists. Shared by the
    domain-building reachability check and the live simulation's
    nearest-resource ranking, so both use the same notion of distance."""
    if start == goal:
        return 0.0
    tie = count()
    best = {start: 0.0}
    frontier = [(0.0, next(tie), start)]
    while frontier:
        dist, _, current = heapq.heappop(frontier)
        if current == goal:
            return dist
        if dist > best.get(current, float("inf")):
            continue
        for neighbor in network.safe_neighbors(current):
            nd = dist + network.road(current, neighbor).length_km
            if nd < best.get(neighbor, float("inf")):
                best[neighbor] = nd
                heapq.heappush(frontier, (nd, next(tie), neighbor))
    return None


# Kept under the old name so older code keeps working.
bfs_safe_distance = safe_distance_km


def build_initial_domains(network: RoadNetwork, victims: List[Victim],
                           resources: List[Resource]) -> Dict[str, List[str]]:
    """Applies all three unary constraints to build each victim's
    starting domain of resource ids. Nothing here is hard-coded per
    victim: a resource qualifies purely on type match, dispatch area
    and safe-road reachability."""
    domains: Dict[str, List[str]] = {}

    for victim in victims:
        domain = []
        for resource in resources:
            # Constraint 1: type compatibility
            if resource.type != victim.requirement:
                continue
            # Constraint 2: dispatch zone (area of the victim's node)
            if network.area(victim.pos) not in resource.zone:
                continue
            # Constraint 3: real safe-route reachability
            if safe_distance_km(network, resource.pos, victim.pos) is None:
                continue
            domain.append(resource.id)
        domains[victim.id] = domain

    return domains


def resources_conflict(resource_id: str, other_resource_id: str) -> bool:
    """The all-different constraint: two victims conflict if they would
    be assigned the very same physical resource."""
    return resource_id == other_resource_id
