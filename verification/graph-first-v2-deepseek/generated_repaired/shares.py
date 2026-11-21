"""Shares module for the 1822 board-game rules engine.

Handles buying, selling and associated cash/loan/flag operations.
"""
from __future__ import annotations

from app.engine.models import GameState

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SOURCE_BANK = "bank"
SOURCE_POOL = "pool"
SOURCE_TREASURY = "treasury"

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------
class ShareError(Exception):
    """Raised for illegal share operations."""
    def __init__(self, code: str, text: str):
        self.code = code
        super().__init__(f"{code}: {text}")

# ---------------------------------------------------------------------------
# Interest helper
# ---------------------------------------------------------------------------
def interest_amount(loans: int) -> int:
    """Interest due on a loan balance: ceil(loans/2)."""
    return (loans + 1) // 2

loan_interest = interest_amount

# ---------------------------------------------------------------------------
# Charge interest (end of stock round)
# ---------------------------------------------------------------------------
def charge_interest(state: GameState) -> None:
    """Add 50% interest to every player's outstanding loans."""
    for player in state.players.values():
        if player.loans > 0:
            player.loans += interest_amount(player.loans)
    # Bank cash unchanged per 4.3.5

apply_interest = charge_interest

# ---------------------------------------------------------------------------
# Sell shares
# ---------------------------------------------------------------------------
def sell_shares(state: GameState, player_id: str, company_id: str, count: int = 1) -> None:
    """Sell *count* ordinary certificates of a major company to the bank pool.

    Precondition checks in order (first failing raises):
        1. player exists
        2. company_id is a major
        3. count is int >= 1
        4. major is floated and has_operated
        5. bank pool would not exceed 5 units
        6. sale_legal returns legal (certificates module)
    """
    # 1. Player existence
    if player_id not in state.players:
        raise ShareError("ERR_UNKNOWN_PLAYER", f"Unknown player {player_id}")

    # 2. Must be a major company
    if company_id not in state.majors:
        raise ShareError("ERR_NOT_SELLABLE",
                         f"{company_id} is not a major company – cannot sell its shares")

    # 3. Count validation
    if not isinstance(count, int) or count < 1:
        raise ShareError("ERR_BAD_COUNT",
                         f"count must be an integer >= 1, got {count!r}")

    major = state.majors[company_id]

    # 4. Must be floated and have operated at least once
    if not major.floated or not major.has_operated:
        raise ShareError("ERR_NOT_SELLABLE",
                         f"{company_id} has not completed its first OR yet")

    # 5. Bank pool capacity
    if major.shares_in_bank_pool + count > 5:
        raise ShareError("ERR_POOL_FULL",
                         f"Selling {count} shares would exceed bank pool limit of 5")

    # Lazy import for certificates module (layer 2 – may be imported at module level,
    # but we do it here to be explicit about cross-module dependencies)
    from app.engine.certificates import sale_legal

    check = sale_legal(state, player_id, company_id, count)
    if not check.legal:
        reason = check.reason or "ERR_TOO_MANY"
        text = {
            "ERR_NOT_SELLABLE": "Company not sellable",
            "ERR_POOL_FULL": "Pool full",
            "ERR_TOO_MANY": "Insufficient ordinary shares or no eligible successor",
        }.get(reason, "Sale not allowed")
        raise ShareError(reason, text)

    # --- All checks passed – begin mutations ---

    # Determine price BEFORE any token movement (assumption A9)
    from app.engine.turn_order import current_price
    price = current_price(state, company_id)

    # If a swap is needed, execute it first
    if check.swap_needed:
        from app.engine.certificates import swap_director
        swap_director(state, company_id, check.successor)

    # Update ordinary certificates: Player.shares includes director's units.
    # We reduce by `count` ordinary certs. The director's cert units are not sold.
    player = state.players[player_id]
    player.shares[company_id] = player.shares.get(company_id, 0) - count

    # Bank pool gains the sold units
    major.shares_in_bank_pool += count

    # Cash flows
    total = count * price
    player.cash += total
    state.bank.cash -= total

    # Move token down one cell per share sold
    from app.engine.turn_order import move_token_down
    move_token_down(state, company_id, count)

    # Record sale for round restrictions
    if player_id not in state.sold_this_round:
        state.sold_this_round[player_id] = []
    if company_id not in state.sold_this_round[player_id]:
        state.sold_this_round[player_id].append(company_id)

    # Set sale flag (module sets it; actions.py may also set it – idempotent)
    state.any_sale_this_stock_round = True

    # Game end trigger check
    from app.engine.scoring import check_game_end_triggers
    check_game_end_triggers(state)

sell_share = sell_shares

# ---------------------------------------------------------------------------
# Buy share
# ---------------------------------------------------------------------------
def buy_share(state: GameState, player_id: str, company_id: str,
              source: str | None = None) -> None:
    """Buy one ordinary share of a started major company.

    Precondition checks in order:
        1. player exists
        2. source is valid (None, 'treasury', 'pool', 'bank')
        3. player has no loans
        4. player is not over the limit and able to sell (must_sell)
        5. company is a major, floated, and has a director
        6. chosen source (or at least one when None) holds at least one share
        7. player has enough cash
        8. player has not sold this company earlier this round
        9. player does not already hold 60% (6 units) of this company
        10. either company is in yellow zone or cert count + 1 <= limit
    """
    # 1. Player existence
    if player_id not in state.players:
        raise ShareError("ERR_UNKNOWN_PLAYER", f"Unknown player {player_id}")

    # 2. Source validation
    valid_sources = {None, 'treasury', 'pool', 'bank'}
    if source not in valid_sources:
        raise ShareError("ERR_BAD_SOURCE",
                         f"Invalid source {source!r}; must be None, 'treasury', 'pool', or 'bank'")

    player = state.players[player_id]

    # 3. Loans must be zero
    if player.loans > 0:
        raise ShareError("ERR_LOANS", "Player has outstanding loans and cannot buy shares")

    # 4. Must not be required to sell
    from app.engine.certificates import must_sell
    if must_sell(state, player_id):
        raise ShareError("ERR_MUST_SELL", "Player is over the limit and must sell first")

    # 5. Company must be a major, floated, with a director
    if company_id not in state.majors:
        raise ShareError("ERR_NOT_STARTED",
                         f"{company_id} is not a major company (or not floated)")
    major = state.majors[company_id]
    if not major.floated or major.director_player_id is None:
        raise ShareError("ERR_NOT_STARTED",
                         f"{company_id} is not yet started (no director)")

    # 6. Determine actual source and check availability
    pool_available = major.shares_in_bank_pool > 0
    treasury_available = major.shares_in_treasury > 0

    if source is None:
        # Default: pool first, then treasury (INTERIM ruling GA22)
        if pool_available:
            effective_source = 'pool'
        elif treasury_available:
            effective_source = 'treasury'
        else:
            raise ShareError("ERR_NO_SHARE_AT_SOURCE",
                             "No shares available in pool or treasury")
    elif source == 'bank':
        effective_source = 'pool'  # 'bank' and 'pool' are the same
    else:
        effective_source = source

    # Check that the effective source has a share
    if effective_source == 'pool':
        if not pool_available:
            raise ShareError("ERR_NO_SHARE_AT_SOURCE",
                             "No shares available in the bank pool")
    else:  # 'treasury'
        if not treasury_available:
            raise ShareError("ERR_NO_SHARE_AT_SOURCE",
                             "No shares available in the company treasury")

    # 7. Cash check
    from app.engine.turn_order import current_price
    price = current_price(state, company_id)
    if player.cash < price:
        raise ShareError("ERR_INSUFFICIENT_CASH",
                         f"Player has £{player.cash}, need £{price}")

    # 8. Sold-this-round check
    sold_list = state.sold_this_round.get(player_id, [])
    if company_id in sold_list:
        raise ShareError("ERR_SOLD_THIS_ROUND",
                         f"Cannot buy {company_id} after selling it this round")

    # 9. 60% cap check (units_held < 6)
    # units_held includes director's cert units. We get it from certificates.units_held.
    from app.engine.certificates import units_held
    if units_held(state, player_id, company_id) >= 6:
        raise ShareError("ERR_AT_60_PERCENT",
                         f"Player already holds 60% of {company_id}")

    # 10. Certificate limit check (unless in yellow)
    from app.engine.certificates import cert_count, cert_limit
    from app.engine.turn_order import in_yellow
    if not in_yellow(state, company_id):
        if cert_count(state, player_id) + 1 > cert_limit(state):
            raise ShareError("ERR_CERT_LIMIT",
                             "Buying this certificate would exceed the certificate limit")

    # --- All checks passed – begin mutations ---

    # Deduct cash from player
    player.cash -= price

    # Transfer the share: increase ordinary certificates (Player.shares)
    # Player.shares holds total units (including director's cert)
    player.shares[company_id] = player.shares.get(company_id, 0) + 1

    # Update source
    if effective_source == 'pool':
        major.shares_in_bank_pool -= 1
        state.bank.cash += price
    else:  # treasury
        major.shares_in_treasury -= 1
        major.treasury += price

    # Swap director if buyer now holds more units than current director
    current_director = major.director_player_id
    if current_director is not None:
        buyer_units = units_held(state, player_id, company_id)
        dir_units = units_held(state, current_director, company_id)
        if buyer_units > dir_units:
            from app.engine.certificates import swap_director
            swap_director(state, company_id, player_id)

    # Set sale flag
    state.any_sale_this_stock_round = True

buy_certificate = buy_share

# ---------------------------------------------------------------------------
# Repay loans
# ---------------------------------------------------------------------------
def repay_loans(state: GameState, player_id: str,
                amount: int | None = None) -> None:
    """Repay all or part of a player's loans.

    Precondition checks in order:
        1. player exists
        2. player has loans > 0
        3. amount is valid (None or int with 0 < amount <= loans)
        4. player.cash >= amount
    """
    # 1. Player existence
    if player_id not in state.players:
        raise ShareError("ERR_UNKNOWN_PLAYER", f"Unknown player {player_id}")

    player = state.players[player_id]

    # 2. Loans must exist
    if player.loans <= 0:
        raise ShareError("ERR_NO_LOANS", "Player has no outstanding loans")

    # 3. Determine amount
    if amount is None:
        amount = min(player.loans, player.cash)
    else:
        if not isinstance(amount, int) or amount <= 0 or amount > player.loans:
            raise ShareError("ERR_BAD_AMOUNT",
                             f"Amount {amount!r} invalid; must be int with 0 < amount <= {player.loans}")

    # 4. Cash check
    if player.cash < amount:
        raise ShareError("ERR_INSUFFICIENT_CASH",
                         f"Player has £{player.cash}, needs £{amount}")

    # --- All checks passed – mutate ---
    player.cash -= amount
    player.loans -= amount
    # Bank cash unchanged per 4.3.5

repay_loan = repay_loans
