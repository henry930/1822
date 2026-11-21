# COMMON conventions (all eight coders)

Read this file, BINDING.md and your own `<module>.md`. Do not read the graph (you do not have it), and do not read
anything outside `/home/claude/sandbox_g`.

## 1. Environment and layout
- Python >= 3.11. Run everything from `/home/claude/sandbox_g/backend` with `PYTHONPATH=.`
  (example: `cd /home/claude/sandbox_g/backend && PYTHONPATH=. python3 -c "import app.engine.actions"`).
- Money is integer pounds (no floats, no `/`; use `//`). Units are 10% of a company (see BINDING 1.3).
- Read-only inputs inside the sandbox: `RULES.md`, `RULINGS.md`, `backend/app/**` (given code), `contract/*.md`.
- You write ONLY your own file `/home/claude/sandbox_g/backend/app/engine/<module>.py`
  (`shares`, `certificates`, `company_formation`, `bidding`, `turn_order`, `trains`, `scoring`, `round_manager`).
  Never edit models.py, setup.py, stock_positions.py, actions.py, operating.py, main.py, rooms.py, db.py, board.py,
  routes.py, network.py, hex_grid.py or anything under app/data. If something in them blocks you, report it
  as a "contract problem"; do not work around it by editing.
- Scratch tests only under `/home/claude/sandbox_g/my_tests/<module>_*` (for example `my_tests/shares_basic.py`).
  There are no official tests; do not search for any. Tests you write are for your own checking.

## 2. Code conventions
- `from __future__ import annotations`, type hints, no third-party imports, no I/O, no randomness, no global mutable state.
- Mutate the passed `GameState` in place and return `None` unless the contract says otherwise.
- Validate ALL preconditions before the first mutation of a function (a rejected call must leave the state unchanged).
  Exception: the multi-bid loop in `actions._apply_bid` is outside your control (see bidding.md gap).
- Exceptions: each module that the given code imports an exception class from defines exactly that class name
  (`ShareError`, `ConcessionError`, `BidError`, `TrainError`), as `class X(Exception)`. Message format
  `"<ERR_CODE>: <human readable text>"` where `ERR_CODE` is the code named in the contract (for example
  `"ERR_POOL_FULL: ..."`). Messages are shown to users (actions.py wraps them in ActionError). Modules without a
  given exception class use the class named in their contract (`CertificateError`, `MarketError`, `RoundError`).
- Do not catch exceptions raised by other modules unless the contract says so.
- Import layering (to avoid circular imports; lower may not import higher at module top level):
  1. `turn_order` (market)  2. `certificates`  3. `scoring`  4. `trains`  5. `shares`, `company_formation`
  6. `bidding`  7. `round_manager`.
  Cross-file calls that go "up" the list are written as imports INSIDE the function body (lazy imports). The contract of
  each module lists which ones (marked `LAZY`). Imports of given modules (`models`, `stock_positions`, `app.data.*`)
  are always allowed at top level. Never import `actions` from the new modules (actions imports you).
- Public names: keep every name in the "External API" list of BINDING.md Part C exactly (spelling, parameter order).
  Extra helpers must start with `_` unless BINDING lists them.
- Use the helper owners in BINDING Part B (do not re-implement a helper that another file owns; import it).
- Do not add game behaviour that is not in your contract. If you believe the contract is wrong, silent or
  contradictory, implement the most literal reading, record it as a numbered ambiguity in your report, and continue.
  Where a contract line is marked `INTERIM` the line is a placeholder decided by the contract author because the
  rulebook-derived graph is silent; implement it exactly and flag it in the report.

## 3. Final report format (reply in this order, nothing else)
1. **Implemented**: file path, list of public functions/classes implemented (one line each).
2. **Numbered ambiguities**: `A1. ...` each with the choice you made and the contract line it concerns.
3. **Contract problems**: places where the contract contradicts the given code, models, data tables or itself,
   or where something cannot be implemented as written (with file and line of the given code).
4. **Integration check** (only if all eight files exist when you finish; otherwise say "not run, files missing: ...").
   Run from `backend/` with `PYTHONPATH=.` a script (kept under `my_tests/<module>_integration.py`) that:
   `s = new_game("g", ["a","b","c","d"], seed=1)`; then drives `actions.apply_action(state, player_id, action)` with
   the action dict formats used in `actions.py` (`bid` with `bids=[{"kind","box_index","amount"}]`, `buy_share`,
   `sell_shares`, `convert_concession`, `pass`) through: three players bidding on items, all four passing until
   the stock round resolves; check no exception is raised, cash/bank totals are conserved
   (`sum(player cash) + bank.cash + sum(company treasury)` changes only as the contract says), and that the next
   stock round or operating round starts. Report what passed and what raised.
