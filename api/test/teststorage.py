import sys
import os
import pytest
from fastapi.testclient import TestClient
from main import app
from admin_storage_logs.security import API_KEY

client = TestClient(app)

HEADERS = {"X-Admin-API-Key": API_KEY}

def test_upload_safe_file():
    # Create a dummy text file
    files = {'file': ('test.txt', b'hello world', 'text/plain')}
    response = client.post("/admin/upload", files=files, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_upload_malicious_file():
    # Create a dummy exe file
    files = {'file': ('virus.exe', b'malicious content', 'application/octet-stream')}
    response = client.post("/admin/upload", files=files, headers=HEADERS)
    # Our logic returns 400 because it was quarantined
    assert response.status_code == 400
    assert response.json()["detail"]["status"] == "quarantined"

def test_unauthorized_access():
    files = {'file': ('test.txt', b'hello world', 'text/plain')}
    response = client.post("/admin/upload", files=files, headers={"X-Admin-API-Key": "wrong"})
    assert response.status_code == 403