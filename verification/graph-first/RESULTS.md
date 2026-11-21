# Graph-first run (rulebook -> graph -> contract -> code)

Pipeline: (1) agent A saw only the rulebook excerpt + owner rulings and built `graph/graph.json` (284 nodes, 930 edges, 8 components; checker passes). (2) agent B derived BINDING.md + 8 module contracts + GAPS.md from the graph and the given skeleton (no tests, no original modules). (3) 8 coder agents in parallel wrote `generated/engine/*.py` (1071 lines) from contract only (no graph, no rulebook, no tests, no original code).
Timing: graph ~14 min, contract ~14 min, coding ~1-2 min per module in parallel.

## Results (same 116 rule tests + 164 legacy tests)
- As delivered: test files could not even import (API names the given code does not use differ: `certificate_limit` vs `cert_limit`, `_face_value`, `compute_operating_order`, `final_wealth`, `upgrade_l_to_2`...).
- With a thin name-alias adapter: 86/116 passed. Extra failures were interface defaults/protocol: `buy_share` without default `source`; source named "pool" instead of "bank"; `resolve_stock_round` refuses unless all players passed (ERR_NOT_OVER); trains refuse unfloated companies.
- With the diagnostic adapter (defaults, bank->pool alias, bypass of sr_over, no floated guard): 105/116 passed, 11 failed: 7 train API (L/2 side purchase "2", rust, order, limit discard: trains were outside the graph), 3.1.2 private revenue (not in graph), 4.1.2 stock round starts with priority holder (represented as player_order[0]), 5.12.13 (given code). Legacy tests: 138 pass / 18 fail (excluding test_trains which cannot import `upgrade_l_to_2`; incl. ~9 sandbox-artifact).
- Stock-round-core rules (4.x) pass except the 4.1.2 representation gap.

## What the graph did and did not do
- Graph found ambiguities/conflicts upfront (A1-A40, incl. R6 vs 10.1.1) before any code was written.
- 42 contract-level gaps (contract/GAPS.md) + 25 binding guesses: the graph does not carry interface names, defaults, error codes, representation (units, 0-based boxes), nor scope outside rules (operating round, trains). 
- Cross-module flag coupling (the v1 failure of earlier runs) did not recur: the graph's cross-component edges listed them.
- Caveat: the graph builder and contract writer are the same model family as coders; one run each; graph agent saw rulings I wrote after seeing earlier failures.
