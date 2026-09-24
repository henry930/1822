"""Hex grid adjacency for the 1822 board.

Coordinate system: "doubled-height" coordinates for flat-top hexes (see
https://www.redblobgames.com/grids/hexagons/#coordinates-doubled) - the
column letter is a plain index, but the row number is *doubled*: a real
hex's straight N/S neighbor (same column) differs by 2 in row, and its
diagonal neighbors (NE/SE/SW/NW) differ by 1 in column and 1 in row. Only
coordinates where `col` and `row` share parity are real hexes (see
`exists()`'s note on why that's not enforced here yet). This is the
convention hex_map.py's ids actually use - confirmed directly against two
rules-confirmed BLOCKED_ADJACENCIES pairs (F23<->F25, F31<->F33, both same-
column pairs 2 rows apart) and against a scan of the real board photo,
which also uses this numbering (see MapTab.tsx's own photo calibration
notes on the frontend).

This replaces an earlier "odd-q offset" implementation (±1-row deltas for
the N/S edges) that was simply the wrong coordinate system for this board -
found via a direct board-photo scan where hexes computed as adjacent under
that formula (e.g. a hex 1 row from another in the same column) turned out
to be two entirely different, non-adjacent physical hexes, while textually
-confirmed adjacent pairs (F23/F25 etc.) came out as *not* adjacent under
it. Every caller (tile-lay connectivity, route tracing, the map tab's
region-correction tool) only ever goes through neighbor()/neighbors(), so
fixing the formula here fixes all of them without any caller-side changes.

It does NOT yet know which of the ~300+ physical hexes actually exist
(land vs sea, board edge) - hex_map.py only catalogs the ~90 named/
informational hexes. Until the full board is catalogued, `exists()` is
permissive (true for any coordinate inside the printed column/row bounds,
regardless of parity) rather than authoritative; callers that need to know
"is this really a hex on the board" should not rely on it yet.

Edge numbering matches app.data.tiles' path specs and the tile SVGs
(0=top/N, 1=upper-right/NE, 2=lower-right/SE, 3=bottom/S, 4=lower-left/SW,
5=upper-left/NW), so a tile's `path=a:E,...` edges line up directly with
the neighbor this module returns for that edge.
"""
from __future__ import annotations

from app.data.hex_map import BLOCKED_ADJACENCIES, EDGE_TOLLS, HEX_COLUMNS

_COL_INDEX = {letter: i for i, letter in enumerate(HEX_COLUMNS)}
_INDEX_COL = {i: letter for letter, i in _COL_INDEX.items()}

MIN_ROW = 1
MAX_ROW = 44

# Directions 0-5 = N, NE, SE, S, SW, NW, as (d_col, d_row) offsets. One
# uniform table - doubled-height coordinates don't need a column-parity
# split the way odd-q offset coordinates do.
_EDGE_DELTAS = [(0, -2), (1, -1), (1, 1), (0, 2), (-1, 1), (-1, -1)]


def parse_id(hex_id: str) -> tuple[int, int]:
    """'H5' -> (col_index=7, row=5)."""
    for i, ch in enumerate(hex_id):
        if ch.isdigit():
            letters, digits = hex_id[:i], hex_id[i:]
            break
    else:
        raise ValueError(f"not a hex id: {hex_id!r}")
    if letters not in _COL_INDEX:
        raise ValueError(f"unknown column letter in hex id: {hex_id!r}")
    return _COL_INDEX[letters], int(digits)


def make_id(col: int, row: int) -> str:
    return f"{_INDEX_COL[col]}{row}"


def exists(col: int, row: int) -> bool:
    """Permissive board-bounds check - see module docstring."""
    return 0 <= col < len(HEX_COLUMNS) and MIN_ROW <= row <= MAX_ROW


_BLOCKED_PAIRS: set[frozenset[str]] = {frozenset((a, b)) for a, b, _confidence in BLOCKED_ADJACENCIES}


def is_adjacency_blocked(hex_id_a: str, hex_id_b: str) -> bool:
    """Rule 1.4.9-style coastal breaks (red lines on the board) where two
    hexes are geometrically adjacent but do not connect for routing."""
    return frozenset((hex_id_a, hex_id_b)) in _BLOCKED_PAIRS


_EDGE_TOLL_BY_PAIR: dict[frozenset[str], int] = {
    frozenset((t.hex_a, t.hex_b)): t.cost for t in EDGE_TOLLS
}


def edge_toll(hex_id_a: str, hex_id_b: str) -> int | None:
    """The one-time fee (if any) a company must pay to build track across
    the specific edge between these two hexes - None means the edge is
    free to cross (the ordinary case) or blocked outright (see
    is_adjacency_blocked; a blocked edge can't be crossed at any price)."""
    return _EDGE_TOLL_BY_PAIR.get(frozenset((hex_id_a, hex_id_b)))


def neighbor(hex_id: str, edge: int) -> str | None:
    """The hex across the given edge (0-5, see module docstring), or None
    if that would fall outside the board or the adjacency is blocked."""
    if not (0 <= edge <= 5):
        raise ValueError("edge must be 0-5")
    col, row = parse_id(hex_id)
    d_col, d_row = _EDGE_DELTAS[edge]
    n_col, n_row = col + d_col, row + d_row
    if not exists(n_col, n_row):
        return None
    n_id = make_id(n_col, n_row)
    if is_adjacency_blocked(hex_id, n_id):
        return None
    return n_id


def neighbors(hex_id: str) -> dict[int, str]:
    """{edge: neighbor_hex_id} for every edge that has a (board-bounds,
    unblocked) neighbor."""
    result = {}
    for edge in range(6):
        n = neighbor(hex_id, edge)
        if n is not None:
            result[edge] = n
    return result


def opposite_edge(edge: int) -> int:
    return (edge + 3) % 6
