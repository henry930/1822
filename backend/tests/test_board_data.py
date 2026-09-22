from app.data.bid_box_tracks import CONCESSION_MINOR_LOOP, PRIVATE_LOOP
from app.data.hex_map import CITIES, MERTHYR_PONTYPOOL_LINK, OFFBOARD_AREAS
from app.data.stock_market import (
    MAJOR_MINOR_START_VALUES,
    MINOR_ONLY_START_VALUE,
    STOCK_MARKET_BY_VALUE,
    STOCK_MARKET_CELLS,
)


def test_stock_market_par_column_is_a_single_vertical_line():
    for value in MAJOR_MINOR_START_VALUES:
        cells = [c for c in STOCK_MARKET_BY_VALUE[value] if c.zone == "start"]
        assert len(cells) == 1, f"expected exactly one 'start' cell for £{value}"
    minor_cells = [c for c in STOCK_MARKET_BY_VALUE[MINOR_ONLY_START_VALUE] if c.zone == "minor_start"]
    assert len(minor_cells) == 1
    assert minor_cells[0].value == 50


def test_stock_market_game_end_cell_present():
    assert any(c.game_end for c in STOCK_MARKET_CELLS)


def test_bid_box_loops_are_20_cells_each():
    assert len(CONCESSION_MINOR_LOOP) == 20
    assert CONCESSION_MINOR_LOOP[0] == 100
    assert CONCESSION_MINOR_LOOP[-1] == 195
    assert len(PRIVATE_LOOP) == 20
    assert PRIVATE_LOOP[0] == 0
    assert PRIVATE_LOOP[-1] == 95


def test_hex_ids_are_unique():
    ids = [c.id for c in CITIES]
    assert len(ids) == len(set(ids)), "duplicate hex ids in CITIES"


def test_rules_confidence_hexes_match_minor_company_table():
    from app.data.minor_companies import MINOR_COMPANIES_BY_NUMBER

    rules_cities = {c.home_of_minor: c.id for c in CITIES if c.home_of_minor is not None}
    for number, hex_id in rules_cities.items():
        expected = MINOR_COMPANIES_BY_NUMBER[number].home_hex
        assert hex_id == expected, f"M{number} hex mismatch: {hex_id} vs {expected}"


def test_merthyr_pontypool_link_hexes_exist_in_offboard_or_cities():
    known_ids = {c.id for c in CITIES} | {a.id for a in OFFBOARD_AREAS}
    for hex_id in MERTHYR_PONTYPOOL_LINK:
        assert hex_id in known_ids
