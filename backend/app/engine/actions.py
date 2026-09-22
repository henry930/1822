"""Action dispatch: the single entry point client actions flow through.

Simplification (see app.engine.bidding's module docstring): each of "bid",
"buy_share", and "sell_shares" is treated as a full, turn-ending action, one
per turn. Rule 4.1.3 actually allows selling and repaying a loan as free
pre-steps before the turn's one "choice" (buy/convert/bid) - that combining
isn't wired up yet, so for now a player who wants to sell then buy in the
same turn needs two turns (sell now, buy on their next turn).
"""
from __future__ import annotations

from .bidding import BidError, place_or_move_bid, resolve_stock_round
from .company_formation import ConcessionError, convert_concession
from .models import GameState, RoundType
from .round_manager import advance_company, advance_stock_player, end_stock_round
from .shares import ShareError, buy_share, sell_shares


class ActionError(Exception):
    """Raised for an illegal action; message is user-facing."""


def apply_action(state: GameState, player_id: str, action: dict) -> GameState:
    if state.game_over:
        raise ActionError("Game is over.")

    action_type = action.get("type")
    if action_type == "pass":
        _apply_pass(state, player_id)
    elif action_type == "bid":
        _apply_bid(state, player_id, action)
    elif action_type == "buy_share":
        _apply_buy_share(state, player_id, action)
    elif action_type == "sell_shares":
        _apply_sell_shares(state, player_id, action)
    elif action_type == "convert_concession":
        _apply_convert_concession(state, player_id, action)
    else:
        raise ActionError(f"Unknown action type: {action_type!r}")

    return state


def _apply_bid(state: GameState, player_id: str, action: dict) -> None:
    if state.round_type != RoundType.STOCK:
        raise ActionError("Bids can only be placed in a stock round.")
    if player_id != state.active_player_id:
        raise ActionError("It is not your turn.")

    bids = action.get("bids", [])
    if not bids:
        raise ActionError("No bids given.")
    if len(bids) > 3:
        raise ActionError("At most 3 bids per turn (rule 4.10.5).")
    if state.bids_this_turn + len(bids) > 3:
        raise ActionError("At most 3 bids per turn (rule 4.10.5).")

    for b in bids:
        try:
            place_or_move_bid(state, player_id, b["kind"], b["box_index"], b["amount"])
        except BidError as e:
            raise ActionError(str(e)) from e
        state.bids_this_turn += 1

    state.consecutive_passes = 0
    advance_stock_player(state)


def _apply_buy_share(state: GameState, player_id: str, action: dict) -> None:
    if state.round_type != RoundType.STOCK:
        raise ActionError("Shares can only be bought in a stock round.")
    if player_id != state.active_player_id:
        raise ActionError("It is not your turn.")

    try:
        buy_share(state, player_id, action["company_id"], action.get("source"))
    except ShareError as e:
        raise ActionError(str(e)) from e

    state.consecutive_passes = 0
    state.any_sale_this_stock_round = True
    advance_stock_player(state)


def _apply_sell_shares(state: GameState, player_id: str, action: dict) -> None:
    if state.round_type != RoundType.STOCK:
        raise ActionError("Shares can only be sold in a stock round.")
    if player_id != state.active_player_id:
        raise ActionError("It is not your turn.")

    try:
        sell_shares(state, player_id, action["company_id"], action["count"])
    except ShareError as e:
        raise ActionError(str(e)) from e

    state.consecutive_passes = 0
    advance_stock_player(state)


def _apply_convert_concession(state: GameState, player_id: str, action: dict) -> None:
    if state.round_type != RoundType.STOCK:
        raise ActionError("Concessions can only be converted in a stock round.")
    if player_id != state.active_player_id:
        raise ActionError("It is not your turn.")

    try:
        convert_concession(state, player_id, action["abbr"], action["start_price"])
    except ConcessionError as e:
        raise ActionError(str(e)) from e

    state.consecutive_passes = 0
    state.any_sale_this_stock_round = True
    advance_stock_player(state)


def _apply_pass(state: GameState, player_id: str) -> None:
    if state.round_type == RoundType.STOCK:
        if player_id != state.active_player_id:
            raise ActionError("It is not your turn.")
        state.consecutive_passes += 1
        if state.consecutive_passes >= len(state.player_order):
            end_stock_round(state)
        else:
            advance_stock_player(state)
    elif state.round_type == RoundType.OPERATING:
        # Passing for a company is the active player's prerogative only if
        # they direct that company; full director-authorization checks land
        # with Task #6's operating-round actions. For now this just advances
        # the turn pointer so the plumbing is exercisable end-to-end.
        advance_company(state)
    else:
        raise ActionError(f"Unhandled round type: {state.round_type!r}")
