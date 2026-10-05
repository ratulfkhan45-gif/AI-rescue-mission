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

    while frontier:
        _, _, current = heapq.heappop(frontier)

        if current in explored_set:
            continue
        explored_set.add(current)
        explored_order.append(current)

        if current == goal:
            found = True
            break

        for neighbor in grid.neighbors(current):
            tentative_g = g_score[current] + grid.edge_cost(current, neighbor)
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                g_score[neighbor] = tentative_g
                came_from[neighbor] = current
                f_score = tentative_g + straight_line(grid, neighbor, goal)
                heapq.heappush(frontier, (f_score, next(tie_breaker), neighbor))

    runtime_ms = (time.perf_counter() - start_time) * 1000.0

    path = reconstruct_path(came_from, start, goal) if found else []
    cost = path_cost(grid, path) if found else 0.0

    return SearchResult(
        algorithm="A*",
        found=found,
        path=path,
        explored_order=explored_order,
        nodes_explored=len(explored_order),
        path_cost=cost,
        runtime_ms=runtime_ms,
    )
