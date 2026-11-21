"""Turn order helpers: stock-round player order (4.1.2), operating order
(5.2.1-5.2.2) and next-round player order by cash (4.11.9)."""
from __future__ import annotations

from .models import GameState
from .stock_positions import descending_price_key


def stock_round_order(state: GameState) -> list[str]:
    """Rule 4.1.2: play starts with the holder of the Player 1 card and proceeds
    in player number order. ``state.player_order`` is the card order (index 0 =
    Player 1 card); ``priority_deal_player_id`` is the holder of that card."""
    order = list(state.player_order)
    first = state.priority_deal_player_id
    if first in order:
        i = order.index(first)
        order = order[i:] + order[:i]
    return order


def _sort_key(state: GameState, company_id: str):
    return descending_price_key(state, company_id)


def compute_operating_order(state: GameState) -> list[str]:
    """Rules 5.2.1-5.2.2: floated minors (descending share price), then floated
    majors (descending share price). Equal value: rightmost space first; same
    space: token on top of the stack first (see descending_price_key)."""
    minors = [
        cid for cid, m in state.minors.items()
        if m.floated and not m.removed and m.acquired_by_major is None
        and cid in state.stock_positions
    ]
    majors = [
        abbr for abbr, c in state.majors.items()
        if c.floated and abbr in state.stock_positions
    ]
    minors.sort(key=lambda c: (_sort_key(state, c), c))
    majors.sort(key=lambda c: (_sort_key(state, c), c))
    return minors + majors


def reorder_players_by_cash(state: GameState) -> list[str]:
    """Rule 4.11.9: most cash gets the Player 1 card, and so on; equal cash keeps
    the previous relative order (``state.player_order``). Stable sort."""
    prev = list(state.player_order)
    return sorted(prev, key=lambda pid: -state.players[pid].cash)
