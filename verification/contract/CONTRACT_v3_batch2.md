# Contract v3: second batch of the 1822 rules engine (trains, scoring, round manager, earnings, ruling patch)

Rulebook excerpt: `RULES.md` (rulebook wins when clear). Python >= 3.11, money in integer pounds, run from `backend/` with `PYTHONPATH=.`.
The rest of the engine is given and must NOT be modified, except where a task below says so: models, setup, actions, operating (tile/route code),
board, routes, network, stock_positions and the stock-round modules `shares/certificates/company_formation/bidding/turn_order`
(already written; they follow earlier contracts). Do not read anything outside `/home/claude/sandbox_b2`. No git, no network.
Several agents work in parallel, each owning different files (listed per task). Never edit a file you do not own.
Data: `app.data.phases.PHASES_BY_NUMBER` (train limits, `trains_rusted`, `operating_rounds_per_stock_round`, `concession_rule`),
`app.data.trains` (costs, counts, `L_TO_2_UPGRADE_COST`), `app.data.stock_market` (cells), `app.data.private_companies` (revenue).

## Shared facts and rulings (the rules owner decided these)
- Bidding on items does NOT count as a sale for rule 10.1.1. Buying shares, selling shares and converting a concession DO set
  `state.any_sale_this_stock_round = True`. `bidding.place_or_move_bid` must NOT set it (earlier contract said it should: reversed).
- From phase 5 unconverted concessions are removed from play: held concessions disappear from `player.concessions`; concessions still in
  `state.concession_bid_boxes` are cleared (set to None; do not refill them afterwards). Concessions are never offered again.
- Price token movement to a cell that already has tokens: the token goes to the BOTTOM of the stack (`stock_positions.place_token`).
- Stock-market direction: rows increase downward (row 0 top); right = col+1 along the row; "up" = row-1 same column; "down" = row+1 same column.
  Arrow rule (5.12.13), provisional because the data has no arrows: moving right off the end of a row moves the token up one row
  (same column, if that cell exists, else it stays); moving left off the start moves it down one row (same column, if it exists, else stays).
  For a two-space move that runs off the end, the first space is the last cell and the remaining step is the arrow move.
- The game's call graph: `actions.py` calls `round_manager.{active_company_id, advance_company, advance_stock_player, end_stock_round}`,
  `scoring.check_game_end_triggers`, `trains.{TrainError, buy_train_from_bank}`, `operating.distribute_earnings`.
  `bidding.py` calls `trains._advance_phase_and_rust(state, code)`, `trains._enforce_train_limits(state)`, `trains.current_buyable_pool(state)`.
  `operating.py` (given) imports `distribute_earnings` from `earnings.py`, calls `trains.buy_train_from_bank`, `scoring.check_game_end_triggers`.
  `main.py` calls `round_manager.start_stock_round`. Keep every one of these names and signatures.

## Task T: `trains.py` (owner: agent T)
Rules 2.1.1-2.1.5, 2.2.x (via PHASES_BY_NUMBER), 5.13.1-5.13.11, 3.4.5 (+ ruling above).
- `class TrainError(Exception)`; `TRAIN_ORDER = ["L","3","4","5","6","7"]` (L/2 share a pool; 7/E share a pool).
- `current_buyable_pool(state) -> str|None`: first pool in order with trains left in `state.bank.train_pool`.
- `buy_train_from_bank(state, company_id, kind, want_code) -> int` (kind "minor"|"major"; returns the price). Pays face value from the company
  treasury to the bank; trains are bought in order (5.13.4); the company must be below its train limit BEFORE buying (5.13.6/5.13.7, limit
  from the current phase: minor/major); at most one E-train per company (5.13.11); L/2 and 7/E: buyer chooses the side (5.13.8/5.13.10);
  raises TrainError on any violation (insufficient funds: forced purchase 5.14 is out of scope, just raise). Then advances the phase and
  rusts trains (2.1.3), then enforces train limits (2.1.4, 2.1.5: excess discarded to `state.bank.discarded_trains`; discard order inside
  one company: oldest first; with several companies, descending share price). Pool bookkeeping: `state.bank.train_pool[pool_key] -= 1`.
- `upgrade_l_to_2(state, company_id, kind) -> int`: rule 5.13.9 (phases 1 and 2 only; £80 = `L_TO_2_UPGRADE_COST`; counts as a purchase of a 2-train
  for the phase trigger; must be raised as TrainError if not allowed).
- `_advance_phase_and_rust(state, bought_code)`: set the phase (first 2 -> 2, 3 -> 3, 4 -> 4, 5 -> 5, 6 -> 6, 7/E -> 7; never lowers the phase),
  rust the trains of every phase passed (also removing that type from the bank pool: 2.1.3), and on reaching phase 5 apply the concession ruling.
  A phase change from a train purchase takes effect immediately; "operating rounds per stock round" is locked by round_manager at the start of an
  OR set (so you do not touch it).
- `_enforce_train_limits(state)`: rule 2.1.4/2.1.5 as above.
- After any purchase call `scoring.check_game_end_triggers(state)` (bank may have changed) only if you import it lazily inside the function.

## Task S: `scoring.py` and `round_manager.py` (owner: agent S)
Rules 5.1.1, 5.2.1 step A, 10.1.1-10.1.3, 4.11.1, 2.1.2.
- `scoring.check_game_end_triggers(state)`: sets `state.end_trigger_pending` (None | "or_end" | "or_set_end" | "next_or") exactly per 10.1.1/10.1.2
  (price token on a `game_end` cell; bank cash <= 0), first trigger wins, no effect if `state.game_over`.
- `scoring.final_wealth(state, player_id)`, `scoring.final_standings(state) -> list[(player_id, wealth)]` richest first: rule 10.1.3.
  (A minor's director certificate counts for the whole 50% block, i.e. twice the market price; majors: units x price; concessions at face value 100.)
- `round_manager`: `start_stock_round(state)`, `advance_stock_player(state)`, `end_stock_round(state)`, `start_operating_round_set(state)`,
  `start_operating_round(state)`, `advance_company(state)`, `active_company_id(state)`.
  * `start_stock_round`: round_type STOCK, passes 0, `any_sale_this_stock_round=False`, active player = `priority_deal_player_id`, bids_this_turn 0, sold_this_round {}.
  * `end_stock_round`: if `stock_rounds_completed == 0` and no sale -> `game_over=True` (10.1.1, nothing else changes). Otherwise call
    `bidding.resolve_stock_round`, `stock_rounds_completed += 1`, `player_order = turn_order.reorder_players_by_cash(state)`,
    `priority_deal_player_id = player_order[0]`, then `start_operating_round_set`.
  * `start_operating_round_set`: round_type OPERATING; `operating_rounds_this_set` locked from the CURRENT phase (2.1.2); `operating_round_index = 0`;
    if `end_trigger_pending == "next_or"`: cap the set at 1 OR and set the pending value to "or_set_end"; then `start_operating_round`.
  * `start_operating_round`: FIRST pay step A of 5.2.1: each private company that is open and owned by a player pays its fixed revenue (from
    `app.data.private_companies`, field for revenue; money comes from the bank; privates owned by a company pay to the company treasury) and each concession
    held by a player pays £10 (3.1.2, 3.4.4); then `operating_order = turn_order.compute_operating_order(state)`, `current_company_index = 0`;
    if the order is empty, advance as below. Call `check_game_end_triggers` after paying. Payment must happen at the start of EACH operating round.
  * `advance_company`: next company; at the end of the order go to the next OR / end of set.
  * End of an OR set, 10.1.1: if `end_trigger_pending == "or_end"` the game ends at the end of that OR; if the set is over: "or_set_end" -> game over, else `start_stock_round`.
    Log a line in `state.log` when the game ends.
  * `active_company_id`: id of the company to act, or None outside operating rounds / when past the end.

## Task E: `earnings.py` (owner: agent E, new file)
Rules 5.12.1-5.12.3, 5.12.7-5.12.14 (5.12.4-5.12.6 special trains: out of scope).
- `distribute_earnings(state, company_id, kind, revenue, choice) -> int` (returns the dividend paid, i.e. the figure that decides the price move).
  choice "full" | "half" | "withhold" (anything else: raise `app.engine.operating.OperatingError`; import it lazily to avoid a cycle, or define the same class
  name in earnings.py and make operating re-export it - you may not edit operating.py, so import lazily from `.operating`).
  Minor: always split, bank pays half to the director and half to the treasury (odd pound: the extra £1 goes to the treasury); dividend_paid = the half paid to
  the director; price moves right if non-zero else left. Major: withhold -> treasury gets all; full -> 10% of the dividend per 10% share to each holder, shares
  in the company treasury pay the company treasury, shares in the bank pool pay nothing (the money stays with the bank); half -> half rounded UP to the next
  multiple of £10 is the dividend (never more than the revenue), the rest goes to the treasury. The bank pays every pound out; `state.bank.cash` may go negative.
  Price: dividend 0 -> left one; < price -> no move; >= price -> right one; >= 2x price -> right two; for a minor see above. Arrow rule per shared facts.
  After the move call `scoring.check_game_end_triggers(state)` (import lazily).
- Helper names are yours, but keep `distribute_earnings` exactly.

## Task P: patch `bidding.py` and `shares.py` for rulings (owner: agent P, edits those two existing files only)
- bidding: remove the setting of `any_sale_this_stock_round` in `place_or_move_bid`. In `resolve_stock_round`, from phase 5 on clear concession bid boxes
  (apply the concession ruling; do not refill the concession boxes after that; if a concession box item had bids in phase 5+, nobody pays).
- shares: `sell_shares` sets `any_sale_this_stock_round = True`; `buy_share` sets it too. Add `must_sell_to_limit(state, player_id) -> bool`:
  True if the player owns more certificates than `certificates.certificate_limit` and still holds something sellable under the sale rules (4.4.7).
  While `must_sell_to_limit` is True, `buy_share` raises ShareError for that player (they must sell first) and `bidding.place_or_move_bid` raises BidError.
  `sell_shares` must stay within all sale rules; any sale is allowed to bring the player over-limit sales down; selling shares of a company in the yellow
  zone is not required to reduce the count (those shares are not counted).
- Keep all existing public names and behaviour otherwise.

## Required for every agent
1. Write only the files you own. Scratch tests go under `/home/claude/sandbox_b2/my_tests/<yourname>_*`.
2. When all the files of the other agents exist (poll with short sleeps, at most ~3 minutes; if still missing say so), run one end-to-end check through the public
   API (`new_game`, `actions.apply_action`: bids, passes, a stock round end, an operating round with a train purchase and an operate action) and report what happened.
3. Final report: (1) what you implemented, (2) numbered ambiguities/assumptions, (3) contract problems, (4) integration check result.
