"""Buying and selling major-company shares in a stock round (rules 4.2.4, 4.3.1,
4.4.1-4.4.7, 4.5.1-4.5.9).

Units: ``Player.shares[company_id]`` counts 10% units; a major's director's
certificate is 2 units (LNWR: 1). ``shares_in_treasury`` / ``shares_in_bank_pool``
are likewise in 10% units. A change of director only changes
``director_player_id`` - the units each player holds do not change.
"""
from __future__ import annotations

from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .certificates import certificate_count, certificate_limit, owned_certificate_count
from .models import GameState, MajorCompanyState
from .stock_positions import company_value, place_token

MAX_HOLDING_UNITS = 6          # rule 4.5.6: no further purchase once a player holds 60%
BANK_POOL_MAX_UNITS = 5        # rule 4.4.2: at most 50% of a company in the bank pool
LNWR_ABBR = "LNWR"


class ShareError(Exception):
    """Raised for an illegal share purchase or sale; message is user-facing."""


def _director_units(company_id: str) -> int:
    """Units represented by the director's certificate (rules 3.3.2, 3.3.3)."""
    return 1 if company_id == LNWR_ABBR else 2


def _get_player(state: GameState, player_id: str):
    player = state.players.get(player_id)
    if player is None:
        raise ShareError(f"Unknown player {player_id!r}.")
    return player


def _get_major(state: GameState, company_id: str) -> MajorCompanyState:
    if company_id in state.minors:
        raise ShareError("Minor companies have no shares that can be bought or sold.")
    company = state.majors.get(company_id)
    if company is None:
        raise ShareError(f"Unknown company {company_id!r}.")
    return company


def _in_yellow_zone(state: GameState, company_id: str) -> bool:
    pos = state.stock_positions.get(company_id)
    if pos is None:
        return False
    return STOCK_MARKET_BY_POSITION[pos].zone == "yellow"


def buy_share(state: GameState, player_id: str, company_id: str, source: str | None = None) -> None:
    player = _get_player(state, player_id)
    company = _get_major(state, company_id)

    if player.loans > 0:                                              # 4.3.1
        raise ShareError("You may not buy shares while you have loans.")
    if must_sell_to_limit(state, player_id):                          # 4.4.7
        raise ShareError("You are over the certificate limit and must sell shares first.")
    if not company.floated:                                           # 4.5.2, 4.6
        raise ShareError(f"{company_id} has not been floated; it has no shares to buy.")
    if company.director_player_id is None or company_id not in state.stock_positions:
        raise ShareError(f"{company_id} has no director yet; its shares cannot be bought.")  # 4.5.2
    if company_id in state.sold_this_round.get(player_id, set()):    # 4.5.5
        raise ShareError(f"You sold {company_id} shares earlier in this stock round.")

    held = player.shares.get(company_id, 0)
    if held >= MAX_HOLDING_UNITS:                                     # 4.5.6
        raise ShareError("You may not hold more than 60% of a company.")

    if source not in (None, "bank", "treasury"):
        raise ShareError(f"Unknown share source {source!r}.")
    if source is None:
        source = "bank" if company.shares_in_bank_pool > 0 else "treasury"
    if source == "bank" and company.shares_in_bank_pool <= 0:
        raise ShareError(f"The bank pool has no {company_id} share.")
    if source == "treasury" and company.shares_in_treasury <= 0:
        raise ShareError(f"The {company_id} treasury has no share to sell.")

    # 4.2.4 / 4.5.7 / 4.5.8: certificate limit, unless the share would not count (yellow zone).
    if not _in_yellow_zone(state, company_id):
        if certificate_count(state, player_id) + 1 > certificate_limit(state):
            raise ShareError("Buying this share would exceed your certificate limit.")

    price = company_value(state, company_id)
    if player.cash < price:
        raise ShareError(f"Not enough cash: the share costs £{price}.")

    # --- all checks passed: apply ---
    player.cash -= price
    if source == "bank":
        state.bank.cash += price                                      # 4.5.1
        company.shares_in_bank_pool -= 1
    else:
        company.treasury += price
        company.shares_in_treasury -= 1
    player.shares[company_id] = held + 1
    state.any_sale_this_stock_round = True                            # 10.1.1

    # 4.5.9: strictly more than the director -> new director (units unchanged).
    director_id = company.director_player_id
    if director_id != player_id:
        director_units = state.players[director_id].shares.get(company_id, 0)
        if held + 1 > director_units:
            company.director_player_id = player_id


def _next_order_distance(state: GameState, from_player: str, to_player: str) -> int:
    order = state.player_order
    if from_player not in order or to_player not in order:
        return len(order) + 1
    n = len(order)
    return (order.index(to_player) - order.index(from_player)) % n or n


def _check_sale(state: GameState, player_id: str, company_id: str, count: int):
    """Validate a sale (4.4.2 etc.); return the new director id (or None). Raises ShareError."""
    player = _get_player(state, player_id)
    company = _get_major(state, company_id)

    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ShareError("You must sell at least one share.")
    if not company.floated or company_id not in state.stock_positions:
        raise ShareError(f"{company_id} has not been floated.")
    if not company.has_operated:                                      # 4.4.2
        raise ShareError(f"{company_id} has not completed an operating round; its shares cannot be sold.")

    held = player.shares.get(company_id, 0)
    if held < count:
        raise ShareError(f"You hold only {held} {company_id} share(s).")
    if company.shares_in_bank_pool + count > BANK_POOL_MAX_UNITS:     # 4.4.2: max 50% in pool
        raise ShareError("At most 50% of a company's stock may be in the bank pool.")

    new_director: str | None = None
    if company.director_player_id == player_id:
        dir_units = _director_units(company_id)
        remaining = held - count
        candidates = [
            (pid, p.shares.get(company_id, 0))
            for pid, p in state.players.items()
            if pid != player_id and p.shares.get(company_id, 0) >= dir_units
            and p.shares.get(company_id, 0) > remaining
        ]
        if candidates:
            best = max(units for _, units in candidates)
            tied = [pid for pid, units in candidates if units == best]
            new_director = min(tied, key=lambda pid: _next_order_distance(state, player_id, pid))
        elif count > held - dir_units:                                # director's certificate unsellable
            raise ShareError("The director's certificate cannot be sold into the bank pool.")
    return new_director


def must_sell_to_limit(state: GameState, player_id: str) -> bool:
    """Rule 4.4.7: over the certificate limit and still able to sell something that counts."""
    if player_id not in state.players:
        return False
    if owned_certificate_count(state, player_id) <= certificate_limit(state):
        return False
    player = state.players[player_id]
    for cid, units in player.shares.items():
        if units <= 0 or cid not in state.majors or _in_yellow_zone(state, cid):
            continue
        try:
            _check_sale(state, player_id, cid, 1)
        except ShareError:
            continue
        return True
    return False


def sell_shares(state: GameState, player_id: str, company_id: str, count: int) -> None:
    player = _get_player(state, player_id)
    company = _get_major(state, company_id)
    new_director = _check_sale(state, player_id, company_id, count)
    held = player.shares.get(company_id, 0)
    state.any_sale_this_stock_round = True                            # 10.1.1

    # --- all checks passed: apply ---
    if new_director is not None:
        company.director_player_id = new_director                     # exchange happens first

    price = company_value(state, company_id)
    player.cash += price * count                                      # 4.4.3
    state.bank.cash -= price * count
    player.shares[company_id] = held - count
    company.shares_in_bank_pool += count
    state.sold_this_round.setdefault(player_id, set()).add(company_id)  # 4.5.5 bookkeeping

    # 4.4.4 / 4.4.5: drop one row per share sold; stop where no cell exists below.
    row, col = state.stock_positions[company_id]
    new_row = row
    for _ in range(count):
        if (new_row + 1, col) in STOCK_MARKET_BY_POSITION:
            new_row += 1
        else:
            break
    if new_row != row:
        place_token(state, company_id, new_row, col)                  # bottom of the new cell's stack
