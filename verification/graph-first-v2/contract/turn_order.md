# Contract: `backend/app/engine/turn_order.py`

Generated mechanically from graph v2 by gen_contracts.py. Read COMMON.md first, then this file; BINDING.md lists the representation rules and the cross-module call matrix.

Import layering: this module is layer 1 (1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares and company_formation, 6 bidding, 7 round_manager). Calls to a HIGHER layer must be lazy imports inside the function body; never import upward at module level.

## 1. Export list (every name below, plus every alias, must exist at module level)

- `MarketError` (exception)
- `token_cell` (function)  aliases: market_cell
- `current_price` (function)  aliases: share_price
- `in_yellow` (function)
- `is_game_end_cell` (function)
- `start_cell` (function)
- `place_start_token` (function)
- `move_token_down` (function)
- `move_token_up` (function)
- `descending_order` (function)  aliases: descending_share_price_order
- `operating_order` (function)
- `next_operating_company` (function)
- `compute_stock_round_order` (function)  aliases: next_player_order
- `reorder_players_by_cash` (function)  aliases: reorder_players
- `raise_sold_out_prices` (function)

Public API count: 15

## 2. Module-level obligations

### States this module writes (flags and data it is responsible for)
- `st.market_stack` (Market piles): Which company tokens sit on which cell and their pile order. Company price = value of its cell. Pile order decides ties (1.6.2, 4.4.5, 4.12.2, 5.2.2). -- written by `act.place_start_token`, `act.move_token_down`, `act.move_token_up`
- `st.sr_order` (Stock-turn order): Order in which players take stock turns; random at setup (1.7.12); recomputed by cash at each stock-round end (4.11.9). Also the direction for 'nearest after' tie-breaks (4.4.2). The player holding card 1 (index 0) is the start player of every stock round. -- written by `act.reorder_players_by_cash`

### Hooks / triggers fired by this module's nodes
- (none)

### Notes that name 'sets ... itself' / flags (from api notes)
- `MarketError`: Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. Raised for market lookups on a company without a token and for invalid start prices.
- `move_token_up`: Calls scoring.check_game_end_triggers(state, 'after_token_move') (LAZY import) after a move onto a game-end cell.
- `reorder_players_by_cash`: Writes BOTH state.player_order and state.priority_deal_player_id (= player_order[0]).
- `raise_sold_out_prices`: Snapshot of affected companies and order taken once before any move (A22). Lazy-imports certificates.fully_sold.

### Module-level decisions (resolve any api or node of this module)
- **GA38** (gap A.2.38, severity S3, kind decision): ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).
  reason: layering (no module for a shared base) and the given except clauses.
- **GB19** (gap B-19, severity S3, kind decision): Layers: 1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares + company_formation, 6 bidding, 7 round_manager; upward calls are lazy imports (api node attrs.layer; lazy edges: turn_order->scoring.check_game_end_triggers, turn_order->certificates.fully_sold, certificates->bidding.items_led, trains->bidding.clear_concession_boxes, bidding->nothing upward now that resolve_stock_round has no sr_over check).
  reason: circular imports.
- **GB11** (gap B-11, severity S3, kind graph_fix): Derived start_cell(price, kind='major') in the graph itself.
  reason: 1.6.3.
- **GA28** (gap A.2.28, severity S3, kind graph_fix): Minor tokens are inserted directly after the leading run of minor tokens in the pile.
  reason: satisfies 'above every major, below existing minors' when minors lead the pile.
- **GB25** (gap B-25, severity S3, kind graph_fix): See GA28.
  reason: GA28.
- **GA17** (gap A.1.17, severity S3, kind carried): R12 stands (down = row+1 same column; absent cell = no move). operating._move_price (given) moves along rows for dividends and is independent of the new market functions; consistency risk noted, not a graph change.
  reason: no new evidence.
- **GA29** (gap A.2.29, severity S3, kind decision): A26 is withdrawn: descending_order uses the given stock_positions.descending_price_key unchanged.
  reason: the case cannot occur on the given grid.
- **GA31** (gap A.2.31, severity S2, kind graph_fix): operating_order excludes minors with acquired_by_major set and removed minors; acquisition itself is out of scope.
  reason: field exists in the model.
- **GA40** (gap A.2.40, severity S3, kind repr): Always equal to player_order[0]: set by setup, rewritten by reorder_players_by_cash, re-asserted by start_stock_round.
  reason: single source of truth.

## 3. API contracts

### `turn_order.MarketError` (exception)

```python
class MarketError(Exception)
```

- bases: ['Exception']; message `<ERR_CODE>: <text>`; attribute `.code` = ERR_CODE
- raised by: turn_order.compute_stock_round_order, turn_order.current_price, turn_order.descending_order, turn_order.move_token_down, turn_order.move_token_up, turn_order.place_start_token, turn_order.start_cell
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 1
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. Raised for market lookups on a company without a token and for invalid start prices.

**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA38** (gap A.2.38, severity S3, kind decision): ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).
  reason: layering (no module for a shared base) and the given except clauses.

### `turn_order.token_cell` (function)

```python
token_cell(state: GameState, company_id: str) -> tuple[int, int] | None
```

- parameters: ['state', 'company_id']
- defaults (explicit): (none)
- returns: (row, col) or None
- layer: 1
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `market_cell`
- callers in given code: none
- callers from graph (calls/triggers): scoring.check_game_end_triggers, turn_order.current_price, turn_order.descending_order, turn_order.in_yellow, turn_order.is_game_end_cell, turn_order.move_token_down, turn_order.move_token_up

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- company_id need not exist: an unknown or tokenless company gives None, no exception

**Implements graph node(s)**: `drv.token_cell`

#### Graph node `drv.token_cell` (derived) - Token cell
Cell where a company's token sits.

- graph signature (abstract): params = ['company c']; returns = cell

**Formula**: [1.6.1] the cell whose pile in market_stack contains c

**State touched**:
- reads `st.market_stack` (Market piles): Which company tokens sit on which cell and their pile order. Company price = value of its cell. Pile order decides ties (1.6.2, 4.4.5, 4.12.2, 5.2.2). [type map cell->ordered list<company> (index 0 = top); unit company ids; scope game]

**Rules constraining this node**:
- 1.6.1: Share price = value of the cell holding the company's token. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Stock market cells and piles** [repr.market_cells]: maps to: state.stock_positions[company_id] = (row, col); state.stock_stack[(row, col)] = list of company ids, index 0 = TOP; grid app.data.stock_market.STOCK_MARKET_BY_POSITION[(row, col)] -> StockCell(row, col, value, zone, game_end)
  rule for coder: Use stock_positions.place_token (removes from the old pile, APPENDS to the new = bottom) only when the cell changes; emptied piles remain as empty lists; down = (row+1, col), up = (row-1, col), absent cell = no move (R12); yellow = zone 'yellow'; game end = game_end True; start cells derived from zone in {'start','minor_start'}. Minors enter after the leading run of minor tokens (4.11.5).


### `turn_order.current_price` (function)

```python
current_price(state: GameState, company_id: str) -> int
```

- parameters: ['state', 'company_id']
- defaults (explicit): (none)
- returns: value of the token's cell
- layer: 1
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `share_price`
- callers in given code: none
- callers from graph (calls/triggers): scoring.player_wealth, shares.buy_share, shares.sell_shares, turn_order.descending_order

**Exceptions**:

| class | code | when |
|---|---|---|
| MarketError | ERR_NO_TOKEN | the company has no token on the market |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. company has a token on the market -> `ERR_NO_TOKEN`

**Implements graph node(s)**: `drv.current_price`

#### Graph node `drv.current_price` (derived) - Current price
Share price of a company.

- graph signature (abstract): params = ['company c']; returns = int

**Formula**: [1.6.1] grid_value(token_cell(c))

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.token_cell -> `turn_order.token_cell` [same module] signature: `token_cell(state: GameState, company_id: str) -> tuple[int, int] | None` 

**Constants used**:
- `const.market_grid` (Stock market grid): The printed market: grid of cells (row, col), rows left-aligned (R12); value in pounds; down = (row+1, col), up = (row-1, col); a cell exists iff its key is in the table; absent cell = no move.; data: `{}`
  (in code: app.data.stock_market.STOCK_MARKET_BY_POSITION[(row, col)] -> StockCell(row, col, value, zone, game_end))

**Rules constraining this node**:
- 1.6.1: Share price = value of the cell holding the company's token. [formula]


### `turn_order.in_yellow` (function)

```python
in_yellow(state: GameState, company_id: str) -> bool
```

- parameters: ['state', 'company_id']
- defaults (explicit): (none)
- returns: False if the company has no token
- layer: 1
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): certificates.cert_count_holdings, shares.buy_share

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception for a tokenless company

**Implements graph node(s)**: `drv.in_yellow`

#### Graph node `drv.in_yellow` (derived) - In yellow zone?
True if the company's token is on a yellow cell.

- graph signature (abstract): params = ['company c']; returns = bool

**Formula**: [1.6.5, 4.2.3] token_cell(c) in yellow_cells; false if the company has no token

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.token_cell -> `turn_order.token_cell` [same module] signature: `token_cell(state: GameState, company_id: str) -> tuple[int, int] | None` 

**Constants used**:
- `const.yellow_cells` (Yellow zone cells): Cells of the yellow zone (1.6.5): StockCell.zone == 'yellow' (39 cells).; data: `{}`
  (in code: StockCell.zone == 'yellow')

**Rules constraining this node**:
- 1.6.5: Certificates of a company whose token is in a yellow cell do not count against the limit. [formula]
- 4.2.3: Share certificates of a company in the yellow zone don't count. [formula]
- 4.5.8: Yellow-zone stock does not count; buyable at the limit.


### `turn_order.is_game_end_cell` (function)

```python
is_game_end_cell(state: GameState, company_id: str) -> bool
```

- parameters: ['state', 'company_id']
- defaults (explicit): (none)
- returns: False if the company has no token
- layer: 1
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): scoring.check_game_end_triggers

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception for a tokenless company

**Implements graph node(s)**: `drv.is_game_end_cell`

#### Graph node `drv.is_game_end_cell` (derived) - Game-end cell?
True if the company's token is on a game-end cell.

- graph signature (abstract): params = ['company c']; returns = bool

**Formula**: [10.1.1] token_cell(c) in game_end_cells

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.token_cell -> `turn_order.token_cell` [same module] signature: `token_cell(state: GameState, company_id: str) -> tuple[int, int] | None` 

**Constants used**:
- `const.game_end_cells` (Game-end cells): Cells carrying the game-end value (10.1.1): StockCell.game_end is True (only (0,3), value 700).; data: `{}`
  (in code: StockCell.game_end is True)

**Rules constraining this node**:
- 10.1.1: Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. [formula]


### `turn_order.start_cell` (function)

```python
start_cell(price: int, kind: str = 'major') -> tuple[int, int]
```

- parameters: ['price', 'kind']
- defaults (explicit): {"kind": "'major'"}
- returns: (row, col)
- layer: 1
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): turn_order.place_start_token

**Exceptions**:

| class | code | when |
|---|---|---|
| MarketError | ERR_BAD_KIND | kind not in {'major','minor'} |
| MarketError | ERR_BAD_START_PRICE | price not a start value for the kind (major 60..100, minor 50..100) |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. kind in {'major','minor'} -> `ERR_BAD_KIND`
2. price in 60..100 step 10 for major; 50..100 step 10 for minor -> `ERR_BAD_START_PRICE`

**Implements graph node(s)**: `drv.start_cell`

#### Graph node `drv.start_cell` (derived) - Start cell for a price
Cell used to start a company at a given price.

- graph signature (abstract): params = ['price', 'kind in {major, minor}']; returns = cell

**Formula**: [1.6.3, 1.6.4] const.start_cells[price]; valid prices: major 60..100, minor 50..100 (50 is solid red, minors only); anything else is an error ERR_BAD_START_PRICE

**Constants used**:
- `const.start_cells` (Start cells): Start cells: cells with zone 'start' or 'minor_start'; price -> cell: 100->(4,4), 90->(5,4), 80->(6,4), 70->(7,4), 60->(8,4), 50->(9,4) (50 minors only).; data: `{"table": {"100": [4, 4], "90": [5, 4], "80": [6, 4], "70": [7, 4], "60": [8, 4], "50": [9, 4]}}`
  (in code: cells with zone in {'start','minor_start'}; derive at import, do not hard-code)
- `const.start_values` (Start values): Allowed starting share prices: 50 (solid red, minors only, 1.6.3), 60, 70, 80, 90, 100 (red-outlined, majors and minors, 1.6.4). Major start price must be in {60..100}.; data: `{"minor_values": [50, 60, 70, 80, 90, 100], "major_values": [60, 70, 80, 90, 100]}`

**Rules constraining this node**:
- 1.6.4: 60..100 cells are start cells for majors and minors. [formula]
- 1.6.3: Cell at 50 is solid red; only minors may start there. [formula]


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GB11** (gap B-11, severity S3, kind graph_fix): Derived start_cell(price, kind='major') in the graph itself.
  reason: 1.6.3.

### `turn_order.place_start_token` (function)

```python
place_start_token(state: GameState, company_id: str, price: int, kind: str = 'major') -> None
```

- parameters: ['state', 'company_id', 'price', 'kind']
- defaults (explicit): {"kind": "'major'"}
- returns: None
- layer: 1
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): company_formation.convert_concession, company_formation.float_minors

**Exceptions**:

| class | code | when |
|---|---|---|
| MarketError | ERR_BAD_KIND | bad kind |
| MarketError | ERR_BAD_START_PRICE | bad price for kind |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. kind in {'major','minor'} -> `ERR_BAD_KIND`
2. price valid for kind (start_cell) -> `ERR_BAD_START_PRICE`

**Must NOT be checked by this function**:
- company exists / is floated / has no token yet (re-placing simply moves the token)

**Implements graph node(s)**: `act.place_start_token`

#### Graph node `act.place_start_token` (action) - Place start token
Place a newly started company's token on its start cell.

- graph signature (abstract): params = ['company c', 'price', 'kind in {major, minor} (default major)']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [1.6.3] price is a valid start value for the kind: major 60..100; minor 50..100 (50 solid red = minors only)
- [1.6.4] kind is major or minor

**Effects, in order** (execute exactly in this order):
1. cell = start_cell(price, kind)
2. [4.7.2] major: insert c at the BOTTOM of the pile in cell
3. [4.11.5] minor: insert directly after the LEADING RUN of minor tokens at the top of the pile (index = number of consecutive minor tokens at the top; above every major token, below the existing leading minors) (GAP A28 fixed)

**Errors listed by the graph node**:
- ERR_BAD_START_PRICE
- ERR_BAD_KIND

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.start_cell -> `turn_order.start_cell` [same module] signature: `start_cell(price: int, kind: str = 'major') -> tuple[int, int]` 

**State touched**:
- reads `st.market_stack` (Market piles): Which company tokens sit on which cell and their pile order. Company price = value of its cell. Pile order decides ties (1.6.2, 4.4.5, 4.12.2, 5.2.2). [type map cell->ordered list<company> (index 0 = top); unit company ids; scope game]
- writes `st.market_stack` (Market piles): Which company tokens sit on which cell and their pile order. Company price = value of its cell. Pile order decides ties (1.6.2, 4.4.5, 4.12.2, 5.2.2). [type map cell->ordered list<company> (index 0 = top); unit company ids; scope game]

**Constants used**:
- `const.start_values` (Start values): Allowed starting share prices: 50 (solid red, minors only, 1.6.3), 60, 70, 80, 90, 100 (red-outlined, majors and minors, 1.6.4). Major start price must be in {60..100}.; data: `{"minor_values": [50, 60, 70, 80, 90, 100], "major_values": [60, 70, 80, 90, 100]}`

**Rules constraining this node**:
- 4.11.5: Minor tokens go on top of majors and beneath existing minors. [demanded in preconditions/effects]
- 1.6.4: 60..100 cells are start cells for majors and minors. [demanded in preconditions/effects]
- 1.6.3: Cell at 50 is solid red; only minors may start there. [demanded in preconditions/effects]
- 4.7.2: Convert, choose a red-outlined start price 60..100, place token under existing tokens. [demanded in preconditions/effects]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Stock market cells and piles** [repr.market_cells]: maps to: state.stock_positions[company_id] = (row, col); state.stock_stack[(row, col)] = list of company ids, index 0 = TOP; grid app.data.stock_market.STOCK_MARKET_BY_POSITION[(row, col)] -> StockCell(row, col, value, zone, game_end)
  rule for coder: Use stock_positions.place_token (removes from the old pile, APPENDS to the new = bottom) only when the cell changes; emptied piles remain as empty lists; down = (row+1, col), up = (row-1, col), absent cell = no move (R12); yellow = zone 'yellow'; game end = game_end True; start cells derived from zone in {'start','minor_start'}. Minors enter after the leading run of minor tokens (4.11.5).


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA28** (gap A.2.28, severity S3, kind graph_fix): Minor tokens are inserted directly after the leading run of minor tokens in the pile.
  reason: satisfies 'above every major, below existing minors' when minors lead the pile.
- **GB25** (gap B-25, severity S3, kind graph_fix): See GA28.
  reason: GA28.

### `turn_order.move_token_down` (function)

```python
move_token_down(state: GameState, company_id: str, steps: int = 1) -> None
```

- parameters: ['state', 'company_id', 'steps']
- defaults (explicit): {"steps": "1"}
- returns: (see signature)
- layer: 1
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): shares.sell_shares

**Exceptions**:

| class | code | when |
|---|---|---|
| MarketError | ERR_NO_TOKEN | no token |
| MarketError | ERR_BAD_STEPS | steps not an int >= 0 |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. steps is an int >= 0 (0 = no-op) -> `ERR_BAD_STEPS`
2. company has a token -> `ERR_NO_TOKEN`

**Must NOT be checked by this function**:
- no game-end check (a drop never reaches the top)

**Implements graph node(s)**: `act.move_token_down`

#### Graph node `act.move_token_down` (action) - Move token down
Price drop after a sale: move down one row per share sold.

- graph signature (abstract): params = ['company c', 'steps s']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [1.6.1] c has a token on the market

**Effects, in order** (execute exactly in this order):
1. [4.4.4, R12] row' = row; repeat s times: if cell (row'+1, col) exists then row' += 1 else stop
2. [4.4.5] if the cell changed: remove c from its pile and append at the BOTTOM of the destination pile; if not, keep its place in the pile

**Errors listed by the graph node**:
- ERR_NO_TOKEN

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.token_cell -> `turn_order.token_cell` [same module] signature: `token_cell(state: GameState, company_id: str) -> tuple[int, int] | None` 

**State touched**:
- reads `st.market_stack` (Market piles): Which company tokens sit on which cell and their pile order. Company price = value of its cell. Pile order decides ties (1.6.2, 4.4.5, 4.12.2, 5.2.2). [type map cell->ordered list<company> (index 0 = top); unit company ids; scope game]
- writes `st.market_stack` (Market piles): Which company tokens sit on which cell and their pile order. Company price = value of its cell. Pile order decides ties (1.6.2, 4.4.5, 4.12.2, 5.2.2). [type map cell->ordered list<company> (index 0 = top); unit company ids; scope game]

**Constants used**:
- `const.market_grid` (Stock market grid): The printed market: grid of cells (row, col), rows left-aligned (R12); value in pounds; down = (row+1, col), up = (row-1, col); a cell exists iff its key is in the table; absent cell = no move.; data: `{}`
  (in code: app.data.stock_market.STOCK_MARKET_BY_POSITION[(row, col)] -> StockCell(row, col, value, zone, game_end))

**Rules constraining this node**:
- 1.6.1: Share price = value of the cell holding the company's token. [demanded in preconditions/effects]
- 4.4.4: Token moves down one cell per share sold; stops at the bottom. [demanded in preconditions/effects]
- R12: Left-aligned rows as printed; price drop = down one row same column; no move if cell does not exist. [demanded in preconditions/effects]
- 4.4.5: Moved token goes to the bottom of the destination pile; unmoved token keeps its place. [demanded in preconditions/effects]
- R11: Out of scope: P16 exceptions, P9 exception, 4.8 direct formation from phase 5, stock-market arrows (provisional: off right end -> up one row same column; off left end -> down one row).

**Representation notes (repr nodes bound to touched states / this node)**:
- **Stock market cells and piles** [repr.market_cells]: maps to: state.stock_positions[company_id] = (row, col); state.stock_stack[(row, col)] = list of company ids, index 0 = TOP; grid app.data.stock_market.STOCK_MARKET_BY_POSITION[(row, col)] -> StockCell(row, col, value, zone, game_end)
  rule for coder: Use stock_positions.place_token (removes from the old pile, APPENDS to the new = bottom) only when the cell changes; emptied piles remain as empty lists; down = (row+1, col), up = (row-1, col), absent cell = no move (R12); yellow = zone 'yellow'; game end = game_end True; start cells derived from zone in {'start','minor_start'}. Minors enter after the leading run of minor tokens (4.11.5).


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA17** (gap A.1.17, severity S3, kind carried): R12 stands (down = row+1 same column; absent cell = no move). operating._move_price (given) moves along rows for dividends and is independent of the new market functions; consistency risk noted, not a graph change.
  reason: no new evidence.

### `turn_order.move_token_up` (function)

```python
move_token_up(state: GameState, company_id: str) -> None
```

- parameters: ['state', 'company_id']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 1
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): turn_order.raise_sold_out_prices
- api notes: Calls scoring.check_game_end_triggers(state, 'after_token_move') (LAZY import) after a move onto a game-end cell.

**Exceptions**:

| class | code | when |
|---|---|---|
| MarketError | ERR_NO_TOKEN | no token |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. company has a token -> `ERR_NO_TOKEN`

**Implements graph node(s)**: `act.move_token_up`

#### Graph node `act.move_token_up` (action) - Move token up
Price rise for a sold-out company: one row up, same column.

- graph signature (abstract): params = ['company c']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [1.6.1] c has a token on the market

**Effects, in order** (execute exactly in this order):
1. [4.12.1, R12] if cell (row-1, col) exists: move there, else no move
2. [4.12.2] appended at the BOTTOM of the destination pile
3. [10.1.1] if the new cell is a game-end cell: call check_game_end_triggers(after_token_move)

**Errors listed by the graph node**:
- ERR_NO_TOKEN

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.token_cell -> `turn_order.token_cell` [same module] signature: `token_cell(state: GameState, company_id: str) -> tuple[int, int] | None` 
- calls act.check_game_end_triggers -> `scoring.check_game_end_triggers` [CROSS-MODULE] signature: `check_game_end_triggers(state: GameState, context: str | None = None) -> None` 

**State touched**:
- reads `st.market_stack` (Market piles): Which company tokens sit on which cell and their pile order. Company price = value of its cell. Pile order decides ties (1.6.2, 4.4.5, 4.12.2, 5.2.2). [type map cell->ordered list<company> (index 0 = top); unit company ids; scope game]
- writes `st.market_stack` (Market piles): Which company tokens sit on which cell and their pile order. Company price = value of its cell. Pile order decides ties (1.6.2, 4.4.5, 4.12.2, 5.2.2). [type map cell->ordered list<company> (index 0 = top); unit company ids; scope game]

**Constants used**:
- `const.market_grid` (Stock market grid): The printed market: grid of cells (row, col), rows left-aligned (R12); value in pounds; down = (row+1, col), up = (row-1, col); a cell exists iff its key is in the table; absent cell = no move.; data: `{}`
  (in code: app.data.stock_market.STOCK_MARKET_BY_POSITION[(row, col)] -> StockCell(row, col, value, zone, game_end))

**Rules constraining this node**:
- 1.6.1: Share price = value of the cell holding the company's token. [demanded in preconditions/effects]
- R12: Left-aligned rows as printed; price drop = down one row same column; no move if cell does not exist. [demanded in preconditions/effects]
- 4.12.2: Move in descending price order, top to bottom within piles; moved token goes to bottom of pile. [demanded in preconditions/effects]
- 4.12.1: 100% in players' hands -> token up one cell; no move at the top. [demanded in preconditions/effects]
- 10.1.1: Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. [demanded in preconditions/effects]
- R11: Out of scope: P16 exceptions, P9 exception, 4.8 direct formation from phase 5, stock-market arrows (provisional: off right end -> up one row same column; off left end -> down one row).

**Representation notes (repr nodes bound to touched states / this node)**:
- **Stock market cells and piles** [repr.market_cells]: maps to: state.stock_positions[company_id] = (row, col); state.stock_stack[(row, col)] = list of company ids, index 0 = TOP; grid app.data.stock_market.STOCK_MARKET_BY_POSITION[(row, col)] -> StockCell(row, col, value, zone, game_end)
  rule for coder: Use stock_positions.place_token (removes from the old pile, APPENDS to the new = bottom) only when the cell changes; emptied piles remain as empty lists; down = (row+1, col), up = (row-1, col), absent cell = no move (R12); yellow = zone 'yellow'; game end = game_end True; start cells derived from zone in {'start','minor_start'}. Minors enter after the leading run of minor tokens (4.11.5).


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA17** (gap A.1.17, severity S3, kind carried): R12 stands (down = row+1 same column; absent cell = no move). operating._move_price (given) moves along rows for dividends and is independent of the new market functions; consistency risk noted, not a graph change.
  reason: no new evidence.
- **GB19** (gap B-19, severity S3, kind decision): Layers: 1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares + company_formation, 6 bidding, 7 round_manager; upward calls are lazy imports (api node attrs.layer; lazy edges: turn_order->scoring.check_game_end_triggers, turn_order->certificates.fully_sold, certificates->bidding.items_led, trains->bidding.clear_concession_boxes, bidding->nothing upward now that resolve_stock_round has no sr_over check).
  reason: circular imports.

### `turn_order.descending_order` (function)

```python
descending_order(state: GameState, company_ids: Iterable[str]) -> list[str]
```

- parameters: ['state', 'company_ids']
- defaults (explicit): (none)
- returns: ids sorted by stock_positions.descending_price_key (given)
- layer: 1
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `descending_share_price_order`
- callers in given code: none
- callers from graph (calls/triggers): trains.discard_excess_trains, turn_order.operating_order, turn_order.raise_sold_out_prices

**Exceptions**:

| class | code | when |
|---|---|---|
| MarketError | ERR_NO_TOKEN | a listed company has no token |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. every listed company has a token -> `ERR_NO_TOKEN`

**Implements graph node(s)**: `drv.descending_order`

#### Graph node `drv.descending_order` (derived) - Descending share price order
Sort companies by share price order.

- graph signature (abstract): params = ['set of companies']; returns = list<company>

**Formula**: [1.6.2] sort by key (-price, -col, pile_index_from_top); price desc; same price -> larger column first; same cell -> topmost first; (assumption A26: same price and same column in different rows -> upper row first)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.current_price -> `turn_order.current_price` [same module] signature: `current_price(state: GameState, company_id: str) -> int` 
- calls drv.token_cell -> `turn_order.token_cell` [same module] signature: `token_cell(state: GameState, company_id: str) -> tuple[int, int] | None` 

**State touched**:
- reads `st.market_stack` (Market piles): Which company tokens sit on which cell and their pile order. Company price = value of its cell. Pile order decides ties (1.6.2, 4.4.5, 4.12.2, 5.2.2). [type map cell->ordered list<company> (index 0 = top); unit company ids; scope game]

**Rules constraining this node**:
- 1.6.2: Order by price desc; same price -> token furthest right first; same cell -> topmost first. [formula]
- 2.1.5: Companies discard in descending share price order.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Stock market cells and piles** [repr.market_cells]: maps to: state.stock_positions[company_id] = (row, col); state.stock_stack[(row, col)] = list of company ids, index 0 = TOP; grid app.data.stock_market.STOCK_MARKET_BY_POSITION[(row, col)] -> StockCell(row, col, value, zone, game_end)
  rule for coder: Use stock_positions.place_token (removes from the old pile, APPENDS to the new = bottom) only when the cell changes; emptied piles remain as empty lists; down = (row+1, col), up = (row-1, col), absent cell = no move (R12); yellow = zone 'yellow'; game end = game_end True; start cells derived from zone in {'start','minor_start'}. Minors enter after the leading run of minor tokens (4.11.5).


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA29** (gap A.2.29, severity S3, kind decision): A26 is withdrawn: descending_order uses the given stock_positions.descending_price_key unchanged.
  reason: the case cannot occur on the given grid.

### `turn_order.operating_order` (function)

```python
operating_order(state: GameState) -> list[str]
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: floated minors then floated majors, each in descending_order; acquired and removed minors excluded
- layer: 1
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): turn_order.next_operating_company

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.operating_order`

#### Graph node `drv.operating_order` (derived) - Operating order
Order in which started companies run in an operating round.

- graph signature (abstract): params = ['none']; returns = list<company>

**Formula**: [5.2.1] floated minors (minor_director != null, token on market, not acquired by a major) in descending_order, then floated majors (major_status = floated, token on market) in descending_order

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.descending_order -> `turn_order.descending_order` [same module] signature: `descending_order(state: GameState, company_ids: Iterable[str]) -> list[str]` 

**State touched**:
- reads `st.market_stack` (Market piles): Which company tokens sit on which cell and their pile order. Company price = value of its cell. Pile order decides ties (1.6.2, 4.4.5, 4.12.2, 5.2.2). [type map cell->ordered list<company> (index 0 = top); unit company ids; scope game]
- reads `st.minor_director` (Minor director's certificate holder): Player holding the 50% director's certificate of a minor (counts 1 certificate; assumption A6). Non-null = purchased and floated. [type map minor->player|null; unit -; scope per minor company]
- reads `st.major_status` (Major company status): Floated once its concession is converted (4.7.3). Phase-5 direct formation deferred (R11). [type map major->enum {unstarted, floated}; unit -; scope per major company]

**Rules constraining this node**:
- 5.2.1: A: privates/concessions pay; B: minors in descending price order; C: majors in descending price order. [formula]
- 5.2.2: Same cell: top first; same value different cells: right first; next company decided after the previous finishes.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Stock market cells and piles** [repr.market_cells]: maps to: state.stock_positions[company_id] = (row, col); state.stock_stack[(row, col)] = list of company ids, index 0 = TOP; grid app.data.stock_market.STOCK_MARKET_BY_POSITION[(row, col)] -> StockCell(row, col, value, zone, game_end)
  rule for coder: Use stock_positions.place_token (removes from the old pile, APPENDS to the new = bottom) only when the cell changes; emptied piles remain as empty lists; down = (row+1, col), up = (row-1, col), absent cell = no move (R12); yellow = zone 'yellow'; game end = game_end True; start cells derived from zone in {'start','minor_start'}. Minors enter after the leading run of minor tokens (4.11.5).
- **Minor company ownership** [repr.minor_ownership]: maps to: MinorCompanyState.director_player_id (non-None after award); NO entry in Player.shares; id 'M<n>'
  rule for coder: A minor counts 1 certificate for its director (certs_held dispatches on `cid in state.minors`). floated=True is set by float_minors; removed=True for a removed minor (director stays None). Follows the graph, not the models.py comment (decision GA10).
- **Company status mirrors** [repr.company_status]: maps to: MajorCompanyState.floated / concession_converted / has_operated / share_price; MinorCompanyState.floated / share_price / removed / acquired_by_major
  rule for coder: floated=True and concession_converted=True on conversion; has_operated False at flotation, True after the first completed operating turn (advance_company); share_price is a display mirror nobody reads (read prices from the grid via current_price).


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA31** (gap A.2.31, severity S2, kind graph_fix): operating_order excludes minors with acquired_by_major set and removed minors; acquisition itself is out of scope.
  reason: field exists in the model.

### `turn_order.next_operating_company` (function)

```python
next_operating_company(state: GameState, done: Iterable[str] = ()) -> str | None
```

- parameters: ['state', 'done']
- defaults (explicit): {"done": "()"}
- returns: first company of operating_order(state) (recomputed now) not in done; None if none
- layer: 1
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): round_manager.advance_company, round_manager.begin_operating_round

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.next_operating_company`

#### Graph node `drv.next_operating_company` (derived) - Next company to operate
Choose the next company after the previous one finished.

- graph signature (abstract): params = ['set of companies already run this OR']; returns = company|null

**Formula**: [5.2.2] recompute operating_order now (stock sales during OR may reorder) and take the first company not in done; minors before majors

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.operating_order -> `turn_order.operating_order` [same module] signature: `operating_order(state: GameState) -> list[str]` 

**Rules constraining this node**:
- 5.2.2: Same cell: top first; same value different cells: right first; next company decided after the previous finishes. [formula]


### `turn_order.compute_stock_round_order` (function)

```python
compute_stock_round_order(cash: dict[str, int], previous_order: list[str]) -> list[str]
```

- parameters: ['cash', 'previous_order']
- defaults (explicit): (none)
- returns: players by cash descending; equal cash keeps previous relative order (stable)
- layer: 1
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `next_player_order`
- callers in given code: none
- callers from graph (calls/triggers): turn_order.reorder_players_by_cash

**Exceptions**:

| class | code | when |
|---|---|---|
| MarketError | ERR_PLAYER_MISMATCH | cash keys differ from previous_order players |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. set(cash) == set(previous_order) -> `ERR_PLAYER_MISMATCH`

**Implements graph node(s)**: `drv.compute_stock_round_order`

#### Graph node `drv.compute_stock_round_order` (derived) - Compute next stock round order
Next round's player order from cash.

- graph signature (abstract): params = ['cash map', 'previous order']; returns = list<player>

**Formula**: [4.11.9] sort players by cash descending; equal cash keeps relative order of the previous sr_order; P9 deferred

**State touched**:
- reads `st.player_cash` (Player cash): Cash in hand of each player. Never negative. [type int map player->int; unit pounds (integer); scope per player]
- reads `st.sr_order` (Stock-turn order): Order in which players take stock turns; random at setup (1.7.12); recomputed by cash at each stock-round end (4.11.9). Also the direction for 'nearest after' tie-breaks (4.4.2). The player holding card 1 (index 0) is the start player of every stock round. [type list<player>; unit player ids, index 0 = Player 1 card; scope game]

**Rules constraining this node**:
- 4.11.9: Most cash gets card 1; ties keep previous relative order (P9 deferred). [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.
- **Stock-turn order** [repr.sr_order]: maps to: state.player_order (list, index 0 = Player-1 card) AND state.priority_deal_player_id
  rule for coder: player_count = len(state.player_order) (3..7; no stored field). Invariant: priority_deal_player_id == player_order[0]. Writers of player_order (reorder_players_by_cash, setup) rewrite priority_deal_player_id too; start_stock_round re-asserts it.


### `turn_order.reorder_players_by_cash` (function)

```python
reorder_players_by_cash(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 1
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `reorder_players`
- callers in given code: none
- callers from graph (calls/triggers): bidding.resolve_stock_round
- api notes: Writes BOTH state.player_order and state.priority_deal_player_id (= player_order[0]).

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception

**Implements graph node(s)**: `act.reorder_players_by_cash`

#### Graph node `act.reorder_players_by_cash` (action) - Reorder players by cash
Set the next round's player order by cash.

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.11.9] after bid payments

**Effects, in order** (execute exactly in this order):
1. [4.11.9] sr_order = compute_stock_round_order(player_cash, sr_order)

**Errors listed by the graph node**:
- NONE for legal input: total function when called in the documented order; ERR_ORDER if invoked out of sequence (e.g. outside resolve_stock_round)

**Order edges**:
- `act.reorder_players_by_cash` runs before `act.check_game_end_triggers` (seq 8; resolve: seq 8 runs before seq 9)
- `act.raise_sold_out_prices` runs before `act.reorder_players_by_cash` (seq 7; resolve: seq 7 runs before seq 8)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.compute_stock_round_order -> `turn_order.compute_stock_round_order` [same module] signature: `compute_stock_round_order(cash: dict[str, int], previous_order: list[str]) -> list[str]` 

**State touched**:
- reads `st.player_cash` (Player cash): Cash in hand of each player. Never negative. [type int map player->int; unit pounds (integer); scope per player]
- reads `st.sr_order` (Stock-turn order): Order in which players take stock turns; random at setup (1.7.12); recomputed by cash at each stock-round end (4.11.9). Also the direction for 'nearest after' tie-breaks (4.4.2). The player holding card 1 (index 0) is the start player of every stock round. [type list<player>; unit player ids, index 0 = Player 1 card; scope game]
- writes `st.sr_order` (Stock-turn order): Order in which players take stock turns; random at setup (1.7.12); recomputed by cash at each stock-round end (4.11.9). Also the direction for 'nearest after' tie-breaks (4.4.2). The player holding card 1 (index 0) is the start player of every stock round. [type list<player>; unit player ids, index 0 = Player 1 card; scope game]

**Rules constraining this node**:
- 4.11.9: Most cash gets card 1; ties keep previous relative order (P9 deferred). [demanded in preconditions/effects]
- R11: Out of scope: P16 exceptions, P9 exception, 4.8 direct formation from phase 5, stock-market arrows (provisional: off right end -> up one row same column; off left end -> down one row).

**Representation notes (repr nodes bound to touched states / this node)**:
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.
- **Stock-turn order** [repr.sr_order]: maps to: state.player_order (list, index 0 = Player-1 card) AND state.priority_deal_player_id
  rule for coder: player_count = len(state.player_order) (3..7; no stored field). Invariant: priority_deal_player_id == player_order[0]. Writers of player_order (reorder_players_by_cash, setup) rewrite priority_deal_player_id too; start_stock_round re-asserts it.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA40** (gap A.2.40, severity S3, kind repr): Always equal to player_order[0]: set by setup, rewritten by reorder_players_by_cash, re-asserted by start_stock_round.
  reason: single source of truth.

### `turn_order.raise_sold_out_prices` (function)

```python
raise_sold_out_prices(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 1
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.resolve_stock_round
- api notes: Snapshot of affected companies and order taken once before any move (A22). Lazy-imports certificates.fully_sold.

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception

**Implements graph node(s)**: `act.raise_sold_out_prices`

#### Graph node `act.raise_sold_out_prices` (action) - Raise sold-out companies
Move up one cell every 100%-sold major.

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.12.3] only floated majors; minors never qualify

**Effects, in order** (execute exactly in this order):
1. [4.12.1, R13] affected = floated majors with fully_sold(c)
2. [4.12.2] order = descending_order(affected) computed once before any move
3. [4.12.2] for c in order: call move_token_up(c)

**Errors listed by the graph node**:
- NONE for legal input: total function when called in the documented order; ERR_ORDER if invoked out of sequence (e.g. outside resolve_stock_round)

**Order edges**:
- `act.raise_sold_out_prices` runs before `act.reorder_players_by_cash` (seq 7; resolve: seq 7 runs before seq 8)
- `act.charge_interest` runs before `act.raise_sold_out_prices` (seq 6; resolve: seq 6 runs before seq 7)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.fully_sold -> `certificates.fully_sold` [CROSS-MODULE] signature: `fully_sold(state: GameState, company_id: str) -> bool` 
- calls drv.descending_order -> `turn_order.descending_order` [same module] signature: `descending_order(state: GameState, company_ids: Iterable[str]) -> list[str]` 
- calls act.move_token_up -> `turn_order.move_token_up` [same module] signature: `move_token_up(state: GameState, company_id: str) -> None` 

**State touched**:
- reads `st.major_status` (Major company status): Floated once its concession is converted (4.7.3). Phase-5 direct formation deferred (R11). [type map major->enum {unstarted, floated}; unit -; scope per major company]

**Rules constraining this node**:
- 4.12.1: 100% in players' hands -> token up one cell; no move at the top. [demanded in preconditions/effects]
- R13: Sold out = treasury and bank pool hold zero units. [demanded in preconditions/effects]
- 4.12.3: Minors are never 100% sold. [demanded in preconditions/effects]
- 4.12.2: Move in descending price order, top to bottom within piles; moved token goes to bottom of pile. [demanded in preconditions/effects]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Company status mirrors** [repr.company_status]: maps to: MajorCompanyState.floated / concession_converted / has_operated / share_price; MinorCompanyState.floated / share_price / removed / acquired_by_major
  rule for coder: floated=True and concession_converted=True on conversion; has_operated False at flotation, True after the first completed operating turn (advance_company); share_price is a display mirror nobody reads (read prices from the grid via current_price).


## 4. Rules this module is responsible for (id + text, verbatim from the graph)

- **1.6.1** (rule): Share price = value of the cell holding the company's token. -- constrains `drv.token_cell`, `drv.current_price`, `act.move_token_down`, `act.move_token_up`
- **1.6.2** (rule): Order by price desc; same price -> token furthest right first; same cell -> topmost first. -- constrains `drv.descending_order`
- **1.6.3** (rule): Cell at 50 is solid red; only minors may start there. -- constrains `drv.start_cell`, `act.place_start_token`
- **1.6.4** (rule): 60..100 cells are start cells for majors and minors. -- constrains `drv.start_cell`, `act.place_start_token`
- **1.6.5** (rule): Certificates of a company whose token is in a yellow cell do not count against the limit. -- constrains `drv.in_yellow`
- **10.1.1** (rule): Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. -- constrains `drv.is_game_end_cell`, `act.move_token_up`
- **2.1.5** (rule): Companies discard in descending share price order. -- constrains `drv.descending_order`
- **4.11.5** (rule): Minor tokens go on top of majors and beneath existing minors. -- constrains `act.place_start_token`
- **4.11.9** (rule): Most cash gets card 1; ties keep previous relative order (P9 deferred). -- constrains `drv.compute_stock_round_order`, `act.reorder_players_by_cash`
- **4.12.1** (rule): 100% in players' hands -> token up one cell; no move at the top. -- constrains `act.move_token_up`, `act.raise_sold_out_prices`
- **4.12.2** (rule): Move in descending price order, top to bottom within piles; moved token goes to bottom of pile. -- constrains `act.move_token_up`, `act.raise_sold_out_prices`
- **4.12.3** (rule): Minors are never 100% sold. -- constrains `act.raise_sold_out_prices`
- **4.2.3** (rule): Share certificates of a company in the yellow zone don't count. -- constrains `drv.in_yellow`
- **4.4.4** (rule): Token moves down one cell per share sold; stops at the bottom. -- constrains `act.move_token_down`
- **4.4.5** (rule): Moved token goes to the bottom of the destination pile; unmoved token keeps its place. -- constrains `act.move_token_down`
- **4.5.8** (rule): Yellow-zone stock does not count; buyable at the limit. -- constrains `drv.in_yellow`
- **4.7.2** (rule): Convert, choose a red-outlined start price 60..100, place token under existing tokens. -- constrains `act.place_start_token`
- **5.2.1** (rule): A: privates/concessions pay; B: minors in descending price order; C: majors in descending price order. -- constrains `drv.operating_order`
- **5.2.2** (rule): Same cell: top first; same value different cells: right first; next company decided after the previous finishes. -- constrains `drv.operating_order`, `drv.next_operating_company`
- **R11** (ruling): Out of scope: P16 exceptions, P9 exception, 4.8 direct formation from phase 5, stock-market arrows (provisional: off right end -> up one row same column; off left end -> down one row). -- constrains `act.move_token_down`, `act.move_token_up`, `act.reorder_players_by_cash`
- **R12** (ruling): Left-aligned rows as printed; price drop = down one row same column; no move if cell does not exist. -- constrains `act.move_token_down`, `act.move_token_up`
- **R13** (ruling): Sold out = treasury and bank pool hold zero units. -- constrains `act.raise_sold_out_prices`

