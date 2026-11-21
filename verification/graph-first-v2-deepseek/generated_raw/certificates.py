"""Certificates module for 1822 board-game rules engine.

This module implements certificate-related logic: counting certificates,
determining sale legality, director swaps, and limit checks.
"""
from __future__ import annotations

from typing import NamedTuple

from app.engine.models import GameState


class CertificateError(Exception):
    """Single exception class for the certificates module.

    Message format: '<ERR_CODE>: <text>'
    Attribute .code holds the ERR_CODE string.
    """
    def __init__(self, code: str, text: str) -> None:
        self.code = code
        super().__init__(f"{code}: {text}")


TOTAL_UNITS = 10
"""Total units (10%) per major company."""

POOL_CAP_UNITS = 5
"""Maximum units the bank pool can hold."""

HOLD_CAP_UNITS = 6
"""Maximum units a single player may hold in one company."""


class SaleCheck(NamedTuple):
    """Result of a sale legality check.

    Fields:
        legal: True if the sale is allowed.
        swap_needed: True if the sale forces a director swap.
        successor: The player who would become director, or None.
        reason: None if legal, else an error code string.
    """
    legal: bool
    swap_needed: bool
    successor: str | None
    reason: str | None = None


def cert_units(company_id: str) -> int:
    """Return the number of 10% units the director's certificate represents.

    LNWR = 1, all other majors = 2.
    """
    return 1 if company_id == 'LNWR' else 2


def ordinary_certs(state: GameState, player_id: str, company_id: str) -> int:
    """Return the number of ordinary 10% certificates a player holds.

    Excludes the director's certificate units.
    """
    units = state.players[player_id].shares.get(company_id, 0)
    if company_id in state.majors:
        major = state.majors[company_id]
        if major.director_player_id == player_id:
            return units - cert_units(company_id)
    return units


def units_held(state: GameState, player_id: str, company_id: str) -> int:
    """Return the total 10% units a player holds in a company.

    Includes the director's certificate units if the player is director.
    """
    return state.players[player_id].shares.get(company_id, 0)


def certs_held(state: GameState, player_id: str, company_id: str) -> int:
    """Return the number of certificate cards a player holds.

    For majors: ordinary_certs + (1 if director).
    For minors: 1 if director else 0.
    Raises CertificateError for unknown companies.
    """
    if company_id in state.majors:
        major = state.majors[company_id]
        ord_certs = ordinary_certs(state, player_id, company_id)
        if major.director_player_id == player_id:
            return ord_certs + 1
        return ord_certs
    elif company_id in state.minors:
        minor = state.minors[company_id]
        return 1 if minor.director_player_id == player_id else 0
    else:
        raise CertificateError("ERR_UNKNOWN_COMPANY",
                               f"Unknown company: {company_id}")


def cert_limit(state: GameState) -> int:
    """Return the certificate limit for the current player count."""
    from app.data.setup import SETUP_BY_PLAYER_COUNT
    n = len(state.player_order)
    return SETUP_BY_PLAYER_COUNT[n].certificate_limit


def cert_count_holdings(state: GameState, player_id: str) -> int:
    """Return certificates held that count toward the limit.

    Yellow-zone companies count 0; privates and concessions count 1 each.
    """
    total = 0
    # Majors
    for cid in state.majors:
        from app.engine.turn_order import in_yellow
        if not in_yellow(state, cid):
            total += certs_held(state, player_id, cid)
    # Minors
    for cid in state.minors:
        from app.engine.turn_order import in_yellow
        if not in_yellow(state, cid):
            total += certs_held(state, player_id, cid)
    # Privates
    player = state.players[player_id]
    total += len(player.private_companies)
    # Concessions
    total += len(player.concessions)
    return total


def cert_count(state: GameState, player_id: str) -> int:
    """Return total certificates including items led (bidding)."""
    from app.engine.bidding import items_led
    return cert_count_holdings(state, player_id) + items_led(state, player_id)


def over_limit(state: GameState, player_id: str) -> bool:
    """Return True if the player holds more certificates than the limit."""
    return cert_count(state, player_id) > cert_limit(state)


def successor(state: GameState, company_id: str, director_id: str,
              remaining_units: int) -> str | None:
    """Return the player who would become director if the current director
    sells down to remaining_units.

    Candidates must hold >= cert_units and more than remaining_units.
    Ties are broken by nearest after the director in player order (cyclic).
    Returns None if no candidate exists.
    """
    cu = cert_units(company_id)
    candidates = []
    for pid in state.players:
        if pid == director_id:
            continue
        u = units_held(state, pid, company_id)
        if u >= cu and u > remaining_units:
            candidates.append((u, pid))
    if not candidates:
        return None
    max_units = max(c[0] for c in candidates)
    tied = [pid for u, pid in candidates if u == max_units]
    if len(tied) == 1:
        return tied[0]
    # Tie-break: nearest after director in player_order (cyclic forward)
    order = state.player_order
    try:
        dir_idx = order.index(director_id)
    except ValueError:
        return None
    for i in range(1, len(order) + 1):
        idx = (dir_idx + i) % len(order)
        if order[idx] in tied:
            return order[idx]
    return None


def sale_legal(state: GameState, player_id: str, company_id: str,
               count: int = 1) -> SaleCheck:
    """Check whether a sale of `count` shares is legal.

    Returns a SaleCheck; never raises for illegal sales.
    """
    # Must be a started major
    if company_id not in state.majors:
        return SaleCheck(False, False, None, "ERR_NOT_SELLABLE")
    major = state.majors[company_id]
    if not major.floated or not major.has_operated:
        return SaleCheck(False, False, None, "ERR_NOT_SELLABLE")
    # Pool capacity
    if major.shares_in_bank_pool + count > POOL_CAP_UNITS:
        return SaleCheck(False, False, None, "ERR_POOL_FULL")
    ord_certs = ordinary_certs(state, player_id, company_id)
    held = units_held(state, player_id, company_id)
    director = major.director_player_id
    if player_id != director:
        # Non-director: can sell up to ordinary_certs
        if count > ord_certs:
            return SaleCheck(False, False, None, "ERR_TOO_MANY")
        return SaleCheck(True, False, None, None)
    else:
        # Director
        if count <= ord_certs:
            # Selling only ordinary certificates
            return SaleCheck(True, False, None, None)
        else:
            # Selling some director certificates
            if count > held:
                return SaleCheck(False, False, None, "ERR_TOO_MANY")
            remaining = held - count
            succ = successor(state, company_id, player_id, remaining)
            if succ is None:
                return SaleCheck(False, False, None, "ERR_TOO_MANY")
            return SaleCheck(True, True, succ, None)


def can_sell_any(state: GameState, player_id: str) -> bool:
    """Return True if the player can legally sell at least one share
    in any floated major company."""
    for cid in state.majors:
        if sale_legal(state, player_id, cid, 1).legal:
            return True
    return False


def must_sell(state: GameState, player_id: str) -> bool:
    """Return True if the player is over the limit and can sell something."""
    return over_limit(state, player_id) and can_sell_any(state, player_id)


def fully_sold(state: GameState, company_id: str) -> bool:
    """Return True if a floated major has zero treasury and zero pool shares.

    Minors and unknown companies return False.
    """
    if company_id in state.majors:
        major = state.majors[company_id]
        return (major.floated and
                major.shares_in_treasury == 0 and
                major.shares_in_bank_pool == 0)
    return False


def swap_director(state: GameState, company_id: str,
                  new_director_id: str) -> None:
    """Swap the director's certificate to a new player.

    Raises CertificateError if the swap is not legal.
    Does not change any Player.shares value.
    """
    if company_id not in state.majors:
        raise CertificateError("ERR_NOT_STARTED",
                               f"Company {company_id} not started")
    major = state.majors[company_id]
    if major.director_player_id is None:
        raise CertificateError("ERR_NOT_STARTED",
                               f"Company {company_id} has no director")
    if major.director_player_id == new_director_id:
        raise CertificateError("ERR_SAME_DIRECTOR",
                               f"{new_director_id} is already director")
    cu = cert_units(company_id)
    if ordinary_certs(state, new_director_id, company_id) < cu:
        raise CertificateError(
            "ERR_NOT_ENOUGH_ORDINARY",
            f"{new_director_id} does not hold enough ordinary certificates")
    # Perform the swap: only the director_player_id changes.
    # ordinary_certs is derived from Player.shares and the director flag,
    # so no share values are modified.
    major.director_player_id = new_director_id
