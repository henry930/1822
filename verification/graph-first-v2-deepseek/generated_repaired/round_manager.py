"""Round manager: stock and operating round sequencing, turn advancement,
game-end trigger maturity.

Module layer: 7 (top). Imports lower layers (1-6) at module level as allowed.
"""
from __future__ import annotations

from typing import Iterable

from app.data.phases import PHASES_BY_NUMBER
from app.engine.models import GameState, RoundType

# ------------------------------------------------------------------ constants
ERR_WRONG_PLAYER = "ERR_WRONG_PLAYER"
ERR_GAME_OVER = "ERR_GAME_OVER"
ERR_NO_ACTIVE_COMPANY = "ERR_NO_ACTIVE_COMPANY"

# ------------------------------------------------------------------ exception
class RoundError(Exception):
    """Single exception class for this module."""
    def __init__(self, code: str, text: str):
        self.code = code
        super().__init__(f"{code}: {text}")

# ------------------------------------------------------------------ helpers
def _get_player_index(state: GameState, player_id: str) -> int:
    try:
        return state.player_order.index(player_id)
    except ValueError:
        raise RoundError(ERR_WRONG_PLAYER, f"Player {player_id} not in player order")

def _set_turn(state: GameState, player_id: str) -> None:
    state.active_player_id = player_id
    state.bids_this_turn = 0

# ------------------------------------------------------------------ public API

def sr_over(state: GameState) -> bool:
    """Check if the stock round is over (all players passed consecutively)."""
    return state.consecutive_passes >= len(state.player_order)


def next_player(state: GameState, player_id: str) -> str:
    """Return the next player in cyclic stock-turn order."""
    idx = _get_player_index(state, player_id)
    n = len(state.player_order)
    nxt = state.player_order[(idx + 1) % n]
    return nxt


def begin_turn(state: GameState, player_id: str) -> None:
    """Begin a player's stock turn: set active player and reset bid counter."""
    _get_player_index(state, player_id)  # validate player exists
    _set_turn(state, player_id)


def start_stock_round(state: GameState) -> None:
    """Start a stock round (round 2+ and debug). Not for round 1 (already in progress)."""
    if state.game_over:
        raise RoundError(ERR_GAME_OVER, "Game is over, cannot start stock round")

    # lazy imports for lower layers
    from app.engine.bidding import refill_boxes

    refill_boxes(state)
    state.round_type = RoundType.STOCK
    state.any_sale_this_stock_round = False
    state.sold_this_round = {}
    state.consecutive_passes = 0
    # priority deal player must equal player_order[0]
    state.priority_deal_player_id = state.player_order[0]
    begin_turn(state, state.player_order[0])


def advance_stock_player(state: GameState) -> None:
    """End the current stock turn and hand over to the next player."""
    current = state.active_player_id
    nxt = next_player(state, current)
    begin_turn(state, nxt)


end_turn = advance_stock_player  # alias


def end_stock_round(state: GameState) -> None:
    """End the stock round: resolve, count, start OR set unless game over."""
    if state.game_over:
        raise RoundError(ERR_GAME_OVER, "Game is over, cannot end stock round")

    from app.engine.bidding import resolve_stock_round

    phase_before = state.phase
    resolve_stock_round(state)
    state.stock_rounds_completed += 1
    if state.game_over:
        return  # immediate game end, no OR set starts
    start_operating_round(state, phase_before)


def active_company_id(state: GameState) -> str | None:
    """Return the company currently operating, or None."""
    if state.round_type != RoundType.OPERATING:
        return None
    if 0 <= state.current_company_index < len(state.operating_order):
        return state.operating_order[state.current_company_index]
    return None


active_company = active_company_id  # alias


def advance_company(state: GameState) -> None:
    """Finish a company's turn and choose the next one, or end the operating round."""
    current = active_company_id(state)
    if current is None:
        raise RoundError(ERR_NO_ACTIVE_COMPANY, "No company is currently operating")

    # mark major as having completed an OR (rule 4.4.2)
    if current in state.majors:
        state.majors[current].has_operated = True

    done = list(state.operating_order[: state.current_company_index + 1])
    from app.engine.turn_order import next_operating_company
    nxt = next_operating_company(state, done)
    if nxt is None:
        end_operating_round(state)
    else:
        state.operating_order.append(nxt)
        state.current_company_index += 1


def start_operating_round(state: GameState, phase_before: int | None = None) -> None:
    """Start the set of operating rounds following a stock round."""
    if state.game_over:
        raise RoundError(ERR_GAME_OVER, "Game is over, cannot start operating round")

    state.round_type = RoundType.OPERATING
    state.operating_round_index = 0
    state.operating_rounds_this_set = operating_rounds_for_next_set(state, phase_before)

    # handle next_or trigger: force 1 OR and convert to or_set_end
    if state.end_trigger_pending == "next_or":
        state.end_trigger_pending = "or_set_end"
        state.operating_rounds_this_set = 1

    begin_operating_round(state)


def begin_operating_round(state: GameState) -> None:
    """Begin one operating round: pay privates/concessions, choose first company."""
    from app.engine.scoring import pay_private_revenues, pay_concession_dividends
    from app.engine.turn_order import next_operating_company

    pay_private_revenues(state)
    pay_concession_dividends(state)

    state.operating_order = []
    state.current_company_index = 0

    first = next_operating_company(state, [])
    if first is None:
        end_operating_round(state)
    else:
        state.operating_order = [first]


start_operating_set_round = begin_operating_round  # alias


def end_operating_round(state: GameState) -> None:
    """End an operating round: possibly end the game, go to next OR, or to stock round."""
    # check triggers that mature at OR end
    if state.end_trigger_pending == "or_end":
        state.game_over = True
        return
    if state.end_trigger_pending == "next_or":
        # next_or matures at the end of an OR (should have been converted, but handle anyway)
        state.game_over = True
        return

    state.operating_round_index += 1
    if state.operating_round_index < state.operating_rounds_this_set:
        begin_operating_round(state)
        return

    # set complete
    if state.end_trigger_pending == "or_set_end":
        state.game_over = True
        return

    # otherwise go to next stock round
    start_stock_round(state)


def operating_rounds_for_next_set(state: GameState, phase_before: int | None = None) -> int:
    """Determine number of operating rounds in the upcoming set (1 or 2)."""
    if state.end_trigger_pending == "next_or":
        return 1
    p = state.phase if phase_before is None else phase_before
    phase_data = PHASES_BY_NUMBER.get(p)
    if phase_data is None:
        return 1  # fallback
    return phase_data.operating_rounds_per_stock_round

# --- eval name adapter ---
start_operating_round_set = start_operating_round
