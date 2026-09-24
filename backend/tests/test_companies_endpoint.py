from fastapi.testclient import TestClient

from app.main import app


def test_list_companies_returns_majors_and_minors_with_current_hexes():
    client = TestClient(app)
    resp = client.get("/companies")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["majors"]) == 10
    assert len(data["minors"]) == 30

    nbr = next(c for c in data["majors"] if c["id"] == "NBR")
    assert nbr["current_home_hex"] == "H5"
    assert nbr["current_destination_hex"] == "H1"
    assert nbr["correction_home_hex"] is None

    m3 = next(c for c in data["minors"] if c["id"] == "M3")
    assert m3["current_home_hex"] == "H5"
    assert m3["kind"] == "minor"


def test_company_correction_round_trip_through_the_api():
    client = TestClient(app)

    resp = client.put("/companies/NBR/correction", json={"data": {"homeHex": "H5", "destinationHex": "H3"}})
    assert resp.status_code == 200

    data = client.get("/companies").json()
    nbr = next(c for c in data["majors"] if c["id"] == "NBR")
    assert nbr["correction_home_hex"] == "H5"
    assert nbr["correction_destination_hex"] == "H3"
    # The "live" lookup is untouched by the correction - it's a proposed
    # override, not applied to the engine's actual data.
    assert nbr["current_destination_hex"] == "H1"

    resp = client.delete("/companies/NBR/correction")
    assert resp.status_code == 200
    data = client.get("/companies").json()
    nbr = next(c for c in data["majors"] if c["id"] == "NBR")
    assert nbr["correction_home_hex"] is None
