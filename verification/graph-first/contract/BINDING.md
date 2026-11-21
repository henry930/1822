# BINDING: graph nodes -> concrete code

Source of truth for names: the given code in `backend/app` (models.py, data/*, setup.py, stock_positions.py, actions.py,
operating.py, main.py, rooms.py). Graph ids are cited as `st.x`, `const.x`, `ent.x`, `act.x`, `drv.x`, `comp.x`;
rules as `4.4.2`, rulings as `R5`. Tags: `[GIVEN]` = verified in given code, `[BIND]` = binding decision of this
document (representation choice, derived from graph + models), `[GUESS]` = not determined by graph or code
(also listed in GAPS.md, section B).

---------------------------------------------------------------------------------------------------------------------
## PART A. State, entity and constant bindings

### A.0 Identifiers and enums
- Player id: `"p1"`..`"pN"` (`state.players` keys, `state.player_order` entries). [GIVEN setup.py]
- Major company id: abbreviation string (`"LNWR"`, `"GWR"`, `"LBSCR"`, `"SECR"`, `"CR"`, `"MR"`, `"L&YR"`, `"NBR"`, `"SWR"`,
  `"NER"`); key of `state.majors`, of `state.stock_positions`, of `Player.shares`, of `Player.concessions`. [GIVEN]
- Minor company id: `"M<number>"` (e.g. `"M19"`); key of `state.minors` and of `state.stock_positions`. The bare number
  (int) is used in `MinorCompanyState.number`, `state.minor_stack` and `BidBoxItem.ref` of kind `"minor"`. [GIVEN setup.py]
- Private id: int number (`state.privates` key, `Player.private_companies` entries, `state.private_stack`,
  `BidBoxItem.ref` of kind `"private"`).
- Concession id: the major abbreviation (`state.concession_stack` entries, `BidBoxItem.ref` of kind `"concession"`,
  `Player.concessions` entries). A concession is NOT a separate object.
- Item kind strings: `"concession"`, `"minor"`, `"private"` (BidBoxItem.kind, action `bids[].kind`).
- Company "kind" argument used by given callers: `"major"` | `"minor"`.
- `state.round_type` is the Enum `RoundType.STOCK` / `RoundType.OPERATING` (compare with the Enum, not strings).
- `MARKET cell` = tuple `(row, col)`; `state.stock_positions[company_id] = (row, col)`;
  `state.stock_stack[(row, col)]` = list of company ids, index 0 = TOP of the pile. [GIVEN stock_positions.py]

### A.1 State nodes (all 34)

| graph node | concrete field / representation | notes |
|---|---|---|
| `st.player_count` | `len(state.player_order)` (3..7) | no stored field |
| `st.sr_order` | `state.player_order` (list of player ids, index 0 = "Player 1 card") AND `state.priority_deal_player_id` | [BIND] `priority_deal_player_id` must always equal `player_order[0]` (setup.py sets it so); whoever rewrites `player_order` rewrites it |
| `st.player_cash` | `state.players[pid].cash` | int, never negative |
| `st.player_loans` | `state.players[pid].loans` | int pounds. Interest: `loans += (loans+1)//2` |
| `st.bank_cash` | `state.bank.cash` | may go negative ("broken" = `< 0`). Initial = `STARTING_BANK - start_money*n` = 9900 [GIVEN setup.py]. `BankState.cash` default 12000 is never used |
| `st.phase` | `state.phase` (int 1..7) | writers: trains.phase_check only (plus given debug code) |
| `st.sr_count` | `state.stock_rounds_completed` (+1 while a stock round is running) | [BIND] "stock rounds started" = `stock_rounds_completed + 1` during a stock round. The "first stock round" test (10.1.1) is `state.stock_rounds_completed == 0` evaluated inside resolve step 9. `round_manager.end_stock_round` increments `stock_rounds_completed` AFTER `resolve_stock_round` returned. `state.round_number` is not in the graph: untouched [GUESS] |
| `st.sr_status` | NO FIELD | [BIND] `round_type == STOCK` means `in_progress`; `resolving` exists only inside `end_stock_round` (not stored); `finished` = `end_stock_round` returned. See GAPS |
| `st.turn` | `state.active_player_id` (turn.active_player) and `state.bids_this_turn` (turn.bids_made) | `stage`, `c_used`, `acted` have NO field and are not needed: the given actions.py ends the turn after every successful action (see C.5). `bids_this_turn` is INCREMENTED BY actions.py after each `place_or_move_bid` call (never by bidding.py) and RESET to 0 by `round_manager` when a turn begins |
| `st.pass_streak` | `state.consecutive_passes` | written ONLY by actions.py (reset to 0 after bid/buy/sell/convert, `+= 1` on pass); `round_manager.start_stock_round` resets it to 0; `advance_stock_player` must NOT touch it |
| `st.sale_happened` | `state.any_sale_this_stock_round` | actions.py sets it True after `buy_share` and `convert_concession`; NOT after `sell_shares` -> `shares.sell_shares` must set it itself (R15). `bidding.resolve_bids` sets it (R6). Reset by `start_stock_round` |
| `st.sold_this_round` | `state.sold_this_round: dict[player_id, collection of company ids]` | [BIND] store each value as a `list[str]` without duplicates, NOT a `set`: `rooms.serialize_state` (json.dumps with a default that handles only dataclasses and Enums) raises TypeError on a `set`. Readers use `company_id in state.sold_this_round.get(pid, ())`. Reset to `{}` by `start_stock_round` |
| `st.ordinary_certs[p,c]` | DERIVED: `state.players[p].shares.get(c,0) - (cert_units(c) if state.majors[c].director_player_id == p else 0)` | owner certificates.py `ordinary_certs()`. See trap T1 |
| `st.director_holder[c]` | `state.majors[c].director_player_id` (None until started) | |
| `st.treasury_shares[c]` | `state.majors[c].shares_in_treasury` | ordinary certificates = units (8; LNWR 9 at flotation). The director's certificate is never in it (the models comment "director's cert = 2" does not apply: operating.py `_pay_major_dividend` counts these as plain units) |
| `st.pool_shares[c]` | `state.majors[c].shares_in_bank_pool` | ordinary certificates = units, max 5 |
| `st.company_cash[c]` | `state.majors[c].treasury` / `state.minors["M<n>"].treasury` | |
| `st.major_status[c]` | `state.majors[c].floated` (False = unstarted, True = floated) | also set `concession_converted = True` on conversion [BIND] |
| `st.has_completed_or[c]` | `state.majors[c].has_operated` | initial False; set False by convert_concession; set True by `round_manager.advance_company` when a MAJOR company has finished an operating turn [BIND, graph says "operating-round module"; given actions.py never sets it, GAPS A-8] |
| `st.market_stack` | `state.stock_positions` + `state.stock_stack` (both, always consistent) | writers only via turn_order functions or `stock_positions.place_token` |
| `st.player_concessions[p]` | `state.players[p].concessions` (list of major abbr) | [BIND] writers also mirror `MajorCompanyState.concession_holder_player_id` (= holder, None after conversion/clearing) [GUESS, not in graph] |
| `st.player_privates[p]` | `state.players[p].private_companies` (list[int]) | [BIND] writer (vacate award) also sets `PrivateCompanyState.owner_player_id` [GUESS mirror] |
| `st.minor_director[m]` | `state.minors["M<m>"].director_player_id` | non-null after award; `floated=True` is set by `company_formation.float_minors` |
| `st.concession_stack` | `state.concession_stack` (list[str], index 0 = top) | |
| `st.minor_stack` | `state.minor_stack` (list[int], index 0 = top) | |
| `st.private_stack` | `state.private_stack` (list[int], index 0 = top) | |
| `st.box_contents` | `state.concession_bid_boxes` (len 3), `state.minor_bid_boxes` (len 4), `state.private_bid_boxes` (len 3): each element `BidBoxItem` or `None` | graph box number = list index + 1 (0-based index in code, trap T3). Lists always keep their fixed length (padding `None`) |
| `st.removed_items` | minors: `MinorCompanyState.removed = True`; concessions: NO FIELD (just absent from stack, boxes and players) | audit only, no reader in given code; GAPS A-15 |
| `st.bids` | `BidBoxItem.bids: dict[player_id, int]` of the item sitting in a box | item identity = `(kind, box_index)` while the item sits in a box. Empty dict = no bid. Trap T11 (a bid of 0 is a bid) |
| `st.items_with_bids` | LOCAL value | [BIND] returned by `bidding.resolve_bids` as `set[(kind, box_index)]` and passed to `unsold_minor_exports`; not stored in state |
| `st.pending_minor_floats` | LOCAL value | [BIND] returned by `bidding.resolve_bids` as `list[tuple[int, int, int, str]]` = `(minor_number, bid, box_index, buyer_player_id)` and passed to `company_formation.float_minors(state, pending)`; not stored |
| `st.train_deck` | `state.bank.train_pool: dict[code, count]` | [BIND] front-first scan order `"L","2","3","4","5","6","7","E"`; the front train type is the first code with count > 0; L and 2 are one physical pool (setup: `L=22,2=0`), 7 and E too (`7=16,E=0`). See trap T12 |
| `st.phase_events` | one line appended to `state.log` | [BIND] format `PHASE_EVENT from=<old> to=<new> rusted=<code or -> or_per_sr=<n>`; there is no consumer in given code (GAPS A-26) |
| `st.game_end` | `state.game_over: bool` + `state.end_trigger_pending: str\|None` | [BIND] graph `none` = (`game_over False`, `end_trigger_pending None`); `immediate` = `game_over True`; `after_next_or` = `end_trigger_pending == "next_or"`; `end_of_current_or` = `"or_end"` (token on game-end cell during an OR) or `"or_set_end"` (bank broken during an OR) per models.py comment. "A trigger exists" = `game_over or end_trigger_pending is not None` |

### A.2 Entity nodes (all 21)

| entity | concrete |
|---|---|
| `ent.player` | `Player` (`state.players[pid]`) |
| `ent.private_company` | `PrivateCompanyState` + `Player.private_companies` |
| `ent.concession` | abbr in `Player.concessions` / `BidBoxItem(kind="concession")`; face value 100 |
| `ent.minor_company` | `MinorCompanyState`, id `"M<n>"` |
| `ent.major_company`, `ent.lnwr` | `MajorCompanyState`, id abbr; LNWR = `"LNWR"` (`LNWR_ABBR` in app.data.major_companies) |
| `ent.director_certificate` | `MajorCompanyState.director_player_id` + (`cert_units` units inside `Player.shares[c]`); ONE certificate for limit counting |
| `ent.share_certificate` | one unit inside `Player.shares[c]` (ordinary) |
| `ent.bid_box` | element of `state.*_bid_boxes` |
| `ent.bidding_token` | one entry in `BidBoxItem.bids` |
| `ent.stock_market`, `ent.market_cell`, `ent.stock_token` | `app.data.stock_market` (`STOCK_MARKET_BY_POSITION`, `StockCell`), `state.stock_positions` / `state.stock_stack` |
| `ent.train` | one count unit in `state.bank.train_pool[code]` |
| `ent.bank`, `ent.bank_pool`, `ent.company_treasury`, `ent.loan` | `state.bank`, `MajorCompanyState.shares_in_bank_pool`, (`treasury`, `shares_in_treasury`), `Player.loans` |
| `ent.item_stack` | `state.concession_stack` / `minor_stack` / `private_stack` |
| `ent.player_order_card` | position in `state.player_order` |
| `ent.game` | `GameState` |

### A.3 Constants (all 18)

| constant | where it lives | value / how to read |
|---|---|---|
| `const.start_money` | `app.data.setup.SETUP_BY_PLAYER_COUNT[n].start_money` | 3:700 4:525 5:420 6:350 7:300 (setup.py already deals it) |
| `const.bank_total` | `app.data.setup.STARTING_BANK` = 12000 | initial `bank.cash` = 12000 - n*start = 9900 [GIVEN setup.py] |
| `const.cert_limit` (MISSING in rulebook) | `SETUP_BY_PLAYER_COUNT[n].certificate_limit` | 3:26 4:20 5:16 6:13 7:11 |
| `const.bidding_tokens` (MISSING) | `SETUP_BY_PLAYER_COUNT[n].bidding_tokens` | 3:6 4:5 5:4 6:3 7:3 |
| `const.start_values` | `app.data.setup.COMPANY_START_PRICES` = `[50,60,70,80,90,100]`, `MINOR_ONLY_START_PRICE` = 50; major values = 60..100 (`app.data.stock_market.MAJOR_MINOR_START_VALUES`) | |
| `const.face_values` | NOT in any data table. Owner: bidding.py module constant `FACE_VALUES = {"concession":100,"minor":100,"private":0}` | R1, 3.4.2, 3.1.3 |
| `const.box_counts` | `app.engine.setup.NUM_MINOR_BID_BOXES=4`, `NUM_CONCESSION_BID_BOXES=3`, `NUM_PRIVATE_BID_BOXES=3` (importable) | box number = index + 1 |
| `const.bid_rules` | NOT in data. bidding.py constants `BID_MULTIPLE = 5`, `MAX_BIDS_PER_TURN = 3` | |
| `const.share_structure` | NOT in data. certificates.py constants `TOTAL_UNITS=10`, `POOL_CAP_UNITS=5`, `HOLD_CAP_UNITS=6`; `cert_units(c)` = 1 if `c == LNWR_ABBR` else 2; ordinary certs at flotation 9 (LNWR) / 8 | |
| `const.market_grid` (MISSING in rulebook) | `app.data.stock_market.STOCK_MARKET_BY_POSITION[(row,col)] -> StockCell(row,col,value,zone,game_end)`; rows are left-aligned lists (`_ROWS`), row 0 top. Cell exists iff `(row,col)` is a key | down = `(row+1,col)`, up = `(row-1,col)`, absent = no move (R12) |
| `const.yellow_cells` (MISSING) | `StockCell.zone == "yellow"` | 39 cells, lower-left staircase |
| `const.game_end_cells` (MISSING) | `StockCell.game_end is True` | only `(0,3)` value 700 |
| `const.start_cells` (MISSING) | cells with `zone in {"start","minor_start"}` | verified: 100 -> (4,4), 90 -> (5,4), 80 -> (6,4), 70 -> (7,4), 60 -> (8,4), 50 -> (9,4) (50 is `minor_start`, minors only) |
| `const.train_deck` (counts MISSING) | `app.data.trains.TRAIN_TYPES` (code, cost, count) and `setup.new_game` | pool after setup: `L 22, 2 0, 3 9, 4 6, 5 3, 6 3, 7 16, E 0`. Order = L/2, 3, 4, 5, 6, 7/E |
| `const.phase_table` | trains.py module constant `TRAIN_PHASE = {"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"E":7}` (L absent); table derived from RULES 2.2.3-2.2.8 | |
| `const.rust_table` | `app.data.phases.PHASES_BY_NUMBER[n].trains_rusted` | 3:"L", 4:"2", 6:"3", 7:"4", others None |
| `const.interest` | shares.py: `ceil(L/2) = (L+1)//2` | |
| `const.stack_setup` | `engine/setup.py` (given) | LNWR / M24 / P1 on top; stacks top-first |

### A.4 Representation traps (read all)

- **T1 Units vs certificates.** `Player.shares[c]` stores UNITS of 10% INCLUDING the director's certificate (2 units; LNWR 1).
  `ordinary_certs(p,c) = shares.get(c,0) - (cert_units(c) if director(c)==p else 0)`; `units_held(p,c) = shares.get(c,0)`;
  `certs_held(p,c) = ordinary_certs(p,c) + (1 if director(c)==p else 0)` (director counts ONE certificate).
  A concession, a private and a minor each count 1 certificate. A director swap (`swap_director`) changes only
  `director_player_id`: every holder's units are unchanged (new director loses `cu` ordinary units and gains `cu` director
  units; old director the reverse), so `Player.shares` is NOT modified by a swap.
- **T2** `Player.shares` has NO entries for minors (minor ownership is `MinorCompanyState.director_player_id`). Zero-valued
  entries may exist; always read with `.get(c, 0)`.
- **T3 Box indexes are 0-based** in code (`box_index` in the bid action, list index). Graph/ruling "box number" = index+1;
  "lower box number wins a tie" = lower index. "Box 1" = index 0.
- **T4 BidBoxItem.ref types:** concession -> `str` abbr; minor -> `int` number (state.minors key is `f"M{ref}"`);
  private -> `int`. (The `ref: int` annotation in models.py is wrong for concessions.)
- **T5** `bids_this_turn` is incremented by actions.py, so bidding must only READ it.
- **T6** `consecutive_passes` is owned by actions.py (see table).
- **T7 Market piles:** `stock_stack[cell]` index 0 = top. `place_token` removes the company from its old pile and APPENDS to the
  new one (= bottom, rule 4.4.5/4.12.2/4.7.2). Never call `place_token` when the token does not change cell (4.4.5: it keeps its
  place). Emptied piles remain as empty lists; readers must not assume the key is absent.
- **T8 Price drop/rise** move along the COLUMN: down = row+1, up = row-1, same col. `operating.py` moves left/right for
  dividends; that is given code and independent.
- **T9** `descending_price_key(state, company_id)` (given, stock_positions.py) is the 1.6.2 order key: sort ascending by it.
- **T10** The bank pays/receives as `state.bank.cash`; loans never touch it (4.3.5).
- **T11** `highest_bid` of an item: `max(item.bids.values())` if `item.bids` (dict non-empty) else `None`. A bid of 0 on a private
  is legal and is a bid: never test `if highest_bid:`.
- **T12 Trains:** `bank.train_pool` counts. L/2 trains remaining = `pool["L"] + pool["2"]`; pop = decrement `"L"` first, then `"2"`.
  7/E remaining = `pool["7"] + pool["E"]` (pop `"7"` first). Front type code = first code in order `L,2,3,4,5,6,7,E` with count > 0.
  [GUESS: how a double-sided card is counted once it has been flipped; graph says only "front train of the deck"].
- **T13 JSON-safety.** `rooms.serialize_state` does `dataclasses.asdict` + `json.dumps` with a default for dataclasses and Enums only.
  After every function the state must contain only: int/str/bool/None, lists, dicts with str keys (the tuple-keyed `stock_stack`
  is handled by rooms), tuples, dataclasses, Enums. NO sets, NO new attributes on dataclasses, NO dict keys of other types.
- **T14** `Player.shares`/`concessions` etc. are per player in `state.players`; iterate `state.players.values()` or `state.player_order`.
- **T15 Floating a minor:** `MinorCompanyState` gets `floated=True`, `treasury`, `director_player_id`, `share_price` (display mirror,
  [GUESS], nothing reads it); majors: `floated=True`, `concession_converted=True`, `treasury`, `shares_in_treasury`,
  `shares_in_bank_pool=0`, `has_operated=False`, `director_player_id`. `share_price` of majors/minors is NOT maintained
  by given operating code; the price of a company is always read from the grid via `turn_order.current_price`.
- **T16 Removed minor:** `removed=True`, `director_player_id` stays None, `floated` False.

### A.5 What does not exist and how to represent it (summary)

| missing in models | representation |
|---|---|
| turn.stage / c_used / acted | not stored; actions.py makes every action turn-ending (see C.5) |
| sr_status | see A.1 |
| items_with_bids, pending_minor_floats | local return values (A.1) |
| removed concessions | absent everywhere (A.1) |
| phase_events | log lines (A.1) |
| "has completed OR" writer | `round_manager.advance_company` (A.1) |
| end-of-game final scores | out of scope; only `scoring.player_wealth` |

### A.6 setup.py (GIVEN, `act.setup_game`) versus the graph effects

setup.py is not rewritten. Differences a contract writer must know (full list in GAPS section B):
1. Graph: boxes empty after setup, filled by the first `start_stock_round`. Given: `new_game` already fills the boxes (3/4/3) and
   returns a state that is ALREADY in the first stock round (`round_type STOCK`, `active_player_id = priority_deal_player_id = player_order[0]`,
   `stock_rounds_completed 0`, `round_number 1`). `start_stock_round` is therefore NOT called for round 1; it is only called after an
   operating round (and by main.py's debug endpoint).
2. `sold_this_round`, `any_sale_this_stock_round`, `consecutive_passes`, `bids_this_turn` start at their model defaults ({} / False / 0 / 0).
3. Other graph setup effects (cash, bank 9900, stacks with tops, deck, random order, empty market, majors unstarted) match.

---------------------------------------------------------------------------------------------------------------------
## PART B. Component -> file mapping and node ownership

Graph has 8 components; code has 8 files. Mapping (a graph component that spans files is split EXPLICITLY below):

| graph component | file(s) |
|---|---|
| `comp.market` | `turn_order.py` (whole component) |
| `comp.certificates` | `certificates.py` (whole component) |
| `comp.share_trading` | `shares.py` (sell_shares, buy_share, repay_loans, + loan interest items from sr_resolution) and `company_formation.py` (convert_concession) |
| `comp.bidding` | `bidding.py` (whole component) |
| `comp.bid_boxes` | `bidding.py` (whole component) |
| `comp.phase_trains` | `trains.py` (whole component) |
| `comp.sr_flow` | `round_manager.py` (start_stock_round, begin_turn, end_turn, pass_turn, sr_over, next_player) and `scoring.py` (check_game_end_triggers, pay_concession_dividends, bank_broken, player_wealth); `setup_game` = GIVEN setup.py |
| `comp.sr_resolution` | split: `bidding.py` (resolve_stock_round, resolve_bids, unsold_minor_exports, remove_box1_minor_and_export, item_resolution_order), `company_formation.py` (float_minors, minor_start_price, minor_start_treasury, minor_float_order), `shares.py` (charge_interest, interest_amount), `turn_order.py` (raise_sold_out_prices, reorder_players_by_cash, compute_stock_round_order) |

### B.1 Every action node -> exactly one file (31)

| action | file | public function |
|---|---|---|
| `act.setup_game` | GIVEN `setup.py` | `new_game` |
| `act.start_stock_round` | round_manager | `start_stock_round` |
| `act.begin_turn` | round_manager | `begin_turn` |
| `act.end_turn` | round_manager | `advance_stock_player` |
| `act.pass_turn` | round_manager | `end_stock_round` (the round-ending branch; the rest is in given actions.py) |
| `act.check_game_end_triggers` | scoring | `check_game_end_triggers` |
| `act.pay_concession_dividends` | scoring | `pay_concession_dividends` |
| `act.sell_shares` | shares | `sell_shares` |
| `act.repay_loans` | shares | `repay_loans` |
| `act.buy_share` | shares | `buy_share` |
| `act.convert_concession` | company_formation | `convert_concession` |
| `act.swap_director` | certificates | `swap_director` |
| `act.place_start_token` | turn_order | `place_start_token` |
| `act.move_token_down` | turn_order | `move_token_down` |
| `act.move_token_up` | turn_order | `move_token_up` |
| `act.place_bid`, `act.move_bid` | bidding | `place_or_move_bid` (one function; branch = player already has a token on the item) |
| `act.shift_boxes` | bidding | `shift_boxes` |
| `act.refill_boxes` | bidding | `refill_boxes` |
| `act.clear_concession_boxes` | bidding | `clear_concession_boxes` |
| `act.vacate_box_item` | bidding | `vacate_box_item` |
| `act.phase_check` | trains | `phase_check` |
| `act.export_train` | trains | `export_train` |
| `act.resolve_stock_round` | bidding | `resolve_stock_round` |
| `act.resolve_bids` | bidding | `resolve_bids` |
| `act.float_minors` | company_formation | `float_minors` |
| `act.unsold_minor_exports` | bidding | `unsold_minor_exports` |
| `act.remove_box1_minor_and_export` | bidding | `remove_box1_minor_and_export` |
| `act.charge_interest` | shares | `charge_interest` |
| `act.raise_sold_out_prices` | turn_order | `raise_sold_out_prices` |
| `act.reorder_players_by_cash` | turn_order | `reorder_players_by_cash` |

### B.2 Every derived node -> exactly one file (41)

| file | derived nodes |
|---|---|
| round_manager | `drv.sr_over` -> `sr_over`, `drv.next_player` -> `next_player` |
| scoring | `drv.bank_broken` -> `bank_broken`, `drv.player_wealth` -> `player_wealth` |
| certificates | `drv.cert_units`, `drv.units_held`, `drv.certs_held`, `drv.cert_limit`, `drv.cert_count_holdings`, `drv.cert_count`, `drv.over_limit`, `drv.successor`, `drv.sale_legal`, `drv.can_sell_any`, `drv.must_sell`, `drv.fully_sold` (same names) |
| turn_order | `drv.token_cell`, `drv.current_price`, `drv.in_yellow`, `drv.start_cell`, `drv.descending_order`, `drv.operating_order`, `drv.next_operating_company`, `drv.is_game_end_cell`, `drv.compute_stock_round_order` |
| bidding | `drv.face_value`, `drv.highest_bid`, `drv.highest_bidder`, `drv.committed_money`, `drv.items_led`, `drv.tokens_total`, `drv.tokens_used`, `drv.min_legal_bid`, `drv.bid_amount_valid`, `drv.item_resolution_order` |
| trains | `drv.phase_of_train`, `drv.front_train` |
| company_formation | `drv.minor_start_price`, `drv.minor_start_treasury`, `drv.minor_float_order` |
| shares | `drv.interest_amount` |

Counts: 31 actions (30 in new files + setup given), 41 derived. Each assigned once.

### B.3 Shared helper owners
- ordinary_certs / units_held / certs_held / cert_units / director lookup: certificates.py. Everybody else imports them.
- Market reads (price, token cell, yellow, game-end): turn_order.py. Everybody else imports them; nobody reads `STOCK_MARKET_BY_POSITION` for those except turn_order.
- Money movement helpers: none shared; every function updates `Player.cash`, `state.bank.cash`, `treasury` itself as its contract says.
- `FACE_VALUES`, `BID_MULTIPLE`, `MAX_BIDS_PER_TURN`: bidding.py.
- Pending-minor tuple format: defined here (A.1) and produced by bidding, consumed by company_formation.
- Exceptions: `ShareError` (shares), `ConcessionError` (company_formation), `BidError` (bidding), `TrainError` (trains),
  `CertificateError` (certificates), `MarketError` (turn_order), `RoundError` (round_manager).

---------------------------------------------------------------------------------------------------------------------
## PART C. External API per file

Notation: `state` = `GameState`; `pid` = player id; `cid` = company id (major abbr or `"M<n>"`).

### C.1 Names the GIVEN code imports or calls (must exist with this exact signature)

| module | name / signature | called by, how |
|---|---|---|
| shares | `class ShareError(Exception)` | actions.py `except ShareError` |
| shares | `buy_share(state, player_id, company_id, source)` `source` is `None`, `"treasury"` or `"pool"` | actions._apply_buy_share: `buy_share(state, player_id, action["company_id"], action.get("source"))`; afterwards actions sets `consecutive_passes=0`, `any_sale_this_stock_round=True`, calls `advance_stock_player(state)` |
| shares | `sell_shares(state, player_id, company_id, count)` | actions._apply_sell_shares; afterwards actions sets `consecutive_passes=0` only and calls `advance_stock_player` (so sell_shares must set `any_sale_this_stock_round`) |
| company_formation | `class ConcessionError(Exception)` | actions |
| company_formation | `convert_concession(state, player_id, abbr, start_price)` | actions._apply_convert_concession (then sets `any_sale_this_stock_round=True`, `advance_stock_player`) |
| bidding | `class BidError(Exception)` | actions |
| bidding | `place_or_move_bid(state, player_id, kind, box_index, amount)` | actions._apply_bid, once per entry of `action["bids"]`; actions itself checks `len(bids) <= 3`, `bids_this_turn + len(bids) <= 3`, increments `state.bids_this_turn` after each call, then resets `consecutive_passes`, then `advance_stock_player` |
| bidding | `resolve_stock_round(state)` | imported by actions.py (unused there); called by `round_manager.end_stock_round` |
| trains | `class TrainError(Exception)` | actions._apply_operate, operating.first_turn_housekeeping |
| trains | `buy_train_from_bank(state, company_id, kind, code)` | actions._apply_operate (`action["buy_train"]` is the code string, e.g. `"2"`), operating.first_turn_housekeeping (`"L"`, TrainError swallowed) |
| scoring | `check_game_end_triggers(state)` | actions.apply_action after EVERY action; operating._move_price after each price move. Must accept the one-argument call |
| round_manager | `active_company_id(state) -> str \| None` | actions._apply_operate / _apply_pass: id of the company whose operating turn it is (`None` if none) |
| round_manager | `advance_company(state)` | actions after an operate action or an operating-round pass |
| round_manager | `advance_stock_player(state)` | actions after every stock-round action that does not end the round |
| round_manager | `end_stock_round(state)` | actions._apply_pass when `consecutive_passes >= len(state.player_order)` |
| round_manager | `start_stock_round(state)` | main.py debug endpoint `force_round` |
| turn_order | (nothing is imported by given code) | |
| certificates | (nothing is imported by given code) | |

### C.2 New cross-file API (derived from graph cross_component edges; all are public names)

**turn_order.py** (layer 1; no new-module imports at top; LAZY `scoring.check_game_end_triggers` inside `move_token_up`, LAZY `certificates.fully_sold` inside `raise_sold_out_prices`)
- `class MarketError(Exception)`
- `token_cell(state, cid) -> tuple[int,int] | None`
- `current_price(state, cid) -> int` (raises `MarketError("ERR_NO_TOKEN: ...")` if no token)
- `in_yellow(state, cid) -> bool` (False if no token)
- `is_game_end_cell(state, cid) -> bool` (False if no token)
- `start_cell(price: int, kind: str = "major") -> tuple[int,int]` (raises MarketError ERR_BAD_START_PRICE)
- `place_start_token(state, cid, price, kind)` (kind `"major"|"minor"`)
- `move_token_down(state, cid, steps)`
- `move_token_up(state, cid)`
- `descending_order(state, company_ids) -> list[str]`
- `operating_order(state) -> list[str]`
- `next_operating_company(state, done) -> str | None`
- `compute_stock_round_order(cash: dict[str,int], previous_order: list[str]) -> list[str]`
- `reorder_players_by_cash(state)`
- `raise_sold_out_prices(state)`

**certificates.py** (layer 2; imports turn_order at top; LAZY `bidding.items_led` inside `cert_count`)
- `class CertificateError(Exception)`
- `class SaleCheck(NamedTuple)`: `legal: bool`, `swap_needed: bool`, `successor: str | None`
- `cert_units(cid) -> int`, `ordinary_certs(state, pid, cid) -> int`, `units_held(state, pid, cid) -> int`,
  `certs_held(state, pid, cid) -> int`, `cert_limit(state) -> int`, `cert_count_holdings(state, pid) -> int`,
  `cert_count(state, pid) -> int`, `over_limit(state, pid) -> bool`,
  `successor(state, cid, director_pid, remaining_units) -> str | None`,
  `sale_legal(state, pid, cid, count) -> SaleCheck`, `can_sell_any(state, pid) -> bool`, `must_sell(state, pid) -> bool`,
  `fully_sold(state, cid) -> bool`, `swap_director(state, cid, new_director_pid)`

**scoring.py** (layer 3; imports turn_order at top)
- `check_game_end_triggers(state, context: str | None = None)`; `bank_broken(state) -> bool`;
  `player_wealth(state, pid) -> int`; `pay_concession_dividends(state)`

**trains.py** (layer 4; LAZY `bidding.clear_concession_boxes` inside `phase_check`)
- `class TrainError(Exception)`, `phase_of_train(code) -> int | None`, `front_train(state) -> str | None`,
  `phase_check(state, code)`, `export_train(state, mode)` (mode `"L_only"` | `"next_with_phase"`),
  `buy_train_from_bank(state, company_id, kind, code)`

**shares.py** (layer 5)
- `class ShareError(Exception)`, `sell_shares`, `buy_share`, `repay_loans(state, pid, amount)`, `interest_amount(loans) -> int`,
  `charge_interest(state)`

**company_formation.py** (layer 5)
- `class ConcessionError(Exception)`, `convert_concession`,
  `minor_start_price(phase, bid) -> int`, `minor_start_treasury(phase, bid, price) -> int`,
  `minor_float_order(pending) -> list`, `float_minors(state, pending)`

**bidding.py** (layer 6; imports certificates, turn_order, scoring, trains, shares, company_formation at top; LAZY `round_manager.sr_over` inside `resolve_stock_round`)
- `class BidError(Exception)`, `FACE_VALUES`, `BID_MULTIPLE`, `MAX_BIDS_PER_TURN`
- `face_value(kind) -> int`, `highest_bid(item) -> int | None`, `highest_bidder(item) -> str | None`,
  `committed_money(state, pid) -> int`, `items_led(state, pid) -> int`, `tokens_total(state) -> int`,
  `tokens_used(state, pid) -> int`, `min_legal_bid(item) -> int`, `bid_amount_valid(state, pid, item, amount) -> bool`,
  `place_or_move_bid(...)`, `shift_boxes(state)`, `refill_boxes(state)`, `clear_concession_boxes(state)`,
  `vacate_box_item(state, kind, box_index, disposition, player_id=None)`, `item_resolution_order(state) -> list[tuple[str,int]]`,
  `resolve_bids(state) -> tuple[set, list]`, `unsold_minor_exports(state, items_with_bids)`,
  `remove_box1_minor_and_export(state)`, `resolve_stock_round(state)`

**round_manager.py** (layer 7; imports everything)
- `class RoundError(Exception)`, `sr_over(state) -> bool`, `next_player(state, pid) -> str`, `begin_turn(state, pid)`,
  `start_stock_round(state)`, `advance_stock_player(state)`, `end_stock_round(state)`, `active_company_id(state)`,
  `advance_company(state)`, `start_operating_round(state)` (helper required by end_stock_round; see round_manager.md)

### C.3 Cross-file call matrix (caller -> callee), with graph edge ids

| caller | callee | graph edge |
|---|---|---|
| round_manager.start_stock_round | bidding.refill_boxes, round_manager.begin_turn | start_stock_round->refill_boxes |
| round_manager.advance_stock_player | round_manager.next_player, begin_turn | end_turn->next_player/begin_turn |
| round_manager.end_stock_round | bidding.resolve_stock_round | pass_turn->resolve_stock_round (triggers) |
| shares.sell_shares | certificates.sale_legal, turn_order.current_price, certificates.swap_director, turn_order.move_token_down, scoring.check_game_end_triggers | sell_shares->* |
| shares.buy_share | turn_order.current_price, certificates.units_held, cert_count, cert_limit, must_sell, swap_director, turn_order.in_yellow | buy_share->* |
| company_formation.convert_concession | turn_order.place_start_token, scoring.check_game_end_triggers, certificates.must_sell, certificates.cert_units | convert_concession->* |
| certificates.swap_director | certificates.cert_units | |
| certificates.cert_count_holdings | turn_order.in_yellow | |
| certificates.cert_count | bidding.items_led (LAZY) | cert_count->items_led |
| certificates.cert_limit | (reads player count) | |
| turn_order.place_start_token | turn_order.start_cell | |
| turn_order.move_token_up | scoring.check_game_end_triggers (LAZY) | move_token_up->check_game_end_triggers |
| turn_order.raise_sold_out_prices | certificates.fully_sold, turn_order.descending_order, move_token_up | |
| scoring.check_game_end_triggers | turn_order.token_cell / is_game_end_cell, scoring.bank_broken | |
| scoring.player_wealth | certificates.units_held, turn_order.current_price | |
| bidding.place_or_move_bid | certificates.must_sell, cert_count, cert_limit | place_bid/move_bid->* |
| bidding.resolve_stock_round | resolve_bids, company_formation.float_minors, unsold_minor_exports, remove_box1_minor_and_export, refill_boxes, shares.charge_interest, turn_order.raise_sold_out_prices, turn_order.reorder_players_by_cash, scoring.check_game_end_triggers | resolve_stock_round->* + order edges |
| bidding.resolve_bids | bidding.vacate_box_item | |
| bidding.unsold_minor_exports / remove_box1_minor_and_export | trains.export_train, bidding.vacate_box_item | |
| company_formation.float_minors | turn_order.place_start_token, scoring.check_game_end_triggers | float_minors->* |
| trains.export_train | trains.front_train, trains.phase_check | |
| trains.phase_check | trains.phase_of_train, bidding.clear_concession_boxes (LAZY) | phase_check->clear_concession_boxes |
| round_manager.* (operating) | turn_order.operating_order / next_operating_company, scoring.pay_concession_dividends | |

### C.4 Mandatory order inside `bidding.resolve_stock_round` (graph `order` edges seq 1..8, then step 9)
1 `resolve_bids` -> 2 `float_minors` -> 3 `unsold_minor_exports` -> 4 `remove_box1_minor_and_export` -> 5 `refill_boxes` ->
6 `charge_interest` -> 7 `raise_sold_out_prices` -> 8 `reorder_players_by_cash` -> 9 `check_game_end_triggers("end_of_stock_round")`.

### C.5 Turn model decided by the GIVEN actions.py (binding on all coders)
Every successful `bid`, `buy_share`, `sell_shares`, `convert_concession` ends the player's turn (`advance_stock_player`). There is no
`repay_loans` action and no `end_turn` action in actions.py. So: within one `apply_action` only one of the graph's steps A/B/C happens;
`turn.stage`, `turn.c_used`, `turn.acted` are not checked or stored. The graph's turn-state-machine preconditions that mention them
are therefore vacuous (they hold trivially) and must not be implemented as extra state. `repay_loans` is implemented and exported but
no given code calls it (GAPS A-1).
