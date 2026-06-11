from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.user import User


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    destination: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    budget_total: Mapped[float | None] = mapped_column(default=None)
    budget_breakdown: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=lambda: datetime.now(tz=UTC)
    )

    user: Mapped[User] = relationship(back_populates="trips")
    days: Mapped[list[TripDay]] = relationship(
        back_populates="trip", cascade="all, delete-orphan"
    )


class TripDay(Base):
    __tablename__ = "trip_days"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    day_index: Mapped[int] = mapped_column()
    date: Mapped[date] = mapped_column(Date)
    weather: Mapped[str | None] = mapped_column(String(100), default=None)

    trip: Mapped[Trip] = relationship(back_populates="days")
    activities: Mapped[list[TripActivity]] = relationship(
        back_populates="trip_day", cascade="all, delete-orphan"
    )


class TripActivity(Base):
    __tablename__ = "trip_activities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_day_id: Mapped[int] = mapped_column(
        ForeignKey("trip_days.id", ondelete="CASCADE")
    )
    order_index: Mapped[int] = mapped_column()
    spot_name: Mapped[str] = mapped_column(String(200))
    time_slot: Mapped[str | None] = mapped_column(String(50), default=None)
    transport: Mapped[str | None] = mapped_column(String(50), default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    estimated_cost: Mapped[float | None] = mapped_column(default=None)
    longitude: Mapped[float | None] = mapped_column(Float, default=None)
    latitude: Mapped[float | None] = mapped_column(Float, default=None)

    trip_day: Mapped[TripDay] = relationship(back_populates="activities")
