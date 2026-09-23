from fastapi.testclient import TestClient

from app.main import app


def _create_and_start(client, names):
    room_id = client.post("/rooms").json()["room_id"]
    for name in names:
        client.post(f"/rooms/{room_id}/join", json={"name": name})
    client.post(f"/rooms/{room_id}/start")
    return room_id


def test_debug_force_round_jumps_straight_to_operating():
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])

    resp = client.post(f"/rooms/{room_id}/debug/force_round", json={"round_type": "operating", "company_id": "M1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["round_type"] == "operating"

    state_resp = client.get(f"/rooms/{room_id}/tile_lay_options", params={"hex_id": "Z1", "company_kind": "minor", "company_id": "M1"})
    assert state_resp.status_code == 200


def test_debug_force_round_sets_phase():
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])

    resp = client.post(f"/rooms/{room_id}/debug/force_round", json={"phase": 3})
    assert resp.status_code == 200
    assert resp.json()["phase"] == 3


def test_debug_force_round_rejects_unknown_company():
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])

    resp = client.post(
        f"/rooms/{room_id}/debug/force_round", json={"round_type": "operating", "company_id": "NOTACOMPANY"}
    )
    assert resp.status_code == 400


def test_debug_force_round_requires_company_id_for_operating():
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])

    resp = client.post(f"/rooms/{room_id}/debug/force_round", json={"round_type": "operating"})
    assert resp.status_code == 400


def test_debug_force_round_back_to_stock():
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])
    client.post(f"/rooms/{room_id}/debug/force_round", json={"round_type": "operating", "company_id": "M1"})

    resp = client.post(f"/rooms/{room_id}/debug/force_round", json={"round_type": "stock"})
    assert resp.status_code == 200
    assert resp.json()["round_type"] == "stock"


def test_debug_force_round_404s_for_unknown_room():
    client = TestClient(app)
    resp = client.post("/rooms/doesnotexist/debug/force_round", json={"phase": 2})
    assert resp.status_code == 404


def test_debug_force_round_400s_before_game_start():
    client = TestClient(app)
    room_id = client.post("/rooms").json()["room_id"]
    resp = client.post(f"/rooms/{room_id}/debug/force_round", json={"phase": 2})
    assert resp.status_code == 400
