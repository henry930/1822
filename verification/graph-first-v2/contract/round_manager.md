# Contract: `backend/app/engine/round_manager.py`

Generated mechanically from graph v2 by gen_contracts.py. Read COMMON.md first, then this file; BINDING.md lists the representation rules and the cross-module call matrix.

Import layering: this module is layer 7 (1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares and company_formation, 6 bidding, 7 round_manager). Calls to a HIGHER layer must be lazy imports inside the function body; never import upward at module level.

## 1. Export list (every name below, plus every alias, must exist at module level)

- `RoundError` (exception)
- `sr_over` (function)
- `next_player` (function)
- `begin_turn` (function)
- `start_stock_round` (function)
- `advance_stock_player` (function)  aliases: end_turn
- `end_stock_round` (function)
- `active_company_id` (function)  aliases: active_company
- `advance_company` (function)
- `start_operating_round` (function)
- `begin_operating_round` (function)  aliases: start_operating_set_round
- `end_operating_round` (function)
- `operating_rounds_for_next_set` (function)

Public API count: 13

## 2. Module-level obligations

### States this module writes (flags and data it is responsible for)
- `st.turn` (Active turn record): Whose stock turn it is and how many bids were already placed/moved in this turn. v2 follows the skeleton turn model: EVERY successful sell / buy / convert / bid action ends the turn; there is no stage, no c_used, no acted. bids_made is incremented by the CALLER (actions.py), never by the bidding module, and reset by begin_turn. -- written by `act.begin_turn`
- `st.round_type` (Round type): Which kind of round is running. The game is in a stock round from setup (round 1 is pre-started by new_game) until end_stock_round starts the first operating-round set, and so on alternately (1.7.14, 5.1.1). Replaces the v1 sr_status (no field exists for it). -- written by `act.start_stock_round`, `act.start_operating_round`
- `st.sale_happened` (A sale happened flag): Set true when a player buys a share, sells a share, converts a concession (R15, R6), or wins a bid-box item at resolution (R6b). Reset at stock-round start. Read by the 10.1.1 first-round nothing-sold test (R6b). Written by the module functions themselves (idempotent; the caller actions.py also sets it after buy and convert). -- written by `act.start_stock_round`
- `st.sold_this_round` (Sold-this-round map): (player, company) pairs such that the player sold >=1 share of the company this stock round; blocks buying that company (4.5.5). Cleared at stock-round start. Stored as lists, not sets (JSON). -- written by `act.start_stock_round`
- `st.pass_streak` (Consecutive passes): Number of consecutive turns that were passes; round ends when it equals the player count (4.11.1). -- written by `act.start_stock_round`
- `st.sr_completed` (Stock rounds completed): Number of stock rounds that have finished their resolution (0 during the first stock round). Written ONLY by end_stock_round, after resolve_stock_round returned; so the 10.1.1 'first stock round' test is sr_completed == 0 inside resolution step 9. -- written by `act.end_stock_round`
- `st.has_completed_or` (Has completed an operating round): True once the major company has completed one operating turn; shares cannot be sold before (4.4.2). Initial false at flotation (set false by convert_concession), set true by advance_company when the company finished its turn. -- written by `act.advance_company`
- `st.or_order` (Operating order so far): Companies already chosen to run in the current operating round, in running order; the next company is chosen only after the previous one finished (5.2.2) (models.operating_order). -- written by `act.advance_company`, `act.begin_operating_round`
- `st.or_current` (Current company index): Index into or_order of the company whose turn it is (models.current_company_index). active_company = or_order[or_current]. -- written by `act.advance_company`, `act.begin_operating_round`
- `st.or_index` (Index of the running operating round): Which operating round of the set is running (models.operating_round_index). -- written by `act.start_operating_round`, `act.end_operating_round`
- `st.or_set_size` (Operating rounds in the current set): Number of operating rounds in the set following the stock round; LOCKED when the set starts (models.operating_rounds_this_set; 2.1.2, 5.1.1); forced to 1 by a 'next_or' trigger (10.1.1). -- written by `act.start_operating_round`
- `st.game_end` (Game end trigger): First trigger wins (10.1.2). over = game_over (immediate trigger or matured deferred trigger). -- written by `act.start_operating_round`, `act.end_operating_round`

### Hooks / triggers fired by this module's nodes
- `act.start_stock_round` triggers `act.begin_turn` (`round_manager.begin_turn`)
- `act.end_turn` triggers `act.begin_turn` (`round_manager.begin_turn`)
- `act.end_stock_round` triggers `act.resolve_stock_round` (`bidding.resolve_stock_round`)
- `act.end_stock_round` triggers `act.start_operating_round` (`round_manager.start_operating_round`)
- `act.advance_company` triggers `act.end_operating_round` (`round_manager.end_operating_round`)
- `act.start_operating_round` triggers `act.begin_operating_round` (`round_manager.begin_operating_round`)
- `act.begin_operating_round` triggers `act.pay_private_revenues` (`scoring.pay_private_revenues`)
- `act.begin_operating_round` triggers `act.pay_concession_dividends` (`scoring.pay_concession_dividends`)
- `act.begin_operating_round` triggers `act.end_operating_round` (`round_manager.end_operating_round`)
- `act.end_operating_round` triggers `act.begin_operating_round` (`round_manager.begin_operating_round`)
- `act.end_operating_round` triggers `act.start_stock_round` (`round_manager.start_stock_round`)

### Notes that name 'sets ... itself' / flags (from api notes)
- `RoundError`: Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. Raised for invalid player ids, game over and missing active company.
- `begin_turn`: Sets active_player_id and bids_this_turn = 0.
- `end_stock_round`: Order: phase_before = phase; bidding.resolve_stock_round; stock_rounds_completed += 1; if game_over: stop; else start_operating_round(state, phase_before).
- `advance_company`: Sets has_operated True for a major that finished its turn.
- `start_operating_round`: phase_before None = current phase (no 2.1.2 deferral).

### Module-level decisions (resolve any api or node of this module)
- **GA38** (gap A.2.38, severity S3, kind decision): ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).
  reason: layering (no module for a shared base) and the given except clauses.
- **GA37** (gap A.2.37, severity S3, kind decision): resolve_stock_round and end_stock_round do NOT check sr_over or round_type; the round manager (actions._apply_pass) decides when. No ERR_NOT_OVER exists.
  reason: callable whenever the caller invokes it; avoids lazy cross-component import.
- **GA04** (gap A.1.4, severity S1, kind graph_fix): setup_game effects now match new_game: boxes are filled by setup and the state is already inside stock round 1 (round_type STOCK, active player = order[0], sr_completed 0). start_stock_round is for rounds >= 2 and debug.
  reason: setup.py is given.
- **GA05** (gap A.1.5, severity S2, kind graph_fix): st.sr_status is dropped; st.round_type (STOCK/OPERATING) replaces it. start_stock_round raises only ERR_GAME_OVER, never 'already running'.
  reason: main.py calls start_stock_round at arbitrary times.
- **GB18** (gap B-18, severity S3, kind decision): See GA05.
  reason: GA05.
- **DN15** (gap new, severity S3, kind decision): After game_over actions.apply_action refuses all actions; round managers raise ERR_GAME_OVER in start_stock_round / start_operating_round / end_stock_round.
  reason: 10.1.2.
- **GA01** (gap A.1.1, severity S1, kind graph_fix): Follow the skeleton: every successful sell / buy / convert / bid action ends the turn. turn.stage, turn.c_used, turn.acted and the errors ERR_WRONG_STAGE / ERR_C_ALREADY_USED / ERR_NO_ACTION_TAKEN are removed; the order edges sell->repay->C are removed; repay_loans stays as an unwired action (wired=false, implemented and exported); a new given action stock_turn_action models actions.py (calls ONE module function, increments bids_this_turn, resets pass_streak, calls end_turn).
  reason: actions.py is given and its docstring says the combination is 'not wired up yet'; a literal v1 implementation would have vacuous preconditions.
- **GA02** (gap A.1.2, severity S1, kind decision): A pass is NOT blocked when must_sell is true (actions.py increments the pass counter before any module code runs); R10 is enforced only for buy_share, convert_concession and bids. end_turn/advance_stock_player and begin_turn have no must_sell check.  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: Not enforceable inside the new modules without editing actions.py. Suggested owner change: reject 'pass' in actions._apply_pass when certificates.must_sell(state, player_id).
- **GB23** (gap B-23, severity S3, kind graph_fix): Explicit in act.end_turn effects.
  reason: GA01.
- **GB17** (gap B-17, severity S3, kind graph_fix): Now an effect line of act.end_stock_round.
  reason: 10.1.1.
- **DN01** (gap new, severity S2, kind decision): The set after a stock round has ors_per_sr[phase_before] rounds, phase_before = phase at the start of that stock round's resolution (a local value of end_stock_round); next_or forces 1. A phase 2 that starts during resolution (export) therefore gives 1 OR after that stock round and 2 after the next; a phase 2 that starts in an operating round gives 2 after the next stock round. No new field is needed.
  reason: 'applies after the following stock round' (2.1.2, 5.1.1, 2.2.3).
- **GA08** (gap A.1.8, severity S2, kind graph_fix): In scope now: active_company_id, advance_company, start/begin/end of operating rounds, set size lock, game_over maturity, has_completed_or writer (advance_company), start-of-OR revenues. States or_set_size, or_index, or_order, or_current, round_type added; phase_events is an audit log only.
  reason: required by actions.py/main.py; without a writer of has_operated no share could ever be sold.
- **GB06** (gap B-6, severity S2, kind graph_fix): advance_company writes has_completed_or for a major (now a graph effect, state no longer external).
  reason: GA08.
- **GB15** (gap B-15, severity S1, kind graph_fix): Now explicit actions start_operating_round / begin_operating_round / advance_company / end_operating_round with the 2.1.2 deferral via phase_before.
  reason: GA08.
- **DN09** (gap new, severity S3, kind decision): begin_operating_round still pays step A, then ends immediately; the set continues.
  reason: 5.2.1 step A applies at the start of EACH OR.
- **DN12** (gap new, severity S3, kind decision): Privates pay before concessions (both step A); the order is irrelevant for money, only the bank-broken latch could differ.
  reason: 5.2.1 A.
- **GA03** (gap A.1.3, severity S2, kind graph_fix): check_game_end_triggers(state, context=None). The kind of a deferred trigger comes from round_type: STOCK -> 'next_or'; OPERATING -> token on game-end cell 'or_end', bank broken 'or_set_end'. context only matters for 'end_of_stock_round' (nothing-sold test). Maturity (setting game_over) is written by end_operating_round.
  reason: All given callers pass one argument; models.py comments define the three stored values.
- **GA36** (gap A.2.36, severity S3, kind graph_fix): game_over is set by check_game_end_triggers (immediate) and by end_operating_round (matured or_end / or_set_end / next_or); drv.final_ranking added (ties keep player order).  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: 10.1.x.
- **GA26** (gap A.2.26, severity S2, kind graph_fix): (a) concession clearing only when old < 5 <= new; (b) rust events of every skipped phase old+1..new are applied; (c) the 2.1.2 deferral is handled by operating_rounds_for_next_set with phase_before; (d) phase_events is an audit log, rust/discard/limits are applied immediately.
  reason: rules 2.1.2-2.1.5, 2.2.1.

## 3. API contracts

### `round_manager.RoundError` (exception)

```python
class RoundError(Exception)
```

- bases: ['Exception']; message `<ERR_CODE>: <text>`; attribute `.code` = ERR_CODE
- raised by: round_manager.advance_company, round_manager.begin_turn, round_manager.end_stock_round, round_manager.next_player, round_manager.start_operating_round, round_manager.start_stock_round
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 7
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. Raised for invalid player ids, game over and missing active company.

**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA38** (gap A.2.38, severity S3, kind decision): ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).
  reason: layering (no module for a shared base) and the given except clauses.

### `round_manager.sr_over` (function)

```python
sr_over(state: GameState) -> bool
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: state.consecutive_passes >= len(state.player_order)
- layer: 7
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.sr_over`

#### Graph node `drv.sr_over` (derived) - Stock round over?
True when all players passed consecutively.

- graph signature (abstract): params = ['none']; returns = bool

**Formula**: [4.11.1] pass_streak >= player_count (actions.py uses >=; == for valid play)

**State touched**:
- reads `st.pass_streak` (Consecutive passes): Number of consecutive turns that were passes; round ends when it equals the player count (4.11.1). [type int; unit turns; scope stock round]
- reads `st.player_count` (Player count): Number of players n; set once at setup. [type int 3..7; unit players; scope game]

**Rules constraining this node**:
- 4.11.1: All players pass consecutively -> stock round over. [formula]
- 4.1.4: One of: buy one share, convert, place/increase up to 3 bids; round ends when all pass consecutively.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Consecutive passes** [repr.pass_streak]: maps to: state.consecutive_passes
  rule for coder: Written ONLY by actions.py (+=1 on pass; =0 after a turn-ending action) and reset by start_stock_round; advance_stock_player must not touch it. Round over when >= len(player_order).
- **Stock-turn order** [repr.sr_order]: maps to: state.player_order (list, index 0 = Player-1 card) AND state.priority_deal_player_id
  rule for coder: player_count = len(state.player_order) (3..7; no stored field). Invariant: priority_deal_player_id == player_order[0]. Writers of player_order (reorder_players_by_cash, setup) rewrite priority_deal_player_id too; start_stock_round re-asserts it.


### `round_manager.next_player` (function)

```python
next_player(state: GameState, player_id: str) -> str
```

- parameters: ['state', 'player_id']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 7
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): round_manager.advance_stock_player

**Exceptions**:

| class | code | when |
|---|---|---|
| RoundError | ERR_WRONG_PLAYER | player_id not in player_order |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. player_id in player_order -> `ERR_WRONG_PLAYER`

**Implements graph node(s)**: `drv.next_player`

#### Graph node `drv.next_player` (derived) - Next player in order
The player after p in the cyclic stock-turn order.

- graph signature (abstract): params = ['player p']; returns = player

**Formula**: [4.1.2] sr_order[(index(p)+1) mod n]

**State touched**:
- reads `st.sr_order` (Stock-turn order): Order in which players take stock turns; random at setup (1.7.12); recomputed by cash at each stock-round end (4.11.9). Also the direction for 'nearest after' tie-breaks (4.4.2). The player holding card 1 (index 0) is the start player of every stock round. [type list<player>; unit player ids, index 0 = Player 1 card; scope game]
- reads `st.player_count` (Player count): Number of players n; set once at setup. [type int 3..7; unit players; scope game]

**Rules constraining this node**:
- 4.1.2: Round starts with Player 1 and proceeds in order; share transfers only between player and bank/company. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Stock-turn order** [repr.sr_order]: maps to: state.player_order (list, index 0 = Player-1 card) AND state.priority_deal_player_id
  rule for coder: player_count = len(state.player_order) (3..7; no stored field). Invariant: priority_deal_player_id == player_order[0]. Writers of player_order (reorder_players_by_cash, setup) rewrite priority_deal_player_id too; start_stock_round re-asserts it.


### `round_manager.begin_turn` (function)

```python
begin_turn(state: GameState, player_id: str) -> None
```

- parameters: ['state', 'player_id']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 7
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): round_manager.advance_stock_player, round_manager.start_stock_round
- api notes: Sets active_player_id and bids_this_turn = 0.

**Exceptions**:

| class | code | when |
|---|---|---|
| RoundError | ERR_WRONG_PLAYER | player_id not in player_order |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. player_id in player_order -> `ERR_WRONG_PLAYER`

**Must NOT be checked by this function**:
- that player_id is the correct successor (callers guarantee)

**Implements graph node(s)**: `act.begin_turn`

#### Graph node `act.begin_turn` (action) - Begin a player's stock turn
Make a player active and reset the per-turn bid counter.

- graph signature (abstract): params = ['player_id']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.1.2] player_id is a player of the game (the correct successor is guaranteed by the callers)

**Effects, in order** (execute exactly in this order):
1. [4.1.3] turn.active_player = player_id; turn.bids_made = 0

**Errors listed by the graph node**:
- ERR_WRONG_PLAYER: player_id not in player_order (RoundError)

**State touched**:
- reads `st.sr_order` (Stock-turn order): Order in which players take stock turns; random at setup (1.7.12); recomputed by cash at each stock-round end (4.11.9). Also the direction for 'nearest after' tie-breaks (4.4.2). The player holding card 1 (index 0) is the start player of every stock round. [type list<player>; unit player ids, index 0 = Player 1 card; scope game]
- writes `st.turn` (Active turn record): Whose stock turn it is and how many bids were already placed/moved in this turn. v2 follows the skeleton turn model: EVERY successful sell / buy / convert / bid action ends the turn; there is no stage, no c_used, no acted. bids_made is incremented by the CALLER (actions.py), never by the bidding module, and reset by begin_turn. [type record {active_player, bids_made}; unit -; scope game]

**Rules constraining this node**:
- 4.1.3: Sell, then repay loans, then one of buy/convert/bid; may pass. [demanded in preconditions/effects]
- 4.1.2: Round starts with Player 1 and proceeds in order; share transfers only between player and bank/company. [demanded in preconditions/effects]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Stock-turn order** [repr.sr_order]: maps to: state.player_order (list, index 0 = Player-1 card) AND state.priority_deal_player_id
  rule for coder: player_count = len(state.player_order) (3..7; no stored field). Invariant: priority_deal_player_id == player_order[0]. Writers of player_order (reorder_players_by_cash, setup) rewrite priority_deal_player_id too; start_stock_round re-asserts it.
- **Stock round start / priority player** [repr.sr_start_player]: maps to: state.active_player_id = player_order[0] at the start of every stock round
  rule for coder: Round 1: set by setup.new_game (the first stock round is pre-started, start_stock_round is not called). Later rounds: start_stock_round -> begin_turn(player_order[0]). Order of play inside a round: next_player(state, pid) = player_order[(index+1) % n]; bids_this_turn reset by begin_turn.
- **Turn record** [repr.turn_record]: maps to: state.active_player_id (turn.active_player) and state.bids_this_turn (turn.bids_made); NO fields for stage / c_used / acted (dropped in v2)
  rule for coder: SKELETON TURN MODEL: every successful sell_shares / buy_share / convert_concession / bid action ends the turn (actions.py calls advance_stock_player). bids_this_turn is incremented by actions.py after each place_or_move_bid and reset by begin_turn; the bidding module only READS it.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA01** (gap A.1.1, severity S1, kind graph_fix): Follow the skeleton: every successful sell / buy / convert / bid action ends the turn. turn.stage, turn.c_used, turn.acted and the errors ERR_WRONG_STAGE / ERR_C_ALREADY_USED / ERR_NO_ACTION_TAKEN are removed; the order edges sell->repay->C are removed; repay_loans stays as an unwired action (wired=false, implemented and exported); a new given action stock_turn_action models actions.py (calls ONE module function, increments bids_this_turn, resets pass_streak, calls end_turn).
  reason: actions.py is given and its docstring says the combination is 'not wired up yet'; a literal v1 implementation would have vacuous preconditions.

### `round_manager.start_stock_round` (function)

```python
start_stock_round(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 7
- given name (fixed by given code, never rename): YES
- aliases: none
- callers in given code: main.debug_force_round
- callers from graph (calls/triggers): round_manager.end_operating_round

**Exceptions**:

| class | code | when |
|---|---|---|
| RoundError | ERR_GAME_OVER | state.game_over |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. not state.game_over -> `ERR_GAME_OVER`

**Must NOT be checked by this function**:
- no 'already running' check (main.py debug calls it at any time)

**Implements graph node(s)**: `act.start_stock_round`

#### Graph node `act.start_stock_round` (action) - Start a stock round (round 2 onwards, and debug)
Begin a stock round after an operating-round set: refill boxes, reset per-round flags, hand the turn to the Player-1 card holder. NOT used for round 1 (pre-started by setup) but must work at any time (main.py debug endpoint).

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [10.1.2] game not over (game_over False)

**Effects, in order** (execute exactly in this order):
1. [4.1.1] call refill_boxes (start-of-round refill)
2. round_type = STOCK
3. [R15] sale_happened = false; sold_this_round = {}; pass_streak = 0
4. [4.1.2] priority player := sr_order[0] (priority_deal_player_id re-asserted equal to player_order[0]); call begin_turn(sr_order[0])

**Errors listed by the graph node**:
- ERR_GAME_OVER: game_over is set (RoundError)

**Node notes**: No 'already running' precondition: there is no sr_status field and main.py calls this function at arbitrary times (decision GA05).

**Calls it must make / may trigger** (callee api in brackets):
- calls act.refill_boxes -> `bidding.refill_boxes` [CROSS-MODULE] signature: `refill_boxes(state: GameState) -> None` 
- calls act.begin_turn -> `round_manager.begin_turn` [same module] signature: `begin_turn(state: GameState, player_id: str) -> None` 
- triggers act.begin_turn -> `round_manager.begin_turn` [same module] signature: `begin_turn(state: GameState, player_id: str) -> None` 

**State touched**:
- reads `st.game_end` (Game end trigger): First trigger wins (10.1.2). over = game_over (immediate trigger or matured deferred trigger). [type record {trigger in {none, next_or, or_end, or_set_end}, over bool}; unit -; scope game]
- reads `st.sr_order` (Stock-turn order): Order in which players take stock turns; random at setup (1.7.12); recomputed by cash at each stock-round end (4.11.9). Also the direction for 'nearest after' tie-breaks (4.4.2). The player holding card 1 (index 0) is the start player of every stock round. [type list<player>; unit player ids, index 0 = Player 1 card; scope game]
- writes `st.round_type` (Round type): Which kind of round is running. The game is in a stock round from setup (round 1 is pre-started by new_game) until end_stock_round starts the first operating-round set, and so on alternately (1.7.14, 5.1.1). Replaces the v1 sr_status (no field exists for it). [type enum {STOCK, OPERATING}; unit -; scope game]
- writes `st.sale_happened` (A sale happened flag): Set true when a player buys a share, sells a share, converts a concession (R15, R6), or wins a bid-box item at resolution (R6b). Reset at stock-round start. Read by the 10.1.1 first-round nothing-sold test (R6b). Written by the module functions themselves (idempotent; the caller actions.py also sets it after buy and convert). [type bool; unit -; scope stock round]
- writes `st.sold_this_round` (Sold-this-round map): (player, company) pairs such that the player sold >=1 share of the company this stock round; blocks buying that company (4.5.5). Cleared at stock-round start. Stored as lists, not sets (JSON). [type map player -> list<major company> (no duplicates); unit pairs; scope stock round]
- writes `st.pass_streak` (Consecutive passes): Number of consecutive turns that were passes; round ends when it equals the player count (4.11.1). [type int; unit turns; scope stock round]

**Rules constraining this node**:
- 4.1.1: Shift certificates to the lowest boxes then fill from stacks (first SR: 4 minors, 3 concessions, 3 privates). [demanded in preconditions/effects]
- 4.1.2: Round starts with Player 1 and proceeds in order; share transfers only between player and bank/company. [demanded in preconditions/effects]
- R15: Selling and buying shares both set the flag 'a sale happened this stock round'. [demanded in preconditions/effects]
- 10.1.2: Once triggered the game ends at the indicated time. [demanded in preconditions/effects]
- 1.7.14: First round is a stock round.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Game end** [repr.game_end]: maps to: state.game_over: bool and state.end_trigger_pending: None | 'next_or' | 'or_end' | 'or_set_end'
  rule for coder: graph trigger none = (False, None); immediate = game_over True; 'a trigger exists' = game_over or end_trigger_pending is not None. 'next_or': stock-round trigger, converted to 'or_set_end' with set size 1 when the next OR set starts; 'or_end': token on game-end cell in an OR (ends after that OR); 'or_set_end': bank broken in an OR (ends after the set). game_over is set by check_game_end_triggers (immediate) and by end_operating_round (matured).
- **Stock-turn order** [repr.sr_order]: maps to: state.player_order (list, index 0 = Player-1 card) AND state.priority_deal_player_id
  rule for coder: player_count = len(state.player_order) (3..7; no stored field). Invariant: priority_deal_player_id == player_order[0]. Writers of player_order (reorder_players_by_cash, setup) rewrite priority_deal_player_id too; start_stock_round re-asserts it.
- **Round type** [repr.round_type]: maps to: state.round_type: Enum RoundType.STOCK / RoundType.OPERATING (compare with the Enum, not strings); no field for sr_status (dropped)
  rule for coder: STOCK from setup (round 1 is pre-started); OPERATING set by start_operating_round; STOCK again by start_stock_round.
- **'A sale happened' flag** [repr.sale_flag]: maps to: state.any_sale_this_stock_round (bool)
  rule for coder: Set True by: sell_shares, buy_share, convert_concession (module functions themselves; actions.py also sets it after buy and convert), and resolve_bids when a bid-box item is WON (R6b). Reset to False by start_stock_round. Read by check_game_end_triggers(context='end_of_stock_round').
- **sold_this_round** [repr.sold_this_round]: maps to: state.sold_this_round: dict[player_id, list[company_id]] (lists without duplicates, NOT sets: rooms.serialize_state cannot encode sets)
  rule for coder: Readers: `company_id in state.sold_this_round.get(player_id, ())`. Reset to {} by start_stock_round.
- **Consecutive passes** [repr.pass_streak]: maps to: state.consecutive_passes
  rule for coder: Written ONLY by actions.py (+=1 on pass; =0 after a turn-ending action) and reset by start_stock_round; advance_stock_player must not touch it. Round over when >= len(player_order).
- **Stock round start / priority player** [repr.sr_start_player]: maps to: state.active_player_id = player_order[0] at the start of every stock round
  rule for coder: Round 1: set by setup.new_game (the first stock round is pre-started, start_stock_round is not called). Later rounds: start_stock_round -> begin_turn(player_order[0]). Order of play inside a round: next_player(state, pid) = player_order[(index+1) % n]; bids_this_turn reset by begin_turn.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA04** (gap A.1.4, severity S1, kind graph_fix): setup_game effects now match new_game: boxes are filled by setup and the state is already inside stock round 1 (round_type STOCK, active player = order[0], sr_completed 0). start_stock_round is for rounds >= 2 and debug.
  reason: setup.py is given.
- **GA05** (gap A.1.5, severity S2, kind graph_fix): st.sr_status is dropped; st.round_type (STOCK/OPERATING) replaces it. start_stock_round raises only ERR_GAME_OVER, never 'already running'.
  reason: main.py calls start_stock_round at arbitrary times.
- **GB18** (gap B-18, severity S3, kind decision): See GA05.
  reason: GA05.
- **DN15** (gap new, severity S3, kind decision): After game_over actions.apply_action refuses all actions; round managers raise ERR_GAME_OVER in start_stock_round / start_operating_round / end_stock_round.
  reason: 10.1.2.
- **GA07** (gap A.1.7, severity S2, kind graph_fix): sell_shares, buy_share and convert_concession all set the flag themselves (idempotent); actions.py's extra write after buy/convert is documented as redundant; resolve_bids sets it when an item is won (R6b).
  reason: makes direct calls of module functions consistent; R15.

### `round_manager.advance_stock_player` (function)

```python
advance_stock_player(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: None
- layer: 7
- given name (fixed by given code, never rename): YES
- **aliases that MUST also be exported** (same object / same behaviour): `end_turn`
- callers in given code: actions._apply_bid, actions._apply_buy_share, actions._apply_sell_shares, actions._apply_convert_concession, actions._apply_pass
- callers from graph (calls/triggers): none

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- raises nothing; does not touch consecutive_passes; does not check must_sell

**Implements graph node(s)**: `act.end_turn`

#### Graph node `act.end_turn` (action) - End a stock turn (advance_stock_player)
Hand the stock turn to the next player after a turn-ending action or a non-final pass. Used for BOTH 'end turn' and 'pass (not last)'. It does not touch pass_streak (written by actions.py only).

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.1.2] a turn-ending action or a non-final pass just happened (guaranteed by the caller actions.py; NOT re-checked)

**Effects, in order** (execute exactly in this order):
1. [4.1.2] call begin_turn(next_player(turn.active_player))
2. pass_streak is NOT written here (stock_turn_action resets it, pass_turn increments it)

**Errors listed by the graph node**:
- NONE for legal input (raises nothing)

**Node notes**: v1 preconditions turn.acted / not must_sell / ERR_NO_ACTION_TAKEN / ERR_MUST_SELL dropped: unenforceable under the skeleton turn model (decision GA01, GA02).

**Calls it must make / may trigger** (callee api in brackets):
- calls act.begin_turn -> `round_manager.begin_turn` [same module] signature: `begin_turn(state: GameState, player_id: str) -> None` 
- calls drv.next_player -> `round_manager.next_player` [same module] signature: `next_player(state: GameState, player_id: str) -> str` 
- triggers act.begin_turn -> `round_manager.begin_turn` [same module] signature: `begin_turn(state: GameState, player_id: str) -> None` 

**State touched**:
- reads `st.turn` (Active turn record): Whose stock turn it is and how many bids were already placed/moved in this turn. v2 follows the skeleton turn model: EVERY successful sell / buy / convert / bid action ends the turn; there is no stage, no c_used, no acted. bids_made is incremented by the CALLER (actions.py), never by the bidding module, and reset by begin_turn. [type record {active_player, bids_made}; unit -; scope game]
- reads `st.sr_order` (Stock-turn order): Order in which players take stock turns; random at setup (1.7.12); recomputed by cash at each stock-round end (4.11.9). Also the direction for 'nearest after' tie-breaks (4.4.2). The player holding card 1 (index 0) is the start player of every stock round. [type list<player>; unit player ids, index 0 = Player 1 card; scope game]

**Rules constraining this node**:
- 4.1.2: Round starts with Player 1 and proceeds in order; share transfers only between player and bank/company. [demanded in preconditions/effects]
- 4.1.3: Sell, then repay loans, then one of buy/convert/bid; may pass.
- 4.4.7: A player over the limit must sell what they can at the first opportunity.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Stock round start / priority player** [repr.sr_start_player]: maps to: state.active_player_id = player_order[0] at the start of every stock round
  rule for coder: Round 1: set by setup.new_game (the first stock round is pre-started, start_stock_round is not called). Later rounds: start_stock_round -> begin_turn(player_order[0]). Order of play inside a round: next_player(state, pid) = player_order[(index+1) % n]; bids_this_turn reset by begin_turn.
- **Turn record** [repr.turn_record]: maps to: state.active_player_id (turn.active_player) and state.bids_this_turn (turn.bids_made); NO fields for stage / c_used / acted (dropped in v2)
  rule for coder: SKELETON TURN MODEL: every successful sell_shares / buy_share / convert_concession / bid action ends the turn (actions.py calls advance_stock_player). bids_this_turn is incremented by actions.py after each place_or_move_bid and reset by begin_turn; the bidding module only READS it.
- **Stock-turn order** [repr.sr_order]: maps to: state.player_order (list, index 0 = Player-1 card) AND state.priority_deal_player_id
  rule for coder: player_count = len(state.player_order) (3..7; no stored field). Invariant: priority_deal_player_id == player_order[0]. Writers of player_order (reorder_players_by_cash, setup) rewrite priority_deal_player_id too; start_stock_round re-asserts it.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA01** (gap A.1.1, severity S1, kind graph_fix): Follow the skeleton: every successful sell / buy / convert / bid action ends the turn. turn.stage, turn.c_used, turn.acted and the errors ERR_WRONG_STAGE / ERR_C_ALREADY_USED / ERR_NO_ACTION_TAKEN are removed; the order edges sell->repay->C are removed; repay_loans stays as an unwired action (wired=false, implemented and exported); a new given action stock_turn_action models actions.py (calls ONE module function, increments bids_this_turn, resets pass_streak, calls end_turn).
  reason: actions.py is given and its docstring says the combination is 'not wired up yet'; a literal v1 implementation would have vacuous preconditions.
- **GA02** (gap A.1.2, severity S1, kind decision): A pass is NOT blocked when must_sell is true (actions.py increments the pass counter before any module code runs); R10 is enforced only for buy_share, convert_concession and bids. end_turn/advance_stock_player and begin_turn have no must_sell check.  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: Not enforceable inside the new modules without editing actions.py. Suggested owner change: reject 'pass' in actions._apply_pass when certificates.must_sell(state, player_id).
- **GB23** (gap B-23, severity S3, kind graph_fix): Explicit in act.end_turn effects.
  reason: GA01.

### `round_manager.end_stock_round` (function)

```python
end_stock_round(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 7
- given name (fixed by given code, never rename): YES
- aliases: none
- callers in given code: actions._apply_pass
- callers from graph (calls/triggers): none
- api notes: Order: phase_before = phase; bidding.resolve_stock_round; stock_rounds_completed += 1; if game_over: stop; else start_operating_round(state, phase_before).

**Exceptions**:

| class | code | when |
|---|---|---|
| RoundError | ERR_GAME_OVER | game_over already set at entry |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. not state.game_over -> `ERR_GAME_OVER`

**Must NOT be checked by this function**:
- NO sr_over check (the caller actions._apply_pass verified it; tests may call directly)
- no round_type check

**Implements graph node(s)**: `act.end_stock_round`

#### Graph node `act.end_stock_round` (action) - End the stock round: resolve, count, start the operating-round set
Called by pass_turn when every player passed in a row. Resolves the round, counts it, and starts the operating-round set unless the game ended immediately.

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.11.1] called by pass_turn after sr_over (4.11.1); NOT re-checked here: the round manager decides when (decision GA37)

**Effects, in order** (execute exactly in this order):
1. let phase_before = phase (needed by the 2.1.2 deferral)
2. [4.11.1] call resolve_stock_round (steps 1..9)
3. sr_completed += 1 (AFTER resolution so that step 9 saw sr_completed = 0 in the first round)
4. [10.1.1] if game_over was set by the immediate trigger: STOP (no operating round starts)
5. [5.1.1] otherwise call start_operating_round(phase_before)

**Errors listed by the graph node**:
- ERR_GAME_OVER: game_over already set at entry (RoundError)

**Calls it must make / may trigger** (callee api in brackets):
- calls act.resolve_stock_round -> `bidding.resolve_stock_round` [CROSS-MODULE] signature: `resolve_stock_round(state: GameState) -> None` 
- calls act.start_operating_round -> `round_manager.start_operating_round` [same module] signature: `start_operating_round(state: GameState, phase_before: int | None = None) -> None` 
- triggers act.resolve_stock_round -> `bidding.resolve_stock_round` [CROSS-MODULE] signature: `resolve_stock_round(state: GameState) -> None` 
- triggers act.start_operating_round -> `round_manager.start_operating_round` [same module] signature: `start_operating_round(state: GameState, phase_before: int | None = None) -> None` 

**State touched**:
- reads `st.game_end` (Game end trigger): First trigger wins (10.1.2). over = game_over (immediate trigger or matured deferred trigger). [type record {trigger in {none, next_or, or_end, or_set_end}, over bool}; unit -; scope game]
- reads `st.phase` (Game phase): Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1). [type int 1..7; unit phase number; scope game]
- writes `st.sr_completed` (Stock rounds completed): Number of stock rounds that have finished their resolution (0 during the first stock round). Written ONLY by end_stock_round, after resolve_stock_round returned; so the 10.1.1 'first stock round' test is sr_completed == 0 inside resolution step 9. [type int; unit rounds; scope game]

**Rules constraining this node**:
- 5.1.1: One OR after each stock round; once the first 2-train is bought, after the NEXT stock round two ORs. [demanded in preconditions/effects]
- 10.1.1: Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. [demanded in preconditions/effects]
- 4.11.1: All players pass consecutively -> stock round over. [demanded in preconditions/effects]
- 2.1.2: Immediate, except two ORs per SR starts after the following SR.
- R6b: In 10.1.1 'nothing sold in the first stock round' means: no share bought or sold, no concession converted, AND no bid-box item won at resolution. A round with only unsuccessful bids (nobody could pay, R8) counts as nothing sold; a round in which at least one bid wins an item counts as something sold. PROVISIONAL ruling (adopted by the task owner), replaces the provisional tail of R6.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Game end** [repr.game_end]: maps to: state.game_over: bool and state.end_trigger_pending: None | 'next_or' | 'or_end' | 'or_set_end'
  rule for coder: graph trigger none = (False, None); immediate = game_over True; 'a trigger exists' = game_over or end_trigger_pending is not None. 'next_or': stock-round trigger, converted to 'or_set_end' with set size 1 when the next OR set starts; 'or_end': token on game-end cell in an OR (ends after that OR); 'or_set_end': bank broken in an OR (ends after the set). game_over is set by check_game_end_triggers (immediate) and by end_operating_round (matured).
- **Phase** [repr.phase_state]: maps to: state.phase: int 1..7; limits and rust from app.data.phases.PHASES_BY_NUMBER; trigger table trains.TRAIN_PHASE (module constant)
  rule for coder: phase only increases (2.2.1) and is written only by phase_check (plus debug code in main.py). PHASES_BY_NUMBER[n].trains_rusted gives ONE code per phase; skipped phases are rusted too (loop old+1..new).
- **Stock-round counter** [repr.sr_counter]: maps to: state.stock_rounds_completed (starts 0); state.round_number (starts 1) is NOT maintained by the engine
  rule for coder: sr_completed = stock_rounds_completed; incremented by end_stock_round AFTER resolve_stock_round returned; the 10.1.1 'first stock round' test is stock_rounds_completed == 0 inside step 9.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA37** (gap A.2.37, severity S3, kind decision): resolve_stock_round and end_stock_round do NOT check sr_over or round_type; the round manager (actions._apply_pass) decides when. No ERR_NOT_OVER exists.
  reason: callable whenever the caller invokes it; avoids lazy cross-component import.
- **GB17** (gap B-17, severity S3, kind graph_fix): Now an effect line of act.end_stock_round.
  reason: 10.1.1.
- **DN01** (gap new, severity S2, kind decision): The set after a stock round has ors_per_sr[phase_before] rounds, phase_before = phase at the start of that stock round's resolution (a local value of end_stock_round); next_or forces 1. A phase 2 that starts during resolution (export) therefore gives 1 OR after that stock round and 2 after the next; a phase 2 that starts in an operating round gives 2 after the next stock round. No new field is needed.
  reason: 'applies after the following stock round' (2.1.2, 5.1.1, 2.2.3).
- **GA42** (gap A.2.42, severity S3, kind repr): st.sr_completed = stock_rounds_completed (0 during round 1); round_number untouched by the engine.
  reason: the model default is never described.
- **GB02** (gap B-2, severity S3, kind graph_fix): State renamed st.sr_completed (rounds completed); incremented by end_stock_round after resolution.
  reason: GA42.

### `round_manager.active_company_id` (function)

```python
active_company_id(state: GameState) -> str | None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: None unless round_type is OPERATING and 0 <= current_company_index < len(operating_order)
- layer: 7
- given name (fixed by given code, never rename): YES
- **aliases that MUST also be exported** (same object / same behaviour): `active_company`
- callers in given code: actions._apply_operate, actions._apply_pass
- callers from graph (calls/triggers): round_manager.advance_company

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.active_company`

#### Graph node `drv.active_company` (derived) - Active company
The company whose operating turn it is.

- graph signature (abstract): params = ['none']; returns = company|null

**Formula**: [5.2.2] or_order[or_current] if round_type = OPERATING and 0 <= or_current < len(or_order) else none

**State touched**:
- reads `st.round_type` (Round type): Which kind of round is running. The game is in a stock round from setup (round 1 is pre-started by new_game) until end_stock_round starts the first operating-round set, and so on alternately (1.7.14, 5.1.1). Replaces the v1 sr_status (no field exists for it). [type enum {STOCK, OPERATING}; unit -; scope game]
- reads `st.or_order` (Operating order so far): Companies already chosen to run in the current operating round, in running order; the next company is chosen only after the previous one finished (5.2.2) (models.operating_order). [type list<company>; unit companies; scope game]
- reads `st.or_current` (Current company index): Index into or_order of the company whose turn it is (models.current_company_index). active_company = or_order[or_current]. [type int; unit index; scope game]

**Rules constraining this node**:
- 5.2.2: Same cell: top first; same value different cells: right first; next company decided after the previous finishes. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Round type** [repr.round_type]: maps to: state.round_type: Enum RoundType.STOCK / RoundType.OPERATING (compare with the Enum, not strings); no field for sr_status (dropped)
  rule for coder: STOCK from setup (round 1 is pre-started); OPERATING set by start_operating_round; STOCK again by start_stock_round.
- **Operating-round bookkeeping** [repr.operating_round_state]: maps to: state.operating_rounds_this_set (set size, locked at set start; default 1), state.operating_round_index (0-based), state.operating_order (companies chosen so far), state.current_company_index
  rule for coder: active_company_id = operating_order[current_company_index] if round_type is OPERATING and the index is in range. The 2.1.2 deferral needs NO extra field: start_operating_round receives phase_before (a local value from end_stock_round) and the set size is ors_per_sr[phase_before], locked in operating_rounds_this_set.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA08** (gap A.1.8, severity S2, kind graph_fix): In scope now: active_company_id, advance_company, start/begin/end of operating rounds, set size lock, game_over maturity, has_completed_or writer (advance_company), start-of-OR revenues. States or_set_size, or_index, or_order, or_current, round_type added; phase_events is an audit log only.
  reason: required by actions.py/main.py; without a writer of has_operated no share could ever be sold.
- **GA05** (gap A.1.5, severity S2, kind graph_fix): st.sr_status is dropped; st.round_type (STOCK/OPERATING) replaces it. start_stock_round raises only ERR_GAME_OVER, never 'already running'.
  reason: main.py calls start_stock_round at arbitrary times.

### `round_manager.advance_company` (function)

```python
advance_company(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 7
- given name (fixed by given code, never rename): YES
- aliases: none
- callers in given code: actions._apply_operate, actions._apply_pass
- callers from graph (calls/triggers): none
- api notes: Sets has_operated True for a major that finished its turn.

**Exceptions**:

| class | code | when |
|---|---|---|
| RoundError | ERR_NO_ACTIVE_COMPANY | no company is active |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. active_company_id(state) is not None -> `ERR_NO_ACTIVE_COMPANY`

**Implements graph node(s)**: `act.advance_company`

#### Graph node `act.advance_company` (action) - Finish a company's turn and choose the next company
Called after a company's operate action or its director's pass. The next company is chosen only now (sales or price moves during the turn may reorder, 5.2.2).

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [5.2.2] a company is active: round_type = OPERATING and 0 <= or_current < len(or_order)

**Effects, in order** (execute exactly in this order):
1. [4.4.2] if the finished company is a major: has_completed_or[c] = true
2. [5.2.2] done = or_order[0..or_current]; nxt = next_operating_company(done)
3. if nxt exists: or_order = or_order[0..or_current] + [nxt]; or_current += 1; else call end_operating_round

**Errors listed by the graph node**:
- ERR_NO_ACTIVE_COMPANY: nothing is operating (RoundError)

**Calls it must make / may trigger** (callee api in brackets):
- calls act.end_operating_round -> `round_manager.end_operating_round` [same module] signature: `end_operating_round(state: GameState) -> None` 
- calls drv.next_operating_company -> `turn_order.next_operating_company` [CROSS-MODULE] signature: `next_operating_company(state: GameState, done: Iterable[str] = ()) -> str | None` 
- calls drv.active_company -> `round_manager.active_company_id` [same module] signature: `active_company_id(state: GameState) -> str | None` 
- triggers act.end_operating_round -> `round_manager.end_operating_round` [same module] signature: `end_operating_round(state: GameState) -> None` 

**State touched**:
- reads `st.round_type` (Round type): Which kind of round is running. The game is in a stock round from setup (round 1 is pre-started by new_game) until end_stock_round starts the first operating-round set, and so on alternately (1.7.14, 5.1.1). Replaces the v1 sr_status (no field exists for it). [type enum {STOCK, OPERATING}; unit -; scope game]
- reads `st.or_order` (Operating order so far): Companies already chosen to run in the current operating round, in running order; the next company is chosen only after the previous one finished (5.2.2) (models.operating_order). [type list<company>; unit companies; scope game]
- reads `st.or_current` (Current company index): Index into or_order of the company whose turn it is (models.current_company_index). active_company = or_order[or_current]. [type int; unit index; scope game]
- writes `st.has_completed_or` (Has completed an operating round): True once the major company has completed one operating turn; shares cannot be sold before (4.4.2). Initial false at flotation (set false by convert_concession), set true by advance_company when the company finished its turn. [type map major->bool; unit -; scope per major company]
- writes `st.or_order` (Operating order so far): Companies already chosen to run in the current operating round, in running order; the next company is chosen only after the previous one finished (5.2.2) (models.operating_order). [type list<company>; unit companies; scope game]
- writes `st.or_current` (Current company index): Index into or_order of the company whose turn it is (models.current_company_index). active_company = or_order[or_current]. [type int; unit index; scope game]

**Rules constraining this node**:
- 5.2.2: Same cell: top first; same value different cells: right first; next company decided after the previous finishes. [demanded in preconditions/effects]
- 4.4.2: Not before company completed an OR; pool <= 50%; director's certificate cannot go into the pool; succession exchange precedes the rest of the sale. [demanded in preconditions/effects]
- 5.2.1: A: privates/concessions pay; B: minors in descending price order; C: majors in descending price order.
- 5.3.1: Decisions for a company are made by its director; step H buys trains; only housekeeping and step H are in scope here (rest is given operating code).

**Representation notes (repr nodes bound to touched states / this node)**:
- **Round type** [repr.round_type]: maps to: state.round_type: Enum RoundType.STOCK / RoundType.OPERATING (compare with the Enum, not strings); no field for sr_status (dropped)
  rule for coder: STOCK from setup (round 1 is pre-started); OPERATING set by start_operating_round; STOCK again by start_stock_round.
- **Operating-round bookkeeping** [repr.operating_round_state]: maps to: state.operating_rounds_this_set (set size, locked at set start; default 1), state.operating_round_index (0-based), state.operating_order (companies chosen so far), state.current_company_index
  rule for coder: active_company_id = operating_order[current_company_index] if round_type is OPERATING and the index is in range. The 2.1.2 deferral needs NO extra field: start_operating_round receives phase_before (a local value from end_stock_round) and the set size is ors_per_sr[phase_before], locked in operating_rounds_this_set.
- **Company status mirrors** [repr.company_status]: maps to: MajorCompanyState.floated / concession_converted / has_operated / share_price; MinorCompanyState.floated / share_price / removed / acquired_by_major
  rule for coder: floated=True and concession_converted=True on conversion; has_operated False at flotation, True after the first completed operating turn (advance_company); share_price is a display mirror nobody reads (read prices from the grid via current_price).


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA08** (gap A.1.8, severity S2, kind graph_fix): In scope now: active_company_id, advance_company, start/begin/end of operating rounds, set size lock, game_over maturity, has_completed_or writer (advance_company), start-of-OR revenues. States or_set_size, or_index, or_order, or_current, round_type added; phase_events is an audit log only.
  reason: required by actions.py/main.py; without a writer of has_operated no share could ever be sold.
- **GB06** (gap B-6, severity S2, kind graph_fix): advance_company writes has_completed_or for a major (now a graph effect, state no longer external).
  reason: GA08.
- **GA05** (gap A.1.5, severity S2, kind graph_fix): st.sr_status is dropped; st.round_type (STOCK/OPERATING) replaces it. start_stock_round raises only ERR_GAME_OVER, never 'already running'.
  reason: main.py calls start_stock_round at arbitrary times.

### `round_manager.start_operating_round` (function)

```python
start_operating_round(state: GameState, phase_before: int | None = None) -> None
```

- parameters: ['state', 'phase_before']
- defaults (explicit): {"phase_before": "None"}
- returns: (see signature)
- layer: 7
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): round_manager.end_stock_round
- api notes: phase_before None = current phase (no 2.1.2 deferral).

**Exceptions**:

| class | code | when |
|---|---|---|
| RoundError | ERR_GAME_OVER | state.game_over |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. not state.game_over -> `ERR_GAME_OVER`

**Must NOT be checked by this function**:
- round_type of the caller

**Implements graph node(s)**: `act.start_operating_round`

#### Graph node `act.start_operating_round` (action) - Start an operating-round set
Start the set of operating rounds that follows a stock round: lock the set size, convert a 'next_or' trigger, begin the first operating round.

- graph signature (abstract): params = ['phase_before (phase at the start of the stock-round resolution; default = current phase)']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [10.1.2] game not over

**Effects, in order** (execute exactly in this order):
1. [5.1.1] round_type = OPERATING; or_index = 0
2. [2.1.2, 5.1.1] or_set_size = operating_rounds_for_next_set(phase_before) (LOCKED for the whole set)
3. [10.1.1] if end_trigger = next_or: end_trigger = or_set_end and or_set_size = 1 (game ends after exactly this one OR)
4. call begin_operating_round

**Errors listed by the graph node**:
- ERR_GAME_OVER (RoundError)

**Order edges**:
- `act.resolve_stock_round` runs before `act.start_operating_round` (seq 1; end_sr: seq 1 runs before seq 2)

**Calls it must make / may trigger** (callee api in brackets):
- calls act.begin_operating_round -> `round_manager.begin_operating_round` [same module] signature: `begin_operating_round(state: GameState) -> None` 
- calls drv.operating_rounds_for_next_set -> `round_manager.operating_rounds_for_next_set` [same module] signature: `operating_rounds_for_next_set(state: GameState, phase_before: int | None = None) -> int` 
- triggers act.begin_operating_round -> `round_manager.begin_operating_round` [same module] signature: `begin_operating_round(state: GameState) -> None` 

**State touched**:
- reads `st.game_end` (Game end trigger): First trigger wins (10.1.2). over = game_over (immediate trigger or matured deferred trigger). [type record {trigger in {none, next_or, or_end, or_set_end}, over bool}; unit -; scope game]
- reads `st.phase` (Game phase): Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1). [type int 1..7; unit phase number; scope game]
- writes `st.round_type` (Round type): Which kind of round is running. The game is in a stock round from setup (round 1 is pre-started by new_game) until end_stock_round starts the first operating-round set, and so on alternately (1.7.14, 5.1.1). Replaces the v1 sr_status (no field exists for it). [type enum {STOCK, OPERATING}; unit -; scope game]
- writes `st.or_index` (Index of the running operating round): Which operating round of the set is running (models.operating_round_index). [type int 0-based; unit rounds; scope game]
- writes `st.or_set_size` (Operating rounds in the current set): Number of operating rounds in the set following the stock round; LOCKED when the set starts (models.operating_rounds_this_set; 2.1.2, 5.1.1); forced to 1 by a 'next_or' trigger (10.1.1). [type int 1..2; unit rounds; scope game]
- writes `st.game_end` (Game end trigger): First trigger wins (10.1.2). over = game_over (immediate trigger or matured deferred trigger). [type record {trigger in {none, next_or, or_end, or_set_end}, over bool}; unit -; scope game]

**Rules constraining this node**:
- 5.1.1: One OR after each stock round; once the first 2-train is bought, after the NEXT stock round two ORs. [demanded in preconditions/effects]
- 2.1.2: Immediate, except two ORs per SR starts after the following SR. [demanded in preconditions/effects]
- 10.1.1: Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. [demanded in preconditions/effects]
- 10.1.2: Once triggered the game ends at the indicated time. [demanded in preconditions/effects]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Game end** [repr.game_end]: maps to: state.game_over: bool and state.end_trigger_pending: None | 'next_or' | 'or_end' | 'or_set_end'
  rule for coder: graph trigger none = (False, None); immediate = game_over True; 'a trigger exists' = game_over or end_trigger_pending is not None. 'next_or': stock-round trigger, converted to 'or_set_end' with set size 1 when the next OR set starts; 'or_end': token on game-end cell in an OR (ends after that OR); 'or_set_end': bank broken in an OR (ends after the set). game_over is set by check_game_end_triggers (immediate) and by end_operating_round (matured).
- **Phase** [repr.phase_state]: maps to: state.phase: int 1..7; limits and rust from app.data.phases.PHASES_BY_NUMBER; trigger table trains.TRAIN_PHASE (module constant)
  rule for coder: phase only increases (2.2.1) and is written only by phase_check (plus debug code in main.py). PHASES_BY_NUMBER[n].trains_rusted gives ONE code per phase; skipped phases are rusted too (loop old+1..new).
- **Round type** [repr.round_type]: maps to: state.round_type: Enum RoundType.STOCK / RoundType.OPERATING (compare with the Enum, not strings); no field for sr_status (dropped)
  rule for coder: STOCK from setup (round 1 is pre-started); OPERATING set by start_operating_round; STOCK again by start_stock_round.
- **Operating-round bookkeeping** [repr.operating_round_state]: maps to: state.operating_rounds_this_set (set size, locked at set start; default 1), state.operating_round_index (0-based), state.operating_order (companies chosen so far), state.current_company_index
  rule for coder: active_company_id = operating_order[current_company_index] if round_type is OPERATING and the index is in range. The 2.1.2 deferral needs NO extra field: start_operating_round receives phase_before (a local value from end_stock_round) and the set size is ors_per_sr[phase_before], locked in operating_rounds_this_set.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA08** (gap A.1.8, severity S2, kind graph_fix): In scope now: active_company_id, advance_company, start/begin/end of operating rounds, set size lock, game_over maturity, has_completed_or writer (advance_company), start-of-OR revenues. States or_set_size, or_index, or_order, or_current, round_type added; phase_events is an audit log only.
  reason: required by actions.py/main.py; without a writer of has_operated no share could ever be sold.
- **GB15** (gap B-15, severity S1, kind graph_fix): Now explicit actions start_operating_round / begin_operating_round / advance_company / end_operating_round with the 2.1.2 deferral via phase_before.
  reason: GA08.
- **GA05** (gap A.1.5, severity S2, kind graph_fix): st.sr_status is dropped; st.round_type (STOCK/OPERATING) replaces it. start_stock_round raises only ERR_GAME_OVER, never 'already running'.
  reason: main.py calls start_stock_round at arbitrary times.

### `round_manager.begin_operating_round` (function)

```python
begin_operating_round(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 7
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `start_operating_set_round`
- callers in given code: none
- callers from graph (calls/triggers): round_manager.end_operating_round, round_manager.start_operating_round

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- raises nothing

**Implements graph node(s)**: `act.begin_operating_round`

#### Graph node `act.begin_operating_round` (action) - Begin one operating round
Step A of 5.2.1 (private and concession revenue), then choose the first company; if nobody can run, the round ends at once.

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [5.2.1] none beyond being inside an operating-round set

**Effects, in order** (execute exactly in this order):
1. [5.2.1 A, 3.1.2] call pay_private_revenues
2. [5.2.1 A, 3.4.4] call pay_concession_dividends
3. or_order = []; or_current = 0
4. [5.2.1 B/C, 5.2.2] first = next_operating_company(done = {}); if none: call end_operating_round; else or_order = [first]

**Errors listed by the graph node**:
- NONE (raises nothing)

**Calls it must make / may trigger** (callee api in brackets):
- calls act.pay_private_revenues -> `scoring.pay_private_revenues` [CROSS-MODULE] signature: `pay_private_revenues(state: GameState) -> None` 
- calls act.pay_concession_dividends -> `scoring.pay_concession_dividends` [CROSS-MODULE] signature: `pay_concession_dividends(state: GameState) -> None` 
- calls act.end_operating_round -> `round_manager.end_operating_round` [same module] signature: `end_operating_round(state: GameState) -> None` 
- calls drv.next_operating_company -> `turn_order.next_operating_company` [CROSS-MODULE] signature: `next_operating_company(state: GameState, done: Iterable[str] = ()) -> str | None` 
- triggers act.pay_private_revenues -> `scoring.pay_private_revenues` [CROSS-MODULE] signature: `pay_private_revenues(state: GameState) -> None` 
- triggers act.pay_concession_dividends -> `scoring.pay_concession_dividends` [CROSS-MODULE] signature: `pay_concession_dividends(state: GameState) -> None` 
- triggers act.end_operating_round -> `round_manager.end_operating_round` [same module] signature: `end_operating_round(state: GameState) -> None` 

**State touched**:
- writes `st.or_order` (Operating order so far): Companies already chosen to run in the current operating round, in running order; the next company is chosen only after the previous one finished (5.2.2) (models.operating_order). [type list<company>; unit companies; scope game]
- writes `st.or_current` (Current company index): Index into or_order of the company whose turn it is (models.current_company_index). active_company = or_order[or_current]. [type int; unit index; scope game]

**Rules constraining this node**:
- 5.2.1: A: privates/concessions pay; B: minors in descending price order; C: majors in descending price order. [demanded in preconditions/effects]
- 3.1.2: While open, a private pays its fixed revenue (maybe 0) to its owner at the start of each operating round. [demanded in preconditions/effects]
- 3.4.4: Each concession pays 10 per OR to its owner. [demanded in preconditions/effects]
- 5.2.2: Same cell: top first; same value different cells: right first; next company decided after the previous finishes. [demanded in preconditions/effects]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Operating-round bookkeeping** [repr.operating_round_state]: maps to: state.operating_rounds_this_set (set size, locked at set start; default 1), state.operating_round_index (0-based), state.operating_order (companies chosen so far), state.current_company_index
  rule for coder: active_company_id = operating_order[current_company_index] if round_type is OPERATING and the index is in range. The 2.1.2 deferral needs NO extra field: start_operating_round receives phase_before (a local value from end_stock_round) and the set size is ors_per_sr[phase_before], locked in operating_rounds_this_set.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA08** (gap A.1.8, severity S2, kind graph_fix): In scope now: active_company_id, advance_company, start/begin/end of operating rounds, set size lock, game_over maturity, has_completed_or writer (advance_company), start-of-OR revenues. States or_set_size, or_index, or_order, or_current, round_type added; phase_events is an audit log only.
  reason: required by actions.py/main.py; without a writer of has_operated no share could ever be sold.
- **GB15** (gap B-15, severity S1, kind graph_fix): Now explicit actions start_operating_round / begin_operating_round / advance_company / end_operating_round with the 2.1.2 deferral via phase_before.
  reason: GA08.
- **DN09** (gap new, severity S3, kind decision): begin_operating_round still pays step A, then ends immediately; the set continues.
  reason: 5.2.1 step A applies at the start of EACH OR.
- **DN12** (gap new, severity S3, kind decision): Privates pay before concessions (both step A); the order is irrelevant for money, only the bank-broken latch could differ.
  reason: 5.2.1 A.

### `round_manager.end_operating_round` (function)

```python
end_operating_round(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 7
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): round_manager.advance_company, round_manager.begin_operating_round

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- raises nothing

**Implements graph node(s)**: `act.end_operating_round`

#### Graph node `act.end_operating_round` (action) - End an operating round
Decide what follows an operating round: game end (matured trigger), the next operating round of the set, or the next stock round.

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [5.2.1] none beyond being inside an operating round

**Effects, in order** (execute exactly in this order):
1. [10.1.1] if end_trigger = or_end (token reached the game-end cell in an OR) or next_or: game_over = true; stop
2. or_index += 1; if or_index < or_set_size: call begin_operating_round; stop
3. [10.1.1] the set is complete: if end_trigger = or_set_end: game_over = true; stop
4. [1.7.14, 5.1.1] otherwise call start_stock_round

**Errors listed by the graph node**:
- NONE (raises nothing)

**Calls it must make / may trigger** (callee api in brackets):
- calls act.begin_operating_round -> `round_manager.begin_operating_round` [same module] signature: `begin_operating_round(state: GameState) -> None` 
- calls act.start_stock_round -> `round_manager.start_stock_round` [same module] signature: `start_stock_round(state: GameState) -> None` 
- triggers act.begin_operating_round -> `round_manager.begin_operating_round` [same module] signature: `begin_operating_round(state: GameState) -> None` 
- triggers act.start_stock_round -> `round_manager.start_stock_round` [same module] signature: `start_stock_round(state: GameState) -> None` 

**State touched**:
- reads `st.game_end` (Game end trigger): First trigger wins (10.1.2). over = game_over (immediate trigger or matured deferred trigger). [type record {trigger in {none, next_or, or_end, or_set_end}, over bool}; unit -; scope game]
- reads `st.or_set_size` (Operating rounds in the current set): Number of operating rounds in the set following the stock round; LOCKED when the set starts (models.operating_rounds_this_set; 2.1.2, 5.1.1); forced to 1 by a 'next_or' trigger (10.1.1). [type int 1..2; unit rounds; scope game]
- reads `st.or_index` (Index of the running operating round): Which operating round of the set is running (models.operating_round_index). [type int 0-based; unit rounds; scope game]
- writes `st.game_end` (Game end trigger): First trigger wins (10.1.2). over = game_over (immediate trigger or matured deferred trigger). [type record {trigger in {none, next_or, or_end, or_set_end}, over bool}; unit -; scope game]
- writes `st.or_index` (Index of the running operating round): Which operating round of the set is running (models.operating_round_index). [type int 0-based; unit rounds; scope game]

**Rules constraining this node**:
- 5.2.1: A: privates/concessions pay; B: minors in descending price order; C: majors in descending price order. [demanded in preconditions/effects]
- 5.1.1: One OR after each stock round; once the first 2-train is bought, after the NEXT stock round two ORs. [demanded in preconditions/effects]
- 1.7.14: First round is a stock round. [demanded in preconditions/effects]
- 10.1.1: Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. [demanded in preconditions/effects]
- 10.1.2: Once triggered the game ends at the indicated time.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Game end** [repr.game_end]: maps to: state.game_over: bool and state.end_trigger_pending: None | 'next_or' | 'or_end' | 'or_set_end'
  rule for coder: graph trigger none = (False, None); immediate = game_over True; 'a trigger exists' = game_over or end_trigger_pending is not None. 'next_or': stock-round trigger, converted to 'or_set_end' with set size 1 when the next OR set starts; 'or_end': token on game-end cell in an OR (ends after that OR); 'or_set_end': bank broken in an OR (ends after the set). game_over is set by check_game_end_triggers (immediate) and by end_operating_round (matured).
- **Operating-round bookkeeping** [repr.operating_round_state]: maps to: state.operating_rounds_this_set (set size, locked at set start; default 1), state.operating_round_index (0-based), state.operating_order (companies chosen so far), state.current_company_index
  rule for coder: active_company_id = operating_order[current_company_index] if round_type is OPERATING and the index is in range. The 2.1.2 deferral needs NO extra field: start_operating_round receives phase_before (a local value from end_stock_round) and the set size is ors_per_sr[phase_before], locked in operating_rounds_this_set.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA03** (gap A.1.3, severity S2, kind graph_fix): check_game_end_triggers(state, context=None). The kind of a deferred trigger comes from round_type: STOCK -> 'next_or'; OPERATING -> token on game-end cell 'or_end', bank broken 'or_set_end'. context only matters for 'end_of_stock_round' (nothing-sold test). Maturity (setting game_over) is written by end_operating_round.
  reason: All given callers pass one argument; models.py comments define the three stored values.
- **GA08** (gap A.1.8, severity S2, kind graph_fix): In scope now: active_company_id, advance_company, start/begin/end of operating rounds, set size lock, game_over maturity, has_completed_or writer (advance_company), start-of-OR revenues. States or_set_size, or_index, or_order, or_current, round_type added; phase_events is an audit log only.
  reason: required by actions.py/main.py; without a writer of has_operated no share could ever be sold.
- **GA36** (gap A.2.36, severity S3, kind graph_fix): game_over is set by check_game_end_triggers (immediate) and by end_operating_round (matured or_end / or_set_end / next_or); drv.final_ranking added (ties keep player order).  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: 10.1.x.
- **GB15** (gap B-15, severity S1, kind graph_fix): Now explicit actions start_operating_round / begin_operating_round / advance_company / end_operating_round with the 2.1.2 deferral via phase_before.
  reason: GA08.

### `round_manager.operating_rounds_for_next_set` (function)

```python
operating_rounds_for_next_set(state: GameState, phase_before: int | None = None) -> int
```

- parameters: ['state', 'phase_before']
- defaults (explicit): {"phase_before": "None"}
- returns: 1 or 2 with the 2.1.2 deferral; 1 if end_trigger_pending == 'next_or'
- layer: 7
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): round_manager.start_operating_round

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- raises nothing

**Implements graph node(s)**: `drv.operating_rounds_for_next_set`

#### Graph node `drv.operating_rounds_for_next_set` (derived) - Operating rounds in the next set
Size of the operating-round set after a stock round, with the 2.1.2 deferral.

- graph signature (abstract): params = ['phase_before']; returns = int

**Formula**: [5.1.1, 2.1.2] if end_trigger = next_or: 1 (game ends after exactly one more OR); else const.phase_table.ors_per_sr[phase_before] where phase_before = the phase when the stock round RESOLUTION started (default: current phase). So a phase change during this stock round's resolution (e.g. the first 2-train exported) changes the set size only from the FOLLOWING stock round on; a phase change during an operating round is already in phase_before of the next stock round

**State touched**:
- reads `st.phase` (Game phase): Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1). [type int 1..7; unit phase number; scope game]
- reads `st.game_end` (Game end trigger): First trigger wins (10.1.2). over = game_over (immediate trigger or matured deferred trigger). [type record {trigger in {none, next_or, or_end, or_set_end}, over bool}; unit -; scope game]

**Constants used**:
- `const.phase_table` (Phase table): Phase of the first train of a type: 2-train (bought, or L upgraded) -> 2; 3 -> 3; 4 -> 4; 5 -> 5; 6 -> 6; 7 or E -> 7 (2.2.3-2.2.8). An L-train never starts a phase. Per phase: train limits (minor/major) 1:2/4 2:2/4 3:2/4 4:1/3 5:1/2 6:1/2 7:1/2; operating rounds per stock round 1:1, 2..7:2; rust 3:L 4:2 6:3 7:4; phase 5 removes concessions (R9).; data: `{"table": {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "E": 7}, "train_limits": {"1": [2, 4], "2": [2, 4], "3": [2, 4], "4": [1, 3], "5": [1, 2], "6": [1, 2], "7": [1, 2]}, "ors_per_sr": {"1": 1, "2": 2, "3": 2, "4": 2, "5": 2, "6": 2, "7": 2}}`
  (in code: app.data.phases.PHASES_BY_NUMBER; trains.TRAIN_PHASE (L absent))

**Rules constraining this node**:
- 5.1.1: One OR after each stock round; once the first 2-train is bought, after the NEXT stock round two ORs. [formula]
- 2.1.2: Immediate, except two ORs per SR starts after the following SR. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Phase** [repr.phase_state]: maps to: state.phase: int 1..7; limits and rust from app.data.phases.PHASES_BY_NUMBER; trigger table trains.TRAIN_PHASE (module constant)
  rule for coder: phase only increases (2.2.1) and is written only by phase_check (plus debug code in main.py). PHASES_BY_NUMBER[n].trains_rusted gives ONE code per phase; skipped phases are rusted too (loop old+1..new).
- **Game end** [repr.game_end]: maps to: state.game_over: bool and state.end_trigger_pending: None | 'next_or' | 'or_end' | 'or_set_end'
  rule for coder: graph trigger none = (False, None); immediate = game_over True; 'a trigger exists' = game_over or end_trigger_pending is not None. 'next_or': stock-round trigger, converted to 'or_set_end' with set size 1 when the next OR set starts; 'or_end': token on game-end cell in an OR (ends after that OR); 'or_set_end': bank broken in an OR (ends after the set). game_over is set by check_game_end_triggers (immediate) and by end_operating_round (matured).


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA26** (gap A.2.26, severity S2, kind graph_fix): (a) concession clearing only when old < 5 <= new; (b) rust events of every skipped phase old+1..new are applied; (c) the 2.1.2 deferral is handled by operating_rounds_for_next_set with phase_before; (d) phase_events is an audit log, rust/discard/limits are applied immediately.
  reason: rules 2.1.2-2.1.5, 2.2.1.
- **DN01** (gap new, severity S2, kind decision): The set after a stock round has ors_per_sr[phase_before] rounds, phase_before = phase at the start of that stock round's resolution (a local value of end_stock_round); next_or forces 1. A phase 2 that starts during resolution (export) therefore gives 1 OR after that stock round and 2 after the next; a phase 2 that starts in an operating round gives 2 after the next stock round. No new field is needed.
  reason: 'applies after the following stock round' (2.1.2, 5.1.1, 2.2.3).

## 4. Rules this module is responsible for (id + text, verbatim from the graph)

- **1.7.14** (rule): First round is a stock round. -- constrains `act.start_stock_round`, `act.end_operating_round`
- **10.1.1** (rule): Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. -- constrains `act.end_stock_round`, `act.start_operating_round`, `act.end_operating_round`
- **10.1.2** (rule): Once triggered the game ends at the indicated time. -- constrains `act.start_stock_round`, `act.start_operating_round`, `act.end_operating_round`
- **2.1.2** (rule): Immediate, except two ORs per SR starts after the following SR. -- constrains `act.end_stock_round`, `act.start_operating_round`, `drv.operating_rounds_for_next_set`
- **3.1.2** (rule): While open, a private pays its fixed revenue (maybe 0) to its owner at the start of each operating round. -- constrains `act.begin_operating_round`
- **3.4.4** (rule): Each concession pays 10 per OR to its owner. -- constrains `act.begin_operating_round`
- **4.1.1** (rule): Shift certificates to the lowest boxes then fill from stacks (first SR: 4 minors, 3 concessions, 3 privates). -- constrains `act.start_stock_round`
- **4.1.2** (rule): Round starts with Player 1 and proceeds in order; share transfers only between player and bank/company. -- constrains `drv.next_player`, `act.begin_turn`, `act.start_stock_round`, `act.end_turn`
- **4.1.3** (rule): Sell, then repay loans, then one of buy/convert/bid; may pass. -- constrains `act.begin_turn`, `act.end_turn`
- **4.1.4** (rule): One of: buy one share, convert, place/increase up to 3 bids; round ends when all pass consecutively. -- constrains `drv.sr_over`
- **4.11.1** (rule): All players pass consecutively -> stock round over. -- constrains `drv.sr_over`, `act.end_stock_round`
- **4.4.2** (rule): Not before company completed an OR; pool <= 50%; director's certificate cannot go into the pool; succession exchange precedes the rest of the sale. -- constrains `act.advance_company`
- **4.4.7** (rule): A player over the limit must sell what they can at the first opportunity. -- constrains `act.end_turn`
- **5.1.1** (rule): One OR after each stock round; once the first 2-train is bought, after the NEXT stock round two ORs. -- constrains `act.end_stock_round`, `act.start_operating_round`, `act.end_operating_round`, `drv.operating_rounds_for_next_set`
- **5.2.1** (rule): A: privates/concessions pay; B: minors in descending price order; C: majors in descending price order. -- constrains `act.advance_company`, `act.begin_operating_round`, `act.end_operating_round`
- **5.2.2** (rule): Same cell: top first; same value different cells: right first; next company decided after the previous finishes. -- constrains `drv.active_company`, `act.advance_company`, `act.begin_operating_round`
- **5.3.1** (rule): Decisions for a company are made by its director; step H buys trains; only housekeeping and step H are in scope here (rest is given operating code). -- constrains `act.advance_company`
- **R15** (ruling): Selling and buying shares both set the flag 'a sale happened this stock round'. -- constrains `act.start_stock_round`
- **R6b** (ruling): In 10.1.1 'nothing sold in the first stock round' means: no share bought or sold, no concession converted, AND no bid-box item won at resolution. A round with only unsuccessful bids (nobody could pay, R8) counts as nothing sold; a round in which at least one bid wins an item counts as something sold. PROVISIONAL ruling (adopted by the task owner), replaces the provisional tail of R6. -- constrains `act.end_stock_round`

