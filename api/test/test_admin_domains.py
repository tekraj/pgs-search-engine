from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def get_admin_token():

    client.post(
        "/api/v1/auth/register",
        json={
            "username": "admin",
            "password": "admin123",
        },
    )

    from auth.service import USERS

    for user in USERS.values():

        if user["username"] == "admin":
            user["roles"] = ["admin"]

    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "admin",
            "password": "admin123",
        },
    )

    return response.json()["access_token"]


def test_admin_domain():

    token = get_admin_token()

    response = client.post(
        "/api/v1/admin/domains",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "domain": "example.com",
            "enabled": True,
            "crawl_enabled": True,
        },
    )

    assert response.status_code == 200