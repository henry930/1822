"""Bidding boxes, bidding tokens and stock-round resolution (contract/bidding.md)."""
from __future__ import annotations

from app.data.setup import SETUP_BY_PLAYER_COUNT

from . import certificates, company_formation, scoring, shares, trains, turn_order
from .models import BidBoxItem, GameState

FACE_VALUES: dict[str, int] = {"concession": 100, "minor": 100, "private": 0}
BID_MULTIPLE = 5
MAX_BIDS_PER_TURN = 3

_KINDS = ("minor", "concession", "private")
_KIND_ORDER = {"minor": 0, "concession": 1, "private": 2}


class BidError(Exception):
    pass


def _err(code: str, text: str) -> BidError:
    return BidError(f"{code}: {text}")


def _boxes(state: GameState, kind: str) -> list:
    if kind == "concession":
        return state.concession_bid_boxes
    if kind == "minor":
        return state.minor_bid_boxes
    return state.private_bid_boxes


def _all_items(state: GameState):
    for kind in _KINDS:
        for item in _boxes(state, kind):
            if item is not None:
                yield item


# ---------------------------------------------------------------- derived

def face_value(kind: str) -> int:
    return FACE_VALUES[kind]


def highest_bid(item: BidBoxItem) -> int | None:
    if item.bids:
        return max(item.bids.values())
    return None


def highest_bidder(item: BidBoxItem) -> str | None:
    if not item.bids:
        return None
    return max(item.bids.items(), key=lambda kv: kv[1])[0]


def committed_money(state: GameState, pid: str) -> int:
    total = 0
    for item in _all_items(state):
        if highest_bidder(item) == pid:
            total += highest_bid(item)
    return total


def items_led(state: GameState, pid: str) -> int:
    return sum(1 for item in _all_items(state) if highest_bidder(item) == pid)


def tokens_total(state: GameState) -> int:
    return SETUP_BY_PLAYER_COUNT[len(state.player_order)].bidding_tokens


def tokens_used(state: GameState, pid: str) -> int:
    return sum(1 for item in _all_items(state) if pid in item.bids)


def min_legal_bid(item: BidBoxItem) -> int:
    if not item.bids:
        return face_value(item.kind)
    return highest_bid(item) + BID_MULTIPLE


def bid_amount_valid(state: GameState, pid: str, item: BidBoxItem, amount: int) -> bool:
    if isinstance(amount, bool) or not isinstance(amount, int):
        return False
    if amount % BID_MULTIPLE != 0:
        return False
    if amount < min_legal_bid(item):
        return False
    return committed_money(state, pid) + amount <= state.players[pid].cash


def item_resolution_order(state: GameState) -> list[tuple[str, int]]:
    entries: list[tuple[int, int, int, str]] = []
    for kind in _KINDS:
        for idx, item in enumerate(_boxes(state, kind)):
            if item is not None and item.bids:
                entries.append((-highest_bid(item), idx, _KIND_ORDER[kind], kind))
    entries.sort()
    return [(kind, idx) for _neg, idx, _k, kind in entries]


# ---------------------------------------------------------------- bidding

def place_or_move_bid(state: GameState, player_id: str, kind: str, box_index: int, amount: int) -> None:
    p = player_id
    # 1
    if kind not in FACE_VALUES:
        raise _err("ERR_ITEM_NOT_IN_BOX", f"unknown item kind {kind!r}")
    boxes = _boxes(state, kind)
    if isinstance(box_index, bool) or not isinstance(box_index, int) or not (0 <= box_index < len(boxes)):
        raise _err("ERR_ITEM_NOT_IN_BOX", "no such box")
    item = boxes[box_index]
    if item is None:
        raise _err("ERR_ITEM_NOT_IN_BOX", "that box is empty")
    if kind == "concession" and state.phase >= 5:
        raise _err("ERR_ITEM_NOT_IN_BOX", "concessions can no longer be bid on (phase 5 or later)")
    # 2
    if state.bids_this_turn >= MAX_BIDS_PER_TURN:
        raise _err("ERR_TOO_MANY_BIDS", "at most 3 bids per turn")
    player = state.players[p]
    # 3
    if player.loans != 0:
        raise _err("ERR_LOANS", "you cannot bid while you have loans")
    # 4
    if certificates.must_sell(state, p):
        raise _err("ERR_MUST_SELL", "you are over the certificate limit and must sell first")
    # 5
    if certificates.cert_count(state, p) >= certificates.cert_limit(state):
        raise _err("ERR_CERT_LIMIT", "you are at the certificate limit")
    # 6
    if not bid_amount_valid(state, p, item, amount):
        raise _err(
            "ERR_BAD_AMOUNT",
            f"bid must be a multiple of {BID_MULTIPLE}, at least {min_legal_bid(item)}, "
            "and affordable together with your other leading bids",
        )
    moving = p in item.bids
    if not moving:
        # 7
        if tokens_used(state, p) >= tokens_total(state):
            raise _err("ERR_NO_TOKENS", "you have no bidding tokens left")
    else:
        # 8
        if highest_bidder(item) == p:
            raise _err("ERR_NOT_OUTBID", "you already lead this item")
    item.bids[p] = amount


# ---------------------------------------------------------------- boxes

def shift_boxes(state: GameState) -> None:
    for kind in _KINDS:
        boxes = _boxes(state, kind)
        n = len(boxes)
        items = [b for b in boxes if b is not None]
        boxes[:] = items + [None] * (n - len(items))


def refill_boxes(state: GameState) -> None:
    shift_boxes(state)
    for kind in _KINDS:
        if kind == "concession" and state.phase >= 5:
            continue
        stack = {
            "minor": state.minor_stack,
            "concession": state.concession_stack,
            "private": state.private_stack,
        }[kind]
        boxes = _boxes(state, kind)
        for i in range(len(boxes)):
            if boxes[i] is None:
                if not stack:
                    break
                boxes[i] = BidBoxItem(kind=kind, ref=stack.pop(0), bids={})


def clear_concession_boxes(state: GameState) -> None:
    n = len(state.concession_bid_boxes) or 3
    state.concession_bid_boxes[:] = [None] * n
    state.concession_stack.clear()
    for player in state.players.values():
        player.concessions = []
    for major in state.majors.values():
        major.concession_holder_player_id = None


def vacate_box_item(state: GameState, kind: str, box_index: int, disposition: str,
                    player_id: str | None = None) -> None:
    if kind not in FACE_VALUES:
        raise _err("ERR_ITEM_NOT_IN_BOX", f"unknown item kind {kind!r}")
    boxes = _boxes(state, kind)
    if not (0 <= box_index < len(boxes)) or boxes[box_index] is None:
        raise _err("ERR_ITEM_NOT_IN_BOX", "that box is empty")
    if disposition not in ("award", "remove"):
        raise _err("ERR_BAD_DISPOSITION", f"unknown disposition {disposition!r}")
    if disposition == "award" and player_id is None:
        raise _err("ERR_BAD_DISPOSITION", "award requires a player")
    item = boxes[box_index]
    boxes[box_index] = None
    ref = item.ref
    if disposition == "award":
        if kind == "concession":
            state.players[player_id].concessions.append(ref)
            if ref in state.majors:
                state.majors[ref].concession_holder_player_id = player_id
        elif kind == "private":
            state.players[player_id].private_companies.append(ref)
            if ref in state.privates:
                state.privates[ref].owner_player_id = player_id
        else:
            state.minors[f"M{ref}"].director_player_id = player_id
    else:
        if kind == "minor":
            state.minors[f"M{ref}"].removed = True


# ---------------------------------------------------------------- resolution

def resolve_bids(state: GameState) -> tuple[set, list]:
    items_with_bids: set[tuple[str, int]] = set()
    for kind in _KINDS:
        for idx, item in enumerate(_boxes(state, kind)):
            if item is not None and item.bids:
                items_with_bids.add((kind, idx))
    pending: list[tuple[int, int, int, str]] = []
    for kind, idx in item_resolution_order(state):
        item = _boxes(state, kind)[idx]
        if item is None:
            continue
        for bidder, amount in sorted(item.bids.items(), key=lambda kv: -kv[1]):
            player = state.players[bidder]
            if player.cash >= amount:
                player.cash -= amount
                state.bank.cash += amount
                ref = item.ref
                vacate_box_item(state, kind, idx, "award", bidder)
                state.any_sale_this_stock_round = True
                if kind == "minor":
                    pending.append((ref, amount, idx, bidder))
                break
    for kind in _KINDS:
        for item in _boxes(state, kind):
            if item is not None:
                item.bids = {}
    return items_with_bids, pending


def unsold_minor_exports(state: GameState, items_with_bids) -> None:
    unsold = [
        idx for idx, item in enumerate(state.minor_bid_boxes)
        if item is not None and ("minor", idx) not in items_with_bids
    ]
    for _ in unsold:
        trains.export_train(state, "L_only")


def remove_box1_minor_and_export(state: GameState) -> None:
    if not state.minor_bid_boxes or state.minor_bid_boxes[0] is None:
        return
    vacate_box_item(state, "minor", 0, "remove")
    trains.export_train(state, "next_with_phase")


def resolve_stock_round(state: GameState) -> None:
    from .round_manager import sr_over

    if not sr_over(state):
        raise _err("ERR_NOT_OVER", "the stock round is not over yet")
    items_with_bids, pending = resolve_bids(state)
    company_formation.float_minors(state, pending)
    unsold_minor_exports(state, items_with_bids)
    remove_box1_minor_and_export(state)
    refill_boxes(state)
    shares.charge_interest(state)
    turn_order.raise_sold_out_prices(state)
    turn_order.reorder_players_by_cash(state)
    scoring.check_game_end_triggers(state, "end_of_stock_round")
