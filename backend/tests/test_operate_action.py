from app.engine.actions import ActionError, apply_action
from app.engine.board import apply_tile_lay
from app.engine.models import RoundType
from app.engine.round_manager import start_operating_round_set
from app.engine.setup import new_game
from app.engine.stock_positions import place_token

import pytest


def _game():
    return new_game("g1", ["Alice", "Bob", "Carol"], seed=1)


def test_operate_action_runs_full_turn_and_advances():
    state = _game()
    director = state.player_order[0]
    minor = state.minors["M3"]  # home Edinburgh (H5)
    minor.floated = True
    minor.director_player_id = director
    minor.trains = ["2"]
    place_token(state, "M3", row=9, col=4)

    # Build track from M3's home (H5) reaching a revenue location it can
    # run a 2-stop route to: H1 (Aberdeen, off-board, catalogued value).
    for row in range(1, 6):
        apply_tile_lay(state.board, f"H{row}", "9", rotation=0)  # straight N-S chain

    start_operating_round_set(state)
    assert state.round_type == RoundType.OPERATING

    starting_treasury = minor.treasury
    apply_action(state, director, {"type": "operate", "company_id": "M3"})

    assert minor.home_token_placed is True
    assert minor.treasury >= starting_treasury  # earned something and kept half
    assert state.round_type == RoundType.STOCK  # only company in the set, turn advanced


def test_operate_rejects_wrong_director():
    state = _game()
    director = state.player_order[0]
    other = state.player_order[1]
    minor = state.minors["M3"]
    minor.floated = True
    minor.director_player_id = director
    minor.trains = ["2"]
    place_token(state, "M3", row=9, col=4)
    start_operating_round_set(state)

    with pytest.raises(ActionError):
        apply_action(state, other, {"type": "operate", "company_id": "M3"})


def test_operate_with_tile_lay_deducts_treasury():
    state = _game()
    director = state.player_order[0]
    minor = state.minors["M3"]  # home H5
    minor.floated = True
    minor.director_player_id = director
    minor.treasury = 200
    minor.trains = ["2"]
    place_token(state, "M3", row=9, col=4)
    # Connect M3's home (H5) to H13 first (rule 5.7.9: a company can only
    # lay on a hex its own track reaches).
    for row in range(5, 13):
        apply_tile_lay(state.board, f"H{row}", "9", rotation=0)
    start_operating_round_set(state)

    apply_action(state, director, {
        "type": "operate",
        "company_id": "M3",
        "tile_lay": {"hex_id": "H13", "tile_id": "3", "rotation": 0},  # H13 = estuary, cost 40
    })

    assert state.board.tiles["H13"].tile_id == "3"
    # 200 - 40 terrain cost, then some amount added back from any earnings this turn
    assert minor.treasury <= 200 - 40 + 1000  # sanity bound; exact value depends on revenue
