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
