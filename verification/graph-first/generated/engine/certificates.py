from __future__ import annotations

from typing import NamedTuple

from app.data.major_companies import LNWR_ABBR
from app.data.setup import SETUP_BY_PLAYER_COUNT

from .models import GameState
from .turn_order import in_yellow

TOTAL_UNITS = 10
POOL_CAP_UNITS = 5
HOLD_CAP_UNITS = 6


class CertificateError(Exception):
    pass


class SaleCheck(NamedTuple):
    legal: bool
    swap_needed: bool
    successor: str | None


def cert_units(cid: str) -> int:
    return 1 if cid == LNWR_ABBR else 2


def _shares(state: GameState, pid: str, cid: str) -> int:
    return state.players[pid].shares.get(cid, 0)


def _director(state: GameState, cid: str) -> str | None:
    return state.majors[cid].director_player_id


def ordinary_certs(state: GameState, pid: str, cid: str) -> int:
    return _shares(state, pid, cid) - (cert_units(cid) if _director(state, cid) == pid else 0)


def units_held(state: GameState, pid: str, cid: str) -> int:
    return ordinary_certs(state, pid, cid) + (cert_units(cid) if _director(state, cid) == pid else 0)


def certs_held(state: GameState, pid: str, cid: str) -> int:
    if cid in state.minors:
        return 1 if state.minors[cid].director_player_id == pid else 0
    return ordinary_certs(state, pid, cid) + (1 if _director(state, cid) == pid else 0)


def cert_limit(state: GameState) -> int:
    return SETUP_BY_PLAYER_COUNT[len(state.player_order)].certificate_limit


def cert_count_holdings(state: GameState, pid: str) -> int:
    total = 0
    for cid in list(state.majors) + list(state.minors):
        if not in_yellow(state, cid):
            total += certs_held(state, pid, cid)
    player = state.players[pid]
    return total + len(player.private_companies) + len(player.concessions)


def cert_count(state: GameState, pid: str) -> int:
    from .bidding import items_led

    return cert_count_holdings(state, pid) + items_led(state, pid)


def over_limit(state: GameState, pid: str) -> bool:
    return cert_count(state, pid) > cert_limit(state)


def successor(state: GameState, cid: str, director_pid: str, remaining_units: int) -> str | None:
    order = list(state.player_order)
    n = len(order)
    cu = cert_units(cid)
    best: str | None = None
    best_key: tuple[int, int] | None = None
    for q in order:
        if q == director_pid:
            continue
        u = units_held(state, q, cid)
        if u >= cu and u > remaining_units:
            dist = (order.index(q) - order.index(director_pid)) % n if director_pid in order else order.index(q)
            key = (-u, dist)
            if best_key is None or key < best_key:
                best, best_key = q, key
    return best


def sale_legal(state: GameState, pid: str, cid: str, count: int) -> SaleCheck:
    if cid not in state.majors or cid in state.minors:
        return SaleCheck(False, False, None)
    m = state.majors[cid]
    s = count
    k = ordinary_certs(state, pid, cid)
    H = units_held(state, pid, cid)
    d = m.director_player_id
    swap_needed = False
    succ: str | None = None
    if d is not None and pid == d and s >= 1:
        succ = successor(state, cid, pid, H - s)
        swap_needed = succ is not None
    if s < 1 or not m.floated or not m.has_operated or m.shares_in_bank_pool + s > POOL_CAP_UNITS:
        return SaleCheck(False, swap_needed, succ if swap_needed else None)
    if pid != d:
        ok = s <= k
    else:
        ok = s <= k or (s <= H and succ is not None)
    return SaleCheck(ok, swap_needed, succ if swap_needed else None)


def can_sell_any(state: GameState, pid: str) -> bool:
    return any(sale_legal(state, pid, c, 1).legal for c in state.majors)


def must_sell(state: GameState, pid: str) -> bool:
    return over_limit(state, pid) and can_sell_any(state, pid)


def fully_sold(state: GameState, cid: str) -> bool:
    if cid in state.minors or cid not in state.majors:
        return False
    m = state.majors[cid]
    return bool(m.floated) and m.shares_in_treasury == 0 and m.shares_in_bank_pool == 0


def swap_director(state: GameState, cid: str, new_director_pid: str) -> None:
    if cid not in state.majors:
        raise CertificateError(f"ERR_NOT_ENOUGH_ORDINARY: unknown company {cid}")
    old = _director(state, cid)
    q = new_director_pid
    if q == old or q not in state.players or ordinary_certs(state, q, cid) < cert_units(cid):
        raise CertificateError(
            f"ERR_NOT_ENOUGH_ORDINARY: {q} does not hold enough ordinary shares of {cid} to become director"
        )
    state.majors[cid].director_player_id = q
