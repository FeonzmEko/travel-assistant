from datetime import date, datetime

from pydantic import BaseModel, Field


class TripActivityCreate(BaseModel):
    order_index: int
    spot_name: str = Field(max_length=200)
    time_slot: str | None = None
    transport: str | None = None
    notes: str | None = None
    estimated_cost: float | None = None


class TripActivityUpdate(BaseModel):
    order_index: int | None = None
    spot_name: str | None = Field(default=None, max_length=200)
    time_slot: str | None = None
    transport: str | None = None
    notes: str | None = None
    estimated_cost: float | None = None


class TripActivityOut(BaseModel):
    id: int
    trip_day_id: int
    order_index: int
    spot_name: str
    time_slot: str | None
    transport: str | None
    notes: str | None
    estimated_cost: float | None

    model_config = {"from_attributes": True}


class TripDayCreate(BaseModel):
    day_index: int
    date: date
    weather: str | None = None
    activities: list[TripActivityCreate] = Field(default_factory=list)


class TripDayUpdate(BaseModel):
    weather: str | None = None


class TripDayOut(BaseModel):
    id: int
    trip_id: int
    day_index: int
    date: date
    weather: str | None
    activities: list[TripActivityOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TripCreate(BaseModel):
    title: str = Field(max_length=200)
    destination: str = Field(max_length=100)
    start_date: date
    end_date: date
    budget_total: float | None = None
    budget_breakdown: str | None = None
    days: list[TripDayCreate] = Field(default_factory=list)


class TripUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    destination: str | None = Field(default=None, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    budget_total: float | None = None
    budget_breakdown: str | None = None


class TripOut(BaseModel):
    id: int
    user_id: int
    title: str
    destination: str
    start_date: date
    end_date: date
    budget_total: float | None
    budget_breakdown: str | None
    created_at: datetime
    updated_at: datetime
    days: list[TripDayOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}
