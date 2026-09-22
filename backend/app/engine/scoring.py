"""Game-end trigger detection and final wealth calculation (rule 10).

Rule 10.1.1's five conditions:
  - first SR ends with nothing sold -> immediate (handled directly in
    app.engine.round_manager.end_stock_round, not here)
  - a company's stock token reaches the game-end (£700) value during an OR
    -> ends at the end of *that* operating round
  - ... during a SR -> ends after the *next* operating round
  - the bank runs out of money during an OR -> ends after the *current set*
    of operating rounds
  - ... during a SR -> ends after the *next* operating round

check_game_end_triggers should be called after anything that could cross
one of these thresholds (a stock price move, or a cash payment out of the
bank) - see its call sites in app.engine.operating and app.engine.trains.
Once one trigger fires, later ones don't override it (rule 10.1.2: the
game ends at the first indicated time).
"""
from __future__ import annotations

from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .models import GameState, RoundType


def check_game_end_triggers(state: GameState) -> None:
    if state.end_trigger_pending is not None or state.game_over:
        return  # first trigger wins, rule 10.1.2

    stock_at_game_end = any(
        pos in STOCK_MARKET_BY_POSITION and STOCK_MARKET_BY_POSITION[pos].game_end
        for pos in state.stock_positions.values()
    )
    bank_empty = state.bank.cash <= 0

    if stock_at_game_end:
        state.end_trigger_pending = "or_end" if state.round_type == RoundType.OPERATING else "next_or"
        state.log.append("Game-end triggered: a company's share price reached £700 (rule 10.1.1).")
    elif bank_empty:
        state.end_trigger_pending = "or_set_end" if state.round_type == RoundType.OPERATING else "next_or"
        state.log.append("Game-end triggered: the bank has run out of money (rule 10.1.1).")


def final_wealth(state: GameState, player_id: str) -> int:
    """Rule 10.1.3: stock value at current prices, plus cash, minus
    outstanding loans. Concessions still held count at face value (£100);
    private companies and company assets count for nothing."""
    player = state.players[player_id]
    total = player.cash - player.loans
    total += 100 * len(player.concessions)

    for company_id, units in player.shares.items():
        pos = state.stock_positions.get(company_id)
        if pos is None:
            continue
        cell = STOCK_MARKET_BY_POSITION.get(pos)
        if cell is None:
            continue
        if company_id in state.minors:
            # a minor's director's certificate (1 "unit" here) represents
            # the whole 50% block, valued at 2x the market price.
            total += cell.value * 2 * units
        else:
            total += cell.value * units

    return total


def final_standings(state: GameState) -> list[tuple[str, int]]:
    """Players ranked richest first (rule 10.1.3: the richest player wins)."""
    scores = [(pid, final_wealth(state, pid)) for pid in state.players]
    scores.sort(key=lambda t: -t[1])
    return scores
