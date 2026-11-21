# Contract: `backend/app/engine/scoring.py`

Generated mechanically from graph v2 by gen_contracts.py. Read COMMON.md first, then this file; BINDING.md lists the representation rules and the cross-module call matrix.

Import layering: this module is layer 3 (1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares and company_formation, 6 bidding, 7 round_manager). Calls to a HIGHER layer must be lazy imports inside the function body; never import upward at module level.

## 1. Export list (every name below, plus every alias, must exist at module level)

- `ScoringError` (exception)
- `CONTEXT_AFTER_BANK_PAYMENT` (constant)
- `CONTEXT_AFTER_TOKEN_MOVE` (constant)
- `CONTEXT_END_OF_STOCK_ROUND` (constant)
- `TRIGGER_NEXT_OR` (constant)
- `TRIGGER_OR_END` (constant)
- `TRIGGER_OR_SET_END` (constant)
- `CONCESSION_DIVIDEND` (constant)
- `check_game_end_triggers` (function)
- `bank_broken` (function)
- `player_wealth` (function)
- `final_ranking` (function)  aliases: ranking
- `private_revenue` (function)
- `pay_concession_dividends` (function)  aliases: pay_concession_revenue
- `pay_private_revenues` (function)  aliases: pay_private_revenue

Public API count: 15

## 2. Module-level obligations

### States this module writes (flags and data it is responsible for)
- `st.game_end` (Game end trigger): First trigger wins (10.1.2). over = game_over (immediate trigger or matured deferred trigger). -- written by `act.check_game_end_triggers`
- `st.player_cash` (Player cash): Cash in hand of each player. Never negative. -- written by `act.pay_concession_dividends`, `act.pay_private_revenues`
- `st.bank_cash` (Bank cash): Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5). -- written by `act.pay_concession_dividends`, `act.pay_private_revenues`
- `st.company_cash` (Company treasury cash): Cash in a company's treasury: credited by buy_share (treasury source), convert_concession, float_minors, pay_private_revenues; debited by buy_train / upgrade_l_train. -- written by `act.pay_private_revenues`

### Hooks / triggers fired by this module's nodes
- (none)

### Notes that name 'sets ... itself' / flags (from api notes)
- `ScoringError`: Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. Raised only for unknown players in player_wealth / final_ranking.
- `CONTEXT_AFTER_BANK_PAYMENT`: check_game_end_triggers context.
- `CONTEXT_AFTER_TOKEN_MOVE`: check_game_end_triggers context.
- `CONTEXT_END_OF_STOCK_ROUND`: check_game_end_triggers context; the only one that enables the nothing-sold test (R6b).
- `TRIGGER_NEXT_OR`: end_trigger_pending value for a trigger during a stock round.
- `TRIGGER_OR_END`: end_trigger_pending value: token on game-end cell during an OR.
- `TRIGGER_OR_SET_END`: end_trigger_pending value: bank broken during an OR (also the converted next_or).
- `CONCESSION_DIVIDEND`: const.concession_dividend (3.4.4).
- `check_game_end_triggers`: Callable with ONE argument (given callers). First trigger wins (10.1.2). Called with a context by shares.sell_shares, company_formation.convert_concession/float_minors, turn_order.move_token_up, bidding.resolve_stock_round, scoring.pay_*.
- `final_ranking`: needs_owner: tie-break is not in the rulebook.

### Module-level decisions (resolve any api or node of this module)
- **GA38** (gap A.2.38, severity S3, kind decision): ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).
  reason: layering (no module for a shared base) and the given except clauses.
- **GA03** (gap A.1.3, severity S2, kind graph_fix): check_game_end_triggers(state, context=None). The kind of a deferred trigger comes from round_type: STOCK -> 'next_or'; OPERATING -> token on game-end cell 'or_end', bank broken 'or_set_end'. context only matters for 'end_of_stock_round' (nothing-sold test). Maturity (setting game_over) is written by end_operating_round.
  reason: All given callers pass one argument; models.py comments define the three stored values.
- **GA24** (gap A.2.24, severity S3, kind decision): Within one call the order is: existing trigger (stop) -> immediate nothing-sold -> token on game-end cell -> bank broken; the first that fires wins; they cannot actually coincide because the check runs after every action.
  reason: 10.1.2.
- **GA33** (gap A.2.33, severity S3, kind graph_fix): Ruling R6b adopted (provisional): nothing sold = no share bought/sold, no concession converted, no bid-box item won at resolution. resolve_bids sets sale_happened only for WON items; an item nobody can pay (R8) is not won.
  reason: task owner.
- **GB16** (gap B-16, severity S2, kind graph_fix): See GA03.
  reason: GA03.
- **GA36** (gap A.2.36, severity S3, kind graph_fix): game_over is set by check_game_end_triggers (immediate) and by end_operating_round (matured or_end / or_set_end / next_or); drv.final_ranking added (ties keep player order).  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: 10.1.x.
- **GA35** (gap A.2.35, severity S3, kind graph_fix): pay_concession_dividends no-ops at phase >= 5; new pay_private_revenues (3.1.2) pays every open private from the bank: player owners via Player.private_companies, company owners via owner_company_id. P15/P20 treasury credit accrual and closing of privates are out of scope.  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: task goal 1.
- **GA25** (gap A.2.25, severity S3, kind decision): float_minors, pay_concession_dividends and pay_private_revenues call check_game_end_triggers ONCE after all payments.
  reason: the bank-broken latch is monotone within a call.
- **DN08** (gap new, severity S3, kind out_of_scope): Privates owned by companies (owner_company_id) are paid to the company treasury; the P15/P20 treasury credit and closing at phase 7 are out of scope.  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: 3.1.2; R11-style deferral.

## 3. API contracts

### `scoring.ScoringError` (exception)

```python
class ScoringError(Exception)
```

- bases: ['Exception']; message `<ERR_CODE>: <text>`; attribute `.code` = ERR_CODE
- raised by: scoring.player_wealth, scoring.private_revenue
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 3
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. Raised only for unknown players in player_wealth / final_ranking.

**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA38** (gap A.2.38, severity S3, kind decision): ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).
  reason: layering (no module for a shared base) and the given except clauses.

### `scoring.CONTEXT_AFTER_BANK_PAYMENT` (constant)

```python
CONTEXT_AFTER_BANK_PAYMENT = 'after_bank_payment'
```

- value: `"after_bank_payment"`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 3
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: check_game_end_triggers context.

### `scoring.CONTEXT_AFTER_TOKEN_MOVE` (constant)

```python
CONTEXT_AFTER_TOKEN_MOVE = 'after_token_move'
```

- value: `"after_token_move"`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 3
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: check_game_end_triggers context.

### `scoring.CONTEXT_END_OF_STOCK_ROUND` (constant)

```python
CONTEXT_END_OF_STOCK_ROUND = 'end_of_stock_round'
```

- value: `"end_of_stock_round"`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 3
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: check_game_end_triggers context; the only one that enables the nothing-sold test (R6b).

### `scoring.TRIGGER_NEXT_OR` (constant)

```python
TRIGGER_NEXT_OR = 'next_or'
```

- value: `"next_or"`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 3
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: end_trigger_pending value for a trigger during a stock round.

### `scoring.TRIGGER_OR_END` (constant)

```python
TRIGGER_OR_END = 'or_end'
```

- value: `"or_end"`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 3
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: end_trigger_pending value: token on game-end cell during an OR.

### `scoring.TRIGGER_OR_SET_END` (constant)

```python
TRIGGER_OR_SET_END = 'or_set_end'
```

- value: `"or_set_end"`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 3
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: end_trigger_pending value: bank broken during an OR (also the converted next_or).

### `scoring.CONCESSION_DIVIDEND` (constant)

```python
CONCESSION_DIVIDEND = 10
```

- value: `10`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 3
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: const.concession_dividend (3.4.4).

### `scoring.check_game_end_triggers` (function)

```python
check_game_end_triggers(state: GameState, context: str | None = None) -> None
```

- parameters: ['state', 'context']
- defaults (explicit): {"context": "None"}
- returns: (see signature)
- layer: 3
- given name (fixed by given code, never rename): YES
- aliases: none
- callers in given code: actions.apply_action, operating._move_price
- callers from graph (calls/triggers): bidding.resolve_stock_round, company_formation.convert_concession, company_formation.float_minors, scoring.pay_concession_dividends, scoring.pay_private_revenues, shares.sell_shares, turn_order.move_token_up
- api notes: Callable with ONE argument (given callers). First trigger wins (10.1.2). Called with a context by shares.sell_shares, company_formation.convert_concession/float_minors, turn_order.move_token_up, bidding.resolve_stock_round, scoring.pay_*.

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception for unknown context strings (treated as None)
- does not check that a round of the matching type is running; the trigger kind comes from state.round_type
- never sets game_over except for the immediate nothing-sold trigger

**Implements graph node(s)**: `act.check_game_end_triggers`

#### Graph node `act.check_game_end_triggers` (action) - Check game-end triggers
Evaluate the game-end conditions and record the FIRST trigger. Called after every action (one argument), after bank payments and token moves, and at the end of stock-round resolution.

- graph signature (abstract): params = ["context in {None, after_bank_payment, after_token_move, end_of_stock_round}; None = 'after any change'; only end_of_stock_round enables the nothing-sold test; the trigger KIND comes from round_type, not from context"]; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [10.1.2] a trigger already exists (game_over or end_trigger_pending): do nothing, the first trigger stands

**Effects, in order** (execute exactly in this order):
1. [10.1.2] if game_end.trigger != none or over: return unchanged
2. [10.1.1, R6b] if context = end_of_stock_round and sr_completed = 0 and not sale_happened: over = true (immediate; game_over = True)
3. [10.1.1] elif round_type = OPERATING and any token on a game-end cell: trigger = or_end (game ends at the end of that operating round)
4. [10.1.1] elif round_type = OPERATING and bank_broken: trigger = or_set_end (game ends after the current set of ORs; complete the set even if a token later reaches the game-end cell)
5. [10.1.1] elif round_type = STOCK and (any token on a game-end cell or bank_broken): trigger = next_or (game ends after exactly one more OR)
6. [10.1.2] a trigger set earlier in this call is never overwritten; steps are evaluated in this order and the first that fires wins

**Errors listed by the graph node**:
- NONE (total function; unknown context strings are treated as None)

**Order edges**:
- `act.reorder_players_by_cash` runs before `act.check_game_end_triggers` (seq 8; resolve: seq 8 runs before seq 9)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.bank_broken -> `scoring.bank_broken` [same module] signature: `bank_broken(state: GameState) -> bool` 
- calls drv.is_game_end_cell -> `turn_order.is_game_end_cell` [CROSS-MODULE] signature: `is_game_end_cell(state: GameState, company_id: str) -> bool` 
- calls drv.token_cell -> `turn_order.token_cell` [CROSS-MODULE] signature: `token_cell(state: GameState, company_id: str) -> tuple[int, int] | None` 

**State touched**:
- reads `st.bank_cash` (Bank cash): Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5). [type int (can go below zero); unit pounds; scope game]
- reads `st.market_stack` (Market piles): Which company tokens sit on which cell and their pile order. Company price = value of its cell. Pile order decides ties (1.6.2, 4.4.5, 4.12.2, 5.2.2). [type map cell->ordered list<company> (index 0 = top); unit company ids; scope game]
- reads `st.sr_completed` (Stock rounds completed): Number of stock rounds that have finished their resolution (0 during the first stock round). Written ONLY by end_stock_round, after resolve_stock_round returned; so the 10.1.1 'first stock round' test is sr_completed == 0 inside resolution step 9. [type int; unit rounds; scope game]
- reads `st.sale_happened` (A sale happened flag): Set true when a player buys a share, sells a share, converts a concession (R15, R6), or wins a bid-box item at resolution (R6b). Reset at stock-round start. Read by the 10.1.1 first-round nothing-sold test (R6b). Written by the module functions themselves (idempotent; the caller actions.py also sets it after buy and convert). [type bool; unit -; scope stock round]
- reads `st.game_end` (Game end trigger): First trigger wins (10.1.2). over = game_over (immediate trigger or matured deferred trigger). [type record {trigger in {none, next_or, or_end, or_set_end}, over bool}; unit -; scope game]
- reads `st.round_type` (Round type): Which kind of round is running. The game is in a stock round from setup (round 1 is pre-started by new_game) until end_stock_round starts the first operating-round set, and so on alternately (1.7.14, 5.1.1). Replaces the v1 sr_status (no field exists for it). [type enum {STOCK, OPERATING}; unit -; scope game]
- writes `st.game_end` (Game end trigger): First trigger wins (10.1.2). over = game_over (immediate trigger or matured deferred trigger). [type record {trigger in {none, next_or, or_end, or_set_end}, over bool}; unit -; scope game]

**Constants used**:
- `const.game_end_cells` (Game-end cells): Cells carrying the game-end value (10.1.1): StockCell.game_end is True (only (0,3), value 700).; data: `{}`
  (in code: StockCell.game_end is True)
- `const.game_end_triggers` (Game-end trigger values): Stored trigger values (models.GameState.end_trigger_pending): 'next_or' (trigger during a stock round: game ends after exactly one more OR), 'or_end' (token on game-end cell during an OR: ends after that OR), 'or_set_end' (bank broken during an OR: ends after the current OR set). game_over=True = ended.; data: `{"values": ["next_or", "or_end", "or_set_end"]}`

**Rules constraining this node**:
- R6b: In 10.1.1 'nothing sold in the first stock round' means: no share bought or sold, no concession converted, AND no bid-box item won at resolution. A round with only unsuccessful bids (nobody could pay, R8) counts as nothing sold; a round in which at least one bid wins an item counts as something sold. PROVISIONAL ruling (adopted by the task owner), replaces the provisional tail of R6. [demanded in preconditions/effects]
- 10.1.1: Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. [demanded in preconditions/effects]
- 10.1.2: Once triggered the game ends at the indicated time. [demanded in preconditions/effects]
- R6: Bidding alone is not a sale; buy, sell, convert count. Phase-1 conflict open; provisional: a bid that wins an item at resolution counts.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.
- **Stock market cells and piles** [repr.market_cells]: maps to: state.stock_positions[company_id] = (row, col); state.stock_stack[(row, col)] = list of company ids, index 0 = TOP; grid app.data.stock_market.STOCK_MARKET_BY_POSITION[(row, col)] -> StockCell(row, col, value, zone, game_end)
  rule for coder: Use stock_positions.place_token (removes from the old pile, APPENDS to the new = bottom) only when the cell changes; emptied piles remain as empty lists; down = (row+1, col), up = (row-1, col), absent cell = no move (R12); yellow = zone 'yellow'; game end = game_end True; start cells derived from zone in {'start','minor_start'}. Minors enter after the leading run of minor tokens (4.11.5).
- **Stock-round counter** [repr.sr_counter]: maps to: state.stock_rounds_completed (starts 0); state.round_number (starts 1) is NOT maintained by the engine
  rule for coder: sr_completed = stock_rounds_completed; incremented by end_stock_round AFTER resolve_stock_round returned; the 10.1.1 'first stock round' test is stock_rounds_completed == 0 inside step 9.
- **'A sale happened' flag** [repr.sale_flag]: maps to: state.any_sale_this_stock_round (bool)
  rule for coder: Set True by: sell_shares, buy_share, convert_concession (module functions themselves; actions.py also sets it after buy and convert), and resolve_bids when a bid-box item is WON (R6b). Reset to False by start_stock_round. Read by check_game_end_triggers(context='end_of_stock_round').
- **Game end** [repr.game_end]: maps to: state.game_over: bool and state.end_trigger_pending: None | 'next_or' | 'or_end' | 'or_set_end'
  rule for coder: graph trigger none = (False, None); immediate = game_over True; 'a trigger exists' = game_over or end_trigger_pending is not None. 'next_or': stock-round trigger, converted to 'or_set_end' with set size 1 when the next OR set starts; 'or_end': token on game-end cell in an OR (ends after that OR); 'or_set_end': bank broken in an OR (ends after the set). game_over is set by check_game_end_triggers (immediate) and by end_operating_round (matured).
- **Round type** [repr.round_type]: maps to: state.round_type: Enum RoundType.STOCK / RoundType.OPERATING (compare with the Enum, not strings); no field for sr_status (dropped)
  rule for coder: STOCK from setup (round 1 is pre-started); OPERATING set by start_operating_round; STOCK again by start_stock_round.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA03** (gap A.1.3, severity S2, kind graph_fix): check_game_end_triggers(state, context=None). The kind of a deferred trigger comes from round_type: STOCK -> 'next_or'; OPERATING -> token on game-end cell 'or_end', bank broken 'or_set_end'. context only matters for 'end_of_stock_round' (nothing-sold test). Maturity (setting game_over) is written by end_operating_round.
  reason: All given callers pass one argument; models.py comments define the three stored values.
- **GA24** (gap A.2.24, severity S3, kind decision): Within one call the order is: existing trigger (stop) -> immediate nothing-sold -> token on game-end cell -> bank broken; the first that fires wins; they cannot actually coincide because the check runs after every action.
  reason: 10.1.2.
- **GA33** (gap A.2.33, severity S3, kind graph_fix): Ruling R6b adopted (provisional): nothing sold = no share bought/sold, no concession converted, no bid-box item won at resolution. resolve_bids sets sale_happened only for WON items; an item nobody can pay (R8) is not won.
  reason: task owner.
- **GB16** (gap B-16, severity S2, kind graph_fix): See GA03.
  reason: GA03.
- **GA42** (gap A.2.42, severity S3, kind repr): st.sr_completed = stock_rounds_completed (0 during round 1); round_number untouched by the engine.
  reason: the model default is never described.
- **GB02** (gap B-2, severity S3, kind graph_fix): State renamed st.sr_completed (rounds completed); incremented by end_stock_round after resolution.
  reason: GA42.
- **GA07** (gap A.1.7, severity S2, kind graph_fix): sell_shares, buy_share and convert_concession all set the flag themselves (idempotent); actions.py's extra write after buy/convert is documented as redundant; resolve_bids sets it when an item is won (R6b).
  reason: makes direct calls of module functions consistent; R15.
- **GA05** (gap A.1.5, severity S2, kind graph_fix): st.sr_status is dropped; st.round_type (STOCK/OPERATING) replaces it. start_stock_round raises only ERR_GAME_OVER, never 'already running'.
  reason: main.py calls start_stock_round at arbitrary times.

### `scoring.bank_broken` (function)

```python
bank_broken(state: GameState) -> bool
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: state.bank.cash < 0
- layer: 3
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): scoring.check_game_end_triggers

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.bank_broken`

#### Graph node `drv.bank_broken` (derived) - Bank broken?
True when the bank has run out of money.

- graph signature (abstract): params = ['none']; returns = bool

**Formula**: [10.1.1] bank_cash < 0 (assumption A29; loans excluded [4.3.5])

**State touched**:
- reads `st.bank_cash` (Bank cash): Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5). [type int (can go below zero); unit pounds; scope game]

**Rules constraining this node**:
- 4.3.5: Loans don't count toward the 12000 bank. [formula]
- 10.1.1: Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.


### `scoring.player_wealth` (function)

```python
player_wealth(state: GameState, player_id: str) -> int
```

- parameters: ['state', 'player_id']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 3
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): scoring.final_ranking

**Exceptions**:

| class | code | when |
|---|---|---|
| ScoringError | ERR_UNKNOWN_PLAYER | player_id not in state.players |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. player exists -> `ERR_UNKNOWN_PLAYER`

**Implements graph node(s)**: `drv.player_wealth`

#### Graph node `drv.player_wealth` (derived) - Player wealth
Wealth of a player at game end.

- graph signature (abstract): params = ['player p']; returns = int

**Formula**: [10.1.3] cash + sum over majors c of units_held(p,c)*current_price(c) + 100 * |concessions held| - loans; privates and company assets count 0

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.units_held -> `certificates.units_held` [CROSS-MODULE] signature: `units_held(state: GameState, player_id: str, company_id: str) -> int` 
- calls drv.current_price -> `turn_order.current_price` [CROSS-MODULE] signature: `current_price(state: GameState, company_id: str) -> int` 

**State touched**:
- reads `st.player_cash` (Player cash): Cash in hand of each player. Never negative. [type int map player->int; unit pounds (integer); scope per player]
- reads `st.player_loans` (Player loans): Outstanding loans of each player. Created by operating-round forced train purchase / emergency money raising (out of scope); reduced by repay_loans; increased by interest. [type int map player->int; unit pounds; scope per player]
- reads `st.player_concessions` (Concessions held): Concession certificates a player holds (acquired after resolution, 4.7.5). Removed at phase 5 (R9). [type map player->set<major>; unit concession certificates; scope per player]

**Rules constraining this node**:
- 10.1.3: Stock at current prices + cash - loans; open concessions at face value; privates 0. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.
- **Concession** [repr.concession]: maps to: Player.concessions: list[str] of major abbr; BidBoxItem(kind='concession', ref=abbr); MajorCompanyState.concession_holder_player_id mirrors the holder (None after conversion/clearing); concession_converted True after conversion
  rule for coder: Removal at phase 5 = absent from stack, boxes and players (no field). Writers keep the mirror fields consistent (vacate_box_item sets, convert_concession/clear_concession_boxes clear).


### `scoring.final_ranking` (function)

```python
final_ranking(state: GameState) -> list[tuple[str, int]]
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: [(player_id, wealth)] richest first; ties keep player_order
- layer: 3
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `ranking`
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: needs_owner: tie-break is not in the rulebook.

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.final_ranking`

#### Graph node `drv.final_ranking` (derived) - Final ranking
Players ordered by wealth, richest first (the richest wins).

- graph signature (abstract): params = ['none']; returns = list<(player, wealth)>

**Formula**: [10.1.3] sort players by player_wealth descending; ties keep sr_order (needs_owner: no tie-break in the rulebook)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.player_wealth -> `scoring.player_wealth` [same module] signature: `player_wealth(state: GameState, player_id: str) -> int` 

**State touched**:
- reads `st.sr_order` (Stock-turn order): Order in which players take stock turns; random at setup (1.7.12); recomputed by cash at each stock-round end (4.11.9). Also the direction for 'nearest after' tie-breaks (4.4.2). The player holding card 1 (index 0) is the start player of every stock round. [type list<player>; unit player ids, index 0 = Player 1 card; scope game]

**Rules constraining this node**:
- 10.1.3: Stock at current prices + cash - loans; open concessions at face value; privates 0. [formula]
- 10.1.1: Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Stock-turn order** [repr.sr_order]: maps to: state.player_order (list, index 0 = Player-1 card) AND state.priority_deal_player_id
  rule for coder: player_count = len(state.player_order) (3..7; no stored field). Invariant: priority_deal_player_id == player_order[0]. Writers of player_order (reorder_players_by_cash, setup) rewrite priority_deal_player_id too; start_stock_round re-asserts it.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA36** (gap A.2.36, severity S3, kind graph_fix): game_over is set by check_game_end_triggers (immediate) and by end_operating_round (matured or_end / or_set_end / next_or); drv.final_ranking added (ties keep player order).  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: 10.1.x.

### `scoring.private_revenue` (function)

```python
private_revenue(private_number: int, phase: int) -> int
```

- parameters: ['private_number', 'phase']
- defaults (explicit): (none)
- returns: '£N' -> N; '£Nx phase' -> N*phase
- layer: 3
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): scoring.pay_private_revenues

**Exceptions**:

| class | code | when |
|---|---|---|
| ScoringError | ERR_UNKNOWN_PRIVATE | number not in PRIVATE_COMPANIES_BY_NUMBER |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. private number exists in the data table -> `ERR_UNKNOWN_PRIVATE`

**Implements graph node(s)**: `drv.private_revenue`

#### Graph node `drv.private_revenue` (derived) - Private revenue
Fixed revenue of one private company in the current phase.

- graph signature (abstract): params = ['private number', 'phase']; returns = int

**Formula**: [3.1.2] value from const.private_revenue_table: '£N' -> N; '£Nx phase' -> N * phase (P15)

**Constants used**:
- `const.private_revenue_table` (Private company revenue table): Fixed revenue of a private company per operating round (3.1.2): from app.data.private_companies revenue strings: '£N' -> N; '£Nx phase' -> N * phase (P15). Base-game P1..P18.; data: `{"table": {"1": "5", "2": "10", "3": "0", "4": "0", "5": "10", "6": "10", "7": "10", "8": "10", "9": "10", "10": "10", "11": "10", "12": "10", "13": "10", "14": "10", "15": "10xphase", "16": "0", "17": "10", "18": "10"}}`
  (in code: app.data.private_companies.PRIVATE_COMPANIES_BY_NUMBER[n].revenue (string))

**Rules constraining this node**:
- 3.1.2: While open, a private pays its fixed revenue (maybe 0) to its owner at the start of each operating round. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Private revenue strings** [repr.private_revenue_parse]: maps to: app.data.private_companies.PRIVATE_COMPANIES_BY_NUMBER[n].revenue: '£5', '£10', '£0', '£10x phase', '£5x phase'
  rule for coder: private_revenue(n, phase): strip '£'; if it ends with 'x phase' multiply by phase.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA35** (gap A.2.35, severity S3, kind graph_fix): pay_concession_dividends no-ops at phase >= 5; new pay_private_revenues (3.1.2) pays every open private from the bank: player owners via Player.private_companies, company owners via owner_company_id. P15/P20 treasury credit accrual and closing of privates are out of scope.  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: task goal 1.

### `scoring.pay_concession_dividends` (function)

```python
pay_concession_dividends(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 3
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `pay_concession_revenue`
- callers in given code: none
- callers from graph (calls/triggers): round_manager.begin_operating_round

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception; phase >= 5 is a no-op

**Implements graph node(s)**: `act.pay_concession_dividends`

#### Graph node `act.pay_concession_dividends` (action) - Pay concession dividends
Operating-round step A for concessions: each held concession pays 10 to its owner from the bank.

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [R9] phase < 5 (concessions exist); at phase >= 5 the call is a no-op

**Effects, in order** (execute exactly in this order):
1. [3.4.4, 5.2.1] for every player and every concession held: player_cash += 10; bank_cash -= 10 (the bank keeps paying when broken)
2. [R9] phase >= 5: nothing to pay
3. [10.1.1] call check_game_end_triggers(after_bank_payment) ONCE after all payments

**Errors listed by the graph node**:
- NONE (raises nothing)

**Order edges**:
- `act.pay_private_revenues` runs before `act.pay_concession_dividends` (seq 1; or_start: seq 1 runs before seq 2)

**Calls it must make / may trigger** (callee api in brackets):
- calls act.check_game_end_triggers -> `scoring.check_game_end_triggers` [same module] signature: `check_game_end_triggers(state: GameState, context: str | None = None) -> None` 

**State touched**:
- reads `st.player_concessions` (Concessions held): Concession certificates a player holds (acquired after resolution, 4.7.5). Removed at phase 5 (R9). [type map player->set<major>; unit concession certificates; scope per player]
- reads `st.phase` (Game phase): Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1). [type int 1..7; unit phase number; scope game]
- writes `st.player_cash` (Player cash): Cash in hand of each player. Never negative. [type int map player->int; unit pounds (integer); scope per player]
- writes `st.bank_cash` (Bank cash): Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5). [type int (can go below zero); unit pounds; scope game]

**Constants used**:
- `const.concession_dividend` (Concession dividend): A held concession pays 10 per operating round to its owner (3.4.4).; data: `{"value": 10}`

**Rules constraining this node**:
- 5.2.1: A: privates/concessions pay; B: minors in descending price order; C: majors in descending price order. [demanded in preconditions/effects]
- 3.4.4: Each concession pays 10 per OR to its owner. [demanded in preconditions/effects]
- R9: From phase 5 held concessions disappear, concession boxes are cleared and never refilled. [demanded in preconditions/effects]
- 10.1.1: Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. [demanded in preconditions/effects]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Concession** [repr.concession]: maps to: Player.concessions: list[str] of major abbr; BidBoxItem(kind='concession', ref=abbr); MajorCompanyState.concession_holder_player_id mirrors the holder (None after conversion/clearing); concession_converted True after conversion
  rule for coder: Removal at phase 5 = absent from stack, boxes and players (no field). Writers keep the mirror fields consistent (vacate_box_item sets, convert_concession/clear_concession_boxes clear).
- **Phase** [repr.phase_state]: maps to: state.phase: int 1..7; limits and rust from app.data.phases.PHASES_BY_NUMBER; trigger table trains.TRAIN_PHASE (module constant)
  rule for coder: phase only increases (2.2.1) and is written only by phase_check (plus debug code in main.py). PHASES_BY_NUMBER[n].trains_rusted gives ONE code per phase; skipped phases are rusted too (loop old+1..new).
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA25** (gap A.2.25, severity S3, kind decision): float_minors, pay_concession_dividends and pay_private_revenues call check_game_end_triggers ONCE after all payments.
  reason: the bank-broken latch is monotone within a call.
- **GA35** (gap A.2.35, severity S3, kind graph_fix): pay_concession_dividends no-ops at phase >= 5; new pay_private_revenues (3.1.2) pays every open private from the bank: player owners via Player.private_companies, company owners via owner_company_id. P15/P20 treasury credit accrual and closing of privates are out of scope.  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: task goal 1.

### `scoring.pay_private_revenues` (function)

```python
pay_private_revenues(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 3
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `pay_private_revenue`
- callers in given code: none
- callers from graph (calls/triggers): round_manager.begin_operating_round

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception; closed privates and zero revenue pay nothing

**Implements graph node(s)**: `act.pay_private_revenues`

#### Graph node `act.pay_private_revenues` (action) - Pay private-company revenue
Operating-round step A for private companies: every open private pays its fixed revenue to its owner (player or company) from the bank.

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [3.1.2] a private pays only while open (not closed)

**Effects, in order** (execute exactly in this order):
1. [3.1.2, 5.2.1 A] for every open private n with revenue r = private_revenue(n, phase) > 0: owner player (Player.private_companies): player_cash += r; owner company (owner_company_id): company_cash += r; bank_cash -= r
2. [3.1.2] revenue 0 (P3, P4, P16): nothing moves
3. [10.1.1] call check_game_end_triggers(after_bank_payment) ONCE after all payments

**Errors listed by the graph node**:
- NONE (raises nothing)

**Node notes**: P15/P20 'treasury credit' accrual and closing of privates are out of scope (decision GA35).

**Order edges**:
- `act.pay_private_revenues` runs before `act.pay_concession_dividends` (seq 1; or_start: seq 1 runs before seq 2)

**Calls it must make / may trigger** (callee api in brackets):
- calls act.check_game_end_triggers -> `scoring.check_game_end_triggers` [same module] signature: `check_game_end_triggers(state: GameState, context: str | None = None) -> None` 
- calls drv.private_revenue -> `scoring.private_revenue` [same module] signature: `private_revenue(private_number: int, phase: int) -> int` 

**State touched**:
- reads `st.private_status` (Private company ownership/closure): Who owns a private (player via Player.private_companies, company via PrivateCompanyState.owner_company_id) and whether it is closed; an open private pays its fixed revenue each OR (3.1.2). Players' side written by vacate_box_item; company acquisition and closing are out of scope (operating-round code). [type map private -> {owner_player | owner_company | none, closed bool}; unit -; scope per private company]
- reads `st.player_privates` (Privates held): Private companies held by each player. [type map player->set<private>; unit private certificates; scope per player]
- reads `st.phase` (Game phase): Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1). [type int 1..7; unit phase number; scope game]
- writes `st.player_cash` (Player cash): Cash in hand of each player. Never negative. [type int map player->int; unit pounds (integer); scope per player]
- writes `st.company_cash` (Company treasury cash): Cash in a company's treasury: credited by buy_share (treasury source), convert_concession, float_minors, pay_private_revenues; debited by buy_train / upgrade_l_train. [type int map company->int; unit pounds; scope per major and minor company]
- writes `st.bank_cash` (Bank cash): Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5). [type int (can go below zero); unit pounds; scope game]

**Constants used**:
- `const.private_revenue_table` (Private company revenue table): Fixed revenue of a private company per operating round (3.1.2): from app.data.private_companies revenue strings: '£N' -> N; '£Nx phase' -> N * phase (P15). Base-game P1..P18.; data: `{"table": {"1": "5", "2": "10", "3": "0", "4": "0", "5": "10", "6": "10", "7": "10", "8": "10", "9": "10", "10": "10", "11": "10", "12": "10", "13": "10", "14": "10", "15": "10xphase", "16": "0", "17": "10", "18": "10"}}`
  (in code: app.data.private_companies.PRIVATE_COMPANIES_BY_NUMBER[n].revenue (string))

**Rules constraining this node**:
- 3.1.2: While open, a private pays its fixed revenue (maybe 0) to its owner at the start of each operating round. [demanded in preconditions/effects]
- 5.2.1: A: privates/concessions pay; B: minors in descending price order; C: majors in descending price order. [demanded in preconditions/effects]
- 10.1.1: Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. [demanded in preconditions/effects]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Private company** [repr.private_company]: maps to: Player.private_companies: list[int]; PrivateCompanyState(number, owner_player_id mirror, owner_company_id, closed, treasury_credit)
  rule for coder: pay_private_revenues pays every open private: if owner_company_id is set -> that company's treasury, else the player holding it in Player.private_companies; closed privates pay nothing.
- **Phase** [repr.phase_state]: maps to: state.phase: int 1..7; limits and rust from app.data.phases.PHASES_BY_NUMBER; trigger table trains.TRAIN_PHASE (module constant)
  rule for coder: phase only increases (2.2.1) and is written only by phase_check (plus debug code in main.py). PHASES_BY_NUMBER[n].trains_rusted gives ONE code per phase; skipped phases are rusted too (loop old+1..new).
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA25** (gap A.2.25, severity S3, kind decision): float_minors, pay_concession_dividends and pay_private_revenues call check_game_end_triggers ONCE after all payments.
  reason: the bank-broken latch is monotone within a call.
- **GA35** (gap A.2.35, severity S3, kind graph_fix): pay_concession_dividends no-ops at phase >= 5; new pay_private_revenues (3.1.2) pays every open private from the bank: player owners via Player.private_companies, company owners via owner_company_id. P15/P20 treasury credit accrual and closing of privates are out of scope.  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: task goal 1.
- **DN08** (gap new, severity S3, kind out_of_scope): Privates owned by companies (owner_company_id) are paid to the company treasury; the P15/P20 treasury credit and closing at phase 7 are out of scope.  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: 3.1.2; R11-style deferral.
- **GB05** (gap B-5, severity S3, kind repr): Documented in repr.concession, repr.private_company, repr.company_status; private_status is a new state.
  reason: coverage.

## 4. Rules this module is responsible for (id + text, verbatim from the graph)

- **10.1.1** (rule): Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. -- constrains `act.check_game_end_triggers`, `drv.bank_broken`, `drv.final_ranking`, `act.pay_concession_dividends`, `act.pay_private_revenues`
- **10.1.2** (rule): Once triggered the game ends at the indicated time. -- constrains `act.check_game_end_triggers`
- **10.1.3** (rule): Stock at current prices + cash - loans; open concessions at face value; privates 0. -- constrains `drv.player_wealth`, `drv.final_ranking`
- **3.1.2** (rule): While open, a private pays its fixed revenue (maybe 0) to its owner at the start of each operating round. -- constrains `drv.private_revenue`, `act.pay_private_revenues`
- **3.4.4** (rule): Each concession pays 10 per OR to its owner. -- constrains `act.pay_concession_dividends`
- **4.3.5** (rule): Loans don't count toward the 12000 bank. -- constrains `drv.bank_broken`
- **5.2.1** (rule): A: privates/concessions pay; B: minors in descending price order; C: majors in descending price order. -- constrains `act.pay_concession_dividends`, `act.pay_private_revenues`
- **R6** (ruling): Bidding alone is not a sale; buy, sell, convert count. Phase-1 conflict open; provisional: a bid that wins an item at resolution counts. -- constrains `act.check_game_end_triggers`
- **R6b** (ruling): In 10.1.1 'nothing sold in the first stock round' means: no share bought or sold, no concession converted, AND no bid-box item won at resolution. A round with only unsuccessful bids (nobody could pay, R8) counts as nothing sold; a round in which at least one bid wins an item counts as something sold. PROVISIONAL ruling (adopted by the task owner), replaces the provisional tail of R6. -- constrains `act.check_game_end_triggers`
- **R9** (ruling): From phase 5 held concessions disappear, concession boxes are cleared and never refilled. -- constrains `act.pay_concession_dividends`

