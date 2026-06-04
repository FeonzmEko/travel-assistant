from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.trip import Trip, TripActivity, TripDay
from backend.schemas.trip import TripCreate, TripUpdate


async def create_trip(db: AsyncSession, user_id: int, trip_in: TripCreate) -> Trip:
    trip = Trip(
        user_id=user_id,
        title=trip_in.title,
        destination=trip_in.destination,
        start_date=trip_in.start_date,
        end_date=trip_in.end_date,
        budget_total=trip_in.budget_total,
        budget_breakdown=trip_in.budget_breakdown,
    )
    db.add(trip)
    await db.flush()

    for day_in in trip_in.days:
        day = TripDay(
            trip_id=trip.id,
            day_index=day_in.day_index,
            date=day_in.date,
            weather=day_in.weather,
        )
        db.add(day)
        await db.flush()

        for activity_in in day_in.activities:
            activity = TripActivity(
                trip_day_id=day.id,
                order_index=activity_in.order_index,
                spot_name=activity_in.spot_name,
                time_slot=activity_in.time_slot,
                transport=activity_in.transport,
                notes=activity_in.notes,
                estimated_cost=activity_in.estimated_cost,
                longitude=activity_in.longitude,
                latitude=activity_in.latitude,
            )
            db.add(activity)

    await db.commit()
    await db.refresh(trip)
    return trip


async def get_trip(db: AsyncSession, trip_id: int) -> Trip | None:
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id)
        .options(
            selectinload(Trip.days).selectinload(TripDay.activities)
        )
    )
    return result.scalar_one_or_none()


async def get_user_trips(db: AsyncSession, user_id: int) -> list[Trip]:
    result = await db.execute(
        select(Trip)
        .where(Trip.user_id == user_id)
        .order_by(Trip.updated_at.desc())
    )
    return list(result.scalars().all())


async def update_trip(db: AsyncSession, trip: Trip, trip_in: TripUpdate) -> Trip:
    update_data = trip_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(trip, field, value)
    await db.commit()
    await db.refresh(trip)
    return trip


async def delete_trip(db: AsyncSession, trip: Trip) -> None:
    await db.delete(trip)
    await db.commit()
