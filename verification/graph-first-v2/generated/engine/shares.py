"""Share trading rules: selling to the bank pool, buying from pool/treasury,
loan repayment and end-of-stock-round loan interest (layer 5).

Representation (see contract/BINDING.md): Player.shares[c] counts units of 10%
including the director's certificate; MajorCompanyState.shares_in_treasury /
shares_in_bank_pool count ordinary units only.
"""
from __future__ import annotations

from .models import GameState

SOURCE_BANK = 'bank'
SOURCE_POOL = 'pool'
SOURCE_TREASURY = 'treasury'

_POOL_CAP = 5
_HOLD_CAP = 6


class ShareError(Exception):
    """Single exception class of the shares module; message '<CODE>: <text>'."""

    def __init__(self, code: str, text: str = ''):
        self.code = code
        super().__init__(f'{code}: {text}' if text else code)


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def interest_amount(loans: int) -> int:
    """Interest on a loan: ceil(loans / 2)."""
    return (loans + 1) // 2


loan_interest = interest_amount


def charge_interest(state: GameState) -> None:
    """Add 50% interest (rounded up) to every player's loans; bank cash unchanged."""
    for player in state.players.values():
        if player.loans > 0:
            player.loans += interest_amount(player.loans)


apply_interest = charge_interest


def sell_shares(state: GameState, player_id: str, company_id: str, count: int = 1) -> None:
    from . import certificates, scoring, turn_order

    # 1-6: validation, in contract order
    player = state.players.get(player_id)
    if player is None:
        raise ShareError('ERR_UNKNOWN_PLAYER', f'unknown player {player_id!r}')
    major = state.majors.get(company_id)
    if major is None:
        raise ShareError('ERR_NOT_SELLABLE', f'{company_id!r} is not a major company')
    if not _is_int(count) or count < 1:
        raise ShareError('ERR_BAD_COUNT', 'count must be an integer >= 1')
    if not (major.floated and major.has_operated):
        raise ShareError('ERR_NOT_SELLABLE',
                         f'{company_id} is not floated or has not completed an operating round')
    if major.shares_in_bank_pool + count > _POOL_CAP:
        raise ShareError('ERR_POOL_FULL', 'the bank pool may hold at most 5 shares')
    check = certificates.sale_legal(state, player_id, company_id, count)
    if not check.legal:
        reason = check.reason or 'ERR_TOO_MANY'
        if reason not in ('ERR_NOT_SELLABLE', 'ERR_POOL_FULL', 'ERR_TOO_MANY'):
            reason = 'ERR_TOO_MANY'
        raise ShareError(reason, f'cannot sell {count} share(s) of {company_id}')

    # effects
    price = turn_order.current_price(state, company_id)
    if check.swap_needed:
        certificates.swap_director(state, company_id, check.successor)
    player.shares[company_id] = player.shares.get(company_id, 0) - count
    major.shares_in_bank_pool += count
    player.cash += count * price
    state.bank.cash -= count * price
    turn_order.move_token_down(state, company_id, count)
    sold = state.sold_this_round.get(player_id)
    if sold is None:
        state.sold_this_round[player_id] = [company_id]
    elif company_id not in sold:
        if isinstance(sold, list):
            sold.append(company_id)
        else:
            sold.add(company_id)
    state.any_sale_this_stock_round = True
    scoring.check_game_end_triggers(state, 'after_bank_payment')


sell_share = sell_shares


def buy_share(state: GameState, player_id: str, company_id: str, source: str | None = None) -> None:
    from . import certificates, turn_order

    player = state.players.get(player_id)
    if player is None:
        raise ShareError('ERR_UNKNOWN_PLAYER', f'unknown player {player_id!r}')
    if source is not None and source not in (SOURCE_TREASURY, SOURCE_POOL, SOURCE_BANK):
        raise ShareError('ERR_BAD_SOURCE', f'unknown source {source!r}')
    if player.loans != 0:
        raise ShareError('ERR_LOANS', 'cannot buy while in debt')
    if certificates.must_sell(state, player_id):
        raise ShareError('ERR_MUST_SELL', 'over the certificate limit and able to sell')
    major = state.majors.get(company_id)
    if major is None or not major.floated or major.director_player_id is None:
        raise ShareError('ERR_NOT_STARTED', f'{company_id!r} is not a started major company')

    in_pool = major.shares_in_bank_pool >= 1
    in_treasury = major.shares_in_treasury >= 1
    if source is None:
        chosen = SOURCE_POOL if in_pool else (SOURCE_TREASURY if in_treasury else None)
    elif source == SOURCE_TREASURY:
        chosen = SOURCE_TREASURY if in_treasury else None
    else:
        chosen = SOURCE_POOL if in_pool else None
    if chosen is None:
        raise ShareError('ERR_NO_SHARE_AT_SOURCE', 'no share available at the chosen source')

    price = turn_order.current_price(state, company_id)
    if player.cash < price:
        raise ShareError('ERR_INSUFFICIENT_CASH', f'cash {player.cash} < price {price}')
    if company_id in state.sold_this_round.get(player_id, ()):
        raise ShareError('ERR_SOLD_THIS_ROUND', f'{company_id} was sold by this player this round')
    if certificates.units_held(state, player_id, company_id) >= _HOLD_CAP:
        raise ShareError('ERR_AT_60_PERCENT', 'player already holds 60%')
    if not turn_order.in_yellow(state, company_id):
        if certificates.cert_count(state, player_id) + 1 > certificates.cert_limit(state):
            raise ShareError('ERR_CERT_LIMIT', 'certificate limit would be exceeded')

    # effects
    player.cash -= price
    if chosen == SOURCE_TREASURY:
        major.treasury += price
        major.shares_in_treasury -= 1
    else:
        state.bank.cash += price
        major.shares_in_bank_pool -= 1
    player.shares[company_id] = player.shares.get(company_id, 0) + 1
    director_id = major.director_player_id
    if director_id != player_id and (
            certificates.units_held(state, player_id, company_id)
            > certificates.units_held(state, director_id, company_id)):
        certificates.swap_director(state, company_id, player_id)
    state.any_sale_this_stock_round = True


buy_certificate = buy_share


def repay_loans(state: GameState, player_id: str, amount: int | None = None) -> None:
    player = state.players.get(player_id)
    if player is None:
        raise ShareError('ERR_UNKNOWN_PLAYER', f'unknown player {player_id!r}')
    if player.loans <= 0:
        raise ShareError('ERR_NO_LOANS', 'player has no loans')
    if amount is None:
        amount = min(player.loans, player.cash)
        if amount <= 0:
            raise ShareError('ERR_INSUFFICIENT_CASH', 'player has no cash to repay with')
    elif not _is_int(amount) or amount <= 0 or amount > player.loans:
        raise ShareError('ERR_BAD_AMOUNT', f'invalid amount {amount!r}')
    if player.cash < amount:
        raise ShareError('ERR_INSUFFICIENT_CASH', f'cash {player.cash} < amount {amount}')
    player.cash -= amount
    player.loans -= amount


repay_loan = repay_loans
