# Contract: stock-round modules of the 1822 rules engine

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
Write your own quick sanity tests if you like, but keep them under `/home/claude/sandbox_rewrite/my_tests/`.
