"""Game phase table (rules section 2)."""
from dataclasses import dataclass
from enum import IntEnum


class TileColor(IntEnum):
    YELLOW = 1
    GREEN = 2
    BROWN = 3
    GREY = 4


@dataclass(frozen=True)
class Phase:
    number: int
    triggered_by: str
    trains_rusted: str | None       # train code rusted when this phase begins
    minor_train_limit: int
    major_train_limit: int
    buy_trains_from_other_companies: bool
    operating_rounds_per_stock_round: int
    max_tile_color: TileColor
    offboard_value_index: int       # 0=yellow,1=green,2=brown,3=grey value used for off-board revenue
    major_tile_lay: str             # description of major company tile-lay allowance
    minor_tile_lay: str
    minor_float_rule: str
    minor_acquisition: str          # "none" | "major_only" | "major_or_bidbox"
    concession_rule: str            # "not_convertible" | "convertible_discount" | "removed"
    major_flotation_rule: str       # "not_possible" | "on_concession_conversion" | "on_50pct_sold"
    capitalisation: str             # "not_applicable" | "incremental" | "full"


PHASES: list[Phase] = [
    Phase(
        number=1, triggered_by="Game start", trains_rusted=None,
        minor_train_limit=2, major_train_limit=4,
        buy_trains_from_other_companies=False,
        operating_rounds_per_stock_round=1,
        max_tile_color=TileColor.YELLOW, offboard_value_index=0,
        major_tile_lay="none", minor_tile_lay="1 yellow",
        minor_float_rule="fixed_50", minor_acquisition="none",
        concession_rule="not_convertible", major_flotation_rule="not_possible",
        capitalisation="not_applicable",
    ),
    Phase(
        number=2, triggered_by="First L-train converted to 2-train, or first 2-train bought",
        trains_rusted=None,
        minor_train_limit=2, major_train_limit=4,
        buy_trains_from_other_companies=False,
        operating_rounds_per_stock_round=2,
        max_tile_color=TileColor.YELLOW, offboard_value_index=0,
        major_tile_lay="1 yellow", minor_tile_lay="1 yellow",
        minor_float_rule="bid_half_capital_2x", minor_acquisition="major_only",
        concession_rule="convertible_discount", major_flotation_rule="on_concession_conversion",
        capitalisation="incremental",
    ),
    Phase(
        number=3, triggered_by="First 3-train bought", trains_rusted="L",
        minor_train_limit=2, major_train_limit=4,
        buy_trains_from_other_companies=True,
        operating_rounds_per_stock_round=2,
        max_tile_color=TileColor.GREEN, offboard_value_index=1,
        major_tile_lay="2 yellow or 1 upgrade", minor_tile_lay="1 yellow or 1 green upgrade",
        minor_float_rule="bid_half_capital_sum_bid", minor_acquisition="major_only",
        concession_rule="convertible_discount", major_flotation_rule="on_concession_conversion",
        capitalisation="incremental",
    ),
    Phase(
        number=4, triggered_by="First 4-train bought", trains_rusted="2",
        minor_train_limit=1, major_train_limit=3,
        buy_trains_from_other_companies=True,
        operating_rounds_per_stock_round=2,
        max_tile_color=TileColor.GREEN, offboard_value_index=1,
        major_tile_lay="2 yellow or 1 upgrade", minor_tile_lay="1 yellow or 1 green upgrade",
        minor_float_rule="bid_half_capital_sum_bid", minor_acquisition="major_only",
        concession_rule="convertible_discount", major_flotation_rule="on_concession_conversion",
        capitalisation="incremental",
    ),
    Phase(
        number=5, triggered_by="First 5-train bought", trains_rusted=None,
        minor_train_limit=1, major_train_limit=2,
        buy_trains_from_other_companies=True,
        operating_rounds_per_stock_round=2,
        max_tile_color=TileColor.BROWN, offboard_value_index=2,
        major_tile_lay="2 yellow or 1 upgrade", minor_tile_lay="1 yellow or 1 green upgrade",
        minor_float_rule="bid_half_capital_sum_bid", minor_acquisition="major_or_bidbox",
        concession_rule="removed", major_flotation_rule="on_50pct_sold",
        capitalisation="incremental",
    ),
    Phase(
        number=6, triggered_by="First 6-train bought", trains_rusted="3",
        minor_train_limit=1, major_train_limit=2,
        buy_trains_from_other_companies=True,
        operating_rounds_per_stock_round=2,
        max_tile_color=TileColor.BROWN, offboard_value_index=2,
        major_tile_lay="2 yellow or 1 upgrade", minor_tile_lay="1 yellow or 1 green upgrade",
        minor_float_rule="bid_half_capital_sum_bid", minor_acquisition="major_or_bidbox",
        concession_rule="removed", major_flotation_rule="on_50pct_sold",
        capitalisation="full",
    ),
    Phase(
        number=7, triggered_by="First 7-train or E-train bought", trains_rusted="4",
        minor_train_limit=1, major_train_limit=2,
        buy_trains_from_other_companies=True,
        operating_rounds_per_stock_round=2,
        max_tile_color=TileColor.GREY, offboard_value_index=3,
        major_tile_lay="2 yellow or 1 upgrade", minor_tile_lay="1 yellow or 1 green upgrade",
        minor_float_rule="bid_half_capital_sum_bid", minor_acquisition="major_or_bidbox",
        concession_rule="removed", major_flotation_rule="on_50pct_sold",
        capitalisation="full",
    ),
]

PHASES_BY_NUMBER = {p.number: p for p in PHASES}
