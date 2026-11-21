"""Bidding boxes (rules 4.10) and end-of-stock-round resolution (4.11, 4.3.4, 4.12)."""
from __future__ import annotations

from app.data.setup import SETUP_BY_PLAYER_COUNT
from app.data.stock_market import STOCK_MARKET_BY_POSITION

from . import stock_positions
from . import trains as _trains
from .certificates import certificate_count, certificate_limit
from . import shares as _shares
from .models import BidBoxItem, GameState
from .setup import _refill_bid_boxes

CONCESSION_FACE_VALUE = 100   # rule 3.4.2
PRIVATE_FACE_VALUE = 0        # rule 3.1.3
MINOR_FACE_VALUE = 100        # provisional (contract v2 item 5); the rulebook excerpt states none

BID_STEP = 5                  # rule 4.10.6
_MINOR_START_PRICES = (50, 60, 70, 80, 90, 100)

_FACE_VALUES = {
    "concession": CONCESSION_FACE_VALUE,
    "minor": MINOR_FACE_VALUE,
    "private": PRIVATE_FACE_VALUE,
}


class BidError(Exception):
    """Raised for an illegal bid."""


def _face_value(kind: str) -> int:
    try:
        return _FACE_VALUES[kind]
    except KeyError:
        raise BidError(f"Unknown bid-box kind {kind!r}.") from None


def _boxes(state: GameState, kind: str) -> list[BidBoxItem | None]:
    if kind == "concession":
        return state.concession_bid_boxes
    if kind == "minor":
        return state.minor_bid_boxes
    if kind == "private":
        return state.private_bid_boxes
    raise BidError(f"Unknown bid-box kind {kind!r}.")


def _all_items(state: GameState):
    for kind in ("concession", "minor", "private"):
        for item in _boxes(state, kind):
            if item is not None:
                yield item


def _highest(item: BidBoxItem) -> tuple[str | None, int | None]:
    if not item.bids:
        return None, None
    pid = max(item.bids, key=lambda p: item.bids[p])
    return pid, item.bids[pid]


def _committed(state: GameState, player_id: str) -> int:
    """Rule 4.10.7: sum of the bids for items on which the player has the highest bid."""
    total = 0
    for item in _all_items(state):
        pid, amt = _highest(item)
        if pid == player_id:
            total += amt
    return total


def place_or_move_bid(state: GameState, player_id: str, kind: str, box_index: int, amount: int) -> None:
    face = _face_value(kind)
    player = state.players.get(player_id)
    if player is None:
        raise BidError(f"Unknown player {player_id!r}.")
    boxes = _boxes(state, kind)

    if not isinstance(box_index, int) or isinstance(box_index, bool) or not 0 <= box_index < len(boxes):
        raise BidError(f"No such {kind} bidding box: {box_index!r}.")
    item = boxes[box_index]
    if item is None:
        raise BidError(f"{kind} bidding box {box_index + 1} is empty.")
    if not isinstance(amount, int) or isinstance(amount, bool):
        raise BidError("A bid must be a whole number of pounds.")

    if kind == "concession" and state.phase >= 5:
        raise BidError("Concessions are removed from play from Phase 5 (rule 3.4.5).")

    # 4.3.1
    if player.loans > 0:
        raise BidError("A player with outstanding loans may not place a bid (rule 4.3.1).")

    # 4.10.6
    if amount % BID_STEP != 0:
        raise BidError("Bids must be a multiple of 5 (rule 4.10.6).")
    if amount < face:
        raise BidError(f"The bid must be at least the face value of {face} (rule 4.10.6).")

    # 4.10.7 / 4.10.4: higher than all earlier bids; a player already highest may not raise.
    top_pid, top_amt = _highest(item)
    if top_pid is not None:
        if amount <= top_amt:
            raise BidError(f"The bid must be higher than the current highest bid of {top_amt} (rule 4.10.7).")
        if top_pid == player_id:
            raise BidError("You already have the highest bid on this item; a bid can only be moved "
                           "after another player has outbid it (rule 4.10.4).")

    # 4.10.3: limited number of bidding tokens
    setup = SETUP_BY_PLAYER_COUNT.get(len(state.players))
    if setup is not None and player_id not in item.bids:
        used = sum(1 for it in _all_items(state) if player_id in it.bids)
        if used >= setup.bidding_tokens:
            raise BidError("You have no unallocated bidding tokens left (rule 4.10.3).")

    # 4.4.7: a player over the certificate limit must sell first
    if _shares.must_sell_to_limit(state, player_id):
        raise BidError("You are over the certificate limit and must sell shares before bidding (rule 4.4.7).")

    # 4.10.8 / 4.2.5
    if certificate_count(state, player_id) >= certificate_limit(state):
        raise BidError("You are at the certificate limit and may not bid (rule 4.10.8).")

    # 4.10.7: committed resources must not exceed cash. (The player's own existing bid on this
    # item is not the highest, so it is not part of the committed sum.)
    if _committed(state, player_id) + amount > player.cash:
        raise BidError("The bid would commit more than your available cash (rule 4.10.7).")

    item.bids[player_id] = amount  # a moved token replaces the old bid (rule 4.10.4)
    # Bidding is not a sale for rule 10.1.1 (contract v3 ruling).


# ---------------------------------------------------------------------------
# End of the stock round
# ---------------------------------------------------------------------------

def _start_price_for_bid(bid: int) -> int:
    """Rule 4.11.4 (phase 2 and later): half the bid rounded down to a start-value space."""
    half = bid // 2
    price = _MINOR_START_PRICES[0]
    for p in _MINOR_START_PRICES:
        if p <= half:
            price = p
    return price


def _start_cell(price: int) -> tuple[int, int]:
    zone = "minor_start" if price == 50 else "start"
    for (row, col), cell in STOCK_MARKET_BY_POSITION.items():
        if cell.value == price and cell.zone == zone:
            return row, col
    raise BidError(f"No start cell for price {price}.")


def _place_minor_token(state: GameState, company_id: str, price: int) -> None:
    row, col = _start_cell(price)
    stock_positions.place_token(state, company_id, row, col)
    # Rule 4.11.5: above major tokens already on the space, beneath minors already there.
    stack = state.stock_stack[(row, col)]
    stack.remove(company_id)
    idx = 0
    for i, cid in enumerate(stack):
        if cid in state.minors:
            idx = i + 1
    stack.insert(idx, company_id)


def _float_minor(state: GameState, number: int, player_id: str, bid: int) -> None:
    cid = f"M{number}"
    minor = state.minors[cid]
    player = state.players[player_id]
    phase = state.phase
    player.cash -= bid
    if phase <= 1:
        price, treasury = 50, 100
        state.bank.cash += bid - treasury
    elif phase == 2:
        price = _start_price_for_bid(bid)
        treasury = 2 * price
        state.bank.cash += bid - treasury
    else:
        price = _start_price_for_bid(bid)
        treasury = bid  # the bid itself goes into the treasury, not to the bank
    minor.floated = True
    minor.director_player_id = player_id
    minor.share_price = price
    minor.treasury = treasury
    minor.removed = False
    player.shares[cid] = 1
    _place_minor_token(state, cid, price)
    state.log.append(f"{player_id} floated {cid} at {price} for {bid}.")


def _export_train(state: GameState, pool_key: str) -> None:
    if state.bank.train_pool.get(pool_key, 0) <= 0:
        return
    state.bank.train_pool[pool_key] -= 1
    # Phase check as for a bank purchase; an exported L/2 card counts as an L (no phase change).
    _trains._advance_phase_and_rust(state, pool_key)
    _trains._enforce_train_limits(state)


def _export_l2(state: GameState) -> None:
    """Rule 4.11.6: only an L/2 train; nothing happens if none remain."""
    _export_train(state, "L")


def _export_next(state: GameState) -> None:
    """Rule 4.11.7: the next available new train from the bank."""
    pool = _trains.current_buyable_pool(state)
    if pool is not None:
        _export_train(state, pool)


def _winner(state: GameState, item: BidBoxItem) -> tuple[str, int] | None:
    """Highest bidder who can still pay (normally always the highest bidder)."""
    for pid, amt in sorted(item.bids.items(), key=lambda kv: -kv[1]):
        if state.players[pid].cash >= amt:
            return pid, amt
    return None


def _remove_concessions_if_phase5(state: GameState) -> None:
    """Rule 3.4.5 / 2.2.8 (contract v3): from phase 5 unconverted concessions leave play."""
    if state.phase < 5:
        return
    for player in state.players.values():
        player.concessions.clear()
    state.concession_bid_boxes = [None for _ in state.concession_bid_boxes]
    state.concession_stack = []


def resolve_stock_round(state: GameState) -> None:
    _remove_concessions_if_phase5(state)  # nobody pays for a concession bid in phase 5+
    box1_minor = state.minor_bid_boxes[0] if state.minor_bid_boxes else None

    # 4.11.2: pay for and take items.  Minors are collected for flotation.
    won_minors: list[tuple[int, int, str, int, BidBoxItem]] = []  # (bid, box, pid, bid, item)
    won_items: set[int] = set()
    for kind in ("concession", "private", "minor"):
        boxes = _boxes(state, kind)
        for idx, item in enumerate(boxes):
            if item is None or not item.bids:
                continue
            res = _winner(state, item)
            if res is None:
                continue
            pid, amt = res
            player = state.players[pid]
            won_items.add(id(item))
            if kind == "concession":
                player.cash -= amt
                state.bank.cash += amt
                player.concessions.append(item.ref)
                state.majors[item.ref].concession_holder_player_id = pid
            elif kind == "private":
                player.cash -= amt
                state.bank.cash += amt
                player.private_companies.append(item.ref)
                state.privates[item.ref].owner_player_id = pid
            else:
                won_minors.append((amt, idx, pid, item.ref, item))  # paid during flotation
            boxes[idx] = None

    # 4.11.3: flotation order: highest bid first, ties by lowest box number.
    won_minors.sort(key=lambda t: (-t[0], t[1]))
    for amt, _idx, pid, number, _item in won_minors:
        _float_minor(state, number, pid, amt)

    # 4.11.6: one L/2 train exported for each minor left in the boxes with no bid on it.
    unsold_minors = [it for it in state.minor_bid_boxes if it is not None and not it.bids]
    # (a minor with an unpayable bid still stays in its box; it counts as having had a bid)
    for _ in unsold_minors:
        _export_l2(state)

    # 4.11.7: unsold minor in box 1 is removed from play and the next new train is exported.
    if box1_minor is not None and id(box1_minor) not in won_items:
        for i, it in enumerate(state.minor_bid_boxes):
            if it is box1_minor:
                state.minor_bid_boxes[i] = None
                state.minors[f"M{box1_minor.ref}"].removed = True
                state.log.append(f"M{box1_minor.ref} removed from play unsold from box 1.")
                _export_next(state)
                break

    # 4.11.2 (tokens removed) and 4.11.8: clear leftover bids, shift and refill.
    for item in _all_items(state):
        item.bids.clear()
    _refill_bid_boxes(state)
    _remove_concessions_if_phase5(state)  # phase may have advanced through exports; no refill

    # 4.3.4 / 4.11.10: 50% interest (rounded up) on outstanding loans.
    for player in state.players.values():
        if player.loans > 0:
            player.loans += (player.loans + 1) // 2

    # 4.12.1-4.12.2: fully sold major companies rise one space, in descending price order.
    sold_out = [
        abbr for abbr, m in state.majors.items()
        if m.floated and m.director_player_id is not None and abbr in state.stock_positions
        and m.shares_in_treasury == 0 and m.shares_in_bank_pool == 0
    ]
    sold_out.sort(key=lambda a: stock_positions.descending_price_key(state, a))
    for abbr in sold_out:
        row, col = state.stock_positions[abbr]
        if (row - 1, col) in STOCK_MARKET_BY_POSITION:
            stock_positions.place_token(state, abbr, row - 1, col)
