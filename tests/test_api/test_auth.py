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


async def test_register_success(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/register",
        json={"username": "testuser", "password": "password123", "email": "test@example.com"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "testuser"
    assert "user_id" in data


async def test_register_duplicate_username(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register",
        json={"username": "dup", "password": "password123", "email": "a@example.com"},
    )
    resp = await client.post(
        "/api/auth/register",
        json={"username": "dup", "password": "password123", "email": "b@example.com"},
    )
    assert resp.status_code == 409


async def test_register_duplicate_email(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register",
        json={"username": "user1", "password": "password123", "email": "same@example.com"},
    )
    resp = await client.post(
        "/api/auth/register",
        json={"username": "user2", "password": "password123", "email": "same@example.com"},
    )
    assert resp.status_code == 409


async def test_register_invalid_email(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/register",
        json={"username": "user", "password": "password123", "email": "notanemail"},
    )
    assert resp.status_code == 422


async def test_register_short_password(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/register",
        json={"username": "user", "password": "short", "email": "test@example.com"},
    )
    assert resp.status_code == 422


async def test_login_success(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register",
        json={"username": "loginuser", "password": "password123", "email": "login@example.com"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "loginuser", "password": "password123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register",
        json={"username": "wrongpw", "password": "password123", "email": "wp@example.com"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "wrongpw", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


async def test_login_nonexistent_user(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"username": "noone", "password": "password123"},
    )
    assert resp.status_code == 401


async def test_profile_with_token(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register",
        json={"username": "profuser", "password": "password123", "email": "prof@example.com"},
    )
    login_resp = await client.post(
        "/api/auth/login",
        json={"username": "profuser", "password": "password123"},
    )
    token = login_resp.json()["access_token"]
    resp = await client.get(
        "/api/user/profile", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "profuser"


async def test_profile_without_token(client: AsyncClient) -> None:
    resp = await client.get("/api/user/profile")
    assert resp.status_code in (401, 403)


async def test_update_profile(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register",
        json={"username": "upuser", "password": "password123", "email": "up@example.com"},
    )
    login_resp = await client.post(
        "/api/auth/login",
        json={"username": "upuser", "password": "password123"},
    )
    token = login_resp.json()["access_token"]
    resp = await client.put(
        "/api/user/profile",
        json={"username": "newname"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "newname"
