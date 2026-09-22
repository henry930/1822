"""Converting a held concession to a major company director's certificate
(rule 4.7, phases 2-4 only). Direct major-company formation from Phase 5
onward (rule 4.8) belongs to Task #7 (company lifecycle), since it's tied
to operating-round acquisition timing rather than being a pure stock-round
choice like conversion is.
"""
from __future__ import annotations

from app.data.major_companies import LNWR_ABBR
from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .models import GameState
from .stock_positions import place_token

VALID_START_PRICES = (60, 70, 80, 90, 100)


class ConcessionError(Exception):
    pass


def convert_concession(state: GameState, player_id: str, abbr: str, start_price: int) -> None:
    if state.phase not in (2, 3, 4):
        raise ConcessionError("Concessions may only be converted in phases 2-4 (rule 4.7.1).")
    if abbr not in state.players[player_id].concessions:
        raise ConcessionError("You do not hold that concession.")
    if start_price not in VALID_START_PRICES:
        raise ConcessionError(f"Starting price must be one of {VALID_START_PRICES}.")

    major = state.majors[abbr]
    player = state.players[player_id]
    is_lnwr = abbr == LNWR_ABBR

    player.concessions.remove(abbr)
    major.director_player_id = player_id
    major.floated = True
    major.share_price = start_price

    if is_lnwr:
        # Rule 4.7.4: director's certificate is a single 10% share; the whole
        # starting price comes from the bank, nothing from the player.
        major.treasury = start_price
        player.shares[abbr] = 1
    else:
        # Rule 4.7.3: £100 (concession face value) from the bank, the player
        # pays the balance of 2x the starting price less that £100.
        major.treasury = 100
        player_contribution = 2 * start_price - 100
        player.cash -= player_contribution
        major.treasury += player_contribution
        player.shares[abbr] = 2

    _place_on_price(state, abbr, start_price)


def _place_on_price(state: GameState, company_id: str, price: int) -> None:
    for (row, col), cell in STOCK_MARKET_BY_POSITION.items():
        if cell.value == price and cell.zone == "start":
            place_token(state, company_id, row, col)
            return
    raise ConcessionError(f"No start-price cell found for £{price}")
