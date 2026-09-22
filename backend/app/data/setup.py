"""Player-count-dependent setup values (rules 1.7.2, 4.2)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerCountSetup:
    players: int
    certificate_limit: int
    start_money: int
    bidding_tokens: int


SETUP_BY_PLAYER_COUNT: dict[int, PlayerCountSetup] = {
    3: PlayerCountSetup(players=3, certificate_limit=26, start_money=700, bidding_tokens=6),
    4: PlayerCountSetup(players=4, certificate_limit=20, start_money=525, bidding_tokens=5),
    5: PlayerCountSetup(players=5, certificate_limit=16, start_money=420, bidding_tokens=4),
    6: PlayerCountSetup(players=6, certificate_limit=13, start_money=350, bidding_tokens=3),
    7: PlayerCountSetup(players=7, certificate_limit=11, start_money=300, bidding_tokens=3),
}

STARTING_BANK = 12000

# Stock market starting-value spaces available to majors and minors (red-outlined) and the
# minor-only start space (solid red, rule 1.6.3/1.6.4).
MINOR_ONLY_START_PRICE = 50
COMPANY_START_PRICES = [50, 60, 70, 80, 90, 100]  # 50 = minors only
