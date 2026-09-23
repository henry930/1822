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

    rules_cities: dict[int, str] = {}
    for c in CITIES:
        if c.home_of_minor is None:
            continue
        numbers = c.home_of_minor if isinstance(c.home_of_minor, tuple) else (c.home_of_minor,)
        for n in numbers:
            rules_cities[n] = c.id

    for number, hex_id in rules_cities.items():
        expected = MINOR_COMPANIES_BY_NUMBER[number].home_hex
        # M2's printed home ("E2-4") is a range across the Highlands
        # off-board area, not one hex - E2 is the chosen concrete pick.
        if "-" in expected:
            assert hex_id in expected, f"M{number} hex {hex_id} not part of range {expected}"
        else:
            assert hex_id == expected, f"M{number} hex mismatch: {hex_id} vs {expected}"


def test_every_company_has_a_resolvable_home_hex():
    """A company with no catalogued home (home_hex_for returns None)
    isn't just missing flavor data - reachable_hexes_for_tile_lay treats
    "no stations" as "nothing is reachable, not even this company's own
    home", so it can never legally lay a single tile anywhere. This caught
    a real bug: a city like London/M38 is genuinely the printed home of
    three minors and three majors at once, and the old single-value
    home_of_minor/home_of_major fields could only ever record one of them,
    silently dropping the rest to None."""
    from app.data.major_companies import MAJOR_COMPANIES
    from app.data.minor_companies import BASE_GAME_MINOR_COMPANIES
    from app.engine.operating import home_hex_for

    for major in MAJOR_COMPANIES:
        assert home_hex_for(major.abbr, "major") is not None, f"{major.abbr} has no home hex"
    for minor in BASE_GAME_MINOR_COMPANIES:
        company_id = f"M{minor.number}"
        assert home_hex_for(company_id, "minor") is not None, f"{company_id} has no home hex"


def test_merthyr_pontypool_link_hexes_exist_in_offboard_or_cities():
    known_ids = {c.id for c in CITIES} | {a.id for a in OFFBOARD_AREAS}
    for hex_id in MERTHYR_PONTYPOOL_LINK:
        assert hex_id in known_ids


def test_labelled_hexes_are_never_towns():
    """Every labelled tile (BM/C/EC/L/S/T/Y) in app.data.tiles is a city
    shape - labels only exist to pick which big-city tile geometry a hex
    takes, so a catalogued hex can't be both is_town=True and carry one of
    these labels. Caught a real data bug: Portsmouth/K42 was marked
    is_town=True with label="T", but no T-labelled tile (405/X10/X16) has a
    town - that hex could never have legally taken any tile."""
    from app.data.tiles import TILE_SPECS, parse_tile_code

    labels_with_city_shape = set()
    for spec in TILE_SPECS:
        parsed = parse_tile_code(spec.id, spec.color, spec.count, spec.code)
        if parsed.label and parsed.cities:
            labels_with_city_shape.add(parsed.label)

    for c in CITIES:
        if c.label in labels_with_city_shape:
            assert not c.is_town, (
                f"{c.id} {c.name!r} is marked is_town=True but label={c.label!r} "
                "only appears on city-shaped tiles"
            )
