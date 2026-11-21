"""Bidding boxes and end-of-stock-round resolution (rules 4.10, 4.11, 4.3.4, 4.12).

Conventions
-----------
* ``box_index`` is the 0-based list index into ``state.<kind>_bid_boxes`` (index 0 = box 1).
* ``BidBoxItem.bids`` maps player_id -> that player's current bidding-token value on the item
  (one token per player per item, so a "move" simply replaces the player's value).
* A concession item's ``ref`` is the major's abbreviation; minor ``ref`` is the minor number;
  private ``ref`` is the private number.
"""
from __future__ import annotations

from app.data.phases import PHASES_BY_NUMBER
from app.data.setup import SETUP_BY_PLAYER_COUNT
from app.data.stock_market import STOCK_MARKET_BY_POSITION

from . import stock_positions
from .models import BidBoxItem, GameState

CONCESSION_FACE_VALUE = 100  # rule 3.4.2
PRIVATE_FACE_VALUE = 0       # rule 3.1.3
# The rulebook states no minor "face value" in a table, but rule 4.11.4 (phase 1: "worth £100")
# and the 4.10 bidding example (M4 bid "at face value" = 100) fix it at 100.
MINOR_FACE_VALUE = 100

BID_STEP = 5  # rule 4.10.6

_BOX_ATTR = {
    "concession": "concession_bid_boxes",
    "minor": "minor_bid_boxes",
    "private": "private_bid_boxes",
}


class BidError(Exception):
    """Raised for an illegal bid."""


def _face_value(kind: str) -> int:
    if kind == "concession":
        return CONCESSION_FACE_VALUE
    if kind == "minor":
        return MINOR_FACE_VALUE
    if kind == "private":
        return PRIVATE_FACE_VALUE
    raise BidError(f"Unknown bid item kind: {kind!r}.")


def _all_items(state: GameState):
    for kind, attr in _BOX_ATTR.items():
        for item in getattr(state, attr):
            if item is not None:
                yield item


def _highest(item: BidBoxItem) -> tuple[str, int] | None:
    if not item.bids:
        return None
    pid = max(item.bids, key=lambda p: item.bids[p])
    return pid, item.bids[pid]


def _committed(state: GameState, player_id: str) -> int:
    """Rule 4.10.7: sum of the player's bids on items where they hold the highest bid."""
    total = 0
    for item in _all_items(state):
        top = _highest(item)
        if top is not None and top[0] == player_id:
            total += top[1]
    return total


def _tokens_in_use(state: GameState, player_id: str) -> int:
    return sum(1 for item in _all_items(state) if player_id in item.bids)


# ---------------------------------------------------------------------------
# Placing / moving a bid
# ---------------------------------------------------------------------------

def place_or_move_bid(state: GameState, player_id: str, kind: str, box_index: int, amount: int) -> None:
    from .certificates import certificate_count, certificate_limit

    if player_id not in state.players:
        raise BidError(f"Unknown player {player_id!r}.")
    player = state.players[player_id]
    face = _face_value(kind)  # raises BidError for an unknown kind

    boxes = getattr(state, _BOX_ATTR[kind])
    if (
        not isinstance(box_index, int) or isinstance(box_index, bool)
        or box_index < 0 or box_index >= len(boxes)
    ):
        raise BidError("No such bidding box.")
    item = boxes[box_index]
    if item is None:
        raise BidError("That bidding box is empty.")

    if kind == "concession" and PHASES_BY_NUMBER[state.phase].concession_rule == "removed":
        raise BidError("Concessions are removed from play from Phase 5 (rule 3.4.5).")

    if not isinstance(amount, int) or isinstance(amount, bool):
        raise BidError("A bid must be a whole number of pounds.")
    if amount % BID_STEP != 0 or amount < 0:
        raise BidError("Bids must be whole multiples of £5 (rule 4.10.6).")

    if player.loans > 0:
        raise BidError("A player with loans may not place a bid (rule 4.3.1).")

    # rule 4.10.8 (and 4.2.5): no bidding at the certificate limit
    if certificate_count(state, player_id) >= certificate_limit(state):
        raise BidError("You are at the certificate limit and may not bid (rule 4.10.8).")

    top = _highest(item)
    already_has_token = player_id in item.bids

    # rule 4.10.4: moving a token is only allowed if another player has the higher bid.
    # A player who already holds the highest bid cannot raise their own bid.
    if already_has_token and top is not None and top[0] == player_id:
        raise BidError("You already hold the highest bid on this item (rule 4.10.4).")

    # rule 4.10.3: limited number of bidding tokens = max number of items bid on.
    if not already_has_token:
        setup = SETUP_BY_PLAYER_COUNT.get(len(state.players))
        if setup is not None and _tokens_in_use(state, player_id) >= setup.bidding_tokens:
            raise BidError("You have no unallocated bidding tokens left (rule 4.10.3).")

    # rule 4.10.6: opening bid >= face value; rule 4.10.7: must beat existing bids.
    if top is None:
        if amount < face:
            raise BidError(f"The opening bid must be at least the face value (£{face}) (rule 4.10.6).")
    elif amount <= top[1]:
        raise BidError(f"A bid must be higher than the current highest bid (£{top[1]}) (rule 4.10.7).")

    # rule 4.10.7: committed resources (this item is not currently the player's highest, so it is
    # not yet in the committed sum) may not exceed cash in hand.
    if _committed(state, player_id) + amount > player.cash:
        raise BidError("The bid exceeds your available cash after your other committed bids (rule 4.10.7).")

    item.bids[player_id] = amount


# ---------------------------------------------------------------------------
# End of stock round
# ---------------------------------------------------------------------------

def _start_cell(price: int) -> tuple[int, int]:
    for (row, col), cell in STOCK_MARKET_BY_POSITION.items():
        if cell.value == price and cell.zone in ("start", "minor_start"):
            return row, col
    raise BidError(f"No stock-market start cell for £{price}.")


def _minor_start_price(phase: int, bid: int) -> int:
    """Rule 4.11.4 starting share price."""
    if phase <= 1:
        return 50
    price = (bid // 2) // 10 * 10          # halve, round down ...
    price = min(price, 100)                 # ... to the highest start space (£50..£100 in steps of 10)
    return max(price, 50)


def _place_minor_token(state: GameState, company_id: str, row: int, col: int) -> None:
    """Rule 4.11.5: a new minor token goes on top of major tokens but beneath other minors."""
    stock_positions.place_token(state, company_id, row, col)
    stack = state.stock_stack[(row, col)]
    stack.remove(company_id)
    idx = 0
    while idx < len(stack) and stack[idx] in state.minors:
        idx += 1
    stack.insert(idx, company_id)


def _float_minor(state: GameState, player_id: str, minor_number: int, bid: int) -> None:
    company_id = f"M{minor_number}"
    minor = state.minors[company_id]
    player = state.players[player_id]

    price = _minor_start_price(state.phase, bid)
    if state.phase <= 2:
        treasury = 2 * price        # funded by the bank; the bid itself was paid to the bank
        state.bank.cash -= treasury
    else:
        treasury = bid              # the sum bid becomes the starting treasury
        state.bank.cash -= bid      # undo the "paid to bank" credit applied at payment time

    minor.director_player_id = player_id
    minor.floated = True
    minor.share_price = price
    minor.treasury = treasury
    player.shares[company_id] = player.shares.get(company_id, 0) + 1

    row, col = _start_cell(price)
    _place_minor_token(state, company_id, row, col)
    state.log.append(f"{player_id} floated {company_id} at £{price} (bid £{bid}, treasury £{treasury}).")


def _export_train(state: GameState, from_pool: str | None = None) -> bool:
    """Remove one train from the bank (not the pool); a phase check follows like a bank purchase."""
    from . import trains

    if from_pool is None:
        pool_key = trains.current_buyable_pool(state)
    else:
        pool_key = from_pool if state.bank.train_pool.get(from_pool, 0) > 0 else None
    if pool_key is None:
        return False
    state.bank.train_pool[pool_key] -= 1
    trains._advance_phase_and_rust(state, pool_key)
    trains._enforce_train_limits(state)
    state.log.append(f"Train exported from the bank: {pool_key}.")
    return True


def _item_won(state: GameState, kind: str, item: BidBoxItem) -> tuple[str, int] | None:
    """Pay for and award one item to the highest bidder who can pay; returns (player, amount)."""
    for pid, amount in sorted(item.bids.items(), key=lambda kv: -kv[1]):
        player = state.players[pid]
        if player.cash < amount:
            continue  # cannot pay (cash dropped after bidding): bid lapses, next bidder is tried
        player.cash -= amount
        state.bank.cash += amount
        if kind == "concession":
            player.concessions.append(item.ref)
            state.majors[item.ref].concession_holder_player_id = pid
        elif kind == "private":
            player.private_companies.append(item.ref)
            state.privates[item.ref].owner_player_id = pid
        return pid, amount
    return None


def resolve_stock_round(state: GameState) -> None:
    sold_minors: list[tuple[int, int, str, int]] = []  # (-bid, box_index, player, minor number)
    sold_boxes: dict[str, set[int]] = {k: set() for k in _BOX_ATTR}
    had_bids_minor_boxes: set[int] = set()

    # 4.11.2: pay for and take items
    for kind, attr in _BOX_ATTR.items():
        for idx, item in enumerate(getattr(state, attr)):
            if item is None:
                continue
            if kind == "minor" and item.bids:
                had_bids_minor_boxes.add(idx)
            if not item.bids:
                continue
            won = _item_won(state, kind, item)
            if won is None:
                continue
            sold_boxes[kind].add(idx)
            if kind == "minor":
                sold_minors.append((-won[1], idx, won[0], item.ref))

    # 4.11.3 / 4.11.4: float purchased minors, highest bid first, ties by lowest box
    for neg_bid, _idx, pid, number in sorted(sold_minors):
        _float_minor(state, pid, number, -neg_bid)

    # 4.11.6: one L/2 train exported per minor remaining without any bid
    for idx, item in enumerate(state.minor_bid_boxes):
        if item is not None and idx not in sold_boxes["minor"] and idx not in had_bids_minor_boxes:
            if not _export_train(state, "L"):
                _export_train(state, "2")

    # 4.11.7: unsold minor in box 1 is removed and the next new train is exported
    box1 = state.minor_bid_boxes[0] if state.minor_bid_boxes else None
    if box1 is not None and 0 not in sold_boxes["minor"]:
        state.minors[f"M{box1.ref}"].removed = True
        state.minor_bid_boxes[0] = None
        state.log.append(f"M{box1.ref} unsold in bid box 1 and removed from play.")
        _export_train(state)

    # 4.11.8 / 4.10.2: clear tokens, drop sold items, shift and refill
    from .setup import _refill_bid_boxes

    for kind, attr in _BOX_ATTR.items():
        boxes = getattr(state, attr)
        for idx in range(len(boxes)):
            if idx in sold_boxes[kind]:
                boxes[idx] = None
            elif boxes[idx] is not None:
                boxes[idx].bids = {}
    _refill_bid_boxes(state)

    # 4.3.4 / 4.11.10: 50% interest (rounded up) on outstanding loans
    for player in state.players.values():
        if player.loans > 0:
            player.loans += (player.loans + 1) // 2

    # 4.12.1 / 4.12.2: fully sold majors rise one space, in descending price order
    sold_out = [
        abbr for abbr, m in state.majors.items()
        if abbr in state.stock_positions
        and m.director_player_id is not None
        and m.shares_in_treasury == 0
        and m.shares_in_bank_pool == 0
    ]
    sold_out.sort(key=lambda abbr: stock_positions.descending_price_key(state, abbr))
    for abbr in sold_out:
        row, col = state.stock_positions[abbr]
        target = (row - 1, col)
        if target in STOCK_MARKET_BY_POSITION:
            stock_positions.place_token(state, abbr, *target)
            state.log.append(f"{abbr} fully sold: price rises to £{stock_positions.company_value(state, abbr)}.")
