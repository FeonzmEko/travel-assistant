from dataclasses import dataclass, field

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


async def amap_poi_search(
    keyword: str,
    city: str,
    type_code: str | None = None,
    page: int = 1,
    size: int = 20,
    client: httpx.AsyncClient | None = None,
) -> list[Spot]:
    params: dict[str, str | int] = {
        "key": settings.amap_api_key,
        "keywords": keyword,
        "city": city,
        "offset": size,
        "page": page,
        "extensions": "all",
    }
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
            location = poi.get("location", "0,0").split(",")
            spots.append(
                Spot(
                    name=poi.get("name", ""),
                    source_id=poi.get("id", ""),
                    city=poi.get("cityname", city),
                    longitude=float(location[0]) if len(location) == 2 else 0.0,
                    latitude=float(location[1]) if len(location) == 2 else 0.0,
                    type_tags=poi.get("type", "").split(";"),
                    address=poi.get("address", ""),
                    tel=poi.get("tel", ""),
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
