"""
utils.py
--------
Small helpers shared by every search algorithm: reconstructing a path
from a came_from map, computing the real cost of a path on the road
network (flooded roads cost more), and the straight-line heuristic.
"""

from typing import Dict, List

from environment.road_network import RoadNetwork

Position = str   # node id


def reconstruct_path(came_from: Dict[Position, Position], start: Position,
                      goal: Position) -> List[Position]:
    """Walk the came_from chain from goal back to start and reverse it."""
    if goal not in came_from and goal != start:
        return []
    path = [goal]
    current = goal
    while current != start:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def path_cost(network: RoadNetwork, path: List[Position]) -> float:
    """Sum of real road costs along a path in km (flooded roads are
    multiplied by FLOOD_MULTIPLIER)."""
    total = 0.0
    for u, v in zip(path, path[1:]):
        total += network.edge_cost(u, v)
    return total


def path_length_km(network: RoadNetwork, path: List[Position]) -> float:
    """Physical driving distance along a path in km (no flood penalty)."""
    return sum(network.road(u, v).length_km for u, v in zip(path, path[1:]))
