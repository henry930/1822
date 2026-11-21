"""Game-end triggers (rules 10.1.1-10.1.2) and final scoring (10.1.3)."""
from __future__ import annotations

from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .models import GameState, RoundType

CONCESSION_FACE_VALUE = 100  # rule 3.4.2


def _any_token_on_game_end_cell(state: GameState) -> bool:
    for pos in state.stock_positions.values():
        cell = STOCK_MARKET_BY_POSITION.get(pos)
        if cell is not None and cell.game_end:
            return True
    return False


def check_game_end_triggers(state: GameState) -> None:
    """Rules 10.1.1/10.1.2: record the first end trigger; later ones are ignored.

    Pending values: "or_end" (price token on a game-end cell during an OR),
    "or_set_end" (bank broken during an OR) and "next_or" (either condition
    reached during a stock round; round_manager turns it into a one-OR set).
    """
    if state.game_over or state.end_trigger_pending is not None:
        return
    token_end = _any_token_on_game_end_cell(state)
    bank_broken = state.bank.cash <= 0
    if not (token_end or bank_broken):
        return
    if state.round_type == RoundType.OPERATING:
        # token trigger takes precedence only if both happen simultaneously:
        # it ends the game sooner (end of this OR).
        state.end_trigger_pending = "or_end" if token_end else "or_set_end"
    else:
        state.end_trigger_pending = "next_or"
    state.log.append(f"Game end triggered ({state.end_trigger_pending}).")


def _share_value(state: GameState, company_id: str, units: int) -> int:
    if units <= 0:
        return 0
    pos = state.stock_positions.get(company_id)
    if pos is None:
        return 0
    cell = STOCK_MARKET_BY_POSITION.get(pos)
    if cell is None:
        return 0
    price = cell.value
    minor = state.minors.get(company_id)
    if minor is not None:
        if minor.removed or minor.acquired_by_major is not None:
            return 0
        # the director's certificate is the whole 50% block: twice the price
        return 2 * price * units
    return units * price


def final_wealth(state: GameState, player_id: str) -> int:
    """Rule 10.1.3: cash + stock at current prices + open concessions at face - loans."""
    p = state.players[player_id]
    total = p.cash - p.loans
    for cid, units in p.shares.items():
        total += _share_value(state, cid, units)
    total += CONCESSION_FACE_VALUE * len(p.concessions)
    return total


def final_standings(state: GameState) -> list[tuple[str, int]]:
    """Richest first; ties keep player_order."""
    order = list(state.player_order) or list(state.players)
    rows = [(pid, final_wealth(state, pid)) for pid in order]
    return sorted(rows, key=lambda r: -r[1])
