"""Round/turn advancement: stock round <-> operating round set transitions
(rule 2.1, 4.1, 5.1-5.2), independent of what any individual action does.
"""
from __future__ import annotations

from app.data.phases import PHASES_BY_NUMBER

from .models import GameState, RoundType
from .turn_order import compute_operating_order, next_priority_deal_player


def start_stock_round(state: GameState) -> None:
    state.round_type = RoundType.STOCK
    state.consecutive_passes = 0
    state.any_sale_this_stock_round = False
    state.active_player_id = state.priority_deal_player_id


def advance_stock_player(state: GameState) -> None:
    order = state.player_order
    idx = order.index(state.active_player_id)
    state.active_player_id = order[(idx + 1) % len(order)]


def end_stock_round(state: GameState) -> None:
    """Rule 10.1.1: if the very first stock round ends with nothing sold,
    the game ends immediately - checked before anything else changes."""
    if state.stock_rounds_completed == 0 and not state.any_sale_this_stock_round:
        state.game_over = True
        state.log.append("Game over: first stock round ended with nothing sold (rule 10.1.1).")
        return

    state.stock_rounds_completed += 1
    state.priority_deal_player_id = next_priority_deal_player(state)
    start_operating_round_set(state)


def start_operating_round_set(state: GameState) -> None:
    """Locks in operating_rounds_this_set from the *current* phase - this is
    what makes rule 2.1.2's deferred OR-count increase work automatically:
    a phase change mid-OR-set doesn't retroactively affect the set already
    running, because the count was already locked when that set started."""
    phase = PHASES_BY_NUMBER[state.phase]
    state.round_type = RoundType.OPERATING
    state.operating_rounds_this_set = phase.operating_rounds_per_stock_round
    state.operating_round_index = 0
    start_operating_round(state)


def start_operating_round(state: GameState) -> None:
    """(Re-)computes company turn order for a single OR within the current
    set - recomputed each OR since share prices (and hence order) can move
    between ORs in the same set."""
    state.operating_order = compute_operating_order(state)
    state.current_company_index = 0


def advance_company(state: GameState) -> None:
    """Called when the active company's turn is finished."""
    state.current_company_index += 1
    if state.current_company_index >= len(state.operating_order):
        _advance_operating_round_set(state)


def _advance_operating_round_set(state: GameState) -> None:
    state.operating_round_index += 1
    if state.operating_round_index >= state.operating_rounds_this_set:
        start_stock_round(state)
    else:
        start_operating_round(state)


def active_company_id(state: GameState) -> str | None:
    if state.round_type != RoundType.OPERATING:
        return None
    if state.current_company_index >= len(state.operating_order):
        return None
    return state.operating_order[state.current_company_index]
