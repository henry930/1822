# Contract: `backend/app/engine/scoring.py`  (part of graph component `comp.sr_flow`: game end, wealth, concession dividends)

Read COMMON.md and BINDING.md first. Layer 3. Top-level imports allowed: `models` (`GameState`, `RoundType`), `turn_order`
(`token_cell`, `is_game_end_cell`, `current_price`), `certificates` (`units_held`). No lazy imports needed.

Given callers (exact):
- `actions.apply_action`: `check_game_end_triggers(state)` after EVERY action (one positional argument).
- `operating._move_price`: `check_game_end_triggers(state)` after every token move.
So the second parameter MUST be optional: `check_game_end_triggers(state, context: str | None = None)`.
Other callers (new modules): `shares.sell_shares` -> `(state, "after_bank_payment")`, `company_formation.convert_concession` and
`float_minors` -> `(state, "after_bank_payment")`, `turn_order.move_token_up` -> `(state, "after_token_move")`,
`bidding.resolve_stock_round` step 9 -> `(state, "end_of_stock_round")`, `scoring.pay_concession_dividends` -> `(state, "after_bank_payment")`.

Field binding (BINDING A.1 `st.game_end`): "a trigger exists" = `state.game_over or state.end_trigger_pending is not None`.
`immediate` = `state.game_over = True`. `after_next_or` = `state.end_trigger_pending = "next_or"`.

---------------------------------------------------------------------------------------------------------------------
## 1. `bank_broken(state) -> bool`   (`drv.bank_broken`; 10.1.1, A29, 4.3.5)
Formula: `state.bank.cash < 0` (loans are not part of it).

## 2. `check_game_end_triggers(state, context=None)`   (`act.check_game_end_triggers`; 10.1.1, 10.1.2, R6)
Context values: `"after_bank_payment"`, `"after_token_move"`, `"end_of_stock_round"`, or `None` (call from actions.py / operating.py; means
"after any change": evaluate only effects 1 and 2).
Precondition [10.1.2]: if a trigger already exists: do nothing (the first trigger stands; never overwrite).
Effects, evaluated in this order, stop at the first that sets a trigger (a trigger set by an earlier effect is never overwritten):
1. [10.1.1] if `bank_broken(state)`: trigger = after_next_or  -> `state.end_trigger_pending = "next_or"`.
2. [10.1.1] if any company token is on a game-end cell (`any(is_game_end_cell(state, c) for c in state.stock_positions)`; use
   `turn_order.is_game_end_cell`): trigger = after_next_or -> `"next_or"`.
3. [10.1.1, R6] if `context == "end_of_stock_round"` and it is the first stock round and `not state.any_sale_this_stock_round`:
   trigger = immediate and over = true -> `state.game_over = True`.
   "First stock round" (BINDING `st.sr_count`): `state.stock_rounds_completed == 0` at the time of the call (round_manager increments it after resolution).
Errors: none for legal input (`ERR_ORDER` in the graph = called outside the documented order: not checked).

Effects 1 and 2 above are the graph's stock-round effects. When `state.round_type == RoundType.OPERATING` the graph has no
effect; the only available specification is the comment on `GameState.end_trigger_pending` in models.py (given code):
INTERIM (not in graph): operating round + token on game-end cell -> `"or_end"`; operating round + bank broken -> `"or_set_end"`; stock round + either ->
`"next_or"` (effects 1/2). Effect 3 applies only with `context == "end_of_stock_round"`. This function never sets `game_over` except by effect 3.

## 3. `pay_concession_dividends(state)`   (`act.pay_concession_dividends`; 3.4.4, 5.2.1, R9)
Precondition [R9]: `state.phase < 5` (concessions exist). If `phase >= 5`: do nothing.
Effects: [3.4.4, 5.2.1] for every player and every concession held (`len(player.concessions)` times): `player.cash += 10; state.bank.cash -= 10`.
[10.1.1] then `check_game_end_triggers(state, "after_bank_payment")` (once, after all payments; graph says "call" once).
Called by `round_manager` at the start of an operating round (step A of 5.2.1). Private-company revenues are not part of this graph (3.1.2 is data outside).

## 4. `player_wealth(state, pid) -> int`   (`drv.player_wealth`; 10.1.3, A34)
Formula: `cash + sum over majors c of units_held(p,c) * current_price(c) + 100 * |concessions held| - loans`; privates and company assets count 0.
Majors without a token on the market (unstarted) contribute 0 (they have no holders either). `units_held` = `certificates.units_held`
(director's certificate counts `cert_units`); `current_price` = `turn_order.current_price`. Concessions are valued 100 only while held (they are removed at phase 5).

---------------------------------------------------------------------------------------------------------------------
## Graph gaps (do not decide; report)
1. The graph's `context` parameter does not match the given one-argument callers; the contract adds a default `None`. What "no context" should evaluate is not specified (contract: effects 1 and 2 only).
2. Effects 1/2 yield only `after_next_or`; the graph enum also has `end_of_current_or` but nothing writes it and the graph does not say when an operating-round token/bank trigger becomes `end_of_current_or` versus `after_next_or`. The OR mapping above is taken from models.py comments, not from the graph.
3. Who sets `game_over = True` when a deferred trigger matures (end of the OR / OR set) is not in the graph (round_manager must do something; see round_manager.md).
4. Effect 3 versus effect 1/2 inside one call: the graph says "never overwrite an existing trigger" and also "immediate and over = true"; whether `immediate` may replace an `after_next_or` set earlier in the same call is unspecified (cannot happen in the first stock round with a sane bank).
5. R6 is explicitly "open conflict" (phase 1: only bids exist); the provisional rule (a bid that wins an item counts as a sale) is implemented in `bidding.resolve_bids`, not here.
6. `player_wealth` for a floated major whose token is missing, and for stock held by the bank pool/treasury: unspecified (contract: only players' units count).
7. `pay_concession_dividends`: graph does not say whether the dividend is paid to concessions held by players only (yes by formula) nor what happens to bank cash going negative mid-loop (trigger check happens once, after the loop).
8. No graph node for final scoring / winner selection / marking `game_over` after the last operating round.
