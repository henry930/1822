"""Hex map coordinate data, transcribed from map.pdf (300dpi scan) and cross-checked
against rules.pdf where the rulebook gives explicit hex ids.

Coordinate system: flat-top hexes, columns A-Q (17 columns) left to right, rows
numbered locally per the printed board (each hex's row number is read directly off
the board next to it). This matches the ids the rulebook itself uses (e.g. "Edinburgh
(hex H5)", "Mid Wales (hexes F25-F31)").

CONFIDENCE LEVELS - each hex/area entry below is tagged:
  "rules"   - id is stated explicitly in rules.pdf text. Ground truth.
  "map"     - id read directly off a high-res crop of map.pdf, cross-checked against
              a nearby "rules"-confidence anchor. High confidence but not text-verified.
  "approx"  - read from map.pdf but without a nearby anchor to cross-check column
              alignment; treat as a strong best-effort guess, verify against the
              physical board before relying on it for exact adjacency/routing logic.

This file does NOT attempt to enumerate every plain hex on the board (there are
several hundred, many blank/undifferentiated land or sea). It catalogs every hex that
carries game information: cities, towns, off-board areas, terrain-cost hexes,
pre-printed track/labels, and special-rule hexes. Plain yellow-track-eligible land
hexes with no marking are generated separately by the map-grid geometry (not yet
built) once the frontend hex renderer needs them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

HEX_COLUMNS: tuple[str, ...] = tuple("ABCDEFGHIJKLMNOPQ")  # 17 columns, left to right


@dataclass(frozen=True)
class OffBoardArea:
    id: str            # hex id, or a name if it spans multiple hexes (e.g. "Mid Wales")
    name: str
    hexes: tuple[str, ...]   # one or more hex ids this area occupies
    # revenue by phase-color: (yellow, green, brown, grey) - rule 5.11.10
    value_yellow: int
    value_green: int
    value_brown: int
    value_grey: int
    confidence: str = "map"


@dataclass(frozen=True)
class CityHex:
    id: str
    name: str
    label: str | None   # None (unlabeled), "BM", "Y", "S", "C", "T", "L" (London), "EC"
    is_town: bool = False
    home_of_minor: int | None = None
    home_of_major: str | None = None
    destination_of_major: str | None = None
    confidence: str = "map"


@dataclass(frozen=True)
class TerrainHex:
    id: str
    terrain: str        # "river_large" | "river_small" | "estuary" | "rough" | "hill" | "mountain"
    cost: int
    confidence: str = "map"


# ---------------------------------------------------------------------------
# City upgrade revenue table (printed on map.pdf page 1; not in rules.pdf text).
# Revenue for a city hex by its label and phase-color. Off-board areas use
# OffBoardArea.value_* instead; this table is for CITY hexes only.
# ---------------------------------------------------------------------------
CITY_UPGRADE_TABLE: dict[str | None, tuple[int, int, int, int]] = {
    None: (20, 30, 40, 50),    # unlabeled city
    "BM": (40, 50, 60, 80),
    "C": (30, 30, 40, 60),
    "L": (40, 60, 80, 100),    # London
    "S": (20, 30, 40, 60),
    "T": (20, 40, 50, 60),
    "Y": (30, 40, 50, 60),
}

ENGLISH_CHANNEL_HEX_VALUE = 100  # flat, per rule 5.7.18
FRANCE_OFFBOARD_VALUES = (0, 60, 90, 120)  # yellow/green/brown/grey, read off map.pdf

# ---------------------------------------------------------------------------
# Off-board grey areas (rule 1.4.8; values read from map.pdf boxes)
# ---------------------------------------------------------------------------
OFFBOARD_AREAS: list[OffBoardArea] = [
    OffBoardArea("H1", "Aberdeen", ("H1",), 30, 40, 50, 60, confidence="rules"),
    OffBoardArea("Highlands", "Highlands", ("E2", "E3", "E4"), 10, 10, 20, 20, confidence="rules"),
    OffBoardArea("E6", "Glasgow area", ("E6",), 40, 50, 60, 70, confidence="map"),
    OffBoardArea("F23", "Holyhead", ("F23",), 20, 20, 30, 40, confidence="rules"),
    OffBoardArea("MidWales", "Mid Wales", ("F25", "F26", "F27", "F28", "F29", "F30", "F31"),
                 10, 20, 20, 30, confidence="rules"),
    OffBoardArea("F33", "Pontypool", ("F33",), 20, 40, 30, 10, confidence="rules"),
    OffBoardArea("E34", "Merthyr Tydfil", ("E34",), 30, 40, 30, 10, confidence="rules"),
    OffBoardArea("D35-ish", "Fishguard", ("A33",), 10, 20, 30, 40, confidence="approx"),
    OffBoardArea("Cornwall", "Cornwall", ("A41", "A42"), 40, 30, 30, 40, confidence="map"),
    OffBoardArea("France", "France", ("Q44",), *FRANCE_OFFBOARD_VALUES, confidence="map"),
]

# ---------------------------------------------------------------------------
# Named city / town hexes. Minor company homes use the exact ids from
# app.data.minor_companies (rules-confidence). Major company home/destination
# cities below are read from map.pdf and cross-checked against the nearest
# rules-confidence anchor on the same crop.
# ---------------------------------------------------------------------------
CITIES: list[CityHex] = [
    # --- Scotland ---
    CityHex("H1", "Aberdeen", None, home_of_minor=1, destination_of_major="NBR", confidence="rules"),
    CityHex("H5", "Edinburgh", "Y", home_of_minor=3, home_of_major="NBR",
            destination_of_major="NER", confidence="rules"),
    CityHex("E6", "Glasgow", None, home_of_minor=27, home_of_major="CR", confidence="map"),
    CityHex("G12", "Carlisle", None, home_of_minor=28, destination_of_major="CR", confidence="rules"),
    CityHex("F4", "Stirling", None, is_town=True, confidence="approx"),
    CityHex("F5", "Falkirk", None, is_town=True, confidence="approx"),
    CityHex("D4", "Dunfermline", None, is_town=True, confidence="approx"),
    CityHex("E7", "Hamilton", None, is_town=True, confidence="approx"),
    CityHex("E7b", "Coatbridge", None, is_town=True, confidence="approx"),
    CityHex("D11", "Stranraer", None, is_town=True, confidence="approx"),
    CityHex("F11", "Dumfries", None, is_town=True, confidence="approx"),
    CityHex("H12", "Penrith", None, is_town=True, confidence="approx"),
    CityHex("K10", "Newcastle", None, home_of_minor=4, confidence="rules"),
    CityHex("K12", "Durham", None, is_town=True, confidence="approx"),
    CityHex("J15", "Darlington", None, home_of_minor=5, confidence="rules"),
    CityHex("L14", "Middlesbrough", None, is_town=True, confidence="approx"),
    CityHex("N16", "Scarborough", None, is_town=True, confidence="approx"),
    CityHex("G16", "Barrow", None, home_of_minor=6, confidence="rules"),
    CityHex("H17", "Lancaster", None, is_town=True, confidence="approx"),
    CityHex("H19", "Preston", None, is_town=True, confidence="approx"),
    CityHex("H20", "Blackpool", None, is_town=True, confidence="approx"),
    CityHex("H21", "Blackburn", None, is_town=True, confidence="approx"),
    CityHex("H21b", "Burnley", None, is_town=True, confidence="approx"),
    CityHex("G22", "Liverpool", "Y", home_of_major="L&YR", confidence="map"),
    CityHex("H22", "Manchester", "BM", home_of_minor=None, home_of_major="LNWR",
            destination_of_major="L&YR", confidence="map"),
    # Note: LNWR destination is also Manchester (same hex as its 2nd home station).
    CityHex("H23", "Warrington", None, home_of_minor=7, confidence="rules"),
    CityHex("H24", "Chester", None, is_town=True, confidence="approx"),
    CityHex("H24b", "Crewe", None, is_town=True, confidence="approx"),
    CityHex("I25", "Stoke on Trent", None, is_town=True, confidence="approx"),
    CityHex("K24", "Sheffield", None, home_of_minor=8, confidence="rules"),
    CityHex("J20", "Leeds", None, is_town=True, confidence="approx"),
    CityHex("J19", "Bradford", None, is_town=True, confidence="approx"),
    CityHex("K19", "York", None, home_of_major="MR", destination_of_major="NER", confidence="map"),
    CityHex("N21", "Hull", None, home_of_minor=26, confidence="rules"),
    CityHex("N23", "Grimsby", None, home_of_minor=9, confidence="rules"),
    CityHex("M26", "Lincoln", None, is_town=True, confidence="approx"),
    CityHex("I30", "Birmingham", "BM", home_of_minor=10, confidence="rules"),
    CityHex("I29", "Derby", None, home_of_major="MR", confidence="map"),
    CityHex("I28", "Nottingham", None, is_town=True, confidence="approx"),
    CityHex("I31", "Coventry", None, is_town=True, confidence="approx"),
    CityHex("J29", "Leicester", None, is_town=True, confidence="approx"),
    CityHex("M30", "Peterborough", None, home_of_minor=11, confidence="rules"),
    CityHex("P30", "King's Lynn", None, is_town=True, confidence="approx"),
    CityHex("Q30", "Norwich", None, home_of_minor=25, confidence="rules"),
    CityHex("L29", "Northampton", None, is_town=True, confidence="approx"),
    CityHex("N32", "Cambridge", None, is_town=True, confidence="approx"),
    CityHex("P35", "Ipswich", None, home_of_minor=12, confidence="rules"),
    CityHex("N36", "Colchester", None, is_town=True, confidence="approx"),
    # --- Wales / West ---
    CityHex("F23", "Holyhead", None, confidence="rules"),
    CityHex("F28", "Mid Wales", None, home_of_minor=29, confidence="rules"),
    CityHex("G27", "Shrewsbury", None, is_town=True, confidence="approx"),
    CityHex("H32", "Hereford", None, is_town=True, confidence="approx"),
    CityHex("G32", "Gloucester", None, home_of_major="SWR", confidence="map"),
    CityHex("F33", "Pontypool", None, home_of_minor=20, confidence="rules"),
    CityHex("E34", "Merthyr Tydfil", None, home_of_minor=21, confidence="rules"),
    CityHex("F35", "Cardiff", "C", home_of_minor=19, confidence="rules"),
    CityHex("F35b", "Newport", None, is_town=True, confidence="approx"),
    CityHex("G36", "Bristol", "Y", home_of_major="GWR", confidence="map"),
    CityHex("D35", "Swansea", None, home_of_minor=24, confidence="rules"),
    CityHex("D35b", "Oystermouth", None, is_town=True, confidence="approx"),
    CityHex("A33", "Fishguard", None, destination_of_major="SWR", confidence="approx"),
    CityHex("G37", "Bath", None, is_town=True, confidence="approx"),
    CityHex("G37b", "Radstock", None, is_town=True, confidence="approx"),
    CityHex("C38", "Barnstaple", None, is_town=True, confidence="approx"),
    CityHex("D40", "Taunton", None, is_town=True, confidence="approx"),
    CityHex("D41", "Exeter", None, home_of_minor=22, confidence="rules"),
    CityHex("A42", "Cornwall (West Cornwall Railway home)", None, home_of_minor=23, confidence="rules"),
    CityHex("B43", "Plymouth", None, home_of_minor=30, confidence="rules"),
    CityHex("G39", "Dorchester", None, is_town=True, confidence="approx"),
    CityHex("I42", "Bournemouth", None, home_of_minor=18, confidence="rules"),
    CityHex("J41", "Southampton", None, home_of_minor=17, confidence="rules"),
    CityHex("K42", "Portsmouth", "T", is_town=True, confidence="approx"),
    CityHex("H40", "Salisbury", None, is_town=True, confidence="approx"),
    CityHex("L40", "Reading", None, is_town=True, confidence="approx"),
    CityHex("K33", "Oxford", None, is_town=True, confidence="approx"),
    CityHex("L33", "Hertford", None, is_town=True, confidence="approx"),
    # --- London & South East ---
    CityHex("M38", "London", "L", home_of_minor=15, home_of_major="LNWR", confidence="rules"),
    # London also hosts M14 (Metropolitan, optional rondel) and M16 (L&BR, NW station),
    # plus home stations for GWR/LBSCR/SECR (all co-located in the same black hex).
    CityHex("M42", "Brighton", None, destination_of_major="LBSCR", confidence="map"),
    CityHex("O40", "Maidstone", None, home_of_minor=13, confidence="rules"),
    CityHex("N39", "Canterbury", None, is_town=True, confidence="approx"),
    CityHex("N41", "Dover", None, destination_of_major="SECR", confidence="map"),
    CityHex("N42", "Folkestone", None, is_town=True, confidence="approx"),
    CityHex("O43", "English Channel", "EC", confidence="rules"),
]

# ---------------------------------------------------------------------------
# Difficult-terrain hexes (rule 5.7.18). Cost table: river_small=20, river_large=40,
# rough=40, hill=60, mountain=80, estuary crossing=40 (per side, so 80 total to cross).
# Read from map.pdf icons (marsh symbol = river, triangle = hill, double-triangle =
# mountain, domed box = rough). This is a partial catalog of the clearer icons;
# several more river/rough hexes are visible but not individually confirmed here.
# ---------------------------------------------------------------------------
TERRAIN_HEXES: list[TerrainHex] = [
    TerrainHex("I2", "hill", 60, confidence="approx"),   # near Aberdeen
    TerrainHex("J7", "hill", 60, confidence="approx"),
    TerrainHex("K7", "hill", 60, confidence="approx"),
    TerrainHex("H13", "estuary", 40, confidence="map"),  # Solway Firth crossing
    TerrainHex("G14", "rough", 40, confidence="approx"),
    TerrainHex("H15", "hill", 60, confidence="approx"),
    TerrainHex("H18", "mountain", 80, confidence="approx"),
    TerrainHex("I18", "hill", 60, confidence="approx"),
    TerrainHex("I20", "mountain", 80, confidence="approx"),
    TerrainHex("I22", "mountain", 80, confidence="approx"),
    TerrainHex("I24", "rough", 40, confidence="approx"),
    TerrainHex("K25", "hill", 60, confidence="approx"),
    TerrainHex("H30", "rough", 40, confidence="approx"),
    TerrainHex("N22", "estuary", 40, confidence="map"),  # Humber estuary crossing
    TerrainHex("C40", "hill", 60, confidence="approx"),
    TerrainHex("D39", "rough", 40, confidence="approx"),
    TerrainHex("B41", "rough", 40, confidence="approx"),
    TerrainHex("G34", "estuary", 40, confidence="map"),  # Severn estuary (Bristol/Newport)
    TerrainHex("H38", "rough", 40, confidence="approx"),
    TerrainHex("I38", "rough", 40, confidence="approx"),
    TerrainHex("I39", "rough", 40, confidence="approx"),
]

# ---------------------------------------------------------------------------
# Hex-adjacency breaks: red lines printed across certain coastal/estuary edges
# on map.pdf, indicating two visually-adjacent hexes do NOT connect (must route
# around). Confirmed textually for Mid Wales / Holyhead / Pontypool (rule 1.4.9);
# the others are read from the same red-line convention elsewhere on the map and
# should be verified against the physical board.
# ---------------------------------------------------------------------------
BLOCKED_ADJACENCIES: list[tuple[str, str, str]] = [
    ("F23", "F25", "rules"),   # Holyhead <-> Mid Wales (north end)
    ("F31", "F33", "rules"),   # Mid Wales <-> Pontypool (south end)
    ("F11", "H13", "approx"),  # Solway Firth
    ("D4", "F5", "approx"),    # Firth of Forth (Dunfermline/Falkirk area)
    ("G16", "H17", "approx"),  # Morecambe Bay (Barrow/Lancaster)
    ("N22", "N23", "approx"),  # Humber estuary
    ("I42", "K42", "approx"),  # South coast near Bournemouth
]

# ---------------------------------------------------------------------------
# The Merthyr Tydfil <-> Pontypool special connection (rules section 9): a direct
# track link exists between these two specific hexes despite the general Mid-Wales
# blocked adjacency above, but only one train may use it per operating round, and
# it acts as a terminus in both directions (routes cannot pass through).
# ---------------------------------------------------------------------------
MERTHYR_PONTYPOOL_LINK = ("E34", "F33")

LONDON_HEX = "M38"
ENGLISH_CHANNEL_HEX = "O43"
FRANCE_HEX = "Q44"
