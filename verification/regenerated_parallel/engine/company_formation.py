"""Major company formation by converting a concession (rules 4.6, 4.7, 4.9).

Phases 2-4 only: the concession holder turns the concession into the director's
certificate, sets the start price on a red-outlined start space and funds the
treasury.  Phase 5+ direct purchase (rule 4.8) is NOT handled here.
"""
from __future__ import annotations

from app.data.major_companies import LNWR_ABBR
from app.data.stock_market import STOCK_MARKET_CELLS

from .models import GameState
from .stock_positions import place_token

VALID_START_PRICES = (60, 70, 80, 90, 100)

CONCESSION_DISCOUNT = 100  # rule 4.7.3 / 3.4.2: bank contributes the concession's face value


class ConcessionError(Exception):
    """Raised when a concession conversion is illegal."""


def _start_cell(price: int):
    for cell in STOCK_MARKET_CELLS:
        if cell.zone == "start" and cell.value == price:
            return cell
    raise ConcessionError(f"No start space on the stock market for price {price}")


def convert_concession(state: GameState, player_id: str, abbr: str, start_price: int) -> None:
    player = state.players.get(player_id)
    if player is None:
        raise ConcessionError(f"Unknown player {player_id}")
    major = state.majors.get(abbr)
    if major is None:
        raise ConcessionError(f"Unknown major company {abbr}")

    # Rule 4.6.2 / 4.6.3 / 4.8.1: conversion is possible only in phases 2-4.
    if state.phase < 2:
        raise ConcessionError("Major companies may not be formed in Phase 1 (rule 4.6.2)")
    if state.phase >= 5:
        raise ConcessionError("Concessions no longer exist from Phase 5 (rule 3.4.5)")

    if isinstance(start_price, bool) or not isinstance(start_price, int) or start_price not in VALID_START_PRICES:
        raise ConcessionError(f"Start price must be one of {VALID_START_PRICES}")

    if abbr not in player.concessions:
        raise ConcessionError(f"Player does not hold the {abbr} concession")
    if major.floated or major.concession_converted or major.director_player_id is not None:
        raise ConcessionError(f"{abbr} has already been formed")

    # Rule 4.3.1: no converting while holding loans.
    if player.loans > 0:
        raise ConcessionError("A player with loans may not convert a concession (rule 4.3.1)")

    lnwr = abbr == LNWR_ABBR
    total_capital = start_price if lnwr else 2 * start_price
    from_bank = total_capital if lnwr else CONCESSION_DISCOUNT
    from_player = total_capital - from_bank  # 0 for LNWR; 2p-100 otherwise
    if player.cash < from_player:
        raise ConcessionError(f"Player needs £{from_player} cash to convert {abbr}, has £{player.cash}")

    cell = _start_cell(start_price)

    # Convert: concession -> director's certificate.
    player.concessions.remove(abbr)
    director_units = 1 if lnwr else 2
    player.shares[abbr] = player.shares.get(abbr, 0) + director_units
    major.concession_holder_player_id = player_id
    major.concession_converted = True
    major.director_player_id = player_id

    # Money: bank pays its part, the player pays the balance, both into the treasury.
    state.bank.cash -= from_bank
    player.cash -= from_player
    major.treasury += total_capital

    # Share price token, underneath any tokens already on the space (rule 4.7.2).
    major.share_price = start_price
    place_token(state, abbr, cell.row, cell.col)

    # Remaining certificates go to the company treasury (10 units in total per company).
    major.shares_in_treasury = 10 - director_units
    major.shares_in_bank_pool = 0

    major.floated = True
    state.log.append(f"{player_id} converted the {abbr} concession at start price £{start_price}")
