# Contract: `backend/app/engine/bidding.py`  (graph components `comp.bidding`, `comp.bid_boxes`, and the resolution orchestration of `comp.sr_resolution`)

Read COMMON.md and BINDING.md first (traps T3, T4, T5, T11; A.1 rows `st.box_contents`, `st.bids`, stacks, `st.items_with_bids`, `st.pending_minor_floats`, `st.removed_items`).
Layer 6. Top-level imports allowed: `models` (`BidBoxItem`, `RoundType`), `app.data.setup` (`SETUP_BY_PLAYER_COUNT`), `certificates` (`must_sell`, `cert_count`, `cert_limit`),
`turn_order` (`raise_sold_out_prices`, `reorder_players_by_cash`), `scoring` (`check_game_end_triggers`), `trains` (`export_train`), `shares` (`charge_interest`),
`company_formation` (`float_minors`). LAZY: `from .round_manager import sr_over` inside `resolve_stock_round`. Your module is imported lazily by `certificates.cert_count`
(for `items_led`) and by `trains.phase_check` (for `clear_concession_boxes`), so it must not do anything at import time except define names.
Exception: `class BidError(Exception)`. Constants: `FACE_VALUES = {"concession": 100, "minor": 100, "private": 0}`, `BID_MULTIPLE = 5`, `MAX_BIDS_PER_TURN = 3`.
An "item" is the `BidBoxItem` object in a box; its identity is `(kind, box_index)` (box_index 0-based; graph box number = index+1). Kinds: `"concession"`, `"minor"`, `"private"`.
Box lists: `state.concession_bid_boxes` (len 3), `state.minor_bid_boxes` (len 4), `state.private_bid_boxes` (len 3), elements `BidBoxItem | None`; lists keep their length.

Given caller (exact), actions._apply_bid, for each entry `b` of `action["bids"]` (max 3 entries):
`place_or_move_bid(state, player_id, b["kind"], b["box_index"], b["amount"])`; afterwards actions does `state.bids_this_turn += 1` itself.
Therefore `place_or_move_bid` only READS `state.bids_this_turn` and never changes it. `BidError` is wrapped by actions into `ActionError`.
actions.py also calls (not you): `advance_stock_player(state)` after the bids, and `end_stock_round(state)` which calls your `resolve_stock_round(state)`.

---------------------------------------------------------------------------------------------------------------------
## 1. Derived functions (comp.bidding)

- `face_value(kind) -> int`   (`drv.face_value`; 3.4.2, 3.1.3, R1): `FACE_VALUES[kind]` (concession 100, minor 100, private 0).
- `highest_bid(item) -> int | None`   (`drv.highest_bid`; 4.10.7): `max(item.bids.values())` if `item.bids` (dict non-empty) else `None`. A bid of 0 is a bid (T11).
- `highest_bidder(item) -> str | None`   (`drv.highest_bidder`; 4.10.7): argmax of `item.bids` (unique because every new bid must be higher); `None` if no bids.
- `committed_money(state, pid) -> int`   (`drv.committed_money`; 4.10.7): sum of `highest_bid(item)` over all items in all 10 boxes with `highest_bidder(item) == pid`; outbid items do not count.
- `items_led(state, pid) -> int`   (`drv.items_led`; 4.2.5): number of items in all boxes with `highest_bidder(item) == pid`. (Used by `certificates.cert_count`.)
- `tokens_total(state) -> int`   (`drv.tokens_total`; 4.10.3, 1.7.2, `const.bidding_tokens`): `SETUP_BY_PLAYER_COUNT[len(state.player_order)].bidding_tokens`.
- `tokens_used(state, pid) -> int`   (`drv.tokens_used`; 4.10.10): number of items in all boxes with `pid in item.bids` (tokens stay until resolution, led or outbid).
- `min_legal_bid(item) -> int`   (`drv.min_legal_bid`; 4.10.6, 4.10.7, R1): `face_value(item.kind)` if `item.bids` is empty, else `highest_bid(item) + 5`.
- `bid_amount_valid(state, pid, item, amount) -> bool`   (`drv.bid_amount_valid`; 4.10.6, 4.10.7, 4.10.9):
  `amount % 5 == 0 and amount >= min_legal_bid(item) and committed_money(p) + amount <= player_cash[p]` (the player does not currently lead the item, so it is not double counted); no upper bound.
- `item_resolution_order(state) -> list[tuple[str,int]]`   (`drv.item_resolution_order`; 4.11.2, A16): `(kind, box_index)` of all items with >= 1 bid, sorted by
  (highest bid descending, box number ascending [= box_index ascending], kind order minor < concession < private).

## 2. Actions of comp.bidding

### `place_or_move_bid(state, player_id, kind, box_index, amount)`   (`act.place_bid` + `act.move_bid`; 4.1.4, 4.2.5, 4.3.1, 4.10.3-4.10.8, 4.10.10, 3.1.4, R9, R10)
One function for both graph actions: it is a MOVE if `player_id in item.bids`, otherwise a PLACE.
Preconditions (check all before mutating); codes -> `BidError`:
1. [R9, 4.10.2] `kind` is one of the three kinds, `0 <= box_index < len(boxes[kind])`, the box holds an item (not `None`), and concession items only while `state.phase < 5`. Else `ERR_ITEM_NOT_IN_BOX`.
2. [4.10.5] `state.bids_this_turn < 3` (read only). Else `ERR_TOO_MANY_BIDS`.
3. [4.3.1] `state.players[p].loans == 0`. Else `ERR_LOANS`.
4. [R10] `not certificates.must_sell(state, p)`. Else `ERR_MUST_SELL`.
5. [4.10.8, 4.2.5] `certificates.cert_count(state, p) < certificates.cert_limit(state)` (leading bids count; applies to privates too; "yellow" exemption lives in cert_count). Else `ERR_CERT_LIMIT`.
6. [4.10.6] `bid_amount_valid(state, p, item, amount)` (amount must be an `int`, not `bool`). Else `ERR_BAD_AMOUNT`.
7. PLACE ([4.10.3] and [4.10.4]): `tokens_used(p) < tokens_total`. Else `ERR_NO_TOKENS`. (`ERR_ALREADY_HAS_TOKEN` of the graph's place_bid is unreachable here: a player with a token on the item takes the MOVE branch.)
8. MOVE ([4.10.4], [4.10.10]): the player is NOT the highest bidder (another player has a higher bid). Else `ERR_NOT_OUTBID`. (`ERR_NO_TOKEN_ON_ITEM` unreachable; a token cannot be withdrawn or moved to another item.)
(`ERR_C_ALREADY_USED`, turn stage: vacuous, BINDING C.5.)
Effects: [4.10.4] `item.bids[player_id] = amount` (for a move the token moves: the old amount is replaced). Nothing else: `turn.bids_made`, `c_used`, `acted` are handled/vacuous (actions increments `bids_this_turn`).
[4.2.5] the player's `items_led` rises automatically through the formulas.
Calls (graph edges): `must_sell`, `cert_count`, `cert_limit`, `bid_amount_valid`, `tokens_used`, `tokens_total`, `highest_bidder`.

## 3. Actions of comp.bid_boxes

### `shift_boxes(state)`   (`act.shift_boxes`; 4.10.2, 4.11.8; `const.box_counts`)
For each kind separately: items in the boxes are moved to the lowest-numbered (lowest index) boxes keeping their relative order; the list keeps its length (padded with `None`).

### `refill_boxes(state)`   (`act.refill_boxes`; 1.7.7, 4.1.1, 4.10.2, 4.11.8, R9)
1. [4.10.2] `shift_boxes(state)`.
2. [1.7.7, 4.1.1] for kind in (minor, concession, private): for each empty box, lowest index first: pop the top (`stack.pop(0)`) of the kind's stack into a new `BidBoxItem(kind=kind, ref=<popped value>, bids={})`; stop when the stack is empty.
   Stacks: `state.minor_stack` (ints), `state.concession_stack` (abbr strings), `state.private_stack` (ints). T4.
3. [R9] when `state.phase >= 5` concession boxes stay empty and `concession_stack` stays empty: skip the concession kind (do not refill it).
Do not call `engine.setup._refill_bid_boxes` (it lacks rule R9); reimplement.

### `clear_concession_boxes(state)`   (`act.clear_concession_boxes`; 2.2.8, 3.4.5, R9)
Precondition: called only when the phase has just reached >= 5 (by `trains.phase_check`; not checked).
Effects: [R9] concession boxes emptied (`[None] * 3`); `concession_stack` emptied; all concessions added to `removed_items` (no field: nothing to write);
[R9, 3.4.5] `player.concessions = []` for every player (no refund; certificate counts drop). Binding: also set every `MajorCompanyState.concession_holder_player_id = None`.
Idempotent (may be called again).

### `vacate_box_item(state, kind, box_index, disposition, player_id=None)`   (`act.vacate_box_item`; 4.11.2)
`disposition` in `{"award", "remove"}`; `award` requires `player_id`.
Precondition: the box holds an item. Else `ERR_ITEM_NOT_IN_BOX`.
Effects: [4.11.2] `boxes[kind][box_index] = None` (no shifting here). award: concession -> `players[pid].concessions.append(ref)` (also `majors[ref].concession_holder_player_id = pid`);
private -> `players[pid].private_companies.append(ref)` (also `privates[ref].owner_player_id = pid`); minor -> `state.minors[f"M{ref}"].director_player_id = pid`.
remove: `removed_items += item`: minor -> `state.minors[f"M{ref}"].removed = True`; concession/private: nothing to store (BINDING A.1).

## 4. Actions of comp.sr_resolution that live here

### `resolve_bids(state) -> tuple[set[tuple[str,int]], list[tuple[int,int,int,str]]]`   (`act.resolve_bids`; 4.11.1, 4.11.2, 4.7.5, R3, R6, R8)
Award each item with bids to the highest bidder who can pay; remove tokens. Returns `(items_with_bids, pending_minor_floats)` (BINDING A.1; these two graph states are returned instead of stored).
Effects, in this order:
1. `items_with_bids` = set of `(kind, box_index)` for every item with >= 1 token (snapshot BEFORE clearing).
2. `for item in item_resolution_order(state)` (computed once, before any payment): iterate the item's bidders by amount descending; the first with `player.cash >= amount` wins [R8]:
   `player.cash -= amount; state.bank.cash += amount` [R3: the full bid is paid to the bank]; `vacate_box_item(state, kind, idx, "award", bidder)`;
   `state.any_sale_this_stock_round = True` [R6 provisional]; if the item is a minor append `(ref, amount, box_index, bidder)` to `pending_minor_floats`.
   [R8] if nobody can pay, the item stays in its box and still counts as having had a bid (it stays in `items_with_bids`).
   The certificate limit is NOT rechecked for the winner (A16).
3. [4.11.2] all bids cleared: `item.bids = {}` for every item still in a box.
Calls: `vacate_box_item`, `item_resolution_order`.

### `unsold_minor_exports(state, items_with_bids)`   (`act.unsold_minor_exports`; 4.11.6)
Precondition: after `float_minors`.
Effects: [4.11.6] for each minor still in a minor box (indexes ascending) whose `("minor", box_index)` is not in `items_with_bids`: `trains.export_train(state, "L_only")`.

### `remove_box1_minor_and_export(state)`   (`act.remove_box1_minor_and_export`; 4.11.7, A15)
Precondition: minor box 1 (`minor_bid_boxes[0]`) still holds a minor after resolution (unsold; unpaid items count as unsold, A15). Otherwise do nothing.
Effects: [4.11.7] `vacate_box_item(state, "minor", 0, "remove")`; `trains.export_train(state, "next_with_phase")`.

### `resolve_stock_round(state)`   (`act.resolve_stock_round`; 4.11.1-4.11.10, 4.12, 10.1.1)
Precondition: `round_manager.sr_over(state)` (LAZY import; i.e. `consecutive_passes >= len(player_order)`). Else `BidError("ERR_NOT_OVER: ...")`.
Effects, in EXACTLY this order (graph order edges seq 1..8, then step 9):
1. `items_with_bids, pending = resolve_bids(state)`  [4.11.2]
2. `company_formation.float_minors(state, pending)`  [4.11.3-4.11.5]
3. `unsold_minor_exports(state, items_with_bids)`  [4.11.6]
4. `remove_box1_minor_and_export(state)`  [4.11.7]
5. `refill_boxes(state)`  [4.11.8, 4.10.2: shift then fill]
6. `shares.charge_interest(state)`  [4.11.10]
7. `turn_order.raise_sold_out_prices(state)`  [4.12]
8. `turn_order.reorder_players_by_cash(state)`  [4.11.9]
9. `scoring.check_game_end_triggers(state, "end_of_stock_round")`  [10.1.1]; `sr_status = finished` (not stored).
This function does not increment `stock_rounds_completed`, does not change `round_type`, does not reset per-round flags (round_manager does after it returns).

---------------------------------------------------------------------------------------------------------------------
## Cross-module obligations
- Writes: box lists, stacks, `BidBoxItem.bids`, `Player.concessions / private_companies / cash`, `state.bank.cash`, `MinorCompanyState.director_player_id / removed`, `state.any_sale_this_stock_round` (R6).
- `trains.phase_check` (reached via the exports in steps 3-4) lazily calls your `clear_concession_boxes`; it may therefore run in the middle of `resolve_stock_round` (step 3 or 4), emptying concession boxes before step 5.
- `certificates.cert_count` lazily calls your `items_led`.
- `bids_this_turn` is owned by actions.py/round_manager (T5).

## Graph gaps (do not decide; report)
1. Atomicity of a multi-bid action: `actions._apply_bid` loops `place_or_move_bid`; if bid 2 raises `BidError`, bid 1 stays applied and `bids_this_turn` was already incremented, and the turn does not advance. The graph does not say whether the 3 bids are one transaction.
2. A5 assumption (one token per player per item, leader cannot raise) is not in the rulebook; 4.10.4 says "moves ... only if another player has a higher bid".
3. Merged place/move: error codes `ERR_ALREADY_HAS_TOKEN`, `ERR_NO_TOKEN_ON_ITEM` of the graph cannot occur.
4. `ERR_BAD_AMOUNT` covers three conditions (not multiple of 5, below minimum, committed money exceeds cash); the graph gives no distinction.
5. Opening bid 0 for privates (A4) - stated by graph as owner to confirm.
6. `resolve_bids` "[R6] sale_happened = true" is marked provisional; R6 is an open conflict.
7. A15: an unpaid box-1 minor (R8 says it "counts as having had a bid") is still removed and exported by step 4; the graph asks the owner to decide.
8. `item_resolution_order` tie: graph orders equal highest bids by box number then kind; between kinds with equal box numbers `minor < concession < private` is an assumption (A16).
9. `resolve_bids` item order is computed once; if a player pays for an earlier item and can no longer pay a later one, reassignment follows the bidders list of that later item (A16).
10. Whether bidding on a concession whose major company is already started is allowed: not stated (concession boxes only contain unstarted companies by construction).
11. 4.10.9 "round the clock" chips: no state; amounts above 195 are plain ints (no data table use).
12. `refill_boxes` at phase >= 5 when the concession stack is non-empty: graph says boxes and stack "stay empty" (R9); `clear_concession_boxes` empties the stack, so the case should not arise.
13. What happens to `Player.concessions` of players for the concession awarded in the same resolution in which the phase reaches 5 (awarded in step 1, cleared in step 3/4): by R9 it vanishes; not stated explicitly.
14. `state.round_type` precondition (stock round only) for `place_or_move_bid` is enforced by actions.py, not graph.
