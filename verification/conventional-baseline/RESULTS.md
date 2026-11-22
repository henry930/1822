# Conventional first-generation baseline (DeepSeek V4 Flash, single run, temperature 0, reasoning low)
Same 8 modules, same given code, same 116 rule tests, same model as graph-first-v2-deepseek. The coder gets the FULL rulebook text (~59k prompt tokens/call incl. given code) + RULINGS.md + given code + a one-line description of each module; no graph, no contracts.
- A: rulebook only. B: + interface list (names/signatures/aliases) taken from our graph's api nodes (so B benefits from our graph).
- Repair: same smoke-traceback loop as ours (no tests), up to 5 rounds, current code of implicated modules + traceback (no contracts).
- "adapted": the same test-facing alias lines applied as for our run, only where the obvious target exists.

| | gen in/out tokens | gen cost | repair calls, in/out tokens | repair cost | rule tests (strict) | rule tests (alias-adapted) |
|---|---|---|---|---|---|---|
| Conventional A (rulebook only) | 471,942 / 85,465 (bidding hit the 40k cap) | $0.074 | 2, 22,070 / 19,286 | $0.012 | 0/116 (import errors) | 0/116 (import errors) |
| Conventional B (+ interface list) | 492,838 / 50,316 | $0.043 | 5, 117,012 / 34,205 | $0.015 | 0/116 (import errors) | 87/116 |
| Graph-first v2 (ours, from earlier run) | 394,260 / 48,456 (excl. 2 wasted runs) | ~$0.077 incl. 2 wasted runs | 3 calls | ~$0.025 | 94/116 raw; 103/116 after repair | (aliases in contract) |
Reading: a conventional coder without interface names cannot satisfy the tests' import names; with the interface list it reaches 87/116 after repair vs 103/116 for ours. Generation tokens and dollars are similar (ours ~16-20% fewer input tokens), so first generation is NOT clearly cheaper with graph-first; the benefit seen is quality and a contract the coder can rely on. NOT counted for ours: the tokens spent building the graph (done earlier with a cloud model, not logged). Interface list in B is derived from our graph. n=1.
