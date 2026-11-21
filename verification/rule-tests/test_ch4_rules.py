"""Pilot: tests derived from rulebook chapter 4 text (rules 4.2-4.5), written from the
rule wording, not from the engine implementation. Each test name carries its rule id
(r4_4_3 = rule 4.4.3). Engine API names were taken from the existing code only to call it.
"""
import pytest

from app.engine.actions import ActionError, apply_action
from app.engine.certificates import certificate_count, certificate_limit
from app.engine.setup import new_game
from app.engine.shares import ShareError, buy_share, sell_shares
from app.engine.stock_positions import place_token

START = (4, 4)      # £100 cell
YELLOW = (14, 0)    # £5, yellow zone
BOTTOM = (14, 2)    # £15, bottom row


def game(n=3):
    return new_game("g", [f"P{i}" for i in range(n)], seed=1)


def major(state, cid="GWR", pos=START, pool=0, treasury=0, operated=True, director="auto"):
    """A floated major. By default it has a director (rule 4.5.2: a company has no buyable ordinary
    shares until a player holds the director's certificate): the last player in order holds it (2 units).
    Pass director=None for a company without director."""
    m = state.majors[cid]
    m.floated = True
    m.has_operated = operated
    m.shares_in_bank_pool = pool
    m.shares_in_treasury = treasury
    if director == "auto":
        director = state.player_order[-1]
        state.players[director].shares[cid] = 2
    m.director_player_id = director
    place_token(state, cid, *pos)
    return m


def pad_certs(state, pid, n):
    """Give player pid n private-company certificates (each counts 1 certificate)."""
    state.players[pid].private_companies = list(range(100, 100 + n))


# ---- 4.2 certificate limit -------------------------------------------------
@pytest.mark.parametrize("n,lim", [(3, 26), (4, 20), (5, 16), (6, 13), (7, 11)])
def test_r4_2_1_certificate_limit_table(n, lim):
    assert certificate_limit(game(n)) == lim


def test_r4_2_2_privates_concessions_and_shares_count():
    s = game(); p = s.player_order[0]
    major(s, pool=5)
    s.players[p].private_companies = [1, 2]
    s.players[p].concessions = ["LNWR"]
    s.players[p].shares["GWR"] = 3
    assert certificate_count(s, p) == 2 + 1 + 3


def test_r4_2_3_yellow_zone_shares_do_not_count():
    s = game(); p = s.player_order[0]
    major(s, pos=YELLOW)
    s.players[p].shares["GWR"] = 4
    assert certificate_count(s, p) == 0


def test_r4_2_4_player_at_limit_cannot_buy():
    s = game(); p = s.player_order[0]
    major(s, pool=5)
    pad_certs(s, p, certificate_limit(s))
    with pytest.raises(ShareError):
        buy_share(s, p, "GWR")


# ---- 4.3 loans -------------------------------------------------------------
def test_r4_3_1_player_with_loans_cannot_buy_shares():
    s = game(); p = s.player_order[0]
    major(s, pool=5)
    s.players[p].loans = 100
    with pytest.raises((ShareError, ActionError)):
        apply_action(s, p, {"type": "buy_share", "company_id": "GWR"})


# ---- 4.4 selling -----------------------------------------------------------
def test_r4_4_1_cannot_sell_before_company_operated():
    s = game(); p = s.player_order[0]
    major(s, operated=False)
    s.players[p].shares["GWR"] = 3
    with pytest.raises(ShareError):
        sell_shares(s, p, "GWR", 1)


def test_r4_4_1_bank_pool_cap_50_percent():
    s = game(); p = s.player_order[0]
    major(s, pool=4)
    s.players[p].shares["GWR"] = 3
    with pytest.raises(ShareError):
        sell_shares(s, p, "GWR", 2)
    sell_shares(s, p, "GWR", 1)  # pool reaches exactly 50%: allowed
    assert s.majors["GWR"].shares_in_bank_pool == 5


def test_r4_4_1_directors_certificate_cannot_be_sold():
    s = game(); p = s.player_order[0]
    major(s, director=p)
    s.players[p].shares["GWR"] = 2   # director's certificate only
    with pytest.raises(ShareError):
        sell_shares(s, p, "GWR", 1)


def test_r4_4_2_director_changes_when_holding_drops_below_other():
    s = game(); p1, p2, p3 = s.player_order
    major(s, director=p1)
    s.players[p1].shares["GWR"] = 4
    s.players[p2].shares["GWR"] = 3
    sell_shares(s, p1, "GWR", 2)
    assert s.majors["GWR"].director_player_id == p2


def test_r4_4_2_no_change_if_other_player_below_20_percent():
    s = game(); p1, p2, p3 = s.player_order
    major(s, director=p1)
    s.players[p1].shares["GWR"] = 3
    s.players[p2].shares["GWR"] = 1   # 10% is not enough to take over (needs 20%)
    sell_shares(s, p1, "GWR", 1)
    assert s.majors["GWR"].director_player_id == p1


def test_r4_4_2_tie_goes_to_player_closest_after_outgoing_director():
    s = game(); p1, p2, p3 = s.player_order
    major(s, director=p3)
    s.players[p3].shares["GWR"] = 4
    s.players[p1].shares["GWR"] = 3
    s.players[p2].shares["GWR"] = 3
    sell_shares(s, p3, "GWR", 2)
    # next in player order after p3 is p1
    assert s.majors["GWR"].director_player_id == p1


def test_r4_4_3_seller_receives_current_price_for_each_share():
    """Rule 4.4.3 then 4.4.4: each share is paid at the current price, then the
    price drops one space per share sold."""
    s = game(); p = s.player_order[0]
    major(s)
    s.players[p].shares["GWR"] = 3
    before = s.players[p].cash
    sell_shares(s, p, "GWR", 2)
    assert s.players[p].cash == before + 2 * 100


def test_r4_4_4_price_drops_one_space_per_share_sold():
    s = game(); p = s.player_order[0]
    major(s)
    s.players[p].shares["GWR"] = 3
    sell_shares(s, p, "GWR", 2)
    assert s.stock_positions["GWR"] == (6, 4)


def test_r4_4_4_token_stops_at_bottom_row():
    s = game(); p = s.player_order[0]
    major(s, pos=BOTTOM)
    s.players[p].shares["GWR"] = 3
    sell_shares(s, p, "GWR", 2)
    assert s.stock_positions["GWR"] == BOTTOM


def test_r4_4_5_arriving_token_goes_to_bottom_of_pile():
    s = game(); p = s.player_order[0]
    major(s, "GWR"); major(s, "LNWR", pos=(5, 4))
    s.players[p].shares["GWR"] = 3
    sell_shares(s, p, "GWR", 1)
    assert s.stock_stack[(5, 4)][-1] == "GWR"      # list is top-first
    assert s.stock_stack[(5, 4)][0] == "LNWR"


def test_r4_4_5_token_that_does_not_move_keeps_relative_position():
    s = game(); p = s.player_order[0]
    major(s, "GWR", pos=BOTTOM); major(s, "LNWR", pos=BOTTOM)
    s.players[p].shares["GWR"] = 3
    order_before = list(s.stock_stack[BOTTOM])
    sell_shares(s, p, "GWR", 1)
    assert s.stock_stack[BOTTOM] == order_before


# ---- 4.5 buying ------------------------------------------------------------
def test_r4_5_1_bank_pool_purchase_pays_bank():
    s = game(); p = s.player_order[0]
    major(s, pool=2, treasury=3)
    cash, bank = s.players[p].cash, s.bank.cash
    buy_share(s, p, "GWR", source="bank")
    assert s.players[p].cash == cash - 100 and s.bank.cash == bank + 100


def test_r4_5_1_treasury_purchase_pays_company():
    s = game(); p = s.player_order[0]
    m = major(s, pool=2, treasury=3)
    t = m.treasury
    buy_share(s, p, "GWR", source="treasury")
    assert m.treasury == t + 100 and m.shares_in_treasury == 2


def test_r4_5_2_ordinary_share_not_buyable_without_director():
    s = game(); p = s.player_order[0]
    major(s, pool=5, director=None)
    with pytest.raises(ShareError):
        buy_share(s, p, "GWR")


def test_r4_5_3_buying_does_not_change_price():
    s = game(); p = s.player_order[0]
    major(s, pool=5)
    buy_share(s, p, "GWR")
    assert s.stock_positions["GWR"] == START


def test_r4_5_4_only_one_certificate_per_turn():
    s = game(); p = s.player_order[0]
    major(s, pool=5)
    s.active_player_id = p
    apply_action(s, p, {"type": "buy_share", "company_id": "GWR"})
    with pytest.raises(ActionError):
        apply_action(s, p, {"type": "buy_share", "company_id": "GWR"})


def test_r4_5_5_cannot_buy_company_sold_earlier_in_same_round():
    s = game(); p = s.player_order[0]
    major(s, pool=0)
    s.players[p].shares["GWR"] = 3
    sell_shares(s, p, "GWR", 1)
    with pytest.raises(ShareError):
        buy_share(s, p, "GWR")


def test_r4_5_6_cannot_exceed_60_percent():
    s = game(); p = s.player_order[0]
    major(s, pool=5)
    s.players[p].shares["GWR"] = 5
    buy_share(s, p, "GWR")           # 60% reached
    assert s.players[p].shares["GWR"] == 6
    with pytest.raises(ShareError):
        buy_share(s, p, "GWR")


def test_r4_5_7_at_limit_purchase_blocked_even_if_it_changes_director():
    s = game(); p1, p2, _ = s.player_order
    major(s, pool=5, director=p2)
    s.players[p2].shares["GWR"] = 2
    s.players[p1].shares["GWR"] = 2
    pad_certs(s, p1, certificate_limit(s) - 2)
    assert certificate_count(s, p1) == certificate_limit(s)
    with pytest.raises(ShareError):
        buy_share(s, p1, "GWR")


def test_r4_5_8_yellow_zone_stock_buyable_at_certificate_limit():
    s = game(); p = s.player_order[0]
    major(s, pos=YELLOW, pool=5)
    pad_certs(s, p, certificate_limit(s))
    buy_share(s, p, "GWR")
    assert s.players[p].shares["GWR"] == 1


def test_r4_5_9_buyer_exceeding_director_becomes_director():
    s = game(); p1, p2, _ = s.player_order
    major(s, pool=5, director=p2)
    s.players[p2].shares["GWR"] = 2
    s.players[p1].shares["GWR"] = 2
    buy_share(s, p1, "GWR")
    assert s.majors["GWR"].director_player_id == p1
