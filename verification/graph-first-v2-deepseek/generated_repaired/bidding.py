# FILE: bidding.py
"""Bidding module for 1822 board-game rules engine.

Handles bid-box management, placing/moving bids, resolving stock rounds,
and all derived quantities (face values, committed money, tokens, etc.).
"""
from __future__ import annotations

from typing import Iterable

from app.engine.models import (
    BidBoxItem,
    GameState,
    MajorCompanyState,
    MinorCompanyState,
    Player,
    PrivateCompanyState,
)
from app.engine.trains import EXPORT_L_ONLY, EXPORT_NEXT_WITH_PHASE


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class BidError(Exception):
    """Single exception class for the bidding module.

    Message format: ``<ERR_CODE>: <text>``
    Attribute ``.code`` holds the error code string.
    """
    def __init__(self, code: str, text: str):
        self.code = code
        super().__init__(f"{code}: {text}")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FACE_VALUES: dict[str, int] = {"concession": 100, "minor": 100, "private": 0}
"""Face value of each item kind (concession £100, minor £100, private £0)."""

BID_MULTIPLE: int = 5
"""All bids must be whole multiples of £5."""

MAX_BIDS_PER_TURN: int = 3
"""Maximum number of bids a player may place or move in one stock turn."""

ITEM_KINDS: tuple[str, ...] = ("minor", "concession", "private")
"""Ordered kinds used for refill order and as tie-break in resolution order."""


# ---------------------------------------------------------------------------
# Helpers – box access
# ---------------------------------------------------------------------------

def _boxes_for_kind(state: GameState, kind: str) -> list[BidBoxItem | None]:
    """Return the bid-box list for the given kind."""
    if kind == "concession":
        return state.concession_bid_boxes
    elif kind == "minor":
        return state.minor_bid_boxes
    elif kind == "private":
        return state.private_bid_boxes
    else:
        raise BidError("ERR_ITEM_NOT_IN_BOX", f"Unknown kind: {kind}")


def _set_boxes_for_kind(state: GameState, kind: str, boxes: list[BidBoxItem | None]) -> None:
    """Replace the bid-box list for the given kind."""
    if kind == "concession":
        state.concession_bid_boxes = boxes
    elif kind == "minor":
        state.minor_bid_boxes = boxes
    elif kind == "private":
        state.private_bid_boxes = boxes
    else:
        raise BidError("ERR_ITEM_NOT_IN_BOX", f"Unknown kind: {kind}")


def _stack_for_kind(state: GameState, kind: str) -> list:
    """Return the stack (list) for the given kind."""
    if kind == "concession":
        return state.concession_stack
    elif kind == "minor":
        return state.minor_stack
    elif kind == "private":
        return state.private_stack
    else:
        raise BidError("ERR_ITEM_NOT_IN_BOX", f"Unknown kind: {kind}")


def _set_stack_for_kind(state: GameState, kind: str, stack: list) -> None:
    """Replace the stack for the given kind."""
    if kind == "concession":
        state.concession_stack = stack
    elif kind == "minor":
        state.minor_stack = stack
    elif kind == "private":
        state.private_stack = stack
    else:
        raise BidError("ERR_ITEM_NOT_IN_BOX", f"Unknown kind: {kind}")


# ---------------------------------------------------------------------------
# Derived quantities (drv)
# ---------------------------------------------------------------------------

def face_value(kind: str) -> int:
    """Return the face value of an item kind.

    Raises ``BidError`` with code ``ERR_ITEM_NOT_IN_BOX`` if *kind* is not
    one of ``ITEM_KINDS``.
    """
    if kind not in ITEM_KINDS:
        raise BidError("ERR_ITEM_NOT_IN_BOX", f"Unknown kind: {kind}")
    return FACE_VALUES[kind]


def highest_bid(item: BidBoxItem) -> int | None:
    """Highest bid on an item, or ``None`` if there are no bids."""
    if not item.bids:
        return None
    return max(item.bids.values())


def highest_bidder(item: BidBoxItem) -> str | None:
    """Player with the highest bid on an item, or ``None``."""
    if not item.bids:
        return None
    # In case of tie (should not happen per rules) pick the first max.
    return max(item.bids, key=item.bids.get)


def committed_money(state: GameState, player_id: str) -> int:
    """Sum of highest bids on items the player currently leads."""
    total = 0
    for boxes in (state.concession_bid_boxes, state.minor_bid_boxes, state.private_bid_boxes):
        for item in boxes:
            if item is not None and highest_bidder(item) == player_id:
                hb = highest_bid(item)
                if hb is not None:
                    total += hb
    return total


def items_led(state: GameState, player_id: str) -> int:
    """Number of items on which the player has the highest bid."""
    count = 0
    for boxes in (state.concession_bid_boxes, state.minor_bid_boxes, state.private_bid_boxes):
        for item in boxes:
            if item is not None and highest_bidder(item) == player_id:
                count += 1
    return count


def tokens_total(state: GameState) -> int:
    """Total bidding tokens each player has, based on player count."""
    from app.data.setup import SETUP_BY_PLAYER_COUNT
    n = len(state.player_order)
    return SETUP_BY_PLAYER_COUNT[n].bidding_tokens


def tokens_used(state: GameState, player_id: str) -> int:
    """Number of tokens a player currently has on items (led or outbid)."""
    count = 0
    for boxes in (state.concession_bid_boxes, state.minor_bid_boxes, state.private_bid_boxes):
        for item in boxes:
            if item is not None and player_id in item.bids:
                count += 1
    return count


def min_legal_bid(item: BidBoxItem) -> int:
    """Smallest bid currently legal on an item.

    Face value if no bids, otherwise highest bid + 5.
    """
    hb = highest_bid(item)
    if hb is None:
        return face_value(item.kind)
    return hb + BID_MULTIPLE


def bid_amount_error(state: GameState, player_id: str, item: BidBoxItem, amount: int) -> str | None:
    """Check bid amount validity.

    Returns an error code string or ``None`` if the amount is legal.
    Never raises.
    """
    # ERR_BAD_AMOUNT
    if not isinstance(amount, int) or amount % BID_MULTIPLE != 0:
        return "ERR_BAD_AMOUNT"
    # ERR_BID_TOO_LOW
    if amount < min_legal_bid(item):
        return "ERR_BID_TOO_LOW"
    # ERR_INSUFFICIENT_CASH
    if committed_money(state, player_id) + amount > state.players[player_id].cash:
        return "ERR_INSUFFICIENT_CASH"
    return None


def bid_amount_valid(state: GameState, player_id: str, item: BidBoxItem, amount: int) -> bool:
    """Thin wrapper: ``True`` iff ``bid_amount_error`` returns ``None``."""
    return bid_amount_error(state, player_id, item, amount) is None


def item_resolution_order(state: GameState) -> list[tuple[str, int]]:
    """Ordered list of ``(kind, box_index)`` for items with at least one bid.

    Sorted by (highest bid descending, box index ascending, kind order
    minor < concession < private).
    """
    items: list[tuple[str, int, BidBoxItem]] = []
    for kind in ITEM_KINDS:
        boxes = _boxes_for_kind(state, kind)
        for idx, box in enumerate(boxes):
            if box is not None and box.bids:
                items.append((kind, idx, box))
    # Sort
    def sort_key(item):
        kind, idx, box = item
        hb = highest_bid(box) or 0
        kind_order = ITEM_KINDS.index(kind)
        return (-hb, idx, kind_order)
    items.sort(key=sort_key)
    return [(kind, idx) for kind, idx, _ in items]


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def place_or_move_bid(
    state: GameState,
    player_id: str,
    kind: str,
    box_index: int,
    amount: int,
) -> None:
    """Place a new bid or move an existing bid on an item.

    If the player already has a token on the item, the bid is moved
    (the player must not be the highest bidder). Otherwise a new token
    is placed (the player must have an unallocated token).

    Raises ``BidError`` on any precondition failure (first failing check).
    """
    # --- Precondition checks (ordered, all before mutation) ---
    # 1. kind/box validity, box not None, concession only if phase < 5
    if kind not in ITEM_KINDS:
        raise BidError("ERR_ITEM_NOT_IN_BOX", f"Unknown kind: {kind}")
    boxes = _boxes_for_kind(state, kind)
    if not (0 <= box_index < len(boxes)):
        raise BidError("ERR_ITEM_NOT_IN_BOX", f"Box index {box_index} out of range for {kind}")
    item = boxes[box_index]
    if item is None:
        raise BidError("ERR_ITEM_NOT_IN_BOX", f"Box {kind}[{box_index}] is empty")
    if kind == "concession" and state.phase >= 5:
        raise BidError("ERR_ITEM_NOT_IN_BOX", "Concession boxes are closed from phase 5")

    # 2. bids_this_turn < 3
    if state.bids_this_turn >= MAX_BIDS_PER_TURN:
        raise BidError("ERR_TOO_MANY_BIDS", "Already placed 3 bids this turn")

    player = state.players.get(player_id)
    if player is None:
        raise BidError("ERR_ITEM_NOT_IN_BOX", f"Unknown player: {player_id}")

    # 3. loans == 0
    if player.loans != 0:
        raise BidError("ERR_LOANS", "Player has outstanding loans")

    # 4. not must_sell
    from app.engine.certificates import must_sell
    if must_sell(state, player_id):
        raise BidError("ERR_MUST_SELL", "Player must sell shares first")

    # 5. cert_count < cert_limit
    from app.engine.certificates import cert_count, cert_limit
    if cert_count(state, player_id) >= cert_limit(state):
        raise BidError("ERR_CERT_LIMIT", "At certificate limit")

    # 6. bid_amount_error is None
    err = bid_amount_error(state, player_id, item, amount)
    if err is not None:
        if err == "ERR_BAD_AMOUNT":
            raise BidError("ERR_BAD_AMOUNT", "Amount must be a whole multiple of 5")
        elif err == "ERR_BID_TOO_LOW":
            raise BidError("ERR_BID_TOO_LOW", f"Bid must be at least {min_legal_bid(item)}")
        elif err == "ERR_INSUFFICIENT_CASH":
            raise BidError("ERR_INSUFFICIENT_CASH", "Insufficient cash for committed money plus bid")
        else:
            raise BidError(err, "Invalid bid amount")

    # 7/8. Branch: place or move
    is_move = player_id in item.bids
    if is_move:
        # move: player must not be the highest bidder
        if highest_bidder(item) == player_id:
            raise BidError("ERR_NOT_OUTBID", "Player already leads this item")
    else:
        # place: must have an unallocated token
        if tokens_used(state, player_id) >= tokens_total(state):
            raise BidError("ERR_NO_TOKENS", "No unallocated bidding tokens left")

    # --- Mutation ---
    item.bids[player_id] = amount
    # Note: bids_this_turn is incremented by the caller (actions.py).
    # No other state changes.


# Aliases
place_bid = place_or_move_bid
move_bid = place_or_move_bid


def shift_boxes(state: GameState) -> None:
    """Compact boxes: shift items to the lowest-numbered boxes, preserving order.

    Applied per kind independently.
    """
    for kind in ITEM_KINDS:
        boxes = _boxes_for_kind(state, kind)
        # Remove None gaps, keep order
        compacted = [b for b in boxes if b is not None]
        # Pad with None to original length
        while len(compacted) < len(boxes):
            compacted.append(None)
        _set_boxes_for_kind(state, kind, compacted)


def refill_boxes(state: GameState) -> None:
    """Shift then fill empty boxes from the stacks, lowest box first.

    Concession boxes are skipped when phase >= 5 (R9).
    """
    shift_boxes(state)
    for kind in ITEM_KINDS:
        if kind == "concession" and state.phase >= 5:
            continue
        boxes = _boxes_for_kind(state, kind)
        stack = _stack_for_kind(state, kind)
        for i in range(len(boxes)):
            if boxes[i] is None:
                if not stack:
                    break
                # Pop from stack (top = first element)
                ref = stack.pop(0)
                boxes[i] = BidBoxItem(kind=kind, ref=ref, bids={})
        _set_boxes_for_kind(state, kind, boxes)
        _set_stack_for_kind(state, kind, stack)


def clear_concession_boxes(state: GameState) -> None:
    """Remove all concessions from play (phase >= 5).

    Empties concession boxes, concession stack, and all players' concession
    lists. No removal tracking is stored (models.py does not define removed_items).
    """
    # Empty boxes
    for i in range(len(state.concession_bid_boxes)):
        state.concession_bid_boxes[i] = None
    # Empty stack
    state.concession_stack.clear()
    # Clear player concessions
    for player in state.players.values():
        player.concessions.clear()
    # Clear mirror fields on majors
    for major in state.majors.values():
        if major.concession_holder_player_id is not None:
            major.concession_holder_player_id = None


def vacate_box_item(
    state: GameState,
    kind: str,
    box_index: int,
    disposition: str,
    player_id: str | None = None,
) -> None:
    """Remove an item from its box and either award it to a player or remove it.

    Parameters
    ----------
    state : GameState
    kind : str
        One of ``ITEM_KINDS``.
    box_index : int
        0-based box index.
    disposition : str
        ``'award'`` or ``'remove'``.
    player_id : str or None
        Required if disposition is ``'award'``.

    Raises ``BidError`` on invalid box or disposition.
    """
    # --- Precondition checks ---
    if kind not in ITEM_KINDS:
        raise BidError("ERR_ITEM_NOT_IN_BOX", f"Unknown kind: {kind}")
    boxes = _boxes_for_kind(state, kind)
    if not (0 <= box_index < len(boxes)):
        raise BidError("ERR_ITEM_NOT_IN_BOX", f"Box index {box_index} out of range")
    item = boxes[box_index]
    if item is None:
        raise BidError("ERR_ITEM_NOT_IN_BOX", f"Box {kind}[{box_index}] is empty")
    if disposition not in ("award", "remove"):
        raise BidError("ERR_BAD_DISPOSITION", f"Unknown disposition: {disposition}")
    if disposition == "award" and player_id is None:
        raise BidError("ERR_BAD_DISPOSITION", "Award requires a player_id")

    # --- Mutation ---
    # Remove from box
    boxes[box_index] = None
    _set_boxes_for_kind(state, kind, boxes)

    if disposition == "award":
        player = state.players.get(player_id)
        if player is None:
            raise BidError("ERR_BAD_DISPOSITION", f"Unknown player: {player_id}")
        if kind == "concession":
            # ref is a string (major abbr)
            abbr = item.ref
            player.concessions.append(abbr)
            # Update mirror on major
            if abbr in state.majors:
                state.majors[abbr].concession_holder_player_id = player_id
        elif kind == "private":
            # ref is an int (private number)
            pvt_num = item.ref
            player.private_companies.append(pvt_num)
            if pvt_num in state.privates:
                state.privates[pvt_num].owner_player_id = player_id
        elif kind == "minor":
            # ref is an int (minor number)
            minor_id = f"M{item.ref}"
            if minor_id in state.minors:
                state.minors[minor_id].director_player_id = player_id
                # floated is set later by float_minors
    else:  # remove
        if kind == "minor":
            minor_id = f"M{item.ref}"
            if minor_id in state.minors:
                state.minors[minor_id].removed = True
        # Concessions and privates: no removal tracking needed; they disappear from play.
        # The models.py does not have a removed_items field, so we don't store it.


def resolve_bids(state: GameState) -> tuple[set[tuple[str, int]], list[tuple[int, int, int, str]]]:
    """Pay and award box items.

    Returns
    -------
    items_with_bids : set of (kind, box_index)
        Every item that had at least one bid (including unpaid ones).
    pending_minor_floats : list of (minor_number, bid, box_index, buyer_player_id)
        Minors that were won and need flotation.
    """
    items_with_bids: set[tuple[str, int]] = set()
    pending_minor_floats: list[tuple[int, int, int, str]] = []

    # Snapshot items with bids before clearing
    for kind in ITEM_KINDS:
        boxes = _boxes_for_kind(state, kind)
        for idx, box in enumerate(boxes):
            if box is not None and box.bids:
                items_with_bids.add((kind, idx))

    # Process in resolution order
    order = item_resolution_order(state)
    for kind, idx in order:
        boxes = _boxes_for_kind(state, kind)
        item = boxes[idx]
        if item is None or not item.bids:
            continue
        # Sort bidders by amount descending
        bidders = sorted(item.bids.items(), key=lambda kv: -kv[1])
        winner = None
        for bidder, amount in bidders:
            player = state.players.get(bidder)
            if player is not None and player.cash >= amount:
                winner = (bidder, amount)
                break
        if winner is not None:
            bidder, amount = winner
            # Payment
            state.players[bidder].cash -= amount
            state.bank.cash += amount
            # Award item
            vacate_box_item(state, kind, idx, "award", bidder)
            # Record sale
            state.any_sale_this_stock_round = True
            # If minor, add to pending flotation
            if kind == "minor":
                # item.ref is the minor number (int)
                pending_minor_floats.append((item.ref, amount, idx, bidder))
        # If no winner, item stays in box (no sale)
        # In either case, the item had a bid and is in items_with_bids.

    # Clear all bids
    for kind in ITEM_KINDS:
        boxes = _boxes_for_kind(state, kind)
        for box in boxes:
            if box is not None:
                box.bids.clear()

    return items_with_bids, pending_minor_floats


def unsold_minor_exports(
    state: GameState,
    items_with_bids: Iterable[tuple[str, int]] = (),
) -> None:
    """Export one L/2 train for each minor box item that had no bid.

    Parameters
    ----------
    items_with_bids : iterable of (kind, box_index)
        Items that had at least one bid (from ``resolve_bids``).
    """
    items_set = set(items_with_bids)
    for idx, box in enumerate(state.minor_bid_boxes):
        if box is not None and ("minor", idx) not in items_set:
            # This minor had no bid – export a train
            from app.engine.trains import export_train
            export_train(state, EXPORT_L_ONLY)


def remove_box1_minor_and_export(state: GameState) -> None:
    """Remove the unsold minor in minor box 1 (if any) and export a train."""
    if state.minor_bid_boxes and state.minor_bid_boxes[0] is not None:
        vacate_box_item(state, "minor", 0, "remove")
        from app.engine.trains import export_train
        export_train(state, EXPORT_NEXT_WITH_PHASE)


def resolve_stock_round(state: GameState) -> None:
    """Orchestrate the end-of-stock-round procedure.

    Steps in order:
        1. resolve_bids
        2. float_minors
        3. unsold_minor_exports
        4. remove_box1_minor_and_export
        5. refill_boxes
        6. charge_interest
        7. raise_sold_out_prices
        8. reorder_players_by_cash
        9. check_game_end_triggers
    """
    # Step 1
    items_with_bids, pending = resolve_bids(state)

    # Step 2
    from app.engine.company_formation import float_minors
    float_minors(state, pending)

    # Step 3
    unsold_minor_exports(state, items_with_bids)

    # Step 4
    remove_box1_minor_and_export(state)

    # Step 5
    refill_boxes(state)

    # Step 6
    from app.engine.shares import charge_interest
    charge_interest(state)

    # Step 7
    from app.engine.turn_order import raise_sold_out_prices
    raise_sold_out_prices(state)

    # Step 8
    from app.engine.turn_order import reorder_players_by_cash
    reorder_players_by_cash(state)

    # Step 9
    from app.engine.scoring import check_game_end_triggers
    check_game_end_triggers(state, "end_of_stock_round")


# --- eval name adapter ---
_face_value = face_value
