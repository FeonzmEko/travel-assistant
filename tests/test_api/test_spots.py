from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.database import Base, get_db
from backend.main import app
from backend.services.amap import Spot


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _make_amap_spots(count: int = 2, city: str = "北京") -> list[Spot]:
    return [
        Spot(
            name=f"景点{i}",
            source_id=f"amap_{i}",
            city=city,
            longitude=116.0 + i * 0.01,
            latitude=39.0 + i * 0.01,
            type_tags=["风景名胜"],
        )
        for i in range(1, count + 1)
    ]


class TestSpotSearch:
    """GET /api/spots/search"""

    @patch("backend.api.spots.amap_poi_search", new_callable=AsyncMock)
    async def test_cache_miss_fetches_from_amap(
        self, mock_amap: AsyncMock, client: AsyncClient
    ) -> None:
        mock_amap.return_value = _make_amap_spots(2)

        resp = await client.get(
            "/api/spots/search", params={"keyword": "故宫", "city": "北京"}
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["source"] == "amap"
        mock_amap.assert_called_once()

    @patch("backend.api.spots.amap_poi_search", new_callable=AsyncMock)
    async def test_cache_hit_skips_amap(
        self, mock_amap: AsyncMock, client: AsyncClient
    ) -> None:
        mock_amap.return_value = _make_amap_spots(2)

        await client.get(
            "/api/spots/search", params={"keyword": "故宫", "city": "北京"}
        )
        mock_amap.reset_mock()

        resp = await client.get(
            "/api/spots/search", params={"keyword": "景点", "city": "北京"}
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        mock_amap.assert_not_called()

    async def test_search_no_params_returns_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/spots/search")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    @patch("backend.api.spots.amap_poi_search", new_callable=AsyncMock)
    async def test_pagination(self, mock_amap: AsyncMock, client: AsyncClient) -> None:
        mock_amap.return_value = _make_amap_spots(5)

        await client.get(
            "/api/spots/search", params={"keyword": "公园", "city": "北京"}
        )
        mock_amap.reset_mock()

        resp = await client.get(
            "/api/spots/search",
            params={"keyword": "景点", "city": "北京", "page": 1, "size": 2},
        )
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2

        resp2 = await client.get(
            "/api/spots/search",
            params={"keyword": "景点", "city": "北京", "page": 2, "size": 2},
        )
        data2 = resp2.json()
        assert len(data2["items"]) == 2

    @patch("backend.api.spots.amap_poi_search", new_callable=AsyncMock)
    async def test_filter_by_type(
        self, mock_amap: AsyncMock, client: AsyncClient
    ) -> None:
        mock_amap.return_value = _make_amap_spots(2)

        await client.get(
            "/api/spots/search", params={"keyword": "景点", "city": "北京"}
        )
        mock_amap.reset_mock()

        resp = await client.get(
            "/api/spots/search",
            params={"keyword": "景点", "city": "北京", "type": "风景名胜"},
        )
        data = resp.json()
        assert data["total"] == 2

        resp2 = await client.get(
            "/api/spots/search",
            params={"keyword": "景点", "city": "北京", "type": "不存在的类型"},
        )
        data2 = resp2.json()
        assert data2["total"] == 0


class TestSpotDetail:
    """GET /api/spots/{id}"""

    @patch("backend.api.spots.amap_poi_search", new_callable=AsyncMock)
    async def test_get_existing_spot(
        self, mock_amap: AsyncMock, client: AsyncClient
    ) -> None:
        mock_amap.return_value = _make_amap_spots(1)

        await client.get(
            "/api/spots/search", params={"keyword": "故宫", "city": "北京"}
        )

        resp = await client.get("/api/spots/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["name"] == "景点1"

    async def test_get_nonexistent_spot(self, client: AsyncClient) -> None:
        resp = await client.get("/api/spots/999")
        assert resp.status_code == 404
