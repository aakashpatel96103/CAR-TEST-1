import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from prometheus_client import Counter, Gauge
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db

APP_VERSION = os.getenv("APP_VERSION", "dev")


# ---------------- Logging: one JSON line per event on stdout (kubectl logs) ----------------
class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for key in ("method", "path", "status", "duration_ms"):
            if hasattr(record, key):
                data[key] = getattr(record, key)
        return json.dumps(data)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logging.getLogger().handlers = [handler]
logging.getLogger().setLevel(logging.INFO)
log = logging.getLogger("vehicle-rental")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Vehicle Rental System API",
    description="Manage vehicles, customers and bookings. Instrumented for Prometheus and Grafana.",
    version=APP_VERSION,
)

# ---------------- Monitoring: /metrics for Prometheus ----------------
Instrumentator().instrument(app).expose(app, include_in_schema=False)
BOOKINGS_CREATED = Counter("bookings_created_total", "Bookings created")
ACTIVE_BOOKINGS = Gauge("active_bookings", "Currently active bookings")
APP_INFO = Gauge("app_info", "Running app version", ["version"])
APP_INFO.labels(version=APP_VERSION).set(1)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    if request.url.path != "/metrics":
        log.info("request", extra={
            "method": request.method, "path": request.url.path,
            "status": response.status_code, "duration_ms": round((time.time() - start) * 1000, 2)})
    return response


# ---------------- System ----------------
@app.get("/", tags=["System Diagnostics"], summary="Service Root Status")
def root():
    return {"message": "Vehicle Rental API is running", "version": APP_VERSION}


@app.get("/health", tags=["System Diagnostics"], summary="Liveness Probe")
def health():
    return {"status": "healthy", "version": APP_VERSION}


@app.get("/ready", tags=["System Diagnostics"], summary="Readiness Probe (checks database)")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


# ---------------- Vehicles ----------------
@app.post("/vehicles", response_model=schemas.VehicleOut, status_code=201, tags=["Vehicles"])
def create_vehicle(data: schemas.VehicleIn, db: Session = Depends(get_db)):
    vehicle = models.Vehicle(**data.model_dump())
    db.add(vehicle)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Vehicle with this plate already exists")
    db.refresh(vehicle)
    return vehicle


@app.get("/vehicles", response_model=list[schemas.VehicleOut], tags=["Vehicles"])
def list_vehicles(available: bool | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Vehicle)
    if available is not None:
        query = query.filter(models.Vehicle.available == available)
    return query.all()


@app.get("/vehicles/{vehicle_id}", response_model=schemas.VehicleOut, tags=["Vehicles"])
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = db.get(models.Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")
    return vehicle


@app.put("/vehicles/{vehicle_id}", response_model=schemas.VehicleOut, tags=["Vehicles"])
def update_vehicle(vehicle_id: int, data: schemas.VehicleIn, db: Session = Depends(get_db)):
    vehicle = db.get(models.Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")
    for key, value in data.model_dump().items():
        setattr(vehicle, key, value)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@app.delete("/vehicles/{vehicle_id}", status_code=204, tags=["Vehicles"])
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = db.get(models.Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")
    db.delete(vehicle)
    db.commit()


# ---------------- Customers ----------------
@app.post("/customers", response_model=schemas.CustomerOut, status_code=201, tags=["Customers"])
def create_customer(data: schemas.CustomerIn, db: Session = Depends(get_db)):
    customer = models.Customer(**data.model_dump())
    db.add(customer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Customer with this email already exists")
    db.refresh(customer)
    return customer


@app.get("/customers", response_model=list[schemas.CustomerOut], tags=["Customers"])
def list_customers(db: Session = Depends(get_db)):
    return db.query(models.Customer).all()


@app.get("/customers/{customer_id}", response_model=schemas.CustomerOut, tags=["Customers"])
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(models.Customer, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    return customer


@app.put("/customers/{customer_id}", response_model=schemas.CustomerOut, tags=["Customers"])
def update_customer(customer_id: int, data: schemas.CustomerIn, db: Session = Depends(get_db)):
    customer = db.get(models.Customer, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    for key, value in data.model_dump().items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer


@app.delete("/customers/{customer_id}", status_code=204, tags=["Customers"])
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(models.Customer, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    db.delete(customer)
    db.commit()


# ---------------- Bookings ----------------
def refresh_active_gauge(db: Session):
    ACTIVE_BOOKINGS.set(db.query(models.Booking).filter(models.Booking.status == "ACTIVE").count())


@app.post("/bookings", response_model=schemas.BookingOut, status_code=201, tags=["Bookings"])
def create_booking(data: schemas.BookingIn, db: Session = Depends(get_db)):
    if data.end_date <= data.start_date:
        raise HTTPException(400, "end_date must be after start_date")
    vehicle = db.get(models.Vehicle, data.vehicle_id)
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")
    if not db.get(models.Customer, data.customer_id):
        raise HTTPException(404, "Customer not found")
    if not vehicle.available:
        raise HTTPException(409, "Vehicle is not available")
    days = (data.end_date - data.start_date).days
    booking = models.Booking(**data.model_dump(), total_cost=days * vehicle.daily_rate, status="ACTIVE")
    vehicle.available = False
    db.add(booking)
    db.commit()
    db.refresh(booking)
    BOOKINGS_CREATED.inc()
    refresh_active_gauge(db)
    log.info(f"booking {booking.id} created for vehicle {vehicle.id}")
    return booking


@app.get("/bookings", response_model=list[schemas.BookingOut], tags=["Bookings"])
def list_bookings(db: Session = Depends(get_db)):
    return db.query(models.Booking).all()


@app.get("/bookings/{booking_id}", response_model=schemas.BookingOut, tags=["Bookings"])
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.get(models.Booking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    return booking


def close_booking(booking_id: int, new_status: str, db: Session):
    booking = db.get(models.Booking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.status != "ACTIVE":
        raise HTTPException(409, f"Booking already {booking.status}")
    booking.status = new_status
    vehicle = db.get(models.Vehicle, booking.vehicle_id)
    if vehicle:
        vehicle.available = True
    db.commit()
    db.refresh(booking)
    refresh_active_gauge(db)
    return booking


@app.post("/bookings/{booking_id}/return", response_model=schemas.BookingOut, tags=["Bookings"])
def return_vehicle(booking_id: int, db: Session = Depends(get_db)):
    return close_booking(booking_id, "COMPLETED", db)


@app.post("/bookings/{booking_id}/cancel", response_model=schemas.BookingOut, tags=["Bookings"])
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    return close_booking(booking_id, "CANCELLED", db)
