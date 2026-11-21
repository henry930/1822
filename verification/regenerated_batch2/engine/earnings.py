"""Earnings distribution and share price movement (rules 5.12.1-5.12.3, 5.12.7-5.12.14).

Special trains (5.12.4-5.12.6) are out of scope: ``revenue`` is a single total.
"""
from __future__ import annotations

from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .models import GameState
from .stock_positions import cell_value, place_token

CHOICES = ("full", "half", "withhold")


def _operating_error(msg: str) -> Exception:
    from .operating import OperatingError  # lazy: operating imports this module

    return OperatingError(msg)


def _step_right(pos: tuple[int, int]) -> tuple[int, int]:
    r, c = pos
    if (r, c + 1) in STOCK_MARKET_BY_POSITION:
        return (r, c + 1)
    if (r - 1, c) in STOCK_MARKET_BY_POSITION:  # arrow rule 5.12.13 (provisional): up
        return (r - 1, c)
    return pos


def _step_left(pos: tuple[int, int]) -> tuple[int, int]:
    r, c = pos
    if (r, c - 1) in STOCK_MARKET_BY_POSITION:
        return (r, c - 1)
    if (r + 1, c) in STOCK_MARKET_BY_POSITION:  # arrow rule: down
        return (r + 1, c)
    return pos


def _move_price(state: GameState, company_id: str, direction: str, spaces: int) -> None:
    pos = state.stock_positions.get(company_id)
    if pos is None or spaces <= 0:
        return
    step = _step_right if direction == "right" else _step_left
    new = pos
    for _ in range(spaces):
        new = step(new)
    if new != pos:  # unmoved token keeps its place in the stack (5.12.14)
        place_token(state, company_id, new[0], new[1])
    entity = state.majors.get(company_id) or state.minors.get(company_id)
    if entity is not None:
        entity.share_price = cell_value(*state.stock_positions[company_id])


def _check_end(state: GameState) -> None:
    from .scoring import check_game_end_triggers  # lazy

    check_game_end_triggers(state)


def distribute_earnings(state: GameState, company_id: str, kind: str, revenue: int, choice: str) -> int:
    """Pay out ``revenue`` for a minor/major and move its price token.
    Returns the dividend paid (the figure that decides the price move)."""
    if choice not in CHOICES:
        raise _operating_error(f"Unknown dividend choice {choice!r}; use full, half or withhold.")
    if kind not in ("minor", "major"):
        raise _operating_error(f"Unknown company kind {kind!r}.")
    revenue = max(0, int(revenue))

    if kind == "minor":
        minor = state.minors.get(company_id)
        if minor is None:
            raise _operating_error(f"Unknown minor company {company_id!r}.")
        to_director = revenue // 2           # 5.12.1: odd pound goes to the treasury
        to_treasury = revenue - to_director
        director = state.players.get(minor.director_player_id) if minor.director_player_id else None
        if director is not None:
            director.cash += to_director
        minor.treasury += to_treasury
        state.bank.cash -= to_director + to_treasury
        dividend = to_director
        _move_price(state, company_id, "right" if dividend > 0 else "left", 1)
        _check_end(state)
        return dividend

    major = state.majors.get(company_id)
    if major is None:
        raise _operating_error(f"Unknown major company {company_id!r}.")

    if choice == "withhold":
        dividend = 0
    elif choice == "full":
        dividend = revenue
    else:  # half, rounded up to the next multiple of 10, never above revenue (5.12.2)
        dividend = min(revenue, -(-(revenue // 2 + revenue % 2) // 10) * 10)
    retained = revenue - dividend

    paid = retained
    major.treasury += retained
    if dividend > 0:
        # 5.12.3: 10% of the dividend per 10% share. Whole pounds only (fractions stay with the bank).
        for player in state.players.values():
            units = player.shares.get(company_id, 0)
            if units > 0:
                amount = dividend * units // 10
                player.cash += amount
                paid += amount
        t_amount = dividend * major.shares_in_treasury // 10
        major.treasury += t_amount
        paid += t_amount
        # shares in the bank pool: money stays with the bank
    state.bank.cash -= paid

    price = cell_value(*state.stock_positions[company_id]) if company_id in state.stock_positions else (major.share_price or 0)
    if dividend == 0:
        _move_price(state, company_id, "left", 1)
    elif dividend >= 2 * price:
        _move_price(state, company_id, "right", 2)
    elif dividend >= price:
        _move_price(state, company_id, "right", 1)
    _check_end(state)
    return dividend
