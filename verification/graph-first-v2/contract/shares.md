# Contract: `backend/app/engine/shares.py`

Generated mechanically from graph v2 by gen_contracts.py. Read COMMON.md first, then this file; BINDING.md lists the representation rules and the cross-module call matrix.

Import layering: this module is layer 5 (1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares and company_formation, 6 bidding, 7 round_manager). Calls to a HIGHER layer must be lazy imports inside the function body; never import upward at module level.

## 1. Export list (every name below, plus every alias, must exist at module level)

- `ShareError` (exception)
- `SOURCE_BANK` (constant)
- `SOURCE_POOL` (constant)
- `SOURCE_TREASURY` (constant)
- `interest_amount` (function)  aliases: loan_interest
- `charge_interest` (function)  aliases: apply_interest
- `sell_shares` (function)  aliases: sell_share
- `buy_share` (function)  aliases: buy_certificate
- `repay_loans` (function)  aliases: repay_loan

Public API count: 9

## 2. Module-level obligations

### States this module writes (flags and data it is responsible for)
- `st.player_loans` (Player loans): Outstanding loans of each player. Created by operating-round forced train purchase / emergency money raising (out of scope); reduced by repay_loans; increased by interest. -- written by `act.charge_interest`, `act.repay_loans`
- `st.ordinary_certs` (Ordinary certificates held): Number of ordinary 10% certificates a player holds in a major company. EXCLUDES the director's certificate, which is stored in director_holder. units_held = ordinary_certs + director units; certs_held = ordinary_certs + (1 if director). -- written by `act.sell_shares`, `act.buy_share`
- `st.pool_shares` (Bank-pool shares): Ordinary certificates in the bank pool. Max 5 (50%) (4.4.2). -- written by `act.sell_shares`, `act.buy_share`
- `st.player_cash` (Player cash): Cash in hand of each player. Never negative. -- written by `act.sell_shares`, `act.buy_share`, `act.repay_loans`
- `st.bank_cash` (Bank cash): Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5). -- written by `act.sell_shares`, `act.buy_share`
- `st.sold_this_round` (Sold-this-round map): (player, company) pairs such that the player sold >=1 share of the company this stock round; blocks buying that company (4.5.5). Cleared at stock-round start. Stored as lists, not sets (JSON). -- written by `act.sell_shares`
- `st.sale_happened` (A sale happened flag): Set true when a player buys a share, sells a share, converts a concession (R15, R6), or wins a bid-box item at resolution (R6b). Reset at stock-round start. Read by the 10.1.1 first-round nothing-sold test (R6b). Written by the module functions themselves (idempotent; the caller actions.py also sets it after buy and convert). -- written by `act.sell_shares`, `act.buy_share`
- `st.company_cash` (Company treasury cash): Cash in a company's treasury: credited by buy_share (treasury source), convert_concession, float_minors, pay_private_revenues; debited by buy_train / upgrade_l_train. -- written by `act.buy_share`
- `st.treasury_shares` (Treasury shares): Ordinary certificates in the company treasury, buyable at the current price (4.5.1, 4.7.3). 8 (LNWR 9) at flotation. -- written by `act.buy_share`

### Hooks / triggers fired by this module's nodes
- (none)

### Notes that name 'sets ... itself' / flags (from api notes)
- `ShareError`: Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. Raised by sell_shares, buy_share, repay_loans.
- `SOURCE_BANK`: buy_share source string: the bank pool (same as 'pool').
- `SOURCE_POOL`: buy_share source string: the bank pool.
- `SOURCE_TREASURY`: buy_share source string: the company treasury.
- `sell_shares`: Sets any_sale_this_stock_round itself (actions.py does not for sells).
- `buy_share`: source None: 'pool' if the pool holds a share else 'treasury' (needs_owner, A12). 'bank' and 'pool' both mean the bank pool. Sets any_sale_this_stock_round itself.

### Module-level decisions (resolve any api or node of this module)
- **GA38** (gap A.2.38, severity S3, kind decision): ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).
  reason: layering (no module for a shared base) and the given except clauses.
- **GB20** (gap B-20, severity S3, kind decision): See GA38.
  reason: GA38.
- **GA20** (gap A.2.20, severity S2, kind graph_fix): SaleCheck gains a reason field (None | ERR_NOT_SELLABLE | ERR_POOL_FULL | ERR_TOO_MANY); sell_shares maps reasons to the three codes.
  reason: exposes the failing clause.
- **GA21** (gap A.2.21, severity S3, kind graph_fix): Every api node lists its enforced preconditions in an ORDERED list (attrs.enforced, field n); the first failing check raises. Order = listed order; unknown ids first, then argument validity, then rule checks.
  reason: mechanical contracts need a total order.
- **GA22** (gap A.2.22, severity S2, kind graph_fix): buy_share(..., source=None). Accepted strings: 'treasury', 'pool', 'bank' ('bank' and 'pool' both = bank pool). None: pool if the pool holds a share, else treasury, else ERR_NO_SHARE_AT_SOURCE.  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: given actions pass None when absent; A12 left the choice to the buyer.
- **GB24** (gap B-24, severity S3, kind graph_fix): See GA21.
  reason: GA21.
- **GA23** (gap A.2.23, severity S3, kind graph_fix): repay_loans(state, player_id, amount=None): None = min(loans, cash); ERR_NO_LOANS, ERR_BAD_AMOUNT (<=0, > loans, non-int), ERR_INSUFFICIENT_CASH; no caller (wired=false).
  reason: completeness.
- **GA01** (gap A.1.1, severity S1, kind graph_fix): Follow the skeleton: every successful sell / buy / convert / bid action ends the turn. turn.stage, turn.c_used, turn.acted and the errors ERR_WRONG_STAGE / ERR_C_ALREADY_USED / ERR_NO_ACTION_TAKEN are removed; the order edges sell->repay->C are removed; repay_loans stays as an unwired action (wired=false, implemented and exported); a new given action stock_turn_action models actions.py (calls ONE module function, increments bids_this_turn, resets pass_streak, calls end_turn).
  reason: actions.py is given and its docstring says the combination is 'not wired up yet'; a literal v1 implementation would have vacuous preconditions.
- **GA07** (gap A.1.7, severity S2, kind graph_fix): sell_shares, buy_share and convert_concession all set the flag themselves (idempotent); actions.py's extra write after buy/convert is documented as redundant; resolve_bids sets it when an item is won (R6b).
  reason: makes direct calls of module functions consistent; R15.
- **GA34** (gap A.2.34, severity S3, kind carried): All remain as in GRAPH_NOTES v1 (copied into v2 notes). Owner-open and worth a ruling: A4 (opening bid 0), A5 (one token per item, leader cannot raise), A9 (batch sale priced before the drop), A15 (unpaid box-1 minor is still removed), A16 (payment order).  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: no new evidence.
- **GB13** (gap B-13, severity S2, kind graph_fix): See GA22 (pool first).  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: GA22.
- **GB03** (gap B-3, severity S3, kind decision): Kept; action marked wired=false.
  reason: GA01.

## 3. API contracts

### `shares.ShareError` (exception)

```python
class ShareError(Exception)
```

- bases: ['Exception']; message `<ERR_CODE>: <text>`; attribute `.code` = ERR_CODE
- raised by: shares.buy_share, shares.repay_loans, shares.sell_shares
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 5
- given name (fixed by given code, never rename): YES
- aliases: none
- callers in given code: actions._apply_buy_share, actions._apply_sell_shares
- callers from graph (calls/triggers): none
- api notes: Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. Raised by sell_shares, buy_share, repay_loans.

**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA38** (gap A.2.38, severity S3, kind decision): ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).
  reason: layering (no module for a shared base) and the given except clauses.
- **GB20** (gap B-20, severity S3, kind decision): See GA38.
  reason: GA38.

### `shares.SOURCE_BANK` (constant)

```python
SOURCE_BANK = 'bank'
```

- value: `"bank"`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 5
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: buy_share source string: the bank pool (same as 'pool').

### `shares.SOURCE_POOL` (constant)

```python
SOURCE_POOL = 'pool'
```

- value: `"pool"`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 5
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: buy_share source string: the bank pool.

### `shares.SOURCE_TREASURY` (constant)

```python
SOURCE_TREASURY = 'treasury'
```

- value: `"treasury"`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 5
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: buy_share source string: the company treasury.

### `shares.interest_amount` (function)

```python
interest_amount(loans: int) -> int
```

- parameters: ['loans']
- defaults (explicit): (none)
- returns: (loans + 1) // 2
- layer: 5
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `loan_interest`
- callers in given code: none
- callers from graph (calls/triggers): shares.charge_interest

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.interest_amount`

#### Graph node `drv.interest_amount` (derived) - Interest
Interest added to a loan.

- graph signature (abstract): params = ['loans L']; returns = int

**Formula**: [R14, 4.3.4] ceil(L/2) = (L+1)//2

**Constants used**:
- `const.interest` (Loan interest): End of stock round: loans += ceil(loans/2) (4.3.4, 4.11.10, R14).; data: `{"rate_percent": 50, "rounding": "up"}`

**Rules constraining this node**:
- 4.3.4: Debt at SR end incurs 50% interest rounded up. [formula]
- R14: Interest at SR end: loans += ceil(loans/2). [formula]


### `shares.charge_interest` (function)

```python
charge_interest(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 5
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `apply_interest`
- callers in given code: none
- callers from graph (calls/triggers): bidding.resolve_stock_round

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception; bank cash is unchanged (4.3.5)

**Implements graph node(s)**: `act.charge_interest`

#### Graph node `act.charge_interest` (action) - Charge loan interest
Add 50% interest to every player's loans.

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.3.4] applies only to players with loans > 0

**Effects, in order** (execute exactly in this order):
1. [R14, 4.11.10] for each player with loans > 0: loans += interest_amount(loans)
2. [4.3.5] bank_cash unchanged

**Errors listed by the graph node**:
- NONE for legal input: total function when called in the documented order; ERR_ORDER if invoked out of sequence (e.g. outside resolve_stock_round)

**Order edges**:
- `act.charge_interest` runs before `act.raise_sold_out_prices` (seq 6; resolve: seq 6 runs before seq 7)
- `act.refill_boxes` runs before `act.charge_interest` (seq 5; resolve: seq 5 runs before seq 6)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.interest_amount -> `shares.interest_amount` [same module] signature: `interest_amount(loans: int) -> int` 

**State touched**:
- reads `st.player_loans` (Player loans): Outstanding loans of each player. Created by operating-round forced train purchase / emergency money raising (out of scope); reduced by repay_loans; increased by interest. [type int map player->int; unit pounds; scope per player]
- writes `st.player_loans` (Player loans): Outstanding loans of each player. Created by operating-round forced train purchase / emergency money raising (out of scope); reduced by repay_loans; increased by interest. [type int map player->int; unit pounds; scope per player]

**Constants used**:
- `const.interest` (Loan interest): End of stock round: loans += ceil(loans/2) (4.3.4, 4.11.10, R14).; data: `{"rate_percent": 50, "rounding": "up"}`

**Rules constraining this node**:
- 4.3.5: Loans don't count toward the 12000 bank. [demanded in preconditions/effects]
- 4.3.4: Debt at SR end incurs 50% interest rounded up. [demanded in preconditions/effects]
- 4.11.10: 50% interest on outstanding loans at stock round end. [demanded in preconditions/effects]
- R14: Interest at SR end: loans += ceil(loans/2). [demanded in preconditions/effects]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.


### `shares.sell_shares` (function)

```python
sell_shares(state: GameState, player_id: str, company_id: str, count: int = 1) -> None
```

- parameters: ['state', 'player_id', 'company_id', 'count']
- defaults (explicit): {"count": "1"}
- returns: (see signature)
- layer: 5
- given name (fixed by given code, never rename): YES
- **aliases that MUST also be exported** (same object / same behaviour): `sell_share`
- callers in given code: actions._apply_sell_shares
- callers from graph (calls/triggers): none
- api notes: Sets any_sale_this_stock_round itself (actions.py does not for sells).

**Exceptions**:

| class | code | when |
|---|---|---|
| ShareError | ERR_UNKNOWN_PLAYER | player_id not in state.players |
| ShareError | ERR_NOT_SELLABLE | not a major / not floated / has not completed an OR |
| ShareError | ERR_BAD_COUNT | count not an int >= 1 |
| ShareError | ERR_POOL_FULL | pool would exceed 5 units |
| ShareError | ERR_TOO_MANY | sale_legal says illegal otherwise (holdings, no successor) |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. player exists -> `ERR_UNKNOWN_PLAYER`
2. company_id is a key of state.majors -> `ERR_NOT_SELLABLE`
3. count is an int >= 1 (bool rejected) -> `ERR_BAD_COUNT`
4. major.floated and major.has_operated -> `ERR_NOT_SELLABLE`
5. shares_in_bank_pool + count <= 5 -> `ERR_POOL_FULL`
6. certificates.sale_legal(...).legal -> `ERR_TOO_MANY`

**Must NOT be checked by this function**:
- round type / active player (actions.py)
- loans (do not block selling)
- sold_this_round, certificate limit, turn stage

**Implements graph node(s)**: `act.sell_shares`

#### Graph node `act.sell_shares` (action) - Sell shares
Sell s ordinary certificates of one major company into the bank pool (one batch). Ends the turn (caller).

- graph signature (abstract): params = ['player', 'major company c', 'count s']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.4.1] c is a major company; privates, minors, concessions can never be sold
- [4.4.1] count is an integer >= 1
- [4.4.2] major_status[c] = floated and has_completed_or[c]
- [4.4.2] pool_shares[c] + s <= 5 (50% of the company)
- [R5] drv.sale_legal(player,c,s).legal: s <= ordinary_certs unless the director has an eligible successor (the director's certificate itself never goes to the pool)
- [4.3.3] loans do not block selling; no round/turn check inside the module (caller checks active player)

**Effects, in order** (execute exactly in this order):
1. let price = current_price(c) read BEFORE any move (assumption A9)
2. [4.4.2] if sale_legal.swap_needed: call swap_director(c, sale_legal.successor) BEFORE the rest of the sale
3. [4.4.1] ordinary_certs[player,c] -= s; pool_shares[c] += s
4. [4.4.3] player_cash += s*price; bank_cash -= s*price
5. [4.4.4, 4.4.5] call move_token_down(c, s)
6. [4.5.5] add c to sold_this_round[player] (list, no duplicates)
7. [R15] sale_happened = true (the module sets it itself; actions.py does not)
8. [10.1.1] call check_game_end_triggers(after_bank_payment)
9. [4.4.6] one call = one batch of ONE company; the turn ends after the call (caller sets pass_streak = 0 and calls end_turn)

**Errors listed by the graph node**:
- ERR_UNKNOWN_PLAYER
- ERR_NOT_SELLABLE: not a major / not floated / has not completed an OR
- ERR_BAD_COUNT: not an int >= 1
- ERR_POOL_FULL
- ERR_TOO_MANY: s exceeds holdings / no successor (sale_legal.reason)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.sale_legal -> `certificates.SaleCheck`, `certificates.sale_legal` [CROSS-MODULE] signature: `class SaleCheck(NamedTuple)`; `sale_legal(state: GameState, player_id: str, company_id: str, count: int = 1) -> SaleCheck` 
- calls drv.current_price -> `turn_order.current_price` [CROSS-MODULE] signature: `current_price(state: GameState, company_id: str) -> int` 
- calls act.swap_director -> `certificates.swap_director` [CROSS-MODULE] signature: `swap_director(state: GameState, company_id: str, new_director_id: str) -> None` 
- calls act.move_token_down -> `turn_order.move_token_down` [CROSS-MODULE] signature: `move_token_down(state: GameState, company_id: str, steps: int = 1) -> None` 
- calls act.check_game_end_triggers -> `scoring.check_game_end_triggers` [CROSS-MODULE] signature: `check_game_end_triggers(state: GameState, context: str | None = None) -> None` 

**State touched**:
- reads `st.major_status` (Major company status): Floated once its concession is converted (4.7.3). Phase-5 direct formation deferred (R11). [type map major->enum {unstarted, floated}; unit -; scope per major company]
- reads `st.has_completed_or` (Has completed an operating round): True once the major company has completed one operating turn; shares cannot be sold before (4.4.2). Initial false at flotation (set false by convert_concession), set true by advance_company when the company finished its turn. [type map major->bool; unit -; scope per major company]
- reads `st.ordinary_certs` (Ordinary certificates held): Number of ordinary 10% certificates a player holds in a major company. EXCLUDES the director's certificate, which is stored in director_holder. units_held = ordinary_certs + director units; certs_held = ordinary_certs + (1 if director). [type int map (player, major)->int; unit certificates = units of 10% (ordinary share = 1 unit); scope per player per major company]
- reads `st.director_holder` (Director's certificate holder): Holder of the director's certificate of a major company (null until the company is started). The director's certificate = cert_units units (2; LNWR 1) but ONE certificate for limit counting. [type map major->player|null; unit -; scope per major company]
- reads `st.pool_shares` (Bank-pool shares): Ordinary certificates in the bank pool. Max 5 (50%) (4.4.2). [type int map major->int; unit ordinary certificates = units of 10%; scope per major company]
- writes `st.ordinary_certs` (Ordinary certificates held): Number of ordinary 10% certificates a player holds in a major company. EXCLUDES the director's certificate, which is stored in director_holder. units_held = ordinary_certs + director units; certs_held = ordinary_certs + (1 if director). [type int map (player, major)->int; unit certificates = units of 10% (ordinary share = 1 unit); scope per player per major company]
- writes `st.pool_shares` (Bank-pool shares): Ordinary certificates in the bank pool. Max 5 (50%) (4.4.2). [type int map major->int; unit ordinary certificates = units of 10%; scope per major company]
- writes `st.player_cash` (Player cash): Cash in hand of each player. Never negative. [type int map player->int; unit pounds (integer); scope per player]
- writes `st.bank_cash` (Bank cash): Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5). [type int (can go below zero); unit pounds; scope game]
- writes `st.sold_this_round` (Sold-this-round map): (player, company) pairs such that the player sold >=1 share of the company this stock round; blocks buying that company (4.5.5). Cleared at stock-round start. Stored as lists, not sets (JSON). [type map player -> list<major company> (no duplicates); unit pairs; scope stock round]
- writes `st.sale_happened` (A sale happened flag): Set true when a player buys a share, sells a share, converts a concession (R15, R6), or wins a bid-box item at resolution (R6b). Reset at stock-round start. Read by the 10.1.1 first-round nothing-sold test (R6b). Written by the module functions themselves (idempotent; the caller actions.py also sets it after buy and convert). [type bool; unit -; scope stock round]

**Rules constraining this node**:
- R5: Director may sell everything only if another player holds >= director's-certificate units (2; LNWR 1) and more than the remaining holding; ties -> nearest after seller in player order. [demanded in preconditions/effects]
- 4.5.5: No buying of a company's stock after selling it earlier in the same round. [demanded in preconditions/effects]
- R15: Selling and buying shares both set the flag 'a sale happened this stock round'. [demanded in preconditions/effects]
- 4.4.1: Any number of stock certificates may be sold to the bank pool; privates, minors, concessions may not. [demanded in preconditions/effects]
- 4.4.3: Player receives the current share price per share sold. [demanded in preconditions/effects]
- 4.4.5: Moved token goes to the bottom of the destination pile; unmoved token keeps its place. [demanded in preconditions/effects]
- 4.4.4: Token moves down one cell per share sold; stops at the bottom. [demanded in preconditions/effects]
- 4.4.6: Seller chooses the order of sales across companies; it fixes relative pile order. [demanded in preconditions/effects]
- 4.4.2: Not before company completed an OR; pool <= 50%; director's certificate cannot go into the pool; succession exchange precedes the rest of the sale. [demanded in preconditions/effects]
- 4.3.3: Not obliged to sell shares to repay. [demanded in preconditions/effects]
- 10.1.1: Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. [demanded in preconditions/effects]
- 3.1.6: Privates may not be traded or sold to the bank.
- 3.2.5: Once bought, a minor may never be sold.
- 4.1.3: Sell, then repay loans, then one of buy/convert/bid; may pass.
- R6b: In 10.1.1 'nothing sold in the first stock round' means: no share bought or sold, no concession converted, AND no bid-box item won at resolution. A round with only unsuccessful bids (nobody could pay, R8) counts as nothing sold; a round in which at least one bid wins an item counts as something sold. PROVISIONAL ruling (adopted by the task owner), replaces the provisional tail of R6.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Company status mirrors** [repr.company_status]: maps to: MajorCompanyState.floated / concession_converted / has_operated / share_price; MinorCompanyState.floated / share_price / removed / acquired_by_major
  rule for coder: floated=True and concession_converted=True on conversion; has_operated False at flotation, True after the first completed operating turn (advance_company); share_price is a display mirror nobody reads (read prices from the grid via current_price).
- **Units vs certificates** [repr.units_vs_certificates]: maps to: Player.shares[company_id] = UNITS of 10% INCLUDING the director's certificate (2 units; LNWR 1)
  rule for coder: units_held(p,c) = Player.shares.get(c,0); ordinary_certs(p,c) = units_held - cert_units(c) if p is the director else units_held; certs_held(p,c) = ordinary_certs + (1 if director). Always read with .get(c, 0); zero entries may exist. A swap_director changes NO Player.shares value.
- **Director's certificate** [repr.director_certificate]: maps to: MajorCompanyState.director_player_id (None until started) + cert_units units inside Player.shares[c]
  rule for coder: ONE certificate for the limit regardless of its units; the holder's Player.shares includes the units; it is never in shares_in_treasury or shares_in_bank_pool; LNWR director = 1 unit.
- **Bank pool naming** [repr.bank_pool_naming]: maps to: SHARES: MajorCompanyState.shares_in_bank_pool (units, max 5) = 'the bank pool'; TRAINS: BankState.discarded_trains (list of codes) = 'the bank pool' of trains
  rule for coder: buy_share source strings: 'bank' and 'pool' BOTH mean the bank pool of shares; 'treasury' = MajorCompanyState.shares_in_treasury (ordinary units only, the director's certificate is never in it; LNWR 9, others 8 at flotation); None = module chooses (pool first, else treasury).
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.
- **sold_this_round** [repr.sold_this_round]: maps to: state.sold_this_round: dict[player_id, list[company_id]] (lists without duplicates, NOT sets: rooms.serialize_state cannot encode sets)
  rule for coder: Readers: `company_id in state.sold_this_round.get(player_id, ())`. Reset to {} by start_stock_round.
- **'A sale happened' flag** [repr.sale_flag]: maps to: state.any_sale_this_stock_round (bool)
  rule for coder: Set True by: sell_shares, buy_share, convert_concession (module functions themselves; actions.py also sets it after buy and convert), and resolve_bids when a bid-box item is WON (R6b). Reset to False by start_stock_round. Read by check_game_end_triggers(context='end_of_stock_round').


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA01** (gap A.1.1, severity S1, kind graph_fix): Follow the skeleton: every successful sell / buy / convert / bid action ends the turn. turn.stage, turn.c_used, turn.acted and the errors ERR_WRONG_STAGE / ERR_C_ALREADY_USED / ERR_NO_ACTION_TAKEN are removed; the order edges sell->repay->C are removed; repay_loans stays as an unwired action (wired=false, implemented and exported); a new given action stock_turn_action models actions.py (calls ONE module function, increments bids_this_turn, resets pass_streak, calls end_turn).
  reason: actions.py is given and its docstring says the combination is 'not wired up yet'; a literal v1 implementation would have vacuous preconditions.
- **GA07** (gap A.1.7, severity S2, kind graph_fix): sell_shares, buy_share and convert_concession all set the flag themselves (idempotent); actions.py's extra write after buy/convert is documented as redundant; resolve_bids sets it when an item is won (R6b).
  reason: makes direct calls of module functions consistent; R15.
- **GA34** (gap A.2.34, severity S3, kind carried): All remain as in GRAPH_NOTES v1 (copied into v2 notes). Owner-open and worth a ruling: A4 (opening bid 0), A5 (one token per item, leader cannot raise), A9 (batch sale priced before the drop), A15 (unpaid box-1 minor is still removed), A16 (payment order).  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: no new evidence.
- **GA08** (gap A.1.8, severity S2, kind graph_fix): In scope now: active_company_id, advance_company, start/begin/end of operating rounds, set size lock, game_over maturity, has_completed_or writer (advance_company), start-of-OR revenues. States or_set_size, or_index, or_order, or_current, round_type added; phase_events is an audit log only.
  reason: required by actions.py/main.py; without a writer of has_operated no share could ever be sold.
- **GB06** (gap B-6, severity S2, kind graph_fix): advance_company writes has_completed_or for a major (now a graph effect, state no longer external).
  reason: GA08.
- **GA20** (gap A.2.20, severity S2, kind graph_fix): SaleCheck gains a reason field (None | ERR_NOT_SELLABLE | ERR_POOL_FULL | ERR_TOO_MANY); sell_shares maps reasons to the three codes.
  reason: exposes the failing clause.
- **GA21** (gap A.2.21, severity S3, kind graph_fix): Every api node lists its enforced preconditions in an ORDERED list (attrs.enforced, field n); the first failing check raises. Order = listed order; unknown ids first, then argument validity, then rule checks.
  reason: mechanical contracts need a total order.

### `shares.buy_share` (function)

```python
buy_share(state: GameState, player_id: str, company_id: str, source: str | None = None) -> None
```

- parameters: ['state', 'player_id', 'company_id', 'source']
- defaults (explicit): {"source": "None"}
- returns: (see signature)
- layer: 5
- given name (fixed by given code, never rename): YES
- **aliases that MUST also be exported** (same object / same behaviour): `buy_certificate`
- callers in given code: actions._apply_buy_share
- callers from graph (calls/triggers): none
- api notes: source None: 'pool' if the pool holds a share else 'treasury' (needs_owner, A12). 'bank' and 'pool' both mean the bank pool. Sets any_sale_this_stock_round itself.

**Exceptions**:

| class | code | when |
|---|---|---|
| ShareError | ERR_UNKNOWN_PLAYER | unknown player |
| ShareError | ERR_BAD_SOURCE | source not None/'treasury'/'pool'/'bank' |
| ShareError | ERR_LOANS | player has loans |
| ShareError | ERR_MUST_SELL | over the limit and able to sell |
| ShareError | ERR_NOT_STARTED | not a floated major with a director |
| ShareError | ERR_NO_SHARE_AT_SOURCE | chosen source (or both when None) holds no share |
| ShareError | ERR_INSUFFICIENT_CASH | cash < price |
| ShareError | ERR_SOLD_THIS_ROUND | player sold the company this round |
| ShareError | ERR_AT_60_PERCENT | player holds >= 6 units |
| ShareError | ERR_CERT_LIMIT | cert_count + 1 > limit and company not yellow |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. player exists -> `ERR_UNKNOWN_PLAYER`
2. source in (None, 'treasury', 'pool', 'bank') -> `ERR_BAD_SOURCE`
3. player.loans == 0 -> `ERR_LOANS`
4. not certificates.must_sell -> `ERR_MUST_SELL`
5. company is a major, floated, director not None -> `ERR_NOT_STARTED`
6. source holds >= 1 certificate -> `ERR_NO_SHARE_AT_SOURCE`
7. cash >= current_price -> `ERR_INSUFFICIENT_CASH`
8. company not in sold_this_round[player] -> `ERR_SOLD_THIS_ROUND`
9. units_held < 6 -> `ERR_AT_60_PERCENT`
10. in_yellow or cert_count + 1 <= cert_limit -> `ERR_CERT_LIMIT`

**Must NOT be checked by this function**:
- round type / active player (actions.py)
- money committed in leading bids (A7)
- one certificate per turn (guaranteed by the turn model)

**Implements graph node(s)**: `act.buy_share`

#### Graph node `act.buy_share` (action) - Buy one share
Buy one ordinary share of a started major company from its treasury or from the bank pool. Ends the turn (caller).

- graph signature (abstract): params = ['player', 'major company c', "source in {None, 'treasury', 'pool', 'bank'}; 'bank' = 'pool' = the bank pool; None = module chooses"]; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.5.1] source is None or one of 'treasury', 'pool', 'bank'
- [4.3.1] player_loans[player] = 0
- [R10] not must_sell(player) (over the limit and still able to sell)
- [4.5.2] c is a major, major_status[c] = floated and director_holder[c] != null (ordinary shares need a director; the director's certificate is not buyable here, phase-5 buying deferred)
- [4.5.1] the source holds >= 1 ordinary certificate (treasury_shares or pool_shares); source None: at least one of them
- [4.5.1] player_cash >= current_price(c) (no allowance for money committed in leading bids; assumption A7)
- [4.5.5] c not in sold_this_round[player]
- [4.5.6] units_held(player,c) < 6
- [4.5.7] if not in_yellow(c): cert_count(player) + 1 <= cert_limit even if directorship would change; in the yellow zone the limit is not checked
- [4.5.4] one certificate per turn and concession-in-play: guaranteed by the skeleton turn model (every action ends the turn; only ordinary shares are bought)

**Effects, in order** (execute exactly in this order):
1. price = current_price(c) [4.5.3: unchanged by the purchase]; source None: pool if it holds a share, else treasury (A12; needs_owner)
2. [4.5.1] player_cash -= price; treasury: company_cash[c] += price and treasury_shares[c] -= 1; pool: bank_cash += price and pool_shares[c] -= 1
3. [4.5.1] ordinary_certs[player,c] += 1
4. [4.5.9] if units_held(player,c) > units_held(director_holder[c], c): call swap_director(c, player)
5. [R15] sale_happened = true (the module sets it; actions.py also does)
6. [turn model] the turn ends after the call (caller)

**Errors listed by the graph node**:
- ERR_UNKNOWN_PLAYER
- ERR_BAD_SOURCE
- ERR_LOANS
- ERR_MUST_SELL
- ERR_NOT_STARTED
- ERR_NO_SHARE_AT_SOURCE
- ERR_INSUFFICIENT_CASH
- ERR_SOLD_THIS_ROUND
- ERR_AT_60_PERCENT
- ERR_CERT_LIMIT

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.current_price -> `turn_order.current_price` [CROSS-MODULE] signature: `current_price(state: GameState, company_id: str) -> int` 
- calls drv.units_held -> `certificates.units_held` [CROSS-MODULE] signature: `units_held(state: GameState, player_id: str, company_id: str) -> int` 
- calls drv.cert_count -> `certificates.cert_count` [CROSS-MODULE] signature: `cert_count(state: GameState, player_id: str) -> int` 
- calls drv.in_yellow -> `turn_order.in_yellow` [CROSS-MODULE] signature: `in_yellow(state: GameState, company_id: str) -> bool` 
- calls drv.cert_limit -> `certificates.cert_limit` [CROSS-MODULE] signature: `cert_limit(state: GameState) -> int` 
- calls drv.must_sell -> `certificates.must_sell` [CROSS-MODULE] signature: `must_sell(state: GameState, player_id: str) -> bool` 
- calls act.swap_director -> `certificates.swap_director` [CROSS-MODULE] signature: `swap_director(state: GameState, company_id: str, new_director_id: str) -> None` 

**State touched**:
- reads `st.player_loans` (Player loans): Outstanding loans of each player. Created by operating-round forced train purchase / emergency money raising (out of scope); reduced by repay_loans; increased by interest. [type int map player->int; unit pounds; scope per player]
- reads `st.major_status` (Major company status): Floated once its concession is converted (4.7.3). Phase-5 direct formation deferred (R11). [type map major->enum {unstarted, floated}; unit -; scope per major company]
- reads `st.director_holder` (Director's certificate holder): Holder of the director's certificate of a major company (null until the company is started). The director's certificate = cert_units units (2; LNWR 1) but ONE certificate for limit counting. [type map major->player|null; unit -; scope per major company]
- reads `st.treasury_shares` (Treasury shares): Ordinary certificates in the company treasury, buyable at the current price (4.5.1, 4.7.3). 8 (LNWR 9) at flotation. [type int map major->int; unit ordinary certificates = units of 10%; scope per major company]
- reads `st.pool_shares` (Bank-pool shares): Ordinary certificates in the bank pool. Max 5 (50%) (4.4.2). [type int map major->int; unit ordinary certificates = units of 10%; scope per major company]
- reads `st.player_cash` (Player cash): Cash in hand of each player. Never negative. [type int map player->int; unit pounds (integer); scope per player]
- reads `st.sold_this_round` (Sold-this-round map): (player, company) pairs such that the player sold >=1 share of the company this stock round; blocks buying that company (4.5.5). Cleared at stock-round start. Stored as lists, not sets (JSON). [type map player -> list<major company> (no duplicates); unit pairs; scope stock round]
- reads `st.ordinary_certs` (Ordinary certificates held): Number of ordinary 10% certificates a player holds in a major company. EXCLUDES the director's certificate, which is stored in director_holder. units_held = ordinary_certs + director units; certs_held = ordinary_certs + (1 if director). [type int map (player, major)->int; unit certificates = units of 10% (ordinary share = 1 unit); scope per player per major company]
- writes `st.player_cash` (Player cash): Cash in hand of each player. Never negative. [type int map player->int; unit pounds (integer); scope per player]
- writes `st.company_cash` (Company treasury cash): Cash in a company's treasury: credited by buy_share (treasury source), convert_concession, float_minors, pay_private_revenues; debited by buy_train / upgrade_l_train. [type int map company->int; unit pounds; scope per major and minor company]
- writes `st.treasury_shares` (Treasury shares): Ordinary certificates in the company treasury, buyable at the current price (4.5.1, 4.7.3). 8 (LNWR 9) at flotation. [type int map major->int; unit ordinary certificates = units of 10%; scope per major company]
- writes `st.pool_shares` (Bank-pool shares): Ordinary certificates in the bank pool. Max 5 (50%) (4.4.2). [type int map major->int; unit ordinary certificates = units of 10%; scope per major company]
- writes `st.bank_cash` (Bank cash): Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5). [type int (can go below zero); unit pounds; scope game]
- writes `st.ordinary_certs` (Ordinary certificates held): Number of ordinary 10% certificates a player holds in a major company. EXCLUDES the director's certificate, which is stored in director_holder. units_held = ordinary_certs + director units; certs_held = ordinary_certs + (1 if director). [type int map (player, major)->int; unit certificates = units of 10% (ordinary share = 1 unit); scope per player per major company]
- writes `st.sale_happened` (A sale happened flag): Set true when a player buys a share, sells a share, converts a concession (R15, R6), or wins a bid-box item at resolution (R6b). Reset at stock-round start. Read by the 10.1.1 first-round nothing-sold test (R6b). Written by the module functions themselves (idempotent; the caller actions.py also sets it after buy and convert). [type bool; unit -; scope stock round]

**Rules constraining this node**:
- 4.5.5: No buying of a company's stock after selling it earlier in the same round. [demanded in preconditions/effects]
- 4.5.2: Director's certificate not buyable before phase 5; ordinary shares not before a director exists. [demanded in preconditions/effects]
- R15: Selling and buying shares both set the flag 'a sale happened this stock round'. [demanded in preconditions/effects]
- 4.3.1: No buying, converting or bidding while in debt. [demanded in preconditions/effects]
- 4.5.6: No further certificates once holding 60% of the company. [demanded in preconditions/effects]
- 4.5.4: Only one certificate may be bought per turn. [demanded in preconditions/effects]
- 4.5.9: If the buyer exceeds the director's holding, they become director via exchange. [demanded in preconditions/effects]
- 4.5.1: Transfer one certificate from pool (pay bank) or treasury (pay company) at the market value. [demanded in preconditions/effects]
- R10: Over the limit must sell down at first opportunity; while over and able to sell the player may not buy or bid. [demanded in preconditions/effects]
- 4.5.7: Cannot buy a certificate that would exceed the limit even if it changes directorship. [demanded in preconditions/effects]
- 3.4.1: Director's certificate can't be bought while the concession is in play.
- 4.1.2: Round starts with Player 1 and proceeds in order; share transfers only between player and bank/company.
- 4.1.4: One of: buy one share, convert, place/increase up to 3 bids; round ends when all pass consecutively.
- 4.2.4: A player at the limit may not buy anything that would exceed it.
- 4.5.3: Buying does not change the share price.
- 4.5.8: Yellow-zone stock does not count; buyable at the limit.
- 4.6.3: Director's certificates cannot be bought directly in phases 2-4.
- R6b: In 10.1.1 'nothing sold in the first stock round' means: no share bought or sold, no concession converted, AND no bid-box item won at resolution. A round with only unsuccessful bids (nobody could pay, R8) counts as nothing sold; a round in which at least one bid wins an item counts as something sold. PROVISIONAL ruling (adopted by the task owner), replaces the provisional tail of R6.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.
- **Company status mirrors** [repr.company_status]: maps to: MajorCompanyState.floated / concession_converted / has_operated / share_price; MinorCompanyState.floated / share_price / removed / acquired_by_major
  rule for coder: floated=True and concession_converted=True on conversion; has_operated False at flotation, True after the first completed operating turn (advance_company); share_price is a display mirror nobody reads (read prices from the grid via current_price).
- **Director's certificate** [repr.director_certificate]: maps to: MajorCompanyState.director_player_id (None until started) + cert_units units inside Player.shares[c]
  rule for coder: ONE certificate for the limit regardless of its units; the holder's Player.shares includes the units; it is never in shares_in_treasury or shares_in_bank_pool; LNWR director = 1 unit.
- **Bank pool naming** [repr.bank_pool_naming]: maps to: SHARES: MajorCompanyState.shares_in_bank_pool (units, max 5) = 'the bank pool'; TRAINS: BankState.discarded_trains (list of codes) = 'the bank pool' of trains
  rule for coder: buy_share source strings: 'bank' and 'pool' BOTH mean the bank pool of shares; 'treasury' = MajorCompanyState.shares_in_treasury (ordinary units only, the director's certificate is never in it; LNWR 9, others 8 at flotation); None = module chooses (pool first, else treasury).
- **sold_this_round** [repr.sold_this_round]: maps to: state.sold_this_round: dict[player_id, list[company_id]] (lists without duplicates, NOT sets: rooms.serialize_state cannot encode sets)
  rule for coder: Readers: `company_id in state.sold_this_round.get(player_id, ())`. Reset to {} by start_stock_round.
- **Units vs certificates** [repr.units_vs_certificates]: maps to: Player.shares[company_id] = UNITS of 10% INCLUDING the director's certificate (2 units; LNWR 1)
  rule for coder: units_held(p,c) = Player.shares.get(c,0); ordinary_certs(p,c) = units_held - cert_units(c) if p is the director else units_held; certs_held(p,c) = ordinary_certs + (1 if director). Always read with .get(c, 0); zero entries may exist. A swap_director changes NO Player.shares value.
- **'A sale happened' flag** [repr.sale_flag]: maps to: state.any_sale_this_stock_round (bool)
  rule for coder: Set True by: sell_shares, buy_share, convert_concession (module functions themselves; actions.py also sets it after buy and convert), and resolve_bids when a bid-box item is WON (R6b). Reset to False by start_stock_round. Read by check_game_end_triggers(context='end_of_stock_round').


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA01** (gap A.1.1, severity S1, kind graph_fix): Follow the skeleton: every successful sell / buy / convert / bid action ends the turn. turn.stage, turn.c_used, turn.acted and the errors ERR_WRONG_STAGE / ERR_C_ALREADY_USED / ERR_NO_ACTION_TAKEN are removed; the order edges sell->repay->C are removed; repay_loans stays as an unwired action (wired=false, implemented and exported); a new given action stock_turn_action models actions.py (calls ONE module function, increments bids_this_turn, resets pass_streak, calls end_turn).
  reason: actions.py is given and its docstring says the combination is 'not wired up yet'; a literal v1 implementation would have vacuous preconditions.
- **GA07** (gap A.1.7, severity S2, kind graph_fix): sell_shares, buy_share and convert_concession all set the flag themselves (idempotent); actions.py's extra write after buy/convert is documented as redundant; resolve_bids sets it when an item is won (R6b).
  reason: makes direct calls of module functions consistent; R15.
- **GA22** (gap A.2.22, severity S2, kind graph_fix): buy_share(..., source=None). Accepted strings: 'treasury', 'pool', 'bank' ('bank' and 'pool' both = bank pool). None: pool if the pool holds a share, else treasury, else ERR_NO_SHARE_AT_SOURCE.  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: given actions pass None when absent; A12 left the choice to the buyer.
- **GB13** (gap B-13, severity S2, kind graph_fix): See GA22 (pool first).  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: GA22.
- **GA39** (gap A.2.39, severity S3, kind repr): shares_in_treasury counts ORDINARY units only (8; LNWR 9); the director's certificate is never in it; the models comment 'director cert = 2' does not apply.
  reason: operating._pay_major_dividend counts them as plain units.
- **GA21** (gap A.2.21, severity S3, kind graph_fix): Every api node lists its enforced preconditions in an ORDERED list (attrs.enforced, field n); the first failing check raises. Order = listed order; unknown ids first, then argument validity, then rule checks.
  reason: mechanical contracts need a total order.
- **GB24** (gap B-24, severity S3, kind graph_fix): See GA21.
  reason: GA21.

### `shares.repay_loans` (function)

```python
repay_loans(state: GameState, player_id: str, amount: int | None = None) -> None
```

- parameters: ['state', 'player_id', 'amount']
- defaults (explicit): {"amount": "None"}
- returns: (see signature)
- layer: 5
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `repay_loan`
- callers in given code: none
- callers from graph (calls/triggers): none

**Exceptions**:

| class | code | when |
|---|---|---|
| ShareError | ERR_UNKNOWN_PLAYER | unknown player |
| ShareError | ERR_NO_LOANS | loans == 0 |
| ShareError | ERR_BAD_AMOUNT | amount not an int, <= 0 or > loans |
| ShareError | ERR_INSUFFICIENT_CASH | cash < amount |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. player exists -> `ERR_UNKNOWN_PLAYER`
2. loans > 0 -> `ERR_NO_LOANS`
3. amount is None (= min(loans, cash)) or an int with 0 < amount <= loans -> `ERR_BAD_AMOUNT`
4. cash >= amount -> `ERR_INSUFFICIENT_CASH`

**Must NOT be checked by this function**:
- no caller in the skeleton (wired=false); no round/stage check

**Implements graph node(s)**: `act.repay_loans`

#### Graph node `act.repay_loans` (action) - Repay loans
Pay all or part of the player's loans to the bank (4.1.3 step B). NOT reachable through apply_action in the skeleton (no repay action): implemented and exported only.

- graph signature (abstract): params = ['player', 'amount (default: all that cash allows)']; returns = none
- wired = false: exported and implemented, but no given code calls it

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.3.2] amount is an int > 0 and <= loans (None = min(loans, cash))
- [4.3.2] player has loans
- [4.3.3] player_cash >= amount; no obligation to sell to raise the money

**Effects, in order** (execute exactly in this order):
1. [4.3.2] player_cash -= amount; player_loans -= amount
2. [4.3.5] bank_cash unchanged (loans are a separate source; assumption A28)

**Errors listed by the graph node**:
- ERR_UNKNOWN_PLAYER
- ERR_NO_LOANS
- ERR_BAD_AMOUNT: not an int, <= 0, or > loans
- ERR_INSUFFICIENT_CASH

**Node notes**: wired=false: no caller in the skeleton (decision GA01).

**State touched**:
- reads `st.player_cash` (Player cash): Cash in hand of each player. Never negative. [type int map player->int; unit pounds (integer); scope per player]
- reads `st.player_loans` (Player loans): Outstanding loans of each player. Created by operating-round forced train purchase / emergency money raising (out of scope); reduced by repay_loans; increased by interest. [type int map player->int; unit pounds; scope per player]
- writes `st.player_cash` (Player cash): Cash in hand of each player. Never negative. [type int map player->int; unit pounds (integer); scope per player]
- writes `st.player_loans` (Player loans): Outstanding loans of each player. Created by operating-round forced train purchase / emergency money raising (out of scope); reduced by repay_loans; increased by interest. [type int map player->int; unit pounds; scope per player]

**Rules constraining this node**:
- 4.3.5: Loans don't count toward the 12000 bank. [demanded in preconditions/effects]
- 4.3.3: Not obliged to sell shares to repay. [demanded in preconditions/effects]
- 4.3.2: After selling, a player may repay loans fully or partly to the bank. [demanded in preconditions/effects]
- 4.1.3: Sell, then repay loans, then one of buy/convert/bid; may pass.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA01** (gap A.1.1, severity S1, kind graph_fix): Follow the skeleton: every successful sell / buy / convert / bid action ends the turn. turn.stage, turn.c_used, turn.acted and the errors ERR_WRONG_STAGE / ERR_C_ALREADY_USED / ERR_NO_ACTION_TAKEN are removed; the order edges sell->repay->C are removed; repay_loans stays as an unwired action (wired=false, implemented and exported); a new given action stock_turn_action models actions.py (calls ONE module function, increments bids_this_turn, resets pass_streak, calls end_turn).
  reason: actions.py is given and its docstring says the combination is 'not wired up yet'; a literal v1 implementation would have vacuous preconditions.
- **GA23** (gap A.2.23, severity S3, kind graph_fix): repay_loans(state, player_id, amount=None): None = min(loans, cash); ERR_NO_LOANS, ERR_BAD_AMOUNT (<=0, > loans, non-int), ERR_INSUFFICIENT_CASH; no caller (wired=false).
  reason: completeness.
- **GB03** (gap B-3, severity S3, kind decision): Kept; action marked wired=false.
  reason: GA01.

## 4. Rules this module is responsible for (id + text, verbatim from the graph)

- **10.1.1** (rule): Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. -- constrains `act.sell_shares`
- **3.1.6** (rule): Privates may not be traded or sold to the bank. -- constrains `act.sell_shares`
- **3.2.5** (rule): Once bought, a minor may never be sold. -- constrains `act.sell_shares`
- **3.4.1** (rule): Director's certificate can't be bought while the concession is in play. -- constrains `act.buy_share`
- **4.1.2** (rule): Round starts with Player 1 and proceeds in order; share transfers only between player and bank/company. -- constrains `act.buy_share`
- **4.1.3** (rule): Sell, then repay loans, then one of buy/convert/bid; may pass. -- constrains `act.sell_shares`, `act.repay_loans`
- **4.1.4** (rule): One of: buy one share, convert, place/increase up to 3 bids; round ends when all pass consecutively. -- constrains `act.buy_share`
- **4.11.10** (rule): 50% interest on outstanding loans at stock round end. -- constrains `act.charge_interest`
- **4.2.4** (rule): A player at the limit may not buy anything that would exceed it. -- constrains `act.buy_share`
- **4.3.1** (rule): No buying, converting or bidding while in debt. -- constrains `act.buy_share`
- **4.3.2** (rule): After selling, a player may repay loans fully or partly to the bank. -- constrains `act.repay_loans`
- **4.3.3** (rule): Not obliged to sell shares to repay. -- constrains `act.sell_shares`, `act.repay_loans`
- **4.3.4** (rule): Debt at SR end incurs 50% interest rounded up. -- constrains `drv.interest_amount`, `act.charge_interest`
- **4.3.5** (rule): Loans don't count toward the 12000 bank. -- constrains `act.charge_interest`, `act.repay_loans`
- **4.4.1** (rule): Any number of stock certificates may be sold to the bank pool; privates, minors, concessions may not. -- constrains `act.sell_shares`
- **4.4.2** (rule): Not before company completed an OR; pool <= 50%; director's certificate cannot go into the pool; succession exchange precedes the rest of the sale. -- constrains `act.sell_shares`
- **4.4.3** (rule): Player receives the current share price per share sold. -- constrains `act.sell_shares`
- **4.4.4** (rule): Token moves down one cell per share sold; stops at the bottom. -- constrains `act.sell_shares`
- **4.4.5** (rule): Moved token goes to the bottom of the destination pile; unmoved token keeps its place. -- constrains `act.sell_shares`
- **4.4.6** (rule): Seller chooses the order of sales across companies; it fixes relative pile order. -- constrains `act.sell_shares`
- **4.5.1** (rule): Transfer one certificate from pool (pay bank) or treasury (pay company) at the market value. -- constrains `act.buy_share`
- **4.5.2** (rule): Director's certificate not buyable before phase 5; ordinary shares not before a director exists. -- constrains `act.buy_share`
- **4.5.3** (rule): Buying does not change the share price. -- constrains `act.buy_share`
- **4.5.4** (rule): Only one certificate may be bought per turn. -- constrains `act.buy_share`
- **4.5.5** (rule): No buying of a company's stock after selling it earlier in the same round. -- constrains `act.sell_shares`, `act.buy_share`
- **4.5.6** (rule): No further certificates once holding 60% of the company. -- constrains `act.buy_share`
- **4.5.7** (rule): Cannot buy a certificate that would exceed the limit even if it changes directorship. -- constrains `act.buy_share`
- **4.5.8** (rule): Yellow-zone stock does not count; buyable at the limit. -- constrains `act.buy_share`
- **4.5.9** (rule): If the buyer exceeds the director's holding, they become director via exchange. -- constrains `act.buy_share`
- **4.6.3** (rule): Director's certificates cannot be bought directly in phases 2-4. -- constrains `act.buy_share`
- **R10** (ruling): Over the limit must sell down at first opportunity; while over and able to sell the player may not buy or bid. -- constrains `act.buy_share`
- **R14** (ruling): Interest at SR end: loans += ceil(loans/2). -- constrains `drv.interest_amount`, `act.charge_interest`
- **R15** (ruling): Selling and buying shares both set the flag 'a sale happened this stock round'. -- constrains `act.sell_shares`, `act.buy_share`
- **R5** (ruling): Director may sell everything only if another player holds >= director's-certificate units (2; LNWR 1) and more than the remaining holding; ties -> nearest after seller in player order. -- constrains `act.sell_shares`
- **R6b** (ruling): In 10.1.1 'nothing sold in the first stock round' means: no share bought or sold, no concession converted, AND no bid-box item won at resolution. A round with only unsuccessful bids (nobody could pay, R8) counts as nothing sold; a round in which at least one bid wins an item counts as something sold. PROVISIONAL ruling (adopted by the task owner), replaces the provisional tail of R6. -- constrains `act.sell_shares`, `act.buy_share`

