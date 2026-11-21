# Contract: `backend/app/engine/bidding.py`

Generated mechanically from graph v2 by gen_contracts.py. Read COMMON.md first, then this file; BINDING.md lists the representation rules and the cross-module call matrix.

Import layering: this module is layer 6 (1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares and company_formation, 6 bidding, 7 round_manager). Calls to a HIGHER layer must be lazy imports inside the function body; never import upward at module level.

## 1. Export list (every name below, plus every alias, must exist at module level)

- `BidError` (exception)
- `FACE_VALUES` (constant)
- `BID_MULTIPLE` (constant)
- `MAX_BIDS_PER_TURN` (constant)
- `ITEM_KINDS` (constant)
- `face_value` (function)
- `highest_bid` (function)
- `highest_bidder` (function)
- `committed_money` (function)
- `items_led` (function)
- `tokens_total` (function)
- `tokens_used` (function)
- `min_legal_bid` (function)
- `bid_amount_error` (function)
- `bid_amount_valid` (function)
- `item_resolution_order` (function)
- `place_or_move_bid` (function)  aliases: place_bid, move_bid
- `shift_boxes` (function)
- `refill_boxes` (function)
- `clear_concession_boxes` (function)
- `vacate_box_item` (function)
- `resolve_bids` (function)
- `unsold_minor_exports` (function)
- `remove_box1_minor_and_export` (function)
- `resolve_stock_round` (function)

Public API count: 25

## 2. Module-level obligations

### States this module writes (flags and data it is responsible for)
- `st.bids` (Bids on box items): Bidding tokens on each item's track: at most one token per player per item (assumption A5). Amount = bid. Highest bid = max amount. Cleared at resolution (4.11.2). -- written by `act.place_bid`, `act.move_bid`, `act.resolve_bids`
- `st.box_contents` (Bid-box contents): Item sitting in each box: minor boxes 1..4, concession boxes 1..3, private boxes 1..3. -- written by `act.shift_boxes`, `act.refill_boxes`, `act.clear_concession_boxes`, `act.vacate_box_item`
- `st.concession_stack` (Concession stack): Remaining concessions; top goes to lowest empty concession box. LNWR on top at setup (1.7.4). Emptied at phase 5 (R9). -- written by `act.refill_boxes`, `act.clear_concession_boxes`
- `st.minor_stack` (Minor stack): Remaining minors; M24 on top at setup (1.7.5). -- written by `act.refill_boxes`
- `st.private_stack` (Private stack): Remaining privates; P1 on top at setup (1.7.6). -- written by `act.refill_boxes`
- `st.player_concessions` (Concessions held): Concession certificates a player holds (acquired after resolution, 4.7.5). Removed at phase 5 (R9). -- written by `act.clear_concession_boxes`, `act.vacate_box_item`
- `st.removed_items` (Items removed from play): Items removed from the game (unsold box-1 minor, concessions at phase 5). Audit only; consumed by operating rounds for minor-acquisition rules. -- written by `act.clear_concession_boxes`, `act.vacate_box_item`
- `st.player_privates` (Privates held): Private companies held by each player. -- written by `act.vacate_box_item`
- `st.minor_director` (Minor director's certificate holder): Player holding the 50% director's certificate of a minor (counts 1 certificate; assumption A6). Non-null = purchased and floated. -- written by `act.vacate_box_item`
- `st.private_status` (Private company ownership/closure): Who owns a private (player via Player.private_companies, company via PrivateCompanyState.owner_company_id) and whether it is closed; an open private pays its fixed revenue each OR (3.1.2). Players' side written by vacate_box_item; company acquisition and closing are out of scope (operating-round code). -- written by `act.vacate_box_item`
- `st.items_with_bids` (Items that had a bid): Snapshot taken by resolve_bids of every item on which any token was placed (including items nobody could pay, R8); passed to unsold_minor_exports (4.11.6). Local return value, not stored. -- written by `act.resolve_bids`
- `st.player_cash` (Player cash): Cash in hand of each player. Never negative. -- written by `act.resolve_bids`
- `st.bank_cash` (Bank cash): Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5). -- written by `act.resolve_bids`
- `st.sale_happened` (A sale happened flag): Set true when a player buys a share, sells a share, converts a concession (R15, R6), or wins a bid-box item at resolution (R6b). Reset at stock-round start. Read by the 10.1.1 first-round nothing-sold test (R6b). Written by the module functions themselves (idempotent; the caller actions.py also sets it after buy and convert). -- written by `act.resolve_bids`
- `st.pending_minor_floats` (Minors awaiting flotation): Minors paid for during resolve_bids, to be floated by float_minors in flotation order (4.11.3). Local return value, not stored. -- written by `act.resolve_bids`

### Hooks / triggers fired by this module's nodes
- `act.unsold_minor_exports` triggers `act.export_train` (`trains.export_train`)
- `act.remove_box1_minor_and_export` triggers `act.export_train` (`trains.export_train`)
- `act.resolve_stock_round` triggers `act.resolve_bids` (`bidding.resolve_bids`)
- `act.resolve_stock_round` triggers `act.float_minors` (`company_formation.float_minors`)
- `act.resolve_stock_round` triggers `act.unsold_minor_exports` (`bidding.unsold_minor_exports`)
- `act.resolve_stock_round` triggers `act.remove_box1_minor_and_export` (`bidding.remove_box1_minor_and_export`)
- `act.resolve_stock_round` triggers `act.refill_boxes` (`bidding.refill_boxes`)
- `act.resolve_stock_round` triggers `act.charge_interest` (`shares.charge_interest`)
- `act.resolve_stock_round` triggers `act.raise_sold_out_prices` (`turn_order.raise_sold_out_prices`)
- `act.resolve_stock_round` triggers `act.reorder_players_by_cash` (`turn_order.reorder_players_by_cash`)
- `act.resolve_stock_round` triggers `act.check_game_end_triggers` (`scoring.check_game_end_triggers`)

### Notes that name 'sets ... itself' / flags (from api notes)
- `BidError`: Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. Raised by place_or_move_bid, vacate_box_item.
- `FACE_VALUES`: const.face_values
- `BID_MULTIPLE`: const.bid_rules
- `MAX_BIDS_PER_TURN`: const.bid_rules
- `ITEM_KINDS`: Refill order and the kind order used as tie-break in item_resolution_order.
- `bid_amount_valid`: Kept for v1 compatibility; thin wrapper over bid_amount_error.
- `place_or_move_bid`: Branch: player_id in item.bids -> move, else place.
- `resolve_bids`: Sets any_sale_this_stock_round when at least one item is WON (R6b).

### Module-level decisions (resolve any api or node of this module)
- **GA38** (gap A.2.38, severity S3, kind decision): ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).
  reason: layering (no module for a shared base) and the given except clauses.
- **GA19** (gap A.2.19, severity S2, kind graph_fix): Three codes: ERR_BAD_AMOUNT (not an int multiple of 5), ERR_BID_TOO_LOW, ERR_INSUFFICIENT_CASH; derived bid_amount_error returns the code, bid_amount_valid = (error is None).
  reason: distinguishable errors.
- **GA18** (gap A.2.18, severity S2, kind graph_fix): One api function place_or_move_bid implements both actions; branch = player already has a token on the item; ERR_ALREADY_HAS_TOKEN and ERR_NO_TOKEN_ON_ITEM are removed from the graph.
  reason: given API.
- **GA21** (gap A.2.21, severity S3, kind graph_fix): Every api node lists its enforced preconditions in an ORDERED list (attrs.enforced, field n); the first failing check raises. Order = listed order; unknown ids first, then argument validity, then rule checks.
  reason: mechanical contracts need a total order.
- **DN10** (gap new, severity S2, kind decision): Every public function validates all preconditions before its first mutation; the given multi-bid loop in actions._apply_bid is not atomic and out of our control.
  reason: state must not be corrupted by a rejected call.
- **GA37** (gap A.2.37, severity S3, kind decision): resolve_stock_round and end_stock_round do NOT check sr_over or round_type; the round manager (actions._apply_pass) decides when. No ERR_NOT_OVER exists.
  reason: callable whenever the caller invokes it; avoids lazy cross-component import.
- **GA06** (gap A.1.6, severity S1, kind graph_fix): place_bid / move_bid do NOT write turn.bids_made; they read it (< 3). The caller (stock_turn_action = actions.py) increments it after each bid; begin_turn resets it.
  reason: avoids double counting.
- **GA34** (gap A.2.34, severity S3, kind carried): All remain as in GRAPH_NOTES v1 (copied into v2 notes). Owner-open and worth a ruling: A4 (opening bid 0), A5 (one token per item, leader cannot raise), A9 (batch sale priced before the drop), A15 (unpaid box-1 minor is still removed), A16 (payment order).  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: no new evidence.
- **GB12** (gap B-12, severity S2, kind graph_fix): See GA18.
  reason: GA18.
- **GA07** (gap A.1.7, severity S2, kind graph_fix): sell_shares, buy_share and convert_concession all set the flag themselves (idempotent); actions.py's extra write after buy/convert is documented as redundant; resolve_bids sets it when an item is won (R6b).
  reason: makes direct calls of module functions consistent; R15.
- **GA33** (gap A.2.33, severity S3, kind graph_fix): Ruling R6b adopted (provisional): nothing sold = no share bought/sold, no concession converted, no bid-box item won at resolution. resolve_bids sets sale_happened only for WON items; an item nobody can pay (R8) is not won.
  reason: task owner.
- **DN13** (gap new, severity S2, kind decision): An item that nobody can pay for (R8) stays in its box, counts as having had a bid for exports (A15) but is NOT won, so it does not set sale_happened (R6b).  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: R6b wording 'won'.
- **DN14** (gap new, severity S3, kind decision): Train exports at resolution never set sale_happened (A17 kept).
  reason: else the first-round rule could never fire.

## 3. API contracts

### `bidding.BidError` (exception)

```python
class BidError(Exception)
```

- bases: ['Exception']; message `<ERR_CODE>: <text>`; attribute `.code` = ERR_CODE
- raised by: bidding.face_value, bidding.place_or_move_bid, bidding.vacate_box_item
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 6
- given name (fixed by given code, never rename): YES
- aliases: none
- callers in given code: actions._apply_bid
- callers from graph (calls/triggers): none
- api notes: Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. Raised by place_or_move_bid, vacate_box_item.

**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA38** (gap A.2.38, severity S3, kind decision): ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).
  reason: layering (no module for a shared base) and the given except clauses.

### `bidding.FACE_VALUES` (constant)

```python
FACE_VALUES = {'concession': 100, 'minor': 100, 'private': 0}
```

- value: `{"concession": 100, "minor": 100, "private": 0}`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: const.face_values

### `bidding.BID_MULTIPLE` (constant)

```python
BID_MULTIPLE = 5
```

- value: `5`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: const.bid_rules

### `bidding.MAX_BIDS_PER_TURN` (constant)

```python
MAX_BIDS_PER_TURN = 3
```

- value: `3`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: const.bid_rules

### `bidding.ITEM_KINDS` (constant)

```python
ITEM_KINDS = ('minor', 'concession', 'private')
```

- value: `["minor", "concession", "private"]`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: Refill order and the kind order used as tie-break in item_resolution_order.

### `bidding.face_value` (function)

```python
face_value(kind: str) -> int
```

- parameters: ['kind']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.min_legal_bid

**Exceptions**:

| class | code | when |
|---|---|---|
| BidError | ERR_ITEM_NOT_IN_BOX | kind not in ITEM_KINDS |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. kind in ITEM_KINDS -> `ERR_ITEM_NOT_IN_BOX`

**Implements graph node(s)**: `drv.face_value`

#### Graph node `drv.face_value` (derived) - Face value of an item
Minimum opening bid for the item kind.

- graph signature (abstract): params = ['item']; returns = int

**Formula**: [3.4.2, 3.1.3, R1] concession 100; minor 100; private 0

**Constants used**:
- `const.face_values` (Face values): Face value: concession 100 (3.4.2), minor 100 (R1), private 0 (3.1.3). Opening bid >= face value (4.10.6).; data: `{"table": {"concession": 100, "minor": 100, "private": 0}}`

**Rules constraining this node**:
- R1: Minor face value = 100 (rulebook states none). [formula]
- 3.1.3: Face value of privates is 0. [formula]
- 3.4.2: Concessions bought through bid boxes; face value 100. [formula]


### `bidding.highest_bid` (function)

```python
highest_bid(item: BidBoxItem) -> int | None
```

- parameters: ['item']
- defaults (explicit): (none)
- returns: max(item.bids.values()) or None (a bid of 0 is a bid)
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.committed_money, bidding.item_resolution_order, bidding.min_legal_bid

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.highest_bid`

#### Graph node `drv.highest_bid` (derived) - Highest bid
Highest bid placed on an item.

- graph signature (abstract): params = ['item']; returns = int|null

**Formula**: [4.10.7] max over bids[item].values(), or none

**State touched**:
- reads `st.bids` (Bids on box items): Bidding tokens on each item's track: at most one token per player per item (assumption A5). Amount = bid. Highest bid = max amount. Cleared at resolution (4.11.2). [type map item->map player->amount; unit pounds (multiple of 5); scope per item]

**Rules constraining this node**:
- 4.10.7: Bid must exceed prior bids and keep committed money <= cash. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Bids and bidding tokens** [repr.bids]: maps to: BidBoxItem.bids: dict[player_id, int] (one entry = one token on the item's track)
  rule for coder: highest_bid = max(bids.values()) if bids else None; a bid of 0 is a bid (never `if highest_bid:`). Tokens in use = items with the player in bids. Empty dict = no bid.


### `bidding.highest_bidder` (function)

```python
highest_bidder(item: BidBoxItem) -> str | None
```

- parameters: ['item']
- defaults (explicit): (none)
- returns: argmax of item.bids or None
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.committed_money, bidding.items_led, bidding.place_or_move_bid

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.highest_bidder`

#### Graph node `drv.highest_bidder` (derived) - Highest bidder
Player with the highest bid on an item.

- graph signature (abstract): params = ['item']; returns = player|null

**Formula**: [4.10.7] argmax of bids[item]; unique because every new bid must be higher

**State touched**:
- reads `st.bids` (Bids on box items): Bidding tokens on each item's track: at most one token per player per item (assumption A5). Amount = bid. Highest bid = max amount. Cleared at resolution (4.11.2). [type map item->map player->amount; unit pounds (multiple of 5); scope per item]

**Rules constraining this node**:
- 4.10.7: Bid must exceed prior bids and keep committed money <= cash. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Bids and bidding tokens** [repr.bids]: maps to: BidBoxItem.bids: dict[player_id, int] (one entry = one token on the item's track)
  rule for coder: highest_bid = max(bids.values()) if bids else None; a bid of 0 is a bid (never `if highest_bid:`). Tokens in use = items with the player in bids. Empty dict = no bid.


### `bidding.committed_money` (function)

```python
committed_money(state: GameState, player_id: str) -> int
```

- parameters: ['state', 'player_id']
- defaults (explicit): (none)
- returns: sum of highest bids on items the player leads
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.bid_amount_error, bidding.bid_amount_valid

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.committed_money`

#### Graph node `drv.committed_money` (derived) - Committed money
Money a player is committed to pay for items they lead.

- graph signature (abstract): params = ['player p']; returns = int

**Formula**: [4.10.7] sum of highest_bid(item) over items with highest_bidder(item)==p; outbid items do not count

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.highest_bid -> `bidding.highest_bid` [same module] signature: `highest_bid(item: BidBoxItem) -> int | None` 
- calls drv.highest_bidder -> `bidding.highest_bidder` [same module] signature: `highest_bidder(item: BidBoxItem) -> str | None` 

**State touched**:
- reads `st.bids` (Bids on box items): Bidding tokens on each item's track: at most one token per player per item (assumption A5). Amount = bid. Highest bid = max amount. Cleared at resolution (4.11.2). [type map item->map player->amount; unit pounds (multiple of 5); scope per item]

**Rules constraining this node**:
- 4.10.7: Bid must exceed prior bids and keep committed money <= cash. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Bids and bidding tokens** [repr.bids]: maps to: BidBoxItem.bids: dict[player_id, int] (one entry = one token on the item's track)
  rule for coder: highest_bid = max(bids.values()) if bids else None; a bid of 0 is a bid (never `if highest_bid:`). Tokens in use = items with the player in bids. Empty dict = no bid.


### `bidding.items_led` (function)

```python
items_led(state: GameState, player_id: str) -> int
```

- parameters: ['state', 'player_id']
- defaults (explicit): (none)
- returns: count of items the player leads
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): certificates.cert_count

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.items_led`

#### Graph node `drv.items_led` (derived) - Items led
Number of items on which the player has the highest bid.

- graph signature (abstract): params = ['player p']; returns = int

**Formula**: [4.2.5] count of items with highest_bidder(item)==p

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.highest_bidder -> `bidding.highest_bidder` [same module] signature: `highest_bidder(item: BidBoxItem) -> str | None` 

**State touched**:
- reads `st.bids` (Bids on box items): Bidding tokens on each item's track: at most one token per player per item (assumption A5). Amount = bid. Highest bid = max amount. Cleared at resolution (4.11.2). [type map item->map player->amount; unit pounds (multiple of 5); scope per item]

**Rules constraining this node**:
- 4.2.5: At the limit a player may not bid; each item on which they hold the highest bid counts as a certificate. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Bids and bidding tokens** [repr.bids]: maps to: BidBoxItem.bids: dict[player_id, int] (one entry = one token on the item's track)
  rule for coder: highest_bid = max(bids.values()) if bids else None; a bid of 0 is a bid (never `if highest_bid:`). Tokens in use = items with the player in bids. Empty dict = no bid.


### `bidding.tokens_total` (function)

```python
tokens_total(state: GameState) -> int
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: SETUP_BY_PLAYER_COUNT[n].bidding_tokens
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.place_or_move_bid

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.tokens_total`

#### Graph node `drv.tokens_total` (derived) - Bidding tokens per player
Tokens each player has.

- graph signature (abstract): params = ['none']; returns = int

**Formula**: [4.10.3, 1.7.2] const.bidding_tokens[player_count] (6/5/4/3/3)

**State touched**:
- reads `st.player_count` (Player count): Number of players n; set once at setup. [type int 3..7; unit players; scope game]

**Constants used**:
- `const.bidding_tokens` (Bidding tokens per player count): Bidding tokens per player by player count (1.7.2, 4.10.3); values from the given data table.; data: `{"table": {"3": 6, "4": 5, "5": 4, "6": 3, "7": 3}}`
  (in code: app.data.setup.SETUP_BY_PLAYER_COUNT[n].bidding_tokens)

**Rules constraining this node**:
- 1.7.2: Bank 12000 incl. start money 2100/n; bidding tokens and cert limit by player count. [formula]
- 4.10.3: Number of tokens by player count = max items a player may bid on. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Stock-turn order** [repr.sr_order]: maps to: state.player_order (list, index 0 = Player-1 card) AND state.priority_deal_player_id
  rule for coder: player_count = len(state.player_order) (3..7; no stored field). Invariant: priority_deal_player_id == player_order[0]. Writers of player_order (reorder_players_by_cash, setup) rewrite priority_deal_player_id too; start_stock_round re-asserts it.


### `bidding.tokens_used` (function)

```python
tokens_used(state: GameState, player_id: str) -> int
```

- parameters: ['state', 'player_id']
- defaults (explicit): (none)
- returns: items with the player in bids
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.place_or_move_bid

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.tokens_used`

#### Graph node `drv.tokens_used` (derived) - Tokens in use
Tokens a player currently has on items, led or outbid.

- graph signature (abstract): params = ['player p']; returns = int

**Formula**: [4.10.10] count of items with p in bids[item] (tokens stay until resolution)

**State touched**:
- reads `st.bids` (Bids on box items): Bidding tokens on each item's track: at most one token per player per item (assumption A5). Amount = bid. Highest bid = max amount. Cleared at resolution (4.11.2). [type map item->map player->amount; unit pounds (multiple of 5); scope per item]

**Rules constraining this node**:
- 4.10.10: A bid cannot be withdrawn or moved to another item. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Bids and bidding tokens** [repr.bids]: maps to: BidBoxItem.bids: dict[player_id, int] (one entry = one token on the item's track)
  rule for coder: highest_bid = max(bids.values()) if bids else None; a bid of 0 is a bid (never `if highest_bid:`). Tokens in use = items with the player in bids. Empty dict = no bid.


### `bidding.min_legal_bid` (function)

```python
min_legal_bid(item: BidBoxItem) -> int
```

- parameters: ['item']
- defaults (explicit): (none)
- returns: face value if no bids else highest + 5
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.bid_amount_error, bidding.bid_amount_valid

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.min_legal_bid`

#### Graph node `drv.min_legal_bid` (derived) - Minimum legal bid
Smallest bid currently legal on an item.

- graph signature (abstract): params = ['item']; returns = int

**Formula**: [4.10.6, 4.10.7, R1] face_value(item) if no bids else highest_bid(item)+5

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.face_value -> `bidding.face_value` [same module] signature: `face_value(kind: str) -> int` 
- calls drv.highest_bid -> `bidding.highest_bid` [same module] signature: `highest_bid(item: BidBoxItem) -> int | None` 

**Rules constraining this node**:
- R1: Minor face value = 100 (rulebook states none). [formula]
- 4.10.6: Opening bid >= face value; whole multiples of 5. [formula]
- 4.10.7: Bid must exceed prior bids and keep committed money <= cash. [formula]


### `bidding.bid_amount_error` (function)

```python
bid_amount_error(state: GameState, player_id: str, item: BidBoxItem, amount: int) -> str | None
```

- parameters: ['state', 'player_id', 'item', 'amount']
- defaults (explicit): (none)
- returns: ERR_BAD_AMOUNT | ERR_BID_TOO_LOW | ERR_INSUFFICIENT_CASH | None
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.place_or_move_bid

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- returns a code, never raises

**Implements graph node(s)**: `drv.bid_amount_error`

#### Graph node `drv.bid_amount_error` (derived) - Why is a bid amount invalid?
The error code of the first failing amount check, or none (GAP A19 fixed: three separate codes).

- graph signature (abstract): params = ['player p', 'item', 'amount']; returns = error code|null

**Formula**: [4.10.6, 4.10.7] amount not an int or amount % 5 != 0 -> ERR_BAD_AMOUNT; amount < min_legal_bid(item) -> ERR_BID_TOO_LOW; committed_money(p) + amount > player_cash[p] -> ERR_INSUFFICIENT_CASH; else none. bid_amount_valid = (bid_amount_error is none)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.min_legal_bid -> `bidding.min_legal_bid` [same module] signature: `min_legal_bid(item: BidBoxItem) -> int` 
- calls drv.committed_money -> `bidding.committed_money` [same module] signature: `committed_money(state: GameState, player_id: str) -> int` 

**State touched**:
- reads `st.player_cash` (Player cash): Cash in hand of each player. Never negative. [type int map player->int; unit pounds (integer); scope per player]

**Constants used**:
- `const.bid_rules` (Bid rule numbers): Bids are whole multiples of 5 (4.10.6); at most 3 bids placed/moved per stock turn (4.10.5); no upper bound on a bid (4.10.9).; data: `{"multiple": 5, "max_bids_per_turn": 3}`

**Rules constraining this node**:
- 4.10.6: Opening bid >= face value; whole multiples of 5. [formula]
- 4.10.7: Bid must exceed prior bids and keep committed money <= cash. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA19** (gap A.2.19, severity S2, kind graph_fix): Three codes: ERR_BAD_AMOUNT (not an int multiple of 5), ERR_BID_TOO_LOW, ERR_INSUFFICIENT_CASH; derived bid_amount_error returns the code, bid_amount_valid = (error is None).
  reason: distinguishable errors.

### `bidding.bid_amount_valid` (function)

```python
bid_amount_valid(state: GameState, player_id: str, item: BidBoxItem, amount: int) -> bool
```

- parameters: ['state', 'player_id', 'item', 'amount']
- defaults (explicit): (none)
- returns: bid_amount_error(...) is None
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: Kept for v1 compatibility; thin wrapper over bid_amount_error.

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.bid_amount_valid`

#### Graph node `drv.bid_amount_valid` (derived) - Is the bid amount valid?
All amount-related checks shared by place_bid and move_bid.

- graph signature (abstract): params = ['player p', 'item', 'amount']; returns = bool

**Formula**: [4.10.6, 4.10.7, 4.10.9] amount % 5 == 0 and amount >= min_legal_bid(item) and committed_money(p) + amount <= player_cash[p] (p does not currently lead the item, so it is not double counted); no upper bound

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.min_legal_bid -> `bidding.min_legal_bid` [same module] signature: `min_legal_bid(item: BidBoxItem) -> int` 
- calls drv.committed_money -> `bidding.committed_money` [same module] signature: `committed_money(state: GameState, player_id: str) -> int` 

**State touched**:
- reads `st.player_cash` (Player cash): Cash in hand of each player. Never negative. [type int map player->int; unit pounds (integer); scope per player]

**Constants used**:
- `const.bid_rules` (Bid rule numbers): Bids are whole multiples of 5 (4.10.6); at most 3 bids placed/moved per stock turn (4.10.5); no upper bound on a bid (4.10.9).; data: `{"multiple": 5, "max_bids_per_turn": 3}`

**Rules constraining this node**:
- 4.10.6: Opening bid >= face value; whole multiples of 5. [formula]
- 4.10.7: Bid must exceed prior bids and keep committed money <= cash. [formula]
- 4.10.9: Any bid >= 100 over face is allowed (physical chip only). [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA19** (gap A.2.19, severity S2, kind graph_fix): Three codes: ERR_BAD_AMOUNT (not an int multiple of 5), ERR_BID_TOO_LOW, ERR_INSUFFICIENT_CASH; derived bid_amount_error returns the code, bid_amount_valid = (error is None).
  reason: distinguishable errors.

### `bidding.item_resolution_order` (function)

```python
item_resolution_order(state: GameState) -> list[tuple[str, int]]
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (kind, box_index) of items with bids by (highest bid desc, box_index asc, kind order minor<concession<private)
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.resolve_bids

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.item_resolution_order`

#### Graph node `drv.item_resolution_order` (derived) - Item payment order
Order in which items with bids are paid for.

- graph signature (abstract): params = ['none']; returns = list<item>

**Formula**: [4.11.2] items with >=1 bid sorted by (highest bid desc, box number asc, kind order minor<concession<private) -- assumption A16

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.highest_bid -> `bidding.highest_bid` [same module] signature: `highest_bid(item: BidBoxItem) -> int | None` 

**State touched**:
- reads `st.bids` (Bids on box items): Bidding tokens on each item's track: at most one token per player per item (assumption A5). Amount = bid. Highest bid = max amount. Cleared at resolution (4.11.2). [type map item->map player->amount; unit pounds (multiple of 5); scope per item]
- reads `st.box_contents` (Bid-box contents): Item sitting in each box: minor boxes 1..4, concession boxes 1..3, private boxes 1..3. [type map (kind, box_no)->item|null; unit items; scope game]

**Rules constraining this node**:
- 4.11.2: Highest bidders pay and take items; tokens are removed. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Bids and bidding tokens** [repr.bids]: maps to: BidBoxItem.bids: dict[player_id, int] (one entry = one token on the item's track)
  rule for coder: highest_bid = max(bids.values()) if bids else None; a bid of 0 is a bid (never `if highest_bid:`). Tokens in use = items with the player in bids. Empty dict = no bid.
- **Bid boxes** [repr.boxes_zero_based]: maps to: state.concession_bid_boxes (len 3), state.minor_bid_boxes (len 4), state.private_bid_boxes (len 3): elements BidBoxItem | None, lists keep their length (None padding)
  rule for coder: Graph 'box number' = list index + 1 ('box 1' = index 0; 'lower box number wins' = lower index). An item's identity in function signatures is (kind, box_index). Box counts: engine.setup.NUM_*_BID_BOXES.
- **Item sitting in a box** [repr.bid_box_item]: maps to: BidBoxItem(kind, ref, bids): ref is str (abbr) for concession, int for minor and private (the int annotation in models.py is wrong for concessions)
  rule for coder: state.minors key = f'M{ref}'.


### `bidding.place_or_move_bid` (function)

```python
place_or_move_bid(state: GameState, player_id: str, kind: str, box_index: int, amount: int) -> None
```

- parameters: ['state', 'player_id', 'kind', 'box_index', 'amount']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 6
- given name (fixed by given code, never rename): YES
- **aliases that MUST also be exported** (same object / same behaviour): `place_bid`, `move_bid`
- callers in given code: actions._apply_bid
- callers from graph (calls/triggers): none
- api notes: Branch: player_id in item.bids -> move, else place.

**Exceptions**:

| class | code | when |
|---|---|---|
| BidError | ERR_ITEM_NOT_IN_BOX | kind/box invalid, empty box, or concession while phase >= 5 |
| BidError | ERR_TOO_MANY_BIDS | bids_this_turn >= 3 |
| BidError | ERR_LOANS | player has loans |
| BidError | ERR_MUST_SELL | must_sell |
| BidError | ERR_CERT_LIMIT | cert_count >= limit |
| BidError | ERR_BAD_AMOUNT | not an int multiple of 5 |
| BidError | ERR_BID_TOO_LOW | below min_legal_bid |
| BidError | ERR_INSUFFICIENT_CASH | committed + amount > cash |
| BidError | ERR_NO_TOKENS | place branch: no unallocated token |
| BidError | ERR_NOT_OUTBID | move branch: the player already leads |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. kind in ITEM_KINDS, 0 <= box_index < len(boxes), box not None, concession only if phase < 5 -> `ERR_ITEM_NOT_IN_BOX`
2. state.bids_this_turn < 3 (READ ONLY) -> `ERR_TOO_MANY_BIDS`
3. player.loans == 0 -> `ERR_LOANS`
4. not must_sell -> `ERR_MUST_SELL`
5. cert_count < cert_limit -> `ERR_CERT_LIMIT`
6. bid_amount_error is None (int, not bool; multiple of 5) -> `ERR_BAD_AMOUNT / ERR_BID_TOO_LOW / ERR_INSUFFICIENT_CASH`
7. place (player not in item.bids): tokens_used < tokens_total -> `ERR_NO_TOKENS`
8. move (player in item.bids): player is not the highest bidder -> `ERR_NOT_OUTBID`

**Must NOT be checked by this function**:
- round type / active player (actions.py)
- never writes bids_this_turn (the caller increments it)
- no atomicity across the 3 bids of one action (the caller loops)

**Implements graph node(s)**: `act.place_bid`, `act.move_bid`

#### Graph node `act.place_bid` (action) - Place a bid
Put an unallocated bidding token on an item at a new bid value. The given API merges place and move into one function: a player with no token on the item takes this branch.

- graph signature (abstract): params = ['player', 'item', 'amount']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [R9] kind in {minor, concession, private} and the box exists and holds an item; concession items only while phase < 5
- [4.10.5] turn.bids_made < 3 (READ ONLY: the caller increments it after each successful bid, never this module)
- [4.3.1] player_loans[player] = 0
- [R10] not must_sell(player)
- [4.10.8] cert_count(player) < cert_limit (leading bids count; applies to privates too)
- [4.10.6] bid_amount_error(player,item,amount) is none: amount an int multiple of 5 (ERR_BAD_AMOUNT), >= min_legal_bid (ERR_BID_TOO_LOW), committed + amount <= cash (ERR_INSUFFICIENT_CASH)
- [4.10.3] tokens_used(player) < tokens_total
- [4.10.4] player has NO token on this item (otherwise the move branch applies; one token per player per item; assumption A5)
- [3.1.4] items are obtainable only by bidding

**Effects, in order** (execute exactly in this order):
1. [4.10.4] bids[item][player] = amount
2. [4.10.5] bids_made is NOT written here (caller actions.py increments it)
3. [4.2.5] the player now counts one more certificate (leading bid)

**Errors listed by the graph node**:
- ERR_ITEM_NOT_IN_BOX
- ERR_TOO_MANY_BIDS
- ERR_LOANS
- ERR_MUST_SELL
- ERR_CERT_LIMIT
- ERR_BAD_AMOUNT
- ERR_BID_TOO_LOW
- ERR_INSUFFICIENT_CASH
- ERR_NO_TOKENS

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.must_sell -> `certificates.must_sell` [CROSS-MODULE] signature: `must_sell(state: GameState, player_id: str) -> bool` 
- calls drv.cert_count -> `certificates.cert_count` [CROSS-MODULE] signature: `cert_count(state: GameState, player_id: str) -> int` 
- calls drv.cert_limit -> `certificates.cert_limit` [CROSS-MODULE] signature: `cert_limit(state: GameState) -> int` 
- calls drv.bid_amount_error -> `bidding.bid_amount_error` [same module] signature: `bid_amount_error(state: GameState, player_id: str, item: BidBoxItem, amount: int) -> str | None` 
- calls drv.tokens_used -> `bidding.tokens_used` [same module] signature: `tokens_used(state: GameState, player_id: str) -> int` 
- calls drv.tokens_total -> `bidding.tokens_total` [same module] signature: `tokens_total(state: GameState) -> int` 

**State touched**:
- reads `st.turn` (Active turn record): Whose stock turn it is and how many bids were already placed/moved in this turn. v2 follows the skeleton turn model: EVERY successful sell / buy / convert / bid action ends the turn; there is no stage, no c_used, no acted. bids_made is incremented by the CALLER (actions.py), never by the bidding module, and reset by begin_turn. [type record {active_player, bids_made}; unit -; scope game]
- reads `st.player_loans` (Player loans): Outstanding loans of each player. Created by operating-round forced train purchase / emergency money raising (out of scope); reduced by repay_loans; increased by interest. [type int map player->int; unit pounds; scope per player]
- reads `st.box_contents` (Bid-box contents): Item sitting in each box: minor boxes 1..4, concession boxes 1..3, private boxes 1..3. [type map (kind, box_no)->item|null; unit items; scope game]
- reads `st.phase` (Game phase): Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1). [type int 1..7; unit phase number; scope game]
- reads `st.bids` (Bids on box items): Bidding tokens on each item's track: at most one token per player per item (assumption A5). Amount = bid. Highest bid = max amount. Cleared at resolution (4.11.2). [type map item->map player->amount; unit pounds (multiple of 5); scope per item]
- writes `st.bids` (Bids on box items): Bidding tokens on each item's track: at most one token per player per item (assumption A5). Amount = bid. Highest bid = max amount. Cleared at resolution (4.11.2). [type map item->map player->amount; unit pounds (multiple of 5); scope per item]

**Rules constraining this node**:
- 4.10.8: No placing/moving at the limit; leading bids count. [demanded in preconditions/effects]
- 4.2.5: At the limit a player may not bid; each item on which they hold the highest bid counts as a certificate. [demanded in preconditions/effects]
- R9: From phase 5 held concessions disappear, concession boxes are cleared and never refilled. [demanded in preconditions/effects]
- 4.10.5: Up to three bids placed/moved per turn. [demanded in preconditions/effects]
- 4.3.1: No buying, converting or bidding while in debt. [demanded in preconditions/effects]
- 3.1.4: A private can only be bought through the bidding mechanism. [demanded in preconditions/effects]
- 4.10.6: Opening bid >= face value; whole multiples of 5. [demanded in preconditions/effects]
- 4.10.3: Number of tokens by player count = max items a player may bid on. [demanded in preconditions/effects]
- R10: Over the limit must sell down at first opportunity; while over and able to sell the player may not buy or bid. [demanded in preconditions/effects]
- 4.10.4: Place an unallocated token on an empty space, or move a token up on the same item only if another player has a higher bid. [demanded in preconditions/effects]
- 3.2.4: Players can only buy minors through bidding.
- 3.4.2: Concessions bought through bid boxes; face value 100.
- 4.1.4: One of: buy one share, convert, place/increase up to 3 bids; round ends when all pass consecutively.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Stock round start / priority player** [repr.sr_start_player]: maps to: state.active_player_id = player_order[0] at the start of every stock round
  rule for coder: Round 1: set by setup.new_game (the first stock round is pre-started, start_stock_round is not called). Later rounds: start_stock_round -> begin_turn(player_order[0]). Order of play inside a round: next_player(state, pid) = player_order[(index+1) % n]; bids_this_turn reset by begin_turn.
- **Turn record** [repr.turn_record]: maps to: state.active_player_id (turn.active_player) and state.bids_this_turn (turn.bids_made); NO fields for stage / c_used / acted (dropped in v2)
  rule for coder: SKELETON TURN MODEL: every successful sell_shares / buy_share / convert_concession / bid action ends the turn (actions.py calls advance_stock_player). bids_this_turn is incremented by actions.py after each place_or_move_bid and reset by begin_turn; the bidding module only READS it.
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.
- **Bid boxes** [repr.boxes_zero_based]: maps to: state.concession_bid_boxes (len 3), state.minor_bid_boxes (len 4), state.private_bid_boxes (len 3): elements BidBoxItem | None, lists keep their length (None padding)
  rule for coder: Graph 'box number' = list index + 1 ('box 1' = index 0; 'lower box number wins' = lower index). An item's identity in function signatures is (kind, box_index). Box counts: engine.setup.NUM_*_BID_BOXES.
- **Item sitting in a box** [repr.bid_box_item]: maps to: BidBoxItem(kind, ref, bids): ref is str (abbr) for concession, int for minor and private (the int annotation in models.py is wrong for concessions)
  rule for coder: state.minors key = f'M{ref}'.
- **Phase** [repr.phase_state]: maps to: state.phase: int 1..7; limits and rust from app.data.phases.PHASES_BY_NUMBER; trigger table trains.TRAIN_PHASE (module constant)
  rule for coder: phase only increases (2.2.1) and is written only by phase_check (plus debug code in main.py). PHASES_BY_NUMBER[n].trains_rusted gives ONE code per phase; skipped phases are rusted too (loop old+1..new).
- **Bids and bidding tokens** [repr.bids]: maps to: BidBoxItem.bids: dict[player_id, int] (one entry = one token on the item's track)
  rule for coder: highest_bid = max(bids.values()) if bids else None; a bid of 0 is a bid (never `if highest_bid:`). Tokens in use = items with the player in bids. Empty dict = no bid.

#### Graph node `act.move_bid` (action) - Move a bid up
Move an already placed token to a higher space on the same item (same API function as place_bid: branch = the player already has a token on the item).

- graph signature (abstract): params = ['player', 'item', 'new_amount']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [R9] kind in {minor, concession, private} and the box exists and holds an item; concession items only while phase < 5
- [4.10.5] turn.bids_made < 3 (READ ONLY: the caller increments it after each successful bid, never this module)
- [4.3.1] player_loans[player] = 0
- [R10] not must_sell(player)
- [4.10.8] cert_count(player) < cert_limit (leading bids count; applies to privates too)
- [4.10.6] bid_amount_error(player,item,amount) is none: amount an int multiple of 5 (ERR_BAD_AMOUNT), >= min_legal_bid (ERR_BID_TOO_LOW), committed + amount <= cash (ERR_INSUFFICIENT_CASH)
- [4.10.4] the player already has a token on the item and is NOT the highest bidder (another player has a higher bid)
- [4.10.10] a token cannot be withdrawn or moved to another item

**Effects, in order** (execute exactly in this order):
1. [4.10.4] bids[item][player] = new_amount (the token moves; the old space becomes empty)
2. [4.10.5] bids_made is NOT written here (caller)
3. the player now leads the item: committed money and certificate count rise

**Errors listed by the graph node**:
- ERR_ITEM_NOT_IN_BOX
- ERR_TOO_MANY_BIDS
- ERR_NOT_OUTBID
- ERR_LOANS
- ERR_MUST_SELL
- ERR_CERT_LIMIT
- ERR_BAD_AMOUNT
- ERR_BID_TOO_LOW
- ERR_INSUFFICIENT_CASH

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.must_sell -> `certificates.must_sell` [CROSS-MODULE] signature: `must_sell(state: GameState, player_id: str) -> bool` 
- calls drv.cert_count -> `certificates.cert_count` [CROSS-MODULE] signature: `cert_count(state: GameState, player_id: str) -> int` 
- calls drv.cert_limit -> `certificates.cert_limit` [CROSS-MODULE] signature: `cert_limit(state: GameState) -> int` 
- calls drv.bid_amount_error -> `bidding.bid_amount_error` [same module] signature: `bid_amount_error(state: GameState, player_id: str, item: BidBoxItem, amount: int) -> str | None` 
- calls drv.highest_bidder -> `bidding.highest_bidder` [same module] signature: `highest_bidder(item: BidBoxItem) -> str | None` 

**State touched**:
- reads `st.turn` (Active turn record): Whose stock turn it is and how many bids were already placed/moved in this turn. v2 follows the skeleton turn model: EVERY successful sell / buy / convert / bid action ends the turn; there is no stage, no c_used, no acted. bids_made is incremented by the CALLER (actions.py), never by the bidding module, and reset by begin_turn. [type record {active_player, bids_made}; unit -; scope game]
- reads `st.player_loans` (Player loans): Outstanding loans of each player. Created by operating-round forced train purchase / emergency money raising (out of scope); reduced by repay_loans; increased by interest. [type int map player->int; unit pounds; scope per player]
- reads `st.box_contents` (Bid-box contents): Item sitting in each box: minor boxes 1..4, concession boxes 1..3, private boxes 1..3. [type map (kind, box_no)->item|null; unit items; scope game]
- reads `st.phase` (Game phase): Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1). [type int 1..7; unit phase number; scope game]
- reads `st.bids` (Bids on box items): Bidding tokens on each item's track: at most one token per player per item (assumption A5). Amount = bid. Highest bid = max amount. Cleared at resolution (4.11.2). [type map item->map player->amount; unit pounds (multiple of 5); scope per item]
- writes `st.bids` (Bids on box items): Bidding tokens on each item's track: at most one token per player per item (assumption A5). Amount = bid. Highest bid = max amount. Cleared at resolution (4.11.2). [type map item->map player->amount; unit pounds (multiple of 5); scope per item]

**Rules constraining this node**:
- 4.10.8: No placing/moving at the limit; leading bids count. [demanded in preconditions/effects]
- R9: From phase 5 held concessions disappear, concession boxes are cleared and never refilled. [demanded in preconditions/effects]
- 4.10.10: A bid cannot be withdrawn or moved to another item. [demanded in preconditions/effects]
- 4.10.5: Up to three bids placed/moved per turn. [demanded in preconditions/effects]
- 4.3.1: No buying, converting or bidding while in debt. [demanded in preconditions/effects]
- 4.10.6: Opening bid >= face value; whole multiples of 5. [demanded in preconditions/effects]
- R10: Over the limit must sell down at first opportunity; while over and able to sell the player may not buy or bid. [demanded in preconditions/effects]
- 4.10.4: Place an unallocated token on an empty space, or move a token up on the same item only if another player has a higher bid. [demanded in preconditions/effects]
- 4.1.4: One of: buy one share, convert, place/increase up to 3 bids; round ends when all pass consecutively.
- 4.2.5: At the limit a player may not bid; each item on which they hold the highest bid counts as a certificate.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Stock round start / priority player** [repr.sr_start_player]: maps to: state.active_player_id = player_order[0] at the start of every stock round
  rule for coder: Round 1: set by setup.new_game (the first stock round is pre-started, start_stock_round is not called). Later rounds: start_stock_round -> begin_turn(player_order[0]). Order of play inside a round: next_player(state, pid) = player_order[(index+1) % n]; bids_this_turn reset by begin_turn.
- **Turn record** [repr.turn_record]: maps to: state.active_player_id (turn.active_player) and state.bids_this_turn (turn.bids_made); NO fields for stage / c_used / acted (dropped in v2)
  rule for coder: SKELETON TURN MODEL: every successful sell_shares / buy_share / convert_concession / bid action ends the turn (actions.py calls advance_stock_player). bids_this_turn is incremented by actions.py after each place_or_move_bid and reset by begin_turn; the bidding module only READS it.
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.
- **Bid boxes** [repr.boxes_zero_based]: maps to: state.concession_bid_boxes (len 3), state.minor_bid_boxes (len 4), state.private_bid_boxes (len 3): elements BidBoxItem | None, lists keep their length (None padding)
  rule for coder: Graph 'box number' = list index + 1 ('box 1' = index 0; 'lower box number wins' = lower index). An item's identity in function signatures is (kind, box_index). Box counts: engine.setup.NUM_*_BID_BOXES.
- **Item sitting in a box** [repr.bid_box_item]: maps to: BidBoxItem(kind, ref, bids): ref is str (abbr) for concession, int for minor and private (the int annotation in models.py is wrong for concessions)
  rule for coder: state.minors key = f'M{ref}'.
- **Phase** [repr.phase_state]: maps to: state.phase: int 1..7; limits and rust from app.data.phases.PHASES_BY_NUMBER; trigger table trains.TRAIN_PHASE (module constant)
  rule for coder: phase only increases (2.2.1) and is written only by phase_check (plus debug code in main.py). PHASES_BY_NUMBER[n].trains_rusted gives ONE code per phase; skipped phases are rusted too (loop old+1..new).
- **Bids and bidding tokens** [repr.bids]: maps to: BidBoxItem.bids: dict[player_id, int] (one entry = one token on the item's track)
  rule for coder: highest_bid = max(bids.values()) if bids else None; a bid of 0 is a bid (never `if highest_bid:`). Tokens in use = items with the player in bids. Empty dict = no bid.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA06** (gap A.1.6, severity S1, kind graph_fix): place_bid / move_bid do NOT write turn.bids_made; they read it (< 3). The caller (stock_turn_action = actions.py) increments it after each bid; begin_turn resets it.
  reason: avoids double counting.
- **GA18** (gap A.2.18, severity S2, kind graph_fix): One api function place_or_move_bid implements both actions; branch = player already has a token on the item; ERR_ALREADY_HAS_TOKEN and ERR_NO_TOKEN_ON_ITEM are removed from the graph.
  reason: given API.
- **GA34** (gap A.2.34, severity S3, kind carried): All remain as in GRAPH_NOTES v1 (copied into v2 notes). Owner-open and worth a ruling: A4 (opening bid 0), A5 (one token per item, leader cannot raise), A9 (batch sale priced before the drop), A15 (unpaid box-1 minor is still removed), A16 (payment order).  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: no new evidence.
- **GB12** (gap B-12, severity S2, kind graph_fix): See GA18.
  reason: GA18.
- **GA01** (gap A.1.1, severity S1, kind graph_fix): Follow the skeleton: every successful sell / buy / convert / bid action ends the turn. turn.stage, turn.c_used, turn.acted and the errors ERR_WRONG_STAGE / ERR_C_ALREADY_USED / ERR_NO_ACTION_TAKEN are removed; the order edges sell->repay->C are removed; repay_loans stays as an unwired action (wired=false, implemented and exported); a new given action stock_turn_action models actions.py (calls ONE module function, increments bids_this_turn, resets pass_streak, calls end_turn).
  reason: actions.py is given and its docstring says the combination is 'not wired up yet'; a literal v1 implementation would have vacuous preconditions.
- **GA21** (gap A.2.21, severity S3, kind graph_fix): Every api node lists its enforced preconditions in an ORDERED list (attrs.enforced, field n); the first failing check raises. Order = listed order; unknown ids first, then argument validity, then rule checks.
  reason: mechanical contracts need a total order.
- **DN10** (gap new, severity S2, kind decision): Every public function validates all preconditions before its first mutation; the given multi-bid loop in actions._apply_bid is not atomic and out of our control.
  reason: state must not be corrupted by a rejected call.

### `bidding.shift_boxes` (function)

```python
shift_boxes(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.refill_boxes

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception

**Implements graph node(s)**: `act.shift_boxes`

#### Graph node `act.shift_boxes` (action) - Compact boxes
Shift items to the lowest-numbered boxes of their kind, preserving order.

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.10.2] applies to every kind separately

**Effects, in order** (execute exactly in this order):
1. [4.10.2, 4.11.8] for each kind: items in boxes 1..m moved to the lowest-numbered boxes in the same relative order

**Errors listed by the graph node**:
- NONE for legal input: total function when called in the documented order; ERR_ORDER if invoked out of sequence (e.g. outside resolve_stock_round)

**State touched**:
- reads `st.box_contents` (Bid-box contents): Item sitting in each box: minor boxes 1..4, concession boxes 1..3, private boxes 1..3. [type map (kind, box_no)->item|null; unit items; scope game]
- writes `st.box_contents` (Bid-box contents): Item sitting in each box: minor boxes 1..4, concession boxes 1..3, private boxes 1..3. [type map (kind, box_no)->item|null; unit items; scope game]

**Constants used**:
- `const.box_counts` (Bid box counts): 4 minor boxes, 3 concession boxes, 3 private boxes (4.10.1). Box numbers start at 1.; data: `{"table": {"minor": 4, "concession": 3, "private": 3}}`

**Rules constraining this node**:
- 4.11.8: Other unsold items remain, shifted to lower boxes. [demanded in preconditions/effects]
- 4.10.2: Shift remaining to lowest boxes, then fill from stack tops lowest first. [demanded in preconditions/effects]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Bid boxes** [repr.boxes_zero_based]: maps to: state.concession_bid_boxes (len 3), state.minor_bid_boxes (len 4), state.private_bid_boxes (len 3): elements BidBoxItem | None, lists keep their length (None padding)
  rule for coder: Graph 'box number' = list index + 1 ('box 1' = index 0; 'lower box number wins' = lower index). An item's identity in function signatures is (kind, box_index). Box counts: engine.setup.NUM_*_BID_BOXES.
- **Item sitting in a box** [repr.bid_box_item]: maps to: BidBoxItem(kind, ref, bids): ref is str (abbr) for concession, int for minor and private (the int annotation in models.py is wrong for concessions)
  rule for coder: state.minors key = f'M{ref}'.


### `bidding.refill_boxes` (function)

```python
refill_boxes(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.resolve_stock_round, round_manager.start_stock_round

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception; concession kind skipped when phase >= 5 (R9)

**Implements graph node(s)**: `act.refill_boxes`

#### Graph node `act.refill_boxes` (action) - Refill boxes
Shift then fill empty boxes from the stacks, lowest box first.

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [R9] concession kind skipped when phase >= 5

**Effects, in order** (execute exactly in this order):
1. [4.10.2] call shift_boxes
2. [1.7.7, 4.1.1] for kind in (minor, concession, private): for each empty box lowest first: pop the top of the kind's stack into the box; stop when the stack is empty
3. [R9] when phase >= 5 concession boxes stay empty and concession_stack stays empty

**Errors listed by the graph node**:
- NONE for legal input: total function when called in the documented order; ERR_ORDER if invoked out of sequence (e.g. outside resolve_stock_round)

**Order edges**:
- `act.refill_boxes` runs before `act.charge_interest` (seq 5; resolve: seq 5 runs before seq 6)
- `act.remove_box1_minor_and_export` runs before `act.refill_boxes` (seq 4; resolve: seq 4 runs before seq 5)

**Calls it must make / may trigger** (callee api in brackets):
- calls act.shift_boxes -> `bidding.shift_boxes` [same module] signature: `shift_boxes(state: GameState) -> None` 

**State touched**:
- reads `st.phase` (Game phase): Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1). [type int 1..7; unit phase number; scope game]
- reads `st.concession_stack` (Concession stack): Remaining concessions; top goes to lowest empty concession box. LNWR on top at setup (1.7.4). Emptied at phase 5 (R9). [type ordered list<major>; unit concession certificates (top first); scope game]
- reads `st.minor_stack` (Minor stack): Remaining minors; M24 on top at setup (1.7.5). [type ordered list<minor>; unit minor certificates (top first); scope game]
- reads `st.private_stack` (Private stack): Remaining privates; P1 on top at setup (1.7.6). [type ordered list<private>; unit private certificates (top first); scope game]
- reads `st.box_contents` (Bid-box contents): Item sitting in each box: minor boxes 1..4, concession boxes 1..3, private boxes 1..3. [type map (kind, box_no)->item|null; unit items; scope game]
- writes `st.concession_stack` (Concession stack): Remaining concessions; top goes to lowest empty concession box. LNWR on top at setup (1.7.4). Emptied at phase 5 (R9). [type ordered list<major>; unit concession certificates (top first); scope game]
- writes `st.minor_stack` (Minor stack): Remaining minors; M24 on top at setup (1.7.5). [type ordered list<minor>; unit minor certificates (top first); scope game]
- writes `st.private_stack` (Private stack): Remaining privates; P1 on top at setup (1.7.6). [type ordered list<private>; unit private certificates (top first); scope game]
- writes `st.box_contents` (Bid-box contents): Item sitting in each box: minor boxes 1..4, concession boxes 1..3, private boxes 1..3. [type map (kind, box_no)->item|null; unit items; scope game]

**Constants used**:
- `const.box_counts` (Bid box counts): 4 minor boxes, 3 concession boxes, 3 private boxes (4.10.1). Box numbers start at 1.; data: `{"table": {"minor": 4, "concession": 3, "private": 3}}`

**Rules constraining this node**:
- 4.1.1: Shift certificates to the lowest boxes then fill from stacks (first SR: 4 minors, 3 concessions, 3 privates). [demanded in preconditions/effects]
- 1.7.7: Fill each box from its stack starting with box 1. [demanded in preconditions/effects]
- R9: From phase 5 held concessions disappear, concession boxes are cleared and never refilled. [demanded in preconditions/effects]
- 4.10.2: Shift remaining to lowest boxes, then fill from stack tops lowest first. [demanded in preconditions/effects]
- 4.11.8: Other unsold items remain, shifted to lower boxes.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Phase** [repr.phase_state]: maps to: state.phase: int 1..7; limits and rust from app.data.phases.PHASES_BY_NUMBER; trigger table trains.TRAIN_PHASE (module constant)
  rule for coder: phase only increases (2.2.1) and is written only by phase_check (plus debug code in main.py). PHASES_BY_NUMBER[n].trains_rusted gives ONE code per phase; skipped phases are rusted too (loop old+1..new).
- **Company, item and player keys** [repr.company_keys]: maps to: major = abbreviation str ('LNWR','GWR','L&YR',...), key of majors/stock_positions/Player.shares/Player.concessions; minor = 'M<n>' (str key) with bare int n in MinorCompanyState.number, minor_stack and BidBoxItem.ref; private = int n; concession = the major's abbr; player = 'p1'..'pN'
  rule for coder: Item kind strings are 'concession' | 'minor' | 'private'; company kind arguments are 'major' | 'minor'. A concession is NOT a separate object.
- **Bid boxes** [repr.boxes_zero_based]: maps to: state.concession_bid_boxes (len 3), state.minor_bid_boxes (len 4), state.private_bid_boxes (len 3): elements BidBoxItem | None, lists keep their length (None padding)
  rule for coder: Graph 'box number' = list index + 1 ('box 1' = index 0; 'lower box number wins' = lower index). An item's identity in function signatures is (kind, box_index). Box counts: engine.setup.NUM_*_BID_BOXES.
- **Item sitting in a box** [repr.bid_box_item]: maps to: BidBoxItem(kind, ref, bids): ref is str (abbr) for concession, int for minor and private (the int annotation in models.py is wrong for concessions)
  rule for coder: state.minors key = f'M{ref}'.


### `bidding.clear_concession_boxes` (function)

```python
clear_concession_boxes(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): trains.phase_check

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- idempotent; no precondition on the phase

**Implements graph node(s)**: `act.clear_concession_boxes`

#### Graph node `act.clear_concession_boxes` (action) - Clear concessions at phase 5
Remove all concessions from play when phase 5 starts.

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [2.2.8] called only when phase just reached >= 5

**Effects, in order** (execute exactly in this order):
1. [R9] concession boxes emptied; concession_stack emptied; all concessions added to removed_items
2. [R9, 3.4.5] player_concessions[p] = empty for every player (no refund; certificate counts drop)

**Errors listed by the graph node**:
- NONE for legal input: total function when called in the documented order; ERR_ORDER if invoked out of sequence (e.g. outside resolve_stock_round)

**Order edges**:
- `act.discard_excess_trains` runs before `act.clear_concession_boxes` (seq 2; phase: seq 2 runs before seq 3)

**State touched**:
- reads `st.concession_stack` (Concession stack): Remaining concessions; top goes to lowest empty concession box. LNWR on top at setup (1.7.4). Emptied at phase 5 (R9). [type ordered list<major>; unit concession certificates (top first); scope game]
- reads `st.box_contents` (Bid-box contents): Item sitting in each box: minor boxes 1..4, concession boxes 1..3, private boxes 1..3. [type map (kind, box_no)->item|null; unit items; scope game]
- reads `st.player_concessions` (Concessions held): Concession certificates a player holds (acquired after resolution, 4.7.5). Removed at phase 5 (R9). [type map player->set<major>; unit concession certificates; scope per player]
- writes `st.concession_stack` (Concession stack): Remaining concessions; top goes to lowest empty concession box. LNWR on top at setup (1.7.4). Emptied at phase 5 (R9). [type ordered list<major>; unit concession certificates (top first); scope game]
- writes `st.box_contents` (Bid-box contents): Item sitting in each box: minor boxes 1..4, concession boxes 1..3, private boxes 1..3. [type map (kind, box_no)->item|null; unit items; scope game]
- writes `st.player_concessions` (Concessions held): Concession certificates a player holds (acquired after resolution, 4.7.5). Removed at phase 5 (R9). [type map player->set<major>; unit concession certificates; scope per player]
- writes `st.removed_items` (Items removed from play): Items removed from the game (unsold box-1 minor, concessions at phase 5). Audit only; consumed by operating rounds for minor-acquisition rules. [type set<item>; unit items; scope game]

**Rules constraining this node**:
- 3.4.5: At phase 5 concessions are removed from play (flipped to director side) -- overridden by R9. [demanded in preconditions/effects]
- R9: From phase 5 held concessions disappear, concession boxes are cleared and never refilled. [demanded in preconditions/effects]
- 2.2.8: Phase 5 removes unconverted concessions; phase 6 rusts 3; phase 7 rusts 4. [demanded in preconditions/effects]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Company, item and player keys** [repr.company_keys]: maps to: major = abbreviation str ('LNWR','GWR','L&YR',...), key of majors/stock_positions/Player.shares/Player.concessions; minor = 'M<n>' (str key) with bare int n in MinorCompanyState.number, minor_stack and BidBoxItem.ref; private = int n; concession = the major's abbr; player = 'p1'..'pN'
  rule for coder: Item kind strings are 'concession' | 'minor' | 'private'; company kind arguments are 'major' | 'minor'. A concession is NOT a separate object.
- **Bid boxes** [repr.boxes_zero_based]: maps to: state.concession_bid_boxes (len 3), state.minor_bid_boxes (len 4), state.private_bid_boxes (len 3): elements BidBoxItem | None, lists keep their length (None padding)
  rule for coder: Graph 'box number' = list index + 1 ('box 1' = index 0; 'lower box number wins' = lower index). An item's identity in function signatures is (kind, box_index). Box counts: engine.setup.NUM_*_BID_BOXES.
- **Item sitting in a box** [repr.bid_box_item]: maps to: BidBoxItem(kind, ref, bids): ref is str (abbr) for concession, int for minor and private (the int annotation in models.py is wrong for concessions)
  rule for coder: state.minors key = f'M{ref}'.
- **Concession** [repr.concession]: maps to: Player.concessions: list[str] of major abbr; BidBoxItem(kind='concession', ref=abbr); MajorCompanyState.concession_holder_player_id mirrors the holder (None after conversion/clearing); concession_converted True after conversion
  rule for coder: Removal at phase 5 = absent from stack, boxes and players (no field). Writers keep the mirror fields consistent (vacate_box_item sets, convert_concession/clear_concession_boxes clear).
- **Company status mirrors** [repr.company_status]: maps to: MajorCompanyState.floated / concession_converted / has_operated / share_price; MinorCompanyState.floated / share_price / removed / acquired_by_major
  rule for coder: floated=True and concession_converted=True on conversion; has_operated False at flotation, True after the first completed operating turn (advance_company); share_price is a display mirror nobody reads (read prices from the grid via current_price).


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GB07** (gap B-7, severity S3, kind repr): Minors: removed=True; concessions and privates: absent everywhere.
  reason: no field.

### `bidding.vacate_box_item` (function)

```python
vacate_box_item(state: GameState, kind: str, box_index: int, disposition: str, player_id: str | None = None) -> None
```

- parameters: ['state', 'kind', 'box_index', 'disposition', 'player_id']
- defaults (explicit): {"player_id": "None"}
- returns: (see signature)
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.remove_box1_minor_and_export, bidding.resolve_bids

**Exceptions**:

| class | code | when |
|---|---|---|
| BidError | ERR_ITEM_NOT_IN_BOX | box empty or invalid |
| BidError | ERR_BAD_DISPOSITION | disposition not 'award'/'remove' or award without player_id |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. box holds an item -> `ERR_ITEM_NOT_IN_BOX`
2. disposition in {'award','remove'}; award needs player_id -> `ERR_BAD_DISPOSITION`

**Implements graph node(s)**: `act.vacate_box_item`

#### Graph node `act.vacate_box_item` (action) - Take an item out of its box
Remove the item from its box and give it to a player or remove it from play.

- graph signature (abstract): params = ['item (kind, box_index)', 'disposition in {award(player), remove}']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.11.2] the box currently holds an item
- [4.11.2] award needs a player

**Effects, in order** (execute exactly in this order):
1. [4.11.2] box_contents[kind][box] = null (no shifting here)
2. award: concession -> player_concessions; private -> player_privates and private_status owner = player; minor -> minor_director[m] = player
3. remove: removed_items += item (minors: MinorCompanyState.removed = true)

**Errors listed by the graph node**:
- ERR_ITEM_NOT_IN_BOX
- ERR_BAD_DISPOSITION

**State touched**:
- reads `st.box_contents` (Bid-box contents): Item sitting in each box: minor boxes 1..4, concession boxes 1..3, private boxes 1..3. [type map (kind, box_no)->item|null; unit items; scope game]
- writes `st.box_contents` (Bid-box contents): Item sitting in each box: minor boxes 1..4, concession boxes 1..3, private boxes 1..3. [type map (kind, box_no)->item|null; unit items; scope game]
- writes `st.player_concessions` (Concessions held): Concession certificates a player holds (acquired after resolution, 4.7.5). Removed at phase 5 (R9). [type map player->set<major>; unit concession certificates; scope per player]
- writes `st.player_privates` (Privates held): Private companies held by each player. [type map player->set<private>; unit private certificates; scope per player]
- writes `st.minor_director` (Minor director's certificate holder): Player holding the 50% director's certificate of a minor (counts 1 certificate; assumption A6). Non-null = purchased and floated. [type map minor->player|null; unit -; scope per minor company]
- writes `st.removed_items` (Items removed from play): Items removed from the game (unsold box-1 minor, concessions at phase 5). Audit only; consumed by operating rounds for minor-acquisition rules. [type set<item>; unit items; scope game]
- writes `st.private_status` (Private company ownership/closure): Who owns a private (player via Player.private_companies, company via PrivateCompanyState.owner_company_id) and whether it is closed; an open private pays its fixed revenue each OR (3.1.2). Players' side written by vacate_box_item; company acquisition and closing are out of scope (operating-round code). [type map private -> {owner_player | owner_company | none, closed bool}; unit -; scope per private company]

**Rules constraining this node**:
- 4.11.2: Highest bidders pay and take items; tokens are removed. [demanded in preconditions/effects]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Bid boxes** [repr.boxes_zero_based]: maps to: state.concession_bid_boxes (len 3), state.minor_bid_boxes (len 4), state.private_bid_boxes (len 3): elements BidBoxItem | None, lists keep their length (None padding)
  rule for coder: Graph 'box number' = list index + 1 ('box 1' = index 0; 'lower box number wins' = lower index). An item's identity in function signatures is (kind, box_index). Box counts: engine.setup.NUM_*_BID_BOXES.
- **Item sitting in a box** [repr.bid_box_item]: maps to: BidBoxItem(kind, ref, bids): ref is str (abbr) for concession, int for minor and private (the int annotation in models.py is wrong for concessions)
  rule for coder: state.minors key = f'M{ref}'.
- **Concession** [repr.concession]: maps to: Player.concessions: list[str] of major abbr; BidBoxItem(kind='concession', ref=abbr); MajorCompanyState.concession_holder_player_id mirrors the holder (None after conversion/clearing); concession_converted True after conversion
  rule for coder: Removal at phase 5 = absent from stack, boxes and players (no field). Writers keep the mirror fields consistent (vacate_box_item sets, convert_concession/clear_concession_boxes clear).
- **Private company** [repr.private_company]: maps to: Player.private_companies: list[int]; PrivateCompanyState(number, owner_player_id mirror, owner_company_id, closed, treasury_credit)
  rule for coder: pay_private_revenues pays every open private: if owner_company_id is set -> that company's treasury, else the player holding it in Player.private_companies; closed privates pay nothing.
- **Minor company ownership** [repr.minor_ownership]: maps to: MinorCompanyState.director_player_id (non-None after award); NO entry in Player.shares; id 'M<n>'
  rule for coder: A minor counts 1 certificate for its director (certs_held dispatches on `cid in state.minors`). floated=True is set by float_minors; removed=True for a removed minor (director stays None). Follows the graph, not the models.py comment (decision GA10).
- **Company status mirrors** [repr.company_status]: maps to: MajorCompanyState.floated / concession_converted / has_operated / share_price; MinorCompanyState.floated / share_price / removed / acquired_by_major
  rule for coder: floated=True and concession_converted=True on conversion; has_operated False at flotation, True after the first completed operating turn (advance_company); share_price is a display mirror nobody reads (read prices from the grid via current_price).


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GB07** (gap B-7, severity S3, kind repr): Minors: removed=True; concessions and privates: absent everywhere.
  reason: no field.
- **GB05** (gap B-5, severity S3, kind repr): Documented in repr.concession, repr.private_company, repr.company_status; private_status is a new state.
  reason: coverage.
- **DN08** (gap new, severity S3, kind out_of_scope): Privates owned by companies (owner_company_id) are paid to the company treasury; the P15/P20 treasury credit and closing at phase 7 are out of scope.  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: 3.1.2; R11-style deferral.

### `bidding.resolve_bids` (function)

```python
resolve_bids(state: GameState) -> tuple[set[tuple[str, int]], list[tuple[int, int, int, str]]]
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (items_with_bids, pending_minor_floats)
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.resolve_stock_round
- api notes: Sets any_sale_this_stock_round when at least one item is WON (R6b).

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception; no sr_over check

**Implements graph node(s)**: `act.resolve_bids`

#### Graph node `act.resolve_bids` (action) - Pay and award box items
Award each item with bids to the highest bidder who can pay; remove tokens. Returns (items_with_bids, pending_minor_floats).

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.11.2] none: callable at any time (R6b: with no bids nothing happens and no sale is recorded)

**Effects, in order** (execute exactly in this order):
1. items_with_bids = every item with >=1 token (snapshot before clearing; returned, not stored)
2. for item in item_resolution_order: for bidders by amount desc: first with player_cash >= amount wins [R8]: player_cash -= amount; bank_cash += amount [R3]; call vacate_box_item(item, award(bidder)); [R6b] sale_happened = true (an item WON counts as a sale); minors also appended to pending_minor_floats (minor, bid, box_index, buyer)
3. [R8, R6b] if nobody can pay the item stays in its box, still counts as having had a bid (in items_with_bids) but does NOT set sale_happened
4. [4.11.2] bids = empty (all tokens removed)

**Errors listed by the graph node**:
- NONE (raises nothing)

**Order edges**:
- `act.resolve_bids` runs before `act.float_minors` (seq 1; resolve: seq 1 runs before seq 2)

**Calls it must make / may trigger** (callee api in brackets):
- calls act.vacate_box_item -> `bidding.vacate_box_item` [same module] signature: `vacate_box_item(state: GameState, kind: str, box_index: int, disposition: str, player_id: str | None = None) -> None` 
- calls drv.item_resolution_order -> `bidding.item_resolution_order` [same module] signature: `item_resolution_order(state: GameState) -> list[tuple[str, int]]` 

**State touched**:
- reads `st.bids` (Bids on box items): Bidding tokens on each item's track: at most one token per player per item (assumption A5). Amount = bid. Highest bid = max amount. Cleared at resolution (4.11.2). [type map item->map player->amount; unit pounds (multiple of 5); scope per item]
- reads `st.box_contents` (Bid-box contents): Item sitting in each box: minor boxes 1..4, concession boxes 1..3, private boxes 1..3. [type map (kind, box_no)->item|null; unit items; scope game]
- reads `st.player_cash` (Player cash): Cash in hand of each player. Never negative. [type int map player->int; unit pounds (integer); scope per player]
- writes `st.items_with_bids` (Items that had a bid): Snapshot taken by resolve_bids of every item on which any token was placed (including items nobody could pay, R8); passed to unsold_minor_exports (4.11.6). Local return value, not stored. [type set<(kind, box_index)>; unit items; scope call-scoped]
- writes `st.player_cash` (Player cash): Cash in hand of each player. Never negative. [type int map player->int; unit pounds (integer); scope per player]
- writes `st.bank_cash` (Bank cash): Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5). [type int (can go below zero); unit pounds; scope game]
- writes `st.sale_happened` (A sale happened flag): Set true when a player buys a share, sells a share, converts a concession (R15, R6), or wins a bid-box item at resolution (R6b). Reset at stock-round start. Read by the 10.1.1 first-round nothing-sold test (R6b). Written by the module functions themselves (idempotent; the caller actions.py also sets it after buy and convert). [type bool; unit -; scope stock round]
- writes `st.pending_minor_floats` (Minors awaiting flotation): Minors paid for during resolve_bids, to be floated by float_minors in flotation order (4.11.3). Local return value, not stored. [type list<(minor_number, bid, box_index, buyer)>; unit -; scope call-scoped]
- writes `st.bids` (Bids on box items): Bidding tokens on each item's track: at most one token per player per item (assumption A5). Amount = bid. Highest bid = max amount. Cleared at resolution (4.11.2). [type map item->map player->amount; unit pounds (multiple of 5); scope per item]

**Rules constraining this node**:
- R3: Player pays full bid to bank. Phase 1: treasury 100, price 50. Phase 2: treasury 2x price. Phase 3+: treasury = bid. Bank covers difference. [demanded in preconditions/effects]
- R6b: In 10.1.1 'nothing sold in the first stock round' means: no share bought or sold, no concession converted, AND no bid-box item won at resolution. A round with only unsuccessful bids (nobody could pay, R8) counts as nothing sold; a round in which at least one bid wins an item counts as something sold. PROVISIONAL ruling (adopted by the task owner), replaces the provisional tail of R6. [demanded in preconditions/effects]
- R8: If the winner can't pay at resolution the item goes to next highest bidder who can; if nobody can it stays in its box and counts as having had a bid. [demanded in preconditions/effects]
- 4.11.2: Highest bidders pay and take items; tokens are removed. [demanded in preconditions/effects]
- 4.7.5: Items bid on are acquired only at round end, so convertible next round.
- R6: Bidding alone is not a sale; buy, sell, convert count. Phase-1 conflict open; provisional: a bid that wins an item at resolution counts.

**Representation notes (repr nodes bound to touched states / this node)**:
- **Bids and bidding tokens** [repr.bids]: maps to: BidBoxItem.bids: dict[player_id, int] (one entry = one token on the item's track)
  rule for coder: highest_bid = max(bids.values()) if bids else None; a bid of 0 is a bid (never `if highest_bid:`). Tokens in use = items with the player in bids. Empty dict = no bid.
- **Bid boxes** [repr.boxes_zero_based]: maps to: state.concession_bid_boxes (len 3), state.minor_bid_boxes (len 4), state.private_bid_boxes (len 3): elements BidBoxItem | None, lists keep their length (None padding)
  rule for coder: Graph 'box number' = list index + 1 ('box 1' = index 0; 'lower box number wins' = lower index). An item's identity in function signatures is (kind, box_index). Box counts: engine.setup.NUM_*_BID_BOXES.
- **Item sitting in a box** [repr.bid_box_item]: maps to: BidBoxItem(kind, ref, bids): ref is str (abbr) for concession, int for minor and private (the int annotation in models.py is wrong for concessions)
  rule for coder: state.minors key = f'M{ref}'.
- **Cash, loans, bank, treasuries** [repr.money]: maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.
- **Values that live only inside one procedure** [repr.call_scoped]: maps to: items_with_bids -> set[(kind, box_index)] and pending_minor_floats -> list[(minor_number, bid, box_index, buyer_player_id)]: return value of resolve_bids, passed to unsold_minor_exports / float_minors; never stored
  rule for coder: float_minors(state, pending=None) and unsold_minor_exports(state, items_with_bids=()) therefore take them as parameters (signature change relative to v1).
- **'A sale happened' flag** [repr.sale_flag]: maps to: state.any_sale_this_stock_round (bool)
  rule for coder: Set True by: sell_shares, buy_share, convert_concession (module functions themselves; actions.py also sets it after buy and convert), and resolve_bids when a bid-box item is WON (R6b). Reset to False by start_stock_round. Read by check_game_end_triggers(context='end_of_stock_round').


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA07** (gap A.1.7, severity S2, kind graph_fix): sell_shares, buy_share and convert_concession all set the flag themselves (idempotent); actions.py's extra write after buy/convert is documented as redundant; resolve_bids sets it when an item is won (R6b).
  reason: makes direct calls of module functions consistent; R15.
- **GA33** (gap A.2.33, severity S3, kind graph_fix): Ruling R6b adopted (provisional): nothing sold = no share bought/sold, no concession converted, no bid-box item won at resolution. resolve_bids sets sale_happened only for WON items; an item nobody can pay (R8) is not won.
  reason: task owner.
- **GA34** (gap A.2.34, severity S3, kind carried): All remain as in GRAPH_NOTES v1 (copied into v2 notes). Owner-open and worth a ruling: A4 (opening bid 0), A5 (one token per item, leader cannot raise), A9 (batch sale priced before the drop), A15 (unpaid box-1 minor is still removed), A16 (payment order).  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: no new evidence.
- **DN13** (gap new, severity S2, kind decision): An item that nobody can pay for (R8) stays in its box, counts as having had a bid for exports (A15) but is NOT won, so it does not set sale_happened (R6b).  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**
  reason: R6b wording 'won'.
- **GA14** (gap A.1.14, severity S2, kind graph_fix): items_with_bids and pending_minor_floats are call-scoped states: returned by resolve_bids and passed as parameters (float_minors(state, pending=None), unsold_minor_exports(state, items_with_bids=())).
  reason: no field exists; signatures changed vs v1.
- **GB09** (gap B-9, severity S2, kind graph_fix): See GA14.
  reason: GA14.

### `bidding.unsold_minor_exports` (function)

```python
unsold_minor_exports(state: GameState, items_with_bids: Iterable[tuple[str, int]] = ()) -> None
```

- parameters: ['state', 'items_with_bids']
- defaults (explicit): {"items_with_bids": "()"}
- returns: (see signature)
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.resolve_stock_round

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception

**Implements graph node(s)**: `act.unsold_minor_exports`

#### Graph node `act.unsold_minor_exports` (action) - Export per unbid minor
One L/2 train exported for each remaining minor box item that had no bid.

- graph signature (abstract): params = ['items_with_bids']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.11.6] after float_minors

**Effects, in order** (execute exactly in this order):
1. [4.11.6] for each minor still in a box and not in items_with_bids (box indexes ascending): call export_train(L_only)

**Errors listed by the graph node**:
- NONE (raises nothing)

**Order edges**:
- `act.unsold_minor_exports` runs before `act.remove_box1_minor_and_export` (seq 3; resolve: seq 3 runs before seq 4)
- `act.float_minors` runs before `act.unsold_minor_exports` (seq 2; resolve: seq 2 runs before seq 3)

**Calls it must make / may trigger** (callee api in brackets):
- calls act.export_train -> `trains.export_train` [CROSS-MODULE] signature: `export_train(state: GameState, mode: str) -> None` 
- triggers act.export_train -> `trains.export_train` [CROSS-MODULE] signature: `export_train(state: GameState, mode: str) -> None` 

**State touched**:
- reads `st.box_contents` (Bid-box contents): Item sitting in each box: minor boxes 1..4, concession boxes 1..3, private boxes 1..3. [type map (kind, box_no)->item|null; unit items; scope game]
- reads `st.items_with_bids` (Items that had a bid): Snapshot taken by resolve_bids of every item on which any token was placed (including items nobody could pay, R8); passed to unsold_minor_exports (4.11.6). Local return value, not stored. [type set<(kind, box_index)>; unit items; scope call-scoped]

**Rules constraining this node**:
- 4.11.6: One L/2-train exported from the bank per minor with no bid; no action if none. [demanded in preconditions/effects]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Bid boxes** [repr.boxes_zero_based]: maps to: state.concession_bid_boxes (len 3), state.minor_bid_boxes (len 4), state.private_bid_boxes (len 3): elements BidBoxItem | None, lists keep their length (None padding)
  rule for coder: Graph 'box number' = list index + 1 ('box 1' = index 0; 'lower box number wins' = lower index). An item's identity in function signatures is (kind, box_index). Box counts: engine.setup.NUM_*_BID_BOXES.
- **Item sitting in a box** [repr.bid_box_item]: maps to: BidBoxItem(kind, ref, bids): ref is str (abbr) for concession, int for minor and private (the int annotation in models.py is wrong for concessions)
  rule for coder: state.minors key = f'M{ref}'.
- **Values that live only inside one procedure** [repr.call_scoped]: maps to: items_with_bids -> set[(kind, box_index)] and pending_minor_floats -> list[(minor_number, bid, box_index, buyer_player_id)]: return value of resolve_bids, passed to unsold_minor_exports / float_minors; never stored
  rule for coder: float_minors(state, pending=None) and unsold_minor_exports(state, items_with_bids=()) therefore take them as parameters (signature change relative to v1).


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **DN14** (gap new, severity S3, kind decision): Train exports at resolution never set sale_happened (A17 kept).
  reason: else the first-round rule could never fire.
- **GA14** (gap A.1.14, severity S2, kind graph_fix): items_with_bids and pending_minor_floats are call-scoped states: returned by resolve_bids and passed as parameters (float_minors(state, pending=None), unsold_minor_exports(state, items_with_bids=())).
  reason: no field exists; signatures changed vs v1.
- **GB09** (gap B-9, severity S2, kind graph_fix): See GA14.
  reason: GA14.

### `bidding.remove_box1_minor_and_export` (function)

```python
remove_box1_minor_and_export(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 6
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.resolve_stock_round

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception; no-op if minor box 1 is empty

**Implements graph node(s)**: `act.remove_box1_minor_and_export`

#### Graph node `act.remove_box1_minor_and_export` (action) - Remove unsold box-1 minor
Remove the unsold minor in minor box 1 and export the next train.

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.11.7] minor box 1 still holds a minor after resolution (unsold; assumption A15 includes unpaid items)

**Effects, in order** (execute exactly in this order):
1. [4.11.7] vacate_box_item(minor, remove); call export_train(next_with_phase)

**Errors listed by the graph node**:
- NONE for legal input: total function when called in the documented order; ERR_ORDER if invoked out of sequence (e.g. outside resolve_stock_round)

**Order edges**:
- `act.remove_box1_minor_and_export` runs before `act.refill_boxes` (seq 4; resolve: seq 4 runs before seq 5)
- `act.unsold_minor_exports` runs before `act.remove_box1_minor_and_export` (seq 3; resolve: seq 3 runs before seq 4)

**Calls it must make / may trigger** (callee api in brackets):
- calls act.vacate_box_item -> `bidding.vacate_box_item` [same module] signature: `vacate_box_item(state: GameState, kind: str, box_index: int, disposition: str, player_id: str | None = None) -> None` 
- calls act.export_train -> `trains.export_train` [CROSS-MODULE] signature: `export_train(state: GameState, mode: str) -> None` 
- triggers act.export_train -> `trains.export_train` [CROSS-MODULE] signature: `export_train(state: GameState, mode: str) -> None` 

**State touched**:
- reads `st.box_contents` (Bid-box contents): Item sitting in each box: minor boxes 1..4, concession boxes 1..3, private boxes 1..3. [type map (kind, box_no)->item|null; unit items; scope game]

**Rules constraining this node**:
- 4.11.7: Unsold minor in box 1 is removed and next train exported (counts for phase). [demanded in preconditions/effects]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Bid boxes** [repr.boxes_zero_based]: maps to: state.concession_bid_boxes (len 3), state.minor_bid_boxes (len 4), state.private_bid_boxes (len 3): elements BidBoxItem | None, lists keep their length (None padding)
  rule for coder: Graph 'box number' = list index + 1 ('box 1' = index 0; 'lower box number wins' = lower index). An item's identity in function signatures is (kind, box_index). Box counts: engine.setup.NUM_*_BID_BOXES.
- **Item sitting in a box** [repr.bid_box_item]: maps to: BidBoxItem(kind, ref, bids): ref is str (abbr) for concession, int for minor and private (the int annotation in models.py is wrong for concessions)
  rule for coder: state.minors key = f'M{ref}'.


### `bidding.resolve_stock_round` (function)

```python
resolve_stock_round(state: GameState) -> None
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 6
- given name (fixed by given code, never rename): YES
- aliases: none
- callers in given code: actions (imported, unused), round_manager.end_stock_round
- callers from graph (calls/triggers): round_manager.end_stock_round

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- NO sr_over check, NO round_type check: callable whenever the caller invokes it (the round manager decides when)
- does not increment sr_completed, switch round type or reset round flags

**Implements graph node(s)**: `act.resolve_stock_round`

#### Graph node `act.resolve_stock_round` (action) - Resolve stock round
Orchestrate the end-of-round procedure (steps in seq order). Callable whenever the caller invokes it: the ROUND MANAGER decides when (no sr_over precondition).

- graph signature (abstract): params = ['none']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [4.11.1] none: no sr_over check, no round_type check (decision GA37); with no bids and no minors in boxes the steps simply do nothing

**Effects, in order** (execute exactly in this order):
1. step1 [4.11.2] resolve_bids -> (items_with_bids, pending_minor_floats)
2. step2 [4.11.3-4.11.5] float_minors(pending)
3. step3 [4.11.6] unsold_minor_exports(items_with_bids)
4. step4 [4.11.7] remove_box1_minor_and_export
5. step5 [4.11.8, 4.10.2] refill_boxes (shift then fill)
6. step6 [4.11.10] charge_interest
7. step7 [4.12] raise_sold_out_prices
8. step8 [4.11.9] reorder_players_by_cash
9. step9 [10.1.1] check_game_end_triggers(end_of_stock_round)
10. does NOT increment sr_completed, change round_type or reset per-round flags (end_stock_round / start_stock_round do)

**Errors listed by the graph node**:
- NONE (raises nothing)

**Order edges**:
- `act.resolve_stock_round` runs before `act.start_operating_round` (seq 1; end_sr: seq 1 runs before seq 2)

**Calls it must make / may trigger** (callee api in brackets):
- calls act.resolve_bids -> `bidding.resolve_bids` [same module] signature: `resolve_bids(state: GameState) -> tuple[set[tuple[str, int]], list[tuple[int, int, int, str]]]` 
- calls act.float_minors -> `company_formation.float_minors` [CROSS-MODULE] signature: `float_minors(state: GameState, pending: Iterable[tuple[int, int, int, str]] | None = None) -> None` 
- calls act.unsold_minor_exports -> `bidding.unsold_minor_exports` [same module] signature: `unsold_minor_exports(state: GameState, items_with_bids: Iterable[tuple[str, int]] = ()) -> None` 
- calls act.remove_box1_minor_and_export -> `bidding.remove_box1_minor_and_export` [same module] signature: `remove_box1_minor_and_export(state: GameState) -> None` 
- calls act.refill_boxes -> `bidding.refill_boxes` [same module] signature: `refill_boxes(state: GameState) -> None` 
- calls act.charge_interest -> `shares.charge_interest` [CROSS-MODULE] signature: `charge_interest(state: GameState) -> None` 
- calls act.raise_sold_out_prices -> `turn_order.raise_sold_out_prices` [CROSS-MODULE] signature: `raise_sold_out_prices(state: GameState) -> None` 
- calls act.reorder_players_by_cash -> `turn_order.reorder_players_by_cash` [CROSS-MODULE] signature: `reorder_players_by_cash(state: GameState) -> None` 
- calls act.check_game_end_triggers -> `scoring.check_game_end_triggers` [CROSS-MODULE] signature: `check_game_end_triggers(state: GameState, context: str | None = None) -> None` 
- triggers act.resolve_bids -> `bidding.resolve_bids` [same module] signature: `resolve_bids(state: GameState) -> tuple[set[tuple[str, int]], list[tuple[int, int, int, str]]]` 
- triggers act.float_minors -> `company_formation.float_minors` [CROSS-MODULE] signature: `float_minors(state: GameState, pending: Iterable[tuple[int, int, int, str]] | None = None) -> None` 
- triggers act.unsold_minor_exports -> `bidding.unsold_minor_exports` [same module] signature: `unsold_minor_exports(state: GameState, items_with_bids: Iterable[tuple[str, int]] = ()) -> None` 
- triggers act.remove_box1_minor_and_export -> `bidding.remove_box1_minor_and_export` [same module] signature: `remove_box1_minor_and_export(state: GameState) -> None` 
- triggers act.refill_boxes -> `bidding.refill_boxes` [same module] signature: `refill_boxes(state: GameState) -> None` 
- triggers act.charge_interest -> `shares.charge_interest` [CROSS-MODULE] signature: `charge_interest(state: GameState) -> None` 
- triggers act.raise_sold_out_prices -> `turn_order.raise_sold_out_prices` [CROSS-MODULE] signature: `raise_sold_out_prices(state: GameState) -> None` 
- triggers act.reorder_players_by_cash -> `turn_order.reorder_players_by_cash` [CROSS-MODULE] signature: `reorder_players_by_cash(state: GameState) -> None` 
- triggers act.check_game_end_triggers -> `scoring.check_game_end_triggers` [CROSS-MODULE] signature: `check_game_end_triggers(state: GameState, context: str | None = None) -> None` 

**Rules constraining this node**:
- 4.11.9: Most cash gets card 1; ties keep previous relative order (P9 deferred). [demanded in preconditions/effects]
- 4.11.8: Other unsold items remain, shifted to lower boxes. [demanded in preconditions/effects]
- 4.10.2: Shift remaining to lowest boxes, then fill from stack tops lowest first. [demanded in preconditions/effects]
- 4.11.2: Highest bidders pay and take items; tokens are removed. [demanded in preconditions/effects]
- 4.11.1: All players pass consecutively -> stock round over. [demanded in preconditions/effects]
- 4.11.10: 50% interest on outstanding loans at stock round end. [demanded in preconditions/effects]
- 4.11.6: One L/2-train exported from the bank per minor with no bid; no action if none. [demanded in preconditions/effects]
- 10.1.1: Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. [demanded in preconditions/effects]
- 4.11.7: Unsold minor in box 1 is removed and next train exported (counts for phase). [demanded in preconditions/effects]
- 4.1.4: One of: buy one share, convert, place/increase up to 3 bids; round ends when all pass consecutively.


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA37** (gap A.2.37, severity S3, kind decision): resolve_stock_round and end_stock_round do NOT check sr_over or round_type; the round manager (actions._apply_pass) decides when. No ERR_NOT_OVER exists.
  reason: callable whenever the caller invokes it; avoids lazy cross-component import.

## 4. Rules this module is responsible for (id + text, verbatim from the graph)

- **1.7.2** (rule): Bank 12000 incl. start money 2100/n; bidding tokens and cert limit by player count. -- constrains `drv.tokens_total`
- **1.7.7** (rule): Fill each box from its stack starting with box 1. -- constrains `act.refill_boxes`
- **10.1.1** (rule): Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR. -- constrains `act.resolve_stock_round`
- **2.2.8** (rule): Phase 5 removes unconverted concessions; phase 6 rusts 3; phase 7 rusts 4. -- constrains `act.clear_concession_boxes`
- **3.1.3** (rule): Face value of privates is 0. -- constrains `drv.face_value`
- **3.1.4** (rule): A private can only be bought through the bidding mechanism. -- constrains `act.place_bid`
- **3.2.4** (rule): Players can only buy minors through bidding. -- constrains `act.place_bid`
- **3.4.2** (rule): Concessions bought through bid boxes; face value 100. -- constrains `drv.face_value`, `act.place_bid`
- **3.4.5** (rule): At phase 5 concessions are removed from play (flipped to director side) -- overridden by R9. -- constrains `act.clear_concession_boxes`
- **4.1.1** (rule): Shift certificates to the lowest boxes then fill from stacks (first SR: 4 minors, 3 concessions, 3 privates). -- constrains `act.refill_boxes`
- **4.1.4** (rule): One of: buy one share, convert, place/increase up to 3 bids; round ends when all pass consecutively. -- constrains `act.place_bid`, `act.move_bid`, `act.resolve_stock_round`
- **4.10.10** (rule): A bid cannot be withdrawn or moved to another item. -- constrains `drv.tokens_used`, `act.move_bid`
- **4.10.2** (rule): Shift remaining to lowest boxes, then fill from stack tops lowest first. -- constrains `act.shift_boxes`, `act.refill_boxes`, `act.resolve_stock_round`
- **4.10.3** (rule): Number of tokens by player count = max items a player may bid on. -- constrains `drv.tokens_total`, `act.place_bid`
- **4.10.4** (rule): Place an unallocated token on an empty space, or move a token up on the same item only if another player has a higher bid. -- constrains `act.place_bid`, `act.move_bid`
- **4.10.5** (rule): Up to three bids placed/moved per turn. -- constrains `act.place_bid`, `act.move_bid`
- **4.10.6** (rule): Opening bid >= face value; whole multiples of 5. -- constrains `drv.min_legal_bid`, `drv.bid_amount_error`, `drv.bid_amount_valid`, `act.place_bid`, `act.move_bid`
- **4.10.7** (rule): Bid must exceed prior bids and keep committed money <= cash. -- constrains `drv.highest_bid`, `drv.highest_bidder`, `drv.committed_money`, `drv.min_legal_bid`, `drv.bid_amount_error`, `drv.bid_amount_valid`
- **4.10.8** (rule): No placing/moving at the limit; leading bids count. -- constrains `act.place_bid`, `act.move_bid`
- **4.10.9** (rule): Any bid >= 100 over face is allowed (physical chip only). -- constrains `drv.bid_amount_valid`
- **4.11.1** (rule): All players pass consecutively -> stock round over. -- constrains `act.resolve_stock_round`
- **4.11.10** (rule): 50% interest on outstanding loans at stock round end. -- constrains `act.resolve_stock_round`
- **4.11.2** (rule): Highest bidders pay and take items; tokens are removed. -- constrains `drv.item_resolution_order`, `act.vacate_box_item`, `act.resolve_bids`, `act.resolve_stock_round`
- **4.11.6** (rule): One L/2-train exported from the bank per minor with no bid; no action if none. -- constrains `act.unsold_minor_exports`, `act.resolve_stock_round`
- **4.11.7** (rule): Unsold minor in box 1 is removed and next train exported (counts for phase). -- constrains `act.remove_box1_minor_and_export`, `act.resolve_stock_round`
- **4.11.8** (rule): Other unsold items remain, shifted to lower boxes. -- constrains `act.shift_boxes`, `act.refill_boxes`, `act.resolve_stock_round`
- **4.11.9** (rule): Most cash gets card 1; ties keep previous relative order (P9 deferred). -- constrains `act.resolve_stock_round`
- **4.2.5** (rule): At the limit a player may not bid; each item on which they hold the highest bid counts as a certificate. -- constrains `drv.items_led`, `act.place_bid`, `act.move_bid`
- **4.3.1** (rule): No buying, converting or bidding while in debt. -- constrains `act.place_bid`, `act.move_bid`
- **4.7.5** (rule): Items bid on are acquired only at round end, so convertible next round. -- constrains `act.resolve_bids`
- **R1** (ruling): Minor face value = 100 (rulebook states none). -- constrains `drv.face_value`, `drv.min_legal_bid`
- **R10** (ruling): Over the limit must sell down at first opportunity; while over and able to sell the player may not buy or bid. -- constrains `act.place_bid`, `act.move_bid`
- **R3** (ruling): Player pays full bid to bank. Phase 1: treasury 100, price 50. Phase 2: treasury 2x price. Phase 3+: treasury = bid. Bank covers difference. -- constrains `act.resolve_bids`
- **R6** (ruling): Bidding alone is not a sale; buy, sell, convert count. Phase-1 conflict open; provisional: a bid that wins an item at resolution counts. -- constrains `act.resolve_bids`
- **R6b** (ruling): In 10.1.1 'nothing sold in the first stock round' means: no share bought or sold, no concession converted, AND no bid-box item won at resolution. A round with only unsuccessful bids (nobody could pay, R8) counts as nothing sold; a round in which at least one bid wins an item counts as something sold. PROVISIONAL ruling (adopted by the task owner), replaces the provisional tail of R6. -- constrains `act.resolve_bids`
- **R8** (ruling): If the winner can't pay at resolution the item goes to next highest bidder who can; if nobody can it stays in its box and counts as having had a bid. -- constrains `act.resolve_bids`
- **R9** (ruling): From phase 5 held concessions disappear, concession boxes are cleared and never refilled. -- constrains `act.place_bid`, `act.move_bid`, `act.refill_boxes`, `act.clear_concession_boxes`

