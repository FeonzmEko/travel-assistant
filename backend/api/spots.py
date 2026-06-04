from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.crud.spot_cache import (
    create_spot_cache,
    get_spot_by_source_id,
    search_spots,
    update_spot_cache,
)
from backend.database import get_db
from backend.schemas.spot import SpotCacheCreate, SpotCacheOut, SpotCacheUpdate
from backend.services.amap import amap_poi_search

router = APIRouter(prefix="/api/spots", tags=["spots"])

CACHE_MAX_AGE_DAYS = 7


async def _cache_amap_spots(
    db: AsyncSession,
    keyword: str,
    city: str,
    type_code: str | None,
    page: int,
    size: int,
) -> list[SpotCacheOut]:
    """Fetch from Amap, upsert into cache, return as SpotCacheOut."""
    remote_spots = await amap_poi_search(
        keyword=keyword, city=city, type_code=type_code, page=page, size=size
    )

    results: list[SpotCacheOut] = []
    cutoff = datetime.now(tz=UTC) - timedelta(days=CACHE_MAX_AGE_DAYS)

    for spot in remote_spots:
        existing = await get_spot_by_source_id(db, "amap", spot.source_id)
        cached_at = existing.cached_at if existing else None
        if cached_at and cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=UTC)
        if existing and cached_at and cached_at >= cutoff:
            results.append(SpotCacheOut.model_validate(existing))
            continue

        type_tags_str = ";".join(spot.type_tags) if spot.type_tags else None

        if existing:
            updated = await update_spot_cache(
                db,
                existing,
                SpotCacheUpdate(description=existing.description),
            )
            results.append(SpotCacheOut.model_validate(updated))
        else:
            created = await create_spot_cache(
                db,
                SpotCacheCreate(
                    source="amap",
                    source_id=spot.source_id,
                    name=spot.name,
                    city=spot.city,
                    longitude=spot.longitude,
                    latitude=spot.latitude,
                    type_tags=type_tags_str,
                ),
            )
            results.append(SpotCacheOut.model_validate(created))

    return results


@router.get("/search")
async def search(
    keyword: str | None = Query(None),
    city: str | None = Query(None),
    type: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    total, cached_items = await search_spots(
        db, keyword=keyword, city=city, type_tag=type, page=page, size=size
    )

    if total > 0:
        items = [SpotCacheOut.model_validate(s) for s in cached_items]
        return {"total": total, "items": items}

    if not keyword or not city:
        return {"total": 0, "items": []}

    base_total, _ = await search_spots(
        db, keyword=keyword, city=city, page=1, size=1
    )
    if base_total > 0:
        return {"total": 0, "items": []}

    remote_items = await _cache_amap_spots(db, keyword, city, type, page, size)
    return {"total": len(remote_items), "items": remote_items}


@router.get("/{spot_id}")
async def get_spot(
    spot_id: int,
    db: AsyncSession = Depends(get_db),
) -> SpotCacheOut:
    from sqlalchemy import select

    from backend.models.spot_cache import SpotCache

    result = await db.execute(select(SpotCache).where(SpotCache.id == spot_id))
    spot = result.scalar_one_or_none()
    if not spot:
        raise HTTPException(status_code=404, detail="Spot not found")
    return SpotCacheOut.model_validate(spot)
