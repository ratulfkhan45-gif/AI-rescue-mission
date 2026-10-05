"""
search_result.py
-----------------
Common result container returned by every search algorithm so the GUI
and comparison panel can treat BFS/A* uniformly.
"""

from dataclasses import dataclass, field
from typing import List

Position = str   # node id


@dataclass
class SearchResult:
    algorithm: str
    found: bool
    path: List[Position] = field(default_factory=list)
    explored_order: List[Position] = field(default_factory=list)  # animation order
    nodes_explored: int = 0
    path_cost: float = 0.0
    runtime_ms: float = 0.0
