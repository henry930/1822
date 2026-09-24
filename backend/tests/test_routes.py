from app.engine.board import BoardState, apply_tile_lay
from app.engine.routes import find_best_route, run_trains


def _vertical_chain_board(count: int, start: int = 1, col_letter: str = "A") -> BoardState:
    """A straight north-south chain of `count` hexes (tile 9, edges {0,3},
    unlimited supply) down a single column - simplest possible connected
    network for testing route search independent of real map data.
    Doubled-height coordinates (see hex_grid's module docstring): a
    straight N-S chain in one column steps by 2 rows per hex, not 1."""
    board = BoardState(tile_pool={})
    for i in range(count):
        row = start + 2 * i
        apply_tile_lay(board, f"{col_letter}{row}", "9", rotation=0)
    return board


def _patch_revenue(monkeypatch, values: dict[str, int]):
    monkeypatch.setattr("app.engine.routes.is_revenue_location", lambda h: h in values)
    monkeypatch.setattr("app.engine.routes.hex_revenue_value", lambda h, phase: values.get(h, 0))


def test_find_best_route_along_a_simple_chain(monkeypatch):
    board = _vertical_chain_board(7)  # A1, A3, A5, A7, A9, A11, A13
    _patch_revenue(monkeypatch, {"A1": 20, "A7": 0, "A13": 30})  # A7 is the station, not a revenue stop

    result = find_best_route(board, phase=1, start_hex="A7", max_stops=2)

    # Best 2-stop route from A7 reaches either A1 (20) or A13 (30); should pick A13.
    assert result.revenue == 30
    assert result.path == ["A7", "A9", "A11", "A13"]


def test_route_respects_max_stops(monkeypatch):
    board = _vertical_chain_board(7)  # A1, A3, A5, A7, A9, A11, A13
    _patch_revenue(monkeypatch, {"A1": 100, "A5": 10, "A9": 10, "A13": 10})

    # From A7, reaching A1 needs stops at A5 and A1 = 2 revenue stops, fits in max_stops=2.
    result = find_best_route(board, phase=1, start_hex="A7", max_stops=2)
    assert "A1" in result.path

    # A train limited to 1 stop can never complete a route needing 2 minimum.
    result_1 = find_best_route(board, phase=1, start_hex="A7", max_stops=1)
    assert result_1.revenue == 0


def test_route_needs_at_least_two_revenue_stops(monkeypatch):
    board = _vertical_chain_board(3)  # A1, A3, A5
    _patch_revenue(monkeypatch, {})  # no revenue locations at all on the chain
    result = find_best_route(board, phase=1, start_hex="A3", max_stops=7)
    assert result.revenue == 0
    assert result.path == []


def test_run_trains_does_not_let_two_trains_share_a_hex(monkeypatch):
    # Station at one end of a linear dead-end chain: A1(station)-A3-A5-A7.
    # Only one possible route exists at all (there's no branching), so once
    # train 1 claims it, train 2 has nothing left.
    board = _vertical_chain_board(4)  # A1, A3, A5, A7
    _patch_revenue(monkeypatch, {"A1": 0, "A7": 50})  # A1 (station) is a free stop

    total, results = run_trains(board, phase=1, station_hexes=["A1"], train_codes=["2", "2"])

    assert results[0].revenue == 50
    assert results[0].path == ["A1", "A3", "A5", "A7"]
    assert results[1].revenue == 0  # every hex beyond the station is already claimed
    assert total == 50
