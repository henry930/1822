from app.engine.actions import apply_action
from app.engine.setup import new_game
from app.rooms import serialize_state


def test_serialize_state_handles_tuple_keyed_stock_stack():
    """GameState.stock_stack is keyed by (row, col) tuples - json.dumps
    raises immediately on a non-str dict key (it never reaches `default`
    for keys), which crashed every broadcast once any company actually
    floated and got placed on the stock market grid. Regression test for
    that crash, found via manual play-testing the map/tile UI."""
    state = new_game("g1", ["Alice", "Bob", "Carol"], seed=1)
    first = state.player_order[0]
    apply_action(state, first, {"type": "bid", "bids": [{"kind": "minor", "box_index": 0, "amount": 100}]})
    for _ in range(3):
        apply_action(state, state.active_player_id, {"type": "pass"})

    assert state.round_type.value == "operating"
    assert state.stock_stack  # at least one company is now on the stock market grid

    raw = serialize_state(state)  # must not raise
    import json

    data = json.loads(raw)
    assert all(isinstance(k, str) for k in data["stock_stack"])
