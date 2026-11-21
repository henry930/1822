"""Company formation: concession conversion (majors) and minor flotation."""
from __future__ import annotations

from ..data.major_companies import LNWR_ABBR
from .certificates import cert_units, must_sell
from .models import GameState
from .scoring import check_game_end_triggers
from .turn_order import place_start_token

_MAJOR_START_PRICES = (60, 70, 80, 90, 100)
_MINOR_PRICE_STEPS = (50, 60, 70, 80, 90, 100)


class ConcessionError(Exception):
    pass


def convert_concession(state: GameState, player_id: str, abbr: str, start_price: int) -> None:
    p = state.players[player_id]
    # --- preconditions (no mutation) ---
    if not (2 <= state.phase <= 4):
        raise ConcessionError(
            "ERR_PHASE: concessions can only be converted in phases 2 to 4.")
    if abbr not in state.majors or abbr not in p.concessions:
        raise ConcessionError(f"ERR_NOT_HELD: you do not hold the concession for {abbr}.")
    major = state.majors[abbr]
    if major.floated:
        raise ConcessionError(f"ERR_ALREADY_STARTED: {abbr} has already been started.")
    if p.loans != 0:
        raise ConcessionError("ERR_LOANS: you must repay all loans before converting a concession.")
    if must_sell(state, player_id):
        raise ConcessionError(
            "ERR_MUST_SELL: you are over the certificate limit and must sell first.")
    if start_price not in _MAJOR_START_PRICES:
        raise ConcessionError("ERR_BAD_START_PRICE: start price must be 60, 70, 80, 90 or 100.")
    is_lnwr = abbr == LNWR_ABBR
    if not is_lnwr and p.cash < 2 * start_price - 100:
        raise ConcessionError(
            f"ERR_INSUFFICIENT_CASH: you need {2 * start_price - 100} to start {abbr}.")

    cu = cert_units(abbr)
    # --- effects ---
    p.concessions.remove(abbr)
    major.director_player_id = player_id
    major.concession_holder_player_id = None
    major.concession_converted = True

    place_start_token(state, abbr, start_price, "major")

    if is_lnwr:
        state.bank.cash -= start_price
        major.treasury = start_price
    else:
        state.bank.cash -= 100
        p.cash -= 2 * start_price - 100
        major.treasury = 2 * start_price

    major.shares_in_treasury = 9 if is_lnwr else 8
    major.shares_in_bank_pool = 0
    p.shares[abbr] = p.shares.get(abbr, 0) + cu
    major.floated = True
    major.has_operated = False
    state.any_sale_this_stock_round = True
    check_game_end_triggers(state, "after_bank_payment")


def minor_start_price(phase: int, bid: int) -> int:
    if phase <= 1:
        return 50
    half = bid // 2
    best = 50
    for v in _MINOR_PRICE_STEPS:
        if v <= half:
            best = v
    return best


def minor_start_treasury(phase: int, bid: int, price: int) -> int:
    if phase <= 1:
        return 100
    if phase == 2:
        return 2 * price
    return bid


def minor_float_order(pending: list) -> list:
    return sorted(pending, key=lambda t: (-t[1], t[2]))


def float_minors(state: GameState, pending: list) -> None:
    for n, bid, _box_index, _buyer in minor_float_order(list(pending)):
        cid = f"M{n}"
        price = minor_start_price(state.phase, bid)
        treasury = minor_start_treasury(state.phase, bid, price)
        place_start_token(state, cid, price, "minor")
        state.bank.cash -= treasury
        minor = state.minors[cid]
        minor.treasury = treasury
        minor.floated = True
        minor.share_price = price
    check_game_end_triggers(state, "after_bank_payment")
