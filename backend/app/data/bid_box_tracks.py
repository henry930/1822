"""Bid-box surrounding price/value tracks, transcribed from board.webp.

Each of the 7 right-side boxes (3 Concession + 4 Minor Company) and 3 left-side
boxes (Private Company) is printed as a labelled card surrounded by a 20-cell
loop track running clockwise from its face-value starting cell. These loops are
where a marker/token can be placed once that box's certificate is bought, to
track the price paid / share value, per rule 4.10 and section 1.6.

Concession & Minor Company boxes: loop runs 100 -> 195 in steps of 5 (20 cells),
starting cell (100) is the hashed/circled "face value" space.

Private Company boxes: loop runs 0 -> 95 in steps of 5 (20 cells), starting cell
(0, hashed/circled) is the private company face value (always £0, rule 3.1.3).
"""
from __future__ import annotations

CONCESSION_MINOR_LOOP: list[int] = [100 + 5 * i for i in range(20)]  # 100..195
PRIVATE_LOOP: list[int] = [5 * i for i in range(20)]                 # 0..95

CONCESSION_BOX_IDS = ["Concession 1", "Concession 2", "Concession 3"]
MINOR_BOX_IDS = ["Minor Company 1", "Minor Company 2", "Minor Company 3", "Minor Company 4"]
PRIVATE_BOX_IDS = ["Private Company 1", "Private Company 2", "Private Company 3"]
