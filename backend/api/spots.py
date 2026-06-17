import logging
from datetime import UTC, datetime, timedelta

import httpx
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
from backend.services.spot_data import search_curated_spots
from backend.utils.spot_images import fallback_images, serialize_images

router = APIRouter(prefix="/api/spots", tags=["spots"])

logger = logging.getLogger(__name__)

CACHE_MAX_AGE_DAYS = 7


async def _upsert_spot(
    db: AsyncSession,
    *,
    source: str,
    source_id: str,
    name: str,
    city: str,
    longitude: float | None,
    latitude: float | None,
    type_tags: str | None,
    address: str | None,
    tel: str | None,
    description: str | None,
    images: str | None,
    rating: float | None,
    open_time: str | None,
    ticket_price: float | None,
) -> SpotCacheOut:
    """写入或刷新单个景点缓存，并返回标准化输出。"""
    existing = await get_spot_by_source_id(db, source, source_id)

    if existing is not None:
        cached_at = existing.cached_at
        if cached_at and cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=UTC)
        cutoff = datetime.now(tz=UTC) - timedelta(days=CACHE_MAX_AGE_DAYS)
        if cached_at and cached_at >= cutoff:
            return SpotCacheOut.model_validate(existing)

        updated = await update_spot_cache(
            db,
            existing,
            SpotCacheUpdate(
                description=(
                    description if description is not None else existing.description
                ),
                images=images or existing.images,
                rating=rating if rating is not None else existing.rating,
                open_time=open_time or existing.open_time,
                ticket_price=(
                    ticket_price
                    if ticket_price is not None
                    else existing.ticket_price
                ),
                address=address or existing.address,
                tel=tel or existing.tel,
            ),
        )
        return SpotCacheOut.model_validate(updated)

    created = await create_spot_cache(
        db,
        SpotCacheCreate(
            source=source,
            source_id=source_id,
            name=name,
            city=city,
            longitude=longitude,
            latitude=latitude,
            type_tags=type_tags,
            address=address,
            tel=tel,
            description=description,
            images=images,
            rating=rating,
            open_time=open_time,
            ticket_price=ticket_price,
        ),
    )
    return SpotCacheOut.model_validate(created)


async def _cache_amap_spots(
    db: AsyncSession,
    keyword: str,
    city: str,
    type_code: str | None,
    page: int,
    size: int,
) -> list[SpotCacheOut]:
    """调用高德 POI，写入缓存（含图片/评分等），并返回标准化输出。"""
    remote_spots = await amap_poi_search(
        keyword=keyword, city=city, type_code=type_code, page=page, size=size
    )

    results: list[SpotCacheOut] = []
    for spot in remote_spots:
        type_tags_str = ";".join(spot.type_tags) if spot.type_tags else None
        results.append(
            await _upsert_spot(
                db,
                source="amap",
                source_id=spot.source_id,
                name=spot.name,
                city=spot.city,
                longitude=spot.longitude,
                latitude=spot.latitude,
                type_tags=type_tags_str,
                address=spot.address or None,
                tel=spot.tel or None,
                description=None,
                images=serialize_images(spot.images),
                rating=spot.rating,
                open_time=spot.open_time or None,
                ticket_price=spot.ticket_price,
            )
        )
    return results


async def _cache_curated_spots(
    db: AsyncSession,
    keyword: str | None,
    city: str | None,
    type_tag: str | None,
    page: int,
    size: int,
) -> tuple[int, list[SpotCacheOut]]:
    """高德不可用时，用内置精选景点数据兜底并写入缓存。"""
    matches = search_curated_spots(keyword=keyword, city=city, type_tag=type_tag)

    for spot in matches:
        type_tags_list = spot.get("type_tags") or []
        type_tags_str = ";".join(type_tags_list) if type_tags_list else None
        images_str = serialize_images(
            fallback_images(
                spot["name"],
                type_tags_str,
                seed=spot["source_id"],
                query=spot.get("image_query"),
            )
        )
        await _upsert_spot(
            db,
            source="curated",
            source_id=spot["source_id"],
            name=spot["name"],
            city=spot.get("city", ""),
            longitude=spot.get("longitude"),
            latitude=spot.get("latitude"),
            type_tags=type_tags_str,
            address=spot.get("address"),
            tel=spot.get("tel"),
            description=spot.get("description"),
            images=images_str,
            rating=spot.get("rating"),
            open_time=spot.get("open_time"),
            ticket_price=spot.get("ticket_price"),
        )

    total, items = await search_spots(
        db, keyword=keyword, city=city, type_tag=type_tag, page=page, size=size
    )
    return total, [SpotCacheOut.model_validate(item) for item in items]


@router.get("/search")
async def search(
    keyword: str | None = Query(None),
    city: str | None = Query(None),
    type: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    total, cached_items = await search_spots(
        db, keyword=keyword, city=city, type_tag=type, page=page, size=size
    )

    if total > 0:
        items = [SpotCacheOut.model_validate(s) for s in cached_items]
        return {"total": total, "items": items}

    if not keyword and not city:
        return {"total": 0, "items": []}

    # 同条件已有基础缓存（仅被 type 过滤掉）时，不再重复拉取远端
    base_total, _ = await search_spots(db, keyword=keyword, city=city, page=1, size=1)
    if base_total > 0:
        return {"total": 0, "items": []}

    # 1) 优先高德 POI（有关键词即可，城市可选；高德支持全国检索）
    remote_items: list[SpotCacheOut] = []
    if keyword:
        try:
            remote_items = await _cache_amap_spots(
                db, keyword, city or "", type, page, size
            )
        except httpx.HTTPError:
            logger.exception("高德 POI 搜索失败，回退到精选景点数据")
    if remote_items:
        return {"total": len(remote_items), "items": remote_items}

    # 2) 回退到内置精选景点数据，保证有结果与对应的图片
    curated_total, curated_items = await _cache_curated_spots(
        db, keyword, city, type, page, size
    )
    return {"total": curated_total, "items": curated_items}


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
