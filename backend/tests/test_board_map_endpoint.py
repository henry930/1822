from fastapi.testclient import TestClient

from app.main import app


def test_board_map_returns_positioned_hex_catalog():
    client = TestClient(app)
    resp = client.get("/board/map")
    assert resp.status_code == 200
    data = resp.json()

    assert data["columns"][0] == "A"
    assert len(data["cities"]) > 50
    assert len(data["offboard"]) > 0
    assert len(data["terrain"]) > 0

    aberdeen = next(c for c in data["cities"] if c["id"] == "H1")
    assert aberdeen["name"] == "Aberdeen"
    assert aberdeen["col"] == 7  # H is the 8th column (0-indexed 7)
    assert aberdeen["row"] == 1
    assert aberdeen["town_count"] == 1
    assert aberdeen["city_count"] == 1
    # Aberdeen is also catalogued as an off-board revenue area - the two
    # aren't mutually exclusive (see app.data.hex_map.CityHex's docstring).
    assert any(h["id"] == "H1" for h in data["offboard"])

    london = next(c for c in data["cities"] if c["id"] == "M38")
    assert london["city_count"] == 6  # X21/X22/X23 each print six cities on this hex

    assert "blocked_adjacencies" in data
    assert any(b["hex_a"] == "F23" and b["hex_b"] == "F25" for b in data["blocked_adjacencies"])
    assert data["edge_tolls"] == []  # none catalogued yet

    # "b"-suffixed secondary-town ids parse leniently instead of being dropped.
    coatbridge = next(c for c in data["cities"] if c["id"] == "E7b")
    assert coatbridge["name"] == "Coatbridge"
    assert coatbridge["dx"] > 0

    # Off-board areas are exploded to their real per-hex ids, not the area's
    # own (sometimes non-hex) id like "Highlands" or "MidWales".
    assert all(h["id"] != "Highlands" for h in data["offboard"])
    highlands_hexes = [h for h in data["offboard"] if h["name"] == "Highlands"]
    assert {h["id"] for h in highlands_hexes} == {"E2", "E3", "E4"}
