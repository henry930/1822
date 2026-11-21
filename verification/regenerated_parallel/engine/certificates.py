"""Certificate limit and certificate counting (rules 4.2.1-4.2.3, 4.10.8)."""
from __future__ import annotations

from app.data.setup import SETUP_BY_PLAYER_COUNT
from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .models import GameState

LNWR = "LNWR"
TAX_HAVEN_PRIVATE = 16


def certificate_limit(state: GameState) -> int:
    """Rule 4.2.1: limit by number of players."""
    n = len(state.players)
    setup = SETUP_BY_PLAYER_COUNT.get(n)
    if setup is None:
        # outside the table: clamp to the nearest defined player count
        n = min(max(n, min(SETUP_BY_PLAYER_COUNT)), max(SETUP_BY_PLAYER_COUNT))
        setup = SETUP_BY_PLAYER_COUNT[n]
    return setup.certificate_limit


def _in_yellow_zone(state: GameState, company_id: str) -> bool:
    pos = state.stock_positions.get(company_id)
    if pos is None:
        return False
    cell = STOCK_MARKET_BY_POSITION.get(tuple(pos))
    return cell is not None and cell.zone == "yellow"


def owned_certificate_count(state: GameState, player_id: str) -> int:
    """Rules 4.2.2-4.2.3: privates (not P16), concessions and share certificates
    held by the player. A major's director's certificate is one certificate
    (two units; LNWR's is one unit); a minor's is one. Shares of companies in
    the yellow zone are exempt. P16 charter shares (tax_haven_shares) are not
    in Player.shares and are not counted."""
    player = state.players[player_id]
    total = 0

    for num in player.private_companies:
        if num == TAX_HAVEN_PRIVATE:
            continue
        ps = state.privates.get(num)
        if ps is not None and (ps.closed or ps.owner_company_id is not None):
            continue
        total += 1

    total += len(player.concessions)

    for cid, units in player.shares.items():
        if units <= 0 or _in_yellow_zone(state, cid):
            continue
        major = state.majors.get(cid)
        if major is not None and cid != LNWR and major.director_player_id == player_id and units >= 2:
            total += units - 1  # director's certificate (2 units) is a single certificate
        else:
            total += units
    return total


def bid_certificate_count(state: GameState, player_id: str) -> int:
    """Rule 4.10.8: each item on which the player holds the highest bid counts 1."""
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
