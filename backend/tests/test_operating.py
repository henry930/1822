import pytest

from app.engine.board import BoardState, apply_tile_lay
from app.engine.operating import (
    OperatingError,
    check_destination_connection,
    distribute_earnings,
    first_turn_housekeeping,
    home_hex_for,
    lay_track,
    reachable_hexes_for_tile_lay,
)
from app.engine.setup import new_game
from app.engine.stock_positions import place_token


def _game():
    return new_game("g1", ["Alice", "Bob", "Carol"], seed=1)


def test_home_hex_lookup_for_minor_and_major():
    assert home_hex_for("M3", "minor") == "H5"    # Edinburgh & Dalkeith (rules-verified)
    assert home_hex_for("NBR", "major") == "H5"    # NBR home is also Edinburgh


def test_first_turn_housekeeping_places_major_home_token_once():
    state = _game()
    board = BoardState(tile_pool={})
    major = state.majors["NBR"]
    first_turn_housekeeping(state, board, "NBR", "major")
    assert major.home_token_placed is True
    assert "H5" in major.tokens_on_map

    first_turn_housekeeping(state, board, "NBR", "major")  # idempotent, no duplicate
    assert major.tokens_on_map.count("H5") == 1


def test_lay_track_deducts_terrain_cost_from_treasury():
    state = _game()
    board = BoardState(tile_pool={})
    major = state.majors["NBR"]
    major.treasury = 100
    # NBR's home is H5 - connect it to H13 first (rule 5.7.9: a company can
    # only lay on a hex its own track reaches), then lay the actual tile
    # under test at the now-connected H13.
    for row in range(5, 13):
        apply_tile_lay(board, f"H{row}", "9", rotation=0)  # straight N-S chain, H5..H12
    cost = lay_track(state, board, "NBR", "major", "H13", "3", 0, treasury_field_owner=major)
    assert cost == 40  # H13 is a catalogued estuary hex
    assert major.treasury == 60
    assert board.tiles["H13"].tile_id == "3"


def test_lay_track_rejects_a_disconnected_hex():
    """The bug this guards against: found via manual play-testing - laying
    a tile on a hex with no track anywhere near it (e.g. J33) was silently
    accepted as long as the tile/rotation/phase were otherwise legal."""
    state = _game()
    board = BoardState(tile_pool={})
    major = state.majors["NBR"]  # home H5
    major.treasury = 1000
    with pytest.raises(OperatingError, match="isn't connected"):
        lay_track(state, board, "NBR", "major", "J33", "3", 0, treasury_field_owner=major)


def test_lay_track_allows_the_home_hex_with_no_track_yet():
    state = _game()
    board = BoardState(tile_pool={})
    major = state.majors["CR"]  # home E6 (Glasgow), unlabeled - plain tile 9 fits
    major.treasury = 1000
    lay_track(state, board, "CR", "major", "E6", "9", 0, treasury_field_owner=major)
    assert board.tiles["E6"].tile_id == "9"


def test_reachable_hexes_includes_home_and_track_connected_neighbors():
    state = _game()
    board = BoardState(tile_pool={})
    apply_tile_lay(board, "H5", "9", rotation=0)  # straight N-S: edges {0,3}
    reachable = reachable_hexes_for_tile_lay(state, board, "NBR", "major")
    assert "H5" in reachable  # home hex itself, always layable/upgradeable
    assert "H4" in reachable  # empty hex the placed tile's track actually points at
    assert "H6" in reachable
    assert "J33" not in reachable  # nowhere near the network


def test_destination_connection_detected_and_token_placed():
    state = _game()
    board = BoardState(tile_pool={})
    # Build a straight track chain from NBR's home (H5, Edinburgh) toward
    # its destination (H1, Aberdeen) - both in the same column, rows 5 and 1.
    for row in range(1, 6):
        apply_tile_lay(board, f"H{row}", "9", rotation=0)  # edges {0,3}: straight N-S

    assert check_destination_connection(board, state, "NBR") is True
    assert state.majors["NBR"].destination_token_placed is True
    assert "H1" in state.majors["NBR"].tokens_on_map


def test_destination_connection_false_when_not_yet_linked():
    state = _game()
    board = BoardState(tile_pool={})
    assert check_destination_connection(board, state, "NBR") is False
    assert state.majors["NBR"].destination_token_placed is False


def test_minor_earnings_always_split_and_bank_funded():
    state = _game()
    minor = state.minors["M3"]
    minor.director_player_id = state.player_order[0]
    place_token(state, "M3", row=9, col=4)  # solid-red minor-only £50 start space
    starting_bank = state.bank.cash
    starting_director_cash = state.players[state.player_order[0]].cash

    paid = distribute_earnings(state, "M3", "minor", revenue=100, choice="ignored")

    assert paid == 50
    assert minor.treasury == 50
    assert state.players[state.player_order[0]].cash == starting_director_cash + 50
    assert state.bank.cash == starting_bank - 100


def test_major_withhold_moves_price_left_one_space():
    state = _game()
    major = state.majors["GWR"]
    major.floated = True
    place_token(state, "GWR", row=4, col=4)  # value 100
    starting_bank = state.bank.cash

    paid = distribute_earnings(state, "GWR", "major", revenue=80, choice="withhold")

    assert paid == 0
    assert major.treasury == 80
    assert state.bank.cash == starting_bank - 80
    assert state.stock_positions["GWR"] == (4, 3)  # one space left


def test_major_full_dividend_pays_players_and_moves_price_right():
    state = _game()
    major = state.majors["GWR"]
    major.floated = True
    place_token(state, "GWR", row=4, col=4)  # value 100
    major.director_player_id = state.player_order[0]
    state.players[state.player_order[0]].shares["GWR"] = 2   # director's cert
    state.players[state.player_order[1]].shares["GWR"] = 1
    major.shares_in_bank_pool = 7
    starting_cash_p1 = state.players[state.player_order[0]].cash
    starting_bank = state.bank.cash

    # revenue = 200 -> per_share = 20; dividend_paid (200) >= 2x price (200) -> +2 spaces
    paid = distribute_earnings(state, "GWR", "major", revenue=200, choice="full")

    assert paid == 200
    assert state.players[state.player_order[0]].cash == starting_cash_p1 + 40  # 2 units * 20
    assert state.players[state.player_order[1]].cash == 700 + 20               # started with 700, +1 unit*20
    # only 3 of 10 units were paid (2 + 1); bank-pool's 7 units cost the bank nothing
    assert state.bank.cash == starting_bank - 60
    assert state.stock_positions["GWR"] == (4, 6)  # two spaces right along row 4: 100 -> 110 -> 120
