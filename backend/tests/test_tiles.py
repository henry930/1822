import json
from pathlib import Path

from app.data.tiles import TILE_SPECS, UNLIMITED, parsed_tiles

FRONTEND_MANIFEST = Path(__file__).resolve().parents[2] / "frontend/src/assets/tiles/manifest.json"


def test_all_tiles_parse_without_error():
    parsed = parsed_tiles()
    assert len(parsed) == len(TILE_SPECS) == 61


def test_tile_color_counts_match_rulebook_tile_manifest():
    by_color = {"yellow": 0, "green": 0, "brown": 0, "gray": 0}
    for t in TILE_SPECS:
        by_color[t.color] += 1
    assert by_color == {"yellow": 14, "green": 20, "brown": 15, "gray": 12}


def test_junction_tiles_have_no_revenue_lots():
    parsed = parsed_tiles()
    for t in TILE_SPECS:
        p = parsed[t.id]
        if p.junction:
            assert not p.cities and not p.towns


def test_matches_frontend_manifest_ids_and_counts():
    data = json.loads(FRONTEND_MANIFEST.read_text())
    frontend_by_id = {d["id"]: d for d in data}
    assert set(frontend_by_id) == {t.id for t in TILE_SPECS}
    for t in TILE_SPECS:
        expected_count = "unlimited" if t.count == UNLIMITED else t.count
        assert frontend_by_id[t.id]["count"] == expected_count, t.id
        assert frontend_by_id[t.id]["color"] == t.color, t.id
