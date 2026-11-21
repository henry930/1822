"""Buying and selling major company shares in a stock round (rules 4.4, 4.5)."""
from __future__ import annotations

from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .certificates import (
    LNWR_ABBR,
    certificate_count,
    certificate_limit,
    is_in_yellow_zone,
)
from .models import GameState
from .stock_positions import company_value, place_token

MAX_HOLDING_UNITS = 6  # rule 4.5.6: 60%
BANK_POOL_MAX_UNITS = 5  # rule 4.4.2: 50% of the company in the bank pool


class ShareError(Exception):
    pass


def _director_cert_units(company_id: str) -> int:
    return 1 if company_id == LNWR_ABBR else 2


def _min_units_to_direct(company_id: str) -> int:
    """Rule 4.4.2: a prospective director needs 20% (10% for the LNWR)."""
    return 1 if company_id == LNWR_ABBR else 2


def buy_share(state: GameState, player_id: str, company_id: str, source: str | None = None) -> None:
    player = state.players.get(player_id)
    if player is None:
        raise ShareError(f"Unknown player {player_id!r}.")
    major = state.majors.get(company_id)
    if major is None:
        raise ShareError("Only major company shares can be bought (rule 3.2.2).")
    if source not in (None, "bank", "treasury"):
        raise ShareError(f"Unknown share source {source!r}.")
    if player.loans > 0:
        raise ShareError("A player with loans may not buy shares (rule 4.3.1).")
    if not major.floated or major.director_player_id is None or company_id not in state.stock_positions:
        raise ShareError("That company has no shares available to buy (rule 4.5.2).")
    if company_id in state.sold_this_round.get(player_id, set()):
        raise ShareError("You sold shares in this company earlier in this stock round (rule 4.5.5).")
    units = player.shares.get(company_id, 0)
    if units >= MAX_HOLDING_UNITS:
        raise ShareError("You may not hold more than 60% of a company (rule 4.5.6).")

    if source is None:
        source = "bank" if major.shares_in_bank_pool > 0 else "treasury"
    if source == "bank" and major.shares_in_bank_pool <= 0:
        raise ShareError("There are no shares in the bank pool.")
    if source == "treasury" and major.shares_in_treasury <= 0:
        raise ShareError("There are no shares in the company treasury.")

    if not is_in_yellow_zone(state, company_id):
        if certificate_count(state, player_id) + 1 > certificate_limit(state):
            raise ShareError("That purchase would exceed the certificate limit (rules 4.2.4, 4.5.7).")

    price = company_value(state, company_id)
    if player.cash < price:
        raise ShareError("Not enough cash.")

    player.cash -= price
    if source == "bank":
        state.bank.cash += price
        major.shares_in_bank_pool -= 1
    else:
        major.treasury += price
        major.shares_in_treasury -= 1
    player.shares[company_id] = units + 1
    state.any_sale_this_stock_round = True

    # Rule 4.5.9: exceeding the director's holding makes the buyer director.
    director_id = major.director_player_id
    if director_id != player_id:
        if player.shares[company_id] > state.players[director_id].shares.get(company_id, 0):
            major.director_player_id = player_id


def _next_player_distance(state: GameState, from_id: str, to_id: str) -> int:
    order = state.player_order
    if from_id not in order or to_id not in order:
        return len(order) + 1
    return (order.index(to_id) - order.index(from_id)) % len(order) or len(order)


def sell_shares(state: GameState, player_id: str, company_id: str, count: int) -> None:
    player = state.players.get(player_id)
    if player is None:
        raise ShareError(f"Unknown player {player_id!r}.")
    if company_id in state.minors:
        raise ShareError("Minor companies may not be sold (rule 4.4.1).")
    major = state.majors.get(company_id)
    if major is None:
        raise ShareError("Unknown company.")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ShareError("Must sell at least one share.")
    units = player.shares.get(company_id, 0)
    if count > units:
        raise ShareError("You do not own that many shares.")
    if not major.floated or company_id not in state.stock_positions:
        raise ShareError("That company has not floated.")
    if not major.has_operated:
        raise ShareError("Shares cannot be sold before the company has completed an operating round (rule 4.4.2).")
    if major.shares_in_bank_pool + count > BANK_POOL_MAX_UNITS:
        raise ShareError("At most 50% of a company may be in the bank pool (rule 4.4.2).")

    is_director = major.director_player_id == player_id
    new_director: str | None = None
    if is_director:
        post = units - count
        candidates = [
            (pid, p.shares.get(company_id, 0))
            for pid, p in state.players.items()
            if pid != player_id
            and p.shares.get(company_id, 0) >= _min_units_to_direct(company_id)
            and p.shares.get(company_id, 0) > post
        ]
        if candidates:
            best = max(h for _, h in candidates)
            tied = [pid for pid, h in candidates if h == best]
            tied.sort(key=lambda pid: _next_player_distance(state, player_id, pid))
            new_director = tied[0]
        elif count > units - _director_cert_units(company_id):
            raise ShareError("The director's certificate cannot be sold into the bank pool (rule 4.4.2).")

    price = company_value(state, company_id)

    # Rule 4.4.2: director change happens before the rest of the sale is resolved.
    if new_director is not None:
        major.director_player_id = new_director

    player.shares[company_id] = units - count
    major.shares_in_bank_pool += count
    player.cash += price * count
    state.bank.cash -= price * count
    state.sold_this_round.setdefault(player_id, set()).add(company_id)
    state.any_sale_this_stock_round = True

    # Rules 4.4.4-4.4.5: one space down per share sold; stop at the bottom.
    row, col = state.stock_positions[company_id]
    start = (row, col)
    for _ in range(count):
        if (row + 1, col) in STOCK_MARKET_BY_POSITION:
            row += 1
        else:
            break
    if (row, col) != start:
        place_token(state, company_id, row, col)
