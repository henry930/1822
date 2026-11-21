# Contract: `backend/app/engine/shares.py`  (graph component `comp.share_trading`: sell, buy, repay; plus loan interest from `comp.sr_resolution`)

Read COMMON.md and BINDING.md first (traps T1, T2, T6, T13; A.1 rows for cash, loans, shares, treasury, pool, sold_this_round, sale flag).
Layer 5. Top-level imports allowed: `models`, `certificates`, `turn_order`, `scoring`. No lazy imports.
Exception: `class ShareError(Exception)` (message prefix = code, COMMON 2).
`convert_concession` is NOT in this file (company_formation.py).

Given callers (exact), in actions.py:
```
buy_share(state, player_id, action["company_id"], action.get("source"))     # source: None | "treasury" | "pool"
sell_shares(state, player_id, action["company_id"], action["count"])
```
actions.py checks "it is your turn" and the round type BEFORE calling; afterwards it sets `consecutive_passes = 0`, and for buy also
`any_sale_this_stock_round = True`, then `advance_stock_player`. actions.py does NOT set `any_sale_this_stock_round` after a sale, so `sell_shares`
must set it. Because the turn ends after the call, the graph's `turn.stage / c_used / acted` preconditions and effects are vacuous (BINDING C.5): do not implement them.
Field names: `player = state.players[player_id]`; `major = state.majors[company_id]`; price via `turn_order.current_price`.

---------------------------------------------------------------------------------------------------------------------
## 1. `sell_shares(state, player_id, company_id, count)`   (`act.sell_shares`; 4.1.3, 4.3.3, 4.4.1-4.4.6, 4.5.5, R5, R15, 10.1.1)
Sell `s = count` ordinary certificates of one major company into the bank pool (one batch).

Preconditions (check all before any mutation), with the graph error codes:
1. [4.4.1] `company_id` is a major company (a key of `state.majors`); privates, minors and concessions can never be sold. Else `ERR_NOT_SELLABLE`.
2. [4.4.2] `major_status[c] = floated` and `has_completed_or[c]` (`major.floated and major.has_operated`). Else `ERR_NOT_SELLABLE`.
3. [4.4.2] `pool_shares[c] + s <= 5` (`major.shares_in_bank_pool + s <= 5`). Else `ERR_POOL_FULL`.
4. [4.4.2, R5] `certificates.sale_legal(state, p, c, s).legal`: `s <= ordinary_certs` unless the player is the director with an eligible successor
   (the director's certificate itself never goes to the pool). Else `ERR_TOO_MANY`. (Also `s < 1` -> `ERR_TOO_MANY`: `sale_legal` requires `s >= 1`.)
5. [4.3.3] loans do NOT block selling (no check on `player.loans`).
(`turn.active_player = player and turn.stage = A_sell`: vacuous; `ERR_WRONG_STAGE` is never raised.)
Check in the order 1, 2, 3, 4 (error precedence is not specified by the graph: GAP).

Effects, in this order [graph effect list]:
1. `price = current_price(c)` read BEFORE any move (A9: the whole batch is paid at the pre-drop price).
2. [4.4.2] `chk = sale_legal(state, p, c, s)`; if `chk.swap_needed`: `certificates.swap_director(state, c, chk.successor)` BEFORE the rest of the sale.
3. [4.4.1] `ordinary_certs[player,c] -= s; pool_shares[c] += s` -> `player.shares[c] -= s` (units; T1) and `major.shares_in_bank_pool += s`.
4. [4.4.3] `player.cash += s * price; state.bank.cash -= s * price`.
5. [4.4.4, 4.4.5] `turn_order.move_token_down(state, c, s)`.
6. [4.5.5] add `c` to `state.sold_this_round[player_id]` (list without duplicates; BINDING `st.sold_this_round`).
7. [R15] `state.any_sale_this_stock_round = True`.
8. [10.1.1] `scoring.check_game_end_triggers(state, "after_bank_payment")`.
Order of sale of several companies in one turn [4.4.6] is the order of calls; with the given actions.py one call = one turn.

## 2. `buy_share(state, player_id, company_id, source)`   (`act.buy_share`; 4.1.4, 4.2.4, 4.5.1-4.5.9, 4.3.1, R10, R15, 3.4.1)
Buy one ordinary share of a started major company from its treasury or from the bank pool.

Preconditions (check all before any mutation), graph error codes:
1. [4.5.4, 4.1.4] one certificate per turn: vacuous (the given actions end the turn). `ERR_C_ALREADY_USED` is never raised.
2. [4.3.1] `player.loans == 0`. Else `ERR_LOANS`.
3. [R10] `not certificates.must_sell(state, p)` (over the limit and still able to sell). Else `ERR_MUST_SELL`.
4. [4.5.2] `c` is a major, `major.floated` and `major.director_player_id is not None`. (The director's certificate is not buyable by "buy"; phase-5 buying is deferred.) Else `ERR_NOT_STARTED`.
5. [4.5.1] the chosen `source` holds >= 1 ordinary certificate (`shares_in_treasury >= 1` for `"treasury"`, `shares_in_bank_pool >= 1` for `"pool"`). Else `ERR_NO_SHARE_AT_SOURCE`.
   `source is None`: INTERIM (graph silent, A12): use `"pool"` if the pool holds a share, else `"treasury"` if the treasury holds one, else `ERR_NO_SHARE_AT_SOURCE`.
6. [4.5.1] `player.cash >= current_price(c)` (no allowance for money committed in leading bids, A7). Else `ERR_INSUFFICIENT_CASH`.
7. [4.5.5] `c not in state.sold_this_round.get(player_id, ())`. Else `ERR_SOLD_THIS_ROUND`.
8. [4.5.6] `units_held(p,c) < 6` (before the purchase). Else `ERR_AT_60_PERCENT`.
9. [4.5.7, 4.5.8] if `not turn_order.in_yellow(state, c)`: `cert_count(p) + 1 <= cert_limit` (even if directorship would change). If `in_yellow(c)` the limit is not checked. Else `ERR_CERT_LIMIT`.
10. [3.4.1] the director's certificate cannot be bought while the concession is in play: vacuous (only ordinary shares are bought here).
Check in the order 2, 3, 4, 5, 6, 7, 8, 9 (precedence not specified by graph: GAP).

Effects, in this order:
1. `price = current_price(c)` [4.5.3: the purchase does not change the price].
2. [4.5.1] `player.cash -= price`; if source = treasury: `major.treasury += price` and `major.shares_in_treasury -= 1`; if source = pool: `state.bank.cash += price` and `major.shares_in_bank_pool -= 1`.
3. [4.5.1] `ordinary_certs[player,c] += 1` -> `player.shares[c] = player.shares.get(c, 0) + 1`.
4. [4.5.9] if `units_held(player,c) > units_held(director_holder[c], c)` (evaluated after step 3; the director is `major.director_player_id`; skip when the buyer is the director): `certificates.swap_director(state, c, player_id)`.
5. [R15] `state.any_sale_this_stock_round = True`.
No game-end check is called in the graph for buy_share.

## 3. `repay_loans(state, player_id, amount)`   (`act.repay_loans`; 4.1.3, 4.3.2, 4.3.3, 4.3.5)
Pay all or part of the player's loans to the bank (step B). NO GIVEN CALLER (actions.py has no repay action; GAPS A-1). Implement and export anyway.
Preconditions: `0 < amount <= min(loans, cash)`: `player.loans == 0` -> `ERR_NO_LOANS`; `player.cash < amount` -> `ERR_INSUFFICIENT_CASH`; `amount <= 0` or `amount > player.loans`: the graph has no
error code (GAP); INTERIM use `ERR_BAD_AMOUNT`. No obligation to sell to raise the money [4.3.3]. (`ERR_WRONG_STAGE` vacuous.)
Effects: [4.3.2] `player.cash -= amount; player.loans -= amount`; [4.3.5] `state.bank.cash` unchanged (A28).

## 4. Interest (from `comp.sr_resolution`, called by `bidding.resolve_stock_round` step 6)
### `interest_amount(loans) -> int`   (`drv.interest_amount`; R14, 4.3.4)
`ceil(L/2) = (L + 1) // 2`.
### `charge_interest(state)`   (`act.charge_interest`; 4.11.10, 4.3.4, 4.3.5, R14)
Precondition: applies only to players with `loans > 0`.
Effects: [R14, 4.11.10] for each player with `loans > 0`: `loans += interest_amount(loans)`; [4.3.5] `state.bank.cash` unchanged.

---------------------------------------------------------------------------------------------------------------------
## Cross-module obligations
- `sell_shares` calls: `certificates.sale_legal`, `turn_order.current_price`, `certificates.swap_director`, `turn_order.move_token_down`, `scoring.check_game_end_triggers` (graph edges of `act.sell_shares`).
- `buy_share` calls: `turn_order.current_price`, `certificates.units_held`, `certificates.cert_count`, `certificates.cert_limit`, `turn_order.in_yellow`, `certificates.must_sell`, `certificates.swap_director`.
- Writers: this file writes `Player.shares`, `Player.cash`, `Player.loans`, `state.bank.cash`, `MajorCompanyState.treasury / shares_in_treasury / shares_in_bank_pool`, `state.sold_this_round`, `state.any_sale_this_stock_round`.
- `has_operated` is written by `round_manager.advance_company` (not here).
- It is `company_formation.convert_concession` that creates the first holdings and sets `shares_in_treasury` (8 / LNWR 9); buy_share only requires `director_player_id is not None`.

## Graph gaps (do not decide; report)
1. `source` = None: graph (A12) says "buyer chooses"; the given action may pass None. Default is INTERIM.
2. Error precedence among simultaneously violated preconditions is not defined (sell: ERR_NOT_SELLABLE / POOL_FULL / TOO_MANY; buy: eight codes).
3. `repay_loans`: the graph names no error for `amount > loans` or `amount <= 0`; no given code calls it (turn stage B is not reachable through actions.py).
4. `sell_shares` cannot distinguish through `sale_legal` why a sale is illegal (single record), so ERR_TOO_MANY is a catch-all for "illegal but not unstarted/not operated/pool full".
5. Selling shares of the company in which the player is the only holder (director with no successor) and `s <= ordinary_certs`: legal by the graph formula; a director selling all ordinary certificates keeps the director's certificate (4.4.2) - stated, no gap; but whether `count` may refer to the director's certificate units when `s <= k` and a swap is possible but undesired is not asked: the swap is automatic when a successor exists (A10).
6. `buy_share` does not check that the company's token exists on the market (a floated major always has one by convert_concession).
7. `buy_share` when the buyer is already the director and buys the 6th unit etc.: covered by `units_held < 6` only; the 4.5.9 swap test compares with the director's units (equal when buyer is the director: no swap).
8. 4.5.5 "sold earlier in the same stock round": `sold_this_round` is reset by `start_stock_round`; the very first stock round is started by `new_game` (default `{}`), fine; but `sold_this_round` per player is not cleared by any action inside a round.
9. R10/A8 "while over the limit and able to sell, no buy": checked in buy_share only; pass is not blocked (see round_manager gaps).
10. Selling does not check `player.loans` ordering vs repay (4.3.2 "after their sell shares step"): no repay action exists.
11. Treasury shares sold at `price` go to the company treasury; no graph rule about the bank pool shares when `bank.cash` is negative.
