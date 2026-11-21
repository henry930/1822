"""
Scoring and game-end trigger module for 1822.

Layer 3: depends on turn_order (1) and certificates (2); no upward imports at module level.
"""
from __future__ import annotations

from typing import Iterable

# Data tables
from app.data.private_companies import PRIVATE_COMPANIES_BY_NUMBER

# Lower-layer modules (import at module level, allowed)
from app.engine import turn_order
from app.engine import certificates

from .models import GameState, RoundType


class ScoringError(Exception):
    """Single exception for this module.

    Message format: "<ERR_CODE>: <text>"
    Attribute .code = ERR_CODE (the string).
    """
    def __init__(self, code: str, text: str):
        self.code = code
        super().__init__(f"{code}: {text}")


# ---- Constants ----

CONTEXT_AFTER_BANK_PAYMENT = "after_bank_payment"
CONTEXT_AFTER_TOKEN_MOVE = "after_token_move"
CONTEXT_END_OF_STOCK_ROUND = "end_of_stock_round"

TRIGGER_NEXT_OR = "next_or"
TRIGGER_OR_END = "or_end"
TRIGGER_OR_SET_END = "or_set_end"

CONCESSION_DIVIDEND = 10


# ---- Game‑end trigger ----

def check_game_end_triggers(state: GameState, context: str | None = None) -> None:
    """Evaluate game‑end conditions and record the first trigger.

    Called after every action, bank payments and token moves, and at the
    end of stock‑round resolution.
    """
    # If a trigger already exists, do nothing (first trigger wins)
    if state.game_over or state.end_trigger_pending is not None:
        return

    # Step 2: immediate nothing‑sold in first stock round
    if context == CONTEXT_END_OF_STOCK_ROUND and state.stock_rounds_completed == 0:
        if not state.any_sale_this_stock_round:
            state.game_over = True
            return

    # Helper: check if any company token sits on a game‑end cell
    def _any_token_on_game_end() -> bool:
        for cid in list(state.majors.keys()) + list(state.minors.keys()):
            if cid not in state.stock_positions:
                continue
            if turn_order.is_game_end_cell(state, cid):
                return True
        return False

    if state.round_type == RoundType.OPERATING:
        if _any_token_on_game_end():
            state.end_trigger_pending = TRIGGER_OR_END
            return
        if bank_broken(state):
            state.end_trigger_pending = TRIGGER_OR_SET_END
            return
    elif state.round_type == RoundType.STOCK:
        if _any_token_on_game_end() or bank_broken(state):
            state.end_trigger_pending = TRIGGER_NEXT_OR
            return


# ---- Bank broken ----

def bank_broken(state: GameState) -> bool:
    """True when the bank has run out of money.

    Formula: bank_cash < 0. Loans are excluded (rule 4.3.5).
    """
    return state.bank.cash < 0


# ---- Player wealth ----

def player_wealth(state: GameState, player_id: str) -> int:
    """Compute a player's total wealth at game end.

    Formula (10.1.3):
        cash + Σ [units_held(p,c) × current_price(c)]
        + 100 × |concessions|
        - loans
    """
    if player_id not in state.players:
        raise ScoringError("ERR_UNKNOWN_PLAYER", f"Player {player_id!r} does not exist.")

    player = state.players[player_id]
    total = player.cash

    # Major company shares
    for cid in state.majors:
        units = certificates.units_held(state, player_id, cid)
        if units > 0:
            total += units * turn_order.current_price(state, cid)

    # Concessions at face value (£100 each)
    total += 100 * len(player.concessions)

    # Subtract loans
    total -= player.loans

    return total


# ---- Final ranking ----

def final_ranking(state: GameState) -> list[tuple[str, int]]:
    """Return list of (player_id, wealth) sorted richest first.

    Ties keep the stock‑round order (state.player_order).
    """
    wealths = {pid: player_wealth(state, pid) for pid in state.player_order}
    # Stable sort by descending wealth, original order for ties
    # Use index as secondary key because sort is stable
    sorted_pairs = sorted(wealths.items(), key=lambda x: (-x[1], state.player_order.index(x[0])))
    return sorted_pairs


# Alias
ranking = final_ranking


# ---- Private revenue ----

def private_revenue(private_number: int, phase: int) -> int:
    """Parse revenue of a private company.

    Revenue string examples: '£5' → 5, '£10x phase' → 10*phase.
    """
    pc = PRIVATE_COMPANIES_BY_NUMBER.get(private_number)
    if pc is None:
        raise ScoringError(
            "ERR_UNKNOWN_PRIVATE",
            f"Private number {private_number} does not exist in the data table."
        )

    rev_str = pc.revenue  # e.g. "£5", "£10x phase", "£0"
    # Remove leading '£'
    if rev_str.startswith("£"):
        rev_str = rev_str[1:]
    if rev_str.endswith("x phase"):
        base = int(rev_str.replace("x phase", ""))
        return base * phase
    else:
        return int(rev_str)


# ---- Pay concession dividends ----

def pay_concession_dividends(state: GameState) -> None:
    """Pay £10 per held concession to its owner from the bank.

    No‑op at phase ≥ 5.
    """
    if state.phase >= 5:
        return

    # Pay each concession
    for player in state.players.values():
        for abbr in player.concessions:
            player.cash += CONCESSION_DIVIDEND
            state.bank.cash -= CONCESSION_DIVIDEND

    # Check game end after all payments
    check_game_end_triggers(state, CONTEXT_AFTER_BANK_PAYMENT)


# Alias
pay_concession_revenue = pay_concession_dividends


# ---- Pay private revenues ----

def pay_private_revenues(state: GameState) -> None:
    """Pay every open private's fixed revenue to its owner.

    Owner: if owner_company_id is set → company treasury;
    otherwise the player who holds the private in Player.private_companies.
    Closed privates pay nothing.
    """
    for pvt in state.privates.values():
        if pvt.closed:
            continue

        # Determine owner
        if pvt.owner_company_id is not None:
            # Company‑owned: credit its treasury
            company_id = pvt.owner_company_id
            revenue = private_revenue(pvt.number, state.phase)
            if revenue > 0:
                if company_id in state.majors:
                    state.majors[company_id].treasury += revenue
                elif company_id in state.minors:
                    state.minors[company_id].treasury += revenue
                state.bank.cash -= revenue
        else:
            # Player‑owned: find which player holds it
            for player in state.players.values():
                if pvt.number in player.private_companies:
                    revenue = private_revenue(pvt.number, state.phase)
                    if revenue > 0:
                        player.cash += revenue
                        state.bank.cash -= revenue
                    break

    # Check game end after all payments
    check_game_end_triggers(state, CONTEXT_AFTER_BANK_PAYMENT)


# Alias
pay_private_revenue = pay_private_revenues

# --- eval name adapter ---
final_wealth = player_wealth
final_standings = final_ranking
