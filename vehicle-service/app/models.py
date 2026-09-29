from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, String

from .database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(Integer, primary_key=True, index=True)
    make = Column(String, nullable=False)
    model = Column(String, nullable=False)
    plate = Column(String, unique=True, nullable=False)
    daily_rate = Column(Float, nullable=False)
    available = Column(Boolean, default=True)


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_cost = Column(Float, nullable=False)
    status = Column(String, default="ACTIVE")  # ACTIVE | COMPLETED | CANCELLED
