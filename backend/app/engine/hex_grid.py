"""Hex grid adjacency for the 1822 board.

Scope note: this module gives correct neighbor-finding math for the
coordinate system already used by hex_map.py and docs/hex-map-board.html
(flat-top hexes, "odd-q" column offset - odd 0-indexed columns are shifted
half a row down). It does NOT yet know which of the ~300+ physical hexes
actually exist (land vs sea, board edge) - hex_map.py only catalogs the
~90 named/informational hexes. Until the full board is catalogued,
`exists()` is permissive (true for any coordinate inside the printed
column/row bounds) rather than authoritative; callers that need to know
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

# Directions 0-5 = N, NE, SE, S, SW, NW, as (d_col, d_row) offsets - two
# variants depending on the hex's column parity (odd-q offset layout).
_EVEN_COL_DELTAS = [(0, -1), (1, -1), (1, 0), (0, 1), (-1, 0), (-1, -1)]
_ODD_COL_DELTAS = [(0, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]


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
    deltas = _ODD_COL_DELTAS if col % 2 == 1 else _EVEN_COL_DELTAS
    d_col, d_row = deltas[edge]
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
