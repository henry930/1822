"""Acceptance tests for the three maintenance changes (new behaviour)."""
import sys
import pytest
from app.engine.bidding import place_or_move_bid, resolve_stock_round
from app.engine.setup import new_game
from app.engine.shares import sell_shares
from app.engine.stock_positions import place_token
from test_ch4_rules import major, game


def test_M1_interest_is_25_percent_rounded_up():
    s = game(); p = s.player_order[0]
    s.players[p].loans = 100
    resolve_stock_round(s)
    assert s.players[p].loans == 125


def test_M1_interest_rounds_up():
    s = game(); p = s.player_order[0]
    s.players[p].loans = 101
    resolve_stock_round(s)
    assert s.players[p].loans == 127          # 101 + ceil(101/4)=26


def test_M2_pool_may_reach_6_units():
    s = game(); a, b, c = s.player_order
    major(s, pool=4); s.players[a].shares["GWR"] = 2
    sell_shares(s, a, "GWR", 2)
    assert s.majors["GWR"].shares_in_bank_pool == 6


def test_M2_pool_cannot_exceed_6_units():
    s = game(); a, b, c = s.player_order
    major(s, pool=5); s.players[a].shares["GWR"] = 2
    with pytest.raises(Exception):
        sell_shares(s, a, "GWR", 2)


def test_M3_phase3_minor_treasury_is_half_the_bid():
    s = game(); p = s.player_order[0]
    s.phase = 3
    num = s.minor_bid_boxes[0].ref
    place_or_move_bid(s, p, "minor", 0, 140)
    cash = s.players[p].cash
    resolve_stock_round(s)
    m = s.minors[f"M{num}"]
    assert m.floated and m.treasury == 70
    assert s.players[p].cash == cash - 140
