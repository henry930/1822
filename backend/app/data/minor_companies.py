"""Minor company table (rules Company Tables, p.36). M1-M24 are base game;
M25-M30 belong to the 1822+ expansion."""
from dataclasses import dataclass


@dataclass(frozen=True)
class MinorCompany:
    number: int
    name: str
    abbr: str
    home_location: str
    home_hex: str
    expansion: bool


MINOR_COMPANIES: list[MinorCompany] = [
    MinorCompany(1, "Great North of Scotland Railway", "GNoSR", "Aberdeen", "H1", False),
    MinorCompany(2, "Lanarkshire & Dunbartonshire Railway", "L&DR", "Highlands", "E2-4", False),
    MinorCompany(3, "Edinburgh & Dalkeith Railway", "E&DR", "Edinburgh", "H5", False),
    MinorCompany(4, "Newcastle & North Shields Railway", "N&NSR", "Newcastle", "K10", False),
    MinorCompany(5, "Stockton and Darlington Railway", "S&DR", "Darlington", "J15", False),
    MinorCompany(6, "Furness Railway", "FR", "Barrow", "G16", False),
    MinorCompany(7, "Warrington & Newton Railway", "W&NR", "Warrington", "H23", False),
    MinorCompany(8, "Manchester, Sheffield & Lincolnshire Railway", "MS&LR", "Sheffield", "K24", False),
    MinorCompany(9, "East Lincolnshire Railway", "ELR", "Grimsby", "N23", False),
    MinorCompany(10, "Grand Junction Railway", "GJR", "Birmingham", "I30", False),
    MinorCompany(11, "Great Northern Railway", "GNR", "Peterborough", "M30", False),
    MinorCompany(12, "Eastern Union Railway", "EUR", "Ipswich", "P35", False),
    MinorCompany(13, "Headcorn & Maidstone Junction Light Railway", "H&MJLR", "Maidstone", "O40", False),
    MinorCompany(14, "Metropolitan Railway", "MetR", "London (Optional)", "M38", False),
    MinorCompany(15, "London, Tilbury & Southend Railway", "LT&SR", "London (NE)", "M38", False),
    MinorCompany(16, "London & Birmingham Railway", "L&BR", "London (NW)", "M38", False),
    MinorCompany(17, "London & Southampton Railway", "L&SR", "Southampton", "J41", False),
    MinorCompany(18, "Somerset & Dorset Joint Railway", "S&DJR", "Bournemouth", "I42", False),
    MinorCompany(19, "Penarth Harbour & Dock Railway Company", "PH&DRC", "Cardiff", "F35", False),
    MinorCompany(20, "Monmouthshire Railway & Canal Company", "MR&CC", "Pontypool", "F33", False),
    MinorCompany(21, "Taff Vale Railway", "TVR", "Merthyr Tydfil", "E34", False),
    MinorCompany(22, "Exeter and Crediton Railway", "E&CR", "Exeter", "D41", False),
    MinorCompany(23, "West Cornwall Railway", "WCR", "Plymouth", "A42", False),
    MinorCompany(24, "Swansea and Mumbles Railway", "S&MR", "Swansea", "D35", False),
    MinorCompany(25, "Yarmouth & Norwich Railway", "Y&NR", "Norwich", "Q30", True),
    MinorCompany(26, "Hull and Selby Railway", "H&SR", "Hull", "N21", True),
    MinorCompany(27, "City of Glasgow Union Railway", "CGR", "Glasgow", "E6", True),
    MinorCompany(28, "Maryport and Carlisle Railway", "M&CR", "Carlisle", "G12", True),
    MinorCompany(29, "Shropshire and Montgomeryshire Railway", "S&MR", "Mid Wales", "F28", True),
    MinorCompany(30, "Plymouth and Dartmoor Railway", "P&DR", "Plymouth", "B43", True),
]

MINOR_COMPANIES_BY_NUMBER = {c.number: c for c in MINOR_COMPANIES}

BASE_GAME_MINOR_COMPANIES = [c for c in MINOR_COMPANIES if not c.expansion]

# M24 (S&MR) is always removed from the shuffled minor stack and placed on top (rule 1.7.5).
# M14 (MetR) is the only minor allowed to place its home station on the off-board London rondel,
# which costs £20 and counts as its track-laying step (see rules section 7).
FIXED_TOP_OF_STACK_MINOR = 24
