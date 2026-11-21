"""Scoring module: game-end triggers, bank state, wealth, ranking and the
start-of-operating-round payments of privates and concessions (layer 3)."""
from __future__ import annotations

from app.data.private_companies import PRIVATE_COMPANIES_BY_NUMBER
from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .models import GameState, RoundType


class ScoringError(Exception):
    """Single exception class of the scoring module."""

    def __init__(self, code: str, text: str = ""):
        self.code = code
        super().__init__(f"{code}: {text}" if text else code)


CONTEXT_AFTER_BANK_PAYMENT = "after_bank_payment"
CONTEXT_AFTER_TOKEN_MOVE = "after_token_move"
CONTEXT_END_OF_STOCK_ROUND = "end_of_stock_round"

TRIGGER_NEXT_OR = "next_or"
TRIGGER_OR_END = "or_end"
TRIGGER_OR_SET_END = "or_set_end"

CONCESSION_DIVIDEND = 10


# ---------------------------------------------------------------- helpers

def _on_game_end_cell(state: GameState, company_id: str) -> bool:
    try:
        from .turn_order import is_game_end_cell
    except Exception:  # lower layer missing / half-written: local fallback
        is_game_end_cell = None
    if is_game_end_cell is not None:
        return bool(is_game_end_cell(state, company_id))
    pos = state.stock_positions.get(company_id)
    if pos is None:
        return False
    cell = STOCK_MARKET_BY_POSITION.get(tuple(pos))
    return bool(cell is not None and cell.game_end)


def _any_token_on_game_end_cell(state: GameState) -> bool:
    for cid in list(state.stock_positions):
        if state.stock_positions.get(cid) is None:
            continue
        if _on_game_end_cell(state, cid):
            return True
    return False


# ------------------------------------------------------------ public API

def bank_broken(state: GameState) -> bool:
    return state.bank.cash < 0


def check_game_end_triggers(state: GameState, context: str | None = None) -> None:
    # 10.1.2: the first trigger stands.
    if state.game_over or state.end_trigger_pending is not None:
        return
    # 10.1.1 / R6b: nothing sold in the first stock round -> immediate.
    if (context == CONTEXT_END_OF_STOCK_ROUND
            and state.stock_rounds_completed == 0
            and not state.any_sale_this_stock_round):
        state.game_over = True
        return
    if state.round_type == RoundType.OPERATING:
        if _any_token_on_game_end_cell(state):
            state.end_trigger_pending = TRIGGER_OR_END
        elif bank_broken(state):
            state.end_trigger_pending = TRIGGER_OR_SET_END
    elif state.round_type == RoundType.STOCK:
        if _any_token_on_game_end_cell(state) or bank_broken(state):
            state.end_trigger_pending = TRIGGER_NEXT_OR


def player_wealth(state: GameState, player_id: str) -> int:
    player = state.players.get(player_id)
    if player is None:
        raise ScoringError("ERR_UNKNOWN_PLAYER", f"unknown player {player_id!r}")
    from .certificates import units_held
    from .turn_order import current_price

    total = player.cash - player.loans
    for cid in state.majors:
        units = units_held(state, player_id, cid)
        if units and cid in state.stock_positions:
            total += units * current_price(state, cid)
    total += 100 * len(player.concessions)
    return total


def final_ranking(state: GameState) -> list[tuple[str, int]]:
    order = list(state.player_order)
    for pid in state.players:
        if pid not in order:
            order.append(pid)
    wealth = [(pid, player_wealth(state, pid)) for pid in order if pid in state.players]
    # sorted() is stable: ties keep player order
    return sorted(wealth, key=lambda t: -t[1])


ranking = final_ranking


def private_revenue(private_number: int, phase: int) -> int:
    info = PRIVATE_COMPANIES_BY_NUMBER.get(private_number)
    if info is None:
        raise ScoringError("ERR_UNKNOWN_PRIVATE", f"unknown private {private_number!r}")
    text = str(info.revenue).replace("£", "").replace("£", "").strip()
    mult = False
    if text.endswith("x phase"):
        text, mult = text[: -len("x phase")], True
    elif text.endswith("xphase"):
        text, mult = text[: -len("xphase")], True
    value = int(text.strip() or 0)
    return value * phase if mult else value


def _credit_company(state: GameState, company_id: str, amount: int) -> bool:
    comp = state.majors.get(company_id)
    if comp is None:
        comp = state.minors.get(company_id)
    if comp is None:
        return False
    comp.treasury += amount
    return True


def pay_private_revenues(state: GameState) -> None:
    paid: set[int] = set()
    # (number, revenue, player_id | None, company_id | None)
    payments: list[tuple[int, int, str | None, str | None]] = []

    def plan(n: int, player_id: str | None) -> None:
        if n in paid or n not in PRIVATE_COMPANIES_BY_NUMBER:
            return
        ps = state.privates.get(n)
        if ps is not None and ps.closed:
            return
        r = private_revenue(n, state.phase)
        paid.add(n)
        if r <= 0:
            return
        company = ps.owner_company_id if ps is not None else None
        if company is not None:
            payments.append((n, r, None, company))
        elif player_id is not None:
            payments.append((n, r, player_id, None))

    # privates owned by companies first (owner_company_id decides)
    for n in sorted(state.privates):
        if state.privates[n].owner_company_id is not None:
            plan(n, None)
    for pid in state.player_order or list(state.players):
        p = state.players.get(pid)
        if p is None:
            continue
        for n in list(p.private_companies):
            plan(n, pid)

    for n, r, pid, cid in payments:
        if cid is not None:
            if not _credit_company(state, cid, r):
                continue
        else:
            state.players[pid].cash += r
        state.bank.cash -= r
    check_game_end_triggers(state, CONTEXT_AFTER_BANK_PAYMENT)


pay_private_revenue = pay_private_revenues


def pay_concession_dividends(state: GameState) -> None:
    if state.phase < 5:
        for p in state.players.values():
            n = len(p.concessions)
            if n:
                p.cash += CONCESSION_DIVIDEND * n
                state.bank.cash -= CONCESSION_DIVIDEND * n
    check_game_end_triggers(state, CONTEXT_AFTER_BANK_PAYMENT)


pay_concession_revenue = pay_concession_dividends
