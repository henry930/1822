"""Turn-order computation for stock rounds (rule 4.1.2) and operating
rounds (rule 5.2).
"""
from __future__ import annotations

from .models import GameState, RoundType
from .stock_positions import descending_price_key


def stock_round_order(state: GameState) -> list[str]:
    """Rule 4.1.2: SR starts with the priority deal player, then proceeds in
    player_order (wrapping around)."""
    order = state.player_order
    if state.priority_deal_player_id not in order:
        return list(order)
    start = order.index(state.priority_deal_player_id)
    return order[start:] + order[:start]


def compute_operating_order(state: GameState) -> list[str]:
    """Rule 5.2.1: floated minor companies in descending share price order,
    then floated major companies in descending share price order."""
    minors = [
        m.company_id for m in state.minors.values()
        if m.floated and not m.removed and m.company_id in state.stock_positions
    ]
    majors = [
        a.abbr for a in state.majors.values()
        if a.floated and a.abbr in state.stock_positions
    ]
    minors.sort(key=lambda cid: descending_price_key(state, cid))
    majors.sort(key=lambda cid: descending_price_key(state, cid))
    return minors + majors


def reorder_players_by_cash(state: GameState) -> list[str]:
    """Rule 4.11.9: the next SR's whole turn order is reassigned by cash,
    most to least; ties keep their relative order from the previous round."""
    prev_order = state.player_order

    def cash_key(pid: str):
        idx = prev_order.index(pid) if pid in prev_order else len(prev_order)
        return (-state.players[pid].cash, idx)

    return sorted(state.players.keys(), key=cash_key)
