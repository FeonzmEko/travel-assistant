from dataclasses import dataclass, field
from typing import Any

import httpx

from backend.config import settings


@dataclass
class Spot:
    name: str
    source_id: str
    city: str
    longitude: float
    latitude: float
    type_tags: list[str] = field(default_factory=list)
    address: str = ""
    tel: str = ""
    images: list[str] = field(default_factory=list)
    rating: float | None = None
    open_time: str = ""
    ticket_price: float | None = None


@dataclass
class RouteSegment:
    origin: str
    destination: str
    distance: float
    duration: float
    steps: list[str] = field(default_factory=list)


@dataclass
class Route:
    distance: float
    duration: float
    segments: list[RouteSegment] = field(default_factory=list)


AMAP_BASE_URL = "https://restapi.amap.com/v3"


def _to_str(value: object) -> str:
    """高德对空字段常返回 [] 而非空串，这里统一归一为字符串。"""
    if isinstance(value, str):
        return value
    return ""


def _to_float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _extract_photos(poi: dict[str, Any]) -> list[str]:
    photos = poi.get("photos")
    if not isinstance(photos, list):
        return []
    urls: list[str] = []
    for photo in photos:
        if isinstance(photo, dict):
            url = photo.get("url")
            if isinstance(url, str) and url.strip():
                urls.append(url.strip())
    return urls


def _extract_biz_ext(poi: dict[str, Any]) -> dict[str, Any]:
    """biz_ext 可能是 dict，也可能在无数据时是空 list。"""
    biz_ext = poi.get("biz_ext")
    return biz_ext if isinstance(biz_ext, dict) else {}


async def amap_poi_search(
    keyword: str,
    city: str = "",
    type_code: str | None = None,
    page: int = 1,
    size: int = 20,
    client: httpx.AsyncClient | None = None,
) -> list[Spot]:
    params: dict[str, str | int] = {
        "key": settings.amap_api_key,
        "keywords": keyword,
        "offset": size,
        "page": page,
        "extensions": "all",
    }
    if city:
        params["city"] = city
    if type_code:
        params["types"] = type_code

    should_close = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=10.0)

    try:
        resp = await client.get(f"{AMAP_BASE_URL}/place/text", params=params)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "1":
            return []

        spots: list[Spot] = []
        for poi in data.get("pois", []):
            location = _to_str(poi.get("location")) or "0,0"
            coords = location.split(",")
            longitude = _to_float(coords[0]) if len(coords) == 2 else None
            latitude = _to_float(coords[1]) if len(coords) == 2 else None
            biz_ext = _extract_biz_ext(poi)
            spots.append(
                Spot(
                    name=_to_str(poi.get("name")),
                    source_id=_to_str(poi.get("id")),
                    city=_to_str(poi.get("cityname")) or city,
                    longitude=longitude if longitude is not None else 0.0,
                    latitude=latitude if latitude is not None else 0.0,
                    type_tags=_to_str(poi.get("type")).split(";"),
                    address=_to_str(poi.get("address")),
                    tel=_to_str(poi.get("tel")),
                    images=_extract_photos(poi),
                    rating=_to_float(biz_ext.get("rating")),
                    open_time=_to_str(biz_ext.get("open_time")),
                    ticket_price=_to_float(biz_ext.get("cost")),
                )
            )
        return spots
    finally:
        if should_close:
            await client.aclose()


async def amap_route_plan(
    origin: str,
    destination: str,
    waypoints: list[str] | None = None,
    strategy: int = 0,
    client: httpx.AsyncClient | None = None,
) -> Route:
    params: dict[str, str | int] = {
        "key": settings.amap_api_key,
        "origin": origin,
        "destination": destination,
        "strategy": strategy,
    }
    if waypoints:
        params["waypoints"] = ";".join(waypoints)

    should_close = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=10.0)

    try:
        resp = await client.get(f"{AMAP_BASE_URL}/direction/driving", params=params)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "1":
            return Route(distance=0, duration=0)

        route_data = data.get("route", {})
        paths = route_data.get("paths", [])
        if not paths:
            return Route(distance=0, duration=0)

        best_path = paths[0]
        segments: list[RouteSegment] = []
        for step in best_path.get("steps", []):
            segments.append(
                RouteSegment(
                    origin=origin,
                    destination=destination,
                    distance=float(step.get("distance", 0)),
                    duration=float(step.get("duration", 0)),
                    steps=[step.get("instruction", "")],
                )
            )

        return Route(
            distance=float(best_path.get("distance", 0)),
            duration=float(best_path.get("duration", 0)),
            segments=segments,
        )
    finally:
        if should_close:
            await client.aclose()
