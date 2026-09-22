import pytest

from app.engine.actions import ActionError, apply_action
from app.engine.setup import new_game
from app.engine.shares import ShareError, buy_share, sell_shares
from app.engine.stock_positions import place_token


def _floated_major(state, company_id="GWR", row=4, col=4, bank_pool=0, treasury_shares=0):
    major = state.majors[company_id]
    major.floated = True
    major.shares_in_bank_pool = bank_pool
    major.shares_in_treasury = treasury_shares
    place_token(state, company_id, row, col)  # value 100 (see test_stock_market_par_column test)
    return major


def _game():
    return new_game("g1", ["Alice", "Bob", "Carol"], seed=1)


def test_buy_share_from_bank_pool_transfers_cash_and_updates_holding():
    state = _game()
    _floated_major(state, bank_pool=5)
    p1 = state.player_order[0]
    starting_cash = state.players[p1].cash
    starting_bank_cash = state.bank.cash

    apply_action(state, p1, {"type": "buy_share", "company_id": "GWR"})

    assert state.players[p1].shares["GWR"] == 1
    assert state.players[p1].cash == starting_cash - 100
    assert state.bank.cash == starting_bank_cash + 100
    assert state.majors["GWR"].shares_in_bank_pool == 4
    assert state.active_player_id == state.player_order[1]  # turn advanced


def test_buy_share_becomes_director_when_holding_exceeds_current_director():
    state = _game()
    _floated_major(state, bank_pool=5)
    p1, p2, _p3 = state.player_order
    state.majors["GWR"].director_player_id = p2
    state.players[p2].shares["GWR"] = 2

    buy_share(state, p1, "GWR")
    assert state.majors["GWR"].director_player_id == p2  # 1 share still < p2's 2

    state.players[p1].shares["GWR"] = 2
    buy_share(state, p1, "GWR")
    assert state.majors["GWR"].director_player_id == p1  # 3 > 2


def test_cannot_hold_more_than_60_percent():
    state = _game()
    _floated_major(state, bank_pool=10)
    p1 = state.player_order[0]
    state.players[p1].shares["GWR"] = 6
    with pytest.raises(ShareError):
        buy_share(state, p1, "GWR")


def test_cannot_sell_before_company_has_operated():
    state = _game()
    _floated_major(state)
    p1 = state.player_order[0]
    state.players[p1].shares["GWR"] = 3
    with pytest.raises(ShareError):
        sell_shares(state, p1, "GWR", 1)


def test_sell_moves_price_down_once_per_share_and_pays_seller():
    state = _game()
    _floated_major(state)
    state.majors["GWR"].has_operated = True
    p1 = state.player_order[0]
    state.players[p1].shares["GWR"] = 3  # not director, so all 3 are sellable

    proceeds_cash_before = state.players[p1].cash
    apply_action(state, p1, {"type": "sell_shares", "company_id": "GWR", "count": 2})

    # value 100 -> after 2 down-moves: row4->5->6, values 100,90,80 (rule 4.4.4)
    # first share sold at 100, second at 90 = 190 total
    assert state.players[p1].cash == proceeds_cash_before + 190
    assert state.players[p1].shares["GWR"] == 1
    assert state.majors["GWR"].shares_in_bank_pool == 2
    assert state.stock_positions["GWR"] == (6, 4)


def test_cannot_sell_more_than_50_percent_into_bank_pool():
    state = _game()
    _floated_major(state, bank_pool=4)
    state.majors["GWR"].has_operated = True
    p1 = state.player_order[0]
    state.players[p1].shares["GWR"] = 3
    with pytest.raises(ShareError):
        sell_shares(state, p1, "GWR", 2)  # would put bank pool at 6 > 5


def test_selling_directors_certificate_amount_is_blocked_not_the_two_units():
    state = _game()
    _floated_major(state)
    state.majors["GWR"].has_operated = True
    p1 = state.player_order[0]
    state.majors["GWR"].director_player_id = p1
    state.players[p1].shares["GWR"] = 2  # exactly the director's certificate
    with pytest.raises(ShareError):
        sell_shares(state, p1, "GWR", 1)  # can't sell into the director's block


def test_director_departs_when_sale_drops_below_another_holder():
    state = _game()
    _floated_major(state)
    state.majors["GWR"].has_operated = True
    p1, p2, _p3 = state.player_order
    state.majors["GWR"].director_player_id = p1
    state.players[p1].shares["GWR"] = 4  # director, sellable = 4 - 2 = 2
    state.players[p2].shares["GWR"] = 3

    sell_shares(state, p1, "GWR", 2)  # p1 drops to 2, p2 (3) now larger
    assert state.majors["GWR"].director_player_id == p2


def test_cannot_buy_and_sell_same_company_in_one_stock_round():
    state = _game()
    _floated_major(state)
    state.majors["GWR"].has_operated = True
    p1 = state.player_order[0]
    state.players[p1].shares["GWR"] = 2
    sell_shares(state, p1, "GWR", 1)
    with pytest.raises(ShareError):
        buy_share(state, p1, "GWR")


def test_wrong_player_cannot_buy_out_of_turn():
    state = _game()
    _floated_major(state)
    _p1, p2, _p3 = state.player_order
    with pytest.raises(ActionError):
        apply_action(state, p2, {"type": "buy_share", "company_id": "GWR"})
