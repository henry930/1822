"""Tests derived from rulebook rules 5.1-5.3 and 5.12-5.13 (operating order, earnings, train purchase).
Rule id in each test name. Written from the rule text; engine used only for API names.
"""
import pytest

from app.engine.operating import distribute_earnings
from app.engine.setup import new_game
from app.engine.stock_positions import place_token
from app.engine.trains import TrainError, buy_train_from_bank
from app.engine.turn_order import compute_operating_order

P100 = (4, 4)       # £100
P110 = (4, 5)
P120 = (4, 6)
P90 = (4, 3)
P100_RIGHT = (5, 5)  # also £100, further right
ROW_END = (4, 20)   # rightmost cell of row 4 (£500)


def game(n=3):
    return new_game("g", [f"P{i}" for i in range(n)], seed=1)


def float_major(s, abbr, pos, director=None, **kw):
    m = s.majors[abbr]
    m.floated = True
    m.director_player_id = director
    for k, v in kw.items():
        setattr(m, k, v)
    place_token(s, abbr, *pos)
    return m


def float_minor(s, num, pos):
    m = s.minors[f"M{num}"]
    m.floated = True
    m.director_player_id = s.player_order[0]
    place_token(s, f"M{num}", *pos)
    return m


# ---- 5.2 operating order ---------------------------------------------------
def test_r5_2_1_minors_run_before_majors_even_if_cheaper():
    s = game()
    float_major(s, "GWR", (4, 6))                       # £120
    float_minor(s, 1, (4, 3))                           # £90
    assert compute_operating_order(s) == ["M1", "GWR"]


def test_r5_2_1_descending_share_price_within_type():
    s = game()
    float_major(s, "GWR", P100); float_major(s, "CR", (4, 6))
    assert compute_operating_order(s) == ["CR", "GWR"]


def test_r5_2_2_same_space_token_on_top_runs_first():
    s = game()
    float_major(s, "GWR", P100); float_major(s, "CR", P100)   # CR placed second -> bottom of pile
    assert compute_operating_order(s) == ["GWR", "CR"]


def test_r5_2_2_equal_value_different_spaces_rightmost_first():
    s = game()
    float_major(s, "GWR", P100); float_major(s, "CR", P100_RIGHT)
    assert compute_operating_order(s) == ["CR", "GWR"]


# ---- 5.12 earnings ---------------------------------------------------------
def major_with_holders(s, units_a, units_b, treasury_units=0, pool=0, pos=P100):
    a, b, _ = s.player_order
    m = float_major(s, "GWR", pos, director=a, shares_in_treasury=treasury_units, shares_in_bank_pool=pool)
    s.players[a].shares["GWR"] = units_a
    s.players[b].shares["GWR"] = units_b
    return m, a, b


def test_r5_12_3_dividend_pays_10_percent_per_share_and_treasury_shares_pay_the_company():
    s = game()
    m, a, b = major_with_holders(s, 4, 2, treasury_units=3, pool=1)
    ca, cb, t = s.players[a].cash, s.players[b].cash, m.treasury
    bank = s.bank.cash
    distribute_earnings(s, "GWR", "major", 100, "full")
    assert s.players[a].cash == ca + 40 and s.players[b].cash == cb + 20
    assert m.treasury == t + 30                          # 3 treasury shares
    assert s.bank.cash == bank - 90                      # bank-pool share's £10 stays in the bank


def test_r5_12_2_withhold_everything_goes_to_treasury():
    s = game(); m, a, b = major_with_holders(s, 4, 2)
    t = m.treasury
    distribute_earnings(s, "GWR", "major", 100, "withhold")
    assert m.treasury == t + 100


def test_r5_12_2_half_dividend_rounded_up_to_next_10():
    s = game(); m, a, b = major_with_holders(s, 10, 0)
    t, ca = m.treasury, s.players[a].cash
    paid = distribute_earnings(s, "GWR", "major", 70, "half")
    assert paid == 40                                    # 35 rounded up
    assert m.treasury == t + 30 and s.players[a].cash == ca + 40


def test_r5_12_8_zero_dividend_moves_price_left_one():
    s = game(); major_with_holders(s, 4, 2)
    distribute_earnings(s, "GWR", "major", 100, "withhold")
    assert s.stock_positions["GWR"] == P90


def test_r5_12_9_dividend_below_price_does_not_move():
    s = game(); major_with_holders(s, 4, 2)
    distribute_earnings(s, "GWR", "major", 50, "full")
    assert s.stock_positions["GWR"] == P100


def test_r5_12_10_dividend_at_least_price_moves_right_one():
    s = game(); major_with_holders(s, 4, 2)
    distribute_earnings(s, "GWR", "major", 100, "full")
    assert s.stock_positions["GWR"] == P110


def test_r5_12_11_dividend_at_least_twice_price_moves_right_two():
    s = game(); major_with_holders(s, 4, 2)
    distribute_earnings(s, "GWR", "major", 200, "full")
    assert s.stock_positions["GWR"] == P120


def test_r5_12_1_minor_splits_earnings_half_director_half_treasury():
    s = game()
    m = float_minor(s, 1, P100)
    d = s.players[m.director_player_id]
    cash, t = d.cash, m.treasury
    distribute_earnings(s, "M1", "minor", 60, "full")
    assert d.cash == cash + 30 and m.treasury == t + 30


def test_r5_12_12_minor_price_moves_right_after_dividend_left_if_none():
    s = game(); float_minor(s, 1, P100); float_minor(s, 2, P100_RIGHT)
    distribute_earnings(s, "M1", "minor", 60, "full")
    distribute_earnings(s, "M2", "minor", 0, "full")
    assert s.stock_positions["M1"] == P110
    assert s.stock_positions["M2"] == (5, 4)


def test_r5_12_13_token_at_row_end_follows_arrow_instead_of_staying():
    s = game(); major_with_holders(s, 4, 2, pos=ROW_END)
    distribute_earnings(s, "GWR", "major", 1000, "full")
    assert s.stock_positions["GWR"] != ROW_END


# ---- 5.13 purchasing trains ---------------------------------------------------
def fund(s, abbr="GWR", cash=2000):
    s.majors[abbr].treasury = cash
    return abbr


def test_r5_13_4_price_is_face_value_paid_to_bank():
    s = game(); a = fund(s)
    t, bank = s.majors[a].treasury, s.bank.cash
    buy_train_from_bank(s, a, "major", "L")
    assert s.majors[a].treasury == t - 60 and s.bank.cash == bank + 60


def test_r5_13_4_trains_must_be_bought_in_order():
    s = game(); a = fund(s)
    with pytest.raises(TrainError):
        buy_train_from_bank(s, a, "major", "3")           # L/2 trains still available


def test_r5_13_6_company_below_limit_may_buy_even_if_phase_change_puts_it_over():
    s = game(); a = fund(s)
    s.phase = 3
    s.bank.train_pool.update({"L": 0, "3": 0})
    s.majors[a].trains = ["3", "3", "3"]                   # 3 < limit 4 in phase 3
    buy_train_from_bank(s, a, "major", "4")                # phase 4 lowers limit to 3; allowed to buy
    assert "4" in s.majors[a].trains or len(s.bank.discarded_trains) == 1


def test_r5_13_7_company_at_train_limit_cannot_buy_even_if_it_triggers_phase_change():
    s = game(); a = fund(s)
    s.phase = 3
    s.bank.train_pool.update({"L": 0, "3": 0})
    s.majors[a].trains = ["3", "3", "3", "3"]              # exactly at limit 4 in phase 3
    with pytest.raises(TrainError):
        buy_train_from_bank(s, a, "major", "4")


def test_r5_13_8_company_chooses_L_or_2_side_when_buying():
    s = game(); a = fund(s)
    buy_train_from_bank(s, a, "major", "2")
    assert s.majors[a].trains == ["2"]


def test_r5_13_11_company_may_own_at_most_one_E_train():
    s = game(); a = fund(s, cash=5000)
    s.bank.train_pool.update({"L": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 16})
    s.phase = 7
    s.majors[a].trains = ["E"]
    with pytest.raises(TrainError):
        buy_train_from_bank(s, a, "major", "E")
