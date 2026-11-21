"""Trains module for 1822 board-game rules engine.

Layer 4: may import from turn_order (layer 1) at module level;
must lazy-import from bidding (layer 6) inside functions.
"""
from __future__ import annotations

from typing import Iterable

from app.data.phases import PHASES_BY_NUMBER
from app.data.trains import TRAIN_TYPES_BY_CODE
from app.engine.turn_order import descending_order

from .models import GameState


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class TrainError(Exception):
    """Single exception class for the trains module."""
    def __init__(self, code: str, text: str) -> None:
        self.code = code
        super().__init__(f"{code}: {text}")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRAIN_PHASE: dict[str, int] = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 'E': 7,
}
"""Phase triggered by the first train of a type. 'L' deliberately absent."""

TRAIN_GROUPS: tuple[tuple[str, ...], ...] = (
    ('L', '2'),
    ('3',),
    ('4',),
    ('5',),
    ('6',),
    ('7', 'E'),
)
"""Deck groups in buying order; double-sided groups are one physical pool."""

SCAN_ORDER: tuple[str, ...] = ('L', '2', '3', '4', '5', '6', '7', 'E')
"""front_train scan order."""

EXPORT_L_ONLY: str = 'L_only'
"""export_train mode for 4.11.6."""

EXPORT_NEXT_WITH_PHASE: str = 'next_with_phase'
"""export_train mode for 4.11.7."""

MAX_E_TRAINS_PER_COMPANY: int = 1
"""Maximum number of E-trains a company may own (5.13.11)."""


# ---------------------------------------------------------------------------
# Helper / derived functions
# ---------------------------------------------------------------------------

def phase_of_train(code: str) -> int | None:
    """Phase triggered by the first train of a type.

    Returns TRAIN_PHASE.get(code); None for 'L' and unknown codes.
    """
    return TRAIN_PHASE.get(code)


def front_train(state: GameState) -> str | None:
    """First code in SCAN_ORDER with a positive count in the bank deck."""
    for code in SCAN_ORDER:
        if state.bank.train_pool.get(code, 0) > 0:
            return code
    return None


def deck_remaining(state: GameState, group: tuple[str, ...]) -> int:
    """Sum of train_pool counts over the group's codes."""
    return sum(state.bank.train_pool.get(code, 0) for code in group)


def front_group(state: GameState) -> tuple[str, ...] | None:
    """First group of TRAIN_GROUPS with remaining > 0, else None."""
    for group in TRAIN_GROUPS:
        if deck_remaining(state, group) > 0:
            return group
    return None


next_train_group = front_group  # alias


def train_group(code: str) -> tuple[str, ...]:
    """Deck group a train code belongs to.

    Raises TrainError if code is unknown.
    """
    for group in TRAIN_GROUPS:
        if code in group:
            return group
    raise TrainError('ERR_UNKNOWN_TRAIN', f"Unknown train code: {code!r}")


def train_cost(code: str) -> int:
    """Face value of a train type.

    Raises TrainError if code is unknown.
    """
    if code not in TRAIN_TYPES_BY_CODE:
        raise TrainError('ERR_UNKNOWN_TRAIN', f"Unknown train code: {code!r}")
    return TRAIN_TYPES_BY_CODE[code].cost


def train_limit(kind: str, phase: int) -> int:
    """Number of trains a company may own in a given phase.

    Raises TrainError if kind is not 'major' or 'minor'.
    """
    if kind not in ('major', 'minor'):
        raise TrainError('ERR_UNKNOWN_COMPANY', f"Unknown company kind: {kind!r}")
    phase_data = PHASES_BY_NUMBER[phase]
    return phase_data.major_train_limit if kind == 'major' else phase_data.minor_train_limit


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def rust_trains(state: GameState, code: str) -> None:
    """Remove every train of a rusted type from the game without compensation.

    Removes from all company train lists, the bank pool, and the deck counts.
    Unknown code is a no-op.
    """
    # Remove from all major companies
    for company in state.majors.values():
        company.trains = [t for t in company.trains if t != code]
    # Remove from all minor companies
    for company in state.minors.values():
        company.trains = [t for t in company.trains if t != code]
    # Remove from bank pool
    state.bank.discarded_trains = [t for t in state.bank.discarded_trains if t != code]
    # Remove from deck
    state.bank.train_pool[code] = 0


rust = rust_trains  # alias


def discard_excess_trains(state: GameState) -> None:
    """Companies above the train limit discard the excess into the bank pool.

    Discard order: descending share price order of companies; within a company,
    lowest face value first (INTERIM decision DN02).
    """
    # Collect all companies that own trains
    company_ids: list[str] = []
    for cid in state.majors:
        if state.majors[cid].trains:
            company_ids.append(cid)
    for cid in state.minors:
        if state.minors[cid].trains:
            company_ids.append(cid)

    if not company_ids:
        return

    # Order by descending share price
    order = descending_order(state, company_ids)

    for cid in order:
        if cid in state.majors:
            company = state.majors[cid]
            kind = 'major'
        else:
            company = state.minors[cid]
            kind = 'minor'
        limit = train_limit(kind, state.phase)
        while len(company.trains) > limit:
            # Discard the cheapest train (lowest face value)
            company.trains.sort(key=lambda t: train_cost(t))
            discarded = company.trains.pop(0)
            state.bank.discarded_trains.append(discarded)


enforce_train_limit = discard_excess_trains  # alias


def phase_check(state: GameState, code: str) -> None:
    """Advance the phase if this is the first train of its type and apply
    phase effects at once: rust, train-limit discard, concession clearing.

    Unknown code or a code that does not raise the phase is a no-op.
    """
    new_phase = phase_of_train(code)
    if new_phase is None or new_phase <= state.phase:
        return

    old = state.phase
    state.phase = new_phase

    # Rust for every skipped phase (including the new one)
    for p in range(old + 1, new_phase + 1):
        rusted = PHASES_BY_NUMBER[p].trains_rusted
        if rusted is not None:
            rust_trains(state, rusted)

    # Count total trains before discard for audit log
    total_before = (
        sum(len(c.trains) for c in state.majors.values())
        + sum(len(c.trains) for c in state.minors.values())
    )

    # Discard excess trains
    discard_excess_trains(state)

    total_after = (
        sum(len(c.trains) for c in state.majors.values())
        + sum(len(c.trains) for c in state.minors.values())
    )
    discarded_count = total_before - total_after

    # Clear concessions if crossing phase 5
    if old < 5 <= new_phase:
        from app.engine.bidding import clear_concession_boxes
        clear_concession_boxes(state)

    # Build audit log line
    rusted_codes: list[str] = []
    for p in range(old + 1, new_phase + 1):
        rc = PHASES_BY_NUMBER[p].trains_rusted
        if rc:
            rusted_codes.append(rc)
    rusted_str = ','.join(rusted_codes) if rusted_codes else '-'
    or_per_sr = PHASES_BY_NUMBER[new_phase].operating_rounds_per_stock_round

    state.phase_events.append(
        f"PHASE_EVENT from={old} to={new_phase} "
        f"rusted={rusted_str} discarded={discarded_count} or_per_sr={or_per_sr}"
    )


advance_phase = phase_check  # alias
check_phase = phase_check    # alias


def export_train(state: GameState, mode: str) -> None:
    """Remove a train from the bank deck (not the pool); exported trains
    leave the game.

    Raises TrainError if mode is invalid. An empty deck is a no-op.
    """
    if mode not in (EXPORT_L_ONLY, EXPORT_NEXT_WITH_PHASE):
        raise TrainError('ERR_BAD_MODE', f"Invalid export mode: {mode!r}")

    front = front_train(state)
    if front is None:
        return  # deck empty, no action

    if mode == EXPORT_L_ONLY:
        # Only act if the front group is L/2
        if front in ('L', '2'):
            group = ('L', '2')
            for c in group:
                if state.bank.train_pool.get(c, 0) > 0:
                    state.bank.train_pool[c] -= 1
                    break
            # No phase check (4.11.6 / R7)
    else:  # EXPORT_NEXT_WITH_PHASE
        group = front_group(state)
        if group is None:
            return
        # Determine effective type for phase check
        if group == ('L', '2'):
            effective = '2'
        elif group == ('7', 'E'):
            effective = '7'
        else:
            effective = group[0]  # single-code group
        # Remove one card from the group
        for c in group:
            if state.bank.train_pool.get(c, 0) > 0:
                state.bank.train_pool[c] -= 1
                break
        phase_check(state, effective)


def buy_train_from_bank(
    state: GameState,
    company_id: str,
    kind: str,
    code: str,
    source: str | None = None,
) -> None:
    """A company buys one train from the bank at face value.

    Raises TrainError on any precondition violation. Does NOT require the
    company to be floated (callers are responsible for round/active checks).
    """
    # 1. Validate company existence
    if kind not in ('major', 'minor'):
        raise TrainError('ERR_UNKNOWN_COMPANY', f"Unknown company kind: {kind!r}")
    if kind == 'major':
        if company_id not in state.majors:
            raise TrainError('ERR_UNKNOWN_COMPANY', f"Major company {company_id!r} not found")
        company = state.majors[company_id]
    else:
        if company_id not in state.minors:
            raise TrainError('ERR_UNKNOWN_COMPANY', f"Minor company {company_id!r} not found")
        company = state.minors[company_id]

    # 2. Validate train code
    if code not in TRAIN_PHASE and code != 'L':
        raise TrainError('ERR_UNKNOWN_TRAIN', f"Unknown train code: {code!r}")

    # 3. Validate source
    if source not in (None, 'new', 'pool'):
        raise TrainError('ERR_BAD_SOURCE', f"Invalid source: {source!r}")

    # 4. Train limit (before buying)
    limit = train_limit(kind, state.phase)
    if len(company.trains) >= limit:
        raise TrainError('ERR_TRAIN_LIMIT',
                         f"{company_id} already at train limit {limit}")

    # 5. E-train limit
    if code == 'E' and 'E' in company.trains:
        raise TrainError('ERR_E_LIMIT',
                         f"{company_id} already owns an E-train")

    # Determine effective source if None
    if source is None:
        if train_group(code) == front_group(state):
            source = 'new'
        else:
            source = 'pool'

    # 6. Source-specific checks
    if source == 'new':
        if train_group(code) != front_group(state):
            raise TrainError('ERR_NOT_NEXT_TRAIN',
                             f"Cannot buy {code!r} as new train; not the front group")
    else:  # 'pool'
        if state.phase < 3:
            raise TrainError('ERR_NOT_IN_POOL',
                             "Pool trains can only be bought from phase 3 onwards")
        if code not in state.bank.discarded_trains:
            raise TrainError('ERR_NOT_IN_POOL',
                             f"{code!r} is not in the bank pool")

    # 7. Sufficient funds
    cost = train_cost(code)
    if company.treasury < cost:
        raise TrainError('ERR_INSUFFICIENT_FUNDS',
                         f"{company_id} treasury £{company.treasury} < cost £{cost}")

    # --- Mutations ---
    company.treasury -= cost
    state.bank.cash += cost

    if source == 'new':
        # Remove one card from the group (decrement first non-zero code)
        group = train_group(code)
        for c in group:
            if state.bank.train_pool.get(c, 0) > 0:
                state.bank.train_pool[c] -= 1
                break
    else:
        # Remove from bank pool
        state.bank.discarded_trains.remove(code)

    company.trains.append(code)

    # Phase check for new trains only
    if source == 'new':
        phase_check(state, code)


def upgrade_l_train(state: GameState, company_id: str, kind: str) -> None:
    """Upgrade an L-train to a 2-train for £80 in phases 1-2.

    Counts as a train purchase and can start phase 2.
    Raises TrainError on any precondition violation.
    """
    # 1. Validate company existence
    if kind not in ('major', 'minor'):
        raise TrainError('ERR_UNKNOWN_COMPANY', f"Unknown company kind: {kind!r}")
    if kind == 'major':
        if company_id not in state.majors:
            raise TrainError('ERR_UNKNOWN_COMPANY', f"Major company {company_id!r} not found")
        company = state.majors[company_id]
    else:
        if company_id not in state.minors:
            raise TrainError('ERR_UNKNOWN_COMPANY', f"Minor company {company_id!r} not found")
        company = state.minors[company_id]

    # 2. Phase must be 1 or 2
    if state.phase > 2:
        raise TrainError('ERR_PHASE',
                         "L-to-2 upgrade only allowed in phases 1-2")

    # 3. Company must own an L-train
    if 'L' not in company.trains:
        raise TrainError('ERR_NO_L_TRAIN',
                         f"{company_id} has no L-train to upgrade")

    # 4. Sufficient funds
    cost = 80  # L_TO_2_UPGRADE_COST
    if company.treasury < cost:
        raise TrainError('ERR_INSUFFICIENT_FUNDS',
                         f"{company_id} treasury £{company.treasury} < £{cost}")

    # --- Mutations ---
    company.treasury -= cost
    state.bank.cash += cost

    # Replace one L with 2
    idx = company.trains.index('L')
    company.trains[idx] = '2'

    # Phase check (counts as a train purchase)
    phase_check(state, '2')


upgrade_l_to_2 = upgrade_l_train  # alias
