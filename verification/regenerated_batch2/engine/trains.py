"""Train purchase, phase advancement, rusting and train limits (rules 2.1.x, 5.13.x, 3.4.5).

Pool bookkeeping: ``state.bank.train_pool`` is keyed by pool ("L" covers the double-sided L/2
cards, "7" covers 7/E, plus "3", "4", "5", "6"); the value is the number of NEW cards left.
Trains owned by companies are stored as code strings in ``company.trains``.
Trains discarded (rule 2.1.4) go to ``state.bank.discarded_trains`` (the bank pool).
"""
from __future__ import annotations

from app.data.phases import PHASES_BY_NUMBER
from app.data.trains import L_TO_2_UPGRADE_COST, TRAIN_TYPES_BY_CODE

from .models import GameState
from .stock_positions import descending_price_key

TRAIN_ORDER = ["L", "3", "4", "5", "6", "7"]

# code of a train -> pool key it is drawn from
_POOL_OF = {"L": "L", "2": "L", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "E": "7"}
# code of a train -> the phase its first purchase triggers
_PHASE_OF = {"L": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "E": 7}


class TrainError(Exception):
    """Raised for an illegal train purchase / upgrade; message is user-facing."""


def current_buyable_pool(state: GameState) -> str | None:
    """First pool, in train order, that still has new trains left (rule 5.13.4)."""
    for key in TRAIN_ORDER:
        if state.bank.train_pool.get(key, 0) > 0:
            return key
    return None


def _company(state: GameState, company_id: str, kind: str):
    if kind == "minor":
        comp = state.minors.get(company_id)
        if comp is None or comp.removed or not comp.floated:
            raise TrainError(f"Minor company {company_id} is not in operation.")
    elif kind == "major":
        comp = state.majors.get(company_id)
        if comp is None or not comp.floated:
            raise TrainError(f"Major company {company_id} is not floated.")
    else:
        raise TrainError(f"Unknown company kind {kind!r}.")
    return comp


def _limit(state: GameState, kind: str, phase: int | None = None) -> int:
    ph = PHASES_BY_NUMBER[phase if phase is not None else state.phase]
    return ph.minor_train_limit if kind == "minor" else ph.major_train_limit


def _check_game_end(state: GameState) -> None:
    from .scoring import check_game_end_triggers  # lazy: avoid import cycles

    check_game_end_triggers(state)


def buy_train_from_bank(state: GameState, company_id: str, kind: str, want_code: str) -> int:
    """Buy one train at face value from the bank. Returns the price paid."""
    comp = _company(state, company_id, kind)
    want_code = str(want_code).upper() if want_code is not None else ""
    if want_code not in _POOL_OF:
        raise TrainError(f"Unknown train type {want_code!r}.")
    cost = TRAIN_TYPES_BY_CODE[want_code].cost

    # Rusted sides can no longer be bought (L from phase 3, 2 from phase 4).
    if want_code == "L" and state.phase >= 3:
        raise TrainError("L-trains have rusted.")
    if want_code == "2" and state.phase >= 4:
        raise TrainError("2-trains have rusted.")

    # 5.13.6 / 5.13.7: must be below the limit BEFORE buying.
    limit = _limit(state, kind)
    if len(comp.trains) >= limit:
        raise TrainError(f"{company_id} is at its train limit ({limit}).")
    # 5.13.11
    if want_code == "E" and "E" in comp.trains:
        raise TrainError(f"{company_id} already owns an E-train.")
    if comp.treasury < cost:
        raise TrainError(f"{company_id} cannot afford a {want_code}-train (costs {cost}).")

    pool = current_buyable_pool(state)
    from_pool_bank = (
        pool is not None and _POOL_OF[want_code] == pool
    )
    if from_pool_bank:
        # New train from the bank (5.13.4: in order; L/2 and 7/E sides chosen by buyer).
        state.bank.train_pool[pool] -= 1
        comp.treasury -= cost
        state.bank.cash += cost
        comp.trains.append(want_code)
        _advance_phase_and_rust(state, want_code)
        _enforce_train_limits(state)
    elif want_code in state.bank.discarded_trains:
        # A train from the bank pool (previously discarded): face value, no phase effect.
        state.bank.discarded_trains.remove(want_code)
        comp.treasury -= cost
        state.bank.cash += cost
        comp.trains.append(want_code)
    else:
        raise TrainError(
            f"A {want_code}-train is not available; trains must be bought in order "
            f"(next: {pool})."
        )

    state.log.append(f"{company_id} bought a {want_code}-train for {cost}.")
    _check_game_end(state)
    return cost


def upgrade_l_to_2(state: GameState, company_id: str, kind: str) -> int:
    """Rule 5.13.9: flip an L-train to a 2-train for 80 in phases 1 and 2."""
    comp = _company(state, company_id, kind)
    if state.phase not in (1, 2):
        raise TrainError("L-trains can only be upgraded to 2-trains in phases 1 and 2.")
    if "L" not in comp.trains:
        raise TrainError(f"{company_id} owns no L-train to upgrade.")
    cost = L_TO_2_UPGRADE_COST
    if comp.treasury < cost:
        raise TrainError(f"{company_id} cannot afford the upgrade (costs {cost}).")
    comp.treasury -= cost
    state.bank.cash += cost
    comp.trains[comp.trains.index("L")] = "2"
    _advance_phase_and_rust(state, "2")
    _enforce_train_limits(state)
    state.log.append(f"{company_id} upgraded an L-train to a 2-train for {cost}.")
    _check_game_end(state)
    return cost


def _rust(state: GameState, code: str) -> None:
    """Remove a train type from the game (2.1.3)."""
    for m in state.minors.values():
        m.trains = [t for t in m.trains if t != code]
    for j in state.majors.values():
        j.trains = [t for t in j.trains if t != code]
    state.bank.discarded_trains = [t for t in state.bank.discarded_trains if t != code]
    # New cards of that type leave the bank. L/2 share the "L" pool: rusting the L side
    # leaves the cards (they can still be bought as 2s); rusting the 2 side removes them.
    if code == "L":
        return
    if code == "2":
        state.bank.train_pool["L"] = 0
        if "2" in state.bank.train_pool:
            state.bank.train_pool["2"] = 0
    elif code in state.bank.train_pool:
        state.bank.train_pool[code] = 0
    state.log.append(f"{code}-trains rusted.")


def _advance_phase_and_rust(state: GameState, bought_code: str) -> None:
    """Advance the phase for the first purchase of a train type; rust; apply concession ruling."""
    target = _PHASE_OF.get(bought_code)
    if target is None:
        raise TrainError(f"Unknown train type {bought_code!r}.")
    old = state.phase
    if target <= old:
        return
    for p in range(old + 1, target + 1):
        state.phase = p
        rusted = PHASES_BY_NUMBER[p].trains_rusted
        if rusted:
            _rust(state, rusted)
        if p == 5:
            _remove_concessions(state)
        state.log.append(f"Phase {p} begins.")


def _remove_concessions(state: GameState) -> None:
    """Rule 3.4.5 + contract ruling: unconverted concessions leave play at phase 5."""
    for player in state.players.values():
        player.concessions = []
    state.concession_bid_boxes = [None for _ in state.concession_bid_boxes]


def _enforce_train_limits(state: GameState) -> None:
    """Rules 2.1.4/2.1.5: discard excess trains (oldest first); companies in descending share price."""
    entries: list[tuple[str, str, object]] = []
    for cid, m in state.minors.items():
        if m.floated and not m.removed:
            entries.append((cid, "minor", m))
    for cid, j in state.majors.items():
        if j.floated:
            entries.append((cid, "major", j))

    def key(e):
        cid = e[0]
        if cid in state.stock_positions:
            return (0, descending_price_key(state, cid))
        return (1, (0, 0, 0))

    for cid, kind, comp in sorted(entries, key=key):
        limit = _limit(state, kind)
        while len(comp.trains) > limit:
            gone = comp.trains.pop(0)  # oldest first
            state.bank.discarded_trains.append(gone)
            state.log.append(f"{cid} discarded a {gone}-train (train limit {limit}).")
