"""Phase / train handling (contract/trains.md)."""
from __future__ import annotations

from .models import GameState
from ..data.phases import PHASES_BY_NUMBER
from ..data.trains import TRAIN_TYPES_BY_CODE

TRAIN_PHASE = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "E": 7}
_SCAN_ORDER = ("L", "2", "3", "4", "5", "6", "7", "E")


class TrainError(Exception):
    pass


def phase_of_train(code: str) -> int | None:
    return TRAIN_PHASE.get(code)


def front_train(state: GameState) -> str | None:
    pool = state.bank.train_pool
    for code in _SCAN_ORDER:
        if pool.get(code, 0) > 0:
            return code
    return None


def phase_check(state: GameState, code: str) -> None:
    new = phase_of_train(code)
    if new is None:
        return
    old = state.phase
    if new > old:
        state.phase = new
        ph = PHASES_BY_NUMBER[new]
        state.log.append(
            f"PHASE_EVENT from={old} to={new} rusted={ph.trains_rusted or '-'} "
            f"or_per_sr={ph.operating_rounds_per_stock_round}"
        )
        if new >= 5:
            from .bidding import clear_concession_boxes
            clear_concession_boxes(state)


def export_train(state: GameState, mode: str) -> None:
    front = front_train(state)
    if front is None:
        return
    if mode == "L_only":
        if front in ("L", "2"):
            state.bank.train_pool[front] -= 1
        return
    if mode == "next_with_phase":
        state.bank.train_pool[front] -= 1
        phase_check(state, "2" if front in ("L", "2") else front)
        return
    raise TrainError(f"ERR_TRAIN_BAD_MODE: unknown export mode {mode!r}")


def buy_train_from_bank(state: GameState, company_id: str, kind: str, code: str) -> None:
    if kind == "major":
        company = state.majors.get(company_id)
    elif kind == "minor":
        company = state.minors.get(company_id)
    else:
        raise TrainError(f"ERR_TRAIN_BAD_KIND: unknown company kind {kind!r}")
    if company is None:
        raise TrainError(f"ERR_TRAIN_NO_COMPANY: unknown company {company_id}")
    if not company.floated:
        raise TrainError(f"ERR_TRAIN_NOT_FLOATED: {company_id} has not floated")
    ttype = TRAIN_TYPES_BY_CODE.get(code)
    if ttype is None:
        raise TrainError(f"ERR_TRAIN_BAD_CODE: unknown train type {code!r}")
    if state.bank.train_pool.get(code, 0) <= 0:
        raise TrainError(f"ERR_TRAIN_NONE_LEFT: no {code}-train left in the bank")
    if company.treasury < ttype.cost:
        raise TrainError(
            f"ERR_TRAIN_FUNDS: {company_id} has {company.treasury}, a {code}-train costs {ttype.cost}")
    ph = PHASES_BY_NUMBER[state.phase]
    limit = ph.minor_train_limit if kind == "minor" else ph.major_train_limit
    if len(company.trains) >= limit:
        raise TrainError(f"ERR_TRAIN_LIMIT: {company_id} already holds {limit} trains")
    company.treasury -= ttype.cost
    state.bank.cash += ttype.cost
    state.bank.train_pool[code] -= 1
    company.trains.append(code)
    phase_check(state, code)
