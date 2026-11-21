# Contract: `backend/app/engine/certificates.py`

Generated mechanically from graph v2 by gen_contracts.py. Read COMMON.md first, then this file; BINDING.md lists the representation rules and the cross-module call matrix.

Import layering: this module is layer 2 (1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares and company_formation, 6 bidding, 7 round_manager). Calls to a HIGHER layer must be lazy imports inside the function body; never import upward at module level.

## 1. Export list (every name below, plus every alias, must exist at module level)

- `CertificateError` (exception)
- `TOTAL_UNITS` (constant)
- `POOL_CAP_UNITS` (constant)
- `HOLD_CAP_UNITS` (constant)
- `SaleCheck` (class)
- `cert_units` (function)
- `ordinary_certs` (function)
- `units_held` (function)
- `certs_held` (function)
- `cert_limit` (function)
- `cert_count_holdings` (function)
- `cert_count` (function)
- `over_limit` (function)
- `successor` (function)
- `sale_legal` (function)
- `can_sell_any` (function)
- `must_sell` (function)
- `fully_sold` (function)
- `swap_director` (function)

Public API count: 19

## 2. Module-level obligations

### States this module writes (flags and data it is responsible for)
- `st.ordinary_certs` (Ordinary certificates held): Number of ordinary 10% certificates a player holds in a major company. EXCLUDES the director's certificate, which is stored in director_holder. units_held = ordinary_certs + director units; certs_held = ordinary_certs + (1 if director). -- written by `act.swap_director`
- `st.director_holder` (Director's certificate holder): Holder of the director's certificate of a major company (null until the company is started). The director's certificate = cert_units units (2; LNWR 1) but ONE certificate for limit counting. -- written by `act.swap_director`

### Hooks / triggers fired by this module's nodes
- (none)

### Notes that name 'sets ... itself' / flags (from api notes)
- `CertificateError`: Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. Raised by swap_director and by lookups of unknown companies.
- `TOTAL_UNITS`: const.share_structure: units per company.
- `POOL_CAP_UNITS`: const.share_structure: bank pool holds at most 5 units.
- `HOLD_CAP_UNITS`: const.share_structure: a player may hold at most 6 units (60%).
- `SaleCheck`: Fields: legal: bool, swap_needed: bool, successor: str | None, reason: str | None = None. reason is None if legal, else ERR_NOT_SELLABLE | ERR_POOL_FULL | ERR_TOO_MANY (GAP A20 fix).
- `ordinary_certs`: Accessor of the DERIVED state node st.ordinary_certs (units, director's certificate excluded).
- `swap_director`: Changes ONLY MajorCompanyState.director_player_id: every Player.shares value is unchanged (units are invariant, T1).

### Module-level decisions (resolve any api or node of this module)
- **GA38** (gap A.2.38, severity S3, kind decision): ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).
  reason: layering (no module for a shared base) and the given except clauses.
- **GA20** (gap A.2.20, severity S2, kind graph_fix): SaleCheck gains a reason field (None | ERR_NOT_SELLABLE | ERR_POOL_FULL | ERR_TOO_MANY); sell_shares maps reasons to the three codes.
  reason: exposes the failing clause.
- **GB19** (gap B-19, severity S3, kind decision): Layers: 1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares + company_formation, 6 bidding, 7 round_manager; upward calls are lazy imports (api node attrs.layer; lazy edges: turn_order->scoring.check_game_end_triggers, turn_order->certificates.fully_sold, certificates->bidding.items_led, trains->bidding.clear_concession_boxes, bidding->nothing upward now that resolve_stock_round has no sr_over check).
  reason: circular imports.
- **GA30** (gap A.2.30, severity S3, kind decision): sale_legal for an unknown, minor or unstarted company returns SaleCheck(False, False, None, 'ERR_NOT_SELLABLE'); can_sell_any scans only floated majors.
  reason: total function.

## 3. API contracts

### `certificates.CertificateError` (exception)

```python
class CertificateError(Exception)
```

- bases: ['Exception']; message `<ERR_CODE>: <text>`; attribute `.code` = ERR_CODE
- raised by: certificates.certs_held, certificates.swap_director
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. Raised by swap_director and by lookups of unknown companies.

**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA38** (gap A.2.38, severity S3, kind decision): ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).
  reason: layering (no module for a shared base) and the given except clauses.

### `certificates.TOTAL_UNITS` (constant)

```python
TOTAL_UNITS = 10
```

- value: `10`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: const.share_structure: units per company.

### `certificates.POOL_CAP_UNITS` (constant)

```python
POOL_CAP_UNITS = 5
```

- value: `5`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: const.share_structure: bank pool holds at most 5 units.

### `certificates.HOLD_CAP_UNITS` (constant)

```python
HOLD_CAP_UNITS = 6
```

- value: `6`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: const.share_structure: a player may hold at most 6 units (60%).

### `certificates.SaleCheck` (class)

```python
class SaleCheck(NamedTuple)
```

- fields (in this order): `legal: bool`, `swap_needed: bool`, `successor: str | None`, `reason: str | None = None`
- parameters: (none)
- defaults (explicit): (none)
- returns: (see signature)
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): certificates.can_sell_any, shares.sell_shares
- api notes: Fields: legal: bool, swap_needed: bool, successor: str | None, reason: str | None = None. reason is None if legal, else ERR_NOT_SELLABLE | ERR_POOL_FULL | ERR_TOO_MANY (GAP A20 fix).

**Implements graph node(s)**: `drv.sale_legal`

#### Graph node `drv.sale_legal` (derived) - Is a sale legal?
Whether player p may sell s shares of company c, what directorship change that causes, and why not.

- graph signature (abstract): params = ['player p', 'major c', 'count s']; returns = record

**Formula**: [4.4.2, R5] let k=ordinary_certs[p,c], H=units_held(p,c), d=director_holder[c]; if c is not a started major: legal=false, reason=ERR_NOT_SELLABLE; legal = s>=1 and major_status[c]==floated and has_completed_or[c] and pool_shares[c]+s<=5 and (p!=d: s<=k ; p==d: s<=k, or (s<=H and successor(c,p,H-s)!=null)); swap_needed = p==d and successor(c,p,H-s)!=null (s<=k: only if another player exceeds H-s; s>k: forced); returns {legal, swap_needed, successor, reason} where reason = null if legal else ERR_NOT_SELLABLE | ERR_POOL_FULL | ERR_TOO_MANY (GAP A20 fixed)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.units_held -> `certificates.units_held` [same module] signature: `units_held(state: GameState, player_id: str, company_id: str) -> int` 
- calls drv.successor -> `certificates.successor` [same module] signature: `successor(state: GameState, company_id: str, director_id: str, remaining_units: int) -> str | None` 

**State touched**:
- reads `st.ordinary_certs` (Ordinary certificates held): Number of ordinary 10% certificates a player holds in a major company. EXCLUDES the director's certificate, which is stored in director_holder. units_held = ordinary_certs + director units; certs_held = ordinary_certs + (1 if director). [type int map (player, major)->int; unit certificates = units of 10% (ordinary share = 1 unit); scope per player per major company]
- reads `st.director_holder` (Director's certificate holder): Holder of the director's certificate of a major company (null until the company is started). The director's certificate = cert_units units (2; LNWR 1) but ONE certificate for limit counting. [type map major->player|null; unit -; scope per major company]
- reads `st.pool_shares` (Bank-pool shares): Ordinary certificates in the bank pool. Max 5 (50%) (4.4.2). [type int map major->int; unit ordinary certificates = units of 10%; scope per major company]
- reads `st.major_status` (Major company status): Floated once its concession is converted (4.7.3). Phase-5 direct formation deferred (R11). [type map major->enum {unstarted, floated}; unit -; scope per major company]
- reads `st.has_completed_or` (Has completed an operating round): True once the major company has completed one operating turn; shares cannot be sold before (4.4.2). Initial false at flotation (set false by convert_concession), set true by advance_company when the company finished its turn. [type map major->bool; unit -; scope per major company]

**Rules constraining this node**:
- R5: Director may sell everything only if another player holds >= director's-certificate units (2; LNWR 1) and more than the remaining holding; ties -> nearest after seller in player order. [formula]
- 4.4.2: Not before company completed an OR; pool <= 50%; director's certificate cannot go into the pool; succession exchange precedes the rest of the sale. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Units vs certificates** [repr.units_vs_certificates]: maps to: Player.shares[company_id] = UNITS of 10% INCLUDING the director's certificate (2 units; LNWR 1)
  rule for coder: units_held(p,c) = Player.shares.get(c,0); ordinary_certs(p,c) = units_held - cert_units(c) if p is the director else units_held; certs_held(p,c) = ordinary_certs + (1 if director). Always read with .get(c, 0); zero entries may exist. A swap_director changes NO Player.shares value.
- **Director's certificate** [repr.director_certificate]: maps to: MajorCompanyState.director_player_id (None until started) + cert_units units inside Player.shares[c]
  rule for coder: ONE certificate for the limit regardless of its units; the holder's Player.shares includes the units; it is never in shares_in_treasury or shares_in_bank_pool; LNWR director = 1 unit.
- **Bank pool naming** [repr.bank_pool_naming]: maps to: SHARES: MajorCompanyState.shares_in_bank_pool (units, max 5) = 'the bank pool'; TRAINS: BankState.discarded_trains (list of codes) = 'the bank pool' of trains
  rule for coder: buy_share source strings: 'bank' and 'pool' BOTH mean the bank pool of shares; 'treasury' = MajorCompanyState.shares_in_treasury (ordinary units only, the director's certificate is never in it; LNWR 9, others 8 at flotation); None = module chooses (pool first, else treasury).
- **Company status mirrors** [repr.company_status]: maps to: MajorCompanyState.floated / concession_converted / has_operated / share_price; MinorCompanyState.floated / share_price / removed / acquired_by_major
  rule for coder: floated=True and concession_converted=True on conversion; has_operated False at flotation, True after the first completed operating turn (advance_company); share_price is a display mirror nobody reads (read prices from the grid via current_price).


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA20** (gap A.2.20, severity S2, kind graph_fix): SaleCheck gains a reason field (None | ERR_NOT_SELLABLE | ERR_POOL_FULL | ERR_TOO_MANY); sell_shares maps reasons to the three codes.
  reason: exposes the failing clause.
- **GA30** (gap A.2.30, severity S3, kind decision): sale_legal for an unknown, minor or unstarted company returns SaleCheck(False, False, None, 'ERR_NOT_SELLABLE'); can_sell_any scans only floated majors.
  reason: total function.
- **GA08** (gap A.1.8, severity S2, kind graph_fix): In scope now: active_company_id, advance_company, start/begin/end of operating rounds, set size lock, game_over maturity, has_completed_or writer (advance_company), start-of-OR revenues. States or_set_size, or_index, or_order, or_current, round_type added; phase_events is an audit log only.
  reason: required by actions.py/main.py; without a writer of has_operated no share could ever be sold.
- **GB06** (gap B-6, severity S2, kind graph_fix): advance_company writes has_completed_or for a major (now a graph effect, state no longer external).
  reason: GA08.

### `certificates.cert_units` (function)

```python
cert_units(company_id: str) -> int
```

- parameters: ['company_id']
- defaults (explicit): (none)
- returns: 1 if company_id == 'LNWR' else 2
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): certificates.successor, certificates.swap_director, certificates.units_held, company_formation.convert_concession

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- no exception for unknown ids

**Implements graph node(s)**: `drv.cert_units`

#### Graph node `drv.cert_units` (derived) - Director certificate units
Units of 10% that a director's certificate counts as.

- graph signature (abstract): params = ['major company c']; returns = int

**Formula**: [3.3.2] 1 if c = LNWR else 2. As certificates the director's certificate always counts exactly 1.

**Constants used**:
- `const.share_structure` (Share structure of a major company): Total 10 units. Standard major: director's certificate = 2 units, 8 ordinary certificates of 1 unit. LNWR: director's certificate = 1 unit, 9 ordinary certificates. Minor: one director's certificate worth 2 shares, no other shares (3.2.2). Pool cap 5 units (4.4.2); player cap 6 units (4.5.6).; data: `{"total_units": 10, "standard": {"director_units": 2, "ordinary_certs": 8}, "lnwr": {"director_units": 1, "ordinary_certs": 9}, "pool_cap_units": 5, "hold_cap_units": 6}`

**Rules constraining this node**:
- 3.3.2: 9 certificates (director 20% = two shares + eight 10%); LNWR 10 certificates. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Director's certificate** [repr.director_certificate]: maps to: MajorCompanyState.director_player_id (None until started) + cert_units units inside Player.shares[c]
  rule for coder: ONE certificate for the limit regardless of its units; the holder's Player.shares includes the units; it is never in shares_in_treasury or shares_in_bank_pool; LNWR director = 1 unit.


### `certificates.ordinary_certs` (function)

```python
ordinary_certs(state: GameState, player_id: str, company_id: str) -> int
```

- parameters: ['state', 'player_id', 'company_id']
- defaults (explicit): (none)
- returns: Player.shares.get(c,0) - cert_units(c) if the player is the director else Player.shares.get(c,0)
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): none
- api notes: Accessor of the DERIVED state node st.ordinary_certs (units, director's certificate excluded).

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- unknown ids: 0

**Implements graph node(s)**: `st.ordinary_certs`

#### Graph node `st.ordinary_certs` (state) - Ordinary certificates held
Number of ordinary 10% certificates a player holds in a major company. EXCLUDES the director's certificate, which is stored in director_holder. units_held = ordinary_certs + director units; certs_held = ordinary_certs + (1 if director).


**Representation notes (repr nodes bound to touched states / this node)**:
- **Units vs certificates** [repr.units_vs_certificates]: maps to: Player.shares[company_id] = UNITS of 10% INCLUDING the director's certificate (2 units; LNWR 1)
  rule for coder: units_held(p,c) = Player.shares.get(c,0); ordinary_certs(p,c) = units_held - cert_units(c) if p is the director else units_held; certs_held(p,c) = ordinary_certs + (1 if director). Always read with .get(c, 0); zero entries may exist. A swap_director changes NO Player.shares value.


### `certificates.units_held` (function)

```python
units_held(state: GameState, player_id: str, company_id: str) -> int
```

- parameters: ['state', 'player_id', 'company_id']
- defaults (explicit): (none)
- returns: = Player.shares.get(c, 0)
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): certificates.SaleCheck, certificates.sale_legal, certificates.successor, scoring.player_wealth, shares.buy_share

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- unknown ids: 0

**Implements graph node(s)**: `drv.units_held`

#### Graph node `drv.units_held` (derived) - Units held
Units of 10% a player holds in a major company.

- graph signature (abstract): params = ['player p', 'major c']; returns = int

**Formula**: [4.5.6] ordinary_certs[p,c] + (cert_units(c) if director_holder[c] == p else 0)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.cert_units -> `certificates.cert_units` [same module] signature: `cert_units(company_id: str) -> int` 

**State touched**:
- reads `st.ordinary_certs` (Ordinary certificates held): Number of ordinary 10% certificates a player holds in a major company. EXCLUDES the director's certificate, which is stored in director_holder. units_held = ordinary_certs + director units; certs_held = ordinary_certs + (1 if director). [type int map (player, major)->int; unit certificates = units of 10% (ordinary share = 1 unit); scope per player per major company]
- reads `st.director_holder` (Director's certificate holder): Holder of the director's certificate of a major company (null until the company is started). The director's certificate = cert_units units (2; LNWR 1) but ONE certificate for limit counting. [type map major->player|null; unit -; scope per major company]

**Rules constraining this node**:
- 4.5.6: No further certificates once holding 60% of the company. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Units vs certificates** [repr.units_vs_certificates]: maps to: Player.shares[company_id] = UNITS of 10% INCLUDING the director's certificate (2 units; LNWR 1)
  rule for coder: units_held(p,c) = Player.shares.get(c,0); ordinary_certs(p,c) = units_held - cert_units(c) if p is the director else units_held; certs_held(p,c) = ordinary_certs + (1 if director). Always read with .get(c, 0); zero entries may exist. A swap_director changes NO Player.shares value.
- **Director's certificate** [repr.director_certificate]: maps to: MajorCompanyState.director_player_id (None until started) + cert_units units inside Player.shares[c]
  rule for coder: ONE certificate for the limit regardless of its units; the holder's Player.shares includes the units; it is never in shares_in_treasury or shares_in_bank_pool; LNWR director = 1 unit.


### `certificates.certs_held` (function)

```python
certs_held(state: GameState, player_id: str, company_id: str) -> int
```

- parameters: ['state', 'player_id', 'company_id']
- defaults (explicit): (none)
- returns: major: ordinary + (1 if director); minor: 1 if director_player_id == player else 0
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): certificates.cert_count_holdings

**Exceptions**:

| class | code | when |
|---|---|---|
| CertificateError | ERR_UNKNOWN_COMPANY | company id in neither state.majors nor state.minors |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. company_id in state.majors or state.minors -> `ERR_UNKNOWN_COMPANY`

**Implements graph node(s)**: `drv.certs_held`

#### Graph node `drv.certs_held` (derived) - Certificates held
Number of certificate cards a player holds in a company, for limit counting.

- graph signature (abstract): params = ['player p', 'company c']; returns = int

**Formula**: [4.2.2] major: ordinary_certs[p,c] + (1 if director_holder[c]==p else 0); minor: 1 if minor_director[c]==p else 0

**State touched**:
- reads `st.ordinary_certs` (Ordinary certificates held): Number of ordinary 10% certificates a player holds in a major company. EXCLUDES the director's certificate, which is stored in director_holder. units_held = ordinary_certs + director units; certs_held = ordinary_certs + (1 if director). [type int map (player, major)->int; unit certificates = units of 10% (ordinary share = 1 unit); scope per player per major company]
- reads `st.director_holder` (Director's certificate holder): Holder of the director's certificate of a major company (null until the company is started). The director's certificate = cert_units units (2; LNWR 1) but ONE certificate for limit counting. [type map major->player|null; unit -; scope per major company]
- reads `st.minor_director` (Minor director's certificate holder): Player holding the 50% director's certificate of a minor (counts 1 certificate; assumption A6). Non-null = purchased and floated. [type map minor->player|null; unit -; scope per minor company]

**Rules constraining this node**:
- 4.2.2: Privates, concessions and stock certificates owned by players count (P16 deferred R11). [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Units vs certificates** [repr.units_vs_certificates]: maps to: Player.shares[company_id] = UNITS of 10% INCLUDING the director's certificate (2 units; LNWR 1)
  rule for coder: units_held(p,c) = Player.shares.get(c,0); ordinary_certs(p,c) = units_held - cert_units(c) if p is the director else units_held; certs_held(p,c) = ordinary_certs + (1 if director). Always read with .get(c, 0); zero entries may exist. A swap_director changes NO Player.shares value.
- **Director's certificate** [repr.director_certificate]: maps to: MajorCompanyState.director_player_id (None until started) + cert_units units inside Player.shares[c]
  rule for coder: ONE certificate for the limit regardless of its units; the holder's Player.shares includes the units; it is never in shares_in_treasury or shares_in_bank_pool; LNWR director = 1 unit.
- **Minor company ownership** [repr.minor_ownership]: maps to: MinorCompanyState.director_player_id (non-None after award); NO entry in Player.shares; id 'M<n>'
  rule for coder: A minor counts 1 certificate for its director (certs_held dispatches on `cid in state.minors`). floated=True is set by float_minors; removed=True for a removed minor (director stays None). Follows the graph, not the models.py comment (decision GA10).


### `certificates.cert_limit` (function)

```python
cert_limit(state: GameState) -> int
```

- parameters: ['state']
- defaults (explicit): (none)
- returns: SETUP_BY_PLAYER_COUNT[len(player_order)].certificate_limit
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.place_or_move_bid, certificates.over_limit, shares.buy_share

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.cert_limit`

#### Graph node `drv.cert_limit` (derived) - Certificate limit
Limit for the current player count.

- graph signature (abstract): params = ['none']; returns = int

**Formula**: [4.2.1] const.cert_limit[player_count] (26/20/16/13/11 for 3..7 players)

**State touched**:
- reads `st.player_count` (Player count): Number of players n; set once at setup. [type int 3..7; unit players; scope game]

**Constants used**:
- `const.cert_limit` (Certificate limit table): Certificate limit per player count (4.2.1, 1.7.2). The rulebook shows only column headers; the values are in the given data table.; data: `{"table": {"3": 26, "4": 20, "5": 16, "6": 13, "7": 11}}`
  (in code: app.data.setup.SETUP_BY_PLAYER_COUNT[n].certificate_limit)

**Rules constraining this node**:
- 4.2.1: Each certificate counts against a limit set by player count. [formula]
- 4.2.2: Privates, concessions and stock certificates owned by players count (P16 deferred R11).

**Representation notes (repr nodes bound to touched states / this node)**:
- **Stock-turn order** [repr.sr_order]: maps to: state.player_order (list, index 0 = Player-1 card) AND state.priority_deal_player_id
  rule for coder: player_count = len(state.player_order) (3..7; no stored field). Invariant: priority_deal_player_id == player_order[0]. Writers of player_order (reorder_players_by_cash, setup) rewrite priority_deal_player_id too; start_stock_round re-asserts it.


### `certificates.cert_count_holdings` (function)

```python
cert_count_holdings(state: GameState, player_id: str) -> int
```

- parameters: ['state', 'player_id']
- defaults (explicit): (none)
- returns: certificates counted against the limit; yellow-zone companies count 0; privates and concessions 1 each
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): certificates.cert_count

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.cert_count_holdings`

#### Graph node `drv.cert_count_holdings` (derived) - Certificates held counted against the limit
Certificates a player owns that count toward the limit.

- graph signature (abstract): params = ['player p']; returns = int

**Formula**: [4.2.2, 3.1.5, 3.4.3, 4.2.3] sum over majors and minors c of (0 if in_yellow(c) else certs_held(p,c)) + |player_privates[p]| + |player_concessions[p]| (P16 not exempted, R11)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.certs_held -> `certificates.certs_held` [same module] signature: `certs_held(state: GameState, player_id: str, company_id: str) -> int` 
- calls drv.in_yellow -> `turn_order.in_yellow` [CROSS-MODULE] signature: `in_yellow(state: GameState, company_id: str) -> bool` 

**State touched**:
- reads `st.player_privates` (Privates held): Private companies held by each player. [type map player->set<private>; unit private certificates; scope per player]
- reads `st.player_concessions` (Concessions held): Concession certificates a player holds (acquired after resolution, 4.7.5). Removed at phase 5 (R9). [type map player->set<major>; unit concession certificates; scope per player]

**Rules constraining this node**:
- 3.4.3: Concessions count toward the owner's certificate limit. [formula]
- 4.2.2: Privates, concessions and stock certificates owned by players count (P16 deferred R11). [formula]
- 4.2.3: Share certificates of a company in the yellow zone don't count. [formula]
- 3.1.5: Privates held by players count against the certificate limit (P16 exception deferred R11). [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Private company** [repr.private_company]: maps to: Player.private_companies: list[int]; PrivateCompanyState(number, owner_player_id mirror, owner_company_id, closed, treasury_credit)
  rule for coder: pay_private_revenues pays every open private: if owner_company_id is set -> that company's treasury, else the player holding it in Player.private_companies; closed privates pay nothing.
- **Concession** [repr.concession]: maps to: Player.concessions: list[str] of major abbr; BidBoxItem(kind='concession', ref=abbr); MajorCompanyState.concession_holder_player_id mirrors the holder (None after conversion/clearing); concession_converted True after conversion
  rule for coder: Removal at phase 5 = absent from stack, boxes and players (no field). Writers keep the mirror fields consistent (vacate_box_item sets, convert_concession/clear_concession_boxes clear).


### `certificates.cert_count` (function)

```python
cert_count(state: GameState, player_id: str) -> int
```

- parameters: ['state', 'player_id']
- defaults (explicit): (none)
- returns: cert_count_holdings + bidding.items_led (LAZY import)
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.place_or_move_bid, certificates.over_limit, shares.buy_share

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.cert_count`

#### Graph node `drv.cert_count` (derived) - Certificate count incl. leading bids
Count used for every 'at the limit' test.

- graph signature (abstract): params = ['player p']; returns = int

**Formula**: [4.2.5, 4.10.8] cert_count_holdings(p) + items_led(p)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.cert_count_holdings -> `certificates.cert_count_holdings` [same module] signature: `cert_count_holdings(state: GameState, player_id: str) -> int` 
- calls drv.items_led -> `bidding.items_led` [CROSS-MODULE] signature: `items_led(state: GameState, player_id: str) -> int` 

**Rules constraining this node**:
- 4.10.8: No placing/moving at the limit; leading bids count. [formula]
- 4.2.5: At the limit a player may not bid; each item on which they hold the highest bid counts as a certificate. [formula]


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GB19** (gap B-19, severity S3, kind decision): Layers: 1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares + company_formation, 6 bidding, 7 round_manager; upward calls are lazy imports (api node attrs.layer; lazy edges: turn_order->scoring.check_game_end_triggers, turn_order->certificates.fully_sold, certificates->bidding.items_led, trains->bidding.clear_concession_boxes, bidding->nothing upward now that resolve_stock_round has no sr_over check).
  reason: circular imports.

### `certificates.over_limit` (function)

```python
over_limit(state: GameState, player_id: str) -> bool
```

- parameters: ['state', 'player_id']
- defaults (explicit): (none)
- returns: cert_count > cert_limit
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): certificates.must_sell

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.over_limit`

#### Graph node `drv.over_limit` (derived) - Over the limit?
True when a player holds more than the limit.

- graph signature (abstract): params = ['player p']; returns = bool

**Formula**: [4.2.6, 4.4.7] cert_count(p) > cert_limit

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.cert_count -> `certificates.cert_count` [same module] signature: `cert_count(state: GameState, player_id: str) -> int` 
- calls drv.cert_limit -> `certificates.cert_limit` [same module] signature: `cert_limit(state: GameState) -> int` 

**Rules constraining this node**:
- 4.4.7: A player over the limit must sell what they can at the first opportunity. [formula]
- 4.2.6: A player over the limit must sell down. [formula]


### `certificates.successor` (function)

```python
successor(state: GameState, company_id: str, director_id: str, remaining_units: int) -> str | None
```

- parameters: ['state', 'company_id', 'director_id', 'remaining_units']
- defaults (explicit): (none)
- returns: eligible successor or None (R5)
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): certificates.SaleCheck, certificates.sale_legal

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.successor`

#### Graph node `drv.successor` (derived) - Eligible successor director
Player who would become director if the director's remaining holding is r.

- graph signature (abstract): params = ['major c', 'director d', 'remaining units r']; returns = player|null

**Formula**: [4.4.2, R5] candidates = {q != d : units_held(q,c) >= cert_units(c) and units_held(q,c) > r}; none -> null; else max units_held; tie -> the tying player closest after d in sr_order (cyclic, forward)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.units_held -> `certificates.units_held` [same module] signature: `units_held(state: GameState, player_id: str, company_id: str) -> int` 
- calls drv.cert_units -> `certificates.cert_units` [same module] signature: `cert_units(company_id: str) -> int` 

**State touched**:
- reads `st.sr_order` (Stock-turn order): Order in which players take stock turns; random at setup (1.7.12); recomputed by cash at each stock-round end (4.11.9). Also the direction for 'nearest after' tie-breaks (4.4.2). The player holding card 1 (index 0) is the start player of every stock round. [type list<player>; unit player ids, index 0 = Player 1 card; scope game]

**Rules constraining this node**:
- R5: Director may sell everything only if another player holds >= director's-certificate units (2; LNWR 1) and more than the remaining holding; ties -> nearest after seller in player order. [formula]
- 4.4.2: Not before company completed an OR; pool <= 50%; director's certificate cannot go into the pool; succession exchange precedes the rest of the sale. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Stock-turn order** [repr.sr_order]: maps to: state.player_order (list, index 0 = Player-1 card) AND state.priority_deal_player_id
  rule for coder: player_count = len(state.player_order) (3..7; no stored field). Invariant: priority_deal_player_id == player_order[0]. Writers of player_order (reorder_players_by_cash, setup) rewrite priority_deal_player_id too; start_stock_round re-asserts it.


### `certificates.sale_legal` (function)

```python
sale_legal(state: GameState, player_id: str, company_id: str, count: int = 1) -> SaleCheck
```

- parameters: ['state', 'player_id', 'company_id', 'count']
- defaults (explicit): {"count": "1"}
- returns: SaleCheck; never raises for illegal sales (reason says why)
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): certificates.can_sell_any, shares.sell_shares

**Exceptions**: none raised.

**Must NOT be checked by this function**:
- raises nothing: an unknown or non-major company id gives SaleCheck(False, False, None, 'ERR_NOT_SELLABLE')

**Implements graph node(s)**: `drv.sale_legal`

#### Graph node `drv.sale_legal` (derived) - Is a sale legal?
Whether player p may sell s shares of company c, what directorship change that causes, and why not.

- graph signature (abstract): params = ['player p', 'major c', 'count s']; returns = record

**Formula**: [4.4.2, R5] let k=ordinary_certs[p,c], H=units_held(p,c), d=director_holder[c]; if c is not a started major: legal=false, reason=ERR_NOT_SELLABLE; legal = s>=1 and major_status[c]==floated and has_completed_or[c] and pool_shares[c]+s<=5 and (p!=d: s<=k ; p==d: s<=k, or (s<=H and successor(c,p,H-s)!=null)); swap_needed = p==d and successor(c,p,H-s)!=null (s<=k: only if another player exceeds H-s; s>k: forced); returns {legal, swap_needed, successor, reason} where reason = null if legal else ERR_NOT_SELLABLE | ERR_POOL_FULL | ERR_TOO_MANY (GAP A20 fixed)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.units_held -> `certificates.units_held` [same module] signature: `units_held(state: GameState, player_id: str, company_id: str) -> int` 
- calls drv.successor -> `certificates.successor` [same module] signature: `successor(state: GameState, company_id: str, director_id: str, remaining_units: int) -> str | None` 

**State touched**:
- reads `st.ordinary_certs` (Ordinary certificates held): Number of ordinary 10% certificates a player holds in a major company. EXCLUDES the director's certificate, which is stored in director_holder. units_held = ordinary_certs + director units; certs_held = ordinary_certs + (1 if director). [type int map (player, major)->int; unit certificates = units of 10% (ordinary share = 1 unit); scope per player per major company]
- reads `st.director_holder` (Director's certificate holder): Holder of the director's certificate of a major company (null until the company is started). The director's certificate = cert_units units (2; LNWR 1) but ONE certificate for limit counting. [type map major->player|null; unit -; scope per major company]
- reads `st.pool_shares` (Bank-pool shares): Ordinary certificates in the bank pool. Max 5 (50%) (4.4.2). [type int map major->int; unit ordinary certificates = units of 10%; scope per major company]
- reads `st.major_status` (Major company status): Floated once its concession is converted (4.7.3). Phase-5 direct formation deferred (R11). [type map major->enum {unstarted, floated}; unit -; scope per major company]
- reads `st.has_completed_or` (Has completed an operating round): True once the major company has completed one operating turn; shares cannot be sold before (4.4.2). Initial false at flotation (set false by convert_concession), set true by advance_company when the company finished its turn. [type map major->bool; unit -; scope per major company]

**Rules constraining this node**:
- R5: Director may sell everything only if another player holds >= director's-certificate units (2; LNWR 1) and more than the remaining holding; ties -> nearest after seller in player order. [formula]
- 4.4.2: Not before company completed an OR; pool <= 50%; director's certificate cannot go into the pool; succession exchange precedes the rest of the sale. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Units vs certificates** [repr.units_vs_certificates]: maps to: Player.shares[company_id] = UNITS of 10% INCLUDING the director's certificate (2 units; LNWR 1)
  rule for coder: units_held(p,c) = Player.shares.get(c,0); ordinary_certs(p,c) = units_held - cert_units(c) if p is the director else units_held; certs_held(p,c) = ordinary_certs + (1 if director). Always read with .get(c, 0); zero entries may exist. A swap_director changes NO Player.shares value.
- **Director's certificate** [repr.director_certificate]: maps to: MajorCompanyState.director_player_id (None until started) + cert_units units inside Player.shares[c]
  rule for coder: ONE certificate for the limit regardless of its units; the holder's Player.shares includes the units; it is never in shares_in_treasury or shares_in_bank_pool; LNWR director = 1 unit.
- **Bank pool naming** [repr.bank_pool_naming]: maps to: SHARES: MajorCompanyState.shares_in_bank_pool (units, max 5) = 'the bank pool'; TRAINS: BankState.discarded_trains (list of codes) = 'the bank pool' of trains
  rule for coder: buy_share source strings: 'bank' and 'pool' BOTH mean the bank pool of shares; 'treasury' = MajorCompanyState.shares_in_treasury (ordinary units only, the director's certificate is never in it; LNWR 9, others 8 at flotation); None = module chooses (pool first, else treasury).
- **Company status mirrors** [repr.company_status]: maps to: MajorCompanyState.floated / concession_converted / has_operated / share_price; MinorCompanyState.floated / share_price / removed / acquired_by_major
  rule for coder: floated=True and concession_converted=True on conversion; has_operated False at flotation, True after the first completed operating turn (advance_company); share_price is a display mirror nobody reads (read prices from the grid via current_price).


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA20** (gap A.2.20, severity S2, kind graph_fix): SaleCheck gains a reason field (None | ERR_NOT_SELLABLE | ERR_POOL_FULL | ERR_TOO_MANY); sell_shares maps reasons to the three codes.
  reason: exposes the failing clause.
- **GA30** (gap A.2.30, severity S3, kind decision): sale_legal for an unknown, minor or unstarted company returns SaleCheck(False, False, None, 'ERR_NOT_SELLABLE'); can_sell_any scans only floated majors.
  reason: total function.
- **GA08** (gap A.1.8, severity S2, kind graph_fix): In scope now: active_company_id, advance_company, start/begin/end of operating rounds, set size lock, game_over maturity, has_completed_or writer (advance_company), start-of-OR revenues. States or_set_size, or_index, or_order, or_current, round_type added; phase_events is an audit log only.
  reason: required by actions.py/main.py; without a writer of has_operated no share could ever be sold.
- **GB06** (gap B-6, severity S2, kind graph_fix): advance_company writes has_completed_or for a major (now a graph effect, state no longer external).
  reason: GA08.

### `certificates.can_sell_any` (function)

```python
can_sell_any(state: GameState, player_id: str) -> bool
```

- parameters: ['state', 'player_id']
- defaults (explicit): (none)
- returns: exists major c with sale_legal(p, c, 1).legal
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): certificates.must_sell

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.can_sell_any`

#### Graph node `drv.can_sell_any` (derived) - Able to sell anything?
True if at least one sale of one share is legal.

- graph signature (abstract): params = ['player p']; returns = bool

**Formula**: [4.4.7] exists major c: sale_legal(p,c,1).legal

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.sale_legal -> `certificates.SaleCheck`, `certificates.sale_legal` [same module] signature: `class SaleCheck(NamedTuple)`; `sale_legal(state: GameState, player_id: str, company_id: str, count: int = 1) -> SaleCheck` 

**State touched**:
- reads `st.major_status` (Major company status): Floated once its concession is converted (4.7.3). Phase-5 direct formation deferred (R11). [type map major->enum {unstarted, floated}; unit -; scope per major company]

**Rules constraining this node**:
- 4.4.7: A player over the limit must sell what they can at the first opportunity. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Company status mirrors** [repr.company_status]: maps to: MajorCompanyState.floated / concession_converted / has_operated / share_price; MinorCompanyState.floated / share_price / removed / acquired_by_major
  rule for coder: floated=True and concession_converted=True on conversion; has_operated False at flotation, True after the first completed operating turn (advance_company); share_price is a display mirror nobody reads (read prices from the grid via current_price).


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA30** (gap A.2.30, severity S3, kind decision): sale_legal for an unknown, minor or unstarted company returns SaleCheck(False, False, None, 'ERR_NOT_SELLABLE'); can_sell_any scans only floated majors.
  reason: total function.

### `certificates.must_sell` (function)

```python
must_sell(state: GameState, player_id: str) -> bool
```

- parameters: ['state', 'player_id']
- defaults (explicit): (none)
- returns: over_limit and can_sell_any
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): bidding.place_or_move_bid, company_formation.convert_concession, shares.buy_share

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.must_sell`

#### Graph node `drv.must_sell` (derived) - Forced to sell?
True when over the limit and able to sell.

- graph signature (abstract): params = ['player p']; returns = bool

**Formula**: [4.4.7, R10] over_limit(p) and can_sell_any(p)

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.over_limit -> `certificates.over_limit` [same module] signature: `over_limit(state: GameState, player_id: str) -> bool` 
- calls drv.can_sell_any -> `certificates.can_sell_any` [same module] signature: `can_sell_any(state: GameState, player_id: str) -> bool` 

**Rules constraining this node**:
- 4.4.7: A player over the limit must sell what they can at the first opportunity. [formula]
- R10: Over the limit must sell down at first opportunity; while over and able to sell the player may not buy or bid. [formula]
- 4.2.6: A player over the limit must sell down.


### `certificates.fully_sold` (function)

```python
fully_sold(state: GameState, company_id: str) -> bool
```

- parameters: ['state', 'company_id']
- defaults (explicit): (none)
- returns: floated major with 0 treasury units and 0 pool units; minors and unknown ids False
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): turn_order.raise_sold_out_prices

**Exceptions**: none raised.

**Implements graph node(s)**: `drv.fully_sold`

#### Graph node `drv.fully_sold` (derived) - Company 100% in players' hands?
Sold-out test for the price rise.

- graph signature (abstract): params = ['major c']; returns = bool

**Formula**: [4.12.1, R13, 4.12.3] major_status[c]==floated and treasury_shares[c]==0 and pool_shares[c]==0 (minors: always false)

**State touched**:
- reads `st.major_status` (Major company status): Floated once its concession is converted (4.7.3). Phase-5 direct formation deferred (R11). [type map major->enum {unstarted, floated}; unit -; scope per major company]
- reads `st.treasury_shares` (Treasury shares): Ordinary certificates in the company treasury, buyable at the current price (4.5.1, 4.7.3). 8 (LNWR 9) at flotation. [type int map major->int; unit ordinary certificates = units of 10%; scope per major company]
- reads `st.pool_shares` (Bank-pool shares): Ordinary certificates in the bank pool. Max 5 (50%) (4.4.2). [type int map major->int; unit ordinary certificates = units of 10%; scope per major company]

**Rules constraining this node**:
- 4.12.1: 100% in players' hands -> token up one cell; no move at the top. [formula]
- R13: Sold out = treasury and bank pool hold zero units. [formula]
- 4.12.3: Minors are never 100% sold. [formula]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Company status mirrors** [repr.company_status]: maps to: MajorCompanyState.floated / concession_converted / has_operated / share_price; MinorCompanyState.floated / share_price / removed / acquired_by_major
  rule for coder: floated=True and concession_converted=True on conversion; has_operated False at flotation, True after the first completed operating turn (advance_company); share_price is a display mirror nobody reads (read prices from the grid via current_price).
- **Bank pool naming** [repr.bank_pool_naming]: maps to: SHARES: MajorCompanyState.shares_in_bank_pool (units, max 5) = 'the bank pool'; TRAINS: BankState.discarded_trains (list of codes) = 'the bank pool' of trains
  rule for coder: buy_share source strings: 'bank' and 'pool' BOTH mean the bank pool of shares; 'treasury' = MajorCompanyState.shares_in_treasury (ordinary units only, the director's certificate is never in it; LNWR 9, others 8 at flotation); None = module chooses (pool first, else treasury).


**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):
- **GA39** (gap A.2.39, severity S3, kind repr): shares_in_treasury counts ORDINARY units only (8; LNWR 9); the director's certificate is never in it; the models comment 'director cert = 2' does not apply.
  reason: operating._pay_major_dividend counts them as plain units.

### `certificates.swap_director` (function)

```python
swap_director(state: GameState, company_id: str, new_director_id: str) -> None
```

- parameters: ['state', 'company_id', 'new_director_id']
- defaults (explicit): (none)
- returns: (see signature)
- layer: 2
- given name (fixed by given code, never rename): no
- aliases: none
- callers in given code: none
- callers from graph (calls/triggers): shares.buy_share, shares.sell_shares
- api notes: Changes ONLY MajorCompanyState.director_player_id: every Player.shares value is unchanged (units are invariant, T1).

**Exceptions**:

| class | code | when |
|---|---|---|
| CertificateError | ERR_NOT_STARTED | the company has no director |
| CertificateError | ERR_SAME_DIRECTOR | new director already is the director |
| CertificateError | ERR_NOT_ENOUGH_ORDINARY | new director holds fewer than cert_units ordinary certificates |

**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:

1. company has a director -> `ERR_NOT_STARTED`
2. new_director_id != current director -> `ERR_SAME_DIRECTOR`
3. ordinary_certs(new) >= cert_units(c) -> `ERR_NOT_ENOUGH_ORDINARY`

**Implements graph node(s)**: `act.swap_director`

#### Graph node `act.swap_director` (action) - Swap director's certificate
Exchange the director's certificate for ordinary certificates of the new director (3.3.3).

- graph signature (abstract): params = ['major company c', 'new director q']; returns = none

**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):
- [3.3.3] q != director_holder[c] and ordinary_certs[q,c] >= cert_units(c)

**Effects, in order** (execute exactly in this order):
1. [3.3.3] old = director_holder[c]
2. [4.4.2, 4.5.9] ordinary_certs[q,c] -= cert_units(c); ordinary_certs[old,c] += cert_units(c); director_holder[c] = q
3. total units of every holder unchanged; certificate counts change: q -(cert_units-1), old +(cert_units-1) (LNWR: no change)

**Errors listed by the graph node**:
- ERR_NOT_ENOUGH_ORDINARY

**Calls it must make / may trigger** (callee api in brackets):
- calls drv.cert_units -> `certificates.cert_units` [same module] signature: `cert_units(company_id: str) -> int` 

**State touched**:
- reads `st.director_holder` (Director's certificate holder): Holder of the director's certificate of a major company (null until the company is started). The director's certificate = cert_units units (2; LNWR 1) but ONE certificate for limit counting. [type map major->player|null; unit -; scope per major company]
- reads `st.ordinary_certs` (Ordinary certificates held): Number of ordinary 10% certificates a player holds in a major company. EXCLUDES the director's certificate, which is stored in director_holder. units_held = ordinary_certs + director units; certs_held = ordinary_certs + (1 if director). [type int map (player, major)->int; unit certificates = units of 10% (ordinary share = 1 unit); scope per player per major company]
- writes `st.ordinary_certs` (Ordinary certificates held): Number of ordinary 10% certificates a player holds in a major company. EXCLUDES the director's certificate, which is stored in director_holder. units_held = ordinary_certs + director units; certs_held = ordinary_certs + (1 if director). [type int map (player, major)->int; unit certificates = units of 10% (ordinary share = 1 unit); scope per player per major company]
- writes `st.director_holder` (Director's certificate holder): Holder of the director's certificate of a major company (null until the company is started). The director's certificate = cert_units units (2; LNWR 1) but ONE certificate for limit counting. [type map major->player|null; unit -; scope per major company]

**Rules constraining this node**:
- 3.3.3: Director's certificate belongs to the majority holder; on change it is swapped for two 10% certificates (LNWR one). [demanded in preconditions/effects]
- 4.4.2: Not before company completed an OR; pool <= 50%; director's certificate cannot go into the pool; succession exchange precedes the rest of the sale. [demanded in preconditions/effects]
- 4.5.9: If the buyer exceeds the director's holding, they become director via exchange. [demanded in preconditions/effects]

**Representation notes (repr nodes bound to touched states / this node)**:
- **Director's certificate** [repr.director_certificate]: maps to: MajorCompanyState.director_player_id (None until started) + cert_units units inside Player.shares[c]
  rule for coder: ONE certificate for the limit regardless of its units; the holder's Player.shares includes the units; it is never in shares_in_treasury or shares_in_bank_pool; LNWR director = 1 unit.
- **Units vs certificates** [repr.units_vs_certificates]: maps to: Player.shares[company_id] = UNITS of 10% INCLUDING the director's certificate (2 units; LNWR 1)
  rule for coder: units_held(p,c) = Player.shares.get(c,0); ordinary_certs(p,c) = units_held - cert_units(c) if p is the director else units_held; certs_held(p,c) = ordinary_certs + (1 if director). Always read with .get(c, 0); zero entries may exist. A swap_director changes NO Player.shares value.


## 4. Rules this module is responsible for (id + text, verbatim from the graph)

- **3.1.5** (rule): Privates held by players count against the certificate limit (P16 exception deferred R11). -- constrains `drv.cert_count_holdings`
- **3.3.2** (rule): 9 certificates (director 20% = two shares + eight 10%); LNWR 10 certificates. -- constrains `drv.cert_units`
- **3.3.3** (rule): Director's certificate belongs to the majority holder; on change it is swapped for two 10% certificates (LNWR one). -- constrains `act.swap_director`
- **3.4.3** (rule): Concessions count toward the owner's certificate limit. -- constrains `drv.cert_count_holdings`
- **4.10.8** (rule): No placing/moving at the limit; leading bids count. -- constrains `drv.cert_count`
- **4.12.1** (rule): 100% in players' hands -> token up one cell; no move at the top. -- constrains `drv.fully_sold`
- **4.12.3** (rule): Minors are never 100% sold. -- constrains `drv.fully_sold`
- **4.2.1** (rule): Each certificate counts against a limit set by player count. -- constrains `drv.cert_limit`
- **4.2.2** (rule): Privates, concessions and stock certificates owned by players count (P16 deferred R11). -- constrains `drv.certs_held`, `drv.cert_limit`, `drv.cert_count_holdings`
- **4.2.3** (rule): Share certificates of a company in the yellow zone don't count. -- constrains `drv.cert_count_holdings`
- **4.2.5** (rule): At the limit a player may not bid; each item on which they hold the highest bid counts as a certificate. -- constrains `drv.cert_count`
- **4.2.6** (rule): A player over the limit must sell down. -- constrains `drv.over_limit`, `drv.must_sell`
- **4.4.2** (rule): Not before company completed an OR; pool <= 50%; director's certificate cannot go into the pool; succession exchange precedes the rest of the sale. -- constrains `drv.sale_legal`, `drv.successor`, `act.swap_director`
- **4.4.7** (rule): A player over the limit must sell what they can at the first opportunity. -- constrains `drv.over_limit`, `drv.can_sell_any`, `drv.must_sell`
- **4.5.6** (rule): No further certificates once holding 60% of the company. -- constrains `drv.units_held`
- **4.5.9** (rule): If the buyer exceeds the director's holding, they become director via exchange. -- constrains `act.swap_director`
- **R10** (ruling): Over the limit must sell down at first opportunity; while over and able to sell the player may not buy or bid. -- constrains `drv.must_sell`
- **R13** (ruling): Sold out = treasury and bank pool hold zero units. -- constrains `drv.fully_sold`
- **R5** (ruling): Director may sell everything only if another player holds >= director's-certificate units (2; LNWR 1) and more than the remaining holding; ties -> nearest after seller in player order. -- constrains `drv.sale_legal`, `drv.successor`

