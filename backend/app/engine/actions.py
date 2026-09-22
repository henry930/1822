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
from .operating import (
    OperatingError,
    check_destination_connection,
    distribute_earnings,
    first_turn_housekeeping,
    home_hex_for,
    lay_track,
    run_trains_for_company,
)
from .round_manager import active_company_id, advance_company, advance_stock_player, end_stock_round
from .scoring import check_game_end_triggers
from .shares import ShareError, buy_share, sell_shares
from .trains import TrainError, buy_train_from_bank


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
    elif action_type == "operate":
        _apply_operate(state, player_id, action)
    else:
        raise ActionError(f"Unknown action type: {action_type!r}")

    check_game_end_triggers(state)
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


def _apply_operate(state: GameState, player_id: str, action: dict) -> None:
    """Bundles one company's operating-round turn: first-turn housekeeping,
    an optional tile lay, a destination-connection check (majors), running
    trains, and dividend distribution - then ends that company's turn.

    Not yet implemented (Task #7): private company acquisition, station
    token placement beyond home/destination, train purchases (including
    the rule that a company without a train must buy one), minor
    acquisition, and issue/redeem stock. A company with no train currently
    just runs for £0 rather than being forced to buy one.
    """
    if state.round_type != RoundType.OPERATING:
        raise ActionError("Not an operating round.")
    company_id = action.get("company_id")
    if company_id != active_company_id(state):
        raise ActionError("That company is not currently operating.")

    kind = "minor" if company_id in state.minors else "major"
    director = (
        state.minors[company_id].director_player_id
        if kind == "minor" else state.majors[company_id].director_player_id
    )
    if player_id != director:
        raise ActionError("Only that company's director may operate it.")

    try:
        first_turn_housekeeping(state, state.board, company_id, kind)

        tile_lay = action.get("tile_lay")
        if tile_lay is not None:
            owner = state.minors[company_id] if kind == "minor" else state.majors[company_id]
            lay_track(
                state, state.board, company_id, kind,
                tile_lay["hex_id"], tile_lay["tile_id"], tile_lay["rotation"],
                treasury_field_owner=owner,
            )

        if kind == "major":
            check_destination_connection(state.board, state, company_id)

        home = home_hex_for(company_id, kind)
        station_hexes = [home] if home else []
        revenue, _routes = run_trains_for_company(state.board, state, company_id, kind, station_hexes)

        if revenue > 0 or kind == "minor":
            distribute_earnings(state, company_id, kind, revenue, action.get("dividend_choice", "withhold"))

        buy_train = action.get("buy_train")
        if buy_train is not None:
            buy_train_from_bank(state, company_id, kind, buy_train)
    except (OperatingError, TrainError) as e:
        raise ActionError(str(e)) from e

    advance_company(state)


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
        company_id = active_company_id(state)
        if company_id is None:
            raise ActionError("No company is currently operating.")
        director = (
            state.minors[company_id].director_player_id
            if company_id in state.minors else state.majors[company_id].director_player_id
        )
        if player_id != director:
            raise ActionError("Only that company's director may act for it.")
        advance_company(state)
    else:
        raise ActionError(f"Unhandled round type: {state.round_type!r}")
