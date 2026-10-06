from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_geo_hierarchy():

    response = client.get(
        "/api/v1/user/geo/hierarchy"
    )

    assert response.status_code == 200

    data = response.json()

    assert "provinces" in data
    assert "total_provinces" in data


def test_bagmati():

    response = client.get(
        "/api/v1/user/geo/hierarchy"
        "?province_code=P3"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_provinces"] == 1