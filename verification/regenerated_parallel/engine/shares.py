"""Buying and selling major-company shares in a stock round.

Rules implemented: 4.2.4, 4.3.1, 4.4.1-4.4.7 (bookkeeping, directorship, payment, price drop),
4.5.1-4.5.9.  Units are 10% shares: a major's director's certificate is 2 units (LNWR: 1).
"""
from __future__ import annotations

from app.data.major_companies import LNWR_ABBR
from app.data.stock_market import STOCK_MARKET_BY_POSITION

from . import stock_positions
from .certificates import certificate_count, certificate_limit
from .models import GameState, RoundType

MAX_HOLDING_UNITS = 6          # rule 4.5.6: no more buying once a player holds 60%
MAX_POOL_UNITS = 5             # rule 4.4.2: at most 50% of a company's stock in the bank pool


class ShareError(Exception):
    """Raised for an illegal share purchase or sale; message is user-facing."""


def _director_units(abbr: str) -> int:
    """Units represented by the director's certificate (rules 3.3.2, 3.3.3)."""
    return 1 if abbr == LNWR_ABBR else 2


def _in_yellow_zone(state: GameState, company_id: str) -> bool:
    pos = state.stock_positions.get(company_id)
    return pos is not None and STOCK_MARKET_BY_POSITION[pos].zone == "yellow"


def _check_common(state: GameState, player_id: str, company_id: str):
    if state.round_type != RoundType.STOCK:
        raise ShareError("Shares can only be bought or sold in a stock round.")
    player = state.players.get(player_id)
    if player is None:
        raise ShareError(f"Unknown player {player_id!r}.")
    if company_id in state.minors:
        raise ShareError("Minor companies have no shares that can be bought or sold.")
    company = state.majors.get(company_id)
    if company is None:
        raise ShareError(f"Unknown company {company_id!r}.")
    if company_id not in state.stock_positions:
        raise ShareError(f"{company_id} has no stock market value.")
    return player, company


def buy_share(state: GameState, player_id: str, company_id: str, source: str | None = None) -> None:
    player, company = _check_common(state, player_id, company_id)

    if player.loans > 0:                                                    # 4.3.1
        raise ShareError("You may not buy shares while you have outstanding loans.")
    if not company.floated:                                                 # 4.5.2
        raise ShareError(f"{company_id} has not floated; it has no shares to buy.")
    if company.director_player_id is None:                                  # 4.5.2
        raise ShareError(f"{company_id} has no director; its shares cannot be bought yet.")
    if company_id in state.sold_this_round.get(player_id, set()):           # 4.5.5
        raise ShareError(f"You sold {company_id} stock earlier this stock round and may not buy it.")

    held = player.shares.get(company_id, 0)
    if held >= MAX_HOLDING_UNITS:                                           # 4.5.6
        raise ShareError("You may not buy more shares once you hold 60% of a company.")

    if source is None:
        source = "bank" if company.shares_in_bank_pool > 0 else "treasury"
    if source == "bank":
        if company.shares_in_bank_pool < 1:
            raise ShareError(f"The bank pool has no {company_id} share.")
    elif source == "treasury":
        if company.shares_in_treasury < 1:
            raise ShareError(f"The {company_id} treasury has no share to sell.")
    else:
        raise ShareError(f"Unknown share source {source!r}.")

    # 4.2.4 / 4.5.7 / 4.5.8: certificate limit (yellow-zone stock does not count)
    if not _in_yellow_zone(state, company_id):
        if certificate_count(state, player_id) + 1 > certificate_limit(state):
            raise ShareError("Buying this share would exceed your certificate limit.")

    price = stock_positions.company_value(state, company_id)
    if player.cash < price:
        raise ShareError(f"You need £{price} to buy this share; you have £{player.cash}.")

    # --- commit ---
    player.cash -= price
    if source == "bank":
        state.bank.cash += price
        company.shares_in_bank_pool -= 1
    else:
        company.treasury += price
        company.shares_in_treasury -= 1
    player.shares[company_id] = held + 1

    # 4.5.9: a holding larger than the director's takes the directorship
    director_id = company.director_player_id
    if director_id != player_id:
        if player.shares[company_id] > state.players[director_id].shares.get(company_id, 0):
            company.director_player_id = player_id
    state.log.append(f"{player_id} bought a {company_id} share from the {source} for £{price}.")


def _next_in_order_distance(state: GameState, from_pid: str, pid: str) -> int:
    order = state.player_order
    if from_pid not in order or pid not in order:
        return len(order) + 1
    return (order.index(pid) - order.index(from_pid)) % len(order)


def sell_shares(state: GameState, player_id: str, company_id: str, count: int) -> None:
    player, company = _check_common(state, player_id, company_id)

    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ShareError("You must sell at least one share.")
    if not company.has_operated:                                            # 4.4.2
        raise ShareError(f"{company_id} has not completed an operating round; its shares cannot be sold.")
    held = player.shares.get(company_id, 0)
    if held < count:
        raise ShareError(f"You hold only {held} {company_id} share unit(s).")
    if company.shares_in_bank_pool + count > MAX_POOL_UNITS:                # 4.4.2
        raise ShareError("At most 50% of a company's stock may be in the bank pool.")
    price = stock_positions.company_value(state, company_id)

    director_id = company.director_player_id
    min_cert = _director_units(company_id)
    new_director = None
    if director_id == player_id:
        remaining = held - count
        candidates = [
            (pid, p.shares.get(company_id, 0)) for pid, p in state.players.items()
            if pid != player_id and p.shares.get(company_id, 0) > remaining
            and p.shares.get(company_id, 0) >= min_cert
        ]
        if candidates:
            best = max(u for _, u in candidates)
            tied = [pid for pid, u in candidates if u == best]
            new_director = min(tied, key=lambda pid: _next_in_order_distance(state, player_id, pid))
        elif count > held - min_cert:                                       # director's cert can't be sold
            raise ShareError("The director's certificate cannot be sold into the bank pool.")

    # --- commit ---
    if new_director is not None:                                            # 4.4.2: swap before the sale
        company.director_player_id = new_director
        state.log.append(f"{new_director} becomes director of {company_id}.")

    player.shares[company_id] = held - count
    if player.shares[company_id] == 0:
        del player.shares[company_id]
    company.shares_in_bank_pool += count
    player.cash += price * count                                            # 4.4.3
    state.bank.cash -= price * count
    state.sold_this_round.setdefault(player_id, set()).add(company_id)      # 4.5.5

    # 4.4.4 / 4.4.5: one space down per share sold; stop at the bottom; unmoved token keeps its place
    row, col = state.stock_positions[company_id]
    new_row = row
    for _ in range(count):
        if (new_row + 1, col) not in STOCK_MARKET_BY_POSITION:
            break
        new_row += 1
    if new_row != row:
        stock_positions.place_token(state, company_id, new_row, col)
    state.log.append(f"{player_id} sold {count} {company_id} share(s) for £{price * count}.")
