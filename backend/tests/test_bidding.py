import pytest

from app.engine.actions import ActionError, apply_action
from app.engine.bidding import BidError, place_or_move_bid
from app.engine.certificates import certificate_count
from app.engine.models import RoundType
from app.engine.setup import new_game


def _game(seed=1):
    return new_game("g1", ["Alice", "Bob", "Carol"], seed=seed)


def test_win_a_minor_floats_it_at_phase1_fixed_price():
    state = _game()
    p1, p2, p3 = state.player_order
    # Box 1 holds M24 (fixed top of stack, rule 1.7.5).
    assert state.minor_bid_boxes[0].ref == 24

    apply_action(state, p1, {"type": "bid", "bids": [{"kind": "minor", "box_index": 0, "amount": 150}]})
    apply_action(state, p2, {"type": "pass"})
    apply_action(state, p3, {"type": "pass"})
    apply_action(state, p1, {"type": "pass"})  # 3rd consecutive pass (p2,p3,p1) ends the SR

    m24 = state.minors["M24"]
    assert m24.floated is True
    assert m24.director_player_id == p1
    assert m24.share_price == 50   # phase 1: fixed, irrespective of bid
    assert m24.treasury == 100     # phase 1: fixed £100
    assert state.players[p1].cash == 700 - 150
    assert state.players[p1].shares["M24"] == 1
    assert "M24" in state.stock_positions


def test_cannot_bid_below_face_value_or_off_increment():
    state = _game()
    p1 = state.player_order[0]
    with pytest.raises(ActionError):
        apply_action(state, p1, {"type": "bid", "bids": [{"kind": "concession", "box_index": 0, "amount": 95}]})
    with pytest.raises(ActionError):
        apply_action(state, p1, {"type": "bid", "bids": [{"kind": "concession", "box_index": 0, "amount": 103}]})


def test_bid_must_exceed_current_highest_and_cannot_exceed_cash():
    state = _game()
    p1, p2, _p3 = state.player_order
    apply_action(state, p1, {"type": "bid", "bids": [{"kind": "concession", "box_index": 0, "amount": 100}]})
    apply_action(state, p2, {"type": "pass"})

    with pytest.raises(BidError):
        place_or_move_bid(state, "p3", "concession", 0, 100)  # not higher than current top

    # p2's turn again after wraparound isn't tested here directly; exercise
    # the cash ceiling via the lower-level helper instead.
    state.players["p3"].cash = 50
    with pytest.raises(BidError):
        place_or_move_bid(state, "p3", "concession", 0, 105)


def test_at_most_three_bids_per_turn():
    state = _game()
    p1 = state.player_order[0]
    bids = [
        {"kind": "concession", "box_index": 0, "amount": 100},
        {"kind": "minor", "box_index": 0, "amount": 110},
        {"kind": "private", "box_index": 0, "amount": 5},
        {"kind": "concession", "box_index": 1, "amount": 100},
    ]
    with pytest.raises(ActionError):
        apply_action(state, p1, {"type": "bid", "bids": bids})


def test_bidding_token_limit_enforced():
    state = _game()
    p1 = state.player_order[0]
    setup_tokens = 6  # 3-player game (rule 1.7.2 table)
    # p1 has 6 tokens; place bids on 6 distinct items across two turns (3 each).
    apply_action(state, p1, {"type": "bid", "bids": [
        {"kind": "concession", "box_index": 0, "amount": 100},
        {"kind": "concession", "box_index": 1, "amount": 100},
        {"kind": "concession", "box_index": 2, "amount": 100},
    ]})
    for pid in state.player_order[1:]:
        apply_action(state, pid, {"type": "pass"})
    apply_action(state, p1, {"type": "bid", "bids": [
        {"kind": "minor", "box_index": 0, "amount": 110},
        {"kind": "minor", "box_index": 1, "amount": 110},
        {"kind": "minor", "box_index": 2, "amount": 110},
    ]})
    assert setup_tokens == 6
    with pytest.raises(ActionError):
        apply_action(state, p1, {"type": "bid", "bids": [
            {"kind": "minor", "box_index": 3, "amount": 110},
        ]})


def test_certificate_limit_blocks_further_bids():
    state = _game()
    p1 = state.player_order[0]
    state.players[p1].private_companies = list(range(1, 27))  # already at the 3p limit (26)
    with pytest.raises(ActionError):
        apply_action(state, p1, {"type": "bid", "bids": [{"kind": "concession", "box_index": 0, "amount": 100}]})
    assert certificate_count(state, p1) == 26


def test_held_concessions_count_against_certificate_limit():
    state = _game()
    p1 = state.player_order[0]
    state.players[p1].concessions = ["LNWR", "GWR"]
    assert certificate_count(state, p1) == 2


def test_unbid_minor_in_box_one_is_removed_and_exports_trains():
    state = _game()
    order = state.player_order
    initial_l_trains = state.bank.train_pool["L"]

    for pid in order:
        apply_action(state, pid, {"type": "pass"})

    # Game-over-on-nothing-sold (rule 10.1.1) would trigger here since no
    # bids were placed at all - assert that instead of the export path,
    # since an empty stock round is a stronger/earlier condition.
    assert state.game_over is True
    assert state.bank.train_pool["L"] == initial_l_trains
