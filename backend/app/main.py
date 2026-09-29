from datetime import date
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Vehicle Rental System", version="1.0.0")
Instrumentator().instrument(app).expose(app)

vehicles = {}
customers = {}
bookings = {}

@app.get("/")
def root():
    return {"message": "Vehicle Rental API is running", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/vehicles")
def list_vehicles():
    return list(vehicles.values())

@app.post("/vehicles")
def create_vehicle(vehicle: dict):
    vehicle_id = int(vehicle.get("id", len(vehicles) + 1))
    vehicle["id"] = vehicle_id
    vehicle.setdefault("available", True)
    vehicles[vehicle_id] = vehicle
    return vehicle

@app.get("/vehicles/{vehicle_id}")
def get_vehicle(vehicle_id: int):
    if vehicle_id not in vehicles:
        raise HTTPException(404, "Vehicle not found")
    return vehicles[vehicle_id]

@app.put("/vehicles/{vehicle_id}")
def update_vehicle(vehicle_id: int, vehicle: dict):
    if vehicle_id not in vehicles:
        raise HTTPException(404, "Vehicle not found")
    vehicle["id"] = vehicle_id
    vehicles[vehicle_id] = vehicle
    return vehicle

@app.delete("/vehicles/{vehicle_id}")
def delete_vehicle(vehicle_id: int):
    if vehicle_id not in vehicles:
        raise HTTPException(404, "Vehicle not found")
    return vehicles.pop(vehicle_id)

@app.get("/customers")
def list_customers():
    return list(customers.values())

@app.post("/customers")
def create_customer(customer: dict):
    customer_id = int(customer.get("id", len(customers) + 1))
    customer["id"] = customer_id
    customers[customer_id] = customer
    return customer

@app.get("/customers/{customer_id}")
def get_customer(customer_id: int):
    if customer_id not in customers:
        raise HTTPException(404, "Customer not found")
    return customers[customer_id]

@app.put("/customers/{customer_id}")
def update_customer(customer_id: int, customer: dict):
    if customer_id not in customers:
        raise HTTPException(404, "Customer not found")
    customer["id"] = customer_id
    customers[customer_id] = customer
    return customer

@app.delete("/customers/{customer_id}")
def delete_customer(customer_id: int):
    if customer_id not in customers:
        raise HTTPException(404, "Customer not found")
    return customers.pop(customer_id)

@app.get("/bookings")
def list_bookings():
    return list(bookings.values())

@app.post("/bookings")
def create_booking(booking: dict):
    booking_id = int(booking.get("id", len(bookings) + 1))
    booking["id"] = booking_id
    booking.setdefault("booking_date", str(date.today()))
    bookings[booking_id] = booking
    return booking

@app.get("/bookings/{booking_id}")
def get_booking(booking_id: int):
    if booking_id not in bookings:
        raise HTTPException(404, "Booking not found")
    return bookings[booking_id]

@app.delete("/bookings/{booking_id}")
def delete_booking(booking_id: int):
    if booking_id not in bookings:
        raise HTTPException(404, "Booking not found")
    return bookings.pop(booking_id)
