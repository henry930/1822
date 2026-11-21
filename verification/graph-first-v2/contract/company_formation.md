# Contract: `backend/app/engine/company_formation.py`

Generated mechanically from graph v2 by gen_contracts.py. Read COMMON.md first, then this file; BINDING.md lists the representation rules and the cross-module call matrix.

Import layering: this module is layer 5 (1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares and company_formation, 6 bidding, 7 round_manager). Calls to a HIGHER layer must be lazy imports inside the function body; never import upward at module level.

## 1. Export list (every name below, plus every alias, must exist at module level)

- `ConcessionError` (exception)
- `MAJOR_START_PRICES` (constant)
- `MINOR_START_PRICES` (constant)
- `convert_concession` (function)  aliases: convert_concession_to_director
- `minor_start_price` (function)  aliases: start_price_for_minor
- `minor_start_treasury` (function)
- `minor_float_order` (function)
- `float_minors` (function)  aliases: float_minor_companies

Public API count: 8

## 2. Module-level obligations

### States this module writes (flags and data it is responsible for)
- `st.player_concessions` (Concessions held): Concession certificates a player holds (acquired after resolution, 4.7.5). Removed at phase 5 (R9). -- written by `act.convert_concession`
- `st.director_holder` (Director's certificate holder): Holder of the director's certificate of a major company (null until the company is started). The director's certificate = cert_units units (2; LNWR 1) but ONE certificate for limit counting. -- written by `act.convert_concession`
- `st.bank_cash` (Bank cash): Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5). -- written by `act.convert_concession`, `act.float_minors`
- `st.player_cash` (Player cash): Cash in hand of each player. Never negative. -- written by `act.convert_concession`
- `st.company_cash` (Company treasury cash): Cash in a company's treasury: credited by buy_share (treasury source), convert_concession, float_minors, pay_private_revenues; debited by buy_train / upgrade_l_train. -- written by `act.convert_concession`, `act.float_minors`
- `st.treasury_shares` (Treasury shares): Ordinary certificates in the company treasury, buyable at the current price (4.5.1, 4.7.3). 8 (LNWR 9) at flotation. -- written by `act.convert_concession`
- `st.pool_shares` (Bank-pool shares): Ordinary certificates in the bank pool. Max 5 (50%) (4.4.2). -- written by `act.convert_concession`
- `st.major_status` (Major company status): Floated once its concession is converted (4.7.3). Phase-5 direct formation deferred (R11). -- written by `act.convert_concession`
- `st.sale_happened` (A sale happened flag): Set true when a player buys a share, sells a share, converts a concession (R15, R6), or wins a bid-box item at resolution (R6b). Reset at stock-round start. Read by the 10.1.1 first-round nothing-sold test (R6b). Written by the module functions themselves (idempotent; the caller actions.py also sets it after buy and convert). -- written by `act.convert_concession`
- `st.has_completed_or` (Has completed an operating round): True once the major company has completed one operating turn; shares cannot be sold before (4.4.2). Initial false at flotation (set false by convert_concession), set true by advance_company when the company finished its turn. -- written by `act.convert_concession`

### Hooks / triggers fired by this module's nodes
- (none)

### Notes that name 'sets ... itself' / flags (from api notes)
- `ConcessionError`: Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. Raised by convert_concession.
- `MAJOR_START_PRICES`: const.start_values for majors.
- `MINOR_START_PRICES`: const.start_values for minors.
- `convert_concession`: Sets any_sale_this_stock_round itself, sets concession_converted True, concession_holder None, has_operated False.
- `float_minors`: pending items are (minor_number, bid, box_index, buyer_player_id). Sets MinorCompanyState.floated, treasury, share_price. Calls check_game_end_triggers once after the loop.

### Module-level decisions (resolve any api or node of this module)
- **GA38** (gap A.2.38, severity S3, kind decision): ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).
  reason: layering (no module for a shared base) and the given except clauses.
- **GA21** (gap A.2.21, severity S3, kind graph_fix): Every api node lists its enforced preconditions in an ORDERED list (attrs.enforced, field n); the first failing check raises. Order = listed order; unknown ids first, then argument validity, then rule checks.
  reason: mechanical contracts need a total order.
- **GA01** (gap A.1.1, severity S1, kind graph_fix): Follow the skeleton: every successful sell / buy / convert / bid action ends the turn. turn.stage, turn.c_used, turn.acted and the errors ERR_WRONG_STAGE / ERR_C_ALREADY_USED / ERR_NO_ACTION_TAKEN are removed; the order edges sell->repay->C are removed; repay_loans stays as an unwired action (wired=false, implemented and exported); a new given action stock_turn_action models actions.py (calls ONE module function, increments bids_this_turn, resets pass_streak, calls end_turn).
  reason: actions.py is given and its docstring says the combination is 'not wired up yet'; a literal v1 implementation would have vacuous preconditions.
- **GA07** (gap A.1.7, severity S2, kind graph_fix): sell_shares, buy_share and convert_concession all set the flag themselves (idempotent); actions.py's extra write after buy/convert is documented as redundant; resolve_bids sets it when an item is won (R6b).
  reason: makes direct calls of module functions consistent; R15.
- **GA32** (gap A.2.32, severity S3, kind carried): No certificate-limit effect (concession 1 -> director certificate 1); leading bids ignored (A7). A major whose concession was not converted before phase 5 can never start (R9 + R11, A25).  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: R9/R11 consequence.
- **GA25** (gap A.2.25, severity S3, kind decision): float_minors, pay_concession_dividends and pay_private_revenues call check_game_end_triggers ONCE after all payments.
  reason: the bank-broken latch is monotone within a call.
- **GB21** (gap B-21, severity S3, kind decision): See GA25.
  reason: GA25.

## 3. API contracts

### `company_formation.ConcessionError` (exception)

```python
class ConcessionError(Exception)
```

- bases: ['Exception']; message `<ERR_CODE>: <text>`; attribute `.code` = ERR_CODE
- raised by: company_formation.convert_concession
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 5
- given name (fixed by given code, never rename): YES
- aliases: none
- callers in given code: actions._apply_convert_concession
- callers from graph (calls/triggers): none
- api notes: Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. Raised by convert_concession.

**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA38** (gap A.2.38, severity S3, kind decision): ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).
  reason: layering (no module for a shared base) and the given except clauses.

### `company_formation.MAJOR_START_PRICES` (constant)

```python
MAJOR_START_PRICES = (60, 70, 80, 90, 100)
```

- value: `[60, 70, 80, 90, 100]`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 5
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: const.start_values for majors.

### `company_formation.MINOR_START_PRICES` (constant)

```python
MINOR_START_PRICES = (50, 60, 70, 80, 90, 100)
```

- value: `[50, 60, 70, 80, 90, 100]`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 5
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: const.start_values for minors.

### `company_formation.convert_concession` (function)

```python
convert_concession(state: GameState, player_id: str, abbr: str, start_price: int) -> None
```

- parameters: ['state', 'player_id', 'abbr', 'start_price']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 5
- given name (fixed by given code, never rename): YES
- **aliases that MUST also be exported** (same object / same behaviour): `convert_concession_to_director`
- callers in given code: actions._apply_convert_concession
- callers from graph (calls/triggers): none
- api notes: Sets any_sale_this_stock_round itself, sets concession_converted True, concession_holder None, has_operated False.

**Exceptions**:

| class | code | when |
|---|---|---|
| ConcessionError | ERR_PHASE | phase not in 2..4 |
| ConcessionError | ERR_NOT_HELD | abbr not in the player's concessions / unknown |
| ConcessionError | ERR_ALREADY_STARTED | major already floated |
| ConcessionError | ERR_LOANS | player has loans |
| ConcessionError | ERR_MUST_SELL | must_sell |
| ConcessionError | ERR_BAD_START_PRICE | start_price not in MAJOR_START_PRICES |
| ConcessionError | ERR_INSUFFICIENT_CASH | non-LNWR: cash < 2*start_price - 100 |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. 2 <= phase <= 4 -> `ERR_PHASE`
2. abbr in player.concessions (unknown abbr -> same code) -> `ERR_NOT_HELD`
3. not major.floated -> `ERR_ALREADY_STARTED`
4. player.loans == 0 -> `ERR_LOANS`
5. not certificates.must_sell -> `ERR_MUST_SELL`
6. start_price in MAJOR_START_PRICES -> `ERR_BAD_START_PRICE`
7. LNWR: nothing; else cash >= 2*start_price - 100 -> `ERR_INSUFFICIENT_CASH`

**Must NOT be checked by this function**:
- round type / active player (actions.py)
- certificate limit (count unchanged)
- leading bids

**Implements graph node(s)**: `act.convert_concession`

#### Graph node `act.convert_concession` (action) - Convert concession
Convert a held concession into the director's certificate, set the start price and float the major company (phases 2-4). Ends the turn (caller).

- graph signature (abstract): params = ['player', 'major company c', 'start_price in {60,70,80,90,100}']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.6.2] 2 <= phase <= 4 (no majors in phase 1; concessions removed at phase 5)
- [4.7.5] c in player_concessions[player]
- [3.4.1] major_status[c] = unstarted
- [4.3.1] player_loans[player] = 0
- [R10] not must_sell(player) (assumption A8)
- [1.6.4] start_price in {60,70,80,90,100}; 50 is for minors only
- [4.7.3] non-LNWR: player_cash >= 2*start_price - 100; LNWR: player pays nothing

**Effects, in order** (execute exactly in this order):
1. [4.7.2] remove c from player_concessions[player]; director_holder[c] = player; the director's units (cert_units) enter the player's holding
2. [4.7.2] call place_start_token(c, start_price, major) -- underneath all tokens already in that cell
3. [4.7.3] non-LNWR: bank_cash -= 100; player_cash -= (2*start_price - 100); company_cash[c] = 2*start_price
4. [4.7.4, R4] LNWR: bank_cash -= start_price; company_cash[c] = start_price; player pays nothing; director certificate is 1 unit
5. [3.3.2] treasury_shares[c] = 8 (LNWR 9); pool_shares[c] = 0
6. [4.7.6] major_status[c] = floated; has_completed_or[c] = false (operates in the next OR)
7. [R6] sale_happened = true (the module sets it; actions.py also does)
8. [10.1.1] call check_game_end_triggers(after_bank_payment)
9. [turn model] the turn ends after the call (caller)

**Errors listed by the graph node**:
- ERR_PHASE
- ERR_NOT_HELD
- ERR_ALREADY_STARTED
- ERR_LOANS
- ERR_MUST_SELL
- ERR_BAD_START_PRICE
- ERR_INSUFFICIENT_CASH

**Calls it must make / may trigger** (callee api in brackets):
- calls act.place_start_token -> `turn_order.place_start_token` [CROSS-MODULE] signature: `place_start_token(state: GameState, company_id: str, price: int, kind: str = 'major') -> None` 
- calls act.check_game_end_triggers -> `scoring.check_game_end_triggers` [CROSS-MODULE] signature: `check_game_end_triggers(state: GameState, context: str | None = None) -> None` 
- calls drv.must_sell -> `certificates.must_sell` [CROSS-MODULE] signature: `must_sell(state: GameState, player_id: str) -> bool` 
- calls drv.cert_units -> `certificates.cert_units` [CROSS-MODULE] signature: `cert_units(company_id: str) -> int` 

**State touched**:
- reads `st.phase` (Game phase): Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1). [type int 1..7; unit phase number; scope game]
- reads `st.player_concessions` (Concessions held): Concession certificates a player holds (acquired after resolution, 4.7.5). Removed at phase 5 (R9). [type map player->set<major>; unit concession certificates; scope per player]
- reads `st.major_status` (Major company status): Floated once its concession is converted (4.7.3). Phase-5 direct formation deferred (R11). [type map major->enum {unstarted, floated}; unit -; scope per major company]
- reads `st.player_loans` (Player loans): Outstanding loans of each player. Created by operating-round forced train purchase / emergency money raising (out of scope); reduced by repay_loans; increased by interest. [type int map player->int; unit pounds; scope per player]
- reads `st.player_cash` (Player cash): Cash in hand of each player. Never negative. [type int map player->int; unit pounds (integer); scope per player]
- writes `st.player_concessions` (Concessions held): Concession certificates a player holds (acquired after resolution, 4.7.5). Removed at phase 5 (R9). [type map player->set<major>; unit concession certificates; scope per player]
- writes `st.director_holder` (Director's certificate holder): Holder of the director's certificate of a major company (null until the company is started). The director's certificate = cert_units units (2; LNWR 1) but ONE certificate for limit counting. [type map major->player|null; unit -; scope per major company]
- writes `st.bank_cash` (Bank cash): Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5). [type int (can go below zero); unit pounds; scope game]
- writes `st.player_cash` (Player cash): Cash in hand of each player. Never negative. [type int map player->int; unit pounds (integer); scope per player]
- writes `st.company_cash` (Company treasury cash): Cash in a company's treasury: credited by buy_share (treasury source), convert_concession, float_minors, pay_private_revenues; debited by buy_train / upgrade_l_train. [type int map company->int; unit pounds; scope per major and minor company]
- writes `st.treasury_shares` (Treasury shares): Ordinary certificates in the company treasury, buyable at the current price (4.5.1, 4.7.3). 8 (LNWR 9) at flotation. [type int map major->int; unit ordinary certificates = units of 10%; scope per major company]
- writes `st.pool_shares` (Bank-pool shares): Ordinary certificates in the bank pool. Max 5 (50%) (4.4.2). [type int map major->int; unit ordinary certificates = units of 10%; scope per major company]
- writes `st.major_status` (Major company status): Floated once its concession is converted (4.7.3). Phase-5 direct formation deferred (R11). [type map major->enum {unstarted, floated}; unit -; scope per major company]
- writes `st.sale_happened` (A sale happened flag): Set true when a player buys a share, sells a share, converts a concession (R15, R6), or wins a bid-box item at resolution (R6b). Reset at stock-round start. Read by the 10.1.1 first-round nothing-sold test (R6b). Written by the module functions themselves (idempotent; the caller actions.py also sets it after buy and convert). [type bool; unit -; scope stock round]
- writes `st.has_completed_or` (Has completed an operating round): True once the major company has completed one operating turn; shares cannot be sold before (4.4.2). Initial false at flotation (set false by convert_concession), set true by advance_company when the company finished its turn. [type map major->bool; unit -; scope per major company]

**Constants used**:
- `const.start_values` (Start values): Allowed starting share prices: 50 (solid red, minors only, 1.6.3), 60, 70, 80, 90, 100 (red-outlined, majors and minors, 1.6.4). Major start price must be in {60..100}.; data: `{"minor_values": [50, 60, 70, 80, 90, 100], "major_values": [60, 70, 80, 90, 100]}`
- `const.share_structure` (Share structure of a major company): Total 10 units. Standard major: director's certificate = 2 units, 8 ordinary certificates of 1 unit. LNWR: director's certificate = 1 unit, 9 ordinary certificates. Minor: one director's certificate worth 2 shares, no other shares (3.2.2). Pool cap 5 units (4.4.2); player cap 6 units (4.5.6).; data: `{"total_units": 10, "standard": {"director_units": 2, "ordinary_certs": 8}, "lnwr": {"director_units": 1, "ordinary_certs": 9}, "pool_cap_units": 5, "hold_cap_units": 6}`

**Rules constraining this node**:
- 3.4.1: Director's certificate can't be bought while the concession is in play. [demanded in preconditions/effects]
- 4.7.3: 100 from bank plus (2*price-100) from player into treasury; floated; rest of certificates into treasury. [demanded in preconditions/effects]
- R4: Bank pays whole start price into treasury; player pays nothing; gets 1-unit director certificate; no extra discount. [demanded in preconditions/effects]
- R6: Bidding alone is not a sale; buy, sell, convert count. Phase-1 conflict open; provisional: a bid that wins an item at resolution counts. [demanded in preconditions/effects]
- 4.3.1: No buying, converting or bidding while in debt. [demanded in preconditions/effects]
- 3.3.2: 9 certificates (director 20% = two shares + eight 10%); LNWR 10 certificates. [demanded in preconditions/effects]
- 4.7.4: LNWR: 10% director's certificate; bank pays start price into treasury; floated. [demanded in preconditions/effects]
- 4.6.2: Majors may not be formed in phase 1. [demanded in preconditions/effects]
- 1.6.4: 60..100 cells are start cells for majors and minors. [demanded in preconditions/effects]
- 10.1.1: Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. [demanded in preconditions/effects]
- R10: Over the limit must sell down at first opportunity; while over and able to sell the player may not buy or bid. [demanded in preconditions/effects]
- 4.7.5: Items bid on are acquired only at round end, so convertible next round. [demanded in preconditions/effects]
- 4.7.6: After conversion the company is floated. [demanded in preconditions/effects]
- 4.7.2: Convert, choose a red-outlined start price 60..100, place token under existing tokens. [demanded in preconditions/effects]
- 2.2.3: Phase 2: minor price = bid/2 rounded down to start value, treasury 2x; concessions convertible; major train limit 4.
- 2.2.6: Text numbered 2.2.6 is the phase-1 description: minor starts at 50 with 100 treasury irrespective of bid; major companies may not be floated.
- 4.1.4: One of: buy one share, convert, place/increase up to 3 bids; round ends when all pass consecutively.
- 4.6.1: Procedure for forming majors depends on phase.
- 4.6.3: Director's certificates cannot be bought directly in phases 2-4.
- 4.7.1: A player may start a major by converting its concession in phases 2-4.
- 4.9.1: Setup after floating is identical for both formation routes; remaining 4.9.x are physical (charter tokens, revenue marker, home station) and skipped.
- R6b: In 10.1.1 'nothing sold in the first stock round' means: no share bought or sold, no concession converted, AND no bid-box item won at resolution. A round with only unsuccessful bids (nobody could pay, R8) counts as nothing sold; a round in which at least one bid wins an item counts as something sold. PROVISIONAL ruling (adopted by the task owner), replaces the provisional tail of R6.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Phase** [repr.phase_state]: maps to: state.phase: int 1..7; limits and rust from app.data.phases.PHASES_BY_NUMBER; trigger table trains.TRAIN_PHASE (module constant)
  rule for coder: phase only increases (2.2.1) and is written only by phase_check (plus debug code in main.py). PHASES_BY_NUMBER[n].trains_rusted gives ONE code per phase; skipped phases are rusted too (loop old+1..new).
- **Concession** [repr.concession]: maps to: Player.concessions: list[str] of major abbr; BidBoxItem(kind='concession', ref=abbr); MajorCompanyState.concession_holder_player_id mirrors the holder (None after conversion/clearing); concession_converted True after conversion
  rule for coder: Removal at phase 5 = absent from stack, boxes and players (no field). Writers keep the mirror fields consistent (vacate_box_item sets, convert_concession/clear_concession_boxes clear).
- **Company status mirrors** [repr.company_status]: maps to: MajorCompanyState.floated / concession_converted / has_operated / share_price; MinorCompanyState.floated / share_price / removed / acquired_by_major
  rule for coder: floated=True and concession_converted=True on conversion; has_operated False at flotation, True after the first completed operating turn (advance_company); share_price is a display mirror nobody reads (read prices from the grid via current_price).
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.
- **Director's certificate** [repr.director_certificate]: maps to: MajorCompanyState.director_player_id (None until started) + cert_units units inside Player.shares[c]
  rule for coder: ONE certificate for the limit regardless of its units; the holder's Player.shares includes the units; it is never in shares_in_treasury or shares_in_bank_pool; LNWR director = 1 unit.
- **Bank pool naming** [repr.bank_pool_naming]: maps to: SHARES: MajorCompanyState.shares_in_bank_pool (units, max 5) = 'the bank pool'; TRAINS: BankState.discarded_trains (list of codes) = 'the bank pool' of trains
  rule for coder: buy_share source strings: 'bank' and 'pool' BOTH mean the bank pool of shares; 'treasury' = MajorCompanyState.shares_in_treasury (ordinary units only, the director's certificate is never in it; LNWR 9, others 8 at flotation); None = module chooses (pool first, else treasury).
- **'A sale happened' flag** [repr.sale_flag]: maps to: state.any_sale_this_stock_round (bool)
  rule for coder: Set True by: sell_shares, buy_share, convert_concession (module functions themselves; actions.py also sets it after buy and convert), and resolve_bids when a bid-box item is WON (R6b). Reset to False by start_stock_round. Read by check_game_end_triggers(context='end_of_stock_round').


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA01** (gap A.1.1, severity S1, kind graph_fix): Follow the skeleton: every successful sell / buy / convert / bid action ends the turn. turn.stage, turn.c_used, turn.acted and the errors ERR_WRONG_STAGE / ERR_C_ALREADY_USED / ERR_NO_ACTION_TAKEN are removed; the order edges sell->repay->C are removed; repay_loans stays as an unwired action (wired=false, implemented and exported); a new given action stock_turn_action models actions.py (calls ONE module function, increments bids_this_turn, resets pass_streak, calls end_turn).
  reason: actions.py is given and its docstring says the combination is 'not wired up yet'; a literal v1 implementation would have vacuous preconditions.
- **GA07** (gap A.1.7, severity S2, kind graph_fix): sell_shares, buy_share and convert_concession all set the flag themselves (idempotent); actions.py's extra write after buy/convert is documented as redundant; resolve_bids sets it when an item is won (R6b).
  reason: makes direct calls of module functions consistent; R15.
- **GA32** (gap A.2.32, severity S3, kind carried): No certificate-limit effect (concession 1 -> director certificate 1); leading bids ignored (A7). A major whose concession was not converted before phase 5 can never start (R9 + R11, A25).  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: R9/R11 consequence.
- **GA39** (gap A.2.39, severity S3, kind repr): shares_in_treasury counts ORDINARY units only (8; LNWR 9); the director's certificate is never in it; the models comment 'director cert = 2' does not apply.
  reason: operating._pay_major_dividend counts them as plain units.
- **GA08** (gap A.1.8, severity S2, kind graph_fix): In scope now: active_company_id, advance_company, start/begin/end of operating rounds, set size lock, game_over maturity, has_completed_or writer (advance_company), start-of-OR revenues. States or_set_size, or_index, or_order, or_current, round_type added; phase_events is an audit log only.
  reason: required by actions.py/main.py; without a writer of has_operated no share could ever be sold.
- **GB06** (gap B-6, severity S2, kind graph_fix): advance_company writes has_completed_or for a major (now a graph effect, state no longer external).
  reason: GA08.
- **GA21** (gap A.2.21, severity S3, kind graph_fix): Every api node lists its enforced preconditions in an ORDERED list (attrs.enforced, field n); the first failing check raises. Order = listed order; unknown ids first, then argument validity, then rule checks.
  reason: mechanical contracts need a total order.

### `company_formation.minor_start_price` (function)

```python
minor_start_price(phase: int, bid: int) -> int
```

- parameters: ['phase', 'bid']
- defaults (explicit): (none)
- returns: phase 1: 50; else max start value <= bid//2, min 50, max 100
- layer: 5
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `start_price_for_minor`
- callers in given code: none
- callers from graph (calls/triggers): company_formation.float_minors

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception

**Implements graph node(s)**: `drv.minor_start_price`

#### Graph node `drv.minor_start_price` (derived) - Minor start price
Starting share price of a purchased minor.

- graph signature (abstract): params = ['phase', 'bid']; returns = int

**Formula**: [4.11.4, R2] phase 1: 50; phase >=2: max{v in {50,60,...,100} : v <= floor(bid/2)}, min 50, max 100

**Constants used**:
- `const.start_values` (Start values): Allowed starting share prices: 50 (solid red, minors only, 1.6.3), 60, 70, 80, 90, 100 (red-outlined, majors and minors, 1.6.4). Major start price must be in {60..100}.; data: `{"minor_values": [50, 60, 70, 80, 90, 100], "major_values": [60, 70, 80, 90, 100]}`

**Rules constraining this node**:
- R2: Highest start value <= half the winning bid, minimum 50. [formula]
- 4.11.4: Phase 1: 50/100; phase 2: half bid down to start value, treasury 2x; phase 3+: same price, treasury = bid. [formula]
- 2.2.3: Phase 2: minor price = bid/2 rounded down to start value, treasury 2x; concessions convertible; major train limit 4.
- 2.2.6: Text numbered 2.2.6 is the phase-1 description: minor starts at 50 with 100 treasury irrespective of bid; major companies may not be floated.


### `company_formation.minor_start_treasury` (function)

```python
minor_start_treasury(phase: int, bid: int, price: int | None = None) -> int
```

- parameters: ['phase', 'bid', 'price']
- defaults (explicit): {"price": "None"}
- returns: phase 1: 100; phase 2: 2*price; phase >= 3: bid; price None = minor_start_price(phase, bid)
- layer: 5
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): company_formation.float_minors

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception

**Implements graph node(s)**: `drv.minor_start_treasury`

#### Graph node `drv.minor_start_treasury` (derived) - Minor starting treasury
Cash a purchased minor receives.

- graph signature (abstract): params = ['phase', 'bid', 'price']; returns = int

**Formula**: [4.11.4, R3] phase 1: 100; phase 2: 2*price; phase >=3: bid

**Rules constraining this node**:
- R3: Player pays full bid to bank. Phase 1: treasury 100, price 50. Phase 2: treasury 2x price. Phase 3+: treasury = bid. Bank covers difference. [formula]
- 4.11.4: Phase 1: 50/100; phase 2: half bid down to start value, treasury 2x; phase 3+: same price, treasury = bid. [formula]
- 2.2.3: Phase 2: minor price = bid/2 rounded down to start value, treasury 2x; concessions convertible; major train limit 4.
- 2.2.4: Phase 3: L rusts; minor price as phase 2 but treasury = full bid.
- 2.2.6: Text numbered 2.2.6 is the phase-1 description: minor starts at 50 with 100 treasury irrespective of bid; major companies may not be floated.


### `company_formation.minor_float_order` (function)

```python
minor_float_order(pending: Iterable[tuple[int, int, int, str]]) -> list[tuple[int, int, int, str]]
```

- parameters: ['pending']
- defaults (explicit): (none)
- returns: bid descending, tie lower box_index first
- layer: 5
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): company_formation.float_minors

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.minor_float_order`

#### Graph node `drv.minor_float_order` (derived) - Minor flotation order
Order in which purchased minors are floated.

- graph signature (abstract): params = ['list of pending minors']; returns = list

**Formula**: [4.11.3] sort by bid desc, tie -> lower box number

**State touched**:
- reads `st.pending_minor_floats` (Minors awaiting flotation): Minors paid for during resolve_bids, to be floated by float_minors in flotation order (4.11.3). Local return value, not stored. [type list<(minor_number, bid, box_index, buyer)>; unit -; scope call-scoped]

**Rules constraining this node**:
- 4.11.3: Purchased minors float from highest sum bid down; tie -> lowest box. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Values that live only inside one procedure** [repr.call_scoped]: maps to: items_with_bids -> set[(kind, box_index)] and pending_minor_floats -> list[(minor_number, bid, box_index, buyer_player_id)]: return value of resolve_bids, passed to unsold_minor_exports / float_minors; never stored
  rule for coder: float_minors(state, pending=None) and unsold_minor_exports(state, items_with_bids=()) therefore take them as parameters (signature change relative to v1).


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA14** (gap A.1.14, severity S2, kind graph_fix): items_with_bids and pending_minor_floats are call-scoped states: returned by resolve_bids and passed as parameters (float_minors(state, pending=None), unsold_minor_exports(state, items_with_bids=())).
  reason: no field exists; signatures changed vs v1.

### `company_formation.float_minors` (function)

```python
float_minors(state: GameState, pending: Iterable[tuple[int, int, int, str]] | None = None) -> None
```

- parameters: ['state', 'pending']
- defaults (explicit): {"pending": "None"}
- returns: (see signature)
- layer: 5
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `float_minor_companies`
- callers in given code: none
- callers from graph (calls/triggers): bidding.resolve_stock_round
- api notes: pending items are (minor_number, bid, box_index, buyer_player_id). Sets MinorCompanyState.floated, treasury, share_price. Calls check_game_end_triggers once after the loop.

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception; None or empty is a no-op

**Implements graph node(s)**: `act.float_minors`

#### Graph node `act.float_minors` (action) - Float purchased minors
Start each purchased minor: price, treasury, token.

- graph signature (abstract): params = ['pending_minor_floats (default none)']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.11.4] flotation uses the phase at resolution time, before this round's exports

**Effects, in order** (execute exactly in this order):
1. [4.11.3] for pending in minor_float_order: price = minor_start_price(phase,bid); treasury = minor_start_treasury(phase,bid,price)
2. [4.11.5] call place_start_token(minor, price, minor)
3. [R3] bank_cash -= treasury; company_cash[minor] = treasury (buyer already paid the full bid to the bank); the minor is marked floated
4. [10.1.1] call check_game_end_triggers(after_bank_payment) ONCE after the loop

**Errors listed by the graph node**:
- NONE (raises nothing)

**Order edges**:
- `act.float_minors` runs before `act.unsold_minor_exports` (seq 2; resolve: seq 2 runs before seq 3)
- `act.resolve_bids` runs before `act.float_minors` (seq 1; resolve: seq 1 runs before seq 2)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.minor_float_order -> `company_formation.minor_float_order` [same module] signature: `minor_float_order(pending: Iterable[tuple[int, int, int, str]]) -> list[tuple[int, int, int, str]]` 
- calls drv.minor_start_price -> `company_formation.minor_start_price` [same module] signature: `minor_start_price(phase: int, bid: int) -> int` 
- calls drv.minor_start_treasury -> `company_formation.minor_start_treasury` [same module] signature: `minor_start_treasury(phase: int, bid: int, price: int | None = None) -> int` 
- calls act.place_start_token -> `turn_order.place_start_token` [CROSS-MODULE] signature: `place_start_token(state: GameState, company_id: str, price: int, kind: str = 'major') -> None` 
- calls act.check_game_end_triggers -> `scoring.check_game_end_triggers` [CROSS-MODULE] signature: `check_game_end_triggers(state: GameState, context: str | None = None) -> None` 

**State touched**:
- reads `st.pending_minor_floats` (Minors awaiting flotation): Minors paid for during resolve_bids, to be floated by float_minors in flotation order (4.11.3). Local return value, not stored. [type list<(minor_number, bid, box_index, buyer)>; unit -; scope call-scoped]
- reads `st.phase` (Game phase): Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1). [type int 1..7; unit phase number; scope game]
- reads `st.minor_director` (Minor director's certificate holder): Player holding the 50% director's certificate of a minor (counts 1 certificate; assumption A6). Non-null = purchased and floated. [type map minor->player|null; unit -; scope per minor company]
- writes `st.company_cash` (Company treasury cash): Cash in a company's treasury: credited by buy_share (treasury source), convert_concession, float_minors, pay_private_revenues; debited by buy_train / upgrade_l_train. [type int map company->int; unit pounds; scope per major and minor company]
- writes `st.bank_cash` (Bank cash): Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5). [type int (can go below zero); unit pounds; scope game]

**Rules constraining this node**:
- 4.11.3: Purchased minors float from highest sum bid down; tie -> lowest box. [demanded in preconditions/effects]
- 4.11.4: Phase 1: 50/100; phase 2: half bid down to start value, treasury 2x; phase 3+: same price, treasury = bid. [demanded in preconditions/effects]
- R3: Player pays full bid to bank. Phase 1: treasury 100, price 50. Phase 2: treasury 2x price. Phase 3+: treasury = bid. Bank covers difference. [demanded in preconditions/effects]
- 4.11.5: Minor tokens go on top of majors and beneath existing minors. [demanded in preconditions/effects]
- 10.1.1: Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. [demanded in preconditions/effects]
- 3.2.2: A minor has only a 50% director's certificate worth two shares; no other shares exist.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Values that live only inside one procedure** [repr.call_scoped]: maps to: items_with_bids -> set[(kind, box_index)] and pending_minor_floats -> list[(minor_number, bid, box_index, buyer_player_id)]: return value of resolve_bids, passed to unsold_minor_exports / float_minors; never stored
  rule for coder: float_minors(state, pending=None) and unsold_minor_exports(state, items_with_bids=()) therefore take them as parameters (signature change relative to v1).
- **Phase** [repr.phase_state]: maps to: state.phase: int 1..7; limits and rust from app.data.phases.PHASES_BY_NUMBER; trigger table trains.TRAIN_PHASE (module constant)
  rule for coder: phase only increases (2.2.1) and is written only by phase_check (plus debug code in main.py). PHASES_BY_NUMBER[n].trains_rusted gives ONE code per phase; skipped phases are rusted too (loop old+1..new).
- **Minor company ownership** [repr.minor_ownership]: maps to: MinorCompanyState.director_player_id (non-None after award); NO entry in Player.shares; id 'M<n>'
  rule for coder: A minor counts 1 certificate for its director (certs_held dispatches on `cid in state.minors`). floated=True is set by float_minors; removed=True for a removed minor (director stays None). Follows the graph, not the models.py comment (decision GA10).
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA25** (gap A.2.25, severity S3, kind decision): float_minors, pay_concession_dividends and pay_private_revenues call check_game_end_triggers ONCE after all payments.
  reason: the bank-broken latch is monotone within a call.
- **GB21** (gap B-21, severity S3, kind decision): See GA25.
  reason: GA25.
- **GA14** (gap A.1.14, severity S2, kind graph_fix): items_with_bids and pending_minor_floats are call-scoped states: returned by resolve_bids and passed as parameters (float_minors(state, pending=None), unsold_minor_exports(state, items_with_bids=())).
  reason: no field exists; signatures changed vs v1.

## 4. Rules this module is responsible for (id + text, verbatim from the graph)

- **1.6.4** (rule): 60..100 cells are start cells for majors and minors. -- constrains `act.convert_concession`
- **10.1.1** (rule): Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. -- constrains `act.convert_concession`, `act.float_minors`
- **2.2.3** (rule): Phase 2: minor price = bid/2 rounded down to start value, treasury 2x; concessions convertible; major train limit 4. -- constrains `act.convert_concession`, `drv.minor_start_price`, `drv.minor_start_treasury`
- **2.2.4** (rule): Phase 3: L rusts; minor price as phase 2 but treasury = full bid. -- constrains `drv.minor_start_treasury`
- **2.2.6** (rule): Text numbered 2.2.6 is the phase-1 description: minor starts at 50 with 100 treasury irrespective of bid; major companies may not be floated. -- constrains `act.convert_concession`, `drv.minor_start_price`, `drv.minor_start_treasury`
- **3.2.2** (rule): A minor has only a 50% director's certificate worth two shares; no other shares exist. -- constrains `act.float_minors`
- **3.3.2** (rule): 9 certificates (director 20% = two shares + eight 10%); LNWR 10 certificates. -- constrains `act.convert_concession`
- **3.4.1** (rule): Director's certificate can't be bought while the concession is in play. -- constrains `act.convert_concession`
- **4.1.4** (rule): One of: buy one share, convert, place/increase up to 3 bids; round ends when all pass consecutively. -- constrains `act.convert_concession`
- **4.11.3** (rule): Purchased minors float from highest sum bid down; tie -> lowest box. -- constrains `drv.minor_float_order`, `act.float_minors`
- **4.11.4** (rule): Phase 1: 50/100; phase 2: half bid down to start value, treasury 2x; phase 3+: same price, treasury = bid. -- constrains `drv.minor_start_price`, `drv.minor_start_treasury`, `act.float_minors`
- **4.11.5** (rule): Minor tokens go on top of majors and beneath existing minors. -- constrains `act.float_minors`
- **4.3.1** (rule): No buying, converting or bidding while in debt. -- constrains `act.convert_concession`
- **4.6.1** (rule): Procedure for forming majors depends on phase. -- constrains `act.convert_concession`
- **4.6.2** (rule): Majors may not be formed in phase 1. -- constrains `act.convert_concession`
- **4.6.3** (rule): Director's certificates cannot be bought directly in phases 2-4. -- constrains `act.convert_concession`
- **4.7.1** (rule): A player may start a major by converting its concession in phases 2-4. -- constrains `act.convert_concession`
- **4.7.2** (rule): Convert, choose a red-outlined start price 60..100, place token under existing tokens. -- constrains `act.convert_concession`
- **4.7.3** (rule): 100 from bank plus (2*price-100) from player into treasury; floated; rest of certificates into treasury. -- constrains `act.convert_concession`
- **4.7.4** (rule): LNWR: 10% director's certificate; bank pays start price into treasury; floated. -- constrains `act.convert_concession`
- **4.7.5** (rule): Items bid on are acquired only at round end, so convertible next round. -- constrains `act.convert_concession`
- **4.7.6** (rule): After conversion the company is floated. -- constrains `act.convert_concession`
- **4.9.1** (rule): Setup after floating is identical for both formation routes; remaining 4.9.x are physical (charter tokens, revenue marker, home station) and skipped. -- constrains `act.convert_concession`
- **R10** (ruling): Over the limit must sell down at first opportunity; while over and able to sell the player may not buy or bid. -- constrains `act.convert_concession`
- **R2** (ruling): Highest start value <= half the winning bid, minimum 50. -- constrains `drv.minor_start_price`
- **R3** (ruling): Player pays full bid to bank. Phase 1: treasury 100, price 50. Phase 2: treasury 2x price. Phase 3+: treasury = bid. Bank covers difference. -- constrains `drv.minor_start_treasury`, `act.float_minors`
- **R4** (ruling): Bank pays whole start price into treasury; player pays nothing; gets 1-unit director certificate; no extra discount. -- constrains `act.convert_concession`
- **R6** (ruling): Bidding alone is not a sale; buy, sell, convert count. Phase-1 conflict open; provisional: a bid that wins an item at resolution counts. -- constrains `act.convert_concession`
- **R6b** (ruling): In 10.1.1 'nothing sold in the first stock round' means: no share bought or sold, no concession converted, AND no bid-box item won at resolution. A round with only unsuccessful bids (nobody could pay, R8) counts as nothing sold; a round in which at least one bid wins an item counts as something sold. PROVISIONAL ruling (adopted by the task owner), replaces the provisional tail of R6. -- constrains `act.convert_concession`

