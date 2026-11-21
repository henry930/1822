# Graph-first v2 with an open-weight model (DeepSeek V4 Flash via OpenRouter) as the "local" coder

Same v2 contracts (generated from the graph) as the cloud-agent run; the model gets only COMMON + BINDING + its module contract + the given skeleton code (no tests, no rulebook, no graph). One API call per module, parallel.
- Raw single-shot (reasoning medium): 6/8 modules produced; 2 (company_formation, scoring) burned the 60k completion budget in reasoning with empty output; re-run with reasoning low -> both fine (~3-4k tokens each).
- Cost: gen ~$0.075 + redo ~$0.0015; tokens in ~480k out ~170k (incl. the 2 wasted runs). Total incl. repair < $0.11. 2073+ lines.
- Rule tests (116, name aliases only): raw 94 passed / 22 failed. Failures: train export mode string mismatch between bidding and trains (cross-module constant not pinned), turn_order raising ERR_NO_TOKEN for floated company without token, start_stock_round priority representation, reorder_players_by_cash returning None, 5.12.13 (given code).
- Repair loop WITHOUT tests: only the traceback of a 3-scenario smoke run (new_game; bids+passes+resolve; convert+buy; passes) is fed back, plus affected contracts and current code; 3 calls (~$0.025). First attempt failed because the model tried to edit the given models.py; after adding "given code cannot be changed" the smoke passed after 3 patches (bidding x2, trains).
- After repair: rule tests 103 passed / 13 failed; legacy tests 137 passed / 19 failed (test_trains not importable).
  Remaining: 8 x ERR_NO_TOKEN (contract ambiguity, cloud coders chose to skip), 5.12.13 (given), 4 representation/return-type items (start_stock_round priority holder, reorder return value).
- Reference: cloud-model agents with the same contracts: 113 / 3 failed (no repair needed).

## Reading
An open-weight model can write the modules from the contract alone for ~$0.10, and ~89% of rule tests pass after a no-test repair loop; the gap to the cloud result comes from cross-module constants and exceptional-case conventions the contract does not pin. No source code of the (hypothetical) project was sent: inputs were contracts + skeleton. Caveats: single run, temperature 0, 'skeleton' (models/setup/actions) was sent as given code - in a real private setting that is the part that would stay local or be abstracted.
