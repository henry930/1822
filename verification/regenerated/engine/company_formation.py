"""Converting a concession into a floated major company (rules 4.7, 4.9)."""
from __future__ import annotations

from app.data.phases import PHASES_BY_NUMBER
from app.data.stock_market import STOCK_MARKET_CELLS

from .certificates import LNWR_ABBR
from .models import GameState
from .stock_positions import place_token

VALID_START_PRICES = (60, 70, 80, 90, 100)
CONCESSION_DISCOUNT = 100


class ConcessionError(Exception):
    pass


def start_cell(price: int) -> tuple[int, int]:
    for c in STOCK_MARKET_CELLS:
        if c.zone == "start" and c.value == price:
            return (c.row, c.col)
    raise ConcessionError(f"No start space for price {price}.")


def convert_concession(state: GameState, player_id: str, abbr: str, start_price: int) -> None:
    player = state.players.get(player_id)
    if player is None:
        raise ConcessionError(f"Unknown player {player_id!r}.")
    major = state.majors.get(abbr)
    if major is None:
        raise ConcessionError(f"Unknown company {abbr!r}.")
    if start_price not in VALID_START_PRICES:
        raise ConcessionError("Start price must be one of 60, 70, 80, 90 or 100.")
    if PHASES_BY_NUMBER[state.phase].major_flotation_rule != "on_concession_conversion":
        raise ConcessionError("Concessions can only be converted in Phases 2-4 (rules 4.6.2-4.6.3).")
    if abbr not in player.concessions:
        raise ConcessionError("You do not hold that concession.")
    if major.floated or major.concession_converted:
        raise ConcessionError("That company has already been formed.")
    if player.loans > 0:
        raise ConcessionError("A player with loans may not convert a concession (rule 4.3.1).")

    is_lnwr = abbr == LNWR_ABBR
    if is_lnwr:
        player_pays = 0           # rule 4.7.4: whole starting price comes from the bank
        bank_pays = start_price
        director_units = 1
        treasury = start_price
        remaining = 9
    else:
        treasury = 2 * start_price  # rule 4.7.3
        bank_pays = CONCESSION_DISCOUNT
        player_pays = treasury - CONCESSION_DISCOUNT
        director_units = 2
        remaining = 8
    if player.cash < player_pays:
        raise ConcessionError("Not enough cash to capitalise the company.")

    player.concessions.remove(abbr)
    player.cash -= player_pays
    state.bank.cash -= bank_pays
    player.shares[abbr] = player.shares.get(abbr, 0) + director_units

    major.concession_converted = True
    major.floated = True
    major.director_player_id = player_id
    major.share_price = start_price
    major.treasury += treasury
    major.shares_in_treasury = remaining
    major.shares_in_bank_pool = 0
    row, col = start_cell(start_price)
    place_token(state, abbr, row, col)  # 4.7.2: underneath any tokens already there
