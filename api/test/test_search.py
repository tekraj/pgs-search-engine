from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_search_endpoint():

    response = client.get(
        "/api/v1/user/search",
        params={
            "query": "Nepal"
        },
    )

    assert response.status_code in (
        200,
        503,
    )