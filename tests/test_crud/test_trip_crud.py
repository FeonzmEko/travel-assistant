from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.crud.trip import (
    create_trip,
    delete_trip,
    get_trip,
    get_user_trips,
    update_trip,
)
from backend.crud.user import create_user
from backend.schemas.trip import (
    TripActivityCreate,
    TripCreate,
    TripDayCreate,
    TripUpdate,
)
from backend.schemas.user import UserCreate


@pytest.fixture
async def user_id(db: AsyncSession) -> int:
    user = await create_user(
        db,
        UserCreate(username="tripuser", password="password123", email="trip@example.com"),
        password_hash="hashed",
    )
    return user.id


@pytest.fixture
def trip_data() -> TripCreate:
    return TripCreate(
        title="北京三日游",
        destination="北京",
        start_date=date(2025, 7, 1),
        end_date=date(2025, 7, 3),
        budget_total=3000.0,
        days=[
            TripDayCreate(
                day_index=1,
                date=date(2025, 7, 1),
                activities=[
                    TripActivityCreate(
                        order_index=1,
                        spot_name="故宫",
                        time_slot="09:00-12:00",
                        estimated_cost=60.0,
                        longitude=116.397026,
                        latitude=39.918058,
                    ),
                    TripActivityCreate(
                        order_index=2,
                        spot_name="天安门广场",
                        time_slot="14:00-16:00",
                        estimated_cost=0.0,
                    ),
                ],
            ),
        ],
    )


async def test_create_trip(
    db: AsyncSession, user_id: int, trip_data: TripCreate
) -> None:
    trip = await create_trip(db, user_id, trip_data)
    assert trip.id is not None
    assert trip.title == "北京三日游"
    assert trip.destination == "北京"


async def test_get_trip_with_days_and_activities(
    db: AsyncSession, user_id: int, trip_data: TripCreate
) -> None:
    trip = await create_trip(db, user_id, trip_data)
    found = await get_trip(db, trip.id)
    assert found is not None
    assert len(found.days) == 1
    assert len(found.days[0].activities) == 2
    assert found.days[0].activities[0].spot_name == "故宫"
    assert found.days[0].activities[0].longitude == 116.397026
    assert found.days[0].activities[0].latitude == 39.918058


async def test_get_trip_not_found(db: AsyncSession) -> None:
    found = await get_trip(db, 999)
    assert found is None


async def test_get_user_trips(
    db: AsyncSession, user_id: int, trip_data: TripCreate
) -> None:
    await create_trip(db, user_id, trip_data)
    trips = await get_user_trips(db, user_id)
    assert len(trips) == 1


async def test_update_trip(
    db: AsyncSession, user_id: int, trip_data: TripCreate
) -> None:
    trip = await create_trip(db, user_id, trip_data)
    updated = await update_trip(db, trip, TripUpdate(title="上海五日游"))
    assert updated.title == "上海五日游"


async def test_delete_trip(
    db: AsyncSession, user_id: int, trip_data: TripCreate
) -> None:
    trip = await create_trip(db, user_id, trip_data)
    await delete_trip(db, trip)
    found = await get_trip(db, trip.id)
    assert found is None
