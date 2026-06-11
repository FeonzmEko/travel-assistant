from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.database import Base, get_db
from backend.main import app

TRIP_PAYLOAD = {
    "title": "东京五日游",
    "destination": "东京",
    "start_date": "2025-08-01",
    "end_date": "2025-08-05",
    "budget_total": 15000.0,
    "budget_breakdown": "交通5000,住宿5000,餐饮3000,门票2000",
    "days": [
        {
            "day_index": 1,
            "date": "2025-08-01",
            "weather": "晴",
            "activities": [
                {
                    "order_index": 1,
                    "spot_name": "浅草寺",
                    "time_slot": "09:00-12:00",
                    "transport": "地铁",
                    "notes": "早起避开人流",
                    "estimated_cost": 500.0,
                    "longitude": 139.7967,
                    "latitude": 35.7148,
                },
                {
                    "order_index": 2,
                    "spot_name": "东京塔",
                    "time_slot": "14:00-17:00",
                    "transport": "步行",
                    "notes": None,
                    "estimated_cost": 1200.0,
                    "longitude": 139.7454,
                    "latitude": 35.6586,
                },
            ],
        },
        {
            "day_index": 2,
            "date": "2025-08-02",
            "weather": "多云",
            "activities": [
                {
                    "order_index": 1,
                    "spot_name": "秋叶原",
                    "time_slot": "10:00-18:00",
                    "transport": "电车",
                    "notes": "买手办",
                    "estimated_cost": 3000.0,
                    "longitude": 139.7731,
                    "latitude": 35.6984,
                }
            ],
        },
    ],
}


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


async def _register_and_login(client: AsyncClient, username: str = "user1") -> str:
    await client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "password123",
            "email": f"{username}@example.com",
        },
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": username, "password": "password123"},
    )
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_create_trip(client: AsyncClient) -> None:
    token = await _register_and_login(client)
    resp = await client.post(
        "/api/trips", json=TRIP_PAYLOAD, headers=_auth_headers(token)
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "trip_id" in data
    assert isinstance(data["trip_id"], int)


async def test_list_trips(client: AsyncClient) -> None:
    token = await _register_and_login(client)
    await client.post("/api/trips", json=TRIP_PAYLOAD, headers=_auth_headers(token))
    resp = await client.get("/api/trips", headers=_auth_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "东京五日游"


async def test_get_trip_detail(client: AsyncClient) -> None:
    token = await _register_and_login(client)
    create_resp = await client.post(
        "/api/trips", json=TRIP_PAYLOAD, headers=_auth_headers(token)
    )
    trip_id = create_resp.json()["trip_id"]

    resp = await client.get(f"/api/trips/{trip_id}", headers=_auth_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "东京五日游"
    assert data["destination"] == "东京"
    assert len(data["days"]) == 2
    assert len(data["days"][0]["activities"]) == 2
    first_activity = data["days"][0]["activities"][0]
    assert first_activity["longitude"] == 139.7967
    assert first_activity["latitude"] == 35.7148


async def test_delete_trip(client: AsyncClient) -> None:
    token = await _register_and_login(client)
    create_resp = await client.post(
        "/api/trips", json=TRIP_PAYLOAD, headers=_auth_headers(token)
    )
    trip_id = create_resp.json()["trip_id"]

    resp = await client.delete(f"/api/trips/{trip_id}", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["message"] == "行程已删除"

    resp = await client.get(f"/api/trips/{trip_id}", headers=_auth_headers(token))
    assert resp.status_code == 404


async def test_trip_access_forbidden(client: AsyncClient) -> None:
    token1 = await _register_and_login(client, "owner")
    token2 = await _register_and_login(client, "other")

    create_resp = await client.post(
        "/api/trips", json=TRIP_PAYLOAD, headers=_auth_headers(token1)
    )
    trip_id = create_resp.json()["trip_id"]

    resp = await client.get(f"/api/trips/{trip_id}", headers=_auth_headers(token2))
    assert resp.status_code == 403

    resp = await client.delete(f"/api/trips/{trip_id}", headers=_auth_headers(token2))
    assert resp.status_code == 403


async def test_export_pdf(client: AsyncClient) -> None:
    token = await _register_and_login(client)
    create_resp = await client.post(
        "/api/trips", json=TRIP_PAYLOAD, headers=_auth_headers(token)
    )
    trip_id = create_resp.json()["trip_id"]

    resp = await client.get(
        f"/api/trips/{trip_id}/export", headers=_auth_headers(token)
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


async def test_export_pdf_twice(client: AsyncClient) -> None:
    token = await _register_and_login(client)
    create_resp = await client.post(
        "/api/trips", json=TRIP_PAYLOAD, headers=_auth_headers(token)
    )
    trip_id = create_resp.json()["trip_id"]

    first_resp = await client.get(
        f"/api/trips/{trip_id}/export", headers=_auth_headers(token)
    )
    second_resp = await client.get(
        f"/api/trips/{trip_id}/export", headers=_auth_headers(token)
    )

    assert first_resp.status_code == 200
    assert second_resp.status_code == 200
    assert first_resp.content[:4] == b"%PDF"
    assert second_resp.content[:4] == b"%PDF"


async def test_create_trip_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post("/api/trips", json=TRIP_PAYLOAD)
    assert resp.status_code in (401, 403)


async def test_list_trips_empty(client: AsyncClient) -> None:
    token = await _register_and_login(client)
    resp = await client.get("/api/trips", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json() == {"total": 0, "items": []}
