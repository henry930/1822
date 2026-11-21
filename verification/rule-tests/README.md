# Rule-derived tests (separate from the source code)

Tests written from the wording of `rules.pdf`, one test per rule, with the rule id in the
test name (`test_r4_4_3_...` = rule 4.4.3). They only *call* the engine in `backend/`;
nothing in `backend/` or `frontend/` is changed. Purpose: find where the engine disagrees
with the rulebook, and keep a rule -> test trace.

Run from the repo root:

    cd backend && pip install -e ".[dev]" && cd ..
    python -m pytest verification/rule-tests -q

Current status (chapter 4.2-4.5 only, 19 rules, 30 tests): 26 pass, 4 fail. The failures are
intentional findings, listed with their classification in `RESULTS.md`. Do not "fix" the tests
to match the engine before a human has decided what the rulebook means.
