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

    # "b"-suffixed secondary-town ids parse leniently instead of being dropped.
    coatbridge = next(c for c in data["cities"] if c["id"] == "E7b")
    assert coatbridge["name"] == "Coatbridge"
    assert coatbridge["dx"] > 0

    # Off-board areas are exploded to their real per-hex ids, not the area's
    # own (sometimes non-hex) id like "Highlands" or "MidWales".
    assert all(h["id"] != "Highlands" for h in data["offboard"])
    highlands_hexes = [h for h in data["offboard"] if h["name"] == "Highlands"]
    assert {h["id"] for h in highlands_hexes} == {"E2", "E3", "E4"}
