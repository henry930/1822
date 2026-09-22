from fastapi.testclient import TestClient

from app.main import app


def _create_and_start(client, names):
    room_id = client.post("/rooms").json()["room_id"]
    for name in names:
        client.post(f"/rooms/{room_id}/join", json={"name": name})
    client.post(f"/rooms/{room_id}/start")
    return room_id


def test_tile_lay_options_returns_full_report_for_live_room():
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])

    resp = client.get(f"/rooms/{room_id}/tile_lay_options", params={"hex_id": "Z1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["hex_id"] == "Z1"
    assert data["phase"] == 1
    assert data["company_kind"] == "major"
    assert len(data["report"]) > 300  # 61 tiles x 6 rotations

    yellow_valid = [r for r in data["report"] if r["tile_id"] == "3" and r["rotation"] == 0]
    assert yellow_valid[0]["valid"] is True
    green_invalid = [r for r in data["report"] if r["tile_id"] == "141" and r["rotation"] == 0]
    assert green_invalid[0]["valid"] is False
    assert green_invalid[0]["reason"]


def test_tile_lay_options_rejects_bad_company_kind():
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])
    resp = client.get(f"/rooms/{room_id}/tile_lay_options", params={"hex_id": "Z1", "company_kind": "bogus"})
    assert resp.status_code == 400


def test_tile_lay_options_404s_for_unknown_room():
    client = TestClient(app)
    resp = client.get("/rooms/doesnotexist/tile_lay_options", params={"hex_id": "Z1"})
    assert resp.status_code == 404


def test_tile_lay_options_400s_before_game_start():
    client = TestClient(app)
    room_id = client.post("/rooms").json()["room_id"]
    resp = client.get(f"/rooms/{room_id}/tile_lay_options", params={"hex_id": "Z1"})
    assert resp.status_code == 400
