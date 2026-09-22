"""Stock market grid, transcribed from board.webp (rule 1.6). Logical (row, col)
grid rather than pixel coordinates - row 0 is the topmost printed row (highest
values, £700 "Game End" cell), increasing downward; col 0 is the leftmost printed
column. Not every (row, col) combination has a cell - the printed chart is a
staircase/triangular shape, so absent cells are simply omitted from CELLS.

Movement semantics (which direction "up"/"down" follow along this staircase,
and what the corner curved-arrows mean) are NOT yet encoded here with full
confidence - rule 4.4.4/4.12/5.12 describe up/down movement, but this needs
verification against the physical board before being load-bearing for the
stock-round engine. Treat CELLS as ground truth for values/positions/special
zones; treat movement adjacency as a TODO.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StockCell:
    row: int
    col: int
    value: int
    zone: str | None = None   # "yellow" (cert-limit-exempt, rule 1.6.5) | "minor_start" (solid red £50)
                               # | "start" (red-outlined £60-£100 major/minor start spaces) | None
    game_end: bool = False    # rule 10.1.1: game ends at end of the OR/SR this is reached


# Rows, left column = col 0. Read directly off board.webp (rule 1.6 stock market grid).
_ROWS: list[list[int]] = [
    [550, 600, 650, 700],                                                            # row 0 (topmost)
    [330, 360, 400, 450, 500, 550, 600, 650],                                         # row 1
    [200, 220, 245, 270, 300, 330, 360, 400, 450, 500, 550, 600],                     # row 2
    [70, 80, 90, 100, 110, 120, 135, 150, 165, 180, 200, 220, 245, 270, 300,
     330, 360, 400, 450, 500, 550],                                                   # row 3
    [60, 70, 80, 90, 100, 110, 120, 135, 150, 165, 180, 200, 220, 245, 270,
     300, 330, 360, 400, 450, 500],                                                   # row 4
    [50, 60, 70, 80, 90, 100, 110, 120, 135, 150, 165, 180, 200, 220, 245,
     270, 300, 330],                                                                  # row 5
    [45, 50, 60, 70, 80, 90, 100, 110, 120, 135, 150, 165, 180, 200, 220, 245],        # row 6
    [40, 45, 50, 60, 70, 80, 90, 100, 110, 120, 135, 150, 165, 180],                   # row 7
    [35, 40, 45, 50, 60, 70, 80, 90, 100, 110, 120],                                   # row 8
    [30, 35, 40, 45, 50, 60, 70, 80, 90, 100],                                         # row 9
    [25, 30, 35, 40, 45, 50, 60, 70, 80],                                              # row 10
    [20, 25, 30, 35, 40, 45, 50, 60],                                                  # row 11
    [15, 20, 25, 30, 35, 40, 45],                                                      # row 12
    [10, 15, 20, 25, 30, 35],                                                          # row 13
    [5, 10, 15, 20, 25],                                                               # row 14 (bottommost)
]

# Row/col of each start-price space, keyed by value, for major/minor company
# flotation (rule 1.6.4: red-outlined £60/£70/£80/£90/£100; rule 1.6.3: solid
# red £50 is minor-only). These sit in the single vertical "par" column visible
# in the board.webp crop (5th cell of the row-3 .. row-9 band).
_START_COL = 4  # 0-indexed column within rows 3-9 that holds 110,100,90,80,70,60,50
MINOR_ONLY_START_VALUE = 50
MAJOR_MINOR_START_VALUES = (60, 70, 80, 90, 100)

# Yellow zone (rule 1.6.5): certificates of a company whose price token sits here
# do not count against the certificate limit. Read as the lower-left triangular
# block of the grid (rows 6-14, only the low-value columns). Recorded as
# (row, col) pairs actually shaded yellow on board.webp.
_YELLOW_ZONE_ROW_COL_MAX: dict[int, int] = {
    6: 0,     # row6: only col0 (value 45) is yellow
    7: 1,     # row7: col0-1 (40,45) yellow
    8: 2,
    9: 3,
    10: 4,
    11: 5,
    12: 6,
    13: 5,
    14: 4,
}


def _build_cells() -> list[StockCell]:
    cells: list[StockCell] = []
    for row_idx, values in enumerate(_ROWS):
        for col_idx, value in enumerate(values):
            zone = None
            if value == MINOR_ONLY_START_VALUE and col_idx == _START_COL and row_idx == 9:
                zone = "minor_start"
            elif value in MAJOR_MINOR_START_VALUES and col_idx == _START_COL and 3 <= row_idx <= 9:
                zone = "start"
            elif row_idx in _YELLOW_ZONE_ROW_COL_MAX and col_idx <= _YELLOW_ZONE_ROW_COL_MAX[row_idx]:
                zone = "yellow"
            game_end = value == 700
            cells.append(StockCell(row=row_idx, col=col_idx, value=value, zone=zone, game_end=game_end))
    return cells


STOCK_MARKET_CELLS: list[StockCell] = _build_cells()
STOCK_MARKET_BY_VALUE: dict[int, list[StockCell]] = {}
for _cell in STOCK_MARKET_CELLS:
    STOCK_MARKET_BY_VALUE.setdefault(_cell.value, []).append(_cell)
