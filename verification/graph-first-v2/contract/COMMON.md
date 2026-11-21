# COMMON contract (read first)

Eight modules of the 1822 rules engine are missing and are written in parallel by eight coders: shares, certificates, company_formation, bidding, turn_order, trains, scoring, round_manager. Each coder works from this directory (contract/) and the given code in backend/app only. Per-module contracts (contract/<module>.md) are generated mechanically from the rule graph; BINDING.md holds the representation notes and the call matrix.

## Environment and conventions
- Python >= 3.11. Run everything from `/home/claude/sandbox_g2/backend/` with `PYTHONPATH=.` (example: `cd /home/claude/sandbox_g2/backend && PYTHONPATH=. python3 -c "from app.engine import shares"`).
- Money is integer pounds everywhere (no floats). Share units are integers of 10%.
- Modules live at `backend/app/engine/<module>.py` and are imported as `app.engine.<module>`.

## What you may read and write
- Read ONLY `/home/claude/sandbox_g2` (the contract/ directory and backend/app, including the given models, data tables, setup, actions, operating, stock_positions, main, rooms, db). Do not read anything else on the machine; no network, no git.
- Write ONLY your own module file `backend/app/engine/<your_module>.py`. Never edit given files or other coders' modules.
- Scratch tests go under `/home/claude/sandbox_g2/my_tests/<name>_*` (name = your module name).

## Hard requirements
1. Export EVERY api name and EVERY alias exactly as listed in your contract (functions, exception class, classes, constants). Aliases are the same callable under another name.
2. Keep exact call compatibility with the given code: given names, argument order, defaults and return types as in the contract signature; the given files (actions.py, setup.py, main.py, operating.py, stock_positions.py ...) call your functions and must keep working unchanged.
3. Exceptions: one exception class per module, derived directly from `Exception` (no shared base, no subclasses); message `"<ERR_CODE>: <text>"`; attribute `.code` = ERR_CODE (the string). Raise only the codes listed.
4. Atomicity: validate everything first (in the listed precedence order: the first failing `enforced` check raises); do not mutate state before the last check has passed.
5. Do not check what the contract says a function must NOT check (round type, active player etc. belong to actions.py).
6. Use the graph text of the contract verbatim; do not invent behaviour. Where the contract is ambiguous or contradictory, choose the most conservative reading, record it as an ambiguity in your report, and do not silently diverge.
7. Decisions marked INTERIM (needs_owner) are conservative defaults pending an owner ruling: follow them as written.
8. Import layering (lower number may be imported at module level by higher): 1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares, 5 company_formation, 6 bidding, 7 round_manager. A call to a higher layer must be a lazy import inside the function. Do not create import cycles.
9. Cross-module calls must go through the callee's public api names exactly as listed in the call matrix (BINDING.md section 2).

## Final report format (your last message)
1. Implemented summary (functions/constants/aliases, deviations if any).
2. Numbered ambiguities (each: what is unclear, what you chose).
3. Contract problems (contradictions, missing information, signatures that cannot work with given code).
4. Integration check: once all eight module files exist (poll the directory for up to about 3 minutes), run an integration check through `new_game` (setup) plus `actions.apply_action` (for example a few passes / bids / buys / sells in a stock round and the transition to an operating round) and report the outcome; if the other files do not appear within about 3 minutes, say so and report what you could test alone.

## Shared names
Exception classes: shares.ShareError, certificates.CertificateError, company_formation.ConcessionError, bidding.BidError, turn_order.MarketError, trains.TrainError, scoring.ScoringError, round_manager.RoundError.

## Names fixed by given code (never rename)
`scoring.check_game_end_triggers` -- called from: actions.apply_action, operating._move_price
`trains.TrainError` -- called from: actions._apply_operate, operating.first_turn_housekeeping
`trains.buy_train_from_bank` -- called from: actions._apply_operate, operating.first_turn_housekeeping
`shares.ShareError` -- called from: actions._apply_buy_share, actions._apply_sell_shares
`shares.sell_shares` -- called from: actions._apply_sell_shares
`shares.buy_share` -- called from: actions._apply_buy_share
`company_formation.ConcessionError` -- called from: actions._apply_convert_concession
`company_formation.convert_concession` -- called from: actions._apply_convert_concession
`bidding.BidError` -- called from: actions._apply_bid
`bidding.place_or_move_bid` -- called from: actions._apply_bid
`bidding.resolve_stock_round` -- called from: actions (imported, unused), round_manager.end_stock_round
`round_manager.start_stock_round` -- called from: main.debug_force_round
`round_manager.advance_stock_player` -- called from: actions._apply_bid, actions._apply_buy_share, actions._apply_sell_shares, actions._apply_convert_concession, actions._apply_pass
`round_manager.end_stock_round` -- called from: actions._apply_pass
`round_manager.active_company_id` -- called from: actions._apply_operate, actions._apply_pass
`round_manager.advance_company` -- called from: actions._apply_operate, actions._apply_pass

## Module summary (api count)
- shares: 9 apis (5 functions, 3 constants, 1 exception/class)
- certificates: 19 apis (14 functions, 3 constants, 2 exception/class)
- company_formation: 8 apis (5 functions, 2 constants, 1 exception/class)
- bidding: 25 apis (20 functions, 4 constants, 1 exception/class)
- turn_order: 15 apis (14 functions, 0 constants, 1 exception/class)
- trains: 20 apis (13 functions, 6 constants, 1 exception/class)
- scoring: 15 apis (7 functions, 7 constants, 1 exception/class)
- round_manager: 13 apis (12 functions, 0 constants, 1 exception/class)
