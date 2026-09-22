"""Certificate-limit accounting (rule 4.2). A player's certificate count is
the sum of: private companies owned, concessions currently winning a bid on,
major/minor share certificates owned, plus any bid-box item they currently
hold the top bid on (rule 4.10.8) - except shares of a company whose stock
market token sits in the yellow zone (rule 4.2.3) and P16 tax haven holdings
(rule 3.1.5), which are exempt.
"""
from __future__ import annotations

from app.data.major_companies import LNWR_ABBR
from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .models import GameState


def _in_yellow_zone(state: GameState, company_id: str) -> bool:
    pos = state.stock_positions.get(company_id)
    if pos is None:
        return False
    cell = STOCK_MARKET_BY_POSITION.get(pos)
    return bool(cell and cell.zone == "yellow")


def owned_certificate_count(state: GameState, player_id: str) -> int:
    player = state.players[player_id]
    total = len(player.private_companies) + len(player.concessions)  # rule 3.4.3

    for company_id, units in player.shares.items():
        if _in_yellow_zone(state, company_id):
            continue
        is_director = (
            state.majors.get(company_id) is not None
            and state.majors[company_id].director_player_id == player_id
        ) or (
            state.minors.get(company_id) is not None
            and state.minors[company_id].director_player_id == player_id
        )
        # A major director's certificate is 2 units but 1 certificate (except
        # the LNWR, whose director's cert is 1 unit = 1 certificate, rule
        # 3.3.2). A minor's director's certificate is the whole 50% block,
        # tracked as 1 unit here (app.engine.models.Player.shares docstring),
        # so no adjustment needed for minors.
        is_major = company_id in state.majors
        if is_director and is_major and company_id != LNWR_ABBR:
            total += units - 1
        else:
            total += units

    return total


def bid_certificate_count(state: GameState, player_id: str) -> int:
    """Rule 4.10.8: each item a player currently holds the top bid on counts
    against their certificate limit, in addition to any they already own
    (P16 tax haven bids count too, per 4.10.8's parenthetical)."""
    count = 0
    for boxes in (state.concession_bid_boxes, state.minor_bid_boxes, state.private_bid_boxes):
        for item in boxes:
            if item is None or not item.bids:
                continue
            top_bidder = max(item.bids, key=lambda pid: item.bids[pid])
            if top_bidder == player_id:
                count += 1
    return count


def certificate_count(state: GameState, player_id: str) -> int:
    return owned_certificate_count(state, player_id) + bid_certificate_count(state, player_id)


def certificate_limit(state: GameState) -> int:
    from app.data.setup import SETUP_BY_PLAYER_COUNT

    return SETUP_BY_PLAYER_COUNT[len(state.players)].certificate_limit
