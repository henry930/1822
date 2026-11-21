"""Bid boxes, bidding and stock-round resolution (engine module 'bidding', layer 6).

Items live in state.minor_bid_boxes / concession_bid_boxes / private_bid_boxes
(lists of BidBoxItem | None). An item is identified by (kind, box_index), box_index
zero-based. Bids are BidBoxItem.bids: player_id -> amount.

Cross-module calls to lower layers are done through lazy imports so that import
order / cycles never matter.
"""
from __future__ import annotations

from typing import Iterable

from app.data.setup import SETUP_BY_PLAYER_COUNT

from .models import BidBoxItem, GameState, MinorCompanyState, PrivateCompanyState


class BidError(Exception):
    """Single exception class of the bidding module: '<ERR_CODE>: <text>', .code."""

    def __init__(self, code: str, text: str = ""):
        self.code = code
        super().__init__(f"{code}: {text}" if text else f"{code}: {code}")


FACE_VALUES = {"concession": 100, "minor": 100, "private": 0}
BID_MULTIPLE = 5
MAX_BIDS_PER_TURN = 3
ITEM_KINDS = ("minor", "concession", "private")

_BOX_ATTR = {
    "minor": "minor_bid_boxes",
    "concession": "concession_bid_boxes",
    "private": "private_bid_boxes",
}


# ---------------------------------------------------------------- helpers

def _boxes(state: GameState, kind: str) -> list:
    return getattr(state, _BOX_ATTR[kind])


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _all_items(state: GameState):
    """Yield (kind, box_index, item) for every non-empty box in kind order."""
    for kind in ITEM_KINDS:
        for i, item in enumerate(_boxes(state, kind)):
            if item is not None:
                yield kind, i, item


def _box_count(kind: str) -> int:
    from . import setup as _setup
    return {
        "minor": _setup.NUM_MINOR_BID_BOXES,
        "concession": _setup.NUM_CONCESSION_BID_BOXES,
        "private": _setup.NUM_PRIVATE_BID_BOXES,
    }[kind]


def _stack(state: GameState, kind: str) -> list:
    return {
        "minor": state.minor_stack,
        "concession": state.concession_stack,
        "private": state.private_stack,
    }[kind]


# ---------------------------------------------------------------- derived values

def face_value(kind: str) -> int:
    if kind not in ITEM_KINDS:
        raise BidError("ERR_ITEM_NOT_IN_BOX", f"unknown item kind {kind!r}")
    return FACE_VALUES[kind]


def highest_bid(item: BidBoxItem) -> int | None:
    if not item.bids:
        return None
    return max(item.bids.values())


def highest_bidder(item: BidBoxItem) -> str | None:
    if not item.bids:
        return None
    best = max(item.bids.values())
    for pid, amt in item.bids.items():
        if amt == best:
            return pid
    return None


def committed_money(state: GameState, player_id: str) -> int:
    total = 0
    for _k, _i, item in _all_items(state):
        if item.bids and highest_bidder(item) == player_id:
            total += highest_bid(item)
    return total


def items_led(state: GameState, player_id: str) -> int:
    n = 0
    for _k, _i, item in _all_items(state):
        if item.bids and highest_bidder(item) == player_id:
            n += 1
    return n


def tokens_total(state: GameState) -> int:
    return SETUP_BY_PLAYER_COUNT[len(state.player_order)].bidding_tokens


def tokens_used(state: GameState, player_id: str) -> int:
    return sum(1 for _k, _i, item in _all_items(state) if player_id in item.bids)


def min_legal_bid(item: BidBoxItem) -> int:
    hb = highest_bid(item)
    if hb is None:
        return face_value(item.kind)
    return hb + BID_MULTIPLE


def bid_amount_error(state: GameState, player_id: str, item: BidBoxItem, amount: int) -> str | None:
    if not _is_int(amount) or amount % BID_MULTIPLE != 0:
        return "ERR_BAD_AMOUNT"
    if amount < min_legal_bid(item):
        return "ERR_BID_TOO_LOW"
    if committed_money(state, player_id) + amount > state.players[player_id].cash:
        return "ERR_INSUFFICIENT_CASH"
    return None


def bid_amount_valid(state: GameState, player_id: str, item: BidBoxItem, amount: int) -> bool:
    return bid_amount_error(state, player_id, item, amount) is None


def item_resolution_order(state: GameState) -> list[tuple[str, int]]:
    rows = []
    for kind_rank, kind in enumerate(ITEM_KINDS):
        for i, item in enumerate(_boxes(state, kind)):
            if item is not None and item.bids:
                rows.append((-highest_bid(item), i, kind_rank, kind))
    rows.sort()
    return [(kind, i) for (_b, i, _r, kind) in rows]


# ---------------------------------------------------------------- bidding action

def place_or_move_bid(state: GameState, player_id: str, kind: str, box_index: int, amount: int) -> None:
    from . import certificates as cert

    # 1. item exists
    if kind not in ITEM_KINDS:
        raise BidError("ERR_ITEM_NOT_IN_BOX", f"unknown item kind {kind!r}")
    boxes = _boxes(state, kind)
    if not _is_int(box_index) or not (0 <= box_index < len(boxes)) or boxes[box_index] is None:
        raise BidError("ERR_ITEM_NOT_IN_BOX", f"no {kind} item in box {box_index}")
    if kind == "concession" and state.phase >= 5:
        raise BidError("ERR_ITEM_NOT_IN_BOX", "concessions cannot be bid on from phase 5")
    item = boxes[box_index]
    player = state.players[player_id]

    # 2. bids per turn
    if state.bids_this_turn >= MAX_BIDS_PER_TURN:
        raise BidError("ERR_TOO_MANY_BIDS", "at most 3 bids per turn")
    # 3. loans
    if player.loans != 0:
        raise BidError("ERR_LOANS", "cannot bid while in debt")
    # 4. must sell
    if cert.must_sell(state, player_id):
        raise BidError("ERR_MUST_SELL", "must sell down to the certificate limit first")
    # 5. certificate limit
    if cert.cert_count(state, player_id) >= cert.cert_limit(state):
        raise BidError("ERR_CERT_LIMIT", "certificate limit reached")
    # 6. amount
    err = bid_amount_error(state, player_id, item, amount)
    if err is not None:
        raise BidError(err, f"invalid bid amount {amount!r}")
    if player_id not in item.bids:
        # 7. place
        if tokens_used(state, player_id) >= tokens_total(state):
            raise BidError("ERR_NO_TOKENS", "no unallocated bidding token left")
    else:
        # 8. move
        if highest_bidder(item) == player_id:
            raise BidError("ERR_NOT_OUTBID", "you already hold the highest bid on this item")

    item.bids[player_id] = amount


place_bid = place_or_move_bid
move_bid = place_or_move_bid


# ---------------------------------------------------------------- boxes

def shift_boxes(state: GameState) -> None:
    for kind in ITEM_KINDS:
        n = max(_box_count(kind), len(_boxes(state, kind)))
        items = [b for b in _boxes(state, kind) if b is not None]
        items += [None] * (n - len(items))
        setattr(state, _BOX_ATTR[kind], items)


def refill_boxes(state: GameState) -> None:
    shift_boxes(state)
    for kind in ITEM_KINDS:
        if kind == "concession" and state.phase >= 5:
            state.concession_stack.clear()
            continue
        boxes = _boxes(state, kind)
        stack = _stack(state, kind)
        for i in range(len(boxes)):
            if not stack:
                break
            if boxes[i] is None:
                boxes[i] = BidBoxItem(kind=kind, ref=stack.pop(0))


def clear_concession_boxes(state: GameState) -> None:
    n = max(_box_count("concession"), len(state.concession_bid_boxes))
    state.concession_bid_boxes = [None] * n
    state.concession_stack.clear()
    for p in state.players.values():
        p.concessions.clear()
    for m in state.majors.values():
        if not m.concession_converted:
            m.concession_holder_player_id = None


def vacate_box_item(state: GameState, kind: str, box_index: int, disposition: str,
                    player_id: str | None = None) -> None:
    boxes = _boxes(state, kind) if kind in ITEM_KINDS else []
    if not _is_int(box_index) or not (0 <= box_index < len(boxes)) or boxes[box_index] is None:
        raise BidError("ERR_ITEM_NOT_IN_BOX", f"no {kind} item in box {box_index}")
    if disposition not in ("award", "remove"):
        raise BidError("ERR_BAD_DISPOSITION", f"bad disposition {disposition!r}")
    if disposition == "award" and (player_id is None or player_id not in state.players):
        raise BidError("ERR_BAD_DISPOSITION", "award needs a valid player_id")

    item = boxes[box_index]
    boxes[box_index] = None
    ref = item.ref
    if disposition == "award":
        player = state.players[player_id]
        if kind == "concession":
            if ref not in player.concessions:
                player.concessions.append(ref)
            if ref in state.majors:
                state.majors[ref].concession_holder_player_id = player_id
        elif kind == "private":
            if ref not in player.private_companies:
                player.private_companies.append(ref)
            ps = state.privates.get(ref)
            if ps is None:
                ps = state.privates[ref] = PrivateCompanyState(number=ref)
            ps.owner_player_id = player_id
        else:  # minor
            key = f"M{ref}"
            ms = state.minors.get(key)
            if ms is None:
                ms = state.minors[key] = MinorCompanyState(number=ref, company_id=key)
            ms.director_player_id = player_id
    else:
        if kind == "minor":
            key = f"M{ref}"
            ms = state.minors.get(key)
            if ms is None:
                ms = state.minors[key] = MinorCompanyState(number=ref, company_id=key)
            ms.removed = True


# ---------------------------------------------------------------- resolution

def resolve_bids(state: GameState):
    items_with_bids = {(k, i) for k, i, item in _all_items(state) if item.bids}
    pending: list[tuple[int, int, int, str]] = []
    order = item_resolution_order(state)
    for kind, idx in order:
        item = _boxes(state, kind)[idx]
        if item is None or not item.bids:
            continue
        for bidder, amount in sorted(item.bids.items(), key=lambda kv: -kv[1]):
            player = state.players.get(bidder)
            if player is None or player.cash < amount:
                continue
            player.cash -= amount
            state.bank.cash += amount
            ref = item.ref
            vacate_box_item(state, kind, idx, "award", bidder)
            state.any_sale_this_stock_round = True
            if kind == "minor":
                pending.append((ref, amount, idx, bidder))
            break
    for _k, _i, item in _all_items(state):
        item.bids = {}
    return items_with_bids, pending


def unsold_minor_exports(state: GameState, items_with_bids: Iterable[tuple[str, int]] = ()) -> None:
    from . import trains
    mode = getattr(trains, "EXPORT_L_ONLY", "L_only")
    had = set(items_with_bids)
    todo = [i for i, item in enumerate(state.minor_bid_boxes)
            if item is not None and ("minor", i) not in had]
    for _ in todo:
        trains.export_train(state, mode)


def remove_box1_minor_and_export(state: GameState) -> None:
    if not state.minor_bid_boxes or state.minor_bid_boxes[0] is None:
        return
    from . import trains
    mode = getattr(trains, "EXPORT_NEXT_WITH_PHASE", "next_with_phase")
    vacate_box_item(state, "minor", 0, "remove")
    trains.export_train(state, mode)


def resolve_stock_round(state: GameState) -> None:
    from . import company_formation, shares, turn_order, scoring

    items_with_bids, pending = resolve_bids(state)
    company_formation.float_minors(state, pending)
    unsold_minor_exports(state, items_with_bids)
    remove_box1_minor_and_export(state)
    refill_boxes(state)
    shares.charge_interest(state)
    turn_order.raise_sold_out_prices(state)
    turn_order.reorder_players_by_cash(state)
    scoring.check_game_end_triggers(state, "end_of_stock_round")
