# GAPS: what the graph did not give a contract writer, and what BINDING had to guess

Scope: contracts for the 8 deleted modules (shares, certificates, company_formation, bidding, turn_order, trains, scoring, round_manager).
Inputs: graph.json (+ GRAPH_NOTES, check_graph), RULES.md, RULINGS.md, and the GIVEN code (models.py, data tables, setup.py, stock_positions.py, actions.py, operating.py, main.py, rooms.py).
Severity: S1 = blocks a working integration / contract author had to invent behaviour; S2 = representation or signature mismatch resolved by a binding decision; S3 = minor/precedence/ambiguity.
Per-module "Graph gaps" lists in each `<module>.md` give the module-local detail; this file is the consolidated, numbered list (section A) and the list of binding guesses (section B).

---------------------------------------------------------------------------------------------------------------------
## A. Graph gaps and ambiguities (numbered)

### A.1 Conflicts between the graph and the given code (the graph was built from the rulebook only)
1. **[S1] Turn state machine vs actions.py.** Graph: sell (A) -> repay (B) -> one C action (buy/convert/bid) in one turn, tracked by `turn.stage`, `turn.c_used`, `turn.acted`; `end_turn` and `repay_loans` are actions. Given actions.py: every `sell_shares`, `buy_share`, `convert_concession`, `bid` ends the turn; no `repay` action, no `end_turn` action. The graph therefore has preconditions (`ERR_WRONG_STAGE`, `ERR_C_ALREADY_USED`, `ERR_NO_ACTION_TAKEN`) that are vacuous, and `repay_loans` has no caller. (The skeleton's own docstring says the combination is "not wired up yet".)
2. **[S1] `pass_turn`/`end_turn` preconditions (`not must_sell`, `ERR_MUST_SELL`) cannot be enforced**: actions.py increments the pass counter before any new module is called, and nothing calls `end_turn`. R10 ("must sell at first opportunity") is only enforceable for buy/bid/convert; a player over the limit can pass.
3. **[S2] `check_game_end_triggers(context)`**: graph signature has a 3-valued `context`; every given caller calls it with `(state)` only (after every action, and in operating.py). Also effects exist only for SR context; the operating-round meaning (`end_of_current_or`) is not written by any effect (graph enum has 4 values, only 3 reachable). Resolution used: optional second parameter; OR mapping from models.py comments (INTERIM).
4. **[S1] `setup_game` vs given `new_game`**: graph says boxes are empty after setup and the first `start_stock_round` fills them and sets `sr_count = 1`, `sr_status = in_progress`. Given `new_game` fills boxes itself and returns a state already inside round 1 (active player set). So `start_stock_round` is for rounds >= 2 (and debug), and `sr_count`/`sr_status` have no stored equivalent.
5. **[S2] `st.sr_status` has no field** (`not_started/in_progress/resolving/finished`); `ERR_SR_ALREADY_RUNNING` is unevaluable and conflicts with main.py's debug call `start_stock_round(state)` at any time.
6. **[S1] `bids_this_turn` increment**: graph says `place_bid`/`move_bid` do `turn.bids_made += 1`; the given actions.py increments `state.bids_this_turn` itself after each call and also pre-checks `<= 3`. A coder following the graph literally double counts. Graph does not know the caller does it.
7. **[S2] `sale_happened` writers**: graph says sell_shares, buy_share, convert_concession all write it; given actions.py writes it only for buy and convert. `sell_shares` must write it itself (R15). The graph gives no way to know which writes are redundant.
8. **[S2] Operating-round machinery referenced by given code is absent from the graph**: `active_company_id`, `advance_company`, `end_stock_round`'s successor round, `operating_order` / `current_company_index` bookkeeping, `operating_rounds_this_set`, OR end and game-end maturity (`game_over` for `"or_end"`, `"or_set_end"`, `"next_or"`). Graph states `phase_events` and `has_completed_or` are tagged `external`, but nothing in the skeleton consumes `phase_events` or sets `has_operated`. Without a writer of `has_operated` no share can ever be sold (sell precondition). Binding decision: `round_manager.advance_company` writes it (INTERIM).
9. **[S1] `buy_train_from_bank(state, company_id, kind, code)` + `TrainError`** are required by given code (actions.py, operating.py) but there is no graph node for buying trains (only exports). Contract is INTERIM (data-table checks, bank receives cost, then `phase_check`). Unspecified: buying order, L->2 upgrade, 2-train availability (`train_pool["2"]` starts at 0 so phase 2 can only come from an export), "must own a train", forced purchase, company train rust.
10. **[S2] Minor representation conflict**: graph says a minor's director certificate lives only in `minor_director` (counts 1 certificate); models.py comment on `Player.shares` says it is "tracked as 1 unit of MinorState.owner". Binding follows the graph (`MinorCompanyState.director_player_id`, no `Player.shares` entry).
11. **[S2] `State.sold_this_round` is typed `set<(player, company)>` in the graph and `dict[str, set[str]]` in models**, but `rooms.serialize_state` cannot JSON-encode sets. The graph carries no JSON/serialization requirement; binding stores lists.
12. **[S2] Box numbering**: the graph uses box numbers from 1 ("box 1", "lower box number"); code uses 0-based list indices and the action field is `box_index`. `BidBoxItem.ref` type differs by kind (concession abbr str, minor number int) while the model annotation says int. Graph never defines how an `item` is identified in function signatures (contract uses `(kind, box_index)` or the `BidBoxItem`).
13. **[S2] `ordinary_certs` excludes the director in the graph; `Player.shares` includes it** (units). The graph never says what Player.shares holds, so the "units vs certificates" translation (and that `swap_director` leaves `Player.shares` unchanged) had to be derived in BINDING (T1). Graph effect text of `swap_director` ("ordinary_certs[q] -= cert_units; ordinary_certs[old] += cert_units") is correct only for the graph's own representation.
14. **[S2] `items_with_bids` and `pending_minor_floats` are graph *states* but live only inside one procedure**; `float_minors(none)` and `unsold_minor_exports(none)` have no parameter for them. Contract turned them into return values / parameters (signature change relative to the graph).
15. **[S2] Graph states with no model field**: `sr_status`, `turn.stage`, `turn.c_used`, `turn.acted`, `items_with_bids`, `pending_minor_floats`, `phase_events`, `removed_items` for concessions. Model fields with no graph state: `round_number`, `stock_rounds_completed` (used for `sr_count`), `priority_deal_player_id`, `operating_*`, `MajorCompanyState.concession_holder_player_id / concession_converted / share_price`, `MinorCompanyState.share_price / floated / removed / acquired_by_major`, `PrivateCompanyState.*`, `BankState.discarded_trains`, `Player.tax_haven_shares`.
16. **[S3] `const.*` marked `missing=true` (certificate limit, bidding tokens, market grid, yellow cells, game-end cells, start cells, train counts)** are all present in the given data tables (`SETUP_BY_PLAYER_COUNT`, `stock_market.py`, `TRAIN_TYPES`); the graph correctly marks them missing from the rulebook but gives no pointer. Constants not in any table: face values, bid rules (5, 3), share structure (10/5/6 units) - they need module constants (BINDING). `const.phase_table` has no machine-readable table in `data/phases.py` (only prose `triggered_by`).
17. **[S3] The stock-market data module warns that movement adjacency is "not encoded with full confidence"** while the graph (R12) fixes "down = row+1 same column, absent cell = no move". Contract follows R12 on the given grid (row 13 col 5 -> row 14 col 5 absent: no move).

### A.2 Missing or ambiguous behaviour in graph nodes
18. **[S2] `place_bid` + `move_bid`**: merged by the given API `place_or_move_bid`; graph errors `ERR_ALREADY_HAS_TOKEN` and `ERR_NO_TOKEN_ON_ITEM` become unreachable; branch rule (token already on item = move) is not in the graph.
19. **[S2] `ERR_BAD_AMOUNT` covers three separate preconditions** (multiple of 5, minimum, cash) in `bid_amount_valid` (a bool); no way to distinguish them.
20. **[S2] `sale_legal` returns one record; `sell_shares` has three distinct codes** (`ERR_NOT_SELLABLE`, `ERR_POOL_FULL`, `ERR_TOO_MANY`). The contract re-evaluates clauses in shares.py; the derived node does not expose the failing clause.
21. **[S3] Error precedence** is never stated (buy_share has nine preconditions; sell, bid, convert similar).
22. **[S2] `buy_share` `source`**: graph parameter is mandatory `{treasury, pool}`; given action passes `None` when absent. A12 says the buyer chooses; no default.
23. **[S3] `repay_loans`**: no error for `amount > loans` or `amount <= 0`; no caller.
24. **[S3] `check_game_end_triggers`**: inside one call, whether `immediate` may replace an `after_next_or` set earlier is unspecified; "no context" semantics unspecified.
25. **[S3] `float_minors` effect list**: "[10.1.1] call check_game_end_triggers" - once after the loop or per minor? Not stated. Same for `pay_concession_dividends`.
26. **[S2] `phase_check`**: (a) clearing of concessions sits ambiguously inside/outside the `new > phase` branch; (b) phase skipping (A18) loses rust events of skipped phases; (c) the 2.1.2 deferral of the two-OR change has no node; (d) the effect on `phase_events` is a queue with no field/consumer.
27. **[S2] `export_train`**: the deck is an ordered list in the graph, a count dict in the model (`bank.train_pool`; L/2 and 7/E are double-sided with an initial `L=22,2=0`, `7=16,E=0` split). How a flipped card is counted is not defined; "L/2 remaining" and "front train" need a convention (BINDING T12).
28. **[S3] `place_start_token` for minors (4.11.5)** "above every major token and below existing minor tokens" is impossible to satisfy when minors and majors interleave (given `place_token` puts moved minors at the bottom). Contract: after the leading run of minor tokens.
29. **[S3] A26 (upper row first for equal price and column) is stated in the graph; the given `descending_price_key` does not implement it** (and with the given grid the case cannot occur).
30. **[S3] `can_sell_any` uses `s = 1` only; `sale_legal` `successor` with remaining units r**: fine, but the derived nodes do not say what to do for a company id that is not a started major.
31. **[S2] `drv.operating_order` / `next_operating_company`** are specified, but acquisition of minors by majors (`acquired_by_major`, phase 2+) is not; floated minors stay in the order forever.
32. **[S3] `convert_concession`**: no certificate-limit effect stated (count unchanged: concession 1 -> director certificate 1), leading bids ignored (A7), P16 and 4.8 deferred (R11), so after phase 5 an unconverted major never starts (A25) - a dead end the graph states as a consequence.
33. **[S3] R6** ("bidding does not count as a sale") is an open conflict with phase 1 (only bids possible); provisional "a bid that wins counts" is in `resolve_bids`; the check at step 9 therefore reads a flag the bids already set. Owner decision pending in graph.
34. **[S3] A15, A16, A4, A5, A9, A10, A11, A13, A17, A21-A24, A26, A28**: graph-declared assumptions; each is implemented literally in the contracts but remains owner-open (listed in GRAPH_NOTES section 4). Two of them were found to matter for implementers: A13 (pass definition) cannot be applied (see 1-2); A9 (batch sale priced before the drop) interacts with the one-call-per-turn actions.
35. **[S3] `pay_concession_dividends`**: phase >= 5 guard is a precondition without an error (contract: no-op); private revenues (3.1.2) are explicitly outside, so OR step A is incomplete.
36. **[S3] `player_wealth` / final scoring**: only a derived formula; no action for end-of-game, winner or the marking of `game_over` after the last OR.
37. **[S3] `resolve_stock_round` precondition `sr_over`** is a derived node of another component (`sr_flow`) while `resolve_stock_round` is in `sr_resolution`; with the file split the contract uses a lazy import. The error `ERR_NOT_OVER` has no exception class in the graph.
38. **[S3] Graph error codes carry no exception type**; contract convention: class per module with `"<ERR_CODE>: text"` messages.
39. **[S3] Cash/units consistency of `shares_in_treasury`**: models.py comment says "director's cert = 2" in treasury units; operating.py `_pay_major_dividend` counts treasury units as plain units. Graph `treasury_shares` (8/9) agrees with operating.py; the comment in models.py is ambiguous.
40. **[S3] Which module writes `priority_deal_player_id`** (not in graph) - setup sets it, `reorder` and `start_stock_round` keep it equal to `player_order[0]` (binding).
41. **[S3] Rulings R11/R12 arrows**: graph says up/down only; given `operating._move_price` moves along rows and ignores the arrow rule; the two code paths use different movement models (not a contract problem, a consistency risk).
42. **[S3] Round-number accounting**: graph `sr_count` ("1 during the first stock round") vs model `stock_rounds_completed` (starts at 0) and `round_number` (starts at 1, never described); contract defines `sr_count = stock_rounds_completed + 1` while a round runs.

---------------------------------------------------------------------------------------------------------------------
## B. What in BINDING had to be guessed (not determined by graph or given code)

B-1. `Player.shares[c]` stores units incl. the director's certificate (determined by operating.py's dividend loop and models comment, but the graph never says so).
B-2. `sr_count` := `stock_rounds_completed + 1` during a round; `end_stock_round` increments `stock_rounds_completed` after resolution; `round_number` untouched.
B-3. `repay_loans` exported although unreachable (no given caller).
B-4. `sold_this_round` values stored as lists.
B-5. Mirrors with no graph state: `MajorCompanyState.concession_holder_player_id`, `concession_converted`, `PrivateCompanyState.owner_player_id`, `MinorCompanyState.share_price`, `MinorCompanyState.floated`, `priority_deal_player_id`.
B-6. `has_operated` written by `round_manager.advance_company` for majors.
B-7. `st.removed_items` for concessions and privates: not stored; minors: `removed=True`.
B-8. `st.phase_events` represented by `state.log` lines (format fixed in BINDING A.1); no consumer exists.
B-9. `st.items_with_bids`, `st.pending_minor_floats`: return values/parameters (tuple shapes fixed in BINDING A.1); `float_minors(state, pending)`, `unsold_minor_exports(state, items_with_bids)` signatures changed from the graph.
B-10. Train pool convention (T12): L/2 remaining = `pool["L"] + pool["2"]`, 7/E likewise; scan order `L,2,3,4,5,6,7,E`.
B-11. `start_cell(price, kind)` got an extra `kind` parameter; start/yellow/game-end cells are read from `StockCell.zone/game_end` (checked: start cells (4,4) 100 ... (9,4) 50; game end (0,3)).
B-12. `place_or_move_bid`: place vs move chosen by `player_id in item.bids`; `ERR_NOT_OUTBID` when the player leads; amount must be a plain int.
B-13. `buy_share` with `source=None`: pool first, else treasury (INTERIM).
B-14. `buy_train_from_bank` minimal data-table behaviour (INTERIM, section A item 9).
B-15. Operating-round sequencing in round_manager (start/advance/end of OR, `"next_or" -> "or_set_end"` conversion, `operating_rounds_this_set` from `PHASES_BY_NUMBER`) (INTERIM, A item 8).
B-16. `check_game_end_triggers(state, context=None)`: with `context=None` only effects 1 and 2; OR-context mapping `"or_end"` (token) / `"or_set_end"` (bank).
B-17. `end_stock_round` stops (no OR) when `game_over` is set by the nothing-sold trigger.
B-18. `start_stock_round` does not raise `ERR_SR_ALREADY_RUNNING`.
B-19. Lazy-import layering of modules (COMMON 2): which direction each cross-file call imports; `sr_over` import in bidding is lazy.
B-20. Error messages are `"<ERR_CODE>: ..."`; extra exception classes `CertificateError`, `MarketError`, `RoundError`.
B-21. `float_minors` calls the game-end check once after the loop; `pay_concession_dividends` once after payments.
B-22. Concession clearing at phase >= 5 is invoked when the phase has just risen to >= 5.
B-23. `advance_stock_player` does not touch `consecutive_passes` and raises nothing.
B-24. Error precedence orders in shares.md (sell 1-4, buy 2-9) and bidding.md (1-8) chosen in graph listing order.
B-25. Minor token placement index in a pile = length of the leading run of minor tokens.

---------------------------------------------------------------------------------------------------------------------
## C. The three most serious gaps
1. **Operating-round / phase / train side is outside the graph but required by the skeleton** (A items 8, 9, 26, 27): `buy_train_from_bank`, `active_company_id`, `advance_company`, OR sequencing, game-end maturity, `has_operated` writer, `phase_events` consumers. Contract authors had to write INTERIM behaviour; two modules (`trains`, `round_manager`) are largely unspecified by the graph.
2. **The graph's turn model contradicts the given actions.py** (A items 1, 2, 6, 7): sell/repay/choice sequencing, `end_turn`, pass preconditions, `bids_this_turn` ownership; some graph preconditions are vacuous or unenforceable, and a literal implementation of the graph would double count bids.
3. **State-to-model mismatches the graph does not describe** (A items 4, 5, 10-15): units vs certificates and `Player.shares`, 0-based box indices and `ref` types, no field for `sr_status/turn.*/phase_events`, set vs JSON, `new_game` pre-starting the round, local-only states passed between procedures. Every one needed a binding decision.
