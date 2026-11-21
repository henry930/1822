"""Major company formation by converting a concession (rules 4.6-4.7, 4.9)."""
from __future__ import annotations

from app.data.major_companies import LNWR_ABBR
from app.data.stock_market import STOCK_MARKET_CELLS

from .models import GameState
from .stock_positions import place_token

VALID_START_PRICES = (60, 70, 80, 90, 100)

CONCESSION_DISCOUNT = 100  # rule 4.7.3: the bank contributes 100 (concession face value)


class ConcessionError(Exception):
    """Raised when a concession conversion is illegal."""


def _start_cell(price: int) -> tuple[int, int]:
    for c in STOCK_MARKET_CELLS:
        if c.zone == "start" and c.value == price:
            return (c.row, c.col)
    raise ConcessionError(f"No start space on the stock market for {price}.")


def convert_concession(state: GameState, player_id: str, abbr: str, start_price: int) -> None:
    player = state.players.get(player_id)
    if player is None:
        raise ConcessionError(f"Unknown player {player_id!r}.")
    major = state.majors.get(abbr)
    if major is None:
        raise ConcessionError(f"Unknown major company {abbr!r}.")

    # 4.6.2 / 4.6.3 / 4.8.1: conversion exists only in phases 2-4.
    if state.phase < 2:
        raise ConcessionError("Major companies may not be formed in Phase 1.")
    if state.phase > 4:
        raise ConcessionError("Concessions no longer exist from Phase 5.")
    # 4.3.1
    if player.loans > 0:
        raise ConcessionError("A player with outstanding loans may not convert a concession.")
    if abbr not in player.concessions:
        raise ConcessionError(f"{player_id} does not hold the {abbr} concession.")
    if major.floated or major.concession_converted or major.director_player_id is not None:
        raise ConcessionError(f"{abbr} has already been formed.")
    # 4.7.2: start price must be one of the red-outlined spaces.
    if isinstance(start_price, bool) or start_price not in VALID_START_PRICES:
        raise ConcessionError(f"Start price must be one of {VALID_START_PRICES}.")

    is_lnwr = abbr == LNWR_ABBR
    if is_lnwr:
        # 4.7.4: the bank pays the starting price into the treasury; player pays nothing.
        treasury = start_price
        bank_part = start_price
        player_part = 0
        units = 1
        treasury_units = 9
    else:
        # 4.7.3: 100 from the bank, balance of 2 x price - 100 from the player.
        treasury = 2 * start_price
        bank_part = CONCESSION_DISCOUNT
        player_part = treasury - CONCESSION_DISCOUNT
        units = 2
        treasury_units = 8
    if player.cash < player_part:
        raise ConcessionError(
            f"Not enough cash: need {player_part}, have {player.cash}."
        )

    row, col = _start_cell(start_price)

    # --- all checks passed: mutate ---
    player.concessions.remove(abbr)
    player.shares[abbr] = player.shares.get(abbr, 0) + units
    player.cash -= player_part
    state.bank.cash -= bank_part

    major.director_player_id = player_id
    major.concession_holder_player_id = player_id
    major.concession_converted = True
    major.floated = True
    major.share_price = start_price
    major.treasury += treasury
    major.shares_in_treasury = treasury_units
    major.shares_in_bank_pool = 0

    place_token(state, abbr, row, col)
    state.log.append(f"{player_id} converted the {abbr} concession at {start_price}.")
