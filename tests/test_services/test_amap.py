import httpx
import pytest
import respx

from backend.services.amap import amap_poi_search, amap_route_plan


@respx.mock
async def test_poi_search_success() -> None:
    respx.get("https://restapi.amap.com/v3/place/text").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "1",
                "count": "1",
                "pois": [
                    {
                        "id": "B000A8UIN8",
                        "name": "故宫博物院",
                        "type": "风景名胜;风景名胜;世界遗产",
                        "location": "116.397026,39.918058",
                        "cityname": "北京市",
                        "address": "景山前街4号",
                        "tel": "010-85007938",
                    }
                ],
            },
        )
    )

    async with httpx.AsyncClient() as client:
        spots = await amap_poi_search("故宫", "北京", client=client)

    assert len(spots) == 1
    assert spots[0].name == "故宫博物院"
    assert spots[0].source_id == "B000A8UIN8"
    assert spots[0].longitude == pytest.approx(116.397026)


@respx.mock
async def test_poi_search_extracts_photos_and_rating() -> None:
    respx.get("https://restapi.amap.com/v3/place/text").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "1",
                "count": "1",
                "pois": [
                    {
                        "id": "B1",
                        "name": "西湖",
                        "type": "风景名胜",
                        "location": "120.149780,30.247478",
                        "cityname": "杭州市",
                        "address": "西湖区",
                        "tel": "0571-12345678",
                        "photos": [
                            {"title": "", "url": "http://img.example/1.jpg"},
                            {"url": "http://img.example/2.jpg"},
                            {"title": "no-url"},
                        ],
                        "biz_ext": {"rating": "4.7", "cost": "80"},
                    }
                ],
            },
        )
    )

    async with httpx.AsyncClient() as client:
        spots = await amap_poi_search("西湖", "杭州", client=client)

    assert spots[0].images == [
        "http://img.example/1.jpg",
        "http://img.example/2.jpg",
    ]
    assert spots[0].rating == pytest.approx(4.7)
    assert spots[0].ticket_price == pytest.approx(80)


@respx.mock
async def test_poi_search_handles_empty_biz_ext() -> None:
    respx.get("https://restapi.amap.com/v3/place/text").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "1",
                "count": "1",
                "pois": [
                    {
                        "id": "B2",
                        "name": "某地",
                        "type": "风景名胜",
                        "location": "120.0,30.0",
                        "cityname": "杭州市",
                        "biz_ext": [],
                        "photos": [],
                    }
                ],
            },
        )
    )

    async with httpx.AsyncClient() as client:
        spots = await amap_poi_search("某地", "杭州", client=client)

    assert spots[0].rating is None
    assert spots[0].ticket_price is None
    assert spots[0].images == []


@respx.mock
async def test_poi_search_api_error() -> None:
    respx.get("https://restapi.amap.com/v3/place/text").mock(
        return_value=httpx.Response(
            200, json={"status": "0", "info": "INVALID_USER_KEY"}
        )
    )

    async with httpx.AsyncClient() as client:
        spots = await amap_poi_search("故宫", "北京", client=client)

    assert spots == []


@respx.mock
async def test_poi_search_http_error() -> None:
    respx.get("https://restapi.amap.com/v3/place/text").mock(
        return_value=httpx.Response(500)
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.HTTPStatusError):
            await amap_poi_search("故宫", "北京", client=client)


@respx.mock
async def test_route_plan_success() -> None:
    respx.get("https://restapi.amap.com/v3/direction/driving").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "1",
                "route": {
                    "paths": [
                        {
                            "distance": "15000",
                            "duration": "1800",
                            "steps": [
                                {
                                    "instruction": "沿XX路向东行驶",
                                    "distance": "5000",
                                    "duration": "600",
                                }
                            ],
                        }
                    ]
                },
            },
        )
    )

    async with httpx.AsyncClient() as client:
        route = await amap_route_plan(
            "116.397026,39.918058",
            "116.427281,39.903719",
            client=client,
        )

    assert route.distance == 15000.0
    assert route.duration == 1800.0
    assert len(route.segments) == 1


@respx.mock
async def test_route_plan_api_error() -> None:
    respx.get("https://restapi.amap.com/v3/direction/driving").mock(
        return_value=httpx.Response(200, json={"status": "0"})
    )

    async with httpx.AsyncClient() as client:
        route = await amap_route_plan("116.0,39.0", "117.0,40.0", client=client)

    assert route.distance == 0
    assert route.duration == 0
