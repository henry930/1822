# Contract: `backend/app/engine/turn_order.py`  (graph component `comp.market` + 3 items of `comp.sr_resolution`)

Read COMMON.md and BINDING.md first. Layer 1: no module-level import of any new module.
Top-level imports allowed: `models`, `stock_positions` (`place_token`, `descending_price_key`, `cell_value`),
`app.data.stock_market` (`STOCK_MARKET_BY_POSITION`). LAZY imports: `from .scoring import check_game_end_triggers` (inside
`move_token_up`), `from .certificates import fully_sold` (inside `raise_sold_out_prices`).

Given callers: none import this file. All callers are the new modules (BINDING C.3).
Exception: `class MarketError(Exception)` (message prefix = error code, COMMON 2).

Data (BINDING A.3): cell exists iff `(row, col) in STOCK_MARKET_BY_POSITION`; yellow = `cell.zone == "yellow"`;
game end = `cell.game_end`; start cells: 100->(4,4), 90->(5,4), 80->(6,4), 70->(7,4), 60->(8,4), 50->(9,4) (found as the cells
with `zone in {"start","minor_start"}`; derive them from the table at import time, do not hard-code).
Pile order: `state.stock_stack[cell]`, index 0 = top. Company ids: major abbr or `"M<n>"`.

---------------------------------------------------------------------------------------------------------------------
## 1. Derived functions

### `token_cell(state, cid) -> tuple[int,int] | None`   (`drv.token_cell`, rule 1.6.1)
Formula: the cell whose pile contains the company = `state.stock_positions.get(cid)`.

### `current_price(state, cid) -> int`   (`drv.current_price`, 1.6.1; uses `const.market_grid`)
Formula: `grid_value(token_cell(cid))` = `STOCK_MARKET_BY_POSITION[cell].value`.
Error: no token -> `MarketError("ERR_NO_TOKEN: ...")` (graph error of `move_token_down/up`; for `current_price` the graph
gives no error: GAP).

### `in_yellow(state, cid) -> bool`   (`drv.in_yellow`, 1.6.5, 4.2.3, 4.5.8)
Formula: `token_cell(cid) in yellow_cells`; False if the company has no token.

### `start_cell(price, kind="major") -> (row, col)`   (`drv.start_cell`, 1.6.3, 1.6.4)
Formula: `const.start_cells[price]`. Valid prices: majors 60,70,80,90,100; minors 50,60,...,100 (50 solid red = minors only, 1.6.3).
Error: price not valid for the kind -> `MarketError("ERR_BAD_START_PRICE: ...")` (the `kind` parameter is an addition needed to
express "50 allowed for minors only", 1.6.3; the graph's `start_cell(price)` has no kind).

### `is_game_end_cell(state, cid) -> bool`   (`drv.is_game_end_cell`, 10.1.1)
Formula: `token_cell(cid) in game_end_cells`; False if no token.

### `descending_order(state, company_ids) -> list[str]`   (`drv.descending_order`, 1.6.2, 2.1.5; A26)
Formula: sort by key `(-price, -col, pile_index_from_top)`: price descending; same price -> larger column first; same cell ->
topmost first. This is exactly `stock_positions.descending_price_key(state, cid)`; use it:
`sorted(company_ids, key=lambda c: descending_price_key(state, c))`. (Graph assumption A26 "same price, same column, different rows:
upper row first" is not implemented by the given key; do not add it. See Graph gaps.)

### `operating_order(state) -> list[str]`   (`drv.operating_order`, 5.2.1)
Formula: floated minors (`minor.director_player_id is not None` and the company has a token on the market), in
`descending_order`, then floated majors (`major.floated` and token on the market) in `descending_order`. Result = list of company ids.

### `next_operating_company(state, done) -> str | None`   (`drv.next_operating_company`, 5.2.2)
Formula: recompute `operating_order(state)` NOW and return the first company not in `done` (an iterable of company ids already run
this operating round); `None` if there is none. Minors precede majors by construction of `operating_order`.

### `compute_stock_round_order(cash: dict[str,int], previous_order: list[str]) -> list[str]`   (`drv.compute_stock_round_order`, 4.11.9)
Formula: players sorted by cash descending; players with equal cash keep their relative order in `previous_order`
(stable sort). P9 exception deferred (R11): do not implement.

---------------------------------------------------------------------------------------------------------------------
## 2. Actions

### `place_start_token(state, cid, price, kind)`   (`act.place_start_token`; rules 1.6.3, 1.6.4, 4.7.2, 4.11.5)
Preconditions: price is a valid start value for `kind` (major: 60..100; minor: 50..100) (1.6.3, 1.6.4).
Error: `ERR_BAD_START_PRICE` -> `MarketError`.
Effects:
1. `cell = start_cell(price, kind)` (call; graph edge place_start_token -> start_cell).
2. `kind == "major"` [4.7.2]: insert the company at the BOTTOM of the pile in `cell` (i.e. `stock_positions.place_token(state, cid, *cell)`).
3. `kind == "minor"` [4.11.5]: insert above every major token and below the existing minor tokens in the cell:
   index = number of consecutive minor tokens at the top of the pile (entries that are keys of `state.minors`, counted from index 0
   until the first non-minor); `stock_stack[cell].insert(index, cid)`; set `stock_positions[cid] = cell`.
   (Use `setdefault` for the pile; remove the company from any old pile first.)

### `move_token_down(state, cid, steps)`   (`act.move_token_down`; 4.4.4, 4.4.5, R12)
Precondition: the company has a token (1.6.1). Error `ERR_NO_TOKEN` -> `MarketError`.
Effects: [4.4.4, R12] `row' = row`; repeat `steps` times: if cell `(row'+1, col)` exists then `row' += 1` else stop.
[4.4.5] if the cell changed: remove from old pile and put at the BOTTOM of the destination pile (`place_token(state, cid, row', col)`);
if it did not change: do nothing at all (keeps its place in the pile). `steps` is a non-negative int.

### `move_token_up(state, cid)`   (`act.move_token_up`; 4.12.1, 4.12.2, R12, 10.1.1)
Precondition: token exists (`ERR_NO_TOKEN`).
Effects: [4.12.1, R12] if cell `(row-1, col)` exists: move there, else no move. [4.12.2] arrives at the BOTTOM of the destination
pile (`place_token`). [10.1.1] if a move happened and the new cell is a game-end cell: LAZY call
`scoring.check_game_end_triggers(state, "after_token_move")`.

### `raise_sold_out_prices(state)`   (`act.raise_sold_out_prices`; 4.12.1, 4.12.2, 4.12.3, R13)
Precondition: only floated majors; minors never qualify (4.12.3).
Effects: [4.12.1, R13] `affected` = floated majors `c` for which (LAZY) `certificates.fully_sold(state, c)` is true.
[4.12.2] `order = descending_order(state, affected)` computed ONCE before any move (A22); then for `c in order`: `move_token_up(state, c)`.
Called by `bidding.resolve_stock_round` step 7 (after `charge_interest`, before `reorder_players_by_cash`).

### `reorder_players_by_cash(state)`   (`act.reorder_players_by_cash`; 4.11.9)
Precondition: after bid payments (i.e. step 8 of resolution).
Effects: `state.player_order = compute_stock_round_order({pid: players[pid].cash}, state.player_order)`; and
`state.priority_deal_player_id = state.player_order[0]` (BINDING A.1 `st.sr_order`).
Do not touch `active_player_id` (round_manager does at the start of the next stock round).

---------------------------------------------------------------------------------------------------------------------
## 3. Obligations of others toward this file / by this file
- Called by: shares.sell_shares (`current_price`, `move_token_down`), shares.buy_share (`current_price`, `in_yellow`),
  company_formation.convert_concession and float_minors (`place_start_token`), scoring (`token_cell`, `is_game_end_cell`),
  certificates (`in_yellow`), bidding.resolve_stock_round (`raise_sold_out_prices` step 7, `reorder_players_by_cash` step 8),
  round_manager (`operating_order`, `next_operating_company`).
- This file never writes money or shares.
- Writers of `stock_positions`/`stock_stack`: only functions in this file (plus the given `operating._move_price`).

## Graph gaps (do not decide; report)
1. `current_price` has no error for a company without a token (graph error list only on the move actions).
2. A26 (same price, same column, different rows -> upper row) is stated in the graph but the given `descending_price_key` does not implement it; contract says use the given key.
3. 4.11.5 placement when minors and majors are interleaved in a pile (operating-round moves via `place_token` can put a minor below a major): graph rule is "above every major, below existing minors" which cannot both hold then; contract uses "after the leading run of minor tokens".
4. `move_token_down`/`up` with `steps < 0` or non-int: unspecified.
5. `operating_order` for a minor that is `removed`/acquired: graph says "floated minors (minor_director != null and token on market)"; no acquisition state exists in the graph.
6. `descending_order` of a company without token: unspecified (use `MarketError ERR_NO_TOKEN` via `token_cell` None).
7. R11 arrows: graph and ruling say up/down only; row-end arrow moves for dividends live in given operating.py, not here.
