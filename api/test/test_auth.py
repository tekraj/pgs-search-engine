from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_register():

    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "password": "password123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["username"] == "testuser"
    assert "id" in data


def test_login():

    client.post(
        "/api/v1/auth/register",
        json={
            "username": "loginuser",
            "password": "password123",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "loginuser",
            "password": "password123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data