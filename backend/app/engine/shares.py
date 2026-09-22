"""Buying and selling major company shares in a stock round (rule 4.4-4.5)."""
from __future__ import annotations

from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .certificates import certificate_count, certificate_limit
from .models import GameState
from .stock_positions import company_value, place_token

MAX_HOLDING_UNITS = 6  # 60% ownership cap (rule 3.3.7 / 4.5.6), exception: P16 tax haven


class ShareError(Exception):
    pass


def _director_cert_units(company_id: str, state: GameState) -> int:
    from app.data.major_companies import LNWR_ABBR

    return 1 if company_id == LNWR_ABBR else 2


def buy_share(state: GameState, player_id: str, company_id: str, source: str | None = None) -> None:
    major = state.majors.get(company_id)
    if major is None or not major.floated:
        raise ShareError("That company has no shares available to buy.")
    if company_id in state.sold_this_round.get(player_id, set()):
        raise ShareError("Cannot buy a company's stock in the same stock round you sold it in (rule 4.5.5).")

    if source is None:
        source = "bank" if major.shares_in_bank_pool > 0 else "treasury"
    available = major.shares_in_bank_pool if source == "bank" else major.shares_in_treasury
    if available <= 0:
        raise ShareError(f"No shares available from the {source}.")

    holding = state.players[player_id].shares.get(company_id, 0)
    if holding + 1 > MAX_HOLDING_UNITS:
        raise ShareError("Cannot hold more than 60% of a company (rule 4.5.6).")

    if certificate_count(state, player_id) >= certificate_limit(state):
        raise ShareError("At certificate limit.")

    price = company_value(state, company_id)
    player = state.players[player_id]
    if player.cash < price:
        raise ShareError("Insufficient cash.")

    player.cash -= price
    if source == "bank":
        state.bank.cash += price
        major.shares_in_bank_pool -= 1
    else:
        major.treasury += price
        major.shares_in_treasury -= 1
    player.shares[company_id] = holding + 1

    # Rule 4.5.9: if this purchase gives the buyer more shares than the
    # current director holds, the director's certificate changes hands.
    if major.director_player_id is not None and major.director_player_id != player_id:
        director_holding = state.players[major.director_player_id].shares.get(company_id, 0)
        if holding + 1 > director_holding:
            major.director_player_id = player_id


def sell_shares(state: GameState, player_id: str, company_id: str, count: int) -> None:
    if count <= 0:
        raise ShareError("Must sell at least one share.")
    major = state.majors.get(company_id)
    if major is None or not major.floated:
        raise ShareError("That company has no sellable shares.")
    if not major.has_operated:
        raise ShareError("Cannot sell shares in a company that hasn't completed an operating round (rule 4.4.1).")

    player = state.players[player_id]
    holding = player.shares.get(company_id, 0)
    director_units = _director_cert_units(company_id, state)
    is_director = major.director_player_id == player_id
    sellable = holding - director_units if is_director else holding
    if count > sellable:
        raise ShareError("Cannot sell the director's certificate, or more shares than you hold.")

    if major.shares_in_bank_pool + count > 5:
        raise ShareError("No more than 50% of a company's stock may sit in the bank pool (rule 4.4.1).")

    total_proceeds = 0
    for _ in range(count):
        price = company_value(state, company_id)
        total_proceeds += price
        _move_price_down_one(state, company_id)

    player.cash += total_proceeds
    new_holding = holding - count
    player.shares[company_id] = new_holding
    major.shares_in_bank_pool += count
    state.sold_this_round.setdefault(player_id, set()).add(company_id)
    state.any_sale_this_stock_round = True

    # Rule 4.4.2: the director changes hands if this sale drops their
    # holding below another (eligible) player's - not below some fixed
    # threshold like the director-certificate size.
    if is_director:
        other_max = max(
            (p.shares.get(company_id, 0) for pid, p in state.players.items() if pid != player_id),
            default=0,
        )
        if other_max > new_holding:
            _handle_director_departure(state, company_id, player_id)


def _move_price_down_one(state: GameState, company_id: str) -> None:
    row, col = state.stock_positions[company_id]
    candidate = (row + 1, col)
    if candidate in STOCK_MARKET_BY_POSITION:
        place_token(state, company_id, *candidate)
    # else: at the bottom of its column, rule 4.4.4 - does not move further


def _handle_director_departure(state: GameState, company_id: str, outgoing_player_id: str) -> None:
    """Rule 4.4.2: exchange the outgoing director's certificate for two
    ordinary certificates belonging to the new director (the largest other
    holder; ties broken by next-player-order proximity to the outgoing
    director, approximated here by player_order rotation)."""
    director_units = _director_cert_units(company_id, state)
    candidates = [
        pid for pid, p in state.players.items()
        if pid != outgoing_player_id and p.shares.get(company_id, 0) >= director_units
    ]
    if not candidates:
        return  # no eligible replacement director; the company simply has none for now

    order = state.player_order
    outgoing_idx = order.index(outgoing_player_id) if outgoing_player_id in order else 0

    def rank(pid: str):
        holding = state.players[pid].shares.get(company_id, 0)
        idx = order.index(pid) if pid in order else 0
        distance = (idx - outgoing_idx) % len(order)
        return (-holding, distance)

    new_director = min(candidates, key=rank)
    state.majors[company_id].director_player_id = new_director
