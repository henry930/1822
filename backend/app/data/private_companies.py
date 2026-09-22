"""Private company table (rules Company Tables, p.37-39). Base game uses P1-P18;
P19-P21 belong to the 1822+ expansion."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PrivateCompany:
    number: int
    name: str
    abbr: str
    revenue: str          # face revenue; some are phase-dependent strings e.g. "£10x phase"
    acquirable_by_minor: bool
    acquirable_from_phase: int | str  # int phase number, or "X" (P16: cannot be acquired)
    expansion: bool       # True if only in 1822+
    notes: str


PRIVATE_COMPANIES: list[PrivateCompany] = [
    PrivateCompany(1, "Butterley Engineering Company", "BEC", "£5", False, 5, False,
                    "Acts as a normal 5-train once acquired. Not usable before Phase 5."),
    PrivateCompany(2, "Middleton Railway", "MtonR", "£10", True, 2, False,
                    "Remove a Town: place a plain yellow tile on an undeveloped town hex, or upgrade "
                    "a town tile one color, even off the normal color track. Closes when used."),
    PrivateCompany(3, "Shrewsbury and Hereford Railway", "S&HR", "£0", False, 2, False,
                    "Permanent 2-Train (2P). Cannot be sold to another company, doesn't count "
                    "against train limit or satisfy mandatory train ownership. Does not close."),
    PrivateCompany(4, "South Devon Railway", "SDR", "£0", False, 2, False,
                    "Permanent 2-Train (2P). Same as P3."),
    PrivateCompany(5, "London, Chatham and Dover Railway", "LC&DR", "£10", False, 3, False,
                    "English Channel: place a free exchange station token in the English Channel "
                    "(no route required). May upgrade+token in one action. Does not close."),
    PrivateCompany(6, "Leeds & Selby Railway", "L&SR", "£10", False, 3, False,
                    "Mail Contract: receive half the base value of the start/end stations of one "
                    "train run into treasury after running trains. Does not close."),
    PrivateCompany(7, "Shrewsbury and Birmingham Railway", "S&BR", "£10", False, 3, False,
                    "Mail Contract. Same as P6."),
    PrivateCompany(8, "Edinburgh and Glasgow Railway", "E&GR", "£10", True, 3, False,
                    "Mountain/Hill Discount: free tile lay in rough/hill/mountain terrain (closes), "
                    "or £20 discount on all hill/mountain lays (does not close)."),
    PrivateCompany(9, "Midland and Great Northern Joint Railway", "M&GNR", "£10", True, 3, False,
                    "Declare 2x cash holding for turn order (player); or pays £20/£40/£60 "
                    "(green/brown/grey) revenue to owning company. Does not close."),
    PrivateCompany(10, "Glasgow and South-Western Railway", "G&SWR", "£10", True, 3, False,
                    "River/Estuary Discount: two discount tokens for estuary crossings, plus £10 "
                    "discount on river terrain until closed."),
    PrivateCompany(11, "Bristol & Exeter Railway", "B&ER", "£10", True, 2, False,
                    "Advanced Tile Lay: lay a tile one color ahead of the currently available color. "
                    "Does not close until power is exercised."),
    PrivateCompany(12, "Leicester & Swannington Railway", "L&SR", "£10", True, 3, False,
                    "Extra Tile Lay: one additional yellow tile (two for majors) or upgrade. "
                    "Does not close until power is exercised."),
    PrivateCompany(13, "York, Newcastle and Berwick Railway", "YN&BR", "£10", True, 5, False,
                    "Pullman car: converts a normal train into a '+' train. Permanent, cannot be sold."),
    PrivateCompany(14, "Kilmarnock and Troon Railway", "K&TR", "£10", True, 5, False,
                    "Pullman car. Same as P13."),
    PrivateCompany(15, "Highland Railway", "HR", "£10x phase", True, 2, False,
                    "Pays owning player £10x phase revenue; accrues £10x phase treasury credit "
                    "for the acquiring company. Closes at start of Phase 7 if not acquired."),
    PrivateCompany(16, "Off-Shore Tax Haven", "TaxHaven", "£0", False, "X", False,
                    "Tax Haven: player-funded off-board share holding; does not count toward the "
                    "60% ownership limit or (usually) certificate limit. Cannot be acquired by a "
                    "company. Cannot hold the LNWR director's certificate."),
    PrivateCompany(17, "Lancashire Union Railway", "LUR", "£10", False, 2, False,
                    "Move Card: move a concession/private/minor certificate to the top or bottom of "
                    "its stack. Closes when exercised."),
    PrivateCompany(18, "Cromford and High Peak Railway", "CHPR", "£10", False, 5, False,
                    "Station Marker Swap: move a token between exchange and available token areas. "
                    "Closes when exercised."),
    PrivateCompany(19, "Avonside Engine Company", "AEC", "£0", True, 1, True,
                    "Permanent L-Train (LP-train). 1822+ expansion only."),
    PrivateCompany(20, "Canterbury and Whitstable Railway", "C&WR", "£5x phase", True, 3, True,
                    "Pays £5x phase revenue and treasury credit; closes at start of Phase 7 if not "
                    "acquired. 1822+ expansion only."),
    PrivateCompany(21, "Humber Suspension Bridge Company", "HSBC", "£10", True, 2, True,
                    "Grimsby/Hull Bridge: lay yellow tiles connecting Grimsby and Hull across the "
                    "Humber estuary. 1822+ expansion only."),
]

PRIVATE_COMPANIES_BY_NUMBER = {c.number: c for c in PRIVATE_COMPANIES}

BASE_GAME_PRIVATE_COMPANIES = [c for c in PRIVATE_COMPANIES if not c.expansion]
