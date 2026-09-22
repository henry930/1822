"""Core mutable game-state models for a running 1822 game.

These are plain, serializable dataclasses representing "the state of the world" —
separate from the rules/actions logic in the other engine modules, and separate from
the FastAPI/WebSocket transport layer. Anything a client needs to render the game
should be derivable from a GameState instance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RoundType(str, Enum):
    STOCK = "stock"
    OPERATING = "operating"


class CompanyKind(str, Enum):
    PRIVATE = "private"
    MINOR = "minor"
    MAJOR = "major"


@dataclass
class Player:
    id: str
    name: str
    cash: int = 0
    loans: int = 0
    # certificates: company_id -> number of 10% shares held (director's cert of a major
    # counts as 2; a minor's director's cert counts as the whole 50% block, tracked as 1 unit
    # of "MinorState.owner").
    shares: dict[str, int] = field(default_factory=dict)
    private_companies: list[int] = field(default_factory=list)  # private company numbers owned
    tax_haven_shares: dict[str, int] = field(default_factory=dict)  # P16 charter holdings


@dataclass
class BidBoxItem:
    """A single certificate sitting in a numbered bidding box."""
    kind: str          # "concession" | "minor" | "private"
    ref: int           # major company index / minor number / private number
    bids: dict[str, int] = field(default_factory=dict)  # player_id -> current bid amount


@dataclass
class PrivateCompanyState:
    number: int
    owner_player_id: str | None = None
    owner_company_id: str | None = None  # set once acquired by a minor/major
    closed: bool = False
    treasury_credit: int = 0  # for P15/P20 style accruing revenue


@dataclass
class MinorCompanyState:
    number: int
    company_id: str  # e.g. "M19"
    director_player_id: str | None = None
    floated: bool = False
    share_price: int | None = None
    treasury: int = 0
    trains: list[str] = field(default_factory=list)
    private_companies: list[int] = field(default_factory=list)
    home_token_placed: bool = False
    acquired_by_major: str | None = None
    removed: bool = False  # taken out of play (acquired, or unsold in bid box 1)


@dataclass
class MajorCompanyState:
    abbr: str
    director_player_id: str | None = None
    floated: bool = False
    concession_holder_player_id: str | None = None
    concession_converted: bool = False
    share_price: int | None = None
    treasury: int = 0
    trains: list[str] = field(default_factory=list)
    private_companies: list[int] = field(default_factory=list)
    home_token_placed: bool = False
    destination_token_placed: bool = False
    stations_available: int = 1     # "available" (non home/destination/exchange) tokens left
    stations_exchange: int = 0      # tokens reserved for minor-acquisition exchanges
    tokens_on_map: list[str] = field(default_factory=list)  # hex ids with a station token
    shares_in_treasury: int = 0     # count of 10% certs (director's cert = 2) held by company
    shares_in_bank_pool: int = 0


@dataclass
class BankState:
    cash: int = 12000
    train_pool: dict[str, int] = field(default_factory=dict)  # code -> count remaining to buy
    discarded_trains: list[str] = field(default_factory=list)  # bank pool trains


@dataclass
class StockMarketToken:
    company_id: str
    price: int


@dataclass
class GameState:
    game_id: str
    player_order: list[str] = field(default_factory=list)
    players: dict[str, Player] = field(default_factory=dict)
    bank: BankState = field(default_factory=BankState)

    phase: int = 1
    round_type: RoundType = RoundType.STOCK
    round_number: int = 1
    operating_round_index: int = 0  # which OR within the current set (0-based)
    priority_deal_player_id: str | None = None
    active_player_id: str | None = None

    privates: dict[int, PrivateCompanyState] = field(default_factory=dict)
    minors: dict[str, MinorCompanyState] = field(default_factory=dict)
    majors: dict[str, MajorCompanyState] = field(default_factory=dict)

    concession_bid_boxes: list[BidBoxItem | None] = field(default_factory=list)
    minor_bid_boxes: list[BidBoxItem | None] = field(default_factory=list)
    private_bid_boxes: list[BidBoxItem | None] = field(default_factory=list)

    concession_stack: list[str] = field(default_factory=list)   # major abbrs, draw order
    minor_stack: list[int] = field(default_factory=list)        # minor numbers, draw order
    private_stack: list[int] = field(default_factory=list)      # private numbers, draw order

    stock_market: dict[str, int] = field(default_factory=dict)  # company_id -> price
    stock_market_stack_order: dict[int, list[str]] = field(default_factory=dict)  # price -> [company_ids] top-first

    consecutive_passes: int = 0
    game_over: bool = False
    log: list[str] = field(default_factory=list)
