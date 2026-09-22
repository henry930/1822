"""Bidding (rule 4.10) and end-of-stock-round resolution (rule 4.11).

Simplification for this pass: a "bid" action processes 1-3 bid placements/
moves as a single atomic player turn (rule 4.1.3's "up to three bids" choice
C), then ends the turn. Combining a sell/loan-repayment step with a bid in
the same turn (rule 4.1.3's steps A/B before C) isn't wired up yet - each
turn is currently either a bid action or a pass.
"""
from __future__ import annotations

from app.data.minor_companies import MINOR_COMPANIES_BY_NUMBER
from app.data.private_companies import PRIVATE_COMPANIES_BY_NUMBER
from app.data.setup import SETUP_BY_PLAYER_COUNT
from app.data.stock_market import STOCK_MARKET_BY_POSITION
from app.data.trains import TRAIN_TYPES_BY_CODE

from . import setup as setup_module
from .certificates import certificate_count, certificate_limit
from .models import BidBoxItem, GameState
from .stock_positions import place_token

CONCESSION_FACE_VALUE = 100  # rule 3.4.2
PRIVATE_FACE_VALUE = 0       # rule 3.1.3
MINOR_FACE_VALUE = 0         # not stated explicitly; minors have no listed face value,
                              # unlike concessions (£100) and privates (£0) - assumed £0
                              # pending confirmation against the physical bid boxes.


class BidError(Exception):
    pass


def _face_value(kind: str) -> int:
    return {"concession": CONCESSION_FACE_VALUE, "minor": MINOR_FACE_VALUE, "private": PRIVATE_FACE_VALUE}[kind]


def _boxes(state: GameState, kind: str) -> list[BidBoxItem | None]:
    return {
        "concession": state.concession_bid_boxes,
        "minor": state.minor_bid_boxes,
        "private": state.private_bid_boxes,
    }[kind]


def _player_bid_item_count(state: GameState, player_id: str) -> int:
    """How many distinct items the player currently has any bid on - capped
    by their bidding token allotment (rule 4.10.3)."""
    count = 0
    for kind in ("concession", "minor", "private"):
        for item in _boxes(state, kind):
            if item is not None and player_id in item.bids:
                count += 1
    return count


def _committed_resources(state: GameState, player_id: str) -> int:
    """Rule 4.10.7: sum of bid amounts for items where the player currently
    holds the highest bid."""
    total = 0
    for kind in ("concession", "minor", "private"):
        for item in _boxes(state, kind):
            if item is None or not item.bids:
                continue
            top_bidder = max(item.bids, key=lambda pid: item.bids[pid])
            if top_bidder == player_id:
                total += item.bids[player_id]
    return total


def place_or_move_bid(state: GameState, player_id: str, kind: str, box_index: int, amount: int) -> None:
    if kind not in ("concession", "minor", "private"):
        raise BidError(f"Unknown bid kind: {kind!r}")
    boxes = _boxes(state, kind)
    if not (0 <= box_index < len(boxes)) or boxes[box_index] is None:
        raise BidError("No item in that bid box.")
    item = boxes[box_index]

    if amount % 5 != 0:
        raise BidError("Bids must be in whole multiples of £5.")

    existing = item.bids.get(player_id)
    if existing is None:
        current_top = max(item.bids.values()) if item.bids else 0
        min_amount = max(_face_value(kind), current_top + 5 if item.bids else _face_value(kind))
        if amount < min_amount:
            raise BidError(f"Opening bid must be at least £{min_amount}.")
        if _player_bid_item_count(state, player_id) >= SETUP_BY_PLAYER_COUNT[len(state.players)].bidding_tokens:
            raise BidError("No bidding tokens left.")
    else:
        current_top = max(item.bids.values())
        if amount <= current_top:
            raise BidError(f"Bid must exceed the current highest bid of £{current_top}.")

    if certificate_count(state, player_id) >= certificate_limit(state):
        raise BidError("At certificate limit.")

    hypothetical_committed = _committed_resources(state, player_id) - item.bids.get(player_id, 0) + amount
    if hypothetical_committed > state.players[player_id].cash:
        raise BidError("Insufficient cash for that bid given your other committed bids.")

    item.bids[player_id] = amount
    state.any_sale_this_stock_round = True  # a live bid; confirmed as a "sale" once resolved at SR end


# ---------------------------------------------------------------------------
# End-of-stock-round resolution (rule 4.11)
# ---------------------------------------------------------------------------

def resolve_stock_round(state: GameState) -> None:
    _resolve_concessions(state)
    _resolve_privates(state)
    _resolve_and_float_minors(state)
    _charge_loan_interest(state)
    setup_module._refill_bid_boxes(state)


def _winner(item: BidBoxItem) -> str | None:
    if not item.bids:
        return None
    return max(item.bids, key=lambda pid: item.bids[pid])


def _resolve_concessions(state: GameState) -> None:
    remaining: list[BidBoxItem | None] = []
    for item in state.concession_bid_boxes:
        if item is None:
            remaining.append(None)
            continue
        winner = _winner(item)
        if winner is None:
            remaining.append(item)  # unsold: stays in its box for next round
            continue
        amount = item.bids[winner]
        state.players[winner].cash -= amount
        state.players[winner].concessions.append(item.ref)
        state.majors[item.ref].concession_holder_player_id = winner
        # won items leave the bid-box stack entirely (the player now holds
        # the concession certificate directly, per rule 4.11.2)
    state.concession_bid_boxes = remaining


def _resolve_privates(state: GameState) -> None:
    remaining: list[BidBoxItem | None] = []
    for item in state.private_bid_boxes:
        if item is None:
            remaining.append(None)
            continue
        winner = _winner(item)
        if winner is None:
            remaining.append(item)
            continue
        amount = item.bids[winner]
        state.players[winner].cash -= amount
        state.players[winner].private_companies.append(item.ref)
        state.privates[item.ref].owner_player_id = winner
    state.private_bid_boxes = remaining


def _resolve_and_float_minors(state: GameState) -> None:
    box1_item = state.minor_bid_boxes[0] if state.minor_bid_boxes else None
    box1_unsold = box1_item is not None and _winner(box1_item) is None

    # Rule 4.11.3: flotation order is by sum bid, highest first; ties by lowest box number.
    winning = [
        (idx, item, _winner(item))
        for idx, item in enumerate(state.minor_bid_boxes)
        if item is not None and _winner(item) is not None
    ]
    winning.sort(key=lambda t: (-max(t[1].bids.values()), t[0]))

    for _idx, item, winner in winning:
        _float_minor(state, item.ref, winner, item.bids[winner])

    won_item_ids = {id(item) for _idx, item, _winner_id in winning}

    # Rule 4.11.6: any minor with *no bid at all* exports one L/2-train.
    for item in state.minor_bid_boxes:
        if item is not None and id(item) not in won_item_ids and not item.bids:
            _export_one_train(state)

    remaining = [
        (None if id(item) in won_item_ids else item)
        for item in state.minor_bid_boxes
    ]

    # Rule 4.11.7: if Box 1's minor specifically was unsold, remove it from play
    # and export a *second* train (on top of the generic 4.11.6 export above).
    if box1_unsold:
        state.minors[f"M{box1_item.ref}"].removed = True
        remaining = [None if item is box1_item else item for item in remaining]
        _export_one_train(state)

    state.minor_bid_boxes = remaining


def _float_minor(state: GameState, number: int, player_id: str, bid_amount: int) -> None:
    from app.data.setup import COMPANY_START_PRICES

    company_id = f"M{number}"
    minor = state.minors[company_id]
    minor.director_player_id = player_id
    minor.floated = True
    state.players[player_id].cash -= bid_amount
    state.players[player_id].shares[company_id] = 1  # whole 50% director's block, 1 unit

    if state.phase == 1:
        price = 50
        treasury = 100
    else:
        price = max(v for v in COMPANY_START_PRICES if v <= bid_amount // 2) if bid_amount >= 100 else 50
        treasury = 2 * price if state.phase == 2 else bid_amount

    minor.share_price = price
    minor.treasury = treasury
    _place_on_start_price(state, company_id, price)


def _place_on_start_price(state: GameState, company_id: str, price: int) -> None:
    for (row, col), cell in STOCK_MARKET_BY_POSITION.items():
        if cell.value == price and cell.zone in ("start", "minor_start"):
            place_token(state, company_id, row, col)
            return
    raise BidError(f"No start-price cell found for £{price}")


def _export_one_train(state: GameState) -> None:
    """Rule 4.11.6/4.11.7: export one L/2-train from the bank (not the bank
    pool). If the L/2 pool is exhausted, no action is taken."""
    if state.bank.train_pool.get("L", 0) > 0:
        state.bank.train_pool["L"] -= 1
    elif state.bank.train_pool.get("2", 0) > 0:
        state.bank.train_pool["2"] -= 1
    # exported trains are removed from the game entirely, not tracked further


def _charge_loan_interest(state: GameState) -> None:
    """Rule 4.3.4: 50% interest (rounded up) on outstanding loans at SR end."""
    import math

    for player in state.players.values():
        if player.loans > 0:
            player.loans += math.ceil(player.loans * 0.5)
