# backend/app/engine/company_formation.py
# Module‑level exports as specified in company_formation.md
# Layer 5: may import lower layers (1–4) lazily inside functions.

from __future__ import annotations

import sys
from typing import Iterable

# ── Exception class ──────────────────────────────────────────────────────────

class ConcessionError(Exception):
    """Single exception for this module; message '<ERR_CODE>: <text>', .code attribute."""
    def __init__(self, code: str, text: str):
        self.code = code
        super().__init__(f"{code}: {text}")

# ── Constants ────────────────────────────────────────────────────────────────

MAJOR_START_PRICES = (60, 70, 80, 90, 100)
MINOR_START_PRICES = (50, 60, 70, 80, 90, 100)

# ── Helper: LNWR detection ──────────────────────────────────────────────────

_LNWR = "LNWR"

# ── convert_concession (aliased as convert_concession_to_director) ───────────

def convert_concession(state, player_id: str, abbr: str, start_price: int) -> None:
    """Convert a held concession into the director's certificate at the given
    start price (phases 2-4). Raises ConcessionError on any violation."""
    # Lazy imports for calls to lower‑layer modules.
    from .certificates import must_sell, cert_units
    from .turn_order import place_start_token
    from .scoring import check_game_end_triggers

    # ── Validation (order as per contract) ──────────────────────────────────
    if not (2 <= state.phase <= 4):
        raise ConcessionError("ERR_PHASE",
                              "Concession conversion is only allowed in phases 2‑4.")

    player = state.players.get(player_id)
    if player is None or abbr not in player.concessions:
        raise ConcessionError("ERR_NOT_HELD",
                              f"Player does not hold the concession {abbr}.")

    major = state.majors.get(abbr)
    if major is None or major.floated:
        raise ConcessionError("ERR_ALREADY_STARTED",
                              f"Major company {abbr} is already floated.")

    if player.loans != 0:
        raise ConcessionError("ERR_LOANS",
                              "Player has outstanding loans.")

    if must_sell(state, player_id):
        raise ConcessionError("ERR_MUST_SELL",
                              "Player must sell shares first (over certificate limit).")

    if start_price not in MAJOR_START_PRICES:
        raise ConcessionError("ERR_BAD_START_PRICE",
                              f"Start price {start_price} is not a valid major start price.")

    if abbr != _LNWR:
        cost_to_player = 2 * start_price - 100
        if player.cash < cost_to_player:
            raise ConcessionError("ERR_INSUFFICIENT_CASH",
                                  "Insufficient cash to pay for the conversion.")
    # LNWR check: player pays nothing, so always enough cash.

    # ── Mutations (atomic after validation) ─────────────────────────────────
    # 4.7.2: Remove concession from player's concessions
    player.concessions.remove(abbr)

    # Set director holder
    major.director_player_id = player_id

    # Add director's certificate units to player's shares
    units = cert_units(abbr)  # 2 for standard, 1 for LNWR
    player.shares[abbr] = player.shares.get(abbr, 0) + units

    # 4.7.2: Place start token (call turn_order.place_start_token)
    place_start_token(state, abbr, start_price, kind='major')

    # Cash movements
    if abbr != _LNWR:
        # non‑LNWR: bank receives 100, player pays (2*start_price - 100)
        state.bank.cash -= 100
        player.cash -= (2 * start_price - 100)
        major.treasury = 2 * start_price
    else:
        # LNWR: bank pays start_price into treasury, player pays nothing
        state.bank.cash -= start_price
        major.treasury = start_price

    # 3.3.2: Treasury and pool – 8 ordinary certs (9 for LNWR), pool 0
    treasury_units = 9 if abbr == _LNWR else 8
    major.shares_in_treasury = treasury_units
    major.shares_in_bank_pool = 0

    # 4.7.6: Mark floated and has_operated false
    major.floated = True
    major.has_operated = False

    # R6 / GA07: Set sale_happened flag (idempotent)
    state.any_sale_this_stock_round = True

    # 10.1.1: Check game‑end triggers after bank payment
    check_game_end_triggers(state, context="after_bank_payment")

# Alias
convert_concession_to_director = convert_concession

# ── minor_start_price (aliased as start_price_for_minor) ─────────────────────

def minor_start_price(phase: int, bid: int) -> int:
    """Starting share price of a purchased minor."""
    if phase == 1:
        return 50
    half = bid // 2
    # Choose the largest start value <= half, clamped to [50,100]
    candidates = [v for v in MINOR_START_PRICES if v <= half]
    if candidates:
        return max(candidates)
    # If half < 50, return minimum 50
    return 50

start_price_for_minor = minor_start_price

# ── minor_start_treasury ─────────────────────────────────────────────────────

def minor_start_treasury(phase: int, bid: int, price: int | None = None) -> int:
    """Cash a purchased minor receives upon flotation."""
    if price is None:
        price = minor_start_price(phase, bid)
    if phase == 1:
        return 100
    if phase == 2:
        return 2 * price
    # phase >= 3
    return bid

# ── minor_float_order ───────────────────────────────────────────────────────

def minor_float_order(pending: Iterable[tuple[int, int, int, str]]) -> list[tuple[int, int, int, str]]:
    """Sort pending minors by descending bid, tie‑break by lower box index."""
    return sorted(pending, key=lambda t: (-t[1], t[2]))

# ── float_minors (aliased as float_minor_companies) ─────────────────────────

def float_minors(state, pending: Iterable[tuple[int, int, int, str]] | None = None) -> None:
    """Float purchased minor companies.

    pending is an iterable of (minor_number, bid, box_index, buyer_player_id).
    If None or empty, this is a no‑op.
    """
    if pending is None:
        return

    # Lazy imports for cross‑module calls.
    from .turn_order import place_start_token
    from .scoring import check_game_end_triggers

    # Sort pending into float order
    sorted_pending = minor_float_order(pending)

    for minor_number, bid, box_index, buyer_id in sorted_pending:
        cid = f"M{minor_number}"
        minor = state.minors.get(cid)
        if minor is None:
            # Should never happen in a well‑formed state, but guard.
            continue

        # Compute price and treasury for the current phase.
        price = minor_start_price(state.phase, bid)
        treasury = minor_start_treasury(state.phase, bid, price)

        # 4.11.5: Place start token (kind='minor')
        place_start_token(state, cid, price, kind='minor')

        # R3: Bank pays treasury to company; buyer already paid bid to bank during resolution.
        state.bank.cash -= treasury
        minor.treasury = treasury

        # Mark minor as floated
        minor.director_player_id = buyer_id
        minor.share_price = price
        minor.floated = True

    # GA25/GB21: Call game‑end triggers once after all flotations.
    check_game_end_triggers(state, context="after_bank_payment")

float_minor_companies = float_minors
