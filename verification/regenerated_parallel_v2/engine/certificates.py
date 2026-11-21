"""Certificate-limit bookkeeping (rules 4.2.1-4.2.5, 4.5.7-4.5.8, 4.10.8)."""
from __future__ import annotations

from app.data.setup import SETUP_BY_PLAYER_COUNT
from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .models import GameState

TAX_HAVEN_PRIVATE = 16  # P16 does not count towards the limit (3.1.5, 4.2.2)
LNWR = "LNWR"


def certificate_limit(state: GameState) -> int:
    """Rule 4.2.1: limit by number of players."""
    n = len(state.players) or len(state.player_order)
    setup = SETUP_BY_PLAYER_COUNT.get(n)
    if setup is None:  # outside the table: use the nearest listed player count
        n = min(SETUP_BY_PLAYER_COUNT, key=lambda k: abs(k - n))
        setup = SETUP_BY_PLAYER_COUNT[n]
    return setup.certificate_limit


def _in_yellow_zone(state: GameState, company_id: str) -> bool:
    pos = state.stock_positions.get(company_id)
    if pos is None:
        return False
    cell = STOCK_MARKET_BY_POSITION.get(pos)
    return cell is not None and cell.zone == "yellow"


def _private_counts(state: GameState, number: int) -> bool:
    if number == TAX_HAVEN_PRIVATE:
        return False
    p = state.privates.get(number)
    if p is not None and (p.closed or p.owner_company_id is not None):
        return False
    return True


def owned_certificate_count(state: GameState, player_id: str) -> int:
    """Rules 4.2.2-4.2.3: privates (not P16), concessions and share certificates
    (not those of yellow-zone companies). A major's director's certificate is
    one certificate although it is two 10% units."""
    player = state.players[player_id]
    total = sum(1 for n in player.private_companies if _private_counts(state, n))
    total += len(player.concessions)
    for cid, units in player.shares.items():
        if units <= 0 or _in_yellow_zone(state, cid):
            continue
        major = state.majors.get(cid)
        if major is not None and major.director_player_id == player_id and cid != LNWR and units >= 2:
            units -= 1  # 2-unit director's certificate is one certificate
        total += units
    return total


def bid_certificate_count(state: GameState, player_id: str) -> int:
    """Rule 4.10.8: each item (any kind) on which the player holds the highest bid."""
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
