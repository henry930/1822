import pytest

from app.engine.actions import ActionError, apply_action
from app.engine.company_formation import ConcessionError, convert_concession
from app.engine.setup import new_game


def _game():
    return new_game("g1", ["Alice", "Bob", "Carol"], seed=1)


def test_convert_concession_sets_price_treasury_and_director():
    state = _game()
    state.phase = 2
    p1 = state.player_order[0]
    state.players[p1].concessions = ["GWR"]
    starting_cash = state.players[p1].cash

    apply_action(state, p1, {"type": "convert_concession", "abbr": "GWR", "start_price": 80})

    major = state.majors["GWR"]
    assert major.floated is True
    assert major.director_player_id == p1
    assert major.share_price == 80
    # rule 4.7.3: £100 from bank + player pays (2*80 - 100) = £60
    assert major.treasury == 160
    assert state.players[p1].cash == starting_cash - 60
    assert state.players[p1].shares["GWR"] == 2
    assert "GWR" not in state.players[p1].concessions
    assert state.stock_positions["GWR"] is not None


def test_lnwr_conversion_is_fully_bank_funded_with_one_unit_share():
    state = _game()
    state.phase = 2
    p1 = state.player_order[0]
    state.players[p1].concessions = ["LNWR"]
    starting_cash = state.players[p1].cash

    apply_action(state, p1, {"type": "convert_concession", "abbr": "LNWR", "start_price": 70})

    major = state.majors["LNWR"]
    assert major.treasury == 70          # rule 4.7.4: full starting price from the bank
    assert state.players[p1].cash == starting_cash  # nothing from the player
    assert state.players[p1].shares["LNWR"] == 1


def test_cannot_convert_outside_phases_2_to_4():
    state = _game()
    state.phase = 5
    p1 = state.player_order[0]
    state.players[p1].concessions = ["GWR"]
    with pytest.raises(ConcessionError):
        convert_concession(state, p1, "GWR", 80)


def test_cannot_convert_a_concession_you_do_not_hold():
    state = _game()
    state.phase = 2
    p1 = state.player_order[0]
    with pytest.raises(ConcessionError):
        convert_concession(state, p1, "GWR", 80)


def test_start_price_must_be_a_valid_red_outlined_space():
    state = _game()
    state.phase = 2
    p1 = state.player_order[0]
    state.players[p1].concessions = ["GWR"]
    with pytest.raises(ConcessionError):
        convert_concession(state, p1, "GWR", 75)


def test_wrong_player_cannot_convert_out_of_turn():
    state = _game()
    state.phase = 2
    _p1, p2, _p3 = state.player_order
    state.players[p2].concessions = ["GWR"]
    with pytest.raises(ActionError):
        apply_action(state, p2, {"type": "convert_concession", "abbr": "GWR", "start_price": 80})
