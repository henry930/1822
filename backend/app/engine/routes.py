"""Route enumeration and revenue calculation (rule 5.4, 5.11).

Scope for this pass: numbered trains (L, 2-7) only - Pullman "+" cars and
Express (E) trains have materially different stop semantics (rule
5.11.14, 5.11.21) and are not handled yet, see run_trains' docstring.
Multi-train allocation is greedy (largest train claims the best route
first, then the next largest picks the best route from what's left) -
this is NOT guaranteed to find the true joint-optimal assignment across
all of a company's trains, just a reasonable approximation.

A route is modeled as a simple path of hexes (no hex visited twice) - see
app.engine.network's docstring for why this is a hex-granularity
approximation of "no track segment reused" rather than the fully precise
rule, and doesn't yet handle the double-town same-hex exception (rule
5.11.3/9.1.1).
"""
from __future__ import annotations

from dataclasses import dataclass

from .board import BoardState
from .network import hex_neighbors_via_track, hex_revenue_value, is_revenue_location

TRAIN_MAX_STOPS = {"L": 2, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7}


@dataclass
class RouteResult:
    revenue: int
    path: list[str]


def find_best_route(
    board: BoardState,
    phase: int,
    start_hex: str,
    max_stops: int,
    blocked_hexes: frozenset[str] = frozenset(),
) -> RouteResult:
    """Best (highest-revenue) simple path from start_hex, using at most
    max_stops revenue locations (rule 5.11.2), not reusing any hex in
    blocked_hexes (already claimed by another of this company's trains this
    turn). A route needs at least 2 revenue-location stops to count."""
    best = RouteResult(revenue=0, path=[])
    start_stops = 1 if is_revenue_location(start_hex) else 0

    def dfs(current: str, visited: set[str], stops: int, path: list[str]) -> None:
        nonlocal best
        for nxt in hex_neighbors_via_track(board, current):
            if nxt in visited or nxt in blocked_hexes:
                continue
            nxt_stops = stops + (1 if is_revenue_location(nxt) else 0)
            if nxt_stops > max_stops:
                continue
            new_path = path + [nxt]
            if nxt_stops >= 2:
                revenue = sum(hex_revenue_value(h, phase) for h in new_path if is_revenue_location(h))
                if revenue > best.revenue:
                    best = RouteResult(revenue=revenue, path=list(new_path))
            dfs(nxt, visited | {nxt}, nxt_stops, new_path)

    dfs(start_hex, {start_hex}, start_stops, [start_hex])
    return best


def run_trains(
    board: BoardState,
    phase: int,
    station_hexes: list[str],
    train_codes: list[str],
) -> tuple[int, list[RouteResult]]:
    """Greedily assigns each train (largest first) the best available route
    from any of the company's station hexes, without reusing a hex another
    of its trains already used this turn. Returns (total_revenue, per-train
    results in the same order as train_codes)."""
    order = sorted(range(len(train_codes)), key=lambda i: -TRAIN_MAX_STOPS.get(train_codes[i], 0))
    results: list[RouteResult | None] = [None] * len(train_codes)
    used: set[str] = set()

    for i in order:
        code = train_codes[i]
        max_stops = TRAIN_MAX_STOPS.get(code)
        if max_stops is None:
            results[i] = RouteResult(revenue=0, path=[])  # unsupported train type this pass
            continue
        best = RouteResult(revenue=0, path=[])
        for start in station_hexes:
            candidate = find_best_route(board, phase, start, max_stops, frozenset(used))
            if candidate.revenue > best.revenue:
                best = candidate
        results[i] = best
        used.update(best.path)

    total = sum(r.revenue for r in results if r is not None)
    return total, results
