from app.engine.actions import apply_action
from app.engine.board import apply_tile_lay
from app.engine.models import RoundType
from app.engine.round_manager import start_operating_round_set
from app.engine.scoring import check_game_end_triggers, final_standings, final_wealth
from app.engine.setup import new_game
from app.engine.stock_positions import place_token


def _game():
    return new_game("g1", ["Alice", "Bob", "Carol"], seed=1)


def test_stock_reaching_game_end_during_operating_round_ends_after_that_or():
    state = _game()
    director = state.player_order[0]
    minor = state.minors["M3"]  # home Edinburgh (H5)
    minor.floated = True
    minor.director_player_id = director
    minor.trains = ["2"]
    # One step below the game-end cell: a positive dividend this OR moves it
    # right exactly one space, onto £700 - simulating actually *reaching* it
    # via play, not teleporting it there and having an unrelated move undo it.
    place_token(state, "M3", row=0, col=2)  # £650

    for row in range(1, 6):
        apply_tile_lay(state.board, f"H{row}", "9", rotation=0)  # H5 -> H1 (Aberdeen), revenue route

    start_operating_round_set(state)
    assert state.round_type == RoundType.OPERATING
    apply_action(state, director, {"type": "operate", "company_id": "M3"})

    assert state.stock_positions["M3"] == (0, 3)  # confirms it actually arrived at £700
    assert state.game_over is True


def test_stock_reaching_game_end_during_stock_round_ends_after_next_or():
    state = _game()
    director = state.player_order[0]
    minor = state.minors["M3"]
    minor.floated = True
    minor.director_player_id = director
    minor.trains = ["2"]
    place_token(state, "M3", row=0, col=3)  # value 700 (game_end cell)

    check_game_end_triggers(state)  # state.round_type is STOCK here
    assert state.end_trigger_pending == "next_or"
    assert state.game_over is False

    start_operating_round_set(state)
    assert state.operating_rounds_this_set == 1  # capped regardless of phase
    apply_action(state, director, {"type": "operate", "company_id": "M3"})
    assert state.game_over is True


def test_bank_empty_during_operating_round_finishes_the_whole_set_first():
    state = _game()
    state.phase = 2  # 2 ORs per set
    director = state.player_order[0]
    minor = state.minors["M3"]
    minor.floated = True
    minor.director_player_id = director
    minor.trains = ["2"]
    place_token(state, "M3", row=9, col=4)
    state.bank.cash = 0
    start_operating_round_set(state)

    assert state.operating_rounds_this_set == 2
    apply_action(state, director, {"type": "operate", "company_id": "M3"})
    assert state.game_over is False  # first OR of the set done, one more to go
    assert state.round_type == RoundType.OPERATING
    apply_action(state, director, {"type": "operate", "company_id": "M3"})
    assert state.game_over is True


def test_final_wealth_includes_cash_stock_value_and_concessions_minus_loans():
    state = _game()
    p1 = state.player_order[0]
    state.players[p1].cash = 500
    state.players[p1].loans = 50
    state.players[p1].concessions = ["GWR"]
    state.players[p1].shares["GWR"] = 2
    place_token(state, "GWR", row=4, col=4)  # value 100

    wealth = final_wealth(state, p1)
    assert wealth == 500 - 50 + 100 + 2 * 100  # cash - loans + concession face + 2 shares @ 100


def test_final_standings_ranks_richest_first():
    state = _game()
    p1, p2, p3 = state.player_order
    state.players[p1].cash = 100
    state.players[p2].cash = 900
    state.players[p3].cash = 500

    standings = final_standings(state)
    assert [pid for pid, _ in standings] == [p2, p3, p1]
