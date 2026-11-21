"""Turn-order helpers: stock round player order (4.1.2), operating order
(5.2.1-5.2.2) and next-round player order by cash (4.11.9)."""
from __future__ import annotations

from .models import GameState
from .stock_positions import descending_price_key

P9_NUMBER = 9  # Midland and Great Northern Joint Railway


def stock_round_order(state: GameState) -> list[str]:
    """Rule 4.1.2: starts with the holder of the Player 1 card and proceeds in
    player number order. ``state.player_order`` is the Player 1..n card order;
    rotated to begin at ``priority_deal_player_id`` if that is set and valid."""
    order = list(state.player_order)
    start = state.priority_deal_player_id
    if start in order:
        i = order.index(start)
        order = order[i:] + order[:i]
    return order


def _sorted_by_price(state: GameState, ids: list[str]) -> list[str]:
    ids = [c for c in ids if c in state.stock_positions]
    return sorted(ids, key=lambda c: descending_price_key(state, c))


def compute_operating_order(state: GameState) -> list[str]:
    """Rules 5.2.1 B/C and 5.2.2: floated minors, then floated majors, each in
    descending share price order; equal value: same space -> token on top
    first, different spaces -> rightmost first."""
    minors = [
        cid for cid, m in state.minors.items()
        if m.floated and not m.removed and m.acquired_by_major is None
    ]
    majors = [abbr for abbr, m in state.majors.items() if m.floated]
    return _sorted_by_price(state, minors) + _sorted_by_price(state, majors)


def _owns_p9(state: GameState, player_id: str) -> bool:
    p9 = state.privates.get(P9_NUMBER)
    player = state.players[player_id]
    if p9 is not None:
        if p9.closed:
            return False
        if p9.owner_company_id is not None:
            return False  # owned by a company: player cannot declare
        if p9.owner_player_id is not None:
            return p9.owner_player_id == player_id
    return P9_NUMBER in player.private_companies


def reorder_players_by_cash(state: GameState) -> list[str]:
    """Rule 4.11.9: most cash first; ties keep their previous relative order.
    Exception P9: its owner counts double cash (assumed always declared)."""
    prev = list(state.player_order)

    def eff(pid: str) -> int:
        cash = state.players[pid].cash
        return cash * 2 if _owns_p9(state, pid) else cash

    return sorted(prev, key=lambda pid: -eff(pid))  # sorted() is stable
