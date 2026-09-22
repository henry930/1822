"""Train purchases (rule 5.13), phase advancement, and rusting (section 2).

Scope for this pass: buying from the bank only. Buying from another
company (rule 5.13.3) and forced/emergency-money-raising purchases (rule
5.14-5.15, when a company can't afford a train it's required to buy) are
not implemented yet - buy_train_from_bank simply raises if the company
can't afford it, rather than forcing a share sale or loan.
"""
from __future__ import annotations

from app.data.phases import PHASES_BY_NUMBER
from app.data.trains import L_TO_2_UPGRADE_COST, TRAIN_TYPES_BY_CODE

from .models import GameState

# Bank purchase order: L/2 share one pool (buyer picks the side), likewise 7/E.
# rule 5.13.4: no train may be bought until every train of the previous type
# has been bought or exported.
TRAIN_ORDER = ["L", "3", "4", "5", "6", "7"]
_POOL_KEY_FOR_CODE = {"L": "L", "2": "L", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "E": "7"}
_PHASE_TRIGGERED_BY_CODE = {"L": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "E": 7}


class TrainError(Exception):
    pass


def current_buyable_pool(state: GameState) -> str | None:
    for pool_key in TRAIN_ORDER:
        if state.bank.train_pool.get(pool_key, 0) > 0:
            return pool_key
    return None


def _company(state: GameState, company_id: str, kind: str):
    return state.minors[company_id] if kind == "minor" else state.majors[company_id]


def buy_train_from_bank(state: GameState, company_id: str, kind: str, want_code: str) -> int:
    pool_key = _POOL_KEY_FOR_CODE.get(want_code)
    if pool_key is None:
        raise TrainError(f"Unknown train code {want_code!r}.")
    current = current_buyable_pool(state)
    if current is None or pool_key != current:
        raise TrainError(f"{want_code} trains are not currently available from the bank (rule 5.13.4).")

    cost = TRAIN_TYPES_BY_CODE[want_code].cost
    company = _company(state, company_id, kind)
    if company.treasury < cost:
        raise TrainError("Insufficient treasury funds (forced/emergency purchase not yet implemented).")

    company.treasury -= cost
    state.bank.cash += cost
    company.trains.append(want_code)
    state.bank.train_pool[current] -= 1

    _advance_phase_and_rust(state, want_code)
    _enforce_train_limits(state)
    return cost


def upgrade_l_to_2(state: GameState, company_id: str, kind: str) -> int:
    """Rule 5.13.9: a company may flip an owned L-train to a 2-train for
    £80, at any time (not just from the bank)."""
    company = _company(state, company_id, kind)
    if "L" not in company.trains:
        raise TrainError("Company does not own an L-train to upgrade.")
    if company.treasury < L_TO_2_UPGRADE_COST:
        raise TrainError("Insufficient treasury funds for the £80 upgrade.")
    company.treasury -= L_TO_2_UPGRADE_COST
    state.bank.cash += L_TO_2_UPGRADE_COST
    company.trains.remove("L")
    company.trains.append("2")
    _advance_phase_and_rust(state, "2")
    return L_TO_2_UPGRADE_COST


def _advance_phase_and_rust(state: GameState, bought_code: str) -> None:
    new_phase = _PHASE_TRIGGERED_BY_CODE.get(bought_code)
    if new_phase is None or new_phase <= state.phase:
        return
    old_phase = state.phase
    state.phase = new_phase
    for p in range(old_phase + 1, new_phase + 1):
        rusted_code = PHASES_BY_NUMBER[p].trains_rusted
        if rusted_code:
            _rust_trains(state, rusted_code)


def _rust_trains(state: GameState, code: str) -> None:
    """Rule 2.1.3: trains of the rusted type are removed from the game
    entirely, without compensation - including any still unsold in the
    bank."""
    for minor in state.minors.values():
        minor.trains = [t for t in minor.trains if t != code]
    for major in state.majors.values():
        major.trains = [t for t in major.trains if t != code]
    pool_key = _POOL_KEY_FOR_CODE.get(code, code)
    if pool_key in state.bank.train_pool:
        state.bank.train_pool[pool_key] = 0
    state.bank.discarded_trains = [t for t in state.bank.discarded_trains if t != code]


def _enforce_train_limits(state: GameState) -> None:
    """Rule 2.1.4: if a phase change lowers the train limit, companies with
    more trains than the new limit must discard the excess to the bank
    pool without compensation. Which train(s) to discard is a company
    choice in the real rules (5.13.5 - higher-value trains kept in
    practice); this simplification always discards the oldest-bought
    train(s) first."""
    phase = PHASES_BY_NUMBER[state.phase]
    for minor in state.minors.values():
        while len(minor.trains) > phase.minor_train_limit:
            state.bank.discarded_trains.append(minor.trains.pop(0))
    for major in state.majors.values():
        while len(major.trains) > phase.major_train_limit:
            state.bank.discarded_trains.append(major.trains.pop(0))
