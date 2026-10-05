"""
astar.py
--------
A* Search: informed search that expands the node with the smallest
f(n) = g(n) + h(n), where g(n) is the real road cost driven so far
(km, with flooded roads multiplied) and h(n) is the straight-line
(haversine) distance to the goal. A* is optimal here because no road
is shorter than the straight line between its ends, so h(n) never
overestimates the true remaining cost.
"""

import heapq
import time
from itertools import count

from environment.road_network import RoadNetwork
from algorithms.search_result import SearchResult
from algorithms.utils import reconstruct_path, path_cost, straight_line

Position = str   # node id


def search(grid: RoadNetwork, start: Position, goal: Position) -> SearchResult:
    start_time = time.perf_counter()

    tie_breaker = count()
    g_score = {start: 0.0}
    f_start = straight_line(grid, start, goal)
    frontier = [(f_start, next(tie_breaker), start)]
    came_from = {}
    explored_set = set()
    explored_order = []
    found = False
