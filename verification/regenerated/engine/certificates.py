"""Certificate limit accounting (rules 4.2.1-4.2.5, 4.5.8, 4.10.8)."""
from __future__ import annotations

from app.data.setup import SETUP_BY_PLAYER_COUNT
from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .models import GameState

LNWR_ABBR = "LNWR"
TAX_HAVEN_PRIVATE = 16


def certificate_limit(state: GameState) -> int:
    """Rule 4.2.1: limit by number of players."""
    return SETUP_BY_PLAYER_COUNT[len(state.players)].certificate_limit


def is_in_yellow_zone(state: GameState, company_id: str) -> bool:
    """Rule 4.2.3 / 4.5.8: the company's price token is in the yellow area."""
    pos = state.stock_positions.get(company_id)
    if pos is None:
        return False
    cell = STOCK_MARKET_BY_POSITION.get(pos)
    return cell is not None and cell.zone == "yellow"


def owned_certificate_count(state: GameState, player_id: str) -> int:
    """Rules 4.2.2-4.2.3: privates (except P16), concessions and share certificates."""
    player = state.players[player_id]
    total = 0
    for number in player.private_companies:
        if number == TAX_HAVEN_PRIVATE:
            continue
        priv = state.privates.get(number)
        if priv is not None and (priv.closed or priv.owner_company_id is not None):
            continue
        total += 1
    total += len(player.concessions)
    for company_id, units in player.shares.items():
        if units <= 0 or is_in_yellow_zone(state, company_id):
            continue
        certs = units
        major = state.majors.get(company_id)
        if (
            major is not None
            and company_id != LNWR_ABBR
            and major.director_player_id == player_id
            and units >= 2
        ):
            certs -= 1  # the 20% director's certificate is one certificate worth two units
        total += certs
    return total


def bid_certificate_count(state: GameState, player_id: str) -> int:
    """Rule 4.10.8: each item (all three kinds) on which the player holds the highest bid."""
    count = 0
    for boxes in (state.concession_bid_boxes, state.minor_bid_boxes, state.private_bid_boxes):
        for item in boxes:
            if item is None or not item.bids:
                continue
            top = max(item.bids.values())
            if item.bids.get(player_id) == top:
                count += 1
    return count


def certificate_count(state: GameState, player_id: str) -> int:
    return owned_certificate_count(state, player_id) + bid_certificate_count(state, player_id)
