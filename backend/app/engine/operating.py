"""Operating round company actions (rule 5.3-5.5, 5.7-5.8, 5.11-5.12).

Scope for this pass: first-turn housekeeping (home station), tile-laying,
destination connection check, running trains, and earnings distribution
with the associated share-price movement. Train purchases (5.13-5.15) and
minor-company acquisition (5.16-5.18) are Task #7's job - they're tied to
company-lifecycle/phase concerns more than the core per-turn loop here.
"""
from __future__ import annotations

from app.data.hex_map import CITIES
from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .board import BoardState, TileLayError, apply_tile_lay, validate_tile_lay
from .hex_grid import neighbor as hex_neighbor
from .models import GameState
from .network import hex_neighbors_via_track, hex_track_edges
from .routes import run_trains
from .scoring import check_game_end_triggers
from .stock_positions import place_token


class OperatingError(Exception):
    pass


def home_hex_for(company_id: str, kind: str) -> str | None:
    for c in CITIES:
        if kind == "minor" and c.home_of_minor is not None:
            minors = c.home_of_minor if isinstance(c.home_of_minor, tuple) else (c.home_of_minor,)
            if any(f"M{n}" == company_id for n in minors):
                return c.id
        if kind == "major" and c.home_of_major is not None:
            majors = c.home_of_major if isinstance(c.home_of_major, tuple) else (c.home_of_major,)
            if company_id in majors:
                return c.id
    return None


def destination_hex_for(major_abbr: str) -> str | None:
    for c in CITIES:
        if c.destination_of_major == major_abbr:
            return c.id
    return None


def first_turn_housekeeping(state: GameState, board: BoardState, company_id: str, kind: str) -> None:
    """Rule 5.5.1: place the company's free home station token. Rule 5.5.3:
    a minor with no train yet may (not must) buy an L-train on this first
    turn - attempted automatically here if affordable, since a minor must
    own a train by the end of its turn (rule 3.2.9) and this is its only
    chance to get an L specifically."""
    if kind == "minor":
        minor = state.minors[company_id]
        if minor.home_token_placed:
            return
        minor.home_token_placed = True
        if not minor.trains:
            from .trains import TrainError, buy_train_from_bank

            try:
                buy_train_from_bank(state, company_id, kind, "L")
            except TrainError:
                pass  # no L-trains left, or can't afford one - leave for a forced purchase later
    else:
        major = state.majors[company_id]
        if major.home_token_placed:
            return
        major.home_token_placed = True
        home_hex = home_hex_for(company_id, "major")
        if home_hex is not None:
            major.tokens_on_map.append(home_hex)


def reachable_hexes_for_tile_lay(state: GameState, board: BoardState, company_id: str, kind: str) -> set[str]:
    """Rule 5.7.9: a company may only lay track on a hex that connects to
    its own network - not anywhere on the board. "Connects" means: is one
    of the company's own station hexes (home, or another token for a major
    - always layable, this is how a network bootstraps), already has a tile
    reached by the company's existing track (always layable - an upgrade),
    or is empty and sits across an edge that an already-reached hex actually
    has track running to (a legal target for a brand new tile).

    Found via manual testing: this wasn't checked at all before - any hex
    id, connected or not, showed every phase-legal tile as placeable."""
    home = home_hex_for(company_id, kind)
    stations: set[str] = {home} if home else set()
    if kind == "major":
        stations |= set(state.majors[company_id].tokens_on_map)
    if not stations:
        return set()

    tiled_component: set[str] = set()
    frontier = [h for h in stations if h in board.tiles]
    seen = set(frontier)
    while frontier:
        current = frontier.pop()
        tiled_component.add(current)
        for nxt in hex_neighbors_via_track(board, current):
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)

    legal = set(stations) | tiled_component
    for hx in tiled_component:
        for edge in hex_track_edges(board, hx):
            n = hex_neighbor(hx, edge)
            if n is not None:
                legal.add(n)
    return legal


def lay_track(
    state: GameState,
    board: BoardState,
    company_id: str,
    kind: str,
    hex_id: str,
    tile_id: str,
    rotation: int,
    treasury_field_owner,  # object with a .treasury int attribute to deduct terrain cost from
) -> int:
    """Validates and applies a tile lay, deducting any terrain cost from the
    company's treasury. Returns the cost paid."""
    if hex_id not in reachable_hexes_for_tile_lay(state, board, company_id, kind):
        raise OperatingError(
            f"{hex_id} isn't connected to {company_id}'s track network (rule 5.7.9)."
        )
    try:
        cost = validate_tile_lay(board, state.phase, hex_id, tile_id, rotation, company_kind=kind)
    except TileLayError as e:
        raise OperatingError(str(e)) from e
    if cost > treasury_field_owner.treasury:
        raise OperatingError("Insufficient treasury funds to pay the terrain cost.")
    treasury_field_owner.treasury -= cost
    apply_tile_lay(board, hex_id, tile_id, rotation)
    return cost


def check_destination_connection(board: BoardState, state: GameState, major_abbr: str) -> bool:
    """Rule 5.8: has the company connected its home to its destination by
    track (any length)? Simple reachability, not a revenue-optimal route -
    if so and the destination token isn't placed yet, places it (free)."""
    major = state.majors[major_abbr]
    if major.destination_token_placed:
        return True
    home = home_hex_for(major_abbr, "major")
    dest = destination_hex_for(major_abbr)
    if home is None or dest is None:
        return False
    if _reachable(board, home, dest):
        major.destination_token_placed = True
        major.tokens_on_map.append(dest)
        return True
    return False


def _reachable(board: BoardState, start: str, goal: str) -> bool:
    if start == goal:
        return True
    seen = {start}
    frontier = [start]
    while frontier:
        current = frontier.pop()
        for nxt in hex_neighbors_via_track(board, current):
            if nxt == goal:
                return True
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    return False


def run_trains_for_company(
    board: BoardState, state: GameState, company_id: str, kind: str, station_hexes: list[str],
) -> tuple[int, list]:
    trains = state.minors[company_id].trains if kind == "minor" else state.majors[company_id].trains
    return run_trains(board, state.phase, station_hexes, trains)


def distribute_earnings(state: GameState, company_id: str, kind: str, revenue: int, choice: str) -> int:
    """choice: "full" | "half" | "withhold". Returns the dividend actually
    paid out (used by the caller to move the stock price, rule 5.12.7-14)."""
    if kind == "minor":
        # Rule 5.12.1: a minor always splits 50/50 between treasury and director.
        # Both halves are sourced from the bank (revenue is bank-funded).
        minor = state.minors[company_id]
        half = revenue // 2
        minor.treasury += revenue - half
        director = state.players.get(minor.director_player_id)
        if director is not None:
            director.cash += half
        state.bank.cash -= revenue
        dividend_paid = half  # for price-movement purposes (rule 5.12.12)
        _move_minor_price(state, company_id, dividend_paid)
        return dividend_paid

    major = state.majors[company_id]
    if choice == "withhold":
        major.treasury += revenue
        state.bank.cash -= revenue
        dividend_paid = 0
    elif choice == "full":
        dividend_paid = revenue
        _pay_major_dividend(state, company_id, revenue)
    elif choice == "half":
        half = (revenue // 2)
        if half % 10 != 0:
            half = half + (10 - half % 10)  # rule 5.12.2: rounded up to next £10
        half = min(half, revenue)
        treasury_portion = revenue - half
        major.treasury += treasury_portion
        state.bank.cash -= treasury_portion
        dividend_paid = half
        _pay_major_dividend(state, company_id, half)
    else:
        raise OperatingError(f"Unknown dividend choice {choice!r}")

    _move_major_price(state, company_id, dividend_paid)
    return dividend_paid


def _pay_major_dividend(state: GameState, company_id: str, amount: int) -> None:
    """Rule 5.12.3: £(amount/10) per 10% share; treasury-held shares' portion
    goes to the company treasury. Bank-pool-held shares' portion is simply
    never taken from the bank - nobody owns them to receive it."""
    major = state.majors[company_id]
    per_share = amount // 10 if amount else 0  # amount is expected to already be a multiple of £10 in practice
    paid_units = 0
    for player in state.players.values():
        units = player.shares.get(company_id, 0)
        if units:
            player.cash += per_share * units
            paid_units += units
    treasury_units = major.shares_in_treasury
    major.treasury += per_share * treasury_units
    paid_units += treasury_units
    state.bank.cash -= per_share * paid_units


def _move_major_price(state: GameState, company_id: str, dividend_paid: int) -> None:
    price = _current_price(state, company_id)
    if dividend_paid == 0:
        _move_price(state, company_id, -1)
    elif dividend_paid >= 2 * price:
        _move_price(state, company_id, +2)
    elif dividend_paid >= price:
        _move_price(state, company_id, +1)
    # else: dividend_paid < price -> token does not move (rule 5.12.9)


def _move_minor_price(state: GameState, company_id: str, dividend_paid: int) -> None:
    _move_price(state, company_id, +1 if dividend_paid > 0 else -1)


def _current_price(state: GameState, company_id: str) -> int:
    row, col = state.stock_positions[company_id]
    return STOCK_MARKET_BY_POSITION[(row, col)].value


def _move_price(state: GameState, company_id: str, steps: int) -> None:
    """Moves right (steps>0) or left (steps<0) along the company's row,
    following the arrows at the row ends per rule 5.12.13/1.6 if the move
    would run off the printed grid (not yet implemented - see
    app.data.stock_market's module docstring; for now the token simply
    stops at the edge of its row, which under-moves it in that case)."""
    row, col = state.stock_positions[company_id]
    direction = 1 if steps > 0 else -1
    remaining = abs(steps)
    while remaining > 0:
        candidate = (row, col + direction)
        if candidate not in STOCK_MARKET_BY_POSITION:
            break
        row, col = candidate
        remaining -= 1
    place_token(state, company_id, row, col)
    check_game_end_triggers(state)  # catch the moment a token reaches £700, not just turn-end
