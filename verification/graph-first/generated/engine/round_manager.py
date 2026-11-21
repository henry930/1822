"""Round / turn state machine for stock rounds and operating-round sequencing."""
from __future__ import annotations

from ..data.phases import PHASES_BY_NUMBER
from .bidding import refill_boxes, resolve_stock_round
from .models import GameState, RoundType
from .scoring import pay_concession_dividends
from .turn_order import next_operating_company


class RoundError(Exception):
    pass


def sr_over(state: GameState) -> bool:
    return state.consecutive_passes >= len(state.player_order)


def next_player(state: GameState, pid: str) -> str:
    order = state.player_order
    return order[(order.index(pid) + 1) % len(order)]


def begin_turn(state: GameState, pid: str) -> None:
    if pid not in state.player_order:
        raise RoundError(f"ERR_WRONG_PLAYER: {pid} is not a player in this game")
    state.active_player_id = pid
    state.bids_this_turn = 0


def advance_stock_player(state: GameState) -> None:
    begin_turn(state, next_player(state, state.active_player_id))


def start_stock_round(state: GameState) -> None:
    if state.game_over:
        raise RoundError("ERR_GAME_OVER: the game is over")
    refill_boxes(state)
    state.round_type = RoundType.STOCK
    state.any_sale_this_stock_round = False
    state.sold_this_round = {}
    state.consecutive_passes = 0
    state.priority_deal_player_id = state.player_order[0]
    begin_turn(state, state.player_order[0])


def end_stock_round(state: GameState) -> None:
    if not sr_over(state):
        raise RoundError("ERR_NOT_OVER: the stock round is not over")
    resolve_stock_round(state)
    state.stock_rounds_completed += 1
    if state.game_over:
        return
    start_operating_round(state)


def active_company_id(state: GameState) -> str | None:
    if state.round_type != RoundType.OPERATING:
        return None
    if 0 <= state.current_company_index < len(state.operating_order):
        return state.operating_order[state.current_company_index]
    return None


def start_operating_round(state: GameState) -> None:
    state.round_type = RoundType.OPERATING
    state.operating_round_index = 0
    state.operating_rounds_this_set = PHASES_BY_NUMBER[
        state.phase
    ].operating_rounds_per_stock_round
    if state.end_trigger_pending == "next_or":
        state.end_trigger_pending = "or_set_end"
        state.operating_rounds_this_set = 1
    _begin_operating_round(state)


def _begin_operating_round(state: GameState) -> None:
    pay_concession_dividends(state)
    state.operating_order = []
    state.current_company_index = 0
    first = next_operating_company(state, set())
    if first is None:
        _end_operating_round(state)
    else:
        state.operating_order = [first]


def advance_company(state: GameState) -> None:
    cur = active_company_id(state)
    if cur is not None and cur in state.majors:
        state.majors[cur].has_operated = True
    done = set(state.operating_order[: state.current_company_index + 1])
    nxt = next_operating_company(state, done)
    if nxt is not None:
        state.operating_order = state.operating_order[: state.current_company_index + 1] + [nxt]
        state.current_company_index += 1
    else:
        _end_operating_round(state)


def _end_operating_round(state: GameState) -> None:
    if state.end_trigger_pending == "or_end":
        state.game_over = True
        return
    state.operating_round_index += 1
    if state.operating_round_index < state.operating_rounds_this_set:
        _begin_operating_round(state)
        return
    if state.end_trigger_pending == "or_set_end":
        state.game_over = True
        return
    start_stock_round(state)
