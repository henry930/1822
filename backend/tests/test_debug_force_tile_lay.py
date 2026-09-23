from fastapi.testclient import TestClient

from app.main import app
from app.rooms import registry


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
        # H1 (Aberdeen) is a catalogued city - tile 57 (edges 0-3, same
        # track pattern as plain tile 9) is the city-compatible equivalent.
        json={"hex_id": "H1", "tile_id": "57", "rotation": 0, "company_id": "M1", "company_kind": "minor"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "hex_id": "H1", "tile_id": "57", "rotation": 0, "cost": 0}


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

    # H1 (Aberdeen) is a catalogued city and needs a city tile; H2 is plain.
    for row, tile_id in [(1, "57"), (2, "9")]:
        resp = client.post(
            f"/rooms/{room_id}/debug/force_tile_lay",
            json={"hex_id": f"H{row}", "tile_id": tile_id, "rotation": 0, "company_id": "M1", "company_kind": "minor"},
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

    # H1 (home) is a city and needs a city tile to establish the network;
    # H2 is a plain hex where tile "1" (only 1 copy in the physical supply)
    # can be used to actually test supply exhaustion.
    home = client.post(
        f"/rooms/{room_id}/debug/force_tile_lay",
        json={"hex_id": "H1", "tile_id": "57", "rotation": 0, "company_id": "M1", "company_kind": "minor"},
    )
    assert home.status_code == 200, home.json()

    first = client.post(
        f"/rooms/{room_id}/debug/force_tile_lay",
        json={"hex_id": "H2", "tile_id": "1", "rotation": 0, "company_id": "M1", "company_kind": "minor"},
    )
    assert first.status_code == 200, first.json()

    second = client.post(
        f"/rooms/{room_id}/debug/force_tile_lay",
        json={"hex_id": "H3", "tile_id": "1", "rotation": 0, "company_id": "M1", "company_kind": "minor"},
    )
    assert second.status_code == 400
    assert "supply" in second.json()["detail"]


def test_debug_force_tile_lay_rejects_a_tile_not_yet_available_in_this_phase():
    """The room starts in phase 1 (yellow only) - a green tile is rejected
    even though it would otherwise be a legal city/connectivity match
    (tile 14 is unlabeled, matching H1's label of None)."""
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])

    resp = client.post(
        f"/rooms/{room_id}/debug/force_tile_lay",
        json={"hex_id": "H1", "tile_id": "14", "rotation": 0, "company_id": "M1", "company_kind": "minor"},
    )
    assert resp.status_code == 400
    assert "not available yet" in resp.json()["detail"]


def test_debug_force_tile_lay_rejects_a_tile_with_no_city_on_a_city_hex():
    """H1 (Aberdeen) is a catalogued city - a plain track tile with no city
    circle at all doesn't belong there, even though its label (None)
    happens to match."""
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])

    resp = client.post(
        f"/rooms/{room_id}/debug/force_tile_lay",
        json={"hex_id": "H1", "tile_id": "9", "rotation": 0, "company_id": "M1", "company_kind": "minor"},
    )
    assert resp.status_code == 400
    assert "has no city" in resp.json()["detail"]


def test_debug_force_tile_lay_rejects_an_upgrade_that_drops_a_connection():
    """Once H1 has a tile whose track uses edges 0 and 2, a green upgrade
    whose track doesn't cover that same pair must be rejected (rule
    5.7.16) - it would cut a route that already exists."""
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])

    first = client.post(
        f"/rooms/{room_id}/debug/force_tile_lay",
        json={"hex_id": "H1", "tile_id": "6", "rotation": 0, "company_id": "M1", "company_kind": "minor"},
    )
    assert first.status_code == 200, first.json()

    client.post(f"/rooms/{room_id}/debug/force_round", json={"phase": 3})

    resp = client.post(
        f"/rooms/{room_id}/debug/force_tile_lay",
        # green city tile 14 only uses edges 0,1,3,4 - drops edge 2 entirely.
        json={"hex_id": "H1", "tile_id": "14", "rotation": 0, "company_id": "M1", "company_kind": "minor"},
    )
    assert resp.status_code == 400
    assert "preserve" in resp.json()["detail"]


def test_debug_force_tile_lay_rejects_insufficient_treasury_for_terrain_cost():
    """H13 is a catalogued estuary hex (£40 terrain cost, rule 5.7.18). A
    company with £0 in its treasury can't afford it. A station is planted
    directly on H13 (bypassing the need to actually build a multi-hex
    network just to reach it) so the connectivity check isn't what fails
    here - only the money check should be."""
    client = TestClient(app)
    room_id = _create_and_start(client, ["Alice", "Bob", "Carol"])

    room = registry.get(room_id)
    major = room.state.majors["NBR"]  # home H5, unrelated to H13
    major.tokens_on_map.append("H13")
    major.treasury = 0

    resp = client.post(
        f"/rooms/{room_id}/debug/force_tile_lay",
        json={"hex_id": "H13", "tile_id": "3", "rotation": 0, "company_id": "NBR", "company_kind": "major"},
    )
    assert resp.status_code == 400
    assert "afford" in resp.json()["detail"]


def test_debug_force_tile_lay_404s_for_unknown_room():
    client = TestClient(app)
    resp = client.post(
        "/rooms/doesnotexist/debug/force_tile_lay",
        json={"hex_id": "H1", "tile_id": "9", "rotation": 0, "company_id": "M1"},
    )
    assert resp.status_code == 404
