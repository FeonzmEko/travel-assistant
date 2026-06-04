import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.crud.spot_cache import (
    create_spot_cache,
    get_spot_by_source_id,
    search_spots,
    update_spot_cache,
)
from backend.schemas.spot import SpotCacheCreate, SpotCacheUpdate


@pytest.fixture
def spot_data() -> SpotCacheCreate:
    return SpotCacheCreate(
        source="amap",
        source_id="B000A8UIN8",
        name="故宫博物院",
        city="北京",
        longitude=116.397026,
        latitude=39.918058,
        type_tags='["景点", "博物馆"]',
        description="明清两代的皇家宫殿",
        rating=4.8,
        ticket_price=60.0,
    )


async def test_create_spot_cache(
    db: AsyncSession, spot_data: SpotCacheCreate
) -> None:
    spot = await create_spot_cache(db, spot_data)
    assert spot.id is not None
    assert spot.name == "故宫博物院"
    assert spot.city == "北京"


async def test_get_spot_by_source_id(
    db: AsyncSession, spot_data: SpotCacheCreate
) -> None:
    await create_spot_cache(db, spot_data)
    found = await get_spot_by_source_id(db, "amap", "B000A8UIN8")
    assert found is not None
    assert found.name == "故宫博物院"


async def test_get_spot_by_source_id_not_found(db: AsyncSession) -> None:
    found = await get_spot_by_source_id(db, "amap", "nonexistent")
    assert found is None


async def test_search_spots_by_keyword(
    db: AsyncSession, spot_data: SpotCacheCreate
) -> None:
    await create_spot_cache(db, spot_data)
    total, items = await search_spots(db, keyword="故宫")
    assert total == 1
    assert items[0].name == "故宫博物院"


async def test_search_spots_by_city(
    db: AsyncSession, spot_data: SpotCacheCreate
) -> None:
    await create_spot_cache(db, spot_data)
    total, items = await search_spots(db, city="北京")
    assert total == 1

    total, items = await search_spots(db, city="上海")
    assert total == 0


async def test_search_spots_pagination(db: AsyncSession) -> None:
    for i in range(5):
        await create_spot_cache(
            db,
            SpotCacheCreate(
                source="amap",
                source_id=f"spot_{i}",
                name=f"景点{i}",
                city="北京",
            ),
        )
    total, items = await search_spots(db, city="北京", page=1, size=2)
    assert total == 5
    assert len(items) == 2

    total, items = await search_spots(db, city="北京", page=3, size=2)
    assert len(items) == 1


async def test_update_spot_cache(
    db: AsyncSession, spot_data: SpotCacheCreate
) -> None:
    spot = await create_spot_cache(db, spot_data)
    updated = await update_spot_cache(
        db, spot, SpotCacheUpdate(rating=4.9, description="更新后的描述")
    )
    assert updated.rating == 4.9
    assert updated.description == "更新后的描述"
