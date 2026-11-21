"""Tests derived from rulebook chapters 2 (phases) and 3 (corporate entities).
Rule id in each test name (r2_2_4 = rule 2.2.4). Written from the rule text; engine used only for API names.
"""
import pytest

from app.data.major_companies import MAJOR_COMPANIES, MAJOR_COMPANIES_BY_ABBR
from app.data.minor_companies import BASE_GAME_MINOR_COMPANIES
from app.data.phases import PHASES_BY_NUMBER
from app.data.private_companies import BASE_GAME_PRIVATE_COMPANIES
from app.data.trains import TRAIN_TYPES_BY_CODE
from app.engine.bidding import _face_value
from app.engine.round_manager import start_operating_round_set
from app.engine.setup import new_game
from app.engine.trains import TrainError, buy_train_from_bank


def game(n=3):
    return new_game("g", [f"P{i}" for i in range(n)], seed=1)


def fund(state, abbr="GWR", cash=2000):
    state.majors[abbr].treasury = cash
    return abbr


# ---- 2 phases --------------------------------------------------------------
def test_r2_2_2_game_starts_in_phase_1():
    assert game().phase == 1


def test_r2_2_3_first_2_train_bought_starts_phase_2():
    s = game(); a = fund(s)
    buy_train_from_bank(s, a, "major", "2")
    assert s.phase == 2


def test_r2_2_4_first_3_train_starts_phase_3_and_rusts_L():
    s = game(); a = fund(s)
    s.bank.train_pool["L"] = 0
    s.majors["CR"].trains = ["L"]
    buy_train_from_bank(s, a, "major", "3")
    assert s.phase == 3
    assert "L" not in s.majors["CR"].trains           # rusted: removed without compensation (2.1.3)


def test_r2_2_5_phase_4_rusts_2_and_lowers_limits():
    s = game(); a = fund(s)
    s.bank.train_pool.update({"L": 0, "3": 0})
    s.phase = 3
    s.majors["CR"].trains = ["2"]
    buy_train_from_bank(s, a, "major", "4")
    assert s.phase == 4 and "2" not in s.majors["CR"].trains
    assert PHASES_BY_NUMBER[4].minor_train_limit == 1 and PHASES_BY_NUMBER[4].major_train_limit == 3


def test_r2_1_3_rusted_trains_removed_without_compensation():
    s = game(); a = fund(s)
    s.bank.train_pool["L"] = 0
    s.minors["M1"].trains = ["L"]
    s.minors["M1"].treasury = 0
    bank_before = s.bank.cash
    buy_train_from_bank(s, a, "major", "3")
    assert s.minors["M1"].trains == [] and s.minors["M1"].treasury == 0
    assert s.bank.cash == bank_before + 200           # only the purchase price


def test_r2_1_4_excess_trains_after_limit_drop_go_to_bank_pool():
    s = game(); a = fund(s)
    s.phase = 3
    s.bank.train_pool.update({"L": 0, "3": 0})
    s.majors[a].trains = ["3", "3", "3"]
    buy_train_from_bank(s, a, "major", "4")           # phase 4: major limit 3, now owns 4
    assert len(s.majors[a].trains) == 3
    assert len(s.bank.discarded_trains) == 1


def test_r2_1_2_second_operating_round_applies_only_after_following_stock_round():
    s = game(); a = fund(s)
    start_operating_round_set(s)                       # phase 1: one OR in this set
    buy_train_from_bank(s, a, "major", "2")            # phase 2 begins mid-set
    assert s.operating_rounds_this_set == 1


@pytest.mark.parametrize("phase,minor,major", [(1, 2, 4), (2, 2, 4), (3, 2, 4), (4, 1, 3), (5, 1, 2)])
def test_r2_2_x_train_limits(phase, minor, major):
    p = PHASES_BY_NUMBER[phase]
    assert p.minor_train_limit == minor and p.major_train_limit == major


@pytest.mark.parametrize("phase,ors", [(1, 1), (2, 2), (3, 2), (7, 2)])
def test_r2_2_x_operating_rounds_per_stock_round(phase, ors):
    assert PHASES_BY_NUMBER[phase].operating_rounds_per_stock_round == ors


def test_r2_2_8_unconverted_concessions_removed_from_phase_5():
    assert PHASES_BY_NUMBER[5].concession_rule == "removed"


@pytest.mark.parametrize("code,cost,count", [("L", 60, 22), ("3", 200, 9), ("4", 300, 6), ("5", 500, 3), ("6", 600, 3)])
def test_r5_10_x_train_costs_and_counts(code, cost, count):
    t = TRAIN_TYPES_BY_CODE[code]
    assert t.cost == cost and t.count == count


# ---- 3 corporate entities --------------------------------------------------
def test_r3_1_1_eighteen_private_companies_in_base_game():
    assert len(BASE_GAME_PRIVATE_COMPANIES) == 18


def test_r3_2_1_twenty_four_minor_companies_in_base_game():
    assert len(BASE_GAME_MINOR_COMPANIES) == 24


def test_r3_3_1_ten_major_companies():
    assert len(MAJOR_COMPANIES) == 10


def test_r3_1_3_private_face_value_is_zero():
    assert _face_value("private") == 0


def test_r3_4_2_concession_face_value_is_100():
    assert _face_value("concession") == 100


def test_r3_3_5_station_tokens_8_except_lnwr_9():
    for c in MAJOR_COMPANIES:
        assert c.station_tokens == (9 if c.abbr == "LNWR" else 8)


def test_r3_3_6_every_major_has_a_destination():
    assert all(c.destination for c in MAJOR_COMPANIES)


def test_r3_1_2_private_company_pays_owner_revenue_at_start_of_operating_round():
    """Rule 3.1.2: engine must pay each open private company's fixed revenue at the start of an OR."""
    s = game(); p = s.player_order[0]
    s.privates[2].owner_player_id = p                  # P2 Middleton Railway, revenue £10
    s.players[p].private_companies = [2]
    before = s.players[p].cash
    start_operating_round_set(s)
    assert s.players[p].cash == before + 10


def test_r3_4_4_concession_pays_10_per_operating_round():
    s = game(); p = s.player_order[0]
    s.players[p].concessions = ["GWR"]
    before = s.players[p].cash
    start_operating_round_set(s)
    assert s.players[p].cash == before + 10
