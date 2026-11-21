# Contract: `backend/app/engine/trains.py`

Generated mechanically from graph v2 by gen_contracts.py. Read COMMON.md first, then this file; BINDING.md lists the representation rules and the cross-module call matrix.

Import layering: this module is layer 4 (1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares and company_formation, 6 bidding, 7 round_manager). Calls to a HIGHER layer must be lazy imports inside the function body; never import upward at module level.

## 1. Export list (every name below, plus every alias, must exist at module level)

- `TrainError` (exception)
- `TRAIN_PHASE` (constant)
- `TRAIN_GROUPS` (constant)
- `SCAN_ORDER` (constant)
- `EXPORT_L_ONLY` (constant)
- `EXPORT_NEXT_WITH_PHASE` (constant)
- `MAX_E_TRAINS_PER_COMPANY` (constant)
- `phase_of_train` (function)
- `front_train` (function)
- `front_group` (function)  aliases: next_train_group
- `deck_remaining` (function)
- `train_group` (function)
- `train_cost` (function)
- `train_limit` (function)
- `phase_check` (function)  aliases: advance_phase, check_phase
- `rust_trains` (function)  aliases: rust
- `discard_excess_trains` (function)  aliases: enforce_train_limit
- `export_train` (function)
- `buy_train_from_bank` (function)
- `upgrade_l_train` (function)  aliases: upgrade_l_to_2

Public API count: 20

## 2. Module-level obligations

### States this module writes (flags and data it is responsible for)
- `st.phase` (Game phase): Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1). -- written by `act.phase_check`
- `st.phase_events` (Phase-change log): Audit log of phase changes: one line per change with from, to, rusted codes, trains discarded, operating rounds per stock round. NOT a work queue: rust, train-limit discard and concession clearing are applied immediately inside phase_check (2.1.2-2.1.5). -- written by `act.phase_check`
- `st.company_trains` (Company trains): Trains owned by each minor and major company; the code records the orientation chosen at purchase (L or 2; 7 or E). Rusted trains vanish (2.1.3); excess trains go to bank_pool_trains (2.1.4). -- written by `act.rust_trains`, `act.discard_excess_trains`, `act.buy_train`, `act.upgrade_l_train`
- `st.bank_pool_trains` (Bank pool trains): Trains in the bank POOL (discarded for exceeding the train limit, 2.1.4); they keep their orientation (code). May be bought from phase 3 at face value (5.13.4, 2.2.4). Not to be confused with the bank pool of SHARES. -- written by `act.rust_trains`, `act.discard_excess_trains`, `act.buy_train`
- `st.train_deck` (Bank train deck): New trains in the bank (not the bank pool), as counts; front = first group (L/2, 3, 4, 5, 6, 7/E) with remaining > 0 (1.7.11). Trains must be bought in this order (5.13.4); exports take from the front (4.11.6/4.11.7). -- written by `act.rust_trains`, `act.export_train`, `act.buy_train`
- `st.company_cash` (Company treasury cash): Cash in a company's treasury: credited by buy_share (treasury source), convert_concession, float_minors, pay_private_revenues; debited by buy_train / upgrade_l_train. -- written by `act.buy_train`, `act.upgrade_l_train`
- `st.bank_cash` (Bank cash): Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5). -- written by `act.buy_train`, `act.upgrade_l_train`

### Hooks / triggers fired by this module's nodes
- `act.phase_check` triggers `act.rust_trains` (`trains.rust_trains`)
- `act.phase_check` triggers `act.discard_excess_trains` (`trains.discard_excess_trains`)
- `act.phase_check` triggers `act.clear_concession_boxes` (`bidding.clear_concession_boxes`)
- `act.export_train` triggers `act.phase_check` (`trains.phase_check`)
- `act.buy_train` triggers `act.phase_check` (`trains.phase_check`)
- `act.upgrade_l_train` triggers `act.phase_check` (`trains.phase_check`)

### Notes that name 'sets ... itself' / flags (from api notes)
- `TrainError`: Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. Raised by buy_train_from_bank, upgrade_l_train and export_train for rule violations.
- `TRAIN_PHASE`: const.phase_table; 'L' deliberately absent (an L-train never starts a phase).
- `TRAIN_GROUPS`: Deck groups in buying order; a double-sided group is one physical pool (T12).
- `SCAN_ORDER`: front_train scan order.
- `EXPORT_L_ONLY`: export_train mode for 4.11.6.
- `EXPORT_NEXT_WITH_PHASE`: export_train mode for 4.11.7.
- `MAX_E_TRAINS_PER_COMPANY`: 5.13.11.
- `phase_check`: Order: phase, rust of every skipped phase, discard excess, clear concessions if old<5<=new, one audit log line.
- `buy_train_from_bank`: source None: new train if train_group(code) is the front group, else pool. L may be bought as long as the L/2 group is the front group. Orientation (L/2, 7/E) is the code passed.

### Module-level decisions (resolve any api or node of this module)
- **GA38** (gap A.2.38, severity S3, kind decision): ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).
  reason: layering (no module for a shared base) and the given except clauses.
- **GB19** (gap B-19, severity S3, kind decision): Layers: 1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares + company_formation, 6 bidding, 7 round_manager; upward calls are lazy imports (api node attrs.layer; lazy edges: turn_order->scoring.check_game_end_triggers, turn_order->certificates.fully_sold, certificates->bidding.items_led, trains->bidding.clear_concession_boxes, bidding->nothing upward now that resolve_stock_round has no sr_over check).
  reason: circular imports.
- **GA09** (gap A.1.9, severity S1, kind graph_fix): New node act.buy_train (+ upgrade_l_train, rust_trains, discard_excess_trains, front_group, deck_remaining, train_group, train_cost, train_limit) derived from rules 5.13.4-5.13.11, 2.1.x; no floated requirement; forced purchase and company-to-company sales deferred (rules 5.13.2/5.13.3 as deferred nodes).
  reason: task goal 1.
- **DN04** (gap new, severity S2, kind decision): buy_train_from_bank does not require the company to be floated and checks no round, active company or director (callers do).
  reason: first_turn_housekeeping buys L trains for companies mid-setup; main.py debug.
- **GA26** (gap A.2.26, severity S2, kind graph_fix): (a) concession clearing only when old < 5 <= new; (b) rust events of every skipped phase old+1..new are applied; (c) the 2.1.2 deferral is handled by operating_rounds_for_next_set with phase_before; (d) phase_events is an audit log, rust/discard/limits are applied immediately.
  reason: rules 2.1.2-2.1.5, 2.2.1.
- **GB22** (gap B-22, severity S3, kind graph_fix): See GA26 (old < 5 <= new).
  reason: GA26.
- **DN02** (gap new, severity S3, kind decision): Companies above the limit discard the lowest-face-value trains first, in descending share price order of companies. A director's real choice cannot be expressed through the skeleton actions.  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: 2.1.4/2.1.5 give the director the choice.
- **GA27** (gap A.2.27, severity S2, kind graph_fix): Deck = counts per code; groups L/2 and 7/E are one pool each; a card leaves by decrementing the first non-zero code of the group; effective type for the phase check: '2' for L/2 cards, the code for others ('7' for 7/E).
  reason: T12.
- **DN14** (gap new, severity S3, kind decision): Train exports at resolution never set sale_happened (A17 kept).
  reason: else the first-round rule could never fire.
- **GB14** (gap B-14, severity S1, kind graph_fix): Replaced by the rule-derived act.buy_train (order, limit before buying, E limit, face value, side choice, phase check); extra optional parameter source=None.
  reason: GA09.
- **DN03** (gap new, severity S2, kind decision): Buying from the bank takes the front group or a pool train; the code passed is the orientation; L may be bought while L/2 is the front group; L->2 upgrade allowed in phases 1-2 for 80 and counts as a purchase.
  reason: 5.13.4-5.13.10.
- **DN07** (gap new, severity S3, kind decision): Trains in bank_pool_trains can be bought from phase 3 on (2.2.4) at face value without a phase check.
  reason: 5.13.4.

## 3. API contracts

### `trains.TrainError` (exception)

```python
class TrainError(Exception)
```

- bases: ['Exception']; message `<ERR_CODE>: <text>`; attribute `.code` = ERR_CODE
- raised by: trains.buy_train_from_bank, trains.export_train, trains.train_cost, trains.train_group, trains.train_limit, trains.upgrade_l_train
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 4
- given name (fixed by given code, never rename): YES
- aliases: none
- callers in given code: actions._apply_operate, operating.first_turn_housekeeping
- callers from graph (calls/triggers): none
- api notes: Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. Raised by buy_train_from_bank, upgrade_l_train and export_train for rule violations.

**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA38** (gap A.2.38, severity S3, kind decision): ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).
  reason: layering (no module for a shared base) and the given except clauses.

### `trains.TRAIN_PHASE` (constant)

```python
TRAIN_PHASE = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 'E': 7}
```

- value: `{"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "E": 7}`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 4
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: const.phase_table; 'L' deliberately absent (an L-train never starts a phase).

### `trains.TRAIN_GROUPS` (constant)

```python
TRAIN_GROUPS = (('L', '2'), ('3',), ('4',), ('5',), ('6',), ('7', 'E'))
```

- value: `[["L", "2"], ["3"], ["4"], ["5"], ["6"], ["7", "E"]]`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 4
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: Deck groups in buying order; a double-sided group is one physical pool (T12).

### `trains.SCAN_ORDER` (constant)

```python
SCAN_ORDER = ('L', '2', '3', '4', '5', '6', '7', 'E')
```

- value: `["L", "2", "3", "4", "5", "6", "7", "E"]`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 4
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: front_train scan order.

### `trains.EXPORT_L_ONLY` (constant)

```python
EXPORT_L_ONLY = 'L_only'
```

- value: `"L_only"`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 4
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: export_train mode for 4.11.6.

### `trains.EXPORT_NEXT_WITH_PHASE` (constant)

```python
EXPORT_NEXT_WITH_PHASE = 'next_with_phase'
```

- value: `"next_with_phase"`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 4
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: export_train mode for 4.11.7.

### `trains.MAX_E_TRAINS_PER_COMPANY` (constant)

```python
MAX_E_TRAINS_PER_COMPANY = 1
```

- value: `1`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 4
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: 5.13.11.

### `trains.phase_of_train` (function)

```python
phase_of_train(code: str) -> int | None
```

- parameters: ['code']
- defaults (explicit): (none)
- returns: TRAIN_PHASE.get(code); None for 'L' and unknown codes
- layer: 4
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): trains.phase_check

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception for unknown codes

**Implements graph node(s)**: `drv.phase_of_train`

#### Graph node `drv.phase_of_train` (derived) - Phase of a train type
Phase triggered by the first train of a type.

- graph signature (abstract): params = ['train type']; returns = int

**Formula**: [2.2.3-2.2.8] const.phase_table (L/2 exported or bought as 2-train -> 2)

**Constants used**:
- `const.phase_table` (Phase table): Phase of the first train of a type: 2-train (bought, or L upgraded) -> 2; 3 -> 3; 4 -> 4; 5 -> 5; 6 -> 6; 7 or E -> 7 (2.2.3-2.2.8). An L-train never starts a phase. Per phase: train limits (minor/major) 1:2/4 2:2/4 3:2/4 4:1/3 5:1/2 6:1/2 7:1/2; operating rounds per stock round 1:1, 2..7:2; rust 3:L 4:2 6:3 7:4; phase 5 removes concessions (R9).; data: `{"table": {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "E": 7}, "train_limits": {"1": [2, 4], "2": [2, 4], "3": [2, 4], "4": [1, 3], "5": [1, 2], "6": [1, 2], "7": [1, 2]}, "ors_per_sr": {"1": 1, "2": 2, "3": 2, "4": 2, "5": 2, "6": 2, "7": 2}}`
  (in code: app.data.phases.PHASES_BY_NUMBER; trains.TRAIN_PHASE (L absent))

**Rules constraining this node**:
- 2.1.1: First train of each type bought or exported advances the phase.


### `trains.front_train` (function)

```python
front_train(state: GameState) -> str | None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: first code in SCAN_ORDER with state.bank.train_pool[code] > 0, else None
- layer: 4
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): trains.export_train

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.front_train`

#### Graph node `drv.front_train` (derived) - Front train of the deck
Code of the next available new train (first code with count > 0 in scan order L,2,3,4,5,6,7,E).

- graph signature (abstract): params = ['none']; returns = train code|null

**Formula**: [R7, 1.7.11] first code in scan order L,2,3,4,5,6,7,E with train_deck[code] > 0, else none

**State touched**:
- reads `st.train_deck` (Bank train deck): New trains in the bank (not the bank pool), as counts; front = first group (L/2, 3, 4, 5, 6, 7/E) with remaining > 0 (1.7.11). Trains must be bought in this order (5.13.4); exports take from the front (4.11.6/4.11.7). [type map train code -> count (groups L/2 and 7/E share one physical pool); unit trains; scope game]

**Rules constraining this node**:
- R7: 4.11.6 exports count as L trains, never trigger a phase. 4.11.7 export takes the current buyable pool, runs the phase check, exports a 3-train when L/2 exhausted. [formula]
- 1.7.11: Trains ascending, L/2 on top, 7/E at bottom. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Train deck** [repr.train_deck_counts]: maps to: state.bank.train_pool: dict[code, count]; setup: L 22, 2 0, 3 9, 4 6, 5 3, 6 3, 7 16, E 0
  rule for coder: Groups L/2 and 7/E are ONE physical pool each: remaining(group) = sum of the codes' counts; a card leaves by decrementing the first non-zero code of the group in order (L then 2; 7 then E) whatever side is bought or exported; the side chosen at purchase is recorded only as the code in the company's train list. front_train = first code in L,2,3,4,5,6,7,E with count > 0.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA27** (gap A.2.27, severity S2, kind graph_fix): Deck = counts per code; groups L/2 and 7/E are one pool each; a card leaves by decrementing the first non-zero code of the group; effective type for the phase check: '2' for L/2 cards, the code for others ('7' for 7/E).
  reason: T12.

### `trains.front_group` (function)

```python
front_group(state: GameState) -> tuple[str, ...] | None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: first group of TRAIN_GROUPS with remaining > 0, else None
- layer: 4
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `next_train_group`
- callers in given code: none
- callers from graph (calls/triggers): trains.buy_train_from_bank

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.front_group`

#### Graph node `drv.front_group` (derived) - Front train group
The deck group that may currently be bought from (5.13.4 order).

- graph signature (abstract): params = ['none']; returns = group|null

**Formula**: [5.13.4, 1.7.11] the first group of [L/2, 3, 4, 5, 6, 7/E] with deck_remaining > 0, else none

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.deck_remaining -> `trains.deck_remaining` [same module] signature: `deck_remaining(state: GameState, group: tuple[str, ...]) -> int` 

**State touched**:
- reads `st.train_deck` (Bank train deck): New trains in the bank (not the bank pool), as counts; front = first group (L/2, 3, 4, 5, 6, 7/E) with remaining > 0 (1.7.11). Trains must be bought in this order (5.13.4); exports take from the front (4.11.6/4.11.7). [type map train code -> count (groups L/2 and 7/E share one physical pool); unit trains; scope game]

**Rules constraining this node**:
- 1.7.11: Trains ascending, L/2 on top, 7/E at bottom. [formula]
- 5.13.4: From the bank: any bank-pool train, or the next new train; trains must be bought in order (all of the previous type bought or exported); price = face value; pool trains appear only by discard. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Train deck** [repr.train_deck_counts]: maps to: state.bank.train_pool: dict[code, count]; setup: L 22, 2 0, 3 9, 4 6, 5 3, 6 3, 7 16, E 0
  rule for coder: Groups L/2 and 7/E are ONE physical pool each: remaining(group) = sum of the codes' counts; a card leaves by decrementing the first non-zero code of the group in order (L then 2; 7 then E) whatever side is bought or exported; the side chosen at purchase is recorded only as the code in the company's train list. front_train = first code in L,2,3,4,5,6,7,E with count > 0.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA27** (gap A.2.27, severity S2, kind graph_fix): Deck = counts per code; groups L/2 and 7/E are one pool each; a card leaves by decrementing the first non-zero code of the group; effective type for the phase check: '2' for L/2 cards, the code for others ('7' for 7/E).
  reason: T12.

### `trains.deck_remaining` (function)

```python
deck_remaining(state: GameState, group: tuple[str, ...]) -> int
```

- parameters: ['state', 'group']
- defaults (explicit): (none)
- returns: sum of train_pool counts over the group's codes
- layer: 4
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): trains.buy_train_from_bank, trains.front_group

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.deck_remaining`

#### Graph node `drv.deck_remaining` (derived) - Remaining cards of a deck group
Number of new cards left in a group.

- graph signature (abstract): params = ['group']; returns = int

**Formula**: [T12] sum of train_deck[code] over the group's codes (L/2: L+2; 7/E: 7+E)

**State touched**:
- reads `st.train_deck` (Bank train deck): New trains in the bank (not the bank pool), as counts; front = first group (L/2, 3, 4, 5, 6, 7/E) with remaining > 0 (1.7.11). Trains must be bought in this order (5.13.4); exports take from the front (4.11.6/4.11.7). [type map train code -> count (groups L/2 and 7/E share one physical pool); unit trains; scope game]

**Rules constraining this node**:
- 1.7.11: Trains ascending, L/2 on top, 7/E at bottom.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Train deck** [repr.train_deck_counts]: maps to: state.bank.train_pool: dict[code, count]; setup: L 22, 2 0, 3 9, 4 6, 5 3, 6 3, 7 16, E 0
  rule for coder: Groups L/2 and 7/E are ONE physical pool each: remaining(group) = sum of the codes' counts; a card leaves by decrementing the first non-zero code of the group in order (L then 2; 7 then E) whatever side is bought or exported; the side chosen at purchase is recorded only as the code in the company's train list. front_train = first code in L,2,3,4,5,6,7,E with count > 0.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA27** (gap A.2.27, severity S2, kind graph_fix): Deck = counts per code; groups L/2 and 7/E are one pool each; a card leaves by decrementing the first non-zero code of the group; effective type for the phase check: '2' for L/2 cards, the code for others ('7' for 7/E).
  reason: T12.

### `trains.train_group` (function)

```python
train_group(code: str) -> tuple[str, ...]
```

- parameters: ['code']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 4
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): trains.buy_train_from_bank

**Exceptions**:

| class | code | when |
|---|---|---|
| TrainError | ERR_UNKNOWN_TRAIN | code not in TRAIN_GROUPS |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. code is a known train code -> `ERR_UNKNOWN_TRAIN`

**Implements graph node(s)**: `drv.train_group`

#### Graph node `drv.train_group` (derived) - Group of a train code
Deck group a train code belongs to.

- graph signature (abstract): params = ['code']; returns = group

**Formula**: [5.13.8, 5.13.10] L,2 -> L/2; 3; 4; 5; 6; 7,E -> 7/E; unknown code -> error ERR_UNKNOWN_TRAIN

**Constants used**:
- `const.train_deck` (Train deck composition): Deck order, front first: double-sided L/2 (22), 3 (9), 4 (6), 5 (3), 6 (3), double-sided 7/E (16) (1.7.11). Stored as counts per code; a double-sided group is ONE physical pool: remaining(group) = sum of its codes' counts; a card leaves by decrementing the first non-zero code in group order (L before 2; 7 before E).; data: `{"groups": [["L", "2"], ["3"], ["4"], ["5"], ["6"], ["7", "E"]], "initial_counts": {"L": 22, "2": 0, "3": 9, "4": 6, "5": 3, "6": 3, "7": 16, "E": 0}}`
  (in code: app.engine.setup.new_game: bank.train_pool; app.data.trains.TRAIN_TYPES)

**Rules constraining this node**:
- 5.13.10: The director chooses 7 or E when buying; cannot be changed; 7 cannot be upgraded to E. [formula]
- 5.13.8: The director chooses L or 2 when buying from the L/2 stack; double-sided cards. [formula]


### `trains.train_cost` (function)

```python
train_cost(code: str) -> int
```

- parameters: ['code']
- defaults (explicit): (none)
- returns: TRAIN_TYPES_BY_CODE[code].cost
- layer: 4
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): trains.buy_train_from_bank

**Exceptions**:

| class | code | when |
|---|---|---|
| TrainError | ERR_UNKNOWN_TRAIN | unknown code |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. code is a known train code -> `ERR_UNKNOWN_TRAIN`

**Implements graph node(s)**: `drv.train_cost`

#### Graph node `drv.train_cost` (derived) - Train face value
Price of a train type.

- graph signature (abstract): params = ['code']; returns = int

**Formula**: [5.13.4] const.train_costs[code]; unknown code -> ERR_UNKNOWN_TRAIN

**Constants used**:
- `const.train_costs` (Train costs): Face value of each train type (5.13.4: price paid must be the face value): L 60, 2 120, 3 200, 4 300, 5 500, 6 600, 7 750, E 1000; L->2 upgrade 80 (5.13.9).; data: `{"table": {"L": 60, "2": 120, "3": 200, "4": 300, "5": 500, "6": 600, "7": 750, "E": 1000}, "l_to_2_upgrade": 80}`
  (in code: app.data.trains.TRAIN_TYPES_BY_CODE[code].cost; L_TO_2_UPGRADE_COST)

**Rules constraining this node**:
- 5.13.4: From the bank: any bank-pool train, or the next new train; trains must be bought in order (all of the previous type bought or exported); price = face value; pool trains appear only by discard. [formula]


### `trains.train_limit` (function)

```python
train_limit(kind: str, phase: int) -> int
```

- parameters: ['kind', 'phase']
- defaults (explicit): (none)
- returns: PHASES_BY_NUMBER[phase].minor_train_limit / major_train_limit
- layer: 4
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): trains.buy_train_from_bank, trains.discard_excess_trains

**Exceptions**:

| class | code | when |
|---|---|---|
| TrainError | ERR_UNKNOWN_COMPANY | kind not in {'major','minor'} |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. kind in {'major','minor'} -> `ERR_UNKNOWN_COMPANY`

**Implements graph node(s)**: `drv.train_limit`

#### Graph node `drv.train_limit` (derived) - Train limit
Number of trains a company may own in a phase.

- graph signature (abstract): params = ['kind in {minor, major}', 'phase']; returns = int

**Formula**: [2.1.4, 2.2.3-2.2.8] const.phase_table.train_limits[phase][kind] (minor/major: 1-3: 2/4; 4: 1/3; 5-7: 1/2)

**Constants used**:
- `const.phase_table` (Phase table): Phase of the first train of a type: 2-train (bought, or L upgraded) -> 2; 3 -> 3; 4 -> 4; 5 -> 5; 6 -> 6; 7 or E -> 7 (2.2.3-2.2.8). An L-train never starts a phase. Per phase: train limits (minor/major) 1:2/4 2:2/4 3:2/4 4:1/3 5:1/2 6:1/2 7:1/2; operating rounds per stock round 1:1, 2..7:2; rust 3:L 4:2 6:3 7:4; phase 5 removes concessions (R9).; data: `{"table": {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "E": 7}, "train_limits": {"1": [2, 4], "2": [2, 4], "3": [2, 4], "4": [1, 3], "5": [1, 2], "6": [1, 2], "7": [1, 2]}, "ors_per_sr": {"1": 1, "2": 2, "3": 2, "4": 2, "5": 2, "6": 2, "7": 2}}`
  (in code: app.data.phases.PHASES_BY_NUMBER; trains.TRAIN_PHASE (L absent))

**Rules constraining this node**:
- 2.1.4: Excess trains discarded after rusting, into bank pool. [formula]
- 2.2.3: Phase 2: minor price = bid/2 rounded down to start value, treasury 2x; concessions convertible; major train limit 4.
- 2.2.4: Phase 3: L rusts; minor price as phase 2 but treasury = full bid.
- 2.2.5: Phase 4: 2-trains rust; limits.
- 2.2.8: Phase 5 removes unconverted concessions; phase 6 rusts 3; phase 7 rusts 4.
- 5.13.6: A company may buy several trains one after another, effects apply at once; a company below its limit may buy even if the purchase lowers the limit.
- 5.13.7: A company at the train limit cannot buy, even if the purchase would rust enough trains to make room.


### `trains.phase_check` (function)

```python
phase_check(state: GameState, code: str) -> None
```

- parameters: ['state', 'code']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 4
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `advance_phase`, `check_phase`
- callers in given code: none
- callers from graph (calls/triggers): trains.buy_train_from_bank, trains.export_train, trains.upgrade_l_train
- api notes: Order: phase, rust of every skipped phase, discard excess, clear concessions if old<5<=new, one audit log line.

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception: unknown code or a code that does not raise the phase is a no-op
- does not require a round type

**Implements graph node(s)**: `act.phase_check`

#### Graph node `act.phase_check` (action) - Phase check
Advance the phase if this is the first train of its type and apply the phase effects AT ONCE: rust, train-limit discard, concession clearing.

- graph signature (abstract): params = ['train code']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [2.2.1] an L-train never triggers a phase; codes 2..7, E map through the phase table; the phase never decreases

**Effects, in order** (execute exactly in this order):
1. [2.1.1] new = phase_of_train(code); if none or new <= phase: do nothing
2. old = phase; phase = new
3. [2.1.3] for every phase p in old+1..new (so skipped phases are not lost): call rust_trains(rust_table[p])
4. [2.1.4, 2.1.5] call discard_excess_trains (AFTER rusting, descending share price order)
5. [2.2.8, R9] if old < 5 <= new: call clear_concession_boxes
6. [2.1.2] append ONE audit line to phase_events (from, to, rusted codes, discarded count, operating rounds per stock round); the operating-round count is applied by start_operating_round, never here

**Errors listed by the graph node**:
- NONE (raises nothing; unknown code = no phase effect)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.phase_of_train -> `trains.phase_of_train` [same module] signature: `phase_of_train(code: str) -> int | None` 
- calls act.rust_trains -> `trains.rust_trains` [same module] signature: `rust_trains(state: GameState, code: str) -> None` 
- calls act.discard_excess_trains -> `trains.discard_excess_trains` [same module] signature: `discard_excess_trains(state: GameState) -> None` 
- calls act.clear_concession_boxes -> `bidding.clear_concession_boxes` [CROSS-MODULE] signature: `clear_concession_boxes(state: GameState) -> None` 
- triggers act.rust_trains -> `trains.rust_trains` [same module] signature: `rust_trains(state: GameState, code: str) -> None` 
- triggers act.discard_excess_trains -> `trains.discard_excess_trains` [same module] signature: `discard_excess_trains(state: GameState) -> None` 
- triggers act.clear_concession_boxes -> `bidding.clear_concession_boxes` [CROSS-MODULE] signature: `clear_concession_boxes(state: GameState) -> None` 

**State touched**:
- reads `st.phase` (Game phase): Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1). [type int 1..7; unit phase number; scope game]
- writes `st.phase` (Game phase): Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1). [type int 1..7; unit phase number; scope game]
- writes `st.phase_events` (Phase-change log): Audit log of phase changes: one line per change with from, to, rusted codes, trains discarded, operating rounds per stock round. NOT a work queue: rust, train-limit discard and concession clearing are applied immediately inside phase_check (2.1.2-2.1.5). [type list<log line>; unit lines; scope game]

**Constants used**:
- `const.rust_table` (Rust table): Phase 3 rusts L; phase 4 rusts 2; phase 6 rusts 3; phase 7 rusts 4 (2.2.4-2.2.8).; data: `{"table": {"3": ["L"], "4": ["2"], "6": ["3"], "7": ["4"]}}`
- `const.phase_table` (Phase table): Phase of the first train of a type: 2-train (bought, or L upgraded) -> 2; 3 -> 3; 4 -> 4; 5 -> 5; 6 -> 6; 7 or E -> 7 (2.2.3-2.2.8). An L-train never starts a phase. Per phase: train limits (minor/major) 1:2/4 2:2/4 3:2/4 4:1/3 5:1/2 6:1/2 7:1/2; operating rounds per stock round 1:1, 2..7:2; rust 3:L 4:2 6:3 7:4; phase 5 removes concessions (R9).; data: `{"table": {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "E": 7}, "train_limits": {"1": [2, 4], "2": [2, 4], "3": [2, 4], "4": [1, 3], "5": [1, 2], "6": [1, 2], "7": [1, 2]}, "ors_per_sr": {"1": 1, "2": 2, "3": 2, "4": 2, "5": 2, "6": 2, "7": 2}}`
  (in code: app.data.phases.PHASES_BY_NUMBER; trains.TRAIN_PHASE (L absent))

**Rules constraining this node**:
- R9: From phase 5 held concessions disappear, concession boxes are cleared and never refilled. [demanded in preconditions/effects]
- 2.1.4: Excess trains discarded after rusting, into bank pool. [demanded in preconditions/effects]
- 2.2.1: Once a phase introduces a rule it stays; the phase number only increases. [demanded in preconditions/effects]
- 2.2.8: Phase 5 removes unconverted concessions; phase 6 rusts 3; phase 7 rusts 4. [demanded in preconditions/effects]
- 2.1.5: Companies discard in descending share price order. [demanded in preconditions/effects]
- 2.1.3: Trains of a prior type rust immediately without compensation. [demanded in preconditions/effects]
- 2.1.2: Immediate, except two ORs per SR starts after the following SR. [demanded in preconditions/effects]
- 2.1.1: First train of each type bought or exported advances the phase. [demanded in preconditions/effects]
- 2.2.3: Phase 2: minor price = bid/2 rounded down to start value, treasury 2x; concessions convertible; major train limit 4.
- 2.2.4: Phase 3: L rusts; minor price as phase 2 but treasury = full bid.
- 2.2.5: Phase 4: 2-trains rust; limits.
- 5.13.5: Buying the first train of a new type advances the phase; some trains rust at once, without compensation.
- 5.13.6: A company may buy several trains one after another, effects apply at once; a company below its limit may buy even if the purchase lowers the limit.
- 5.13.9: In phases 1 and 2 an L can be converted to a 2 for the indicated price; counts as a train purchase.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Phase** [repr.phase_state]: maps to: state.phase: int 1..7; limits and rust from app.data.phases.PHASES_BY_NUMBER; trigger table trains.TRAIN_PHASE (module constant)
  rule for coder: phase only increases (2.2.1) and is written only by phase_check (plus debug code in main.py). PHASES_BY_NUMBER[n].trains_rusted gives ONE code per phase; skipped phases are rusted too (loop old+1..new).
- **Phase events** [repr.phase_log]: maps to: one line per phase change appended to state.log: 'PHASE_EVENT from=<old> to=<new> rusted=<codes comma-separated or -> discarded=<n> or_per_sr=<n>'
  rule for coder: Audit only; there is no consumer; rust, discard and concession clearing happen inside phase_check.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA26** (gap A.2.26, severity S2, kind graph_fix): (a) concession clearing only when old < 5 <= new; (b) rust events of every skipped phase old+1..new are applied; (c) the 2.1.2 deferral is handled by operating_rounds_for_next_set with phase_before; (d) phase_events is an audit log, rust/discard/limits are applied immediately.
  reason: rules 2.1.2-2.1.5, 2.2.1.
- **GB22** (gap B-22, severity S3, kind graph_fix): See GA26 (old < 5 <= new).
  reason: GA26.
- **GB08** (gap B-8, severity S3, kind repr): One audit line in state.log (repr.phase_log); no consumer needed.
  reason: GA26.
- **GB19** (gap B-19, severity S3, kind decision): Layers: 1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares + company_formation, 6 bidding, 7 round_manager; upward calls are lazy imports (api node attrs.layer; lazy edges: turn_order->scoring.check_game_end_triggers, turn_order->certificates.fully_sold, certificates->bidding.items_led, trains->bidding.clear_concession_boxes, bidding->nothing upward now that resolve_stock_round has no sr_over check).
  reason: circular imports.

### `trains.rust_trains` (function)

```python
rust_trains(state: GameState, code: str) -> None
```

- parameters: ['state', 'code']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 4
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `rust`
- callers in given code: none
- callers from graph (calls/triggers): trains.phase_check

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception; unknown code is a no-op

**Implements graph node(s)**: `act.rust_trains`

#### Graph node `act.rust_trains` (action) - Rust trains
Remove every train of a rusted type from the game without compensation.

- graph signature (abstract): params = ['train code']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [2.1.3] rusting is immediate and without compensation

**Effects, in order** (execute exactly in this order):
1. [2.1.3] remove every train with that code from every company_trains list, from bank_pool_trains and from the deck counts; nothing is paid

**Errors listed by the graph node**:
- NONE (raises nothing)

**Order edges**:
- `act.rust_trains` runs before `act.discard_excess_trains` (seq 1; phase: seq 1 runs before seq 2)

**State touched**:
- reads `st.company_trains` (Company trains): Trains owned by each minor and major company; the code records the orientation chosen at purchase (L or 2; 7 or E). Rusted trains vanish (2.1.3); excess trains go to bank_pool_trains (2.1.4). [type map company -> list<train code>; unit trains; scope per company]
- reads `st.bank_pool_trains` (Bank pool trains): Trains in the bank POOL (discarded for exceeding the train limit, 2.1.4); they keep their orientation (code). May be bought from phase 3 at face value (5.13.4, 2.2.4). Not to be confused with the bank pool of SHARES. [type list<train code>; unit trains; scope game]
- reads `st.train_deck` (Bank train deck): New trains in the bank (not the bank pool), as counts; front = first group (L/2, 3, 4, 5, 6, 7/E) with remaining > 0 (1.7.11). Trains must be bought in this order (5.13.4); exports take from the front (4.11.6/4.11.7). [type map train code -> count (groups L/2 and 7/E share one physical pool); unit trains; scope game]
- writes `st.company_trains` (Company trains): Trains owned by each minor and major company; the code records the orientation chosen at purchase (L or 2; 7 or E). Rusted trains vanish (2.1.3); excess trains go to bank_pool_trains (2.1.4). [type map company -> list<train code>; unit trains; scope per company]
- writes `st.bank_pool_trains` (Bank pool trains): Trains in the bank POOL (discarded for exceeding the train limit, 2.1.4); they keep their orientation (code). May be bought from phase 3 at face value (5.13.4, 2.2.4). Not to be confused with the bank pool of SHARES. [type list<train code>; unit trains; scope game]
- writes `st.train_deck` (Bank train deck): New trains in the bank (not the bank pool), as counts; front = first group (L/2, 3, 4, 5, 6, 7/E) with remaining > 0 (1.7.11). Trains must be bought in this order (5.13.4); exports take from the front (4.11.6/4.11.7). [type map train code -> count (groups L/2 and 7/E share one physical pool); unit trains; scope game]

**Constants used**:
- `const.rust_table` (Rust table): Phase 3 rusts L; phase 4 rusts 2; phase 6 rusts 3; phase 7 rusts 4 (2.2.4-2.2.8).; data: `{"table": {"3": ["L"], "4": ["2"], "6": ["3"], "7": ["4"]}}`

**Rules constraining this node**:
- 2.1.3: Trains of a prior type rust immediately without compensation. [demanded in preconditions/effects]
- 5.13.5: Buying the first train of a new type advances the phase; some trains rust at once, without compensation.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Trains of companies and of the bank pool** [repr.company_trains]: maps to: MajorCompanyState.trains / MinorCompanyState.trains: list[str] of codes ('L','2','3',...,'7','E'); BankState.discarded_trains: list[str] (bank pool, orientation kept)
  rule for coder: Purchase appends the code chosen; rust removes by code everywhere (companies, pool, deck counts); discard moves one code to discarded_trains; 'E' appears at most once per company.
- **Bank pool naming** [repr.bank_pool_naming]: maps to: SHARES: MajorCompanyState.shares_in_bank_pool (units, max 5) = 'the bank pool'; TRAINS: BankState.discarded_trains (list of codes) = 'the bank pool' of trains
  rule for coder: buy_share source strings: 'bank' and 'pool' BOTH mean the bank pool of shares; 'treasury' = MajorCompanyState.shares_in_treasury (ordinary units only, the director's certificate is never in it; LNWR 9, others 8 at flotation); None = module chooses (pool first, else treasury).
- **Train deck** [repr.train_deck_counts]: maps to: state.bank.train_pool: dict[code, count]; setup: L 22, 2 0, 3 9, 4 6, 5 3, 6 3, 7 16, E 0
  rule for coder: Groups L/2 and 7/E are ONE physical pool each: remaining(group) = sum of the codes' counts; a card leaves by decrementing the first non-zero code of the group in order (L then 2; 7 then E) whatever side is bought or exported; the side chosen at purchase is recorded only as the code in the company's train list. front_train = first code in L,2,3,4,5,6,7,E with count > 0.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA09** (gap A.1.9, severity S1, kind graph_fix): New node act.buy_train (+ upgrade_l_train, rust_trains, discard_excess_trains, front_group, deck_remaining, train_group, train_cost, train_limit) derived from rules 5.13.4-5.13.11, 2.1.x; no floated requirement; forced purchase and company-to-company sales deferred (rules 5.13.2/5.13.3 as deferred nodes).
  reason: task goal 1.
- **GA26** (gap A.2.26, severity S2, kind graph_fix): (a) concession clearing only when old < 5 <= new; (b) rust events of every skipped phase old+1..new are applied; (c) the 2.1.2 deferral is handled by operating_rounds_for_next_set with phase_before; (d) phase_events is an audit log, rust/discard/limits are applied immediately.
  reason: rules 2.1.2-2.1.5, 2.2.1.
- **DN07** (gap new, severity S3, kind decision): Trains in bank_pool_trains can be bought from phase 3 on (2.2.4) at face value without a phase check.
  reason: 5.13.4.
- **GA27** (gap A.2.27, severity S2, kind graph_fix): Deck = counts per code; groups L/2 and 7/E are one pool each; a card leaves by decrementing the first non-zero code of the group; effective type for the phase check: '2' for L/2 cards, the code for others ('7' for 7/E).
  reason: T12.

### `trains.discard_excess_trains` (function)

```python
discard_excess_trains(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 4
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `enforce_train_limit`
- callers in given code: none
- callers from graph (calls/triggers): trains.phase_check

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception

**Implements graph node(s)**: `act.discard_excess_trains`

#### Graph node `act.discard_excess_trains` (action) - Discard excess trains
Companies above the new train limit discard the excess into the bank pool, without compensation.

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [2.1.5] applies after rusting; companies act in descending share price order

**Effects, in order** (execute exactly in this order):
1. [2.1.5] order = descending_order(companies that own trains)
2. [2.1.4] for each company in order: while len(trains) > train_limit(kind, phase): discard ONE train into bank_pool_trains (orientation kept); which train: the lowest face value first (needs_owner: a director's choice)
3. no compensation

**Errors listed by the graph node**:
- NONE (raises nothing)

**Order edges**:
- `act.discard_excess_trains` runs before `act.clear_concession_boxes` (seq 2; phase: seq 2 runs before seq 3)
- `act.rust_trains` runs before `act.discard_excess_trains` (seq 1; phase: seq 1 runs before seq 2)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.train_limit -> `trains.train_limit` [same module] signature: `train_limit(kind: str, phase: int) -> int` 
- calls drv.descending_order -> `turn_order.descending_order` [CROSS-MODULE] signature: `descending_order(state: GameState, company_ids: Iterable[str]) -> list[str]` 

**State touched**:
- reads `st.company_trains` (Company trains): Trains owned by each minor and major company; the code records the orientation chosen at purchase (L or 2; 7 or E). Rusted trains vanish (2.1.3); excess trains go to bank_pool_trains (2.1.4). [type map company -> list<train code>; unit trains; scope per company]
- reads `st.phase` (Game phase): Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1). [type int 1..7; unit phase number; scope game]
- reads `st.market_stack` (Market piles): Which company tokens sit on which cell and their pile order. Company price = value of its cell. Pile order decides ties (1.6.2, 4.4.5, 4.12.2, 5.2.2). [type map cell->ordered list<company> (index 0 = top); unit company ids; scope game]
- writes `st.company_trains` (Company trains): Trains owned by each minor and major company; the code records the orientation chosen at purchase (L or 2; 7 or E). Rusted trains vanish (2.1.3); excess trains go to bank_pool_trains (2.1.4). [type map company -> list<train code>; unit trains; scope per company]
- writes `st.bank_pool_trains` (Bank pool trains): Trains in the bank POOL (discarded for exceeding the train limit, 2.1.4); they keep their orientation (code). May be bought from phase 3 at face value (5.13.4, 2.2.4). Not to be confused with the bank pool of SHARES. [type list<train code>; unit trains; scope game]

**Constants used**:
- `const.train_costs` (Train costs): Face value of each train type (5.13.4: price paid must be the face value): L 60, 2 120, 3 200, 4 300, 5 500, 6 600, 7 750, E 1000; L->2 upgrade 80 (5.13.9).; data: `{"table": {"L": 60, "2": 120, "3": 200, "4": 300, "5": 500, "6": 600, "7": 750, "E": 1000}, "l_to_2_upgrade": 80}`
  (in code: app.data.trains.TRAIN_TYPES_BY_CODE[code].cost; L_TO_2_UPGRADE_COST)

**Rules constraining this node**:
- 2.1.4: Excess trains discarded after rusting, into bank pool. [demanded in preconditions/effects]
- 2.1.5: Companies discard in descending share price order. [demanded in preconditions/effects]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Trains of companies and of the bank pool** [repr.company_trains]: maps to: MajorCompanyState.trains / MinorCompanyState.trains: list[str] of codes ('L','2','3',...,'7','E'); BankState.discarded_trains: list[str] (bank pool, orientation kept)
  rule for coder: Purchase appends the code chosen; rust removes by code everywhere (companies, pool, deck counts); discard moves one code to discarded_trains; 'E' appears at most once per company.
- **Phase** [repr.phase_state]: maps to: state.phase: int 1..7; limits and rust from app.data.phases.PHASES_BY_NUMBER; trigger table trains.TRAIN_PHASE (module constant)
  rule for coder: phase only increases (2.2.1) and is written only by phase_check (plus debug code in main.py). PHASES_BY_NUMBER[n].trains_rusted gives ONE code per phase; skipped phases are rusted too (loop old+1..new).
- **Stock market cells and piles** [repr.market_cells]: maps to: state.stock_positions[company_id] = (row, col); state.stock_stack[(row, col)] = list of company ids, index 0 = TOP; grid app.data.stock_market.STOCK_MARKET_BY_POSITION[(row, col)] -> StockCell(row, col, value, zone, game_end)
  rule for coder: Use stock_positions.place_token (removes from the old pile, APPENDS to the new = bottom) only when the cell changes; emptied piles remain as empty lists; down = (row+1, col), up = (row-1, col), absent cell = no move (R12); yellow = zone 'yellow'; game end = game_end True; start cells derived from zone in {'start','minor_start'}. Minors enter after the leading run of minor tokens (4.11.5).
- **Bank pool naming** [repr.bank_pool_naming]: maps to: SHARES: MajorCompanyState.shares_in_bank_pool (units, max 5) = 'the bank pool'; TRAINS: BankState.discarded_trains (list of codes) = 'the bank pool' of trains
  rule for coder: buy_share source strings: 'bank' and 'pool' BOTH mean the bank pool of shares; 'treasury' = MajorCompanyState.shares_in_treasury (ordinary units only, the director's certificate is never in it; LNWR 9, others 8 at flotation); None = module chooses (pool first, else treasury).


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA09** (gap A.1.9, severity S1, kind graph_fix): New node act.buy_train (+ upgrade_l_train, rust_trains, discard_excess_trains, front_group, deck_remaining, train_group, train_cost, train_limit) derived from rules 5.13.4-5.13.11, 2.1.x; no floated requirement; forced purchase and company-to-company sales deferred (rules 5.13.2/5.13.3 as deferred nodes).
  reason: task goal 1.
- **GA26** (gap A.2.26, severity S2, kind graph_fix): (a) concession clearing only when old < 5 <= new; (b) rust events of every skipped phase old+1..new are applied; (c) the 2.1.2 deferral is handled by operating_rounds_for_next_set with phase_before; (d) phase_events is an audit log, rust/discard/limits are applied immediately.
  reason: rules 2.1.2-2.1.5, 2.2.1.
- **DN02** (gap new, severity S3, kind decision): Companies above the limit discard the lowest-face-value trains first, in descending share price order of companies. A director's real choice cannot be expressed through the skeleton actions.  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: 2.1.4/2.1.5 give the director the choice.
- **DN07** (gap new, severity S3, kind decision): Trains in bank_pool_trains can be bought from phase 3 on (2.2.4) at face value without a phase check.
  reason: 5.13.4.

### `trains.export_train` (function)

```python
export_train(state: GameState, mode: str) -> None
```

- parameters: ['state', 'mode']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 4
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.remove_box1_minor_and_export, bidding.unsold_minor_exports

**Exceptions**:

| class | code | when |
|---|---|---|
| TrainError | ERR_BAD_MODE | mode not EXPORT_L_ONLY / EXPORT_NEXT_WITH_PHASE |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. mode in (EXPORT_L_ONLY, EXPORT_NEXT_WITH_PHASE) -> `ERR_BAD_MODE`

**Must NOT be checked by this function**:
- an empty deck is a no-op, never an error

**Implements graph node(s)**: `act.export_train`

#### Graph node `act.export_train` (action) - Export a train
Remove a train from the bank deck (not the pool); exported trains leave the game.

- graph signature (abstract): params = ['mode in {L_only, next_with_phase}']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.11.6] deck not empty (else no action)

**Effects, in order** (execute exactly in this order):
1. mode L_only [4.11.6, R7]: if the front group is L/2: remove one card (decrement L first, then 2); counts as an L-train: NO phase check; if no L/2 remains: no action
2. mode next_with_phase [4.11.7, R7]: remove one card from the front group (L/2 while any remain, then 3, 4, ...; decrement the first non-zero code of the group); effective type = '2' if the card came from L/2, else its code ('7' for the 7/E group); call phase_check(effective type)

**Errors listed by the graph node**:
- ERR_BAD_MODE: mode not one of the two constants (TrainError)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.front_train -> `trains.front_train` [same module] signature: `front_train(state: GameState) -> str | None` 
- calls act.phase_check -> `trains.phase_check` [same module] signature: `phase_check(state: GameState, code: str) -> None` 
- triggers act.phase_check -> `trains.phase_check` [same module] signature: `phase_check(state: GameState, code: str) -> None` 

**State touched**:
- reads `st.train_deck` (Bank train deck): New trains in the bank (not the bank pool), as counts; front = first group (L/2, 3, 4, 5, 6, 7/E) with remaining > 0 (1.7.11). Trains must be bought in this order (5.13.4); exports take from the front (4.11.6/4.11.7). [type map train code -> count (groups L/2 and 7/E share one physical pool); unit trains; scope game]
- writes `st.train_deck` (Bank train deck): New trains in the bank (not the bank pool), as counts; front = first group (L/2, 3, 4, 5, 6, 7/E) with remaining > 0 (1.7.11). Trains must be bought in this order (5.13.4); exports take from the front (4.11.6/4.11.7). [type map train code -> count (groups L/2 and 7/E share one physical pool); unit trains; scope game]

**Constants used**:
- `const.train_deck` (Train deck composition): Deck order, front first: double-sided L/2 (22), 3 (9), 4 (6), 5 (3), 6 (3), double-sided 7/E (16) (1.7.11). Stored as counts per code; a double-sided group is ONE physical pool: remaining(group) = sum of its codes' counts; a card leaves by decrementing the first non-zero code in group order (L before 2; 7 before E).; data: `{"groups": [["L", "2"], ["3"], ["4"], ["5"], ["6"], ["7", "E"]], "initial_counts": {"L": 22, "2": 0, "3": 9, "4": 6, "5": 3, "6": 3, "7": 16, "E": 0}}`
  (in code: app.engine.setup.new_game: bank.train_pool; app.data.trains.TRAIN_TYPES)

**Rules constraining this node**:
- R7: 4.11.6 exports count as L trains, never trigger a phase. 4.11.7 export takes the current buyable pool, runs the phase check, exports a 3-train when L/2 exhausted. [demanded in preconditions/effects]
- 4.11.6: One L/2-train exported from the bank per minor with no bid; no action if none. [demanded in preconditions/effects]
- 4.11.7: Unsold minor in box 1 is removed and next train exported (counts for phase). [demanded in preconditions/effects]
- 2.1.1: First train of each type bought or exported advances the phase.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Train deck** [repr.train_deck_counts]: maps to: state.bank.train_pool: dict[code, count]; setup: L 22, 2 0, 3 9, 4 6, 5 3, 6 3, 7 16, E 0
  rule for coder: Groups L/2 and 7/E are ONE physical pool each: remaining(group) = sum of the codes' counts; a card leaves by decrementing the first non-zero code of the group in order (L then 2; 7 then E) whatever side is bought or exported; the side chosen at purchase is recorded only as the code in the company's train list. front_train = first code in L,2,3,4,5,6,7,E with count > 0.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA27** (gap A.2.27, severity S2, kind graph_fix): Deck = counts per code; groups L/2 and 7/E are one pool each; a card leaves by decrementing the first non-zero code of the group; effective type for the phase check: '2' for L/2 cards, the code for others ('7' for 7/E).
  reason: T12.
- **DN14** (gap new, severity S3, kind decision): Train exports at resolution never set sale_happened (A17 kept).
  reason: else the first-round rule could never fire.

### `trains.buy_train_from_bank` (function)

```python
buy_train_from_bank(state: GameState, company_id: str, kind: str, code: str, source: str | None = None) -> None
```

- parameters: ['state', 'company_id', 'kind', 'code', 'source']
- defaults (explicit): {"source": "None"}
- returns: (see signature)
- layer: 4
- given name (fixed by given code, never rename): YES
- aliases: none
- callers in given code: actions._apply_operate, operating.first_turn_housekeeping
- callers from graph (calls/triggers): none
- api notes: source None: new train if train_group(code) is the front group, else pool. L may be bought as long as the L/2 group is the front group. Orientation (L/2, 7/E) is the code passed.

**Exceptions**:

| class | code | when |
|---|---|---|
| TrainError | ERR_UNKNOWN_COMPANY | kind invalid or company id not in the matching dict |
| TrainError | ERR_UNKNOWN_TRAIN | code unknown |
| TrainError | ERR_BAD_SOURCE | source not None/'new'/'pool' |
| TrainError | ERR_TRAIN_LIMIT | company already at its train limit |
| TrainError | ERR_E_LIMIT | code E and the company owns an E-train |
| TrainError | ERR_NOT_NEXT_TRAIN | new train outside the front group |
| TrainError | ERR_NOT_IN_POOL | pool train absent from the pool or phase < 3 |
| TrainError | ERR_INSUFFICIENT_FUNDS | treasury < face value |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. kind in {'major','minor'} and company exists in state.majors / state.minors -> `ERR_UNKNOWN_COMPANY`
2. code in TRAIN_PHASE or code == 'L' -> `ERR_UNKNOWN_TRAIN`
3. source in (None, 'new', 'pool') -> `ERR_BAD_SOURCE`
4. len(company.trains) < train_limit(kind, phase) (before buying) -> `ERR_TRAIN_LIMIT`
5. code != 'E' or no 'E' in company.trains -> `ERR_E_LIMIT`
6. new: train_group(code) == front_group(state); pool: code in bank.discarded_trains and phase >= 3 -> `ERR_NOT_NEXT_TRAIN / ERR_NOT_IN_POOL`
7. company.treasury >= train_cost(code) -> `ERR_INSUFFICIENT_FUNDS`

**Must NOT be checked by this function**:
- the company need NOT be floated (main.py debug and first_turn_housekeeping buy for companies in any state)
- no round_type / active-company / director check (actions.py does that)
- no 'must own a train' rule, no forced purchase (5.13.2 deferred)
- no company-to-company purchase (5.13.3 deferred)

**Implements graph node(s)**: `act.buy_train`

#### Graph node `act.buy_train` (action) - Buy a train from the bank
A company buys one train from the bank (new train in order, or a bank-pool train) at face value; phase effects apply at once. Does NOT require the company to be floated.

- graph signature (abstract): params = ['company c', 'kind in {major, minor}', 'train code', "source in {None, 'new', 'pool'} (None: new train if the code's group is the front group, else pool)"]; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [5.3.1] c exists in the dict of its kind
- [5.13.4] code is a known train code; source valid
- [5.13.7] len(company_trains[c]) < train_limit(kind, phase) BEFORE buying (the phase after the purchase is irrelevant)
- [5.13.11] code = E: company owns no E-train yet
- [5.13.4] new train: train_group(code) = front_group (all trains of the previous group bought or exported); pool train: code in bank_pool_trains and phase >= 3
- [5.13.4] company_cash[c] >= train_cost(code) (price = face value); forced purchase / emergency money is out of scope

**Effects, in order** (execute exactly in this order):
1. [5.13.4] company_cash[c] -= cost; bank_cash += cost
2. [5.13.8, 5.13.10] new train: remove one card from the group (decrement the first non-zero code of the group); the orientation chosen = the code appended; pool train: remove that code from bank_pool_trains
3. company_trains[c] += [code] (orientation is final; 7 cannot become E)
4. [5.13.5, 5.13.6] new train: call phase_check(code) at once (rust, discard, phases); pool train: no phase check (type already in play)

**Errors listed by the graph node**:
- ERR_UNKNOWN_COMPANY
- ERR_UNKNOWN_TRAIN
- ERR_BAD_SOURCE
- ERR_TRAIN_LIMIT
- ERR_E_LIMIT
- ERR_NOT_NEXT_TRAIN
- ERR_NOT_IN_POOL
- ERR_INSUFFICIENT_FUNDS

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.train_limit -> `trains.train_limit` [same module] signature: `train_limit(kind: str, phase: int) -> int` 
- calls drv.front_group -> `trains.front_group` [same module] signature: `front_group(state: GameState) -> tuple[str, ...] | None` 
- calls drv.train_group -> `trains.train_group` [same module] signature: `train_group(code: str) -> tuple[str, ...]` 
- calls drv.train_cost -> `trains.train_cost` [same module] signature: `train_cost(code: str) -> int` 
- calls drv.deck_remaining -> `trains.deck_remaining` [same module] signature: `deck_remaining(state: GameState, group: tuple[str, ...]) -> int` 
- calls act.phase_check -> `trains.phase_check` [same module] signature: `phase_check(state: GameState, code: str) -> None` 
- triggers act.phase_check -> `trains.phase_check` [same module] signature: `phase_check(state: GameState, code: str) -> None` 

**State touched**:
- reads `st.company_trains` (Company trains): Trains owned by each minor and major company; the code records the orientation chosen at purchase (L or 2; 7 or E). Rusted trains vanish (2.1.3); excess trains go to bank_pool_trains (2.1.4). [type map company -> list<train code>; unit trains; scope per company]
- reads `st.phase` (Game phase): Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1). [type int 1..7; unit phase number; scope game]
- reads `st.train_deck` (Bank train deck): New trains in the bank (not the bank pool), as counts; front = first group (L/2, 3, 4, 5, 6, 7/E) with remaining > 0 (1.7.11). Trains must be bought in this order (5.13.4); exports take from the front (4.11.6/4.11.7). [type map train code -> count (groups L/2 and 7/E share one physical pool); unit trains; scope game]
- reads `st.bank_pool_trains` (Bank pool trains): Trains in the bank POOL (discarded for exceeding the train limit, 2.1.4); they keep their orientation (code). May be bought from phase 3 at face value (5.13.4, 2.2.4). Not to be confused with the bank pool of SHARES. [type list<train code>; unit trains; scope game]
- reads `st.company_cash` (Company treasury cash): Cash in a company's treasury: credited by buy_share (treasury source), convert_concession, float_minors, pay_private_revenues; debited by buy_train / upgrade_l_train. [type int map company->int; unit pounds; scope per major and minor company]
- writes `st.company_cash` (Company treasury cash): Cash in a company's treasury: credited by buy_share (treasury source), convert_concession, float_minors, pay_private_revenues; debited by buy_train / upgrade_l_train. [type int map company->int; unit pounds; scope per major and minor company]
- writes `st.bank_cash` (Bank cash): Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5). [type int (can go below zero); unit pounds; scope game]
- writes `st.train_deck` (Bank train deck): New trains in the bank (not the bank pool), as counts; front = first group (L/2, 3, 4, 5, 6, 7/E) with remaining > 0 (1.7.11). Trains must be bought in this order (5.13.4); exports take from the front (4.11.6/4.11.7). [type map train code -> count (groups L/2 and 7/E share one physical pool); unit trains; scope game]
- writes `st.bank_pool_trains` (Bank pool trains): Trains in the bank POOL (discarded for exceeding the train limit, 2.1.4); they keep their orientation (code). May be bought from phase 3 at face value (5.13.4, 2.2.4). Not to be confused with the bank pool of SHARES. [type list<train code>; unit trains; scope game]
- writes `st.company_trains` (Company trains): Trains owned by each minor and major company; the code records the orientation chosen at purchase (L or 2; 7 or E). Rusted trains vanish (2.1.3); excess trains go to bank_pool_trains (2.1.4). [type map company -> list<train code>; unit trains; scope per company]

**Constants used**:
- `const.train_costs` (Train costs): Face value of each train type (5.13.4: price paid must be the face value): L 60, 2 120, 3 200, 4 300, 5 500, 6 600, 7 750, E 1000; L->2 upgrade 80 (5.13.9).; data: `{"table": {"L": 60, "2": 120, "3": 200, "4": 300, "5": 500, "6": 600, "7": 750, "E": 1000}, "l_to_2_upgrade": 80}`
  (in code: app.data.trains.TRAIN_TYPES_BY_CODE[code].cost; L_TO_2_UPGRADE_COST)
- `const.train_deck` (Train deck composition): Deck order, front first: double-sided L/2 (22), 3 (9), 4 (6), 5 (3), 6 (3), double-sided 7/E (16) (1.7.11). Stored as counts per code; a double-sided group is ONE physical pool: remaining(group) = sum of its codes' counts; a card leaves by decrementing the first non-zero code in group order (L before 2; 7 before E).; data: `{"groups": [["L", "2"], ["3"], ["4"], ["5"], ["6"], ["7", "E"]], "initial_counts": {"L": 22, "2": 0, "3": 9, "4": 6, "5": 3, "6": 3, "7": 16, "E": 0}}`
  (in code: app.engine.setup.new_game: bank.train_pool; app.data.trains.TRAIN_TYPES)

**Rules constraining this node**:
- 5.13.10: The director chooses 7 or E when buying; cannot be changed; 7 cannot be upgraded to E. [demanded in preconditions/effects]
- 5.3.1: Decisions for a company are made by its director; step H buys trains; only housekeeping and step H are in scope here (rest is given operating code). [demanded in preconditions/effects]
- 5.13.7: A company at the train limit cannot buy, even if the purchase would rust enough trains to make room. [demanded in preconditions/effects]
- 5.13.11: A company may own at most one E-train (minors may own but not run it). [demanded in preconditions/effects]
- 5.13.4: From the bank: any bank-pool train, or the next new train; trains must be bought in order (all of the previous type bought or exported); price = face value; pool trains appear only by discard. [demanded in preconditions/effects]
- 5.13.5: Buying the first train of a new type advances the phase; some trains rust at once, without compensation. [demanded in preconditions/effects]
- 5.13.8: The director chooses L or 2 when buying from the L/2 stack; double-sided cards. [demanded in preconditions/effects]
- 5.13.6: A company may buy several trains one after another, effects apply at once; a company below its limit may buy even if the purchase lowers the limit. [demanded in preconditions/effects]
- 1.7.11: Trains ascending, L/2 on top, 7/E at bottom.
- 2.1.1: First train of each type bought or exported advances the phase.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Trains of companies and of the bank pool** [repr.company_trains]: maps to: MajorCompanyState.trains / MinorCompanyState.trains: list[str] of codes ('L','2','3',...,'7','E'); BankState.discarded_trains: list[str] (bank pool, orientation kept)
  rule for coder: Purchase appends the code chosen; rust removes by code everywhere (companies, pool, deck counts); discard moves one code to discarded_trains; 'E' appears at most once per company.
- **Phase** [repr.phase_state]: maps to: state.phase: int 1..7; limits and rust from app.data.phases.PHASES_BY_NUMBER; trigger table trains.TRAIN_PHASE (module constant)
  rule for coder: phase only increases (2.2.1) and is written only by phase_check (plus debug code in main.py). PHASES_BY_NUMBER[n].trains_rusted gives ONE code per phase; skipped phases are rusted too (loop old+1..new).
- **Train deck** [repr.train_deck_counts]: maps to: state.bank.train_pool: dict[code, count]; setup: L 22, 2 0, 3 9, 4 6, 5 3, 6 3, 7 16, E 0
  rule for coder: Groups L/2 and 7/E are ONE physical pool each: remaining(group) = sum of the codes' counts; a card leaves by decrementing the first non-zero code of the group in order (L then 2; 7 then E) whatever side is bought or exported; the side chosen at purchase is recorded only as the code in the company's train list. front_train = first code in L,2,3,4,5,6,7,E with count > 0.
- **Bank pool naming** [repr.bank_pool_naming]: maps to: SHARES: MajorCompanyState.shares_in_bank_pool (units, max 5) = 'the bank pool'; TRAINS: BankState.discarded_trains (list of codes) = 'the bank pool' of trains
  rule for coder: buy_share source strings: 'bank' and 'pool' BOTH mean the bank pool of shares; 'treasury' = MajorCompanyState.shares_in_treasury (ordinary units only, the director's certificate is never in it; LNWR 9, others 8 at flotation); None = module chooses (pool first, else treasury).
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA09** (gap A.1.9, severity S1, kind graph_fix): New node act.buy_train (+ upgrade_l_train, rust_trains, discard_excess_trains, front_group, deck_remaining, train_group, train_cost, train_limit) derived from rules 5.13.4-5.13.11, 2.1.x; no floated requirement; forced purchase and company-to-company sales deferred (rules 5.13.2/5.13.3 as deferred nodes).
  reason: task goal 1.
- **GB14** (gap B-14, severity S1, kind graph_fix): Replaced by the rule-derived act.buy_train (order, limit before buying, E limit, face value, side choice, phase check); extra optional parameter source=None.
  reason: GA09.
- **DN03** (gap new, severity S2, kind decision): Buying from the bank takes the front group or a pool train; the code passed is the orientation; L may be bought while L/2 is the front group; L->2 upgrade allowed in phases 1-2 for 80 and counts as a purchase.
  reason: 5.13.4-5.13.10.
- **DN07** (gap new, severity S3, kind decision): Trains in bank_pool_trains can be bought from phase 3 on (2.2.4) at face value without a phase check.
  reason: 5.13.4.
- **GA27** (gap A.2.27, severity S2, kind graph_fix): Deck = counts per code; groups L/2 and 7/E are one pool each; a card leaves by decrementing the first non-zero code of the group; effective type for the phase check: '2' for L/2 cards, the code for others ('7' for 7/E).
  reason: T12.
- **DN04** (gap new, severity S2, kind decision): buy_train_from_bank does not require the company to be floated and checks no round, active company or director (callers do).
  reason: first_turn_housekeeping buys L trains for companies mid-setup; main.py debug.

### `trains.upgrade_l_train` (function)

```python
upgrade_l_train(state: GameState, company_id: str, kind: str) -> None
```

- parameters: ['state', 'company_id', 'kind']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 4
- given name (fixed by given code, never rename): no
- **aliases that MUST also be exported** (same object / same behaviour): `upgrade_l_to_2`
- callers in given code: none
- callers from graph (calls/triggers): none

**Exceptions**:

| class | code | when |
|---|---|---|
| TrainError | ERR_UNKNOWN_COMPANY | unknown company/kind |
| TrainError | ERR_PHASE | phase > 2 |
| TrainError | ERR_NO_L_TRAIN | company owns no L-train |
| TrainError | ERR_INSUFFICIENT_FUNDS | treasury < 80 |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. company exists for kind -> `ERR_UNKNOWN_COMPANY`
2. phase <= 2 -> `ERR_PHASE`
3. 'L' in company.trains -> `ERR_NO_L_TRAIN`
4. treasury >= 80 -> `ERR_INSUFFICIENT_FUNDS`

**Must NOT be checked by this function**:
- company need not be floated

**Implements graph node(s)**: `act.upgrade_l_train`

#### Graph node `act.upgrade_l_train` (action) - Upgrade an L-train to a 2-train
Flip an owned L-train to a 2-train for 80 in phases 1-2; counts as a train purchase and can start phase 2.

- graph signature (abstract): params = ['company c', 'kind in {major, minor}']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [5.3.1] c exists in the dict of its kind
- [5.13.9] phase <= 2
- [5.13.9] the company owns an L-train
- [5.13.9] company_cash[c] >= 80

**Effects, in order** (execute exactly in this order):
1. [5.13.9] company_cash[c] -= 80; bank_cash += 80
2. one L in company_trains[c] becomes '2' (the card is flipped; the deck counts are unchanged)
3. [2.2.3, 5.13.9] call phase_check('2') (counts as a train purchase)

**Errors listed by the graph node**:
- ERR_UNKNOWN_COMPANY
- ERR_PHASE
- ERR_NO_L_TRAIN
- ERR_INSUFFICIENT_FUNDS

**Calls it must make / may trigger** (callee api in brackets):
- calls act.phase_check -> `trains.phase_check` [same module] signature: `phase_check(state: GameState, code: str) -> None` 
- triggers act.phase_check -> `trains.phase_check` [same module] signature: `phase_check(state: GameState, code: str) -> None` 

**State touched**:
- reads `st.company_trains` (Company trains): Trains owned by each minor and major company; the code records the orientation chosen at purchase (L or 2; 7 or E). Rusted trains vanish (2.1.3); excess trains go to bank_pool_trains (2.1.4). [type map company -> list<train code>; unit trains; scope per company]
- reads `st.phase` (Game phase): Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1). [type int 1..7; unit phase number; scope game]
- reads `st.company_cash` (Company treasury cash): Cash in a company's treasury: credited by buy_share (treasury source), convert_concession, float_minors, pay_private_revenues; debited by buy_train / upgrade_l_train. [type int map company->int; unit pounds; scope per major and minor company]
- writes `st.company_cash` (Company treasury cash): Cash in a company's treasury: credited by buy_share (treasury source), convert_concession, float_minors, pay_private_revenues; debited by buy_train / upgrade_l_train. [type int map company->int; unit pounds; scope per major and minor company]
- writes `st.bank_cash` (Bank cash): Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5). [type int (can go below zero); unit pounds; scope game]
- writes `st.company_trains` (Company trains): Trains owned by each minor and major company; the code records the orientation chosen at purchase (L or 2; 7 or E). Rusted trains vanish (2.1.3); excess trains go to bank_pool_trains (2.1.4). [type map company -> list<train code>; unit trains; scope per company]

**Constants used**:
- `const.train_costs` (Train costs): Face value of each train type (5.13.4: price paid must be the face value): L 60, 2 120, 3 200, 4 300, 5 500, 6 600, 7 750, E 1000; L->2 upgrade 80 (5.13.9).; data: `{"table": {"L": 60, "2": 120, "3": 200, "4": 300, "5": 500, "6": 600, "7": 750, "E": 1000}, "l_to_2_upgrade": 80}`
  (in code: app.data.trains.TRAIN_TYPES_BY_CODE[code].cost; L_TO_2_UPGRADE_COST)

**Rules constraining this node**:
- 2.2.3: Phase 2: minor price = bid/2 rounded down to start value, treasury 2x; concessions convertible; major train limit 4. [demanded in preconditions/effects]
- 5.3.1: Decisions for a company are made by its director; step H buys trains; only housekeeping and step H are in scope here (rest is given operating code). [demanded in preconditions/effects]
- 5.13.9: In phases 1 and 2 an L can be converted to a 2 for the indicated price; counts as a train purchase. [demanded in preconditions/effects]
- 2.1.1: First train of each type bought or exported advances the phase.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Trains of companies and of the bank pool** [repr.company_trains]: maps to: MajorCompanyState.trains / MinorCompanyState.trains: list[str] of codes ('L','2','3',...,'7','E'); BankState.discarded_trains: list[str] (bank pool, orientation kept)
  rule for coder: Purchase appends the code chosen; rust removes by code everywhere (companies, pool, deck counts); discard moves one code to discarded_trains; 'E' appears at most once per company.
- **Phase** [repr.phase_state]: maps to: state.phase: int 1..7; limits and rust from app.data.phases.PHASES_BY_NUMBER; trigger table trains.TRAIN_PHASE (module constant)
  rule for coder: phase only increases (2.2.1) and is written only by phase_check (plus debug code in main.py). PHASES_BY_NUMBER[n].trains_rusted gives ONE code per phase; skipped phases are rusted too (loop old+1..new).
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA09** (gap A.1.9, severity S1, kind graph_fix): New node act.buy_train (+ upgrade_l_train, rust_trains, discard_excess_trains, front_group, deck_remaining, train_group, train_cost, train_limit) derived from rules 5.13.4-5.13.11, 2.1.x; no floated requirement; forced purchase and company-to-company sales deferred (rules 5.13.2/5.13.3 as deferred nodes).
  reason: task goal 1.
- **DN03** (gap new, severity S2, kind decision): Buying from the bank takes the front group or a pool train; the code passed is the orientation; L may be bought while L/2 is the front group; L->2 upgrade allowed in phases 1-2 for 80 and counts as a purchase.
  reason: 5.13.4-5.13.10.

## 4. Rules this module is responsible for (id + text, verbatim from the graph)

- **1.7.11** (rule): Trains ascending, L/2 on top, 7/E at bottom. -- constrains `drv.front_train`, `drv.front_group`, `drv.deck_remaining`, `act.buy_train`
- **2.1.1** (rule): First train of each type bought or exported advances the phase. -- constrains `drv.phase_of_train`, `act.phase_check`, `act.export_train`, `act.buy_train`, `act.upgrade_l_train`
- **2.1.2** (rule): Immediate, except two ORs per SR starts after the following SR. -- constrains `act.phase_check`
- **2.1.3** (rule): Trains of a prior type rust immediately without compensation. -- constrains `act.phase_check`, `act.rust_trains`
- **2.1.4** (rule): Excess trains discarded after rusting, into bank pool. -- constrains `drv.train_limit`, `act.phase_check`, `act.discard_excess_trains`
- **2.1.5** (rule): Companies discard in descending share price order. -- constrains `act.phase_check`, `act.discard_excess_trains`
- **2.2.1** (rule): Once a phase introduces a rule it stays; the phase number only increases. -- constrains `act.phase_check`
- **2.2.3** (rule): Phase 2: minor price = bid/2 rounded down to start value, treasury 2x; concessions convertible; major train limit 4. -- constrains `drv.train_limit`, `act.phase_check`, `act.upgrade_l_train`
- **2.2.4** (rule): Phase 3: L rusts; minor price as phase 2 but treasury = full bid. -- constrains `drv.train_limit`, `act.phase_check`
- **2.2.5** (rule): Phase 4: 2-trains rust; limits. -- constrains `drv.train_limit`, `act.phase_check`
- **2.2.8** (rule): Phase 5 removes unconverted concessions; phase 6 rusts 3; phase 7 rusts 4. -- constrains `drv.train_limit`, `act.phase_check`
- **4.11.6** (rule): One L/2-train exported from the bank per minor with no bid; no action if none. -- constrains `act.export_train`
- **4.11.7** (rule): Unsold minor in box 1 is removed and next train exported (counts for phase). -- constrains `act.export_train`
- **5.13.10** (rule): The director chooses 7 or E when buying; cannot be changed; 7 cannot be upgraded to E. -- constrains `drv.train_group`, `act.buy_train`
- **5.13.11** (rule): A company may own at most one E-train (minors may own but not run it). -- constrains `act.buy_train`
- **5.13.4** (rule): From the bank: any bank-pool train, or the next new train; trains must be bought in order (all of the previous type bought or exported); price = face value; pool trains appear only by discard. -- constrains `drv.front_group`, `drv.train_cost`, `act.buy_train`
- **5.13.5** (rule): Buying the first train of a new type advances the phase; some trains rust at once, without compensation. -- constrains `act.phase_check`, `act.rust_trains`, `act.buy_train`
- **5.13.6** (rule): A company may buy several trains one after another, effects apply at once; a company below its limit may buy even if the purchase lowers the limit. -- constrains `drv.train_limit`, `act.phase_check`, `act.buy_train`
- **5.13.7** (rule): A company at the train limit cannot buy, even if the purchase would rust enough trains to make room. -- constrains `drv.train_limit`, `act.buy_train`
- **5.13.8** (rule): The director chooses L or 2 when buying from the L/2 stack; double-sided cards. -- constrains `drv.train_group`, `act.buy_train`
- **5.13.9** (rule): In phases 1 and 2 an L can be converted to a 2 for the indicated price; counts as a train purchase. -- constrains `act.phase_check`, `act.upgrade_l_train`
- **5.3.1** (rule): Decisions for a company are made by its director; step H buys trains; only housekeeping and step H are in scope here (rest is given operating code). -- constrains `act.buy_train`, `act.upgrade_l_train`
- **R7** (ruling): 4.11.6 exports count as L trains, never trigger a phase. 4.11.7 export takes the current buyable pool, runs the phase check, exports a 3-train when L/2 exhausted. -- constrains `drv.front_train`, `act.export_train`
- **R9** (ruling): From phase 5 held concessions disappear, concession boxes are cleared and never refilled. -- constrains `act.phase_check`

