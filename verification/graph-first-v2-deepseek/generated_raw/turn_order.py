"""
Turn order, stock market, and player order module for 1822 rules engine.
Layer 1 – may be imported by all higher layers; upward calls are lazy.
"""
from __future__ import annotations

import itertools
from typing import Iterable

from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .models import GameState
from .stock_positions import descending_price_key, place_token


class MarketError(Exception):
    """Single exception class for turn_order module."""

    def __init__(self, code: str, text: str):
        self.code = code
        super().__init__(f"{code}: {text}")


def token_cell(state: GameState, company_id: str) -> tuple[int, int] | None:
    """Return (row, col) of company's token, or None if no token placed."""
    return state.stock_positions.get(company_id)


market_cell = token_cell


def current_price(state: GameState, company_id: str) -> int:
    """Share price of a company, raising MarketError if no token."""
    pos = token_cell(state, company_id)
    if pos is None:
        raise MarketError("ERR_NO_TOKEN", f"Company {company_id} has no token on the market")
    row, col = pos
    return STOCK_MARKET_BY_POSITION[(row, col)].value


share_price = current_price


def in_yellow(state: GameState, company_id: str) -> bool:
    """True if company's token is on a yellow cell. False if no token."""
    pos = token_cell(state, company_id)
    if pos is None:
        return False
    cell = STOCK_MARKET_BY_POSITION[pos]
    return cell.zone == "yellow"


def is_game_end_cell(state: GameState, company_id: str) -> bool:
    """True if company's token sits on a game-end cell. False if no token."""
    pos = token_cell(state, company_id)
    if pos is None:
        return False
    cell = STOCK_MARKET_BY_POSITION[pos]
    return cell.game_end


# ---------------------------------------------------------------------------
# Build start cells mapping at module level (static data)
_start_cells: dict[int, tuple[int, int]] = {}
for cell in STOCK_MARKET_BY_POSITION.values():
    if cell.zone in ("start", "minor_start"):
        _start_cells[cell.value] = (cell.row, cell.col)
_major_start_values = [60, 70, 80, 90, 100]
_minor_start_values = [50, 60, 70, 80, 90, 100]


def start_cell(price: int, kind: str = "major") -> tuple[int, int]:
    """Return (row, col) for a given start price and kind.

    Raises MarketError for invalid kind or price.
    """
    if kind not in ("major", "minor"):
        raise MarketError("ERR_BAD_KIND", f"kind must be 'major' or 'minor', got {kind!r}")
    valid = _major_start_values if kind == "major" else _minor_start_values
    if price not in valid:
        raise MarketError(
            "ERR_BAD_START_PRICE",
            f"Price {price} not valid for {kind}. Valid: {valid}",
        )
    return _start_cells[price]


def place_start_token(state: GameState, company_id: str, price: int, kind: str = "major") -> None:
    """Place a company token on the start cell for the given price.

    For majors: token goes to the bottom of the cell's pile.
    For minors: token is inserted directly after the leading run of minor tokens.
    """
    if kind not in ("major", "minor"):
        raise MarketError("ERR_BAD_KIND", f"kind must be 'major' or 'minor', got {kind!r}")
    valid = _major_start_values if kind == "major" else _minor_start_values
    if price not in valid:
        raise MarketError(
            "ERR_BAD_START_PRICE",
            f"Price {price} not valid for {kind}. Valid: {valid}",
        )
    cell = start_cell(price, kind)
    if kind == "major":
        # Major goes to the bottom of the pile (append via place_token)
        place_token(state, company_id, cell[0], cell[1])
    else:
        # Minor: insert after leading run of minor tokens
        row, col = cell
        # Remove from old position if any
        old_pos = state.stock_positions.get(company_id)
        if old_pos is not None:
            old_pile = state.stock_stack.get(old_pos)
            if old_pile and company_id in old_pile:
                old_pile.remove(company_id)
            # Remove empty piles (optional, but safe)
            if old_pile and not old_pile:
                del state.stock_stack[old_pos]

        # Set new position
        state.stock_positions[company_id] = (row, col)
        pile = state.stock_stack.setdefault((row, col), [])
        # Count leading minors (ids starting with 'M')
        count_leading = 0
        for cid in pile:
            if cid.startswith('M'):
                count_leading += 1
            else:
                break
        # Insert after leading minors
        pile.insert(count_leading, company_id)


def move_token_down(state: GameState, company_id: str, steps: int = 1) -> None:
    """Move company's token down (row+1) by steps, stopping at grid bottom.

    steps must be an integer >= 0. 0 is a no-op.
    """
    if not isinstance(steps, int) or steps < 0:
        raise MarketError("ERR_BAD_STEPS", f"steps must be an int >= 0, got {steps}")
    old_pos = token_cell(state, company_id)
    if old_pos is None:
        raise MarketError("ERR_NO_TOKEN", f"Company {company_id} has no token")
    row, col = old_pos
    new_row = row
    for _ in range(steps):
        candidate = (new_row + 1, col)
        if candidate in STOCK_MARKET_BY_POSITION:
            new_row = candidate[0]
        else:
            break
    if (new_row, col) == old_pos:
        # No actual cell change – keep position in pile (do nothing)
        return
    # Move to the bottom of the destination pile
    place_token(state, company_id, new_row, col)


def move_token_up(state: GameState, company_id: str) -> None:
    """Move company's token up one row (row-1, same column). If the new cell is
    a game-end cell, triggers check_game_end_triggers."""
    old_pos = token_cell(state, company_id)
    if old_pos is None:
        raise MarketError("ERR_NO_TOKEN", f"Company {company_id} has no token")
    row, col = old_pos
    up = (row - 1, col)
    if up in STOCK_MARKET_BY_POSITION:
        place_token(state, company_id, up[0], up[1])
        # Check if it's a game-end cell
        if STOCK_MARKET_BY_POSITION[up].game_end:
            # lazy import to avoid circular dependency
            from .scoring import check_game_end_triggers

            check_game_end_triggers(state, context="after_token_move")
    # else: no move (top of grid)


def descending_order(state: GameState, company_ids: Iterable[str]) -> list[str]:
    """Sort company_ids in descending share price order (by price desc, col desc, then pile top first).
    Raises MarketError if any listed company has no token."""
    ids = list(company_ids)
    # Validate tokens exist
    for cid in ids:
        if cid not in state.stock_positions:
            raise MarketError("ERR_NO_TOKEN", f"Company {cid} has no token on the market")
    # Sort using descending_price_key from stock_positions (given code)
    return sorted(ids, key=lambda c: descending_price_key(state, c))


descending_share_price_order = descending_order


def operating_order(state: GameState) -> list[str]:
    """Return floated minors then floated majors, each group in descending order.
    Minors excluded if acquired_by_major or removed."""
    minors = [
        mid
        for mid, m in state.minors.items()
        if m.director_player_id is not None
        and mid in state.stock_positions
        and not m.acquired_by_major
        and not m.removed
    ]
    majors = [
        cid
        for cid, m in state.majors.items()
        if m.floated and cid in state.stock_positions
    ]
    return descending_order(state, minors) + descending_order(state, majors)


def next_operating_company(state: GameState, done: Iterable[str] = ()) -> str | None:
    """Return the first company in current operating_order not in done, or None."""
    done_set = set(done)
    for cid in operating_order(state):
        if cid not in done_set:
            return cid
    return None


def compute_stock_round_order(cash: dict[str, int], previous_order: list[str]) -> list[str]:
    """Sort players by cash descending; ties keep relative order from previous_order.
    Raises MarketError if cash keys differ from previous_order."""
    if set(cash) != set(previous_order):
        raise MarketError(
            "ERR_PLAYER_MISMATCH",
            f"cash keys {set(cash)} do not match previous_order players {set(previous_order)}",
        )
    # Build a mapping of player -> index in previous_order for stable sort
    prev_index = {pid: idx for idx, pid in enumerate(previous_order)}
    return sorted(cash.keys(), key=lambda pid: (-cash[pid], prev_index[pid]))


next_player_order = compute_stock_round_order


def reorder_players_by_cash(state: GameState) -> None:
    """Set player_order and priority_deal_player_id according to cash order."""
    cash = {pid: state.players[pid].cash for pid in state.player_order}
    new_order = compute_stock_round_order(cash, state.player_order)
    state.player_order = new_order
    state.priority_deal_player_id = new_order[0]


reorder_players = reorder_players_by_cash


def raise_sold_out_prices(state: GameState) -> None:
    """Move up one cell every 100%-sold major. Minors are never sold out."""
    # Lazy import to avoid circularity
    from .certificates import fully_sold

    # Only floated majors with fully_sold
    affected = [
        cid
        for cid, m in state.majors.items()
        if m.floated and cid in state.stock_positions and fully_sold(state, cid)
    ]
    if not affected:
        return
    # Snapshot order before any move
    sorted_affected = descending_order(state, affected)
    for cid in sorted_affected:
        move_token_up(state, cid)
