# Contract: `backend/app/engine/company_formation.py`  (graph: `act.convert_concession` of `comp.share_trading`; `act.float_minors` + 3 derived of `comp.sr_resolution`)

Read COMMON.md and BINDING.md first (traps T1, T4, T5, T15, T16; A.1 rows for concessions, director, treasury, major status, minor director, pending floats).
Layer 5. Top-level imports allowed: `models`, `certificates` (`cert_units`, `must_sell`), `turn_order` (`place_start_token`), `scoring` (`check_game_end_triggers`),
`app.data.major_companies` (`LNWR_ABBR`). No lazy imports. Exception: `class ConcessionError(Exception)`.

Given caller (exact), actions._apply_convert_concession:
`convert_concession(state, player_id, action["abbr"], action["start_price"])`; actions checks turn/round type before; afterwards sets `consecutive_passes = 0`,
`any_sale_this_stock_round = True`, `advance_stock_player`. The graph's `turn.stage/c_used/acted` are vacuous (BINDING C.5).

---------------------------------------------------------------------------------------------------------------------
## 1. `convert_concession(state, player_id, abbr, start_price)`   (`act.convert_concession`; 1.6.4, 2.2.3, 2.2.6, 3.3.2, 3.4.1, 4.1.4, 4.3.1, 4.6.1-4.6.3, 4.7.1-4.7.6, 4.9.1, R4, R6, R10, 10.1.1)
Convert a held concession into the director's certificate, set the start price and float the major company (phases 2-4).
Let `p = state.players[player_id]`, `major = state.majors[abbr]` (`abbr` not a key -> `ERR_NOT_HELD`), `cu = cert_units(abbr)` (LNWR 1, else 2).

Preconditions (check all before any mutation), graph error codes:
1. [4.6.2, 2.2.6] `2 <= state.phase <= 4` (no majors in phase 1; concessions removed at phase 5). Else `ERR_PHASE`.
2. [4.7.5] `abbr in p.concessions`. Else `ERR_NOT_HELD`.
3. [3.4.1] `major_status[c] = unstarted` (`not major.floated`). Else `ERR_ALREADY_STARTED`.
4. [4.3.1] `p.loans == 0`. Else `ERR_LOANS`.
5. [R10, A8] `not certificates.must_sell(state, player_id)`. Else `ERR_MUST_SELL`.
6. [1.6.4] `start_price in {60, 70, 80, 90, 100}` (50 is for minors only). Else `ERR_BAD_START_PRICE`.
7. [4.7.3] non-LNWR: `p.cash >= 2 * start_price - 100`. Else `ERR_INSUFFICIENT_CASH`. [R4] LNWR: the player pays nothing (no cash check).
(`ERR_C_ALREADY_USED` vacuous.)

Effects, in this order:
1. [4.7.2] remove `abbr` from `p.concessions`; `director_holder[c] = player` -> `major.director_player_id = player_id`. (Binding: also `major.concession_holder_player_id = None`, `major.concession_converted = True`.)
2. [4.7.2] `turn_order.place_start_token(state, abbr, start_price, "major")` (underneath all tokens already in that cell).
3. Money:
   - [4.7.3] non-LNWR: `state.bank.cash -= 100; p.cash -= (2 * start_price - 100); major.treasury = 2 * start_price`.
   - [4.7.4, R4] LNWR: `state.bank.cash -= start_price; major.treasury = start_price`; the player pays nothing; the director's certificate is 1 unit.
4. [3.3.2] `treasury_shares[c] = 8` (LNWR 9) -> `major.shares_in_treasury`; `pool_shares[c] = 0` -> `major.shares_in_bank_pool = 0`;
   `ordinary_certs[player,c]` unchanged (0): the holder's units are the director's certificate only -> `p.shares[abbr] = p.shares.get(abbr, 0) + cu` (T1; the company is unstarted so the value was 0).
5. [4.7.6] `major_status[c] = floated` -> `major.floated = True` (operates in the next OR); `has_completed_or[c] = false` -> `major.has_operated = False`.
6. [R6] `state.any_sale_this_stock_round = True`.
7. [10.1.1] `scoring.check_game_end_triggers(state, "after_bank_payment")`.
Calls (graph edges): `place_start_token`, `check_game_end_triggers`, `must_sell`, `cert_units`.

---------------------------------------------------------------------------------------------------------------------
## 2. Minor flotation (called by `bidding.resolve_stock_round` step 2, after `resolve_bids`)

Pending record (BINDING A.1 `st.pending_minor_floats`): `tuple[int, int, int, str]` = `(minor_number, bid, box_index, buyer_player_id)`; `box_index` is the 0-based
index of the box the minor sat in (graph "box number" = index + 1).

### `minor_start_price(phase, bid) -> int`   (`drv.minor_start_price`; 4.11.4, R2, 2.2.3, 2.2.6)
phase 1: `50`. phase >= 2: `max{v in {50,60,70,80,90,100} : v <= floor(bid/2)}`, minimum 50, maximum 100.
(Examples from the rulebook: bid 100..115 -> 50; 120..135 -> 60; 200+ -> 100.)

### `minor_start_treasury(phase, bid, price) -> int`   (`drv.minor_start_treasury`; 4.11.4, R3)
phase 1: `100`; phase 2: `2 * price`; phase >= 3: `bid`.

### `minor_float_order(pending) -> list`   (`drv.minor_float_order`; 4.11.3)
Sort by bid descending; tie -> lower box number (lower `box_index`). Returns the sorted list of pending tuples.

### `float_minors(state, pending)`   (`act.float_minors`; 3.2.2, 4.11.3, 4.11.4, 4.11.5, R3, 10.1.1)
Start each purchased minor. The buyer has ALREADY paid the full bid to the bank in `resolve_bids` (R3). The phase used is `state.phase` as it is NOW
(before this round's train exports; A19).
Precondition: flotation uses the phase at resolution time, before the round's exports [4.11.4].
Effects:
1. [4.11.3] for each `(n, bid, box_index, buyer)` in `minor_float_order(pending)`: `price = minor_start_price(state.phase, bid)`; `treasury = minor_start_treasury(state.phase, bid, price)`.
2. [4.11.5] `turn_order.place_start_token(state, f"M{n}", price, "minor")`.
3. [R3] `state.bank.cash -= treasury`; `company_cash[minor] = treasury` -> `state.minors[f"M{n}"].treasury = treasury`.
   Binding: also `minor.floated = True`, `minor.share_price = price` (display mirror, T15). `minor.director_player_id` was already set by `bidding.vacate_box_item` (award); do not change it.
4. [10.1.1] after the loop: `scoring.check_game_end_triggers(state, "after_bank_payment")` (once; the graph lists it as one effect).
Calls: `minor_float_order`, `minor_start_price`, `minor_start_treasury`, `place_start_token`, `check_game_end_triggers`.

---------------------------------------------------------------------------------------------------------------------
## Cross-module obligations
- `bidding.resolve_bids` must have (a) charged the buyer the full bid (`player.cash -= bid; state.bank.cash += bid`), (b) set `minors["M<n>"].director_player_id = buyer` via `vacate_box_item` BEFORE `float_minors` runs; it returns the pending list.
- Concession holder of a player is `Player.concessions` (list of abbr); bidding.vacate_box_item appends, this file removes (and clears at phase 5 in bidding.clear_concession_boxes).
- `has_operated` is set True later by `round_manager.advance_company`.

## Graph gaps (do not decide; report)
1. No certificate-limit check on conversion (a concession counts 1, the director's certificate counts 1: count unchanged); the graph is silent on whether the limit could block it.
2. A player who has a leading bid or must_sell: only `must_sell` blocks (R10, A8); leading bids are not mentioned.
3. `float_minors` "[10.1.1] call check_game_end_triggers": once after the loop vs once per minor is not stated.
4. `minor_start_price` for phase >= 2 when `bid // 2 < 50` (cannot happen: bid >= 100) and for phase 1 the bid is ignored (R3).
5. The model keeps `MajorCompanyState.concession_holder_player_id` / `concession_converted` and `MinorCompanyState.share_price`; the graph has no state for them (binding mirrors them).
6. Phase 5+ minor float: graph uses the "phase >= 3" row (bid as treasury) for all later phases; acquisition from boxes by majors (phase 5+) is out of scope.
7. The unused case "abbr is not LNWR but `start_price` allows `2*start_price - 100` > cash after the bid payments": covered by ERR_INSUFFICIENT_CASH; the committed money of leading bids is not considered (A7).
8. Whether the converting player's `sold_this_round` must be updated: graph says nothing.
