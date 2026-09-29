import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_root_and_health():
    assert client.get("/").status_code == 200
    assert client.get("/health").json()["status"] == "healthy"


def test_ready_and_metrics():
    assert client.get("/ready").status_code == 200
    body = client.get("/metrics").text
    assert "http_requests_total" in body
    assert "active_bookings" in body


def test_full_booking_flow():
    vehicle = client.post("/vehicles", json={
        "make": "Toyota", "model": "Innova", "plate": "MH04AB1234", "daily_rate": 2000}).json()
    customer = client.post("/customers", json={
        "name": "Asha", "email": "asha@example.com", "phone": "9999999999"}).json()

    booking = client.post("/bookings", json={
        "vehicle_id": vehicle["id"], "customer_id": customer["id"],
        "start_date": "2026-10-01", "end_date": "2026-10-04"})
    assert booking.status_code == 201
    assert booking.json()["total_cost"] == 6000

    # same vehicle cannot be booked twice
    again = client.post("/bookings", json={
        "vehicle_id": vehicle["id"], "customer_id": customer["id"],
        "start_date": "2026-10-05", "end_date": "2026-10-06"})
    assert again.status_code == 409

    # returning the vehicle makes it available again
    assert client.post(f"/bookings/{booking.json()['id']}/return").json()["status"] == "COMPLETED"
    assert client.get(f"/vehicles/{vehicle['id']}").json()["available"] is True


def test_validation_and_not_found():
    bad = {"make": "X", "model": "Y", "plate": "P", "daily_rate": -5}
    assert client.post("/vehicles", json=bad).status_code == 422
    assert client.get("/vehicles/9999").status_code == 404
