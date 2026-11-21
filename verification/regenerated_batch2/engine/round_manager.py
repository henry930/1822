"""Round sequencing: stock rounds, operating-round sets and game end."""
from __future__ import annotations

import re

from app.data.phases import PHASES_BY_NUMBER
from app.data.private_companies import PRIVATE_COMPANIES

from . import bidding, turn_order
from .models import GameState, RoundType
from .scoring import check_game_end_triggers

CONCESSION_DIVIDEND = 10  # rules 3.4.4
_PRIVATE_BY_NUMBER = {p.number: p for p in PRIVATE_COMPANIES}


# --------------------------------------------------------------- stock round
def start_stock_round(state: GameState) -> None:
    state.round_type = RoundType.STOCK
    state.consecutive_passes = 0
    state.any_sale_this_stock_round = False
    state.active_player_id = state.priority_deal_player_id
    state.bids_this_turn = 0
    state.sold_this_round = {}
    state.operating_order = []
    state.current_company_index = 0


def advance_stock_player(state: GameState) -> None:
    order = turn_order.stock_round_order(state)
    if not order:
        state.active_player_id = None
        return
    if state.active_player_id in order:
        nxt = order[(order.index(state.active_player_id) + 1) % len(order)]
    else:
        nxt = order[0]
    state.active_player_id = nxt
    state.bids_this_turn = 0


def end_stock_round(state: GameState) -> None:
    if state.stock_rounds_completed == 0 and not state.any_sale_this_stock_round:
        state.game_over = True  # rule 10.1.1
        state.log.append("Game over: the first stock round ended with nothing sold.")
        return
    bidding.resolve_stock_round(state)
    state.stock_rounds_completed += 1
    state.player_order = turn_order.reorder_players_by_cash(state)
    state.priority_deal_player_id = state.player_order[0] if state.player_order else None
    check_game_end_triggers(state)  # the resolution may have emptied the bank
    start_operating_round_set(state)


# ------------------------------------------------------------ operating set
def start_operating_round_set(state: GameState) -> None:
    state.round_type = RoundType.OPERATING
    state.active_player_id = None
    state.operating_rounds_this_set = PHASES_BY_NUMBER[state.phase].operating_rounds_per_stock_round
    state.operating_round_index = 0
    if state.end_trigger_pending == "next_or":
        state.operating_rounds_this_set = 1
        state.end_trigger_pending = "or_set_end"
    start_operating_round(state)


def _private_revenue(number: int, phase: int) -> int:
    spec = _PRIVATE_BY_NUMBER.get(number)
    if spec is None:
        return 0
    m = re.match(r"\s*£\s*(\d+)\s*(x\s*phase)?", str(spec.revenue))
    if not m:
        return 0
    amount = int(m.group(1))
    return amount * phase if m.group(2) else amount


def _pay_step_a(state: GameState) -> None:
    """Rule 5.2.1 A (3.1.2, 3.4.4): the bank pays privates and concessions."""
    for number, pc in sorted(state.privates.items()):
        if pc.closed:
            continue
        rev = _private_revenue(number, state.phase)
        if rev <= 0:
            continue
        if pc.owner_company_id is not None:
            cid = pc.owner_company_id
            holder = state.minors.get(cid) or state.majors.get(cid)
            if holder is None:
                continue
            holder.treasury += rev
        elif pc.owner_player_id is not None and pc.owner_player_id in state.players:
            state.players[pc.owner_player_id].cash += rev
        else:
            continue
        state.bank.cash -= rev
    for player in state.players.values():
        n = len(player.concessions)
        if n:
            player.cash += CONCESSION_DIVIDEND * n
            state.bank.cash -= CONCESSION_DIVIDEND * n


def start_operating_round(state: GameState) -> None:
    state.round_type = RoundType.OPERATING
    _pay_step_a(state)
    check_game_end_triggers(state)
    state.operating_order = turn_order.compute_operating_order(state)
    state.current_company_index = 0
    _skip_invalid(state)
    if state.current_company_index >= len(state.operating_order):
        _end_of_operating_round(state)


def _still_operating(state: GameState, cid: str) -> bool:
    m = state.minors.get(cid)
    if m is not None:
        return m.floated and not m.removed and m.acquired_by_major is None
    c = state.majors.get(cid)
    return c is not None and c.floated


def _skip_invalid(state: GameState) -> None:
    """Skip companies that vanished from play after the order was fixed
    (e.g. a minor acquired by a major earlier in the same round)."""
    while (state.current_company_index < len(state.operating_order)
           and not _still_operating(state, state.operating_order[state.current_company_index])):
        state.current_company_index += 1


def advance_company(state: GameState) -> None:
    if state.game_over or state.round_type != RoundType.OPERATING:
        return
    state.current_company_index += 1
    _skip_invalid(state)
    if state.current_company_index >= len(state.operating_order):
        _end_of_operating_round(state)


def _game_ends(state: GameState, why: str) -> None:
    state.game_over = True
    state.log.append(f"Game over: {why}")


def _end_of_operating_round(state: GameState) -> None:
    check_game_end_triggers(state)
    pending = state.end_trigger_pending
    if pending == "or_end":
        _game_ends(state, "game end value reached; final operating round complete.")
        return
    state.operating_round_index += 1
    if state.operating_round_index < state.operating_rounds_this_set:
        start_operating_round(state)
        return
    if pending == "or_set_end":
        _game_ends(state, "end trigger reached; final operating round set complete.")
        return
    start_stock_round(state)


def active_company_id(state: GameState) -> str | None:
    if state.game_over or state.round_type != RoundType.OPERATING:
        return None
    i = state.current_company_index
    if 0 <= i < len(state.operating_order):
        return state.operating_order[i]
    return None
