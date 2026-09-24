from app.engine.hex_grid import (
    edge_toll,
    is_adjacency_blocked,
    make_id,
    neighbor,
    neighbors,
    opposite_edge,
    parse_id,
)


def test_parse_and_make_id_round_trip():
    for hex_id in ["A1", "H5", "Q44", "F23"]:
        col, row = parse_id(hex_id)
        assert make_id(col, row) == hex_id


def test_neighbor_relationships_are_reciprocal():
    """If B is A's neighbor across edge E, A must be B's neighbor across
    the opposite edge - this holds regardless of which real-world hexes
    actually exist, since it's a property of the coordinate math itself."""
    for hex_id in ["B10", "C10", "H20", "I20", "M25", "N25"]:
        for edge in range(6):
            n = neighbor(hex_id, edge)
            if n is None:
                continue
            back = neighbor(n, opposite_edge(edge))
            assert back == hex_id, f"{hex_id} edge {edge} -> {n}, but back-edge gave {back}"


def test_neighbors_returns_up_to_six_distinct_hexes():
    result = neighbors("H20")
    assert len(result) <= 6
    assert len(set(result.values())) == len(result)


def test_out_of_bounds_edge_returns_none():
    assert neighbor("A1", 0) is None  # off the top of the board
    assert neighbor("A1", 5) is None  # off the left edge


def test_blocked_adjacency_from_rules_confirmed_pair():
    # rule 1.4.9: Holyhead (F23) and Mid Wales's northern hex (F25) do not connect.
    assert is_adjacency_blocked("F23", "F25") is True
    assert is_adjacency_blocked("H20", "H22") is False


def test_doubled_height_same_column_neighbor_two_rows_away():
    """Doubled-height coordinates (see hex_grid's module docstring): a
    hex's straight N/S neighbor stays in the same column but is 2 rows
    away, not 1. Confirmed directly against the rules-confirmed F23<->F25
    blocked adjacency (rule 1.4.9, both textually and via a direct scan of
    the board photo) - a same-column pair the rulebook says is adjacent
    (that's the whole point of blocking it) is 2 rows apart, not 1."""
    col_f23, row_f23 = parse_id("F23")
    col_f25, row_f25 = parse_id("F25")
    assert col_f23 == col_f25
    assert row_f25 - row_f23 == 2


def test_neighbor_uses_doubled_height_deltas():
    # Straight N/S (edges 0/3): same column, 2 rows away.
    assert neighbor("H20", 3) == "H22"
    assert neighbor("H22", 0) == "H20"
    # Diagonals (edges 1/2/4/5): 1 column and 1 row away.
    assert neighbor("H20", 1) == "I19"  # NE
    assert neighbor("H20", 2) == "I21"  # SE
    assert neighbor("H20", 4) == "G21"  # SW
    assert neighbor("H20", 5) == "G19"  # NW


def test_edge_toll_is_symmetric_and_none_when_uncatalogued():
    # EDGE_TOLLS is intentionally empty until confirmed via the map tab's
    # cross-check tool (see app.data.hex_map) - this just guards the lookup
    # plumbing itself, order-independent as a real entry would need to be.
    assert edge_toll("H20", "H21") is None
    assert edge_toll("H21", "H20") is None
