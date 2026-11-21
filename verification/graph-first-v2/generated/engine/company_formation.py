"""Company formation: converting concessions into major companies and floating
purchased minors (layer 5).

Contract: contract/company_formation.md.  Money is integer pounds.
"""
from __future__ import annotations

from typing import Iterable

from .models import GameState

MAJOR_START_PRICES = (60, 70, 80, 90, 100)
MINOR_START_PRICES = (50, 60, 70, 80, 90, 100)


class ConcessionError(Exception):
    """Raised by convert_concession. Message '<ERR_CODE>: <text>', .code = ERR_CODE."""

    def __init__(self, code: str, text: str = "") -> None:
        self.code = code
        super().__init__(f"{code}: {text}" if text else f"{code}: {code}")


def convert_concession(state: GameState, player_id: str, abbr: str, start_price: int) -> None:
    """Convert a held concession into the director's certificate and float the major."""
    # Lower layers: module-level imports allowed, kept lazy for robustness.
    from . import certificates, scoring, turn_order

    player = state.players.get(player_id)
    if player is None:
        raise ConcessionError("ERR_NOT_HELD", f"unknown player {player_id!r}")

    # 1. phase
    if not (2 <= state.phase <= 4):
        raise ConcessionError("ERR_PHASE", f"concessions cannot be converted in phase {state.phase}")
    # 2. held
    major = state.majors.get(abbr)
    if major is None or abbr not in player.concessions:
        raise ConcessionError("ERR_NOT_HELD", f"{player_id} does not hold the concession {abbr!r}")
    # 3. not started
    if major.floated:
        raise ConcessionError("ERR_ALREADY_STARTED", f"{abbr} is already floated")
    # 4. loans
    if player.loans != 0:
        raise ConcessionError("ERR_LOANS", f"{player_id} has loans")
    # 5. must sell
    if certificates.must_sell(state, player_id):
        raise ConcessionError("ERR_MUST_SELL", f"{player_id} must sell down first")
    # 6. start price
    if start_price not in MAJOR_START_PRICES:
        raise ConcessionError("ERR_BAD_START_PRICE", f"{start_price!r} is not a major start price")
    # 7. cash
    is_lnwr = abbr == "LNWR"
    if not is_lnwr and player.cash < 2 * start_price - 100:
        raise ConcessionError(
            "ERR_INSUFFICIENT_CASH",
            f"need {2 * start_price - 100}, have {player.cash}",
        )

    units = certificates.cert_units(abbr)

    # Effects, in order.
    # 1
    player.concessions.remove(abbr)
    major.director_player_id = player_id
    major.concession_holder_player_id = None
    player.shares[abbr] = player.shares.get(abbr, 0) + units
    # 2
    turn_order.place_start_token(state, abbr, start_price, "major")
    # 3 / 4
    if is_lnwr:
        state.bank.cash -= start_price
        major.treasury = start_price
        major.shares_in_treasury = 9
    else:
        state.bank.cash -= 100
        player.cash -= 2 * start_price - 100
        major.treasury = 2 * start_price
        major.shares_in_treasury = 8
    # 5
    major.shares_in_bank_pool = 0
    # 6
    major.concession_converted = True
    major.floated = True
    major.has_operated = False
    major.share_price = start_price
    # 7
    state.any_sale_this_stock_round = True
    # 8
    scoring.check_game_end_triggers(state, "after_bank_payment")


def minor_start_price(phase: int, bid: int) -> int:
    """Phase 1: 50; else highest start value <= bid//2, min 50, max 100."""
    if phase <= 1:
        return 50
    half = bid // 2
    best = MINOR_START_PRICES[0]
    for v in MINOR_START_PRICES:
        if v <= half:
            best = v
    return best


def minor_start_treasury(phase: int, bid: int, price: int | None = None) -> int:
    """Phase 1: 100; phase 2: 2*price; phase >= 3: bid."""
    if phase <= 1:
        return 100
    if price is None:
        price = minor_start_price(phase, bid)
    if phase == 2:
        return 2 * price
    return bid


def minor_float_order(pending: Iterable[tuple[int, int, int, str]]) -> list[tuple[int, int, int, str]]:
    """Bid descending, ties: lower box index first."""
    return sorted(pending, key=lambda p: (-p[1], p[2]))


def float_minors(state: GameState, pending: Iterable[tuple[int, int, int, str]] | None = None) -> None:
    """Float the purchased minors (pending = (minor_number, bid, box_index, buyer_id))."""
    if not pending:
        return
    from . import scoring, turn_order

    phase = state.phase
    for number, bid, _box, _buyer in minor_float_order(pending):
        cid = f"M{number}"
        minor = state.minors.get(cid)
        if minor is None:
            continue
        price = minor_start_price(phase, bid)
        treasury = minor_start_treasury(phase, bid, price)
        turn_order.place_start_token(state, cid, price, "minor")
        state.bank.cash -= treasury
        minor.treasury = treasury
        minor.share_price = price
        minor.floated = True
    scoring.check_game_end_triggers(state, "after_bank_payment")


# Aliases
convert_concession_to_director = convert_concession
start_price_for_minor = minor_start_price
float_minor_companies = float_minors
