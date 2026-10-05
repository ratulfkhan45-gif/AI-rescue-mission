"""
ac3.py
------
A genuine implementation of the AC-3 arc-consistency algorithm applied
to the "no two victims share the same resource" (not-equal) binary
constraint between every pair of victims that could otherwise compete
for the same resource.

Standard AC-3:

    queue = all arcs (Xi, Xj)
    while queue not empty:
        (Xi, Xj) = queue.pop()
        if REVISE(Xi, Xj):
            if Domain(Xi) is empty: return failure (empty domain)
            for each Xk in neighbors(Xi) - {Xj}:
                queue.push((Xk, Xi))

REVISE(Xi, Xj) removes value x from Domain(Xi) when there is no value
y in Domain(Xj) that satisfies the not-equal constraint (y != x); for
a not-equal constraint this only happens when Domain(Xj) == {x}.
"""

from collections import deque
from typing import Dict, List, Tuple

Domains = Dict[str, List[str]]
