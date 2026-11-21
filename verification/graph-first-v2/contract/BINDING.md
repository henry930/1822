# BINDING: representation notes and call matrix (generated)

## 1. Representation (repr nodes grouped by area)

Each entry: concept, where it lives in the given data model, and the rule the coder must follow. `binds` lists the graph nodes it applies to.

### Certificates, shares and ownership

- **Units vs certificates** (`repr.units_vs_certificates`)
  - maps to: Player.shares[company_id] = UNITS of 10% INCLUDING the director's certificate (2 units; LNWR 1)
  - rule for coder: units_held(p,c) = Player.shares.get(c,0); ordinary_certs(p,c) = units_held - cert_units(c) if p is the director else units_held; certs_held(p,c) = ordinary_certs + (1 if director). Always read with .get(c, 0); zero entries may exist. A swap_director changes NO Player.shares value.
  - binds: `st.ordinary_certs`, `ent.share_certificate`, `drv.units_held`, `drv.certs_held`, `api.certificates.ordinary_certs`
  - source: BINDING T1, GAPS A13/B-1
- **Director's certificate** (`repr.director_certificate`)
  - maps to: MajorCompanyState.director_player_id (None until started) + cert_units units inside Player.shares[c]
  - rule for coder: ONE certificate for the limit regardless of its units; the holder's Player.shares includes the units; it is never in shares_in_treasury or shares_in_bank_pool; LNWR director = 1 unit.
  - binds: `st.director_holder`, `ent.director_certificate`, `ent.lnwr`, `drv.cert_units`
  - source: BINDING A.1/T1
- **Minor company ownership** (`repr.minor_ownership`)
  - maps to: MinorCompanyState.director_player_id (non-None after award); NO entry in Player.shares; id 'M<n>'
  - rule for coder: A minor counts 1 certificate for its director (certs_held dispatches on `cid in state.minors`). floated=True is set by float_minors; removed=True for a removed minor (director stays None). Follows the graph, not the models.py comment (decision GA10).
  - binds: `st.minor_director`, `ent.minor_company`
  - source: GAPS A10
- **Company, item and player keys** (`repr.company_keys`)
  - maps to: major = abbreviation str ('LNWR','GWR','L&YR',...), key of majors/stock_positions/Player.shares/Player.concessions; minor = 'M<n>' (str key) with bare int n in MinorCompanyState.number, minor_stack and BidBoxItem.ref; private = int n; concession = the major's abbr; player = 'p1'..'pN'
  - rule for coder: Item kind strings are 'concession' | 'minor' | 'private'; company kind arguments are 'major' | 'minor'. A concession is NOT a separate object.
  - binds: `ent.major_company`, `ent.minor_company`, `ent.private_company`, `ent.concession`, `ent.player`, `st.concession_stack`, `st.minor_stack`, `st.private_stack`
  - source: BINDING A.0
- **Private company** (`repr.private_company`)
  - maps to: Player.private_companies: list[int]; PrivateCompanyState(number, owner_player_id mirror, owner_company_id, closed, treasury_credit)
  - rule for coder: pay_private_revenues pays every open private: if owner_company_id is set -> that company's treasury, else the player holding it in Player.private_companies; closed privates pay nothing.
  - binds: `st.player_privates`, `st.private_status`, `ent.private_company`, `const.private_revenue_table`
  - source: BINDING A.1; v2
- **Bid boxes** (`repr.boxes_zero_based`)
  - maps to: state.concession_bid_boxes (len 3), state.minor_bid_boxes (len 4), state.private_bid_boxes (len 3): elements BidBoxItem | None, lists keep their length (None padding)
  - rule for coder: Graph 'box number' = list index + 1 ('box 1' = index 0; 'lower box number wins' = lower index). An item's identity in function signatures is (kind, box_index). Box counts: engine.setup.NUM_*_BID_BOXES.
  - binds: `st.box_contents`, `ent.bid_box`, `const.box_counts`
  - source: BINDING T3, GAPS A12
- **Item sitting in a box** (`repr.bid_box_item`)
  - maps to: BidBoxItem(kind, ref, bids): ref is str (abbr) for concession, int for minor and private (the int annotation in models.py is wrong for concessions)
  - rule for coder: state.minors key = f'M{ref}'.
  - binds: `st.box_contents`, `ent.item_stack`
  - source: BINDING T4
- **Bank pool naming** (`repr.bank_pool_naming`)
  - maps to: SHARES: MajorCompanyState.shares_in_bank_pool (units, max 5) = 'the bank pool'; TRAINS: BankState.discarded_trains (list of codes) = 'the bank pool' of trains
  - rule for coder: buy_share source strings: 'bank' and 'pool' BOTH mean the bank pool of shares; 'treasury' = MajorCompanyState.shares_in_treasury (ordinary units only, the director's certificate is never in it; LNWR 9, others 8 at flotation); None = module chooses (pool first, else treasury).
  - binds: `st.pool_shares`, `st.treasury_shares`, `ent.bank_pool`, `ent.company_treasury`, `st.bank_pool_trains`, `api.shares.SOURCE_BANK`, `api.shares.SOURCE_POOL`, `api.shares.SOURCE_TREASURY`
  - source: GAPS A22/A39
- **Cash, loans, bank, treasuries** (`repr.money`)
  - maps to: Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury
  - rule for coder: Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.
  - binds: `st.player_cash`, `st.player_loans`, `st.bank_cash`, `st.company_cash`, `ent.bank`, `ent.loan`, `const.interest`, `const.bank_total`, `const.start_money`
  - source: BINDING A.1
- **Company status mirrors** (`repr.company_status`)
  - maps to: MajorCompanyState.floated / concession_converted / has_operated / share_price; MinorCompanyState.floated / share_price / removed / acquired_by_major
  - rule for coder: floated=True and concession_converted=True on conversion; has_operated False at flotation, True after the first completed operating turn (advance_company); share_price is a display mirror nobody reads (read prices from the grid via current_price).
  - binds: `st.major_status`, `st.has_completed_or`, `st.removed_items`
  - source: BINDING T15/T16, GAPS B-5
- **Train deck** (`repr.train_deck_counts`)
  - maps to: state.bank.train_pool: dict[code, count]; setup: L 22, 2 0, 3 9, 4 6, 5 3, 6 3, 7 16, E 0
  - rule for coder: Groups L/2 and 7/E are ONE physical pool each: remaining(group) = sum of the codes' counts; a card leaves by decrementing the first non-zero code of the group in order (L then 2; 7 then E) whatever side is bought or exported; the side chosen at purchase is recorded only as the code in the company's train list. front_train = first code in L,2,3,4,5,6,7,E with count > 0.
  - binds: `st.train_deck`, `const.train_deck`, `ent.train`, `drv.front_train`, `drv.front_group`, `drv.deck_remaining`
  - source: BINDING T12, GAPS A27
- **Trains of companies and of the bank pool** (`repr.company_trains`)
  - maps to: MajorCompanyState.trains / MinorCompanyState.trains: list[str] of codes ('L','2','3',...,'7','E'); BankState.discarded_trains: list[str] (bank pool, orientation kept)
  - rule for coder: Purchase appends the code chosen; rust removes by code everywhere (companies, pool, deck counts); discard moves one code to discarded_trains; 'E' appears at most once per company.
  - binds: `st.company_trains`, `st.bank_pool_trains`
  - source: v2
- **Values that live only inside one procedure** (`repr.call_scoped`)
  - maps to: items_with_bids -> set[(kind, box_index)] and pending_minor_floats -> list[(minor_number, bid, box_index, buyer_player_id)]: return value of resolve_bids, passed to unsold_minor_exports / float_minors; never stored
  - rule for coder: float_minors(state, pending=None) and unsold_minor_exports(state, items_with_bids=()) therefore take them as parameters (signature change relative to v1).
  - binds: `st.items_with_bids`, `st.pending_minor_floats`
  - source: GAPS A14/B-9
- **Constants not in any data table** (`repr.module_constants`)
  - maps to: FACE_VALUES, BID_MULTIPLE, MAX_BIDS_PER_TURN (bidding); TOTAL_UNITS, POOL_CAP_UNITS, HOLD_CAP_UNITS (certificates); TRAIN_PHASE, TRAIN_GROUPS, SCAN_ORDER (trains); trigger strings (scoring)
  - rule for coder: Values from the data tables (cert limit, tokens, market, trains, phases) are read from app.data.* and never re-typed.
  - binds: `const.face_values`, `const.bid_rules`, `const.share_structure`, `const.stack_setup`, `const.box_counts`
  - source: GAPS A16
- **Company kind arguments** (`repr.kind_args`)
  - maps to: 'major' | 'minor' strings in buy_train_from_bank(state, company_id, kind, code), place_start_token(..., kind) and start_cell(price, kind)
  - rule for coder: Given callers pass 'minor' if company_id in state.minors else 'major'.
  - binds: `api.trains.buy_train_from_bank`, `api.turn_order.place_start_token`
  - source: BINDING A.0
- **Given setup** (`repr.setup_given`)
  - maps to: engine.setup.new_game(game_id, player_names, seed): fills cash, bank 9900, stacks (tops LNWR / M24 / P1), train pool, random order, boxes (via _refill_bid_boxes) and returns a state already inside round 1
  - rule for coder: Do not rewrite; new modules must tolerate its defaults ({} / False / 0).
  - binds: `act.setup_game`
  - source: BINDING A.6

### Bid boxes and concessions

- **Concession** (`repr.concession`)
  - maps to: Player.concessions: list[str] of major abbr; BidBoxItem(kind='concession', ref=abbr); MajorCompanyState.concession_holder_player_id mirrors the holder (None after conversion/clearing); concession_converted True after conversion
  - rule for coder: Removal at phase 5 = absent from stack, boxes and players (no field). Writers keep the mirror fields consistent (vacate_box_item sets, convert_concession/clear_concession_boxes clear).
  - binds: `st.player_concessions`, `ent.concession`, `st.removed_items`
  - source: BINDING A.1, GAPS B-5/B-7
- **Bids and bidding tokens** (`repr.bids`)
  - maps to: BidBoxItem.bids: dict[player_id, int] (one entry = one token on the item's track)
  - rule for coder: highest_bid = max(bids.values()) if bids else None; a bid of 0 is a bid (never `if highest_bid:`). Tokens in use = items with the player in bids. Empty dict = no bid.
  - binds: `st.bids`, `ent.bidding_token`, `drv.highest_bid`, `drv.highest_bidder`, `drv.tokens_used`
  - source: BINDING T11
- **Turn record** (`repr.turn_record`)
  - maps to: state.active_player_id (turn.active_player) and state.bids_this_turn (turn.bids_made); NO fields for stage / c_used / acted (dropped in v2)
  - rule for coder: SKELETON TURN MODEL: every successful sell_shares / buy_share / convert_concession / bid action ends the turn (actions.py calls advance_stock_player). bids_this_turn is incremented by actions.py after each place_or_move_bid and reset by begin_turn; the bidding module only READS it.
  - binds: `st.turn`, `act.stock_turn_action`, `act.end_turn`
  - source: GAPS A1/A6
- **Private revenue strings** (`repr.private_revenue_parse`)
  - maps to: app.data.private_companies.PRIVATE_COMPANIES_BY_NUMBER[n].revenue: '£5', '£10', '£0', '£10x phase', '£5x phase'
  - rule for coder: private_revenue(n, phase): strip '£'; if it ends with 'x phase' multiply by phase.
  - binds: `const.private_revenue_table`, `drv.private_revenue`, `const.concession_dividend`
  - source: v2

### Rounds, turns and order

- **Stock-turn order** (`repr.sr_order`)
  - maps to: state.player_order (list, index 0 = Player-1 card) AND state.priority_deal_player_id
  - rule for coder: player_count = len(state.player_order) (3..7; no stored field). Invariant: priority_deal_player_id == player_order[0]. Writers of player_order (reorder_players_by_cash, setup) rewrite priority_deal_player_id too; start_stock_round re-asserts it.
  - binds: `st.sr_order`, `st.player_count`, `ent.player_order_card`, `act.reorder_players_by_cash`
  - source: BINDING A.1, GAPS A40
- **Stock round start / priority player** (`repr.sr_start_player`)
  - maps to: state.active_player_id = player_order[0] at the start of every stock round
  - rule for coder: Round 1: set by setup.new_game (the first stock round is pre-started, start_stock_round is not called). Later rounds: start_stock_round -> begin_turn(player_order[0]). Order of play inside a round: next_player(state, pid) = player_order[(index+1) % n]; bids_this_turn reset by begin_turn.
  - binds: `st.turn`, `act.start_stock_round`, `act.begin_turn`, `act.setup_game`
  - source: GAPS A4
- **'A sale happened' flag** (`repr.sale_flag`)
  - maps to: state.any_sale_this_stock_round (bool)
  - rule for coder: Set True by: sell_shares, buy_share, convert_concession (module functions themselves; actions.py also sets it after buy and convert), and resolve_bids when a bid-box item is WON (R6b). Reset to False by start_stock_round. Read by check_game_end_triggers(context='end_of_stock_round').
  - binds: `st.sale_happened`, `ruling.R6b`, `act.resolve_bids`
  - source: GAPS A7
- **sold_this_round** (`repr.sold_this_round`)
  - maps to: state.sold_this_round: dict[player_id, list[company_id]] (lists without duplicates, NOT sets: rooms.serialize_state cannot encode sets)
  - rule for coder: Readers: `company_id in state.sold_this_round.get(player_id, ())`. Reset to {} by start_stock_round.
  - binds: `st.sold_this_round`
  - source: GAPS A11
- **Round type** (`repr.round_type`)
  - maps to: state.round_type: Enum RoundType.STOCK / RoundType.OPERATING (compare with the Enum, not strings); no field for sr_status (dropped)
  - rule for coder: STOCK from setup (round 1 is pre-started); OPERATING set by start_operating_round; STOCK again by start_stock_round.
  - binds: `st.round_type`, `act.start_operating_round`, `act.start_stock_round`
  - source: GAPS A5
- **Stock-round counter** (`repr.sr_counter`)
  - maps to: state.stock_rounds_completed (starts 0); state.round_number (starts 1) is NOT maintained by the engine
  - rule for coder: sr_completed = stock_rounds_completed; incremented by end_stock_round AFTER resolve_stock_round returned; the 10.1.1 'first stock round' test is stock_rounds_completed == 0 inside step 9.
  - binds: `st.sr_completed`
  - source: GAPS A42
- **Game end** (`repr.game_end`)
  - maps to: state.game_over: bool and state.end_trigger_pending: None | 'next_or' | 'or_end' | 'or_set_end'
  - rule for coder: graph trigger none = (False, None); immediate = game_over True; 'a trigger exists' = game_over or end_trigger_pending is not None. 'next_or': stock-round trigger, converted to 'or_set_end' with set size 1 when the next OR set starts; 'or_end': token on game-end cell in an OR (ends after that OR); 'or_set_end': bank broken in an OR (ends after the set). game_over is set by check_game_end_triggers (immediate) and by end_operating_round (matured).
  - binds: `st.game_end`, `const.game_end_triggers`, `act.end_operating_round`
  - source: BINDING A.1
- **Operating-round bookkeeping** (`repr.operating_round_state`)
  - maps to: state.operating_rounds_this_set (set size, locked at set start; default 1), state.operating_round_index (0-based), state.operating_order (companies chosen so far), state.current_company_index
  - rule for coder: active_company_id = operating_order[current_company_index] if round_type is OPERATING and the index is in range. The 2.1.2 deferral needs NO extra field: start_operating_round receives phase_before (a local value from end_stock_round) and the set size is ors_per_sr[phase_before], locked in operating_rounds_this_set.
  - binds: `st.or_set_size`, `st.or_index`, `st.or_order`, `st.or_current`, `ent.operating_round`
  - source: GAPS A8

### Other

- **Consecutive passes** (`repr.pass_streak`)
  - maps to: state.consecutive_passes
  - rule for coder: Written ONLY by actions.py (+=1 on pass; =0 after a turn-ending action) and reset by start_stock_round; advance_stock_player must not touch it. Round over when >= len(player_order).
  - binds: `st.pass_streak`, `drv.sr_over`, `act.pass_turn`
  - source: BINDING T6
- **JSON-safe state** (`repr.json_safety`)
  - maps to: rooms.serialize_state does dataclasses.asdict + json.dumps with a default for dataclasses and Enums only
  - rule for coder: After every function the state must contain only int/str/bool/None, lists, dicts with str keys (the tuple-keyed stock_stack is handled by rooms), tuples, dataclasses, Enums: NO sets, NO new attributes on dataclasses.
  - binds: `ent.game`
  - source: BINDING T13

### Stock market and token pile

- **Stock market cells and piles** (`repr.market_cells`)
  - maps to: state.stock_positions[company_id] = (row, col); state.stock_stack[(row, col)] = list of company ids, index 0 = TOP; grid app.data.stock_market.STOCK_MARKET_BY_POSITION[(row, col)] -> StockCell(row, col, value, zone, game_end)
  - rule for coder: Use stock_positions.place_token (removes from the old pile, APPENDS to the new = bottom) only when the cell changes; emptied piles remain as empty lists; down = (row+1, col), up = (row-1, col), absent cell = no move (R12); yellow = zone 'yellow'; game end = game_end True; start cells derived from zone in {'start','minor_start'}. Minors enter after the leading run of minor tokens (4.11.5).
  - binds: `st.market_stack`, `ent.stock_market`, `ent.market_cell`, `ent.stock_token`, `const.market_grid`, `const.yellow_cells`, `const.game_end_cells`, `const.start_cells`
  - source: BINDING T7-T9

### Trains and phases

- **Phase** (`repr.phase_state`)
  - maps to: state.phase: int 1..7; limits and rust from app.data.phases.PHASES_BY_NUMBER; trigger table trains.TRAIN_PHASE (module constant)
  - rule for coder: phase only increases (2.2.1) and is written only by phase_check (plus debug code in main.py). PHASES_BY_NUMBER[n].trains_rusted gives ONE code per phase; skipped phases are rusted too (loop old+1..new).
  - binds: `st.phase`, `const.phase_table`, `const.rust_table`, `api.trains.TRAIN_PHASE`
  - source: BINDING A.1, GAPS A26
- **Phase events** (`repr.phase_log`)
  - maps to: one line per phase change appended to state.log: 'PHASE_EVENT from=<old> to=<new> rusted=<codes comma-separated or -> discarded=<n> or_per_sr=<n>'
  - rule for coder: Audit only; there is no consumer; rust, discard and concession clearing happen inside phase_check.
  - binds: `st.phase_events`
  - source: GAPS B-8

## 2. Call matrix (cross-module edges: calls and triggers between graph nodes implemented in different modules)

Caller module.function -> callee module.api (edge type, graph nodes). A call into a higher layer must be a lazy import.

| caller api | callee api | edge | nodes | callee signature |
|---|---|---|---|---|
| bidding.place_or_move_bid | certificates.cert_count | calls | act.move_bid -> drv.cert_count | cert_count(state: GameState, player_id: str) -> int |
| bidding.place_or_move_bid | certificates.cert_count | calls | act.place_bid -> drv.cert_count | cert_count(state: GameState, player_id: str) -> int |
| bidding.place_or_move_bid | certificates.cert_limit | calls | act.move_bid -> drv.cert_limit | cert_limit(state: GameState) -> int |
| bidding.place_or_move_bid | certificates.cert_limit | calls | act.place_bid -> drv.cert_limit | cert_limit(state: GameState) -> int |
| bidding.place_or_move_bid | certificates.must_sell | calls | act.move_bid -> drv.must_sell | must_sell(state: GameState, player_id: str) -> bool |
| bidding.place_or_move_bid | certificates.must_sell | calls | act.place_bid -> drv.must_sell | must_sell(state: GameState, player_id: str) -> bool |
| bidding.remove_box1_minor_and_export | trains.export_train | calls | act.remove_box1_minor_and_export -> act.export_train | export_train(state: GameState, mode: str) -> None |
| bidding.remove_box1_minor_and_export | trains.export_train | triggers | act.remove_box1_minor_and_export -> act.export_train | export_train(state: GameState, mode: str) -> None |
| bidding.resolve_stock_round | company_formation.float_minors | calls | act.resolve_stock_round -> act.float_minors | float_minors(state: GameState, pending: Iterable[tuple[int, int, int, str]] \| None = None) -> None |
| bidding.resolve_stock_round | company_formation.float_minors | triggers | act.resolve_stock_round -> act.float_minors | float_minors(state: GameState, pending: Iterable[tuple[int, int, int, str]] \| None = None) -> None |
| bidding.resolve_stock_round | scoring.check_game_end_triggers | calls | act.resolve_stock_round -> act.check_game_end_triggers | check_game_end_triggers(state: GameState, context: str \| None = None) -> None |
| bidding.resolve_stock_round | scoring.check_game_end_triggers | triggers | act.resolve_stock_round -> act.check_game_end_triggers | check_game_end_triggers(state: GameState, context: str \| None = None) -> None |
| bidding.resolve_stock_round | shares.charge_interest | calls | act.resolve_stock_round -> act.charge_interest | charge_interest(state: GameState) -> None |
| bidding.resolve_stock_round | shares.charge_interest | triggers | act.resolve_stock_round -> act.charge_interest | charge_interest(state: GameState) -> None |
| bidding.resolve_stock_round | turn_order.raise_sold_out_prices | calls | act.resolve_stock_round -> act.raise_sold_out_prices | raise_sold_out_prices(state: GameState) -> None |
| bidding.resolve_stock_round | turn_order.raise_sold_out_prices | triggers | act.resolve_stock_round -> act.raise_sold_out_prices | raise_sold_out_prices(state: GameState) -> None |
| bidding.resolve_stock_round | turn_order.reorder_players_by_cash | calls | act.resolve_stock_round -> act.reorder_players_by_cash | reorder_players_by_cash(state: GameState) -> None |
| bidding.resolve_stock_round | turn_order.reorder_players_by_cash | triggers | act.resolve_stock_round -> act.reorder_players_by_cash | reorder_players_by_cash(state: GameState) -> None |
| bidding.unsold_minor_exports | trains.export_train | calls | act.unsold_minor_exports -> act.export_train | export_train(state: GameState, mode: str) -> None |
| bidding.unsold_minor_exports | trains.export_train | triggers | act.unsold_minor_exports -> act.export_train | export_train(state: GameState, mode: str) -> None |
| certificates.cert_count | bidding.items_led | calls | drv.cert_count -> drv.items_led | items_led(state: GameState, player_id: str) -> int |
| certificates.cert_count_holdings | turn_order.in_yellow | calls | drv.cert_count_holdings -> drv.in_yellow | in_yellow(state: GameState, company_id: str) -> bool |
| company_formation.convert_concession | certificates.cert_units | calls | act.convert_concession -> drv.cert_units | cert_units(company_id: str) -> int |
| company_formation.convert_concession | certificates.must_sell | calls | act.convert_concession -> drv.must_sell | must_sell(state: GameState, player_id: str) -> bool |
| company_formation.convert_concession | scoring.check_game_end_triggers | calls | act.convert_concession -> act.check_game_end_triggers | check_game_end_triggers(state: GameState, context: str \| None = None) -> None |
| company_formation.convert_concession | turn_order.place_start_token | calls | act.convert_concession -> act.place_start_token | place_start_token(state: GameState, company_id: str, price: int, kind: str = 'major') -> None |
| company_formation.float_minors | scoring.check_game_end_triggers | calls | act.float_minors -> act.check_game_end_triggers | check_game_end_triggers(state: GameState, context: str \| None = None) -> None |
| company_formation.float_minors | turn_order.place_start_token | calls | act.float_minors -> act.place_start_token | place_start_token(state: GameState, company_id: str, price: int, kind: str = 'major') -> None |
| round_manager.advance_company | turn_order.next_operating_company | calls | act.advance_company -> drv.next_operating_company | next_operating_company(state: GameState, done: Iterable[str] = ()) -> str \| None |
| round_manager.begin_operating_round | scoring.pay_concession_dividends | calls | act.begin_operating_round -> act.pay_concession_dividends | pay_concession_dividends(state: GameState) -> None |
| round_manager.begin_operating_round | scoring.pay_concession_dividends | triggers | act.begin_operating_round -> act.pay_concession_dividends | pay_concession_dividends(state: GameState) -> None |
| round_manager.begin_operating_round | scoring.pay_private_revenues | calls | act.begin_operating_round -> act.pay_private_revenues | pay_private_revenues(state: GameState) -> None |
| round_manager.begin_operating_round | scoring.pay_private_revenues | triggers | act.begin_operating_round -> act.pay_private_revenues | pay_private_revenues(state: GameState) -> None |
| round_manager.begin_operating_round | turn_order.next_operating_company | calls | act.begin_operating_round -> drv.next_operating_company | next_operating_company(state: GameState, done: Iterable[str] = ()) -> str \| None |
| round_manager.end_stock_round | bidding.resolve_stock_round | calls | act.end_stock_round -> act.resolve_stock_round | resolve_stock_round(state: GameState) -> None |
| round_manager.end_stock_round | bidding.resolve_stock_round | triggers | act.end_stock_round -> act.resolve_stock_round | resolve_stock_round(state: GameState) -> None |
| round_manager.start_stock_round | bidding.refill_boxes | calls | act.start_stock_round -> act.refill_boxes | refill_boxes(state: GameState) -> None |
| scoring.check_game_end_triggers | turn_order.is_game_end_cell | calls | act.check_game_end_triggers -> drv.is_game_end_cell | is_game_end_cell(state: GameState, company_id: str) -> bool |
| scoring.check_game_end_triggers | turn_order.token_cell | calls | act.check_game_end_triggers -> drv.token_cell | token_cell(state: GameState, company_id: str) -> tuple[int, int] \| None |
| scoring.player_wealth | certificates.units_held | calls | drv.player_wealth -> drv.units_held | units_held(state: GameState, player_id: str, company_id: str) -> int |
| scoring.player_wealth | turn_order.current_price | calls | drv.player_wealth -> drv.current_price | current_price(state: GameState, company_id: str) -> int |
| shares.buy_share | certificates.cert_count | calls | act.buy_share -> drv.cert_count | cert_count(state: GameState, player_id: str) -> int |
| shares.buy_share | certificates.cert_limit | calls | act.buy_share -> drv.cert_limit | cert_limit(state: GameState) -> int |
| shares.buy_share | certificates.must_sell | calls | act.buy_share -> drv.must_sell | must_sell(state: GameState, player_id: str) -> bool |
| shares.buy_share | certificates.swap_director | calls | act.buy_share -> act.swap_director | swap_director(state: GameState, company_id: str, new_director_id: str) -> None |
| shares.buy_share | certificates.units_held | calls | act.buy_share -> drv.units_held | units_held(state: GameState, player_id: str, company_id: str) -> int |
| shares.buy_share | turn_order.current_price | calls | act.buy_share -> drv.current_price | current_price(state: GameState, company_id: str) -> int |
| shares.buy_share | turn_order.in_yellow | calls | act.buy_share -> drv.in_yellow | in_yellow(state: GameState, company_id: str) -> bool |
| shares.sell_shares | certificates.SaleCheck | calls | act.sell_shares -> drv.sale_legal | class SaleCheck(NamedTuple) |
| shares.sell_shares | certificates.sale_legal | calls | act.sell_shares -> drv.sale_legal | sale_legal(state: GameState, player_id: str, company_id: str, count: int = 1) -> SaleCheck |
| shares.sell_shares | certificates.swap_director | calls | act.sell_shares -> act.swap_director | swap_director(state: GameState, company_id: str, new_director_id: str) -> None |
| shares.sell_shares | scoring.check_game_end_triggers | calls | act.sell_shares -> act.check_game_end_triggers | check_game_end_triggers(state: GameState, context: str \| None = None) -> None |
| shares.sell_shares | turn_order.current_price | calls | act.sell_shares -> drv.current_price | current_price(state: GameState, company_id: str) -> int |
| shares.sell_shares | turn_order.move_token_down | calls | act.sell_shares -> act.move_token_down | move_token_down(state: GameState, company_id: str, steps: int = 1) -> None |
| trains.discard_excess_trains | turn_order.descending_order | calls | act.discard_excess_trains -> drv.descending_order | descending_order(state: GameState, company_ids: Iterable[str]) -> list[str] |
| trains.phase_check | bidding.clear_concession_boxes | calls | act.phase_check -> act.clear_concession_boxes | clear_concession_boxes(state: GameState) -> None |
| trains.phase_check | bidding.clear_concession_boxes | triggers | act.phase_check -> act.clear_concession_boxes | clear_concession_boxes(state: GameState) -> None |
| turn_order.move_token_up | scoring.check_game_end_triggers | calls | act.move_token_up -> act.check_game_end_triggers | check_game_end_triggers(state: GameState, context: str \| None = None) -> None |
| turn_order.raise_sold_out_prices | certificates.fully_sold | calls | act.raise_sold_out_prices -> drv.fully_sold | fully_sold(state: GameState, company_id: str) -> bool |

### Calls made by GIVEN code (graph nodes with implementation=given)

| given symbol | callee api | edge | nodes | callee signature |
|---|---|---|---|---|
| engine/actions.py:_apply_bid | bidding.place_or_move_bid | calls | act.stock_turn_action -> act.move_bid | place_or_move_bid(state: GameState, player_id: str, kind: str, box_index: int, amount: int) -> None |
| engine/actions.py:_apply_bid | bidding.place_or_move_bid | calls | act.stock_turn_action -> act.place_bid | place_or_move_bid(state: GameState, player_id: str, kind: str, box_index: int, amount: int) -> None |
| engine/actions.py:_apply_bid | bidding.place_or_move_bid | triggers | act.stock_turn_action -> act.move_bid | place_or_move_bid(state: GameState, player_id: str, kind: str, box_index: int, amount: int) -> None |
| engine/actions.py:_apply_bid | bidding.place_or_move_bid | triggers | act.stock_turn_action -> act.place_bid | place_or_move_bid(state: GameState, player_id: str, kind: str, box_index: int, amount: int) -> None |
| engine/actions.py:_apply_bid | company_formation.convert_concession | calls | act.stock_turn_action -> act.convert_concession | convert_concession(state: GameState, player_id: str, abbr: str, start_price: int) -> None |
| engine/actions.py:_apply_bid | company_formation.convert_concession | triggers | act.stock_turn_action -> act.convert_concession | convert_concession(state: GameState, player_id: str, abbr: str, start_price: int) -> None |
| engine/actions.py:_apply_bid | round_manager.advance_stock_player | calls | act.stock_turn_action -> act.end_turn | advance_stock_player(state: GameState) -> None |
| engine/actions.py:_apply_bid | round_manager.advance_stock_player | triggers | act.stock_turn_action -> act.end_turn | advance_stock_player(state: GameState) -> None |
| engine/actions.py:_apply_bid | shares.buy_share | calls | act.stock_turn_action -> act.buy_share | buy_share(state: GameState, player_id: str, company_id: str, source: str \| None = None) -> None |
| engine/actions.py:_apply_bid | shares.buy_share | triggers | act.stock_turn_action -> act.buy_share | buy_share(state: GameState, player_id: str, company_id: str, source: str \| None = None) -> None |
| engine/actions.py:_apply_bid | shares.sell_shares | calls | act.stock_turn_action -> act.sell_shares | sell_shares(state: GameState, player_id: str, company_id: str, count: int = 1) -> None |
| engine/actions.py:_apply_bid | shares.sell_shares | triggers | act.stock_turn_action -> act.sell_shares | sell_shares(state: GameState, player_id: str, company_id: str, count: int = 1) -> None |
| engine/actions.py:_apply_operate | round_manager.active_company_id | calls | act.operate_company -> drv.active_company | active_company_id(state: GameState) -> str \| None |
| engine/actions.py:_apply_operate | round_manager.advance_company | calls | act.operate_company -> act.advance_company | advance_company(state: GameState) -> None |
| engine/actions.py:_apply_operate | round_manager.advance_company | triggers | act.operate_company -> act.advance_company | advance_company(state: GameState) -> None |
| engine/actions.py:_apply_operate | trains.buy_train_from_bank | calls | act.operate_company -> act.buy_train | buy_train_from_bank(state: GameState, company_id: str, kind: str, code: str, source: str \| None = None) -> None |
| engine/actions.py:_apply_operate | trains.buy_train_from_bank | triggers | act.operate_company -> act.buy_train | buy_train_from_bank(state: GameState, company_id: str, kind: str, code: str, source: str \| None = None) -> None |
| engine/actions.py:_apply_pass | round_manager.advance_company | calls | act.pass_turn -> act.advance_company | advance_company(state: GameState) -> None |
| engine/actions.py:_apply_pass | round_manager.advance_company | triggers | act.pass_turn -> act.advance_company | advance_company(state: GameState) -> None |
| engine/actions.py:_apply_pass | round_manager.advance_stock_player | calls | act.pass_turn -> act.end_turn | advance_stock_player(state: GameState) -> None |
| engine/actions.py:_apply_pass | round_manager.advance_stock_player | triggers | act.pass_turn -> act.end_turn | advance_stock_player(state: GameState) -> None |
| engine/actions.py:_apply_pass | round_manager.end_stock_round | calls | act.pass_turn -> act.end_stock_round | end_stock_round(state: GameState) -> None |
| engine/actions.py:_apply_pass | round_manager.end_stock_round | triggers | act.pass_turn -> act.end_stock_round | end_stock_round(state: GameState) -> None |
| engine/actions.py:_apply_pass | round_manager.sr_over | calls | act.pass_turn -> drv.sr_over | sr_over(state: GameState) -> bool |
| engine/actions.py:apply_action | scoring.check_game_end_triggers | calls | act.apply_action -> act.check_game_end_triggers | check_game_end_triggers(state: GameState, context: str \| None = None) -> None |

### Callers per module (api-level callers fields: given code + graph)

#### shares
- `ShareError`: actions._apply_buy_share, actions._apply_sell_shares
- `interest_amount`: shares.charge_interest
- `charge_interest`: bidding.resolve_stock_round
- `sell_shares`: actions._apply_sell_shares
- `buy_share`: actions._apply_buy_share

#### certificates
- `SaleCheck`: certificates.can_sell_any, shares.sell_shares
- `cert_units`: certificates.successor, certificates.swap_director, certificates.units_held, company_formation.convert_concession
- `units_held`: certificates.SaleCheck, certificates.sale_legal, certificates.successor, scoring.player_wealth, shares.buy_share
- `certs_held`: certificates.cert_count_holdings
- `cert_limit`: bidding.place_or_move_bid, certificates.over_limit, shares.buy_share
- `cert_count_holdings`: certificates.cert_count
- `cert_count`: bidding.place_or_move_bid, certificates.over_limit, shares.buy_share
- `over_limit`: certificates.must_sell
- `successor`: certificates.SaleCheck, certificates.sale_legal
- `sale_legal`: certificates.can_sell_any, shares.sell_shares
- `can_sell_any`: certificates.must_sell
- `must_sell`: bidding.place_or_move_bid, company_formation.convert_concession, shares.buy_share
- `fully_sold`: turn_order.raise_sold_out_prices
- `swap_director`: shares.buy_share, shares.sell_shares

#### company_formation
- `ConcessionError`: actions._apply_convert_concession
- `convert_concession`: actions._apply_convert_concession
- `minor_start_price`: company_formation.float_minors
- `minor_start_treasury`: company_formation.float_minors
- `minor_float_order`: company_formation.float_minors
- `float_minors`: bidding.resolve_stock_round

#### bidding
- `BidError`: actions._apply_bid
- `face_value`: bidding.min_legal_bid
- `highest_bid`: bidding.committed_money, bidding.item_resolution_order, bidding.min_legal_bid
- `highest_bidder`: bidding.committed_money, bidding.items_led, bidding.place_or_move_bid
- `committed_money`: bidding.bid_amount_error, bidding.bid_amount_valid
- `items_led`: certificates.cert_count
- `tokens_total`: bidding.place_or_move_bid
- `tokens_used`: bidding.place_or_move_bid
- `min_legal_bid`: bidding.bid_amount_error, bidding.bid_amount_valid
- `bid_amount_error`: bidding.place_or_move_bid
- `item_resolution_order`: bidding.resolve_bids
- `place_or_move_bid`: actions._apply_bid
- `shift_boxes`: bidding.refill_boxes
- `refill_boxes`: bidding.resolve_stock_round, round_manager.start_stock_round
- `clear_concession_boxes`: trains.phase_check
- `vacate_box_item`: bidding.remove_box1_minor_and_export, bidding.resolve_bids
- `resolve_bids`: bidding.resolve_stock_round
- `unsold_minor_exports`: bidding.resolve_stock_round
- `remove_box1_minor_and_export`: bidding.resolve_stock_round
- `resolve_stock_round`: actions (imported, unused), round_manager.end_stock_round

#### turn_order
- `token_cell`: scoring.check_game_end_triggers, turn_order.current_price, turn_order.descending_order, turn_order.in_yellow, turn_order.is_game_end_cell, turn_order.move_token_down, turn_order.move_token_up
- `current_price`: scoring.player_wealth, shares.buy_share, shares.sell_shares, turn_order.descending_order
- `in_yellow`: certificates.cert_count_holdings, shares.buy_share
- `is_game_end_cell`: scoring.check_game_end_triggers
- `start_cell`: turn_order.place_start_token
- `place_start_token`: company_formation.convert_concession, company_formation.float_minors
- `move_token_down`: shares.sell_shares
- `move_token_up`: turn_order.raise_sold_out_prices
- `descending_order`: trains.discard_excess_trains, turn_order.operating_order, turn_order.raise_sold_out_prices
- `operating_order`: turn_order.next_operating_company
- `next_operating_company`: round_manager.advance_company, round_manager.begin_operating_round
- `compute_stock_round_order`: turn_order.reorder_players_by_cash
- `reorder_players_by_cash`: bidding.resolve_stock_round
- `raise_sold_out_prices`: bidding.resolve_stock_round

#### trains
- `TrainError`: actions._apply_operate, operating.first_turn_housekeeping
- `phase_of_train`: trains.phase_check
- `front_train`: trains.export_train
- `front_group`: trains.buy_train_from_bank
- `deck_remaining`: trains.buy_train_from_bank, trains.front_group
- `train_group`: trains.buy_train_from_bank
- `train_cost`: trains.buy_train_from_bank
- `train_limit`: trains.buy_train_from_bank, trains.discard_excess_trains
- `phase_check`: trains.buy_train_from_bank, trains.export_train, trains.upgrade_l_train
- `rust_trains`: trains.phase_check
- `discard_excess_trains`: trains.phase_check
- `export_train`: bidding.remove_box1_minor_and_export, bidding.unsold_minor_exports
- `buy_train_from_bank`: actions._apply_operate, operating.first_turn_housekeeping

#### scoring
- `check_game_end_triggers`: actions.apply_action, bidding.resolve_stock_round, company_formation.convert_concession, company_formation.float_minors, operating._move_price, scoring.pay_concession_dividends, scoring.pay_private_revenues, shares.sell_shares, turn_order.move_token_up
- `bank_broken`: scoring.check_game_end_triggers
- `player_wealth`: scoring.final_ranking
- `private_revenue`: scoring.pay_private_revenues
- `pay_concession_dividends`: round_manager.begin_operating_round
- `pay_private_revenues`: round_manager.begin_operating_round

#### round_manager
- `next_player`: round_manager.advance_stock_player
- `begin_turn`: round_manager.advance_stock_player, round_manager.start_stock_round
- `start_stock_round`: main.debug_force_round, round_manager.end_operating_round
- `advance_stock_player`: actions._apply_bid, actions._apply_buy_share, actions._apply_convert_concession, actions._apply_pass, actions._apply_sell_shares
- `end_stock_round`: actions._apply_pass
- `active_company_id`: actions._apply_operate, actions._apply_pass, round_manager.advance_company
- `advance_company`: actions._apply_operate, actions._apply_pass
- `start_operating_round`: round_manager.end_stock_round
- `begin_operating_round`: round_manager.end_operating_round, round_manager.start_operating_round
- `end_operating_round`: round_manager.advance_company, round_manager.begin_operating_round
- `operating_rounds_for_next_set`: round_manager.start_operating_round

