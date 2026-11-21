"""Trains, phases, rust, train limits, exports (layer 4).

Deck = state.bank.train_pool (code -> count; L/2 and 7/E are one physical
pool each), bank pool of trains = state.bank.discarded_trains.
"""
from __future__ import annotations

from app.data.phases import PHASES_BY_NUMBER
from app.data.trains import L_TO_2_UPGRADE_COST, TRAIN_TYPES_BY_CODE

from .models import GameState


class TrainError(Exception):
    def __init__(self, code: str, text: str = ""):
        self.code = code
        super().__init__(f"{code}: {text}")


TRAIN_PHASE = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 'E': 7}
TRAIN_GROUPS = (('L', '2'), ('3',), ('4',), ('5',), ('6',), ('7', 'E'))
SCAN_ORDER = ('L', '2', '3', '4', '5', '6', '7', 'E')
EXPORT_L_ONLY = 'L_only'
EXPORT_NEXT_WITH_PHASE = 'next_with_phase'
MAX_E_TRAINS_PER_COMPANY = 1


def phase_of_train(code):
    return TRAIN_PHASE.get(code)


def front_train(state):
    pool = state.bank.train_pool
    for code in SCAN_ORDER:
        if pool.get(code, 0) > 0:
            return code
    return None


def deck_remaining(state, group):
    pool = state.bank.train_pool
    return sum(pool.get(c, 0) for c in group)


def front_group(state):
    for g in TRAIN_GROUPS:
        if deck_remaining(state, g) > 0:
            return g
    return None


next_train_group = front_group


def train_group(code):
    for g in TRAIN_GROUPS:
        if code in g:
            return g
    raise TrainError("ERR_UNKNOWN_TRAIN", f"unknown train code {code!r}")


def train_cost(code):
    t = TRAIN_TYPES_BY_CODE.get(code)
    if t is None:
        raise TrainError("ERR_UNKNOWN_TRAIN", f"unknown train code {code!r}")
    return t.cost


def train_limit(kind, phase):
    if kind not in ("major", "minor"):
        raise TrainError("ERR_UNKNOWN_COMPANY", f"unknown company kind {kind!r}")
    p = PHASES_BY_NUMBER[phase]
    return p.minor_train_limit if kind == "minor" else p.major_train_limit


# ---------------------------------------------------------------- helpers

def _company(state, company_id, kind):
    if kind not in ("major", "minor"):
        raise TrainError("ERR_UNKNOWN_COMPANY", f"unknown company kind {kind!r}")
    d = state.minors if kind == "minor" else state.majors
    c = d.get(company_id)
    if c is None:
        raise TrainError("ERR_UNKNOWN_COMPANY", f"unknown {kind} company {company_id!r}")
    return c


def _take_from_group(state, group):
    """Decrement the first non-zero code of the group; return that code."""
    pool = state.bank.train_pool
    for c in group:
        if pool.get(c, 0) > 0:
            pool[c] -= 1
            return c
    return None


# ------------------------------------------------------------------ rust

def rust_trains(state, code):
    for c in state.majors.values():
        c.trains[:] = [t for t in c.trains if t != code]
    for c in state.minors.values():
        c.trains[:] = [t for t in c.trains if t != code]
    state.bank.discarded_trains[:] = [t for t in state.bank.discarded_trains if t != code]
    if code in state.bank.train_pool:
        state.bank.train_pool[code] = 0


rust = rust_trains


# --------------------------------------------------------------- discard

def discard_excess_trains(state):
    owners = [(cid, "minor", c) for cid, c in state.minors.items() if c.trains]
    owners += [(cid, "major", c) for cid, c in state.majors.items() if c.trains]
    info = {cid: (kind, c) for cid, kind, c in owners}
    ids = [cid for cid, _, _ in owners]
    with_token = [cid for cid in ids if cid in state.stock_positions]
    without = [cid for cid in ids if cid not in state.stock_positions]
    from .turn_order import descending_order
    order = list(descending_order(state, with_token)) + without
    for cid in order:
        kind, c = info[cid]
        limit = train_limit(kind, state.phase)
        while len(c.trains) > limit:
            # lowest face value first (DN02, INTERIM)
            idx = min(range(len(c.trains)), key=lambda i: TRAIN_TYPES_BY_CODE[c.trains[i]].cost)
            state.bank.discarded_trains.append(c.trains.pop(idx))


enforce_train_limit = discard_excess_trains


# ----------------------------------------------------------- phase check

def phase_check(state, code):
    new = phase_of_train(code)
    if new is None or new <= state.phase:
        return
    old = state.phase
    state.phase = new
    rusted = []
    for p in range(old + 1, new + 1):
        rc = PHASES_BY_NUMBER[p].trains_rusted
        if rc:
            rust_trains(state, rc)
            rusted.append(rc)
    before = len(state.bank.discarded_trains)
    discard_excess_trains(state)
    discarded = len(state.bank.discarded_trains) - before
    if old < 5 <= new:
        from .bidding import clear_concession_boxes
        clear_concession_boxes(state)
    state.log.append(
        f"PHASE_EVENT from={old} to={new} rusted={','.join(rusted) if rusted else '-'} "
        f"discarded={discarded} or_per_sr={PHASES_BY_NUMBER[new].operating_rounds_per_stock_round}"
    )


advance_phase = phase_check
check_phase = phase_check


# ---------------------------------------------------------------- export

def export_train(state, mode):
    if mode not in (EXPORT_L_ONLY, EXPORT_NEXT_WITH_PHASE):
        raise TrainError("ERR_BAD_MODE", f"unknown export mode {mode!r}")
    g = front_group(state)
    if g is None:
        return
    if mode == EXPORT_L_ONLY:
        if g == TRAIN_GROUPS[0]:
            _take_from_group(state, g)
        return
    _take_from_group(state, g)
    effective = '2' if g == TRAIN_GROUPS[0] else g[0]
    phase_check(state, effective)


# ------------------------------------------------------------------- buy

def buy_train_from_bank(state, company_id, kind, code, source=None):
    comp = _company(state, company_id, kind)
    if code not in TRAIN_PHASE and code != 'L':
        raise TrainError("ERR_UNKNOWN_TRAIN", f"unknown train code {code!r}")
    if source not in (None, 'new', 'pool'):
        raise TrainError("ERR_BAD_SOURCE", f"bad source {source!r}")
    if len(comp.trains) >= train_limit(kind, state.phase):
        raise TrainError("ERR_TRAIN_LIMIT", f"{company_id} is at its train limit")
    if code == 'E' and 'E' in comp.trains:
        raise TrainError("ERR_E_LIMIT", f"{company_id} already owns an E-train")
    group = train_group(code)
    fg = front_group(state)
    use_new = (source == 'new') or (source is None and group == fg)
    if use_new:
        if group != fg:
            raise TrainError("ERR_NOT_NEXT_TRAIN", f"{code} is not in the front group")
    else:
        if code not in state.bank.discarded_trains or state.phase < 3:
            raise TrainError("ERR_NOT_IN_POOL", f"{code} is not available in the bank pool")
    cost = train_cost(code)
    if comp.treasury < cost:
        raise TrainError("ERR_INSUFFICIENT_FUNDS", f"{company_id} cannot afford {cost}")
    # all checks passed: mutate
    comp.treasury -= cost
    state.bank.cash += cost
    if use_new:
        _take_from_group(state, group)
        comp.trains.append(code)
        phase_check(state, code)
    else:
        state.bank.discarded_trains.remove(code)
        comp.trains.append(code)


# --------------------------------------------------------------- upgrade

def upgrade_l_train(state, company_id, kind):
    comp = _company(state, company_id, kind)
    if state.phase > 2:
        raise TrainError("ERR_PHASE", "L-trains can only be upgraded in phases 1-2")
    if 'L' not in comp.trains:
        raise TrainError("ERR_NO_L_TRAIN", f"{company_id} owns no L-train")
    if comp.treasury < L_TO_2_UPGRADE_COST:
        raise TrainError("ERR_INSUFFICIENT_FUNDS", f"{company_id} cannot afford {L_TO_2_UPGRADE_COST}")
    comp.treasury -= L_TO_2_UPGRADE_COST
    state.bank.cash += L_TO_2_UPGRADE_COST
    comp.trains[comp.trains.index('L')] = '2'
    phase_check(state, '2')


upgrade_l_to_2 = upgrade_l_train
