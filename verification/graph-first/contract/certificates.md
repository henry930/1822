# Contract: `backend/app/engine/certificates.py`  (graph component `comp.certificates`)

Read COMMON.md and BINDING.md first (especially trap T1: units vs certificates).
Layer 2. Top-level imports allowed: `models`, `app.data.setup` (`SETUP_BY_PLAYER_COUNT`), `app.data.major_companies`
(`LNWR_ABBR`), `turn_order` (`in_yellow`). LAZY: `from .bidding import items_led` inside `cert_count` (bidding imports this module).
Given callers: none. Callers are the new modules (BINDING C.3).
Exception: `class CertificateError(Exception)` (`ERR_NOT_ENOUGH_ORDINARY`).
Return type for `sale_legal`: `class SaleCheck(NamedTuple): legal: bool; swap_needed: bool; successor: str | None`.

Notation (BINDING A.1/T1): `shares(p,c) = state.players[p].shares.get(c,0)` (units, includes the director's certificate);
`dir(c) = state.majors[c].director_player_id`; `floated(c) = state.majors[c].floated`; `has_op(c) = state.majors[c].has_operated`;
`tre(c) = state.majors[c].shares_in_treasury`; `pool(c) = state.majors[c].shares_in_bank_pool`; `n = len(state.player_order)`.
Major ids are abbreviations in `state.majors`; minor ids are `"M<n>"` in `state.minors`.
The ONLY state this file writes is `state.majors[c].director_player_id` (via `swap_director`).

---------------------------------------------------------------------------------------------------------------------
## 1. Derived functions (formulas copied from the graph)

### `cert_units(cid) -> int`   (`drv.cert_units`; 3.3.2, `const.share_structure`)
`1 if cid == LNWR_ABBR else 2`. As certificates the director's certificate always counts exactly 1.

### `ordinary_certs(state, pid, cid) -> int`   (`st.ordinary_certs`, binding of the state node)
`shares(pid,cid) - (cert_units(cid) if dir(cid) == pid else 0)`. Excludes the director's certificate.

### `units_held(state, pid, cid) -> int`   (`drv.units_held`; 4.5.6)
`ordinary_certs[p,c] + (cert_units(c) if director_holder[c] == p else 0)` = `shares(pid,cid)` (identical by T1; implement via the formula).

### `certs_held(state, pid, cid) -> int`   (`drv.certs_held`; 4.2.2)
major: `ordinary_certs[p,c] + (1 if director_holder[c] == p else 0)`; minor: `1 if minor_director[c] == p else 0`
(minor_director = `state.minors[cid].director_player_id`). Dispatch on `cid in state.minors`.

### `cert_limit(state) -> int`   (`drv.cert_limit`; 4.2.1; `const.cert_limit`)
`SETUP_BY_PLAYER_COUNT[n].certificate_limit`.

### `cert_count_holdings(state, pid) -> int`   (`drv.cert_count_holdings`; 4.2.2, 3.1.5, 3.4.3, 4.2.3)
`sum over majors and minors c of (0 if in_yellow(c) else certs_held(p,c)) + |player_privates[p]| + |player_concessions[p]|`
= over all keys of `state.majors` and `state.minors`; `len(player.private_companies)`; `len(player.concessions)`.
P16 is NOT exempted (R11 deferred). `in_yellow` = `turn_order.in_yellow`.

### `cert_count(state, pid) -> int`   (`drv.cert_count`; 4.2.5, 4.10.8)
`cert_count_holdings(p) + items_led(p)` where `items_led` = `bidding.items_led(state, pid)` (LAZY import). Used for EVERY "at the limit" test.

### `over_limit(state, pid) -> bool`   (`drv.over_limit`; 4.2.6, 4.4.7)
`cert_count(p) > cert_limit`.

### `successor(state, cid, director_pid, remaining_units) -> str | None`   (`drv.successor`; 4.4.2, R5)
Let `d = director_pid`, `r = remaining_units`.
`candidates = {q != d : units_held(q,c) >= cert_units(c) and units_held(q,c) > r}` (q ranges over `state.player_order`).
None -> `None`; else the candidate with maximum `units_held`; tie -> the tying player closest after `d` in `state.player_order`
(forward, cyclic: position `(index(q) - index(d)) mod n` smallest).

### `sale_legal(state, pid, cid, count) -> SaleCheck`   (`drv.sale_legal`; 4.4.2, R5)
Let `k = ordinary_certs[p,c]`, `H = units_held(p,c)`, `d = director_holder[c]`, `s = count`.
```
legal = s >= 1 and floated(c) and has_completed_or(c) and pool(c) + s <= 5
        and ( (p != d and s <= k)
              or (p == d and (s <= k or (s <= H and successor(c, p, H - s) is not None))) )
swap_needed = (p == d and successor(c, p, H - s) is not None)
   # s <= k: only if another player exceeds the director's remaining holding H - s; s > k: forced
successor field = successor(c, p, H - s) if swap_needed else None
```
Return `SaleCheck(legal, swap_needed, successor)`. If `c` is not in `state.majors` (e.g. a minor id) -> `legal False`.
`has_completed_or(c)` = `has_operated`. (`d` None = not started -> not legal because `floated` is False.)

### `can_sell_any(state, pid) -> bool`   (`drv.can_sell_any`; 4.4.7)
`exists major c: sale_legal(p, c, 1).legal`.

### `must_sell(state, pid) -> bool`   (`drv.must_sell`; 4.4.7, R10)
`over_limit(p) and can_sell_any(p)`.

### `fully_sold(state, cid) -> bool`   (`drv.fully_sold`; 4.12.1, R13, 4.12.3)
`floated(c) and treasury_shares[c] == 0 and pool_shares[c] == 0`. Minors (`cid in state.minors`): always False.

---------------------------------------------------------------------------------------------------------------------
## 2. Action: `swap_director(state, cid, new_director_pid)`   (`act.swap_director`; 3.3.3, 4.4.2, 4.5.9)
Precondition [3.3.3]: `q != director_holder[c]` and `ordinary_certs[q,c] >= cert_units(c)`.
Error: `ERR_NOT_ENOUGH_ORDINARY` -> `CertificateError`.
Effects (graph, then binding to fields):
1. `old = director_holder[c]`.
2. [4.4.2, 4.5.9] `ordinary_certs[q,c] -= cert_units(c); ordinary_certs[old,c] += cert_units(c); director_holder[c] = q`.
   BINDING (T1): `Player.shares` is NOT changed by this (units of every holder unchanged); the whole effect is
   `state.majors[c].director_player_id = q`. (After it `ordinary_certs(q)` has dropped by `cu` and `ordinary_certs(old)` risen by `cu` by formula.)
3. "total units of every holder unchanged; certificate counts change: q `-(cert_units-1)`, old `+(cert_units-1)` (LNWR: no change)" - this
   follows automatically from the formulas in section 1; nothing else to write.
Calls `cert_units` (graph edge swap_director -> cert_units). It does not move cash, does not touch `has_operated`.

---------------------------------------------------------------------------------------------------------------------
## 3. Cross-module obligations
- shares.sell_shares calls `sale_legal` (reading `swap_needed`/`successor`), then, if `swap_needed`, `swap_director(c, successor)` BEFORE reducing
  the seller's holding (4.4.2 "exchange occurs before resolving the rest of the sale"); shares.buy_share calls `swap_director(c, player)`
  when the buyer's `units_held` after the purchase exceeds the director's.
- All writers of `Player.shares` (shares.py, company_formation.py) keep the T1 representation. company_formation.convert_concession sets
  `Player.shares[c] = cert_units(c)` and `director_player_id` itself (it does not call `swap_director`).
- `bidding.items_led` is required by `cert_count` (cross-component read). `turn_order.in_yellow` is required by `cert_count_holdings`.
- `state.player_order` is the "sr_order" used for the tie-break in `successor`.

## Graph gaps (do not decide; report)
1. `sale_legal`: the graph returns {legal, swap_needed, successor} but the sell action needs distinct error codes (ERR_NOT_SELLABLE, ERR_POOL_FULL, ERR_TOO_MANY); the derived node does not expose which clause failed.
2. `successor` when `r` is 0 or when the director's remaining holding is exactly equal to another player's: graph says strictly greater ("drops below"), stated; but R5 text "more than the director's remaining holding" and 3.3.3 "acquires more shares than the director" agree; no gap, except for the 4.5.9 buy-swap where the contract uses `units_held(buyer) > units_held(director)` (in shares.md).
3. `cert_count_holdings` for minors in yellow zone: graph applies the exemption (assumption A6) although 4.2.2 does not mention minors.
4. P16 and `Player.tax_haven_shares` are ignored (R11).
5. The graph defines `can_sell_any` with s = 1 only: a player who could sell 2 shares at once but not 1 (cannot happen with the stated rules) is not covered; also whether sale legality of "1 share" should consider the has-completed-OR rule for each company (it does through sale_legal).
6. `certs_held` / `cert_count_holdings` do not say what to do for a company id that does not exist.
7. Order of evaluation / which player order is used for tie-break when `director_pid` is not in `player_order`: unspecified (cannot happen).
8. `swap_director` precondition does not forbid `q` being the LNWR holder of P16-held shares etc. (R11 deferred).
