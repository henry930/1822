import pytest

from app.engine.setup import new_game
from app.engine.trains import (
    TrainError,
    buy_train_from_bank,
    current_buyable_pool,
    upgrade_l_to_2,
)


def _game():
    return new_game("g1", ["Alice", "Bob", "Carol"], seed=1)


def test_initial_buyable_pool_is_l():
    state = _game()
    assert current_buyable_pool(state) == "L"


def test_buy_l_train_deducts_treasury_and_credits_bank():
    state = _game()
    minor = state.minors["M3"]
    minor.treasury = 100
    starting_bank = state.bank.cash

    cost = buy_train_from_bank(state, "M3", "minor", "L")

    assert cost == 60
    assert minor.treasury == 40
    assert minor.trains == ["L"]
    assert state.bank.cash == starting_bank + 60
    assert state.bank.train_pool["L"] == 21


def test_cannot_buy_3_train_before_l_pool_exhausted():
    state = _game()
    major = state.majors["GWR"]
    major.treasury = 1000
    with pytest.raises(TrainError):
        buy_train_from_bank(state, "GWR", "major", "3")


def test_buying_first_2_train_advances_phase_and_rusts_nothing_yet():
    state = _game()
    major = state.majors["GWR"]
    major.treasury = 1000
    buy_train_from_bank(state, "GWR", "major", "2")
    assert state.phase == 2
    assert major.trains == ["2"]


def test_buying_first_3_train_rusts_l_trains():
    state = _game()
    minor = state.minors["M3"]
    minor.treasury = 1000
    minor.trains = ["L"]
    major = state.majors["GWR"]
    major.treasury = 1000

    # Exhaust the whole L/2 pool (22 cards) to reach phase 3's precondition
    # (rule 5.13.4: can't buy 3-trains until all L/2s are gone).
    state.bank.train_pool["L"] = 0

    buy_train_from_bank(state, "GWR", "major", "3")

    assert state.phase == 3
    assert minor.trains == []  # L-train rusted, removed without compensation
    assert major.trains == ["3"]


def test_phase_change_that_lowers_train_limit_forces_discard():
    state = _game()
    major = state.majors["GWR"]
    major.treasury = 10000
    # 3-trains (rusted by 6, not by 4) so they survive the phase-4 transition
    # and only the train-limit drop (not rusting) causes the discard.
    major.trains = ["3", "3", "3", "3"]  # phase 1-3 major limit is 4, legal so far
    state.bank.train_pool["L"] = 0
    state.bank.train_pool["3"] = 0

    # Buying the first 4-train triggers phase 4, which drops the major
    # train limit from 4 to 3 (rule 2.2.5) - GWR now has 5 trains (4 old +
    # the new 4-train), one over the new limit of 3.
    buy_train_from_bank(state, "GWR", "major", "4")

    assert state.phase == 4
    assert len(major.trains) == 3
    assert len(state.bank.discarded_trains) == 2


def test_upgrade_l_to_2_flips_the_train_and_can_trigger_phase_2():
    state = _game()
    minor = state.minors["M3"]
    minor.treasury = 200
    minor.trains = ["L"]

    cost = upgrade_l_to_2(state, "M3", "minor")

    assert cost == 80
    assert minor.trains == ["2"]
    assert minor.treasury == 120
    assert state.phase == 2


def test_cannot_afford_train_raises():
    state = _game()
    minor = state.minors["M3"]
    minor.treasury = 10
    with pytest.raises(TrainError):
        buy_train_from_bank(state, "M3", "minor", "L")
