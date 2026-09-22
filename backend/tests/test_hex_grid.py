from app.engine.hex_grid import (
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
    assert is_adjacency_blocked("H20", "H21") is False
