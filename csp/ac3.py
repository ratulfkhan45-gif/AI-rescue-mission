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


def _revise(domains: Domains, xi: str, xj: str) -> Tuple[bool, List[str]]:
    """Remove values from Domain(xi) that have no consistent support in
    Domain(xj). Returns (changed, removed_values)."""
    removed = []
    new_domain = []
    for x in domains[xi]:
        # x is supported if there exists some y in Domain(xj), y != x
        has_support = any(y != x for y in domains[xj])
        if has_support:
            new_domain.append(x)
        else:
            removed.append(x)

    if removed:
        domains[xi] = new_domain
        return True, removed
    return False, removed


def run_ac3(domains: Domains, victim_ids: List[str]):
    """Runs AC-3 over all pairs of victims. Returns:
        (success, domains, log)
    success is False only if some domain becomes empty (no valid value
    remains for that victim - an unsolvable CSP as constrained).
    log is a list of human-readable strings describing each pruning
    step, useful for the GUI to display genuine AC-3 activity."""
    domains = {vid: list(vals) for vid, vals in domains.items()}
    log: List[str] = []

    # Build all directed arcs between victim pairs.
    arcs = deque()
    for xi in victim_ids:
        for xj in victim_ids:
            if xi != xj:
                arcs.append((xi, xj))
