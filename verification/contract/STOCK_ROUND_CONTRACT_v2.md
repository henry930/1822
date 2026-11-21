# Contract (v2): stock-round modules of the 1822 rules engine

Your job: write five Python modules in `backend/app/engine/` so that they satisfy this contract and the
rulebook excerpt in `RULES.md`. The rest of the engine (data model, setup, actions glue, round manager,
operating round, data tables) is given and must NOT be modified. The rulebook wins over anything else:
when a rule is clear, implement it exactly, even if some other code or comment seems to assume otherwise.

Files to create (each currently missing):
`shares.py`, `certificates.py`, `company_formation.py`, `bidding.py`, `turn_order.py`
(all in `backend/app/engine/`). Python >= 3.11. Run from `backend/` with `pip install -e ".[dev]"` done
(or just `PYTHONPATH=.`). Money is integer pounds. Do not read anything outside this sandbox directory.

## Data model (given: `app/engine/models.py`, `app/data/*`, `app/engine/setup.py`, `stock_positions.py`)
- `GameState`, `Player.shares[company_id]` = number of 10% units held (a major's director's certificate = 2 units,
  LNWR's = 1 unit; a minor's director's certificate = 1 unit). `MajorCompanyState.shares_in_treasury` and
  `shares_in_bank_pool` are counted in 10% units (director's certificate counts as 2 units).
- `state.stock_positions[company_id] = (row, col)`; value via `stock_positions.company_value`; moves via
  `stock_positions.place_token` (puts the token at the bottom of the cell's stack). Cell `zone` "yellow" = rule 1.6.5 yellow area.
- Stock-market rows increase downward (row 0 is the top); a company's price drops by moving to row+1 in the same column.
  A move is impossible if the target cell does not exist (token stays).
- Bid boxes: `state.concession_bid_boxes`, `minor_bid_boxes`, `private_bid_boxes` (lists, index 0 = box 1, `None` = empty);
  items are `BidBoxItem(kind, ref, bids={player_id: amount})`. `setup._refill_bid_boxes(state)` (given) shifts and refills boxes.
- Sold-this-round bookkeeping: `state.sold_this_round[player_id]` = set of company ids; `state.any_sale_this_stock_round`.
- Player ids look like "p1"; minors are keyed `"M<number>"` in `state.minors`; majors by abbreviation (e.g. "GWR", "LNWR").

## certificates.py
- `certificate_limit(state) -> int`: rule 4.2.1 (by number of players; table in `app.data.setup`).
- `owned_certificate_count(state, player_id) -> int`: rules 4.2.2-4.2.3. Counts private companies, concessions and share
  certificates (a major's director's certificate = 1 certificate even though it is 2 units; LNWR's = 1; a minor's = 1).
  Shares of a company whose token is in the yellow zone are not counted.
- `bid_certificate_count(state, player_id) -> int`: rule 4.10.8; each bid-box item (all three kinds) on which the player holds the highest bid counts as 1.
- `certificate_count(state, player_id) = owned + bid`.

## shares.py
- `class ShareError(Exception)`; constant `MAX_HOLDING_UNITS = 6`.
- `buy_share(state, player_id, company_id, source: str | None = None) -> None`: rules 4.2.4, 4.3.1, 4.5.1-4.5.9.
  `source` is `"bank"` (bank pool) or `"treasury"` (company treasury); `None` = bank pool if it has a share, else treasury.
  Raise `ShareError` when the purchase is illegal. Pay the share's current stock-market value to the bank or to the company treasury.
  Update `player.shares`, the pool/treasury counts, the director (rule 4.5.9) and the cash.
  Note: a major whose `floated` is False has nothing to buy; a company with no director has no buyable ordinary shares.
- `sell_shares(state, player_id, company_id, count) -> None`: rules 4.4.1-4.4.7 (and 4.5.5 bookkeeping, 4.4.2 director change,
  4.4.3 payment, 4.4.4-4.4.5 price drop). Raise `ShareError` when illegal. The director change is a change of
  `director_player_id` (the units held do not change).

## company_formation.py
- `class ConcessionError(Exception)`; `VALID_START_PRICES = (60, 70, 80, 90, 100)`.
- `convert_concession(state, player_id, abbr, start_price) -> None`: rules 4.7.1-4.7.4 and 4.9 (company ends up floated, with a director,
  `share_price` set, token placed on the red-outlined start cell ("start" zone) of that value, treasury funded exactly as the rules
  say with money moving from the right source (bank / player), remaining certificates in the company treasury). Raise `ConcessionError` if illegal.

## bidding.py
- Constants `CONCESSION_FACE_VALUE`, `PRIVATE_FACE_VALUE`, `MINOR_FACE_VALUE`; `class BidError(Exception)`; helper `_face_value(kind) -> int`
  (kind in "concession" | "minor" | "private"; use the face values the rulebook states; where it states none, use 0).
- `place_or_move_bid(state, player_id, kind, box_index, amount) -> None`: rules 4.10.3-4.10.8, 4.10.10 (raise `BidError` when illegal; the 3-bids-per-turn
  limit 4.10.5 is enforced by the given `actions.py`, not here). Record the bid in `item.bids[player_id]`.
- `resolve_stock_round(state) -> None`: the end-of-stock-round procedure: rule 4.11 (all of it, incl. flotation of minors by phase, train exports,
  removal of an unsold box-1 minor, refilling boxes via `setup._refill_bid_boxes`), 4.3.4/4.11.10 (loan interest) and 4.12.1-4.12.2 (price rise of fully-sold majors).
  (Player order for the next round is handled by the given `round_manager.py`.)
  Train export means: remove one L/2 train from `state.bank.train_pool["L"]` (and run a phase check as bank purchases do: see given `trains.py`).
  When a minor is floated it becomes `floated`, gets its director, price/treasury per 4.11.4, a token on the stock market, and the paid bid goes to the right place.

## turn_order.py
- `stock_round_order(state) -> list[str]`: rule 4.1.2.
- `compute_operating_order(state) -> list[str]`: rules 5.2.1-5.2.2 (floated minors then floated majors; descending share price; ties by token position).
  Use `stock_positions.descending_price_key` if it fits; check it against the rule text.
- `reorder_players_by_cash(state) -> list[str]`: rule 4.11.9.

## Report back
When done, reply with (1) a short summary of what you implemented, (2) a numbered list of every ambiguity, assumption or rule that you could not
implement or are unsure about (this list will be shown to the game's rules owner for decisions), (3) any problem you found in the contract itself.
Write your own quick sanity tests if you like, but keep them under `/home/claude/sandbox_par2/my_tests/`.

## Cross-module behaviour and provisional decisions (v2 - binding for all five modules)
These settle points on which an earlier attempt had to guess. Where a "provisional" decision is marked, the rules owner has not ruled yet; implement it exactly as written so that all modules agree.
1. **First-round end (rule 10.1.1) coupling.** The given `round_manager.end_stock_round` ends the game if `state.any_sale_this_stock_round` is False in the very first stock round. `place_or_move_bid` MUST set `state.any_sale_this_stock_round = True` on every successful bid; `buy_share`, `sell_shares` and `convert_concession` need not (the given `actions.py` sets it for them).
2. **`shares_in_treasury` after conversion** counts ordinary units only: 8 for a normal major (nine certificates, the director's certificate = 2 units), 9 for LNWR (director's = 1 unit). Nothing else is placed in the treasury; `shares_in_bank_pool` stays 0.
3. **Where things are recorded.** A won concession goes into `player.concessions` as the major's abbreviation string (bid-box `ref` of a concession is that string, not an index). A won private: `player.private_companies` and `state.privates[n].owner_player_id`. A floated minor: `state.minors["M<n>"]` (director, floated, share_price, treasury) and `player.shares["M<n>"] = 1`. A minor's director's certificate counts 1 certificate.
4. **Bid boxes** are indexed 0-based (index 0 = box 1).
5. **Provisional decisions:** minor face value = 100 (`MINOR_FACE_VALUE = 100`); a phase-1 minor starts at 50 with a treasury of 100; for phases 2 and 3+ follow 4.11.4's formulas; money paid for items goes to the bank, treasuries of newly floated minors are funded from the bank in phases 1-2 and with the bid itself in phase 3+. LNWR conversion: the bank pays the whole start price into the treasury, the player pays nothing. P16 (tax haven) and the P9 exception to 4.11.9: ignored. Phase 5+ direct formation (4.8): not in scope; `buy_share` refuses a major that is not floated.
6. **Loans:** a player with `loans > 0` may not buy a share, convert a concession or place a bid (rule 4.3.1). Interest at end of the stock round: `loans += ceil(loans / 2)`.
7. **Who calls whom.** `shares` and `bidding` use `certificates.certificate_count/certificate_limit`. `bidding.resolve_stock_round` is the only place that exports trains (via `trains.py` helpers) and refills boxes (`setup._refill_bid_boxes`). `turn_order` and `company_formation` call no other new module.
8. **Integration check (required).** When all five files exist (poll for them; the others are written concurrently), run a short end-to-end check of your own through the public API: `new_game`, then `actions.apply_action` for a bid turn followed by passes until the stock round ends, then a share purchase/sale on a company you set up by hand. Fix anything that breaks in YOUR module; report anything that breaks in someone else's module instead of editing it.
