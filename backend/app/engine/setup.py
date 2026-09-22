"""Game setup / initialisation (rules section 1.7)."""
from __future__ import annotations

import random

from app.data.major_companies import MAJOR_COMPANIES
from app.data.minor_companies import BASE_GAME_MINOR_COMPANIES, FIXED_TOP_OF_STACK_MINOR
from app.data.private_companies import BASE_GAME_PRIVATE_COMPANIES
from app.data.setup import SETUP_BY_PLAYER_COUNT, STARTING_BANK
from app.data.trains import TRAIN_TYPES

from .models import (
    BankState,
    BidBoxItem,
    GameState,
    MajorCompanyState,
    MinorCompanyState,
    Player,
    PrivateCompanyState,
)

FIXED_TOP_OF_STACK_PRIVATE = 1   # P1 Butterley Engineering Company always on top (rule 1.7.6)
LNWR_CONCESSION_ABBR = "LNWR"    # LNWR concession always on top (rule 1.7.4)

NUM_MINOR_BID_BOXES = 4
NUM_CONCESSION_BID_BOXES = 3
NUM_PRIVATE_BID_BOXES = 3


def _shuffled_with_fixed_top(items: list, fixed_top, key=lambda x: x) -> list:
    rest = [i for i in items if key(i) != fixed_top]
    random.shuffle(rest)
    top = [i for i in items if key(i) == fixed_top]
    return top + rest


def new_game(game_id: str, player_names: list[str], seed: int | None = None) -> GameState:
    if seed is not None:
        random.seed(seed)

    num_players = len(player_names)
    if num_players not in SETUP_BY_PLAYER_COUNT:
        raise ValueError(f"1822 supports 3-7 players, got {num_players}")
    setup = SETUP_BY_PLAYER_COUNT[num_players]

    player_ids = [f"p{i+1}" for i in range(num_players)]
    order = list(player_ids)
    random.shuffle(order)  # rule 1.7.12: random player order via dealt number cards

    players = {
        pid: Player(id=pid, name=name, cash=setup.start_money)
        for pid, name in zip(player_ids, player_names)
    }

    bank = BankState(cash=STARTING_BANK - setup.start_money * num_players)
    bank.train_pool = {t.code: (t.count or 0) for t in TRAIN_TYPES}
    # L and 2 share one physical pool of 22 double-sided cards; likewise 7/E share 16.
    bank.train_pool["2"] = 0  # all 22 start as "L" side up
    bank.train_pool["L"] = 22
    bank.train_pool["E"] = 0  # all 16 start as "7" side up
    bank.train_pool["7"] = 16

    concession_stack = _shuffled_with_fixed_top(
        [c.abbr for c in MAJOR_COMPANIES], LNWR_CONCESSION_ABBR
    )
    minor_stack = _shuffled_with_fixed_top(
        [c.number for c in BASE_GAME_MINOR_COMPANIES], FIXED_TOP_OF_STACK_MINOR
    )
    private_stack = _shuffled_with_fixed_top(
        [c.number for c in BASE_GAME_PRIVATE_COMPANIES], FIXED_TOP_OF_STACK_PRIVATE
    )

    state = GameState(
        game_id=game_id,
        player_order=order,
        players=players,
        bank=bank,
        concession_stack=concession_stack,
        minor_stack=minor_stack,
        private_stack=private_stack,
        priority_deal_player_id=order[0],
        active_player_id=order[0],
    )

    for c in MAJOR_COMPANIES:
        state.majors[c.abbr] = MajorCompanyState(abbr=c.abbr, stations_available=1, stations_exchange=5)
    for c in BASE_GAME_MINOR_COMPANIES:
        state.minors[f"M{c.number}"] = MinorCompanyState(number=c.number, company_id=f"M{c.number}")
    for c in BASE_GAME_PRIVATE_COMPANIES:
        state.privates[c.number] = PrivateCompanyState(number=c.number)

    state.concession_bid_boxes = [None] * NUM_CONCESSION_BID_BOXES
    state.minor_bid_boxes = [None] * NUM_MINOR_BID_BOXES
    state.private_bid_boxes = [None] * NUM_PRIVATE_BID_BOXES
    _refill_bid_boxes(state)

    return state


def _refill_bid_boxes(state: GameState) -> None:
    """Rule 4.1.1 / 4.10.2: shift remaining items down, then fill empty boxes from the stacks."""
    state.concession_bid_boxes = [b for b in state.concession_bid_boxes if b is not None]
    while len(state.concession_bid_boxes) < NUM_CONCESSION_BID_BOXES and state.concession_stack:
        state.concession_bid_boxes.append(BidBoxItem(kind="concession", ref=state.concession_stack.pop(0)))
    while len(state.concession_bid_boxes) < NUM_CONCESSION_BID_BOXES:
        state.concession_bid_boxes.append(None)

    state.minor_bid_boxes = [b for b in state.minor_bid_boxes if b is not None]
    while len(state.minor_bid_boxes) < NUM_MINOR_BID_BOXES and state.minor_stack:
        state.minor_bid_boxes.append(BidBoxItem(kind="minor", ref=state.minor_stack.pop(0)))
    while len(state.minor_bid_boxes) < NUM_MINOR_BID_BOXES:
        state.minor_bid_boxes.append(None)

    state.private_bid_boxes = [b for b in state.private_bid_boxes if b is not None]
    while len(state.private_bid_boxes) < NUM_PRIVATE_BID_BOXES and state.private_stack:
        state.private_bid_boxes.append(BidBoxItem(kind="private", ref=state.private_stack.pop(0)))
    while len(state.private_bid_boxes) < NUM_PRIVATE_BID_BOXES:
        state.private_bid_boxes.append(None)
