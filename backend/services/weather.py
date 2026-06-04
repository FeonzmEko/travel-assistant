from dataclasses import dataclass

import httpx

from backend.config import settings

AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"


@dataclass
class WeatherForecast:
    date: str
    dayweather: str
    nightweather: str
    daytemp: str
    nighttemp: str
    daywind: str
    nightwind: str
    daypower: str
    nightpower: str


async def weather_query(
    city: str,
    client: httpx.AsyncClient | None = None,
) -> list[WeatherForecast]:
    params = {
        "key": settings.amap_api_key,
        "city": city,
        "extensions": "all",
    }

    should_close = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=10.0)

    try:
        resp = await client.get(AMAP_WEATHER_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "1":
            return []

        forecasts: list[WeatherForecast] = []
        forecast_list = data.get("forecasts", [])
        if not forecast_list:
            return []
        for cast in forecast_list[0].get("casts", []):
            forecasts.append(
                WeatherForecast(
                    date=cast.get("date", ""),
                    dayweather=cast.get("dayweather", ""),
                    nightweather=cast.get("nightweather", ""),
                    daytemp=cast.get("daytemp", ""),
                    nighttemp=cast.get("nighttemp", ""),
                    daywind=cast.get("daywind", ""),
                    nightwind=cast.get("nightwind", ""),
                    daypower=cast.get("daypower", ""),
                    nightpower=cast.get("nightpower", ""),
                )
            )
        return forecasts
    finally:
        if should_close:
            await client.aclose()
