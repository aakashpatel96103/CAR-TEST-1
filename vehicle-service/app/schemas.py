from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class VehicleIn(BaseModel):
    make: str
    model: str
    plate: str
    daily_rate: float = Field(gt=0)


class VehicleOut(VehicleIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    available: bool


class CustomerIn(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None


class CustomerOut(CustomerIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class BookingIn(BaseModel):
    vehicle_id: int
    customer_id: int
    start_date: date
    end_date: date


class BookingOut(BookingIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    total_cost: float
    status: str
