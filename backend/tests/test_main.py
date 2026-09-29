from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    assert client.get("/").status_code == 200

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"

def test_metrics():
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "python_info" in r.text or "process_" in r.text

def test_vehicle():
    r = client.post("/vehicles", json={"id": 9001, "registration": "MH01AB1234", "model": "Sedan"})
    assert r.status_code == 200
    assert client.get("/vehicles/9001").json()["model"] == "Sedan"

def test_customer():
    r = client.post("/customers", json={"id": 9001, "name": "Test Customer", "phone": "9999999999"})
    assert r.status_code == 200

def test_booking():
    r = client.post("/bookings", json={"id": 9001, "vehicle_id": 9001, "customer_id": 9001, "days": 3})
    assert r.status_code == 200
