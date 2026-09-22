"""Train types available in 1822 (rules section 5.10)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TrainType:
    code: str          # "L", "2", "3", ... "7", "E"
    cost: int
    count: int | None  # None = unlimited (shares a pool with its double-sided partner)
    rusted_by: str | None  # code of train type whose purchase/export rusts this one; None = never rusts
    name: str          # locomotive name/class printed on the physical card (train.webp)


# L and 2 share one pool of 22 double-sided cards; 7 and E share a pool of 16 double-sided cards.
# Names transcribed directly from the photographed cards (train.webp) - do not
# invent/guess a plausible-sounding locomotive name here; if a name looks
# unverified, check it against that photo before trusting it.
TRAIN_TYPES: list[TrainType] = [
    TrainType(code="L", cost=60, count=22, rusted_by="3", name="Stephenson's Rocket 2-2-0"),
    TrainType(code="2", cost=120, count=22, rusted_by="4", name="Caledonian Railway Connor Single (1862)"),
    TrainType(code="3", cost=200, count=9, rusted_by="6", name="Highland Railway Dingwall & Skye 4-4-0"),
    TrainType(code="4", cost=300, count=6, rusted_by="7", name="North British Railway Class H 4-4-2"),
    TrainType(code="5", cost=500, count=3, rusted_by=None, name="LNWR Claughton Class 2-3-0"),
    TrainType(code="6", cost=600, count=3, rusted_by=None,
              name="London Midland and Scottish Princess Royal Class 2-3-1"),
    TrainType(code="7", cost=750, count=16, rusted_by=None, name="Class 37 BR Co-Co Diesel Electric"),
    TrainType(code="E", cost=1000, count=16, rusted_by=None, name="Class 90 'Vice Admiral Lord Nelson'"),
]

TRAIN_TYPES_BY_CODE = {t.code: t for t in TRAIN_TYPES}

# L-trains may be upgraded (flipped) to 2-trains for this cost (5.13.9 / 5.10.1).
L_TO_2_UPGRADE_COST = 80
