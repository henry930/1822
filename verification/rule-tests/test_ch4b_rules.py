"""Tests derived from rulebook rules 4.1 and 4.6-4.12 (formation, bidding, end of stock round).
Rule id in each test name. Written from the rule text; engine used only for API names.
"""
import pytest

from app.engine.actions import ActionError, apply_action
from app.engine.bidding import BidError, place_or_move_bid, resolve_stock_round
from app.engine.certificates import certificate_limit
from app.engine.company_formation import ConcessionError, convert_concession
from app.engine.models import BidBoxItem
from app.engine.round_manager import end_stock_round, start_stock_round
from app.engine.setup import new_game
from app.engine.stock_positions import place_token
from app.engine.turn_order import reorder_players_by_cash


def game(n=3):
    return new_game("g", [f"P{i}" for i in range(n)], seed=1)


def total_money(s):
    return (s.bank.cash + sum(p.cash for p in s.players.values())
            + sum(m.treasury for m in s.majors.values()) + sum(m.treasury for m in s.minors.values()))


def holder(s, abbr="GWR"):
    p = s.player_order[0]
    s.players[p].concessions = [abbr]
    return p


# ---- 4.1 -------------------------------------------------------------------
def test_r4_1_2_stock_round_starts_with_player_1_card_holder():
    s = game()
    s.priority_deal_player_id = s.player_order[1]
    start_stock_round(s)
    assert s.active_player_id == s.player_order[1]


def test_r4_10_1_bidding_box_counts():
    s = game()
    assert (len(s.minor_bid_boxes), len(s.concession_bid_boxes), len(s.private_bid_boxes)) == (4, 3, 3)


def test_r4_1_1_boxes_filled_at_start():
    s = game()
    assert all(b is not None for b in s.minor_bid_boxes + s.concession_bid_boxes + s.private_bid_boxes)


# ---- 4.7 converting a concession ------------------------------------------
@pytest.mark.parametrize("phase,ok", [(1, False), (2, True), (3, True), (4, True), (5, False)])
def test_r4_7_1_concession_conversion_only_in_phases_2_to_4(phase, ok):
    s = game(); p = holder(s); s.phase = phase
    if ok:
        convert_concession(s, p, "GWR", 80)
        assert s.majors["GWR"].floated
    else:
        with pytest.raises(ConcessionError):
            convert_concession(s, p, "GWR", 80)


def test_r4_7_2_start_price_must_be_a_red_outlined_value_60_to_100():
    s = game(); p = holder(s); s.phase = 2
    with pytest.raises(ConcessionError):
        convert_concession(s, p, "GWR", 50)


def test_r4_7_2_token_placed_on_announced_price():
    s = game(); p = holder(s); s.phase = 2
    convert_concession(s, p, "GWR", 80)
    from app.engine.stock_positions import company_value
    assert company_value(s, "GWR") == 80


def test_r4_7_3_treasury_is_twice_start_price_funded_100_from_bank_rest_from_player():
    s = game(); p = holder(s); s.phase = 2
    cash, bank = s.players[p].cash, s.bank.cash
    convert_concession(s, p, "GWR", 80)
    assert s.majors["GWR"].treasury == 160
    assert s.players[p].cash == cash - 60            # 2*80 - 100
    assert s.bank.cash == bank - 100                 # the £100 comes from the bank


def test_r4_7_3_money_is_conserved_when_converting():
    s = game(); p = holder(s); s.phase = 2
    before = total_money(s)
    convert_concession(s, p, "GWR", 80)
    assert total_money(s) == before


def test_r4_7_3_remaining_certificates_go_to_company_treasury():
    s = game(); p = holder(s); s.phase = 2
    convert_concession(s, p, "GWR", 80)
    assert s.majors["GWR"].shares_in_treasury == 8   # nine certs: director's (2 shares) + 8 single shares


def test_r4_7_4_lnwr_whole_start_price_from_bank_player_pays_nothing():
    s = game(); p = holder(s, "LNWR"); s.phase = 2
    cash, bank = s.players[p].cash, s.bank.cash
    convert_concession(s, p, "LNWR", 80)
    assert s.players[p].cash == cash and s.bank.cash == bank - 80
    assert s.majors["LNWR"].treasury == 80 and s.players[p].shares["LNWR"] == 1
    assert s.majors["LNWR"].shares_in_treasury == 9


# ---- 4.10 bidding ----------------------------------------------------------
def bid_ready(n=3):
    s = game(n)
    return s, s.player_order[0], s.player_order[1]


def test_r4_10_6_opening_bid_at_least_face_value():
    s, p, _ = bid_ready()
    with pytest.raises(BidError):
        place_or_move_bid(s, p, "concession", 0, 95)


def test_r4_10_6_bids_in_multiples_of_5():
    s, p, _ = bid_ready()
    with pytest.raises(BidError):
        place_or_move_bid(s, p, "concession", 0, 102)


def test_r4_10_7_bid_must_exceed_previous_bids():
    s, p, q = bid_ready()
    place_or_move_bid(s, p, "concession", 0, 120)
    with pytest.raises(BidError):
        place_or_move_bid(s, q, "concession", 0, 120)
    place_or_move_bid(s, q, "concession", 0, 125)


def test_r4_10_7_committed_resources_cannot_exceed_cash():
    s, p, _ = bid_ready()
    s.players[p].cash = 150
    place_or_move_bid(s, p, "concession", 0, 100)
    with pytest.raises(BidError):
        place_or_move_bid(s, p, "concession", 1, 100)   # 200 committed > 150 cash


def test_r4_10_4_cannot_raise_own_bid_when_already_highest():
    s, p, _ = bid_ready()
    place_or_move_bid(s, p, "concession", 0, 100)
    with pytest.raises(BidError):
        place_or_move_bid(s, p, "concession", 0, 105)


def test_r4_10_4_may_move_bid_up_when_outbid():
    s, p, q = bid_ready()
    place_or_move_bid(s, p, "concession", 0, 100)
    place_or_move_bid(s, q, "concession", 0, 110)
    place_or_move_bid(s, p, "concession", 0, 115)
    assert s.concession_bid_boxes[0].bids[p] == 115


def test_r4_10_3_bidding_tokens_limit_items_bid_on():
    s = game(7)                                       # 7 players: 3 bidding tokens
    p = s.player_order[0]
    place_or_move_bid(s, p, "private", 0, 5)
    place_or_move_bid(s, p, "private", 1, 5)
    place_or_move_bid(s, p, "private", 2, 5)
    with pytest.raises(BidError):
        place_or_move_bid(s, p, "minor", 0, 100)


def test_r4_10_5_at_most_three_bids_per_turn():
    s = game(); p = s.player_order[0]; s.active_player_id = p
    four = [{"kind": "private", "box_index": 0, "amount": 5}, {"kind": "private", "box_index": 1, "amount": 5},
            {"kind": "private", "box_index": 2, "amount": 5}, {"kind": "concession", "box_index": 0, "amount": 100}]
    with pytest.raises(ActionError):
        apply_action(s, p, {"type": "bid", "bids": four})
    s2 = game(); p2 = s2.player_order[0]; s2.active_player_id = p2
    apply_action(s2, p2, {"type": "bid", "bids": four[:3]})   # three bids in one turn are allowed


def test_r4_10_8_player_at_certificate_limit_cannot_bid():
    s, p, _ = bid_ready()
    s.players[p].private_companies = list(range(100, 100 + certificate_limit(s)))
    with pytest.raises(BidError):
        place_or_move_bid(s, p, "concession", 0, 100)


def test_r4_10_8_items_with_top_bid_count_against_limit():
    s, p, _ = bid_ready()
    s.players[p].private_companies = list(range(100, 100 + certificate_limit(s) - 1))
    place_or_move_bid(s, p, "concession", 0, 100)     # now at the limit
    with pytest.raises(BidError):
        place_or_move_bid(s, p, "concession", 1, 100)


def test_r4_10_9_bid_100_or_more_over_face_value_allowed():
    s, p, _ = bid_ready()
    s.players[p].cash = 700
    place_or_move_bid(s, p, "concession", 0, 250)
    assert s.concession_bid_boxes[0].bids[p] == 250


# ---- 4.11 end of stock round ----------------------------------------------
def test_r4_11_2_winner_pays_and_takes_concession_and_tokens_removed():
    s, p, q = bid_ready()
    abbr = s.concession_bid_boxes[0].ref
    place_or_move_bid(s, p, "concession", 0, 120)
    place_or_move_bid(s, q, "concession", 0, 130)
    cash_q = s.players[q].cash
    resolve_stock_round(s)
    assert s.players[q].cash == cash_q - 130
    assert len(s.players[q].concessions) == 1


def test_r4_11_2_winner_of_private_becomes_owner():
    s, p, _ = bid_ready()
    num = s.private_bid_boxes[0].ref
    place_or_move_bid(s, p, "private", 0, 10)
    resolve_stock_round(s)
    assert s.privates[num].owner_player_id == p


def test_r4_11_4_phase_1_minor_starts_at_50_with_100_treasury_whatever_the_bid():
    s, p, _ = bid_ready()
    num = s.minor_bid_boxes[0].ref
    place_or_move_bid(s, p, "minor", 0, 140)
    cash = s.players[p].cash
    resolve_stock_round(s)
    m = s.minors[f"M{num}"]
    assert m.floated and m.treasury == 100
    assert s.players[p].cash == cash - 140
    assert s.stock_positions[f"M{num}"] is not None


def test_r4_11_6_each_unsold_minor_exports_one_train_and_box1_unsold_exports_another():
    s = game()
    before = s.bank.train_pool["L"]
    resolve_stock_round(s)                            # nobody bid: 4 unsold minors + box-1 minor removed
    assert s.bank.train_pool["L"] == before - 5


def test_r4_11_7_unsold_minor_in_box_1_is_removed_from_play():
    s = game()
    num = s.minor_bid_boxes[0].ref
    resolve_stock_round(s)
    assert s.minors[f"M{num}"].removed


def test_r4_11_8_boxes_refilled_after_resolution():
    s = game()
    resolve_stock_round(s)
    assert all(b is not None for b in s.minor_bid_boxes + s.concession_bid_boxes + s.private_bid_boxes)


def test_r4_11_9_turn_order_by_cash_ties_keep_previous_order():
    s = game(); a, b, c = s.player_order
    s.players[a].cash, s.players[b].cash, s.players[c].cash = 300, 500, 300
    assert reorder_players_by_cash(s) == [b, a, c]


def test_r4_11_10_interest_50_percent_rounded_up_on_loans():
    s = game(); p = s.player_order[0]
    s.players[p].loans = 101
    resolve_stock_round(s)
    assert s.players[p].loans == 101 + 51


# ---- 4.12 ------------------------------------------------------------------
def test_r4_12_1_fully_sold_company_price_moves_up_at_end_of_stock_round():
    s = game(); a, b, c = s.player_order
    m = s.majors["GWR"]
    m.floated = True; m.director_player_id = a; m.shares_in_bank_pool = 0; m.shares_in_treasury = 0
    s.players[a].shares["GWR"] = 6; s.players[b].shares["GWR"] = 4
    place_token(s, "GWR", 4, 4)                       # £100
    s.stock_rounds_completed = 1; s.any_sale_this_stock_round = True
    end_stock_round(s)
    assert s.stock_positions["GWR"] == (3, 4)         # one space up


def test_r4_12_1_company_with_shares_in_pool_does_not_move_up():
    s = game(); a, b, c = s.player_order
    m = s.majors["GWR"]
    m.floated = True; m.director_player_id = a; m.shares_in_bank_pool = 1
    s.players[a].shares["GWR"] = 5; s.players[b].shares["GWR"] = 4
    place_token(s, "GWR", 4, 4)
    s.stock_rounds_completed = 1; s.any_sale_this_stock_round = True
    end_stock_round(s)
    assert s.stock_positions["GWR"] == (4, 4)
