import pytest

from app.engine.board import (
    TileLayError,
    apply_tile_lay,
    connection_pairs,
    new_board_state,
    validate_tile_lay,
)
from app.data.tiles import parse_tile_code, TILE_SPECS_BY_ID


def _parsed(tile_id):
    spec = TILE_SPECS_BY_ID[tile_id]
    return parse_tile_code(spec.id, spec.color, spec.count, spec.code)


def test_first_tile_on_a_hex_must_be_yellow():
    board = new_board_state()
    with pytest.raises(TileLayError):
        validate_tile_lay(board, phase=3, hex_id="Z1", tile_id="14", rotation=0)


def test_lay_yellow_tile_and_check_inventory_depletes():
    board = new_board_state()
    assert board.tile_pool["3"] == 6
    validate_tile_lay(board, phase=1, hex_id="Z1", tile_id="3", rotation=0)
    apply_tile_lay(board, "Z1", "3", 0)
    assert board.tile_pool["3"] == 5
    assert board.tiles["Z1"].tile_id == "3"


def test_unlimited_tiles_do_not_deplete():
    board = new_board_state()
    assert board.tile_pool["7"] is None
    validate_tile_lay(board, phase=1, hex_id="Z1", tile_id="7", rotation=0)
    apply_tile_lay(board, "Z1", "7", 0)
    assert board.tile_pool["7"] is None


def test_color_not_yet_available_in_phase():
    board = new_board_state()
    validate_tile_lay(board, phase=1, hex_id="Z1", tile_id="3", rotation=0)
    apply_tile_lay(board, "Z1", "3", 0)
    with pytest.raises(TileLayError):
        # green requires phase >= 3
        validate_tile_lay(board, phase=1, hex_id="Z1", tile_id="141", rotation=0)


def test_cannot_skip_a_color_step():
    board = new_board_state()
    validate_tile_lay(board, phase=1, hex_id="Z1", tile_id="3", rotation=0)
    apply_tile_lay(board, "Z1", "3", 0)
    with pytest.raises(TileLayError):
        # yellow -> brown directly, skipping green
        validate_tile_lay(board, phase=7, hex_id="Z1", tile_id="767", rotation=0)


def test_upgrade_preserving_connections_succeeds():
    board = new_board_state()
    # tile 3: town with edges {0,1}
    validate_tile_lay(board, phase=1, hex_id="Z1", tile_id="3", rotation=0)
    apply_tile_lay(board, "Z1", "3", 0)
    # tile 141: town with edges {0,3,1} - superset of {0,1}
    validate_tile_lay(board, phase=3, hex_id="Z1", tile_id="141", rotation=0)  # should not raise


def test_upgrade_dropping_a_connection_fails():
    board = new_board_state()
    # tile 4: town with edges {0,3}
    validate_tile_lay(board, phase=1, hex_id="Z1", tile_id="4", rotation=0)
    apply_tile_lay(board, "Z1", "4", 0)
    # tile 143: town with edges {0,1,2} - does NOT include the 0-3 connection
    with pytest.raises(TileLayError):
        validate_tile_lay(board, phase=3, hex_id="Z1", tile_id="143", rotation=0)


def test_rotation_shifts_which_connections_are_preserved():
    board = new_board_state()
    validate_tile_lay(board, phase=1, hex_id="Z1", tile_id="4", rotation=0)  # edges {0,3}
    apply_tile_lay(board, "Z1", "4", 0)
    # tile 143 rotated by 3 has edges {3,4,5} - still doesn't cover {0,3}
    with pytest.raises(TileLayError):
        validate_tile_lay(board, phase=3, hex_id="Z1", tile_id="143", rotation=3)


def test_minor_company_cannot_upgrade_past_green():
    board = new_board_state()
    with pytest.raises(TileLayError):
        validate_tile_lay(board, phase=5, hex_id="Z1", tile_id="X10", rotation=0, company_kind="minor")


def test_terrain_cost_charged_only_on_first_lay():
    board = new_board_state()
    # H13 is catalogued as an estuary hex, cost 40 (app.data.hex_map.TERRAIN_HEXES)
    cost = validate_tile_lay(board, phase=1, hex_id="H13", tile_id="3", rotation=0)
    assert cost == 40
    apply_tile_lay(board, "H13", "3", 0)
    cost2 = validate_tile_lay(board, phase=3, hex_id="H13", tile_id="141", rotation=0)
    assert cost2 == 0


def test_connection_pairs_treats_city_edges_as_mutually_connected():
    parsed = _parsed("14")  # city with edges {0,1,3,4}
    pairs = connection_pairs(parsed, rotation=0)
    assert frozenset((0, 1)) in pairs
    assert frozenset((0, 4)) in pairs
    assert frozenset((1, 3)) in pairs
