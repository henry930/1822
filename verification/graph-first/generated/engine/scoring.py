"""Game-end triggers, concession dividends and player wealth (comp.sr_flow part)."""
from __future__ import annotations

from .certificates import units_held
from .models import GameState, RoundType
from .turn_order import current_price, is_game_end_cell, token_cell

CONCESSION_DIVIDEND = 10
CONCESSION_VALUE = 100


def bank_broken(state: GameState) -> bool:
    return state.bank.cash < 0


def check_game_end_triggers(state: GameState, context: str | None = None) -> None:
    # 10.1.2: the first trigger stands.
    if state.game_over or state.end_trigger_pending is not None:
        return
    in_or = state.round_type == RoundType.OPERATING
    if bank_broken(state):
        state.end_trigger_pending = "or_set_end" if in_or else "next_or"
        return
    if any(is_game_end_cell(state, c) for c in list(state.stock_positions)):
        state.end_trigger_pending = "or_end" if in_or else "next_or"
        return
    if (
        context == "end_of_stock_round"
        and state.stock_rounds_completed == 0
        and not state.any_sale_this_stock_round
    ):
        state.game_over = True


def pay_concession_dividends(state: GameState) -> None:
    if state.phase >= 5:
        return
    for player in state.players.values():
        n = len(player.concessions)
        if n:
            amount = CONCESSION_DIVIDEND * n
            player.cash += amount
            state.bank.cash -= amount
    check_game_end_triggers(state, "after_bank_payment")


def player_wealth(state: GameState, pid: str) -> int:
    player = state.players[pid]
    total = player.cash - player.loans + CONCESSION_VALUE * len(player.concessions)
    for cid in state.majors:
        if token_cell(state, cid) is None:
            continue
        units = units_held(state, pid, cid)
        if units:
            total += units * current_price(state, cid)
    return total
