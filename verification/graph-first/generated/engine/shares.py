"""Share trading: sell, buy, repay loans, loan interest (contract shares.md)."""
from __future__ import annotations

from .models import GameState
from . import certificates, turn_order, scoring


class ShareError(Exception):
    pass


POOL_CAP = 5
HOLD_CAP_UNITS = 6


def _err(code: str, text: str) -> ShareError:
    return ShareError(f"{code}: {text}")


def _player(state: GameState, player_id: str):
    p = state.players.get(player_id)
    if p is None:
        raise _err("ERR_NOT_SELLABLE", f"unknown player {player_id}")
    return p


def sell_shares(state: GameState, player_id: str, company_id: str, count: int) -> None:
    player = _player(state, player_id)
    major = state.majors.get(company_id)
    if major is None:
        raise _err("ERR_NOT_SELLABLE", f"{company_id} is not a major company; only major company shares can be sold")
    if not (major.floated and major.has_operated):
        raise _err("ERR_NOT_SELLABLE", f"{company_id} has not yet completed an operating round; its shares cannot be sold")
    if not isinstance(count, int) or isinstance(count, bool):
        raise _err("ERR_TOO_MANY", "count must be an integer")
    if major.shares_in_bank_pool + count > POOL_CAP:
        raise _err("ERR_POOL_FULL", f"the bank pool cannot hold more than {POOL_CAP} shares of {company_id}")
    if count < 1:
        raise _err("ERR_TOO_MANY", "you must sell at least one share")
    chk = certificates.sale_legal(state, player_id, company_id, count)
    if not chk.legal:
        raise _err("ERR_TOO_MANY", f"you cannot sell {count} share(s) of {company_id}")

    price = turn_order.current_price(state, company_id)
    if chk.swap_needed:
        certificates.swap_director(state, company_id, chk.successor)
    player.shares[company_id] = player.shares.get(company_id, 0) - count
    major.shares_in_bank_pool += count
    player.cash += count * price
    state.bank.cash -= count * price
    turn_order.move_token_down(state, company_id, count)
    sold = list(state.sold_this_round.get(player_id, ()))
    if company_id not in sold:
        sold.append(company_id)
    state.sold_this_round[player_id] = sold
    state.any_sale_this_stock_round = True
    scoring.check_game_end_triggers(state, "after_bank_payment")


def buy_share(state: GameState, player_id: str, company_id: str, source: str | None) -> None:
    player = _player(state, player_id)
    if player.loans != 0:
        raise _err("ERR_LOANS", "you cannot buy shares while you have loans")
    if certificates.must_sell(state, player_id):
        raise _err("ERR_MUST_SELL", "you are over the certificate limit and must sell before buying")
    major = state.majors.get(company_id)
    if major is None or not major.floated or major.director_player_id is None:
        raise _err("ERR_NOT_STARTED", f"{company_id} has not been started")
    if source not in (None, "treasury", "pool"):
        raise _err("ERR_NO_SHARE_AT_SOURCE", f"unknown source {source!r}")
    if source is None:
        if major.shares_in_bank_pool >= 1:
            source = "pool"
        elif major.shares_in_treasury >= 1:
            source = "treasury"
        else:
            raise _err("ERR_NO_SHARE_AT_SOURCE", f"no share of {company_id} is available")
    elif source == "pool" and major.shares_in_bank_pool < 1:
        raise _err("ERR_NO_SHARE_AT_SOURCE", f"the bank pool holds no share of {company_id}")
    elif source == "treasury" and major.shares_in_treasury < 1:
        raise _err("ERR_NO_SHARE_AT_SOURCE", f"the treasury of {company_id} holds no share")
    price = turn_order.current_price(state, company_id)
    if player.cash < price:
        raise _err("ERR_INSUFFICIENT_CASH", f"a share of {company_id} costs {price} and you have {player.cash}")
    if company_id in state.sold_this_round.get(player_id, ()):
        raise _err("ERR_SOLD_THIS_ROUND", f"you sold {company_id} earlier in this stock round")
    if certificates.units_held(state, player_id, company_id) >= HOLD_CAP_UNITS:
        raise _err("ERR_AT_60_PERCENT", f"you already hold 60% of {company_id}")
    if not turn_order.in_yellow(state, company_id):
        if certificates.cert_count(state, player_id) + 1 > certificates.cert_limit(state):
            raise _err("ERR_CERT_LIMIT", "buying this share would exceed the certificate limit")

    if source == "treasury":
        major.treasury += price
        major.shares_in_treasury -= 1
    else:
        state.bank.cash += price
        major.shares_in_bank_pool -= 1
    player.cash -= price
    player.shares[company_id] = player.shares.get(company_id, 0) + 1
    director = major.director_player_id
    if director != player_id and (
        certificates.units_held(state, player_id, company_id)
        > certificates.units_held(state, director, company_id)
    ):
        certificates.swap_director(state, company_id, player_id)
    state.any_sale_this_stock_round = True


def repay_loans(state: GameState, player_id: str, amount: int) -> None:
    player = _player(state, player_id)
    if player.loans == 0:
        raise _err("ERR_NO_LOANS", "you have no loans")
    if amount <= 0 or amount > player.loans:
        raise _err("ERR_BAD_AMOUNT", f"amount must be between 1 and {player.loans}")
    if player.cash < amount:
        raise _err("ERR_INSUFFICIENT_CASH", f"you have {player.cash} and need {amount}")
    player.cash -= amount
    player.loans -= amount


def interest_amount(loans: int) -> int:
    return (loans + 1) // 2


def charge_interest(state: GameState) -> None:
    for p in state.players.values():
        if p.loans > 0:
            p.loans += interest_amount(p.loans)
