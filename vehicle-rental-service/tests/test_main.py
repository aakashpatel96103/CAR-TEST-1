import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── System ────────────────────────────────────────────────────────────────────
def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "version" in response.json()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "version" in body
    assert "vehicles_count" in body


def test_version():
    response = client.get("/version")
    assert response.status_code == 200
    assert "version" in response.json()


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "python_info" in response.text or "process_" in response.text


def test_logs_endpoint():
    response = client.get("/logs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ── Vehicles ──────────────────────────────────────────────────────────────────
VEHICLE_PAYLOAD = {
    "registration_no": "MH01AB1234",
    "make": "Toyota",
    "model": "Innova",
    "vehicle_type": "SUV",
    "daily_rate": 2500,
    "available": True,
}


def test_vehicle_create():
    r = client.post("/vehicles", json=VEHICLE_PAYLOAD)
    assert r.status_code == 201
    assert r.json()["registration_no"] == "MH01AB1234"


def test_vehicle_list():
    r = client.get("/vehicles")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_vehicle_crud():
    r = client.post("/vehicles", json=VEHICLE_PAYLOAD)
    assert r.status_code == 201
    vid = r.json()["id"]

    assert client.get(f"/vehicles/{vid}").status_code == 200

    updated = VEHICLE_PAYLOAD.copy()
    updated["daily_rate"] = 2800
    assert client.put(f"/vehicles/{vid}", json=updated).status_code == 200

    assert client.delete(f"/vehicles/{vid}").status_code == 200


def test_vehicle_not_found():
    assert client.get("/vehicles/99999").status_code == 404
    assert client.put("/vehicles/99999", json=VEHICLE_PAYLOAD).status_code == 404
    assert client.delete("/vehicles/99999").status_code == 404


# ── Customers ─────────────────────────────────────────────────────────────────
CUSTOMER_PAYLOAD = {
    "name": "Alice Smith",
    "email": "alice@example.com",
    "phone": "9876543210",
}


def test_customer_create():
    r = client.post("/customers", json=CUSTOMER_PAYLOAD)
    assert r.status_code == 201
    assert r.json()["name"] == "Alice Smith"


def test_customer_crud():
    r = client.post("/customers", json=CUSTOMER_PAYLOAD)
    assert r.status_code == 201
    cid = r.json()["id"]

    assert client.get(f"/customers/{cid}").status_code == 200
    assert client.delete(f"/customers/{cid}").status_code == 200


def test_customer_not_found():
    assert client.get("/customers/99999").status_code == 404
    assert client.put("/customers/99999", json=CUSTOMER_PAYLOAD).status_code == 404
    assert client.delete("/customers/99999").status_code == 404


# ── Bookings ──────────────────────────────────────────────────────────────────
def test_booking_requires_vehicle_and_customer():
    payload = {
        "vehicle_id": 9999,
        "customer_id": 9999,
        "start_date": "2026-10-01",
        "end_date": "2026-10-03",
        "total_amount": 5000,
    }
    response = client.post("/bookings", json=payload)
    assert response.status_code == 404


def test_booking_full_crud():
    """Create vehicle → customer → booking → read → update → delete."""
    v = client.post("/vehicles", json=VEHICLE_PAYLOAD).json()
    c = client.post("/customers", json=CUSTOMER_PAYLOAD).json()

    booking_payload = {
        "vehicle_id": v["id"],
        "customer_id": c["id"],
        "start_date": "2026-10-01",
        "end_date": "2026-10-03",
        "total_amount": 5000,
    }
    r = client.post("/bookings", json=booking_payload)
    assert r.status_code == 201
    bid = r.json()["id"]

    assert client.get(f"/bookings/{bid}").status_code == 200

    booking_payload["total_amount"] = 6000
    assert client.put(f"/bookings/{bid}", json=booking_payload).status_code == 200

    assert client.delete(f"/bookings/{bid}").status_code == 200

    # Cleanup
    client.delete(f"/vehicles/{v['id']}")
    client.delete(f"/customers/{c['id']}")


def test_booking_list():
    r = client.get("/bookings")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_booking_not_found():
    assert client.get("/bookings/99999").status_code == 404
    assert client.delete("/bookings/99999").status_code == 404


# ── Request-ID header ────────────────────────────────────────────────────────
def test_request_id_header():
    r = client.get("/health")
    assert "x-request-id" in r.headers
    assert "x-response-time-ms" in r.headers


def test_custom_request_id():
    r = client.get("/health", headers={"X-Request-ID": "test-123"})
    assert r.headers["x-request-id"] == "test-123"
