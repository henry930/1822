"""Train types available in 1822 (rules section 5.10)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TrainType:
    code: str          # "L", "2", "3", ... "7", "E"
    cost: int
    count: int | None  # None = unlimited (shares a pool with its double-sided partner)
    rusted_by: str | None  # code of train type whose purchase/export rusts this one; None = never rusts


# L and 2 share one pool of 22 double-sided cards; 7 and E share a pool of 16 double-sided cards.
TRAIN_TYPES: list[TrainType] = [
    TrainType(code="L", cost=60, count=22, rusted_by="3"),
    TrainType(code="2", cost=120, count=22, rusted_by="4"),
    TrainType(code="3", cost=200, count=9, rusted_by="6"),
    TrainType(code="4", cost=300, count=6, rusted_by="7"),
    TrainType(code="5", cost=500, count=3, rusted_by=None),
    TrainType(code="6", cost=600, count=3, rusted_by=None),
    TrainType(code="7", cost=750, count=16, rusted_by=None),
    TrainType(code="E", cost=1000, count=16, rusted_by=None),
]

TRAIN_TYPES_BY_CODE = {t.code: t for t in TRAIN_TYPES}

# L-trains may be upgraded (flipped) to 2-trains for this cost (5.13.9 / 5.10.1).
L_TO_2_UPGRADE_COST = 80
