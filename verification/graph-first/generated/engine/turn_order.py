"""Market component (stock market tokens, orders) of the 1822 engine. Layer 1."""
from __future__ import annotations

from typing import Iterable

from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .models import GameState
from .stock_positions import descending_price_key, place_token


class MarketError(Exception):
    """Message format: "<ERR_CODE>: <text>"."""


# ---------------------------------------------------------------------------
# Constants derived from the data table at import time.
# ---------------------------------------------------------------------------
_YELLOW_CELLS: frozenset[tuple[int, int]] = frozenset(
    pos for pos, c in STOCK_MARKET_BY_POSITION.items() if c.zone == "yellow"
)
_GAME_END_CELLS: frozenset[tuple[int, int]] = frozenset(
    pos for pos, c in STOCK_MARKET_BY_POSITION.items() if c.game_end
)
_START_CELLS: dict[int, tuple[int, int]] = {
    c.value: pos
    for pos, c in STOCK_MARKET_BY_POSITION.items()
    if c.zone in ("start", "minor_start")
}
_MINOR_ONLY_PRICES: frozenset[int] = frozenset(
    c.value for c in STOCK_MARKET_BY_POSITION.values() if c.zone == "minor_start"
)


# ---------------------------------------------------------------------------
# Derived functions
# ---------------------------------------------------------------------------
def token_cell(state: GameState, cid: str) -> tuple[int, int] | None:
    pos = state.stock_positions.get(cid)
    return tuple(pos) if pos is not None else None  # type: ignore[return-value]


def _require_cell(state: GameState, cid: str) -> tuple[int, int]:
    cell = token_cell(state, cid)
    if cell is None:
        raise MarketError(f"ERR_NO_TOKEN: company {cid} has no token on the stock market")
    return cell


def current_price(state: GameState, cid: str) -> int:
    cell = _require_cell(state, cid)
    return STOCK_MARKET_BY_POSITION[cell].value


def in_yellow(state: GameState, cid: str) -> bool:
    cell = token_cell(state, cid)
    return cell is not None and cell in _YELLOW_CELLS


def is_game_end_cell(state: GameState, cid: str) -> bool:
    cell = token_cell(state, cid)
    return cell is not None and cell in _GAME_END_CELLS


def start_cell(price: int, kind: str = "major") -> tuple[int, int]:
    if kind not in ("major", "minor"):
        raise MarketError(f"ERR_BAD_START_PRICE: unknown company kind {kind!r}")
    if isinstance(price, bool) or not isinstance(price, int) or price not in _START_CELLS:
        raise MarketError(f"ERR_BAD_START_PRICE: {price} is not a start price")
    if kind == "major" and price in _MINOR_ONLY_PRICES:
        raise MarketError(f"ERR_BAD_START_PRICE: {price} is a start price for minor companies only")
    return _START_CELLS[price]


def descending_order(state: GameState, company_ids: Iterable[str]) -> list[str]:
    ids = list(company_ids)
    for c in ids:
        _require_cell(state, c)
    return sorted(ids, key=lambda c: descending_price_key(state, c))


def operating_order(state: GameState) -> list[str]:
    minors = [
        k for k, m in state.minors.items()
        if m.director_player_id is not None and k in state.stock_positions
    ]
    majors = [
        k for k, m in state.majors.items()
        if m.floated and k in state.stock_positions
    ]
    return descending_order(state, minors) + descending_order(state, majors)


def next_operating_company(state: GameState, done: Iterable[str]) -> str | None:
    done_set = set(done)
    for cid in operating_order(state):
        if cid not in done_set:
            return cid
    return None


def compute_stock_round_order(cash: dict[str, int], previous_order: list[str]) -> list[str]:
    return sorted(previous_order, key=lambda p: -cash[p])


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
def place_start_token(state: GameState, cid: str, price: int, kind: str) -> None:
    cell = start_cell(price, kind)  # validates everything before mutation
    if kind == "major":
        place_token(state, cid, cell[0], cell[1])
        return
    # minor: above every major token, below the existing leading run of minors
    old = state.stock_positions.get(cid)
    if old is not None:
        old_pile = state.stock_stack.get(old)
        if old_pile and cid in old_pile:
            old_pile.remove(cid)
    pile = state.stock_stack.setdefault(cell, [])
    index = 0
    while index < len(pile) and pile[index] in state.minors:
        index += 1
    pile.insert(index, cid)
    state.stock_positions[cid] = cell


def move_token_down(state: GameState, cid: str, steps: int) -> None:
    row, col = _require_cell(state, cid)
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 0:
        raise MarketError(f"ERR_BAD_STEPS: steps must be a non-negative integer, got {steps!r}")
    new_row = row
    for _ in range(steps):
        if (new_row + 1, col) in STOCK_MARKET_BY_POSITION:
            new_row += 1
        else:
            break
    if new_row != row:
        place_token(state, cid, new_row, col)


def move_token_up(state: GameState, cid: str) -> None:
    row, col = _require_cell(state, cid)
    if (row - 1, col) not in STOCK_MARKET_BY_POSITION:
        return
    place_token(state, cid, row - 1, col)
    if is_game_end_cell(state, cid):
        from .scoring import check_game_end_triggers

        check_game_end_triggers(state, "after_token_move")


def raise_sold_out_prices(state: GameState) -> None:
    from .certificates import fully_sold

    affected = [
        c for c, m in state.majors.items()
        if m.floated and c in state.stock_positions and fully_sold(state, c)
    ]
    order = descending_order(state, affected)
    for c in order:
        move_token_up(state, c)


def reorder_players_by_cash(state: GameState) -> None:
    cash = {pid: p.cash for pid, p in state.players.items()}
    state.player_order = compute_stock_round_order(cash, list(state.player_order))
    state.priority_deal_player_id = state.player_order[0]
