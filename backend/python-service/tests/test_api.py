# backend/python-service/tests/test_api.py
from fastapi.testclient import TestClient
from app.main_test import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "Test Mode" in response.json()["message"]

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "environment": "test"}

# You can add more test functions here as you develop your API