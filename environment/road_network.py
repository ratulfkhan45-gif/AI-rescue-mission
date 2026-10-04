"""
road_network.py
---------------
The disaster zone as a real road network (a weighted graph) instead of
a grid:

    nodes = real intersections / landmarks, each with latitude & longitude
    edges = road segments, each with a length in km and a status:
              OPEN     - normal road
              FLOODED  - passable by the rescue vehicle at FLOOD_MULTIPLIER x
                         the cost; support resources may NOT use it
              BLOCKED  - impassable (collapsed building, debris, ...)

Every search algorithm only needs three things from this class:
    neighbors(node)          - nodes reachable over non-blocked roads
    edge_cost(u, v)          - real cost of driving road u -> v (km)
    heuristic(node, goal)    - straight-line (haversine) distance in km

The heuristic is admissible: a road can never be shorter than the
straight line between its ends, and flood multipliers are >= 1, so A*
remains guaranteed to find the cheapest route.
"""

from dataclasses import dataclass
from math import radians, sin, cos, asin, sqrt
from typing import Dict, List, Tuple

OPEN = "OPEN"
FLOODED = "FLOODED"
BLOCKED = "BLOCKED"
ROAD_STATUSES = (OPEN, FLOODED, BLOCKED)

# Driving a flooded road costs this many times its real length.
FLOOD_MULTIPLIER = 3.0

EARTH_RADIUS_KM = 6371.0


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Great-circle (straight-line) distance between two (lat, lon) points."""
    lat1, lon1, lat2, lon2 = map(radians, (a[0], a[1], b[0], b[1]))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(h))


@dataclass
class Node:
    id: str
    name: str
    lat: float
    lon: float
    area: str          # e.g. "north" / "south" bank - used for dispatch zones


@dataclass
class Road:
    u: str
    v: str
    length_km: float
    status: str = OPEN
    shape: Tuple[Tuple[float, float], ...] = ()   # optional (lat, lon) bends between u and v


def road_key(u: str, v: str) -> Tuple[str, str]:
    """Roads are two-way; store each one under a sorted key."""
    return (u, v) if u <= v else (v, u)


class RoadNetwork:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.roads: Dict[Tuple[str, str], Road] = {}
        self._adj: Dict[str, List[str]] = {}

    # ---------------- building ---------------- #
    def add_node(self, node_id: str, name: str, lat: float, lon: float, area: str) -> None:
        self.nodes[node_id] = Node(node_id, name, lat, lon, area)
        self._adj.setdefault(node_id, [])

    def add_road(self, u: str, v: str, length_km: float = None, status: str = OPEN,
                 shape: Tuple[Tuple[float, float], ...] = ()) -> None:
        """Adds a two-way road. If no length is given, it is estimated as
        the straight-line distance x 1.25 (real streets are never
        perfectly straight) - or, when a `shape` (waypoints from u to v)
        is given, as the length of that path. Either way length >= straight
        line, which keeps the haversine heuristic admissible."""
        if u not in self.nodes or v not in self.nodes:
            raise KeyError(f"Unknown node in road {u}-{v}")
        straight = self.straight_line_km(u, v)
        if length_km is None:
            if shape:
                pts = [(self.nodes[u].lat, self.nodes[u].lon), *shape,
                       (self.nodes[v].lat, self.nodes[v].lon)]
                length_km = round(sum(haversine_km(a, b) for a, b in zip(pts, pts[1:])), 3)
            else:
                length_km = round(straight * 1.25, 3)
        length_km = max(length_km, straight)
        key = road_key(u, v)
        if key[0] != u:                       # stored sorted, so flip the shape too
            shape = tuple(reversed(shape))
        self.roads[key] = Road(*key, length_km, status, tuple(shape))
        if v not in self._adj[u]:
            self._adj[u].append(v)
        if u not in self._adj[v]:
            self._adj[v].append(u)

    # ---------------- queries ---------------- #
    def has_node(self, node_id: str) -> bool:
        return node_id in self.nodes

    def road(self, u: str, v: str) -> Road:
        return self.roads.get(road_key(u, v))

    def set_status(self, u: str, v: str, status: str) -> None:
        self.roads[road_key(u, v)].status = status

    def area(self, node_id: str) -> str:
        return self.nodes[node_id].area

    def name(self, node_id: str) -> str:
        return self.nodes[node_id].name

    def neighbors(self, node_id: str) -> List[str]:
        """Neighbors over any non-blocked road (rescue vehicle rules)."""
        return [n for n in self._adj[node_id]
                if self.roads[road_key(node_id, n)].status != BLOCKED]

    def safe_neighbors(self, node_id: str) -> List[str]:
        """Neighbors over OPEN roads only (support-resource rules)."""
        return [n for n in self._adj[node_id]
                if self.roads[road_key(node_id, n)].status == OPEN]

    def edge_cost(self, u: str, v: str) -> float:
        road = self.roads[road_key(u, v)]
        if road.status == FLOODED:
            return road.length_km * FLOOD_MULTIPLIER
        return road.length_km

    def straight_line_km(self, a: str, b: str) -> float:
        na, nb = self.nodes[a], self.nodes[b]
        return haversine_km((na.lat, na.lon), (nb.lat, nb.lon))

    def heuristic(self, node_id: str, goal_id: str) -> float:
        """h(n): straight-line distance to the goal in km (admissible)."""
        return self.straight_line_km(node_id, goal_id)
