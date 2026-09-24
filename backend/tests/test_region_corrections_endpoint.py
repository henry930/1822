from fastapi.testclient import TestClient

from app.main import app


def test_region_corrections_round_trip_through_the_api():
    client = TestClient(app)

    resp = client.put("/board/corrections/H1", json={"data": {"cityOrTown": "city", "name": "Aberdeen"}})
    assert resp.status_code == 200

    resp = client.get("/board/corrections")
    assert resp.status_code == 200
    corrections = resp.json()
    assert corrections["H1"]["name"] == "Aberdeen"

    resp = client.delete("/board/corrections/H1")
    assert resp.status_code == 200

    resp = client.get("/board/corrections")
    assert "H1" not in resp.json()


def test_bulk_region_corrections_endpoint():
    client = TestClient(app)

    resp = client.put("/board/corrections", json={"hex_ids": ["Z1", "Z2", "Z3"], "data": {"disabled": True}})
    assert resp.status_code == 200
    assert resp.json()["count"] == 3

    corrections = client.get("/board/corrections").json()
    for hex_id in ["Z1", "Z2", "Z3"]:
        assert corrections[hex_id]["disabled"] is True

    resp = client.put("/board/corrections", json={"hex_ids": [], "data": {"disabled": True}})
    assert resp.status_code == 400
