from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.spot_cache import SpotCache
from backend.schemas.spot import SpotCacheCreate, SpotCacheUpdate


async def create_spot_cache(
    db: AsyncSession, spot_in: SpotCacheCreate
) -> SpotCache:
    spot = SpotCache(**spot_in.model_dump())
    db.add(spot)
    await db.commit()
    await db.refresh(spot)
    return spot


async def get_spot_by_source_id(
    db: AsyncSession, source: str, source_id: str
) -> SpotCache | None:
    result = await db.execute(
        select(SpotCache).where(
            SpotCache.source == source, SpotCache.source_id == source_id
        )
    )
    return result.scalar_one_or_none()


async def search_spots(
    db: AsyncSession,
    keyword: str | None = None,
    city: str | None = None,
    type_tag: str | None = None,
    page: int = 1,
    size: int = 20,
    max_age_days: int = 7,
) -> tuple[int, list[SpotCache]]:
    cutoff = datetime.now(tz=UTC) - timedelta(days=max_age_days)
    query = select(SpotCache).where(SpotCache.cached_at >= cutoff)

    if keyword:
        query = query.where(SpotCache.name.contains(keyword))
    if city:
        query = query.where(SpotCache.city.contains(city))
    if type_tag:
        query = query.where(SpotCache.type_tags.contains(type_tag))

    from sqlalchemy import func

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return total, items


async def update_spot_cache(
    db: AsyncSession, spot: SpotCache, spot_in: SpotCacheUpdate
) -> SpotCache:
    update_data = spot_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(spot, field, value)
    spot.cached_at = datetime.now(tz=UTC)
    await db.commit()
    await db.refresh(spot)
    return spot
