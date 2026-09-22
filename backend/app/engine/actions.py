"""Action dispatch: the single entry point client actions flow through.

Only "pass" is implemented here (round-sequencing plumbing). Stock round
actions (bid, buy, sell...) land in Task #2; operating round actions (lay
tile, run trains...) land in Task #6+. Both will register handlers into
ACTION_HANDLERS the same way `pass` does below, keyed by round type.
"""
from __future__ import annotations

from .bidding import BidError, place_or_move_bid, resolve_stock_round
from .models import GameState, RoundType
from .round_manager import advance_company, advance_stock_player, end_stock_round


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
