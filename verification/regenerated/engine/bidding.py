"""Bidding boxes and end-of-stock-round resolution (rules 4.10, 4.11, 4.3.4, 4.12)."""
from __future__ import annotations

import math

from app.data.phases import PHASES_BY_NUMBER
from app.data.setup import SETUP_BY_PLAYER_COUNT
from app.data.stock_market import STOCK_MARKET_BY_POSITION, STOCK_MARKET_CELLS

from .certificates import certificate_count, certificate_limit
from .models import BidBoxItem, GameState
from .setup import _refill_bid_boxes
from .stock_positions import descending_price_key, place_token
from .trains import (
    _enforce_train_limits,
    _advance_phase_and_rust,
    current_buyable_pool,
)

CONCESSION_FACE_VALUE = 100   # rule 3.4.2
PRIVATE_FACE_VALUE = 0        # rule 3.1.3
# Rulebook states no explicit minor face value; the 4.10 example ("M4 ... at face value" = 100)
# and the 4.11.4 table (lowest bid 100) imply 100. See report.
MINOR_FACE_VALUE = 100

_START_VALUES = (50, 60, 70, 80, 90, 100)


class BidError(Exception):
    pass


def _face_value(kind: str) -> int:
    if kind == "concession":
        return CONCESSION_FACE_VALUE
    if kind == "minor":
        return MINOR_FACE_VALUE
    if kind == "private":
        return PRIVATE_FACE_VALUE
    raise BidError(f"Unknown bid kind {kind!r}.")


def _boxes(state: GameState, kind: str) -> list[BidBoxItem | None]:
    return {
        "concession": state.concession_bid_boxes,
        "minor": state.minor_bid_boxes,
        "private": state.private_bid_boxes,
    }[kind]


def _all_items(state: GameState):
    for kind in ("concession", "minor", "private"):
        for item in _boxes(state, kind):
            if item is not None:
                yield item


def place_or_move_bid(state: GameState, player_id: str, kind: str, box_index: int, amount: int) -> None:
    player = state.players.get(player_id)
    if player is None:
        raise BidError(f"Unknown player {player_id!r}.")
    face = _face_value(kind)
    boxes = _boxes(state, kind)
    if not isinstance(box_index, int) or isinstance(box_index, bool) or not 0 <= box_index < len(boxes):
        raise BidError("No such bidding box.")
    item = boxes[box_index]
    if item is None:
        raise BidError("That bidding box is empty.")
    if not isinstance(amount, int) or isinstance(amount, bool):
        raise BidError("Bid must be a whole number of pounds.")
    if kind == "concession" and PHASES_BY_NUMBER[state.phase].concession_rule == "removed":
        raise BidError("Concessions are removed from play from Phase 5 (rule 3.4.5).")
    if player.loans > 0:
        raise BidError("A player with loans may not place a bid (rule 4.3.1).")
    if amount % 5 != 0:
        raise BidError("Bids must be multiples of £5 (rule 4.10.6).")
    if amount < face:
        raise BidError(f"The opening bid must be at least the face value, £{face} (rule 4.10.6).")

    top = max(item.bids.values()) if item.bids else None
    if top is not None and amount <= top:
        raise BidError("A bid must be higher than any previous bid on that item (rule 4.10.7).")
    if top is not None and item.bids.get(player_id) == top:
        raise BidError("You already hold the highest bid on that item (rule 4.10.4).")

    if certificate_count(state, player_id) >= certificate_limit(state):
        raise BidError("You are at the certificate limit (rule 4.10.8).")

    if player_id not in item.bids:
        tokens = SETUP_BY_PLAYER_COUNT[len(state.players)].bidding_tokens
        used = sum(1 for it in _all_items(state) if player_id in it.bids)
        if used >= tokens:
            raise BidError("You have no unallocated bidding tokens (rule 4.10.3).")

    committed = sum(
        max(it.bids.values()) for it in _all_items(state)
        if it.bids and it.bids.get(player_id) == max(it.bids.values())
    )
    if committed + amount > player.cash:
        raise BidError("The bid exceeds your available cash (rule 4.10.7).")

    item.bids[player_id] = amount  # a moved token replaces the old bid; bids are never withdrawn (4.10.10)
    state.any_sale_this_stock_round = True  # a bid always results in a purchase at round end


# ---------------------------------------------------------------- resolution

def _start_price_cell(price: int) -> tuple[int, int]:
    zone = "minor_start" if price == 50 else "start"
    for c in STOCK_MARKET_CELLS:
        if c.zone == zone and c.value == price:
            return (c.row, c.col)
    raise BidError(f"No start space for £{price}.")


def _minor_start(phase: int, bid: int) -> tuple[int, int]:
    """Return (start price, starting treasury) per rule 4.11.4."""
    if phase <= 1:
        return 50, 100
    price = 50
    for v in _START_VALUES:
        if 2 * v <= bid:
            price = v
    if phase == 2:
        return price, 2 * price
    return price, bid


def _place_minor_token(state: GameState, company_id: str, row: int, col: int) -> None:
    """Rule 4.11.5: on top of major tokens, beneath other minor tokens."""
    place_token(state, company_id, row, col)
    stack = state.stock_stack[(row, col)]
    stack.remove(company_id)
    idx = 0
    for i, c in enumerate(stack):
        if c in state.minors:
            idx = i + 1
    stack.insert(idx, company_id)


def _export_train(state: GameState, pool_key: str) -> None:
    state.bank.train_pool[pool_key] -= 1
    code = "L" if pool_key == "L" else pool_key
    _advance_phase_and_rust(state, code)
    _enforce_train_limits(state)


def _export_next_train(state: GameState) -> None:
    pool = current_buyable_pool(state)
    if pool is not None:
        _export_train(state, pool)


def resolve_stock_round(state: GameState) -> None:
    box1 = state.minor_bid_boxes[0] if state.minor_bid_boxes else None
    box1_unsold = box1 is not None and not box1.bids

    # 4.11.2: pay for and take concessions and privates.
    for idx, item in enumerate(state.concession_bid_boxes):
        if item is None or not item.bids:
            continue
        pid, amount = max(item.bids.items(), key=lambda kv: kv[1])
        winner = state.players[pid]
        winner.cash -= amount
        state.bank.cash += amount
        winner.concessions.append(item.ref)
        state.majors[item.ref].concession_holder_player_id = pid
        state.concession_bid_boxes[idx] = None
    for idx, item in enumerate(state.private_bid_boxes):
        if item is None or not item.bids:
            continue
        pid, amount = max(item.bids.items(), key=lambda kv: kv[1])
        winner = state.players[pid]
        winner.cash -= amount
        state.bank.cash += amount
        winner.private_companies.append(item.ref)
        state.privates[item.ref].owner_player_id = pid
        state.private_bid_boxes[idx] = None

    # 4.11.3-4.11.5: float purchased minors, highest bid first, ties by lowest box.
    sold_minors = []
    for idx, item in enumerate(state.minor_bid_boxes):
        if item is not None and item.bids:
            pid, amount = max(item.bids.items(), key=lambda kv: kv[1])
            sold_minors.append((-amount, idx, pid, item))
    sold_minors.sort(key=lambda t: (t[0], t[1]))
    phase = state.phase
    for neg_amount, idx, pid, item in sold_minors:
        amount = -neg_amount
        price, capital = _minor_start(phase, amount)
        winner = state.players[pid]
        winner.cash -= amount
        state.bank.cash += amount - capital  # capital goes to the company treasury
        cid = f"M{item.ref}"
        minor = state.minors[cid]
        minor.floated = True
        minor.director_player_id = pid
        minor.share_price = price
        minor.treasury += capital
        winner.shares[cid] = winner.shares.get(cid, 0) + 1
        row, col = _start_price_cell(price)
        _place_minor_token(state, cid, row, col)
        state.minor_bid_boxes[idx] = None

    # 4.11.6: one L/2 train exported per unsold minor.
    unsold = [it for it in state.minor_bid_boxes if it is not None]
    for _ in unsold:
        if state.bank.train_pool.get("L", 0) > 0:
            _export_train(state, "L")

    # 4.11.7: unsold minor in box 1 is removed and the next new train exported.
    if box1_unsold and state.minor_bid_boxes and state.minor_bid_boxes[0] is box1:
        state.minors[f"M{box1.ref}"].removed = True
        state.minor_bid_boxes[0] = None
        _export_next_train(state)

    # 4.11.8
    _refill_bid_boxes(state)

    # 4.3.4 / 4.11.10: 50% interest rounded up on outstanding loans.
    for p in state.players.values():
        if p.loans > 0:
            p.loans += math.ceil(p.loans * 0.5)

    # 4.12: fully player-held majors rise one space.
    risers = [
        abbr for abbr, m in state.majors.items()
        if m.floated and abbr in state.stock_positions
        and m.shares_in_treasury == 0 and m.shares_in_bank_pool == 0
    ]
    risers.sort(key=lambda a: descending_price_key(state, a))
    for abbr in risers:
        row, col = state.stock_positions[abbr]
        if (row - 1, col) in STOCK_MARKET_BY_POSITION:
            place_token(state, abbr, row - 1, col)
