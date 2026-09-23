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


def test_debug_force_tile_lay_rejects_exhausted_tile_supply():
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])

    # tile "1" only has 1 copy in the physical supply.
    first = client.post(
        f"/rooms/{room_id}/debug/force_tile_lay",
        json={"hex_id": "H1", "tile_id": "1", "rotation": 0, "company_id": "M1", "company_kind": "minor"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/rooms/{room_id}/debug/force_tile_lay",
        json={"hex_id": "H2", "tile_id": "1", "rotation": 0, "company_id": "M1", "company_kind": "minor"},
    )
    assert second.status_code == 400
    assert "supply" in second.json()["detail"]


def test_debug_force_tile_lay_allows_relaying_the_same_tile_on_its_own_hex():
    """Laying the one copy of a limited tile back onto the hex it's
    already on (e.g. just to change rotation) shouldn't count as needing
    a second copy - apply_tile_lay returns the old one before drawing."""
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])

    client.post(
        f"/rooms/{room_id}/debug/force_tile_lay",
        json={"hex_id": "H1", "tile_id": "1", "rotation": 0, "company_id": "M1", "company_kind": "minor"},
    )
    resp = client.post(
        f"/rooms/{room_id}/debug/force_tile_lay",
        json={"hex_id": "H1", "tile_id": "1", "rotation": 2, "company_id": "M1", "company_kind": "minor"},
    )
    assert resp.status_code == 200


def test_debug_force_tile_lay_404s_for_unknown_room():
    client = TestClient(app)
    resp = client.post(
        "/rooms/doesnotexist/debug/force_tile_lay",
        json={"hex_id": "H1", "tile_id": "9", "rotation": 0, "company_id": "M1"},
    )
    assert resp.status_code == 404
