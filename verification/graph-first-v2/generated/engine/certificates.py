"""Certificates: units, certificate counting, certificate limit, sale legality, directorship."""
from __future__ import annotations

from typing import NamedTuple

from app.data.setup import SETUP_BY_PLAYER_COUNT

TOTAL_UNITS = 10
POOL_CAP_UNITS = 5
HOLD_CAP_UNITS = 6


class CertificateError(Exception):
    def __init__(self, code: str, text: str = ""):
        self.code = code
        super().__init__(f"{code}: {text}" if text else f"{code}: {code}")


class SaleCheck(NamedTuple):
    legal: bool
    swap_needed: bool
    successor: str | None
    reason: str | None = None


def cert_units(company_id: str) -> int:
    return 1 if company_id == "LNWR" else 2


def units_held(state, player_id: str, company_id: str) -> int:
    p = state.players.get(player_id)
    if p is None:
        return 0
    return p.shares.get(company_id, 0)


def ordinary_certs(state, player_id: str, company_id: str) -> int:
    held = units_held(state, player_id, company_id)
    c = state.majors.get(company_id)
    if c is not None and c.director_player_id == player_id:
        return held - cert_units(company_id)
    return held


def certs_held(state, player_id: str, company_id: str) -> int:
    if company_id in state.majors:
        c = state.majors[company_id]
        n = ordinary_certs(state, player_id, company_id)
        if c.director_player_id == player_id:
            n += 1
        return n
    if company_id in state.minors:
        return 1 if state.minors[company_id].director_player_id == player_id else 0
    raise CertificateError("ERR_UNKNOWN_COMPANY", f"unknown company {company_id!r}")


def cert_limit(state) -> int:
    return SETUP_BY_PLAYER_COUNT[len(state.player_order)].certificate_limit


def cert_count_holdings(state, player_id: str) -> int:
    from app.engine.turn_order import in_yellow  # layer 1

    total = 0
    for cid in list(state.majors) + list(state.minors):
        n = certs_held(state, player_id, cid)
        if n and not in_yellow(state, cid):
            total += n
    p = state.players.get(player_id)
    if p is not None:
        total += len(p.private_companies) + len(p.concessions)
    return total


def cert_count(state, player_id: str) -> int:
    from app.engine.bidding import items_led  # lazy: higher layer

    return cert_count_holdings(state, player_id) + items_led(state, player_id)


def over_limit(state, player_id: str) -> bool:
    return cert_count(state, player_id) > cert_limit(state)


def successor(state, company_id: str, director_id: str, remaining_units: int) -> str | None:
    need = cert_units(company_id)
    order = list(state.player_order)
    best = None
    best_units = -1
    best_dist = None
    n = len(order)
    d_idx = order.index(director_id) if director_id in order else 0
    for q in order:
        if q == director_id:
            continue
        u = units_held(state, q, company_id)
        if u < need or u <= remaining_units:
            continue
        dist = (order.index(q) - d_idx) % n if n else 0
        if u > best_units or (u == best_units and dist < best_dist):
            best, best_units, best_dist = q, u, dist
    return best


def sale_legal(state, player_id: str, company_id: str, count: int = 1) -> SaleCheck:
    c = state.majors.get(company_id)
    if c is None or c.director_player_id is None:
        return SaleCheck(False, False, None, "ERR_NOT_SELLABLE")
    s = count
    if s < 1 or not c.floated or not c.has_operated:
        return SaleCheck(False, False, None, "ERR_NOT_SELLABLE")
    if c.shares_in_bank_pool + s > POOL_CAP_UNITS:
        return SaleCheck(False, False, None, "ERR_POOL_FULL")
    d = c.director_player_id
    k = ordinary_certs(state, player_id, company_id)
    H = units_held(state, player_id, company_id)
    if player_id != d:
        if s <= k:
            return SaleCheck(True, False, None, None)
        return SaleCheck(False, False, None, "ERR_TOO_MANY")
    if s > H:
        return SaleCheck(False, False, None, "ERR_TOO_MANY")
    succ = successor(state, company_id, player_id, H - s)
    if s <= k:
        return SaleCheck(True, succ is not None, succ, None)
    if succ is not None:
        return SaleCheck(True, True, succ, None)
    return SaleCheck(False, False, None, "ERR_TOO_MANY")


def can_sell_any(state, player_id: str) -> bool:
    for cid, c in state.majors.items():
        if c.floated and sale_legal(state, player_id, cid, 1).legal:
            return True
    return False


def must_sell(state, player_id: str) -> bool:
    return over_limit(state, player_id) and can_sell_any(state, player_id)


def fully_sold(state, company_id: str) -> bool:
    c = state.majors.get(company_id)
    if c is None:
        return False
    return bool(c.floated and c.shares_in_treasury == 0 and c.shares_in_bank_pool == 0)


def swap_director(state, company_id: str, new_director_id: str) -> None:
    c = state.majors.get(company_id)
    if c is None or c.director_player_id is None:
        raise CertificateError("ERR_NOT_STARTED", f"{company_id} has no director")
    if new_director_id == c.director_player_id:
        raise CertificateError("ERR_SAME_DIRECTOR", f"{new_director_id} is already director of {company_id}")
    if ordinary_certs(state, new_director_id, company_id) < cert_units(company_id):
        raise CertificateError("ERR_NOT_ENOUGH_ORDINARY",
                               f"{new_director_id} holds too few ordinary certificates of {company_id}")
    c.director_player_id = new_director_id
