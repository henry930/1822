"""Major company table (rules Company Tables, p.40)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class MajorCompany:
    abbr: str
    name: str
    home_location: str
    destination: str
    station_tokens: int  # LNWR has 9 (2 home stations + destination + 6 others); others have 8


MAJOR_COMPANIES: list[MajorCompany] = [
    MajorCompany("LNWR", "London and North West Railway", "London (N) & Manchester", "Manchester", 9),
    MajorCompany("GWR", "Great Western Railway", "London (SW)", "Bristol", 8),
    MajorCompany("LBSCR", "London, Brighton and South Coast Railway", "London (S)", "Brighton", 8),
    MajorCompany("SECR", "South Eastern & Chatham Railway", "London (SE)", "Dover", 8),
    MajorCompany("CR", "Caledonian Railway", "Glasgow", "Carlisle", 8),
    MajorCompany("MR", "Midland Railway", "Derby", "York", 8),
    MajorCompany("L&YR", "Lancashire & Yorkshire Railway", "Liverpool", "Manchester", 8),
    MajorCompany("NBR", "North British Railway", "Edinburgh", "Aberdeen", 8),
    MajorCompany("SWR", "South Wales Railway", "Gloucester", "Fishguard", 8),
    MajorCompany("NER", "North Eastern Railway", "York", "Edinburgh", 8),
]

MAJOR_COMPANIES_BY_ABBR = {c.abbr: c for c in MAJOR_COMPANIES}

# The LNWR's director's certificate represents 10% (not 20%) of a 10-certificate company,
# and it starts with both its home (London N) and destination (Manchester) stations in play
# (rules 3.3.2, 3.3.7, 5.5.2, 6.1... / company tables footnote).
LNWR_ABBR = "LNWR"
