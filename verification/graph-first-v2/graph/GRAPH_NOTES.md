# GRAPH_NOTES v2 - 1822 stock round + trains/phases + round flow, with interface (api), representation (repr) and decision layers

Files: `graph.json` (complete graph, not a diff), `build_graph.py` (generator; all data lives in it; also writes GAP_RESOLUTION.md and stats.json), `check_graph.py` (verifier, `python3 check_graph.py [graph.json] [given_code_dir]`, exit 1 on violations), `GAP_RESOLUTION.md` (every v1 gap with its resolution).
Inputs read: graph v1 (graph.json, notes, builder, checker), RULES.md, RULINGS.md, RULES_v3.md, the v1 contracts/BINDING.md/GAPS.md, and the given code (models, data tables, setup, actions, operating, stock_positions, main, rooms, db). The eight module files that exist in the skeleton directory were NOT read.

## 1. Schema (v1 + v2)
- v1 node types: rule, ruling, entity, state, action, derived, component, constant (see v1 notes; attrs unchanged). New node ids: `api.<module>.<name>`, `repr.<name>`, `decision.<GA|GB|DN><nn>`, `ruling.R6b`.
- `api` (one per public function, per exception class, per shared constant of the 8 modules): attrs module, name, kind (function|exception|class|constant), signature (python text WITH defaults, syntax-checked), params, defaults (explicit dict), returns, raises [{class, code, when}], enforced [{n, check, code}] (ORDERED: the first failing check raises = error precedence), not_enforced [text] (what the function must NOT check), given_callers, graph_callers (derived from calls/triggers edges), callers (union), aliases (the module must export every alias), given_name (name fixed by given code), layer (import layering), implements (ids), notes.
- `repr` (where a concept lives in the given data model): concept, maps_to, rule_for_coder, binds [ids], source. Every `state` node is bound by at least one repr node (checked).
- `decision` (resolution of a v1 gap or a new-scope choice): gap id, severity, kind (graph_fix | repr | decision | carried | out_of_scope), choice, reason, needs_owner, resolves [ids].
- New edge types: `implements` (api -> action/derived/state), `binds` (repr -> any), `resolves` (decision -> any), `supersedes` (ruling R6b -> ruling R6).
- Given-code actions have no api: `act.setup_game`, `act.apply_action`, `act.stock_turn_action`, `act.pass_turn`, `act.operate_company` carry `implementation=given` and a `given_symbol` that the checker verifies in the given files.

## 2. Counts (generated)
Nodes: action 44, api 124, component 8, constant 22, decision 82, derived 51, entity 22, repr 33, rule 129, ruling 16, state 41, TOTAL 572
Edges: binds 121, calls 147, constrains 434, implements 92, member_of 95, order 12, overrides 45, part_of 41, reads 163, refers 62, resolves 192, supersedes 1, triggers 42, uses_constant 46, writes 139, TOTAL 1632

## 3. Turn model: the graph follows the skeleton (decision GA01)
actions.py ends the turn after EVERY successful sell_shares / buy_share / convert_concession / bid action. v2 therefore has NO turn stage, no c_used, no acted; the graph node `act.stock_turn_action` (given) models the wrapper: one module call, `bids_this_turn += 1` per bid (by the wrapper, never by bidding), `pass_streak = 0`, then `end_turn` (= advance_stock_player). `act.pass_turn` (given): `pass_streak += 1`, then `end_stock_round` if `sr_over` else `end_turn`. `repay_loans` exists (wired=false). A pass cannot be blocked by must_sell (GA02, needs_owner).

## 4. Round flow
- Stock round 1 is pre-started by setup (round_type STOCK, active player = player_order[0]). `start_stock_round` serves rounds >= 2 and debug: refill boxes, STOCK, reset flags, priority player := order[0], begin_turn.
- Who acts: `turn.active_player`; next = player_order[(i+1) % n]. Turn ends after any turn-ending action or a non-final pass. Round ends when `consecutive_passes >= n` -> `end_stock_round`: phase_before := phase; `resolve_stock_round` (1 resolve_bids, 2 float_minors, 3 unsold_minor_exports, 4 remove_box1_minor_and_export, 5 refill_boxes, 6 charge_interest, 7 raise_sold_out_prices, 8 reorder_players_by_cash, 9 check_game_end_triggers('end_of_stock_round')); `sr_completed += 1`; stop if game_over; else `start_operating_round(phase_before)`.
- Operating-round set: size = ors_per_sr[phase_before] (locked; 1 if trigger next_or; the second OR starts only after the following stock round, 2.1.2). Each OR: step A `pay_private_revenues` then `pay_concession_dividends` (5.2.1 A, 3.1.2, 3.4.4), then the next company is chosen one at a time by `next_operating_company` (minors, then majors, descending share price; recomputed after each company, 5.2.2). `advance_company` marks a major `has_operated`. When nobody is left: `end_operating_round`: matured trigger -> game_over; next OR of the set; else `start_stock_round`.
- Game end (10.1.x): immediate (first SR nothing sold, R6b) sets game_over in step 9; token on a game-end cell: STOCK -> `next_or`, OPERATING -> `or_end`; bank broken: STOCK -> `next_or`, OPERATING -> `or_set_end`; first trigger stands (10.1.2); `next_or` becomes `or_set_end` with set size 1 when the next set starts; `end_operating_round` sets game_over. `final_ranking` implements 10.1.3.
- R6b (provisional ruling, node `ruling.R6b`): 'nothing sold in the first stock round' = no share bought or sold, no concession converted, and no bid-box item WON at resolution. An item nobody can pay for (R8) is not won.

## 5. Trains and phases
Deck = counts per code (L/2 and 7/E are one physical pool each); buying from the bank must follow the front group (5.13.4), face value, train limit checked BEFORE buying (5.13.6/7), at most one E (5.13.11), orientation = the code passed (5.13.8/5.13.10), L->2 upgrade 80 in phases 1-2 (5.13.9), pool trains from phase 3. `phase_check` applies at once: phase, rust of every skipped phase, discard of excess trains (descending share price order, lowest face value first - needs_owner), concession clearing when old < 5 <= new. No floated requirement on purchases. Forced purchase (5.13.2) and company-to-company sales (5.13.3) are deferred rule nodes.

## 6. Interface policy
- Names: every name given code imports or calls is kept exactly (given_name=True): ShareError, buy_share, sell_shares, ConcessionError, convert_concession, BidError, place_or_move_bid, resolve_stock_round, TrainError, buy_train_from_bank, check_game_end_triggers, active_company_id, advance_company, advance_stock_player, end_stock_round, start_stock_round. Other names are the v1 BINDING names; v2 additions: begin_operating_round, end_operating_round, pay_private_revenues, private_revenue, final_ranking, upgrade_l_train, rust_trains, discard_excess_trains, front_group, deck_remaining, train_group, train_cost, train_limit, bid_amount_error, operating_rounds_for_next_set. Aliases are listed per api (attrs.aliases) and must be exported.
- Exceptions (GA38): one class per module, derived directly from Exception, message `<ERR_CODE>: <text>`, attribute `.code`: shares.ShareError, certificates.CertificateError, company_formation.ConcessionError, bidding.BidError, turn_order.MarketError, trains.TrainError, scoring.ScoringError, round_manager.RoundError.
- Atomicity (DN10): validate everything before the first mutation. Preconditions NOT enforced on purpose: resolve_stock_round and end_stock_round do not check sr_over or round type (GA37); buy_train_from_bank does not require a floated company (DN04); module functions do not check round type / active player (actions.py does); start_stock_round has no 'already running' check (GA05).
- Import layering: 1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares, 5 company_formation, 6 bidding, 7 round_manager; upward calls are lazy imports.
- Component -> module mapping: decision DN11.

## 7. Public API per module (generated; functions, classes, constants)

### shares (layer 5)
- `class ShareError(Exception)`  [given name]
- `SOURCE_BANK = 'bank'`
- `SOURCE_POOL = 'pool'`
- `SOURCE_TREASURY = 'treasury'`
- `interest_amount(loans: int) -> int`  aliases: loan_interest
- `charge_interest(state: GameState) -> None`  aliases: apply_interest
- `sell_shares(state: GameState, player_id: str, company_id: str, count: int = 1) -> None`  [given name]  aliases: sell_share
- `buy_share(state: GameState, player_id: str, company_id: str, source: str | None = None) -> None`  [given name]  aliases: buy_certificate
- `repay_loans(state: GameState, player_id: str, amount: int | None = None) -> None`  aliases: repay_loan

### certificates (layer 2)
- `class CertificateError(Exception)`
- `TOTAL_UNITS = 10`
- `POOL_CAP_UNITS = 5`
- `HOLD_CAP_UNITS = 6`
- `class SaleCheck(NamedTuple)`
- `cert_units(company_id: str) -> int`
- `ordinary_certs(state: GameState, player_id: str, company_id: str) -> int`
- `units_held(state: GameState, player_id: str, company_id: str) -> int`
- `certs_held(state: GameState, player_id: str, company_id: str) -> int`
- `cert_limit(state: GameState) -> int`
- `cert_count_holdings(state: GameState, player_id: str) -> int`
- `cert_count(state: GameState, player_id: str) -> int`
- `over_limit(state: GameState, player_id: str) -> bool`
- `successor(state: GameState, company_id: str, director_id: str, remaining_units: int) -> str | None`
- `sale_legal(state: GameState, player_id: str, company_id: str, count: int = 1) -> SaleCheck`
- `can_sell_any(state: GameState, player_id: str) -> bool`
- `must_sell(state: GameState, player_id: str) -> bool`
- `fully_sold(state: GameState, company_id: str) -> bool`
- `swap_director(state: GameState, company_id: str, new_director_id: str) -> None`

### company_formation (layer 5)
- `class ConcessionError(Exception)`  [given name]
- `MAJOR_START_PRICES = (60, 70, 80, 90, 100)`
- `MINOR_START_PRICES = (50, 60, 70, 80, 90, 100)`
- `convert_concession(state: GameState, player_id: str, abbr: str, start_price: int) -> None`  [given name]  aliases: convert_concession_to_director
- `minor_start_price(phase: int, bid: int) -> int`  aliases: start_price_for_minor
- `minor_start_treasury(phase: int, bid: int, price: int | None = None) -> int`
- `minor_float_order(pending: Iterable[tuple[int, int, int, str]]) -> list[tuple[int, int, int, str]]`
- `float_minors(state: GameState, pending: Iterable[tuple[int, int, int, str]] | None = None) -> None`  aliases: float_minor_companies

### bidding (layer 6)
- `class BidError(Exception)`  [given name]
- `FACE_VALUES = {'concession': 100, 'minor': 100, 'private': 0}`
- `BID_MULTIPLE = 5`
- `MAX_BIDS_PER_TURN = 3`
- `ITEM_KINDS = ('minor', 'concession', 'private')`
- `face_value(kind: str) -> int`
- `highest_bid(item: BidBoxItem) -> int | None`
- `highest_bidder(item: BidBoxItem) -> str | None`
- `committed_money(state: GameState, player_id: str) -> int`
- `items_led(state: GameState, player_id: str) -> int`
- `tokens_total(state: GameState) -> int`
- `tokens_used(state: GameState, player_id: str) -> int`
- `min_legal_bid(item: BidBoxItem) -> int`
- `bid_amount_error(state: GameState, player_id: str, item: BidBoxItem, amount: int) -> str | None`
- `bid_amount_valid(state: GameState, player_id: str, item: BidBoxItem, amount: int) -> bool`
- `item_resolution_order(state: GameState) -> list[tuple[str, int]]`
- `place_or_move_bid(state: GameState, player_id: str, kind: str, box_index: int, amount: int) -> None`  [given name]  aliases: place_bid, move_bid
- `shift_boxes(state: GameState) -> None`
- `refill_boxes(state: GameState) -> None`
- `clear_concession_boxes(state: GameState) -> None`
- `vacate_box_item(state: GameState, kind: str, box_index: int, disposition: str, player_id: str | None = None) -> None`
- `resolve_bids(state: GameState) -> tuple[set[tuple[str, int]], list[tuple[int, int, int, str]]]`
- `unsold_minor_exports(state: GameState, items_with_bids: Iterable[tuple[str, int]] = ()) -> None`
- `remove_box1_minor_and_export(state: GameState) -> None`
- `resolve_stock_round(state: GameState) -> None`  [given name]

### turn_order (layer 1)
- `class MarketError(Exception)`
- `token_cell(state: GameState, company_id: str) -> tuple[int, int] | None`  aliases: market_cell
- `current_price(state: GameState, company_id: str) -> int`  aliases: share_price
- `in_yellow(state: GameState, company_id: str) -> bool`
- `is_game_end_cell(state: GameState, company_id: str) -> bool`
- `start_cell(price: int, kind: str = 'major') -> tuple[int, int]`
- `place_start_token(state: GameState, company_id: str, price: int, kind: str = 'major') -> None`
- `move_token_down(state: GameState, company_id: str, steps: int = 1) -> None`
- `move_token_up(state: GameState, company_id: str) -> None`
- `descending_order(state: GameState, company_ids: Iterable[str]) -> list[str]`  aliases: descending_share_price_order
- `operating_order(state: GameState) -> list[str]`
- `next_operating_company(state: GameState, done: Iterable[str] = ()) -> str | None`
- `compute_stock_round_order(cash: dict[str, int], previous_order: list[str]) -> list[str]`  aliases: next_player_order
- `reorder_players_by_cash(state: GameState) -> None`  aliases: reorder_players
- `raise_sold_out_prices(state: GameState) -> None`

### trains (layer 4)
- `class TrainError(Exception)`  [given name]
- `TRAIN_PHASE = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 'E': 7}`
- `TRAIN_GROUPS = (('L', '2'), ('3',), ('4',), ('5',), ('6',), ('7', 'E'))`
- `SCAN_ORDER = ('L', '2', '3', '4', '5', '6', '7', 'E')`
- `EXPORT_L_ONLY = 'L_only'`
- `EXPORT_NEXT_WITH_PHASE = 'next_with_phase'`
- `MAX_E_TRAINS_PER_COMPANY = 1`
- `phase_of_train(code: str) -> int | None`
- `front_train(state: GameState) -> str | None`
- `front_group(state: GameState) -> tuple[str, ...] | None`  aliases: next_train_group
- `deck_remaining(state: GameState, group: tuple[str, ...]) -> int`
- `train_group(code: str) -> tuple[str, ...]`
- `train_cost(code: str) -> int`
- `train_limit(kind: str, phase: int) -> int`
- `phase_check(state: GameState, code: str) -> None`  aliases: advance_phase, check_phase
- `rust_trains(state: GameState, code: str) -> None`  aliases: rust
- `discard_excess_trains(state: GameState) -> None`  aliases: enforce_train_limit
- `export_train(state: GameState, mode: str) -> None`
- `buy_train_from_bank(state: GameState, company_id: str, kind: str, code: str, source: str | None = None) -> None`  [given name]
- `upgrade_l_train(state: GameState, company_id: str, kind: str) -> None`  aliases: upgrade_l_to_2

### scoring (layer 3)
- `class ScoringError(Exception)`
- `CONTEXT_AFTER_BANK_PAYMENT = 'after_bank_payment'`
- `CONTEXT_AFTER_TOKEN_MOVE = 'after_token_move'`
- `CONTEXT_END_OF_STOCK_ROUND = 'end_of_stock_round'`
- `TRIGGER_NEXT_OR = 'next_or'`
- `TRIGGER_OR_END = 'or_end'`
- `TRIGGER_OR_SET_END = 'or_set_end'`
- `CONCESSION_DIVIDEND = 10`
- `check_game_end_triggers(state: GameState, context: str | None = None) -> None`  [given name]
- `bank_broken(state: GameState) -> bool`
- `player_wealth(state: GameState, player_id: str) -> int`
- `final_ranking(state: GameState) -> list[tuple[str, int]]`  aliases: ranking
- `private_revenue(private_number: int, phase: int) -> int`
- `pay_concession_dividends(state: GameState) -> None`  aliases: pay_concession_revenue
- `pay_private_revenues(state: GameState) -> None`  aliases: pay_private_revenue

### round_manager (layer 7)
- `class RoundError(Exception)`
- `sr_over(state: GameState) -> bool`
- `next_player(state: GameState, player_id: str) -> str`
- `begin_turn(state: GameState, player_id: str) -> None`
- `start_stock_round(state: GameState) -> None`  [given name]
- `advance_stock_player(state: GameState) -> None`  [given name]  aliases: end_turn
- `end_stock_round(state: GameState) -> None`  [given name]
- `active_company_id(state: GameState) -> str | None`  [given name]  aliases: active_company
- `advance_company(state: GameState) -> None`  [given name]
- `start_operating_round(state: GameState, phase_before: int | None = None) -> None`
- `begin_operating_round(state: GameState) -> None`  aliases: start_operating_set_round
- `end_operating_round(state: GameState) -> None`
- `operating_rounds_for_next_set(state: GameState, phase_before: int | None = None) -> int`

## 8. Rules not modelled
- 5.12.x (dividends, price movement of operating): given code operating.py. 5.13.1 is an index fragment. 2.2.7 is empty in the excerpt. 5.13.2 (forced purchase) and 5.13.3 (company-to-company) are deferred nodes. 5.3.1 is modelled only for who decides and step H (buy trains). Private powers and closing (3.1.1, 3.1.7-3.1.10), P15/P20 credit: out of scope. All v1 skips (1.7.x physical set-up, 3.2.x/3.3.x operating details, 4.9.2-4.9.4) stay skipped; 4.8.x/4.6.4 stay deferred (R11).

## 9. Carried v1 assumptions
Assumptions A1-A40 of the v1 notes remain valid unless a decision in GAP_RESOLUTION.md overrides them: A1 (missing data) is closed by the given data tables; A13 (pass definition) is replaced by the skeleton turn model; A6/A7/A9-A11/A14-A17/A21-A24/A26/A28-A30 are unchanged; A18 (phase effects belong to the operating-round module) is now in scope; A29/A30 are refined by the OR-maturity actions.

## 10. needs_owner
- GA02 (A.1.2): pass / end_turn preconditions (must_sell)
- GA22 (A.2.22): buy_share source default
- GA32 (A.2.32): convert_concession limit effect and dead end
- GA34 (A.2.34): Carried assumptions A4, A5, A9, A10, A11, A13, A15, A16, A17, A21-A24, A26, A28
- GA35 (A.2.35): Concession dividends and private revenue
- GA36 (A.2.36): Final scoring and game_over
- GB13 (B-13): buy_share source None default
- DN02 (new): Which train is discarded
- DN05 (new): Forced train purchase and company-to-company sales
- DN08 (new): Company-owned privates and P15/P20
- DN13 (new): Unpaid winner and the sale flag

## 11. Checker result
`python3 check_graph.py` -> see the end of this run (0 violations required); warnings: entities without states (lnwr, stock_market, stock_token), intentional.
