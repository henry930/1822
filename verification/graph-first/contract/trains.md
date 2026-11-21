# Contract: `backend/app/engine/trains.py`  (graph component `comp.phase_trains` + the given-code function `buy_train_from_bank`)

Read COMMON.md and BINDING.md first (trap T12 for the train pool, A.1 rows `st.phase`, `st.train_deck`, `st.phase_events`).
Layer 4. Top-level imports allowed: `models`, `app.data.trains` (`TRAIN_TYPES_BY_CODE`), `app.data.phases` (`PHASES_BY_NUMBER`).
LAZY: `from .bidding import clear_concession_boxes` inside `phase_check`. Do not import scoring/shares.

Given callers (exact):
- `actions._apply_operate`: `buy_train_from_bank(state, company_id, kind, buy_train)` with `kind` `"major"|"minor"` and `buy_train` a code string; catches `TrainError`.
- `operating.first_turn_housekeeping`: `buy_train_from_bank(state, company_id, "minor", "L")` inside `try/except TrainError: pass`.
Exception: `class TrainError(Exception)`.

Constants (BINDING A.3):
`TRAIN_PHASE = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "E": 7}` (`const.phase_table`; `"L"` absent: an L-train never triggers a phase);
rust: `PHASES_BY_NUMBER[n].trains_rusted` (`const.rust_table`: phase 3 "L", 4 "2", 6 "3", 7 "4").
Deck = `state.bank.train_pool` (BINDING T12): scan order `("L","2","3","4","5","6","7","E")`.

---------------------------------------------------------------------------------------------------------------------
## 1. Derived functions

### `phase_of_train(code) -> int | None`   (`drv.phase_of_train`; 2.2.3-2.2.8, `const.phase_table`)
`TRAIN_PHASE.get(code)`; `None` for `"L"` (L/2 exported or bought as a 2-train gives 2: the caller passes `"2"`).

### `front_train(state) -> str | None`   (`drv.front_train`; R7)
`train_deck[0]` or null if empty = the first code in the scan order whose `state.bank.train_pool[code] > 0`, else `None`.

---------------------------------------------------------------------------------------------------------------------
## 2. Actions

### `phase_check(state, code)`   (`act.phase_check`; 2.1.1, 2.1.2-2.1.5, 2.2.8, R9)
Precondition [2.1.1]: train type in `{2,3,4,5,6,7,E}`; an L-train never triggers a phase (call with `"L"`: do nothing).
Effects:
1. [2.1.1] `new = phase_of_train(code)`.
2. if `new > state.phase`: `old = state.phase; state.phase = new`; append the phase event to `state.log` (BINDING `st.phase_events`):
   `f"PHASE_EVENT from={old} to={new} rusted={rusted or '-'} or_per_sr={n}"` with `rusted = PHASES_BY_NUMBER[new].trains_rusted`,
   `n = PHASES_BY_NUMBER[new].operating_rounds_per_stock_round` [2.1.2-2.1.5: rusting, train-limit discard and operating-round count are
   consumed by the operating-round module, which does not exist in given code; this file records the event only].
3. [2.2.8, R9] if `new >= 5`: LAZY call `bidding.clear_concession_boxes(state)` (graph edge phase_check -> clear_concession_boxes, "called only when phase just reached >= 5").
   Implement as: call it whenever `new > old` and `new >= 5` (i.e. when the phase has just been raised to 5 or more).
Errors: none for legal input.

### `export_train(state, mode)`   (`act.export_train`; 4.11.6, 4.11.7, R7)
`mode` in `{"L_only", "next_with_phase"}`. Precondition [4.11.6]: deck not empty (else no action).
Effects:
- `mode == "L_only"` [4.11.6, R7]: if the front train is L/2 (`front_train(state) in ("L","2")`): pop it (decrement that code in `train_pool`);
  it counts as an L-train: NO phase check. If no L/2 remains (front is another type or deck empty): no action.
- `mode == "next_with_phase"` [4.11.7, R7]: pop the front train (L/2 while any remain, then 3, 4, ...; decrement its code in `train_pool`);
  `effective = "2" if popped code in ("L","2") else popped code`; call `phase_check(state, effective)`.
Exported trains leave the game (no other state is written; they are not added to `bank.discarded_trains`).
Called by `bidding.unsold_minor_exports` (`"L_only"`) and `bidding.remove_box1_minor_and_export` (`"next_with_phase"`).

### `buy_train_from_bank(state, company_id, kind, code)`   (REQUIRED BY GIVEN CODE; NOT IN THE GRAPH - INTERIM)
The graph has no node for train purchase (operating rounds are out of scope; the graph's `phase` text says only that the phase advances when the
first train of a type is "bought or exported"). Minimal INTERIM behaviour, derived only from the data tables and from 2.1.1:
1. Preconditions (each failure -> `TrainError("ERR_TRAIN_...: ...")`): `kind` is `"major"` or `"minor"` and `company_id` is a key of `state.majors`/`state.minors`
   (matching kind) and the company is floated; `code in TRAIN_TYPES_BY_CODE`; `state.bank.train_pool.get(code, 0) > 0`; company `treasury >= cost` (`TRAIN_TYPES_BY_CODE[code].cost`);
   `len(company.trains) < limit` where `limit = PHASES_BY_NUMBER[state.phase].minor_train_limit` (minor) or `.major_train_limit` (major).
2. Effects: `company.treasury -= cost; state.bank.cash += cost; state.bank.train_pool[code] -= 1; company.trains.append(code)`; then `phase_check(state, code)` [2.1.1: first train of a type bought].
Nothing else (no forced purchase, no emergency money, no buying from other companies, no rusting of company trains).

---------------------------------------------------------------------------------------------------------------------
## 3. Cross-module obligations
- `phase_check` is the ONLY writer of `state.phase` (besides debug code in main.py). It triggers `bidding.clear_concession_boxes` at phase >= 5.
- `export_train` is called in `resolve_stock_round` steps 3 and 4 (so after minors were floated at the phase in force at resolution, A19).
- `phase_check` must be callable with any of the codes `"2","3","4","5","6","7","E"` and with `"L"` (no-op).

## Graph gaps (do not decide; report)
1. No graph node for buying trains: `buy_train_from_bank` (required by given code) is entirely unspecified; the contract above is INTERIM. Buying order (only front type?), cost payment target (bank), "must own a train", forced purchase, L->2 upgrade and 2-train purchase while `train_pool["2"] == 0` are not covered. How a flipped L/2 card is counted in the deck is not defined (A17 says an L/2 train counts as a 2-train for the phase check only).
2. `phase_check`: "if new > phase: ... ; if new >= 5 trigger clear_concession_boxes": whether the clearing is inside or outside the `new > phase` branch is ambiguous (idempotent).
3. Phase skipping (A18): `rusted = rust_table[new]` only lists the new phase's row; rust events of skipped phases (for example jumping from 2 to 4 skips the phase-3 rusting of L) are not specified.
4. The phase event queue has no field (`st.phase_events`); log-line format is a binding choice. The consumers (rusting 2.1.3, train-limit discard 2.1.4/2.1.5, "two ORs only after the following stock round" 2.1.2) are not in the graph and not in given code.
5. `export_train` in `next_with_phase` mode for 7/E and for a deck holding both "7" and "E" counts: effective type 7 either way (phase table), not stated for E explicitly in the export action.
6. The effective type when the popped card is a flipped "2" (count in `"2"`) versus "L": both are "L/2" per graph; counting convention is binding T12 [GUESS].
7. Whether an exported train that triggers a phase 5+ change during a stock round clears concessions held by players immediately (yes by R9) while the same round's already-paid concessions are inside players' hands: not discussed.
