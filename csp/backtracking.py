"""
backtracking.py
----------------
Backtracking search that finds a complete, valid victim -> resource
assignment from the (already AC-3-pruned) domains. This is genuine
recursive backtracking: victims are selected one at a time (most
constrained variable first - smallest remaining domain), a value is
tried from its domain, constraints are checked, and the algorithm
recurses; on failure it undoes the assignment and tries the next
value, backtracking further if none work.
"""

from typing import Dict, List, Optional

Domains = Dict[str, List[str]]
Assignment = Dict[str, str]


def _select_unassigned_victim(domains: Domains, assignment: Assignment) -> Optional[str]:
    """Most-constrained-variable heuristic: pick the unassigned victim
    with the fewest remaining candidate resources."""
    unassigned = [v for v in domains if v not in assignment]
    if not unassigned:
        return None
    return min(unassigned, key=lambda v: len(domains[v]))


def _is_consistent(resource_id: str, assignment: Assignment) -> bool:
    """All-different constraint: the resource must not already be used
    by another victim in the current partial assignment."""
    return resource_id not in assignment.values()


def backtrack(domains: Domains, assignment: Assignment):
    if len(assignment) == len(domains):
        return dict(assignment)

    victim_id = _select_unassigned_victim(domains, assignment)
    if victim_id is None:
        return dict(assignment)

    for resource_id in domains[victim_id]:
        if _is_consistent(resource_id, assignment):
            assignment[victim_id] = resource_id
            result = backtrack(domains, assignment)
            if result is not None:
                return result
            del assignment[victim_id]  # undo and try the next candidate

    return None  # no value worked for this victim - trigger backtracking


def run_backtracking(domains: Domains):
    """Returns (success, assignment_or_none)."""
    result = backtrack(domains, {})
    return (result is not None), (result if result is not None else {})
