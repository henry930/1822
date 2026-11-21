"""Round manager (layer 7): stock-round turns, operating-round sets, game-end maturity.

Implements contract/round_manager.md.  Lower layers (turn_order, scoring) and
bidding are imported lazily inside the functions so the module imports even
while sibling modules are missing.
"""
from __future__ import annotations

from app.data.phases import PHASES_BY_NUMBER

from .models import GameState, RoundType


class RoundError(Exception):
    """Single exception class of the round manager: '<ERR_CODE>: <text>'."""

    def __init__(self, code: str, text: str = ""):
        super().__init__(f"{code}: {text}" if text else code)
        self.code = code


# ---------------------------------------------------------------------------
# Stock round
# ---------------------------------------------------------------------------

def sr_over(state: GameState) -> bool:
    """[4.11.1] True when every player passed consecutively."""
    return state.consecutive_passes >= len(state.player_order)


def next_player(state: GameState, player_id: str) -> str:
    """[4.1.2] Next player in the cyclic stock-turn order."""
    order = state.player_order
    if player_id not in order:
        raise RoundError("ERR_WRONG_PLAYER", f"{player_id!r} is not a player of this game")
    return order[(order.index(player_id) + 1) % len(order)]


def begin_turn(state: GameState, player_id: str) -> None:
    """[4.1.3] Make player_id active and reset the per-turn bid counter."""
    if player_id not in state.player_order:
        raise RoundError("ERR_WRONG_PLAYER", f"{player_id!r} is not a player of this game")
    state.active_player_id = player_id
    state.bids_this_turn = 0


def start_stock_round(state: GameState) -> None:
    """Begin a stock round (round 2 onwards, and debug)."""
    if state.game_over:
        raise RoundError("ERR_GAME_OVER", "the game is over")
    if not state.player_order:
        # begin_turn(sr_order[0]) cannot work: refuse before any mutation
        raise RoundError("ERR_WRONG_PLAYER", "no players in the stock-turn order")
    from . import bidding  # lazy: higher layer than most modules

    bidding.refill_boxes(state)
    state.round_type = RoundType.STOCK
    state.any_sale_this_stock_round = False
    state.sold_this_round = {}
    state.consecutive_passes = 0
    state.priority_deal_player_id = state.player_order[0]
    begin_turn(state, state.player_order[0])


def advance_stock_player(state: GameState) -> None:
    """[4.1.2] Hand the stock turn to the next player (does not touch consecutive_passes)."""
    current = state.active_player_id
    if current in state.player_order:
        nxt = next_player(state, current)
    elif state.player_order:
        # defensive: no valid active player; fall back to the priority player
        nxt = state.player_order[0]
    else:
        return
    begin_turn(state, nxt)


end_turn = advance_stock_player


def end_stock_round(state: GameState) -> None:
    """Resolve the stock round, count it, then start the operating-round set."""
    if state.game_over:
        raise RoundError("ERR_GAME_OVER", "the game is over")
    from . import bidding  # lazy

    phase_before = state.phase
    bidding.resolve_stock_round(state)
    state.stock_rounds_completed += 1
    if state.game_over:
        return
    start_operating_round(state, phase_before)


# ---------------------------------------------------------------------------
# Operating rounds
# ---------------------------------------------------------------------------

def active_company_id(state: GameState) -> str | None:
    """[5.2.2] operating_order[current_company_index] while in an operating round."""
    if state.round_type != RoundType.OPERATING:
        return None
    idx = state.current_company_index
    if 0 <= idx < len(state.operating_order):
        return state.operating_order[idx]
    return None


active_company = active_company_id


def operating_rounds_for_next_set(state: GameState, phase_before: int | None = None) -> int:
    """[5.1.1, 2.1.2] size of the next operating-round set."""
    if state.end_trigger_pending == "next_or":
        return 1
    phase = state.phase if phase_before is None else phase_before
    ph = PHASES_BY_NUMBER.get(phase)
    if ph is None:
        ph = PHASES_BY_NUMBER[state.phase]
    return ph.operating_rounds_per_stock_round


def start_operating_round(state: GameState, phase_before: int | None = None) -> None:
    """Start the set of operating rounds following a stock round."""
    if state.game_over:
        raise RoundError("ERR_GAME_OVER", "the game is over")
    state.round_type = RoundType.OPERATING
    state.operating_round_index = 0
    state.operating_rounds_this_set = operating_rounds_for_next_set(state, phase_before)
    if state.end_trigger_pending == "next_or":
        state.end_trigger_pending = "or_set_end"
        state.operating_rounds_this_set = 1
    begin_operating_round(state)


def begin_operating_round(state: GameState) -> None:
    """[5.2.1] Step A payments, then choose the first company (or end the round)."""
    from . import scoring, turn_order  # lazy

    scoring.pay_private_revenues(state)
    scoring.pay_concession_dividends(state)
    state.operating_order = []
    state.current_company_index = 0
    first = turn_order.next_operating_company(state, ())
    if first is None:
        end_operating_round(state)
    else:
        state.operating_order = [first]


start_operating_set_round = begin_operating_round


def advance_company(state: GameState) -> None:
    """Finish the active company's turn and choose the next one."""
    cid = active_company_id(state)
    if cid is None:
        raise RoundError("ERR_NO_ACTIVE_COMPANY", "no company is operating")
    from . import turn_order  # lazy

    idx = state.current_company_index
    if cid in state.majors:
        state.majors[cid].has_operated = True
    done = list(state.operating_order[: idx + 1])
    nxt = turn_order.next_operating_company(state, done)
    if nxt is not None:
        state.operating_order = done + [nxt]
        state.current_company_index = idx + 1
    else:
        end_operating_round(state)


def end_operating_round(state: GameState) -> None:
    """[10.1.1] Game end, next operating round of the set, or next stock round."""
    if state.end_trigger_pending in ("or_end", "next_or"):
        state.game_over = True
        return
    state.operating_round_index += 1
    if state.operating_round_index < state.operating_rounds_this_set:
        begin_operating_round(state)
        return
    if state.end_trigger_pending == "or_set_end":
        state.game_over = True
        return
    start_stock_round(state)
