# Contract: `backend/app/engine/round_manager.py`  (graph component `comp.sr_flow`: round/turn state machine; plus the operating-round sequencing required by given code)

Read COMMON.md and BINDING.md first (A.1 rows `st.sr_order`, `st.sr_count`, `st.sr_status`, `st.turn`, `st.pass_streak`, `st.sale_happened`, `st.sold_this_round`, `st.has_completed_or`; A.6; C.5).
Layer 7 (top). Top-level imports allowed: everything below it: `models` (`RoundType`), `app.data.phases` (`PHASES_BY_NUMBER`), `bidding` (`refill_boxes`, `resolve_stock_round`),
`turn_order` (`next_operating_company`), `scoring` (`pay_concession_dividends`). No lazy imports needed (nobody below imports you at top level except `bidding.resolve_stock_round`, lazily).
Exception: `class RoundError(Exception)`.

Given callers (exact), from actions.py:
- `active_company_id(state)` -> company id or `None`; `advance_company(state)`; `advance_stock_player(state)`; `end_stock_round(state)`; and main.py: `start_stock_round(state)`.
- `actions._apply_pass` (stock round): `state.consecutive_passes += 1`; if `consecutive_passes >= len(state.player_order)`: `end_stock_round(state)` else `advance_stock_player(state)`.
- every other stock action: actions sets `consecutive_passes = 0` itself, then `advance_stock_player(state)`.
- operating round: `_apply_operate` and `_apply_pass` check `company_id == active_company_id(state)` and the director, then call `advance_company(state)`.
Consequently: `advance_stock_player` is used for BOTH "end_turn" and "pass_turn (not last)". It must NOT touch `consecutive_passes`
(the pass-streak writes `st.pass_streak` of `act.end_turn`/`act.pass_turn` are performed by actions.py). actions.py does the active-player check
(`ERR_NOT_ACTIVE`/`ERR_WRONG_PLAYER`) and the "game over" check.

---------------------------------------------------------------------------------------------------------------------
## 1. Derived functions

### `sr_over(state) -> bool`   (`drv.sr_over`; 4.11.1, 4.1.4)
Formula: `pass_streak == player_count` -> `state.consecutive_passes >= len(state.player_order)`.

### `next_player(state, pid) -> str`   (`drv.next_player`; 4.1.2)
Formula: `sr_order[(index(p) + 1) mod n]` -> `state.player_order[(state.player_order.index(pid) + 1) % len(state.player_order)]`.

## 2. Actions of the stock-round state machine

### `begin_turn(state, pid)`   (`act.begin_turn`; 4.1.2, 4.1.3)
Make a player active and reset the per-turn record: `state.active_player_id = pid; state.bids_this_turn = 0`. (`stage`, `c_used`, `acted`: no fields, vacuous.)
Precondition [4.1.2]: `pid` is in `state.player_order` (else `RoundError("ERR_WRONG_PLAYER: ...")`); whether it is the correct successor is guaranteed by the callers.

### `advance_stock_player(state)`   (`act.end_turn`; 4.1.2, 4.4.7, R10)
Effects: [4.1.2] `begin_turn(state, next_player(state, state.active_player_id))`.
The graph's `act.end_turn` also sets `pass_streak = 0` and checks `turn.acted` and `not must_sell(player)` (`ERR_NO_ACTION_TAKEN`, `ERR_MUST_SELL`): NOT implementable here (see Graph gaps 1-3): do not reset `consecutive_passes`, do not raise.

### `start_stock_round(state)`   (`act.start_stock_round`; 1.7.14, 4.1.1, 4.1.2, 10.1.2, R15)
Preconditions: [10.1.2] game not over: `state.game_over` -> `RoundError("ERR_GAME_OVER: ...")`.
`ERR_SR_ALREADY_RUNNING` (sr_status in {not_started, finished}) is NOT raised: there is no `sr_status` field and `new_game` returns a state that is already inside round 1,
and main.py's debug endpoint calls this function at arbitrary times (BINDING A.1 `st.sr_status`, A.6).
Effects, in this order:
1. [4.1.1] `bidding.refill_boxes(state)` (start-of-round refill).
2. `state.round_type = RoundType.STOCK` (binding: sr_status = in_progress).
   `sr_count += 1`: nothing to write (`sr_count` = `stock_rounds_completed + 1`, BINDING).
3. [R15] `state.any_sale_this_stock_round = False`.
4. `state.sold_this_round = {}`; `items_with_bids`, `pending_minor_floats`: nothing to clear (not stored); `state.consecutive_passes = 0`.
5. [4.1.2] `state.priority_deal_player_id = state.player_order[0]` (binding, A.1 `st.sr_order`) and `begin_turn(state, state.player_order[0])`.

### `end_stock_round(state)`   (`act.pass_turn`, branch "if drv.sr_over then trigger resolve_stock_round and set sr_status = resolving"; 4.11.1)
Called by actions._apply_pass after `consecutive_passes` reached `len(player_order)`.
Effects, in this order:
1. [4.11.1] `sr_status = resolving` (not stored). Precondition `sr_over(state)`; else `RoundError("ERR_NOT_OVER: ...")`.
2. `bidding.resolve_stock_round(state)` (triggers resolution steps 1-9; BINDING C.4).
3. `state.stock_rounds_completed += 1` (BINDING `st.sr_count`; after the resolution so that step 9 sees the first round as `stock_rounds_completed == 0`).
4. If `state.game_over` (set by an `immediate` trigger in step 9): stop here (no operating round is started; actions.apply_action then reports game over on the next action).
5. Otherwise INTERIM (see section 3): `start_operating_round(state)`.

## 3. Operating-round sequencing (REQUIRED BY GIVEN CODE; NOT IN THE GRAPH EXCEPT 5.2.1, 5.2.2 and two derived nodes) - INTERIM
Sources used: rules 5.2.1/5.2.2 (graph: `drv.operating_order`, `drv.next_operating_company`, `act.pay_concession_dividends`), the comments on `GameState.operating_rounds_this_set`,
`operating_order`, `current_company_index`, `operating_round_index`, `end_trigger_pending`, `game_over` in models.py, and the way actions.py/main.py use them.
Everything in this section is flagged to the owner; do not add more.

### `active_company_id(state) -> str | None`
`None` unless `state.round_type == RoundType.OPERATING` and `0 <= state.current_company_index < len(state.operating_order)`; else `state.operating_order[state.current_company_index]`.

### `start_operating_round(state)`  (start of an operating-round SET)
1. `state.round_type = RoundType.OPERATING`; `state.operating_round_index = 0`;
   `state.operating_rounds_this_set = PHASES_BY_NUMBER[state.phase].operating_rounds_per_stock_round` (captured now, models.py comment; the rulebook's "increase applies only after the following stock round" 2.1.2 is NOT implemented: GAP).
2. If `state.end_trigger_pending == "next_or"`: set it to `"or_set_end"` and `state.operating_rounds_this_set = 1` (models.py comment: "resolved into or_set_end with operating_rounds_this_set forced to 1").
3. Call the private helper that begins one operating round (below).

### private `_begin_operating_round(state)`
1. [5.2.1 A] `scoring.pay_concession_dividends(state)`. (Private-company revenue: not in graph, not paid.)
2. `state.operating_order = []; state.current_company_index = 0`.
3. [5.2.1 B/C, 5.2.2] `first = turn_order.next_operating_company(state, set())`. If `None`: no company operates: call `_end_operating_round(state)`. Else `state.operating_order = [first]`.
   (`operating_order` holds the companies chosen so far in this OR; the current one is at `current_company_index`; this matches main.py's debug code `operating_order = [company_id]; current_company_index = 0`.)

### `advance_company(state)`
Called after a company's operating action or a director's pass in an operating round.
1. If the company just finished (`active_company_id`) is a major: `state.majors[c].has_operated = True` (BINDING `st.has_completed_or`; graph note: "set true by the operating-round module after the company's first completed operating turn").
2. [5.2.2] `done = set(state.operating_order[: current_company_index + 1])`; `nxt = turn_order.next_operating_company(state, done)` (recomputed now, because sales may have changed prices).
3. If `nxt` is not `None`: `state.operating_order = state.operating_order[: current_company_index + 1] + [nxt]; state.current_company_index += 1`. Else `_end_operating_round(state)`.

### private `_end_operating_round(state)`
1. [models.py comments on `end_trigger_pending`] if `state.end_trigger_pending == "or_end"`: `state.game_over = True`; return.
2. `state.operating_round_index += 1`. If `state.operating_round_index < state.operating_rounds_this_set`: `_begin_operating_round(state)`; return.
3. The set is finished: if `state.end_trigger_pending == "or_set_end"`: `state.game_over = True`; return.
4. Otherwise `start_stock_round(state)`.

---------------------------------------------------------------------------------------------------------------------
## Cross-module obligations
- Calls: `bidding.refill_boxes` (start_stock_round), `bidding.resolve_stock_round` (end_stock_round), `turn_order.next_operating_company`, `scoring.pay_concession_dividends`.
- Owns the writes: `active_player_id`, `bids_this_turn` (reset), `priority_deal_player_id` (start), `any_sale_this_stock_round` reset, `sold_this_round` reset, `stock_rounds_completed`,
  `round_type`, `operating_order`, `current_company_index`, `operating_round_index`, `operating_rounds_this_set`, `game_over` (OR end), `MajorCompanyState.has_operated`.
- `consecutive_passes` is written by actions.py (+ reset to 0 in `start_stock_round`).

## Graph gaps (do not decide; report)
1. `act.end_turn` / `act.pass_turn` carry preconditions (`not must_sell`, `turn.acted` true/false, `ERR_MUST_SELL`, `ERR_NO_ACTION_TAKEN`, `ERR_ACTION_ALREADY_TAKEN`) that cannot be evaluated: the given actions.py increments the pass counter before calling any new module and never calls `end_turn`; the state `turn.acted` has no field. A player over the limit who can sell is therefore able to pass; R10 is only enforced for buy/bid/convert.
2. The graph's sell -> repay -> C turn sequence (order edges, `turn.stage`) contradicts the given actions.py, which ends the turn after each of sell/buy/convert/bid; the graph forbids neither.
3. `ERR_SR_ALREADY_RUNNING`: `sr_status` has no field and main.py calls `start_stock_round` in any state (debug). Not raised.
4. The graph (`act.start_stock_round`) has no effect for the round-type switch, the round counter (`round_number`), `operating_order`/`current_company_index`, or the OR set state; those fields exist in the model.
5. No graph node for the operating round as a whole: sequencing of ORs after a stock round (number of ORs per phase, the 2.1.2 deferral "two ORs only from the stock round after the phase starts"), the end of an OR/OR set, when `game_over` is set after a deferred trigger, the meaning of `"or_end"/"or_set_end"/"next_or"` versus the graph enum `end_of_current_or/after_next_or`, and a safe stop when no company has floated. Everything in section 3 is INTERIM.
6. `has_completed_or` writer: graph names "the operating-round module" (not present in given code). Binding assigns `advance_company` (majors only).
7. `act.start_stock_round` precondition "player is the next in sr_order after the previous turn's player" of `begin_turn` is guaranteed by callers, not checkable.
8. Private-company revenue (3.1.2) and minor/major operating (5.3+) are outside the graph; `pay_concession_dividends` is the only OR step A item.
9. The effect of `check_game_end_triggers` result `game_over` being set during a stock round's resolution on `end_stock_round` (stop without OR) is not in the graph (it says only `over = true`).
10. `drv.sr_over` is `==` in the graph; actions uses `>=`; equivalent for valid play.
