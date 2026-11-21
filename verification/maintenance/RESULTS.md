# Maintenance-cost experiment (DeepSeek V4 Flash, single run per cell)
Base: graph-first v2 engine (114/121 pass). Three rule changes M1 (interest 50%->25%), M2 (pool cap 5->6), M3 (phase-3 minor treasury = bid/2). Oracle = reference patch; arm must reproduce the oracle's exact pass/fail set.
Arms: B = regenerate affected modules from new contract; C = contract-diff + current code -> patch affected modules; D = conventional baseline: change request + full engine source (8 modules, ~126k prompt tokens) -> all modules.
Affected modules (computed locally from graph diff, 0 tokens): M1 6 (BINDING changed), M2 4, M3 2. Graph/contract diff: M3 = 4 nodes, 22 contract lines.

| change | arm | modules | tokens in | tokens out | cost $ | oracle match |
|---|---|---|---|---|---|---|
| M1 | B | 6 | 293,979 | 29,698 | 0.0168 | NO (import errors) |
| M1 | C | 6 | 21,749 | 23,949 | 0.0026 | YES |
| M1 | D | 8 | 126,238 | 18,667 | 0.0066 | YES |
| M2 | B | 4 | 188,517 | 16,221 | 0.0082 | NO |
| M2 | C | 4 | 14,781 | 12,578 | 0.0017 | YES |
| M2 | D | 8 | 126,190 | 18,717 | 0.0113 | YES |
| M3 | B | 2 | 103,780 | 10,538 | 0.0073 | NO |
| M3 | C | 2 | 7,384 | 13,238 | 0.0005 | YES |
| M3 | D | 8 | 126,278 | 19,309 | 0.0039 | YES |

Findings: (1) contract-diff patching (C) matched the oracle 3/3 with 6-17x fewer input tokens than source-upload (D); (2) partial regeneration from contract alone (B) breaks 3/3: regenerated modules drop test-facing aliases (e.g. `_face_value`) that other modules/tests rely on and that are not in the graph -> whole-module regeneration needs those conventions as graph nodes, or patch mode; (3) D also matches but uploads all source (privacy cost). Caveats: n=1, 3 changes, small engine, output tokens dominated by full-file rewrites, cost via OpenRouter.
