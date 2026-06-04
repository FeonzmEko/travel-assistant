import httpx
import respx

from backend.services.weather import weather_query


@respx.mock
async def test_weather_query_success() -> None:
    respx.get("https://restapi.amap.com/v3/weather/weatherInfo").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "1",
                "forecasts": [
                    {
                        "city": "北京市",
                        "casts": [
                            {
                                "date": "2025-07-01",
                                "dayweather": "晴",
                                "nightweather": "多云",
                                "daytemp": "35",
                                "nighttemp": "25",
                                "daywind": "南",
                                "nightwind": "南",
                                "daypower": "≤3",
                                "nightpower": "≤3",
                            },
                            {
                                "date": "2025-07-02",
                                "dayweather": "多云",
                                "nightweather": "阴",
                                "daytemp": "33",
                                "nighttemp": "24",
                                "daywind": "东",
                                "nightwind": "东",
                                "daypower": "≤3",
                                "nightpower": "≤3",
                            },
                        ],
                    }
                ],
            },
        )
    )

    async with httpx.AsyncClient() as client:
        forecasts = await weather_query("北京", client=client)

    assert len(forecasts) == 2
    assert forecasts[0].dayweather == "晴"
    assert forecasts[0].daytemp == "35"


@respx.mock
async def test_weather_query_api_error() -> None:
    respx.get("https://restapi.amap.com/v3/weather/weatherInfo").mock(
        return_value=httpx.Response(200, json={"status": "0"})
    )

    async with httpx.AsyncClient() as client:
        forecasts = await weather_query("北京", client=client)

    assert forecasts == []
