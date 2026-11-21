# GRAPH_NOTES - 1822 stock-round knowledge graph

Files: `graph.json` (graph), `build_graph.py` (generator; the graph data lives there), `check_graph.py` (verifier; run `python3 check_graph.py`, exit 1 on violations).
Inputs used: only `/home/claude/graphrun/in/RULES.md` and `RULINGS.md`.

## 1. Schema summary

Node ids: `rule.<n.n.n>`, `ruling.R<k>`, `ent.*`, `st.*` (state), `act.*`, `drv.*` (derived), `comp.*`, `const.*`.
Rule/ruling nodes: `text` = source id ("4.4.3", "R3"); the paraphrase is in `attrs.summary`.

- Action attrs: `signature{params,returns}`, `preconditions[{check, rule}]` (each check cites the demanding rule/ruling), `effects[]` (ordered, rule ids in brackets), `errors[]`, `component`, `notes`.
- Derived attrs: `signature`, `formula` (exact, with rule ids), `component`.
- State attrs: `type`, `scope`, `unit`, `owner_component`, `part_of_entity`, `reader_components`, `writer_components`, `shared`, optional `external` + `external_note`.
- Constant attrs: the tables; `missing=true` where the input does not contain the data.
- Edge types: constrains (rule/ruling -> action/derived/state/constant; generated from every rule id cited in a precondition/effect/formula, plus hand-curated links), overrides (ruling -> rule, meaning "overrides or completes"), refers (rule -> rule), reads/writes/calls/triggers (carry `cross_component`, verified by the checker against the owner component of the state / member_of of the callee), member_of, uses_constant, part_of, order (carries `seq`: inside `resolve_stock_round` seq n runs before seq n+1; also sell(1) -> repay(2) -> C action for turn order).

Conventions that make contracts precise:
- Unit = 10% of a company. A director's certificate = `cert_units` units (2; LNWR 1) but exactly ONE certificate. An ordinary share = 1 unit = 1 certificate. `ordinary_certs[p,c]` excludes the director's certificate (held in `director_holder[c]`). `units_held = ordinary_certs + (cert_units if director)`; `certs_held = ordinary_certs + (1 if director)`. A major has 10 units; pool cap 5; hold cap 6 (60%).
- Limit counting uses `cert_count = cert_count_holdings + items_led` (leading bids count, 4.2.5/4.10.8). Yellow-zone companies contribute 0.
- Rulings link to actions/derived with `constrains` (they fill a gap) and to rules with `overrides` (override or complete).
- 8 components; every state has an owner component; every cross-component read/write/call is an explicit flagged edge. Shared states (`sale_happened`, `phase`, `bank_cash`, `player_cash`, `sr_order`, `market_stack`, `turn`, ...) list all reader/writer components in their attrs.

## 2. Counts (generated)
Nodes
- action: 31
- component: 8
- constant: 18
- derived: 41
- entity: 21
- rule: 116
- ruling: 15
- state: 34
- TOTAL: 284

Edges
- calls: 106
- constrains: 316
- member_of: 72
- order: 13
- overrides: 44
- part_of: 34
- reads: 127
- refers: 56
- triggers: 17
- uses_constant: 32
- writes: 113
- TOTAL: 930

## 3. Rules skipped (no checkable consequence for the stock round, or physical/out of scope) - no node created
- 1.7.1, 1.7.3, 1.7.8, 1.7.9, 1.7.10, 1.7.13: physical set-up (board, tiles, round marker, banker, reminder tokens, London token).
- 2.2.1: general statement (a rule once introduced stays).
- 2.2.7: empty in the excerpt.
- 3.1.1 (private rules take precedence; P16/P9 deferred by R11), 3.1.7 (closing of P15/P20), 3.1.8-3.1.10 (private acquisitions/powers in operating rounds).
- 3.2.1 (counts; covered by 1.7.5), 3.2.3 (director controls), 3.2.6-3.2.9 (minor operating rules; 3.2.8 is an index fragment).
- 3.3.1 (count), 3.3.4-3.3.6, 3.3.8-3.3.10 (operating-round, token, destination matters); 3.3.7 is garbled index text.
- 4.9.2-4.9.4: physical company setup (charter tokens, revenue token, home station). 4.9.1 is kept as a node.
- 4.8.1-4.8.7 and 4.6.4 ARE nodes but marked `deferred` (R11: direct formation from phase 5 out of scope); they carry only refers/overrides edges.
- 3.1.2 is a node with only a refers edge (to 5.2.1); private revenue values are table data outside this graph.
- Entities without a state node (checker warnings, intentional): lnwr, stock_market, stock_token.

## 4. Ambiguities, conflicts and assumptions (nothing resolved silently; the assumption is stated)
A1. MISSING DATA (input defect). Certificate limit and bidding tokens per player count are column headers only in 1.7.2/4.2.1. The market grid, yellow cells, game-end cells, start-cell positions, train-deck counts per type and the company/private tables are not in the input. They are constants with `missing=true`; a program cannot be finished without them. Start money (700/525/420/350/300) is present.
A2. GARBLED TEXT. The 2.1.x phase table is flattened; phase-1 text appears under 2.2.6 and 2.2.7 is empty; 2.2.8 holds phases 5, 6 and 7; 3.2.8 and 3.3.7 are index fragments. 2.2.6 is used as the phase-1 description (minor start 50/100, no majors).
A3. Player counts 3..7 inferred from the five start-money values (2100/n). The 2-player variant is out of scope.
A4. Private face value is 0 (3.1.3), so an opening bid of 0 is legal (multiple of 5, >= face) and counts as a bid. Owner should confirm.
A5. Not stated: may a player hold two tokens on one item or raise their own leading bid? Assumed one token per player per item; a leader cannot raise (4.10.4 allows moving only when another player has a higher bid). 4.1.4 says "increase", 4.10.5 "place and/or move": one counter, max 3 per turn.
A6. Minor director's certificates are not listed in 4.2.2. Assumed each counts 1 certificate, and the yellow exemption applies if the minor's token is on yellow.
A7. Buying shares or converting does not check money committed in leading bids (4.10.7 restricts only bids). A player can therefore be unable to pay at resolution; R8 covers that.
A8. R10 names "buy or bid"; conversion is not named. Assumed conversion is also blocked while the player must sell.
A9. Sale batching: 4.4.3/4.4.4 do not say whether a multi-share sale is priced before the whole drop. Assumed one `sell_shares` call = a batch of s shares of one company paid at s x (price before the drop), then the token drops s cells. Splitting into several calls gets lower prices (player's choice). 4.4.6 order = order of calls.
A10. Director succession (4.4.2 vs 3.3.3 vs R5): strict ("drops below"), so equal holdings keep the director. Successor needs units >= cert_units and > the remaining holding; largest holding wins; tie -> nearest after the seller in `sr_order` (forward, cyclic). If s <= ordinary certs the swap happens only when someone exceeds the remainder; if s > ordinary certs a successor is mandatory (R5) and the exchange precedes the rest of the sale. In that case the remainder is below cert_units, so "units >= cert_units" suffices.
A11. 4.5.9 swap by purchase: the buyer gives cert_units ordinary certificates for the director's certificate. For standard majors the old director gains one certificate and the buyer loses one, so the old director can end over the limit; 4.5.7 ignores this and forced selling (R10) handles it.
A12. When both treasury and pool hold shares the buyer chooses the source (4.5.1 silent).
A13. Pass: a turn with no action at all is a pass. A turn with only sells or repayments ends via `end_turn` and resets the pass streak. The rules do not define "pass" precisely.
A14. R6 vs R15 vs 10.1.1: R6 lists buying, selling, conversion; R15 only buy/sell; conversion is treated as a sale (R6). Phase-1 conflict is open per R6; provisional rule "a bid that wins an item at resolution counts" is implemented in resolve_bids. The test runs at the very end of resolution; if it triggers, the remaining steps still ran (assumption).
A15. R8 vs 4.11.7: R8 says an unpayable item "stays in its box and counts as having had a bid" (no 4.11.6 export). A box-1 minor in that state was still "not sold", so 4.11.7 would remove it and export. Implemented literally (removed). Owner to decide whether R8 shields it.
A16. Payment order when a player wins several items and cannot pay all (R8): items processed by highest bid desc, then lower box number, then minor < concession < private. The next-highest bidder who can pay takes the item at their own bid; the certificate limit is NOT rechecked for a reassigned winner.
A17. Train exports (R7 vs 4.11.6/4.11.7): 4.11.6 exports remove an L/2 train and never trigger a phase; 4.11.7 takes the front of the deck (L/2 first, then 3, 4...); an L/2 train counts as a 2-train for the phase check. "Counts as a sale" in 4.11.7 is read as "counts as a train bought" for the phase only; it does NOT set `sale_happened` (else the first-round nothing-sold rule could never fire, because an unsold box-1 minor always exports).
A18. Empty deck: exports do nothing. Phases may skip (a 3-train exported in phase 1 gives phase 3). Phase effects beyond phase number, concession clearing and the `phase_events` hook (rust, train-limit discard, ORs per SR; 2.1.2-2.1.5) belong to the operating-round module.
A19. 4.11.4 uses the phase at resolution, before this resolution's exports.
A20. 4.11.4's "bid over 200 -> 100" is the cap at 100. R3 makes the buyer pay the full bid to the bank, the treasury comes from the bank.
A21. Token placement: 4.7.2 (majors underneath all tokens) vs 4.11.5 (minors above majors, below existing minors); implemented per kind. Matters only for ordering ties.
A22. 4.12: the affected companies and their order are computed once (snapshot) before any token moves. Only floated majors qualify.
A23. Arrows (R11/R12): the stock round moves tokens only vertically; "up" when the cell above is absent means no move; the provisional arrow rule is unused. Assumes contiguous columns, so "down" stops at the first absent cell.
A24. 4.4.7/R10 forced selling uses `cert_count` (holdings plus leading bids). Bids cannot be withdrawn (4.10.10). A player over the limit who has no legal sale is not forced.
A25. R9 vs 3.4.5/4.8.1/2.2.8: R9 overrides: concessions vanish (not converted). With R11 deferring direct formation, a major whose concession was not converted before phase 5 can never start (consequence of the rulings).
A26. 1.6.2 does not cover "same price, same column, different rows"; assumed the upper row first.
A27. 5.2.2 deferred choice is `next_operating_company` recomputing after each company. Companies floated in this SR operate in the next OR. Minors always before majors.
A28. 4.3.2 "paid to the bank" vs 4.3.5 "separate source": repayment and interest do not change `bank_cash`.
A29. "Bank runs out" = `bank_cash < 0` (bank keeps paying, 10.1.1). Initial `bank_cash` = 9900. Game-end cell positions are missing (A1).
A30. 10.1.1 "after the next operating round" is recorded as a trigger value; OR/endgame scheduling is out of scope. 10.1.2: first trigger wins.
A31. 3.4.1 is vacuous: 4.6.3 forbids buying in phases 2-4 and R9 removes concessions from phase 5.
A32. 4.1.3 "any number" of sells: several sell calls in a chosen order before repay and C. Loans left after step B block buy/convert/bid but not selling.
A33. Turn steps are enforced through `turn.stage` (A_sell < B_repay < C_main).
A34. 10.1.3 wealth is included (`player_wealth`); final scoring is out of scope; concessions valued 100 only while held (phase < 5).
A35. A directorship exchange does not count as selling (4.5.5).
A36. 4.11.3 "sum bid" = the winning bid; tie -> lower box number.
A37. The LNWR concession is on top, so in box 1 of the first SR; biddable in phase 1, convertible only in phases 2-4.
A38. 4.11.10 interest also applies after the last stock round; no loans can exist in SR 1.
A39. Deferred by R11: P16 (treated as an ordinary private for counting), P9 (4.11.9 exception), 4.8 direct formation, arrows.
A40. External providers (checker `external=true`): `has_completed_or` (OR module), increases of `player_loans` (forced train purchase), consumers of `company_cash`, `removed_items`, `phase_events`. Setup inputs: shuffles, random player order, train deck, market data.

## 5. Checker result
`python3 check_graph.py` gives 0 violations (4 warnings: three entities without a state, rule 3.1.2 refers-only).
