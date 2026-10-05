"""
bfs.py
------
Breadth-First Search: uninformed search using a FIFO queue. Explores
the road network level by level and is guaranteed to find the path with the
fewest road segments (not necessarily the shortest or cheapest
route, since it ignores road lengths and flooding while searching).
"""

import time
from collections import deque

from environment.road_network import RoadNetwork
from algorithms.search_result import SearchResult
from algorithms.utils import reconstruct_path, path_cost

Position = str   # node id


def search(grid: RoadNetwork, start: Position, goal: Position) -> SearchResult:
    start_time = time.perf_counter()

    frontier = deque([start])
    came_from = {}
    visited = {start}
    explored_order = []
    found = False

    if start == goal:
        found = True
    else:
        while frontier:
            current = frontier.popleft()
            explored_order.append(current)

            if current == goal:
                found = True
                break

            for neighbor in grid.neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    came_from[neighbor] = current
                    frontier.append(neighbor)

    runtime_ms = (time.perf_counter() - start_time) * 1000.0

    path = reconstruct_path(came_from, start, goal) if found else []
    cost = path_cost(grid, path) if found else 0.0

    return SearchResult(
        algorithm="BFS",
        found=found,
        path=path,
        explored_order=explored_order,
        nodes_explored=len(explored_order),
        path_cost=cost,
        runtime_ms=runtime_ms,
    )
