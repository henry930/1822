"""Stock market token handling, price/operating order, stock-round order (layer 1)."""
from __future__ import annotations

from typing import Iterable

from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .models import GameState
from . import stock_positions as _sp


class MarketError(Exception):
    def __init__(self, code: str, text: str = ""):
        self.code = code
        super().__init__(f"{code}: {text}" if text else code)


# start cells derived from the grid: price -> (row, col)
_START_CELLS: dict[int, tuple[int, int]] = {}
for _pos, _c in STOCK_MARKET_BY_POSITION.items():
    if _c.zone in ("start", "minor_start"):
        _START_CELLS[_c.value] = _pos
_MAJOR_PRICES = tuple(p for p in range(60, 101, 10))
_MINOR_PRICES = tuple(p for p in range(50, 101, 10))


def token_cell(state, company_id):
    pos = state.stock_positions.get(company_id)
    if pos is None:
        return None
    return (pos[0], pos[1])


def current_price(state, company_id):
    pos = token_cell(state, company_id)
    if pos is None:
        raise MarketError("ERR_NO_TOKEN", f"company {company_id} has no token on the market")
    return STOCK_MARKET_BY_POSITION[pos].value


def in_yellow(state, company_id):
    pos = token_cell(state, company_id)
    return pos is not None and STOCK_MARKET_BY_POSITION[pos].zone == "yellow"


def is_game_end_cell(state, company_id):
    pos = token_cell(state, company_id)
    return pos is not None and bool(STOCK_MARKET_BY_POSITION[pos].game_end)


def start_cell(price, kind="major"):
    if kind not in ("major", "minor"):
        raise MarketError("ERR_BAD_KIND", f"kind must be 'major' or 'minor', got {kind!r}")
    allowed = _MAJOR_PRICES if kind == "major" else _MINOR_PRICES
    if isinstance(price, bool) or not isinstance(price, int) or price not in allowed:
        raise MarketError("ERR_BAD_START_PRICE", f"{price!r} is not a start price for a {kind}")
    return _START_CELLS[price]


def place_start_token(state, company_id, price, kind="major"):
    row, col = start_cell(price, kind)
    old = state.stock_positions.get(company_id)
    if old is not None:
        st = state.stock_stack.get(old)
        if st and company_id in st:
            st.remove(company_id)
    pile = state.stock_stack.setdefault((row, col), [])
    if kind == "major":
        pile.append(company_id)
    else:
        idx = 0
        while idx < len(pile) and pile[idx] in state.minors:
            idx += 1
        pile.insert(idx, company_id)
    state.stock_positions[company_id] = (row, col)


def move_token_down(state, company_id, steps=1):
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 0:
        raise MarketError("ERR_BAD_STEPS", f"steps must be an int >= 0, got {steps!r}")
    pos = token_cell(state, company_id)
    if pos is None:
        raise MarketError("ERR_NO_TOKEN", f"company {company_id} has no token on the market")
    row, col = pos
    for _ in range(steps):
        if (row + 1, col) in STOCK_MARKET_BY_POSITION:
            row += 1
        else:
            break
    if (row, col) != pos:
        _sp.place_token(state, company_id, row, col)


def move_token_up(state, company_id):
    pos = token_cell(state, company_id)
    if pos is None:
        raise MarketError("ERR_NO_TOKEN", f"company {company_id} has no token on the market")
    new = (pos[0] - 1, pos[1])
    if new not in STOCK_MARKET_BY_POSITION:
        return
    _sp.place_token(state, company_id, new[0], new[1])
    if STOCK_MARKET_BY_POSITION[new].game_end:
        from . import scoring  # lazy (higher layer)
        scoring.check_game_end_triggers(state, "after_token_move")


def descending_order(state, company_ids):
    ids = list(company_ids)
    for c in ids:
        if token_cell(state, c) is None:
            raise MarketError("ERR_NO_TOKEN", f"company {c} has no token on the market")
    return sorted(ids, key=lambda c: _sp.descending_price_key(state, c))


def operating_order(state):
    minors = [
        cid for cid, m in state.minors.items()
        if m.director_player_id is not None and not m.removed
        and not m.acquired_by_major and token_cell(state, cid) is not None
    ]
    majors = [
        cid for cid, m in state.majors.items()
        if m.floated and token_cell(state, cid) is not None
    ]
    return descending_order(state, minors) + descending_order(state, majors)


def next_operating_company(state, done=()):
    done = set(done)
    for cid in operating_order(state):
        if cid not in done:
            return cid
    return None


def compute_stock_round_order(cash, previous_order):
    if set(cash) != set(previous_order):
        raise MarketError("ERR_PLAYER_MISMATCH", "cash keys differ from previous order players")
    return sorted(previous_order, key=lambda p: -cash[p])


def reorder_players_by_cash(state):
    cash = {p: state.players[p].cash for p in state.player_order}
    new = compute_stock_round_order(cash, list(state.player_order))
    state.player_order = new
    state.priority_deal_player_id = new[0] if new else None


def raise_sold_out_prices(state):
    from . import certificates  # lazy (higher layer)
    affected = [
        cid for cid, m in state.majors.items()
        if m.floated and token_cell(state, cid) is not None
        and certificates.fully_sold(state, cid)
    ]
    for cid in descending_order(state, affected):
        move_token_up(state, cid)


market_cell = token_cell
share_price = current_price
descending_share_price_order = descending_order
next_player_order = compute_stock_round_order
reorder_players = reorder_players_by_cash
