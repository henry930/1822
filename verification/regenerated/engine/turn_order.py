"""Player and company ordering (rules 4.1.2, 4.11.9, 5.2.1-5.2.2)."""
from __future__ import annotations

from .models import GameState
from .stock_positions import descending_price_key


def stock_round_order(state: GameState) -> list[str]:
    """Rule 4.1.2: start with the Player 1 card holder, then player number order."""
    order = list(state.player_order)
    start = state.priority_deal_player_id
    if start in order:
        i = order.index(start)
        order = order[i:] + order[:i]
    return order


def compute_operating_order(state: GameState) -> list[str]:
    """Rules 5.2.1-5.2.2: floated minors, then floated majors, each by descending price.

    Ties: same cell -> token on top first; same value in different cells -> rightmost first.
    """
    minors = [
        cid for cid, m in state.minors.items()
        if m.floated and not m.removed and m.acquired_by_major is None and cid in state.stock_positions
    ]
    majors = [
        cid for cid, m in state.majors.items()
        if m.floated and cid in state.stock_positions
    ]
    key = lambda cid: descending_price_key(state, cid)
    return sorted(minors, key=key) + sorted(majors, key=key)


def reorder_players_by_cash(state: GameState) -> list[str]:
    """Rule 4.11.9: most cash first; ties keep their previous relative order."""
    previous = list(state.player_order)
    return sorted(previous, key=lambda pid: -state.players[pid].cash)  # sorted() is stable
