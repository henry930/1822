from app.engine.setup import new_game


def test_new_game_basic_invariants():
    state = new_game("test", ["Alice", "Bob", "Carol", "Dave"], seed=42)

    assert len(state.players) == 4
    assert len(state.player_order) == 4
    assert set(state.player_order) == set(state.players)

    for p in state.players.values():
        assert p.cash == 525  # 4-player start money

    assert state.bank.cash == 12000 - 525 * 4

    assert len(state.majors) == 10
    assert len(state.minors) == 24
    assert len(state.privates) == 18

    # LNWR concession must be on top of the concession stack / in bid box 1.
    assert state.concession_bid_boxes[0].ref == "LNWR"
    # M24 always on top of the minor stack.
    assert state.minor_bid_boxes[0].ref == 24
    # P1 always on top of the private stack.
    assert state.private_bid_boxes[0].ref == 1

    assert len(state.concession_bid_boxes) == 3
    assert len(state.minor_bid_boxes) == 4
    assert len(state.private_bid_boxes) == 3

    assert state.phase == 1
    assert state.round_type.value == "stock"


def test_new_game_rejects_invalid_player_counts():
    import pytest

    with pytest.raises(ValueError):
        new_game("test", ["Solo"])

    with pytest.raises(ValueError):
        new_game("test", [f"P{i}" for i in range(9)])
