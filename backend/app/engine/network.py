"""Track-network connectivity built from the runtime board state
(app.engine.board), used by route-tracing (this module) for revenue
calculation.

Known gaps (see app.engine.board's docstring for the underlying cause):
pre-printed cities (BM/Y/C/EC labels) have no PlacedTile until their first
upgrade, so they won't appear connected here until that's fixed. Revenue
values are only known for the ~90 hexes catalogued in app.data.hex_map;
everything else values at £0, which is wrong but honest given the gap.
"""
from __future__ import annotations

from app.data.hex_map import CITIES, CITY_UPGRADE_TABLE, OFFBOARD_AREAS

from .board import BoardState, _parsed, rotated_edges_used
from .hex_grid import neighbor, opposite_edge

PHASE_COLOR_INDEX = {1: 0, 2: 0, 3: 1, 4: 1, 5: 2, 6: 2, 7: 3}  # rule 5.11.10


def hex_track_edges(board: BoardState, hex_id: str) -> set[int]:
    placed = board.tiles.get(hex_id)
    if placed is None:
        return set()
    return rotated_edges_used(_parsed(placed.tile_id), placed.rotation)


def hex_neighbors_via_track(board: BoardState, hex_id: str) -> list[str]:
    """Hexes reachable from hex_id by track that actually lines up on both
    sides (both hexes have track meeting at the shared edge)."""
    result = []
    for e in hex_track_edges(board, hex_id):
        n = neighbor(hex_id, e)
        if n is None:
            continue
        if opposite_edge(e) in hex_track_edges(board, n):
            result.append(n)
    return result


_CITY_BY_ID = {c.id: c for c in CITIES}
_OFFBOARD_HEX_TO_AREA = {h: a for a in OFFBOARD_AREAS for h in a.hexes}


def is_revenue_location(hex_id: str) -> bool:
    return hex_id in _CITY_BY_ID or hex_id in _OFFBOARD_HEX_TO_AREA


def hex_revenue_value(hex_id: str, phase: int) -> int:
    color_idx = PHASE_COLOR_INDEX[phase]
    area = _OFFBOARD_HEX_TO_AREA.get(hex_id)
    if area is not None:
        return (area.value_yellow, area.value_green, area.value_brown, area.value_grey)[color_idx]
    city = _CITY_BY_ID.get(hex_id)
    if city is not None:
        return CITY_UPGRADE_TABLE.get(city.label, CITY_UPGRADE_TABLE[None])[color_idx]
    return 0  # uncatalogued hex - see module docstring
