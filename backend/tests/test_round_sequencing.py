import pytest

from app.engine.actions import ActionError, apply_action
from app.engine.models import RoundType
from app.engine.round_manager import active_company_id, start_operating_round_set
from app.engine.setup import new_game
from app.engine.stock_positions import place_token
from app.engine.turn_order import compute_operating_order, stock_round_order


def _game():
    return new_game("g1", ["Alice", "Bob", "Carol"], seed=1)


def test_first_stock_round_ending_with_nothing_sold_ends_the_game():
    state = _game()
    assert state.round_type == RoundType.STOCK
    order = list(state.player_order)
    assert stock_round_order(state) == order  # starts at priority deal player

    for pid in order:
        apply_action(state, pid, {"type": "pass"})

    assert state.game_over is True
    assert "nothing sold" in state.log[-1]


def test_stock_round_only_ends_after_a_full_lap_of_consecutive_passes():
    state = _game()
    p1, p2, p3 = state.player_order
    apply_action(state, p1, {"type": "pass"})
    apply_action(state, p2, {"type": "pass"})
    state.any_sale_this_stock_round = True  # simulate p3 having bought something earlier
    apply_action(state, p3, {"type": "pass"})
    # Only 3 consecutive passes total but round should have ended (not game_over,
    # since a sale occurred this SR) and moved into an operating round set.
    assert state.round_type == RoundType.OPERATING


def test_wrong_player_cannot_act_out_of_turn():
    state = _game()
    _, p2, _ = state.player_order
    with pytest.raises(ActionError):
        apply_action(state, p2, {"type": "pass"})


def test_operating_order_is_minors_then_majors_by_descending_price():
    state = _game()
    state.minors["M1"].floated = True
    state.minors["M2"].floated = True
    state.majors["GWR"].floated = True
    place_token(state, "M1", row=9, col=4)   # value 50
    place_token(state, "M2", row=8, col=4)   # value 60
    place_token(state, "GWR", row=4, col=4)  # value 100

    order = compute_operating_order(state)
    assert order == ["M2", "M1", "GWR"]  # minors first (by price), then majors


def test_operating_round_set_uses_phase_locked_or_count_and_returns_to_stock():
    state = _game()
    director = state.player_order[0]
    state.minors["M1"].floated = True
    state.minors["M1"].director_player_id = director
    place_token(state, "M1", row=9, col=4)
    start_operating_round_set(state)

    assert state.round_type == RoundType.OPERATING
    assert state.operating_rounds_this_set == 1  # phase 1 -> 1 OR per rule 2.2.2
    assert active_company_id(state) == "M1"

    apply_action(state, director, {"type": "pass"})  # company turn -> advance
    assert state.round_type == RoundType.STOCK  # only company was M1, set had 1 OR


def test_operating_round_set_runs_two_ors_from_phase_2_onward():
    state = _game()
    director = state.player_order[0]
    state.phase = 2
    state.minors["M1"].floated = True
    state.minors["M1"].director_player_id = director
    place_token(state, "M1", row=9, col=4)
    start_operating_round_set(state)

    assert state.operating_rounds_this_set == 2
    apply_action(state, director, {"type": "pass"})  # OR1's only company finishes
    assert state.round_type == RoundType.OPERATING  # still in the set (OR2 next)
    assert state.operating_round_index == 1
    apply_action(state, director, {"type": "pass"})  # OR2's only company finishes
    assert state.round_type == RoundType.STOCK
