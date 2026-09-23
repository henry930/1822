from fastapi.testclient import TestClient

from app.main import app


def _create_and_start(client, names):
    room_id = client.post("/rooms").json()["room_id"]
    for name in names:
        client.post(f"/rooms/{room_id}/join", json={"name": name})
    client.post(f"/rooms/{room_id}/start")
    return room_id


def test_debug_force_tile_lay_places_on_home_hex_with_no_operating_round():
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])

    resp = client.post(
        f"/rooms/{room_id}/debug/force_tile_lay",
        json={"hex_id": "H1", "tile_id": "9", "rotation": 0, "company_id": "M1", "company_kind": "minor"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "hex_id": "H1", "tile_id": "9", "rotation": 0}


def test_debug_force_tile_lay_rejects_disconnected_hex():
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])

    resp = client.post(
        f"/rooms/{room_id}/debug/force_tile_lay",
        json={"hex_id": "J33", "tile_id": "9", "rotation": 0, "company_id": "M1", "company_kind": "minor"},
    )
    assert resp.status_code == 400
    assert "connected" in resp.json()["detail"]


def test_debug_force_tile_lay_allows_multiple_lays_without_a_turn():
    """The whole point: never goes through _apply_operate, so there's no
    per-turn limit and no round to end - the connectivity check is the
    only gate."""
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])

    for row in [1, 2]:
        resp = client.post(
            f"/rooms/{room_id}/debug/force_tile_lay",
            json={"hex_id": f"H{row}", "tile_id": "9", "rotation": 0, "company_id": "M1", "company_kind": "minor"},
        )
        assert resp.status_code == 200, resp.json()


def test_debug_force_tile_lay_rejects_unknown_company():
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])

    resp = client.post(
        f"/rooms/{room_id}/debug/force_tile_lay",
        json={"hex_id": "H1", "tile_id": "9", "rotation": 0, "company_id": "NOTACOMPANY"},
    )
    assert resp.status_code == 400


def test_debug_force_tile_lay_404s_for_unknown_room():
    client = TestClient(app)
    resp = client.post(
        "/rooms/doesnotexist/debug/force_tile_lay",
        json={"hex_id": "H1", "tile_id": "9", "rotation": 0, "company_id": "M1"},
    )
    assert resp.status_code == 404
