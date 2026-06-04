"""Chat API (M5) 测试

Mock Agent，测试 SSE 事件流格式、会话 CRUD、对话历史。
"""

from __future__ import annotations

import json
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


async def _register_and_login(client: AsyncClient, username: str = "chatuser") -> str:
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


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# =================== Session CRUD 测试 ===================

class TestSessionCRUD:
    async def test_create_session(self, client: AsyncClient) -> None:
        token = await _register_and_login(client)
        resp = await client.post(
            "/api/chat/session",
            json={"title": "测试会话"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert isinstance(data["session_id"], int)

    async def test_create_session_default_title(self, client: AsyncClient) -> None:
        token = await _register_and_login(client)
        resp = await client.post("/api/chat/session", headers=_auth(token))
        assert resp.status_code == 200
        assert "session_id" in resp.json()

    async def test_list_sessions(self, client: AsyncClient) -> None:
        token = await _register_and_login(client)
        await client.post(
            "/api/chat/session", json={"title": "会话1"}, headers=_auth(token)
        )
        await client.post(
            "/api/chat/session", json={"title": "会话2"}, headers=_auth(token)
        )

        resp = await client.get("/api/chat/sessions", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "sessions" in data
        assert len(data["sessions"]) == 2

    async def test_list_sessions_empty(self, client: AsyncClient) -> None:
        token = await _register_and_login(client)
        resp = await client.get("/api/chat/sessions", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["sessions"] == []

    async def test_delete_session(self, client: AsyncClient) -> None:
        token = await _register_and_login(client)
        create_resp = await client.post(
            "/api/chat/session", json={"title": "待删除"}, headers=_auth(token)
        )
        sid = create_resp.json()["session_id"]

        resp = await client.delete(f"/api/chat/session/{sid}", headers=_auth(token))
        assert resp.status_code == 200

        resp = await client.get("/api/chat/sessions", headers=_auth(token))
        assert len(resp.json()["sessions"]) == 0

    async def test_delete_nonexistent_session(self, client: AsyncClient) -> None:
        token = await _register_and_login(client)
        resp = await client.delete("/api/chat/session/9999", headers=_auth(token))
        assert resp.status_code == 404

    async def test_session_isolation(self, client: AsyncClient) -> None:
        token1 = await _register_and_login(client, "user_a")
        token2 = await _register_and_login(client, "user_b")

        create_resp = await client.post(
            "/api/chat/session", json={"title": "A的会话"}, headers=_auth(token1)
        )
        sid = create_resp.json()["session_id"]

        resp = await client.delete(f"/api/chat/session/{sid}", headers=_auth(token2))
        assert resp.status_code == 404

    async def test_unauthenticated_session(self, client: AsyncClient) -> None:
        resp = await client.post("/api/chat/session")
        assert resp.status_code in (401, 403)


# =================== History 测试 ===================

class TestHistory:
    async def test_get_empty_history(self, client: AsyncClient) -> None:
        token = await _register_and_login(client)
        create_resp = await client.post(
            "/api/chat/session", headers=_auth(token)
        )
        sid = create_resp.json()["session_id"]

        resp = await client.get(
            f"/api/chat/session/{sid}/history", headers=_auth(token)
        )
        assert resp.status_code == 200
        assert resp.json()["messages"] == []

    async def test_history_not_found(self, client: AsyncClient) -> None:
        token = await _register_and_login(client)
        resp = await client.get(
            "/api/chat/session/9999/history", headers=_auth(token)
        )
        assert resp.status_code == 404

    async def test_history_isolation(self, client: AsyncClient) -> None:
        token1 = await _register_and_login(client, "hist_a")
        token2 = await _register_and_login(client, "hist_b")

        create_resp = await client.post(
            "/api/chat/session", headers=_auth(token1)
        )
        sid = create_resp.json()["session_id"]

        resp = await client.get(
            f"/api/chat/session/{sid}/history", headers=_auth(token2)
        )
        assert resp.status_code == 404


# =================== SSE Message 测试 ===================

def _make_fake_stream(events: list[dict]):  # type: ignore[type-arg]
    """创建一个假的 run_planner_stream 异步生成器。"""
    async def fake_stream(user_message: str, history: list | None = None):  # type: ignore[type-arg]
        for evt in events:
            yield evt
    return fake_stream


class TestSSEMessage:
    @patch("backend.api.chat.run_planner_stream")
    async def test_sse_token_events(
        self, mock_stream: AsyncMock, client: AsyncClient
    ) -> None:
        mock_stream.side_effect = _make_fake_stream([
            {"type": "token", "data": "你好"},
            {"type": "token", "data": "世界"},
            {"type": "done", "data": {"text": "你好世界"}},
        ])

        token = await _register_and_login(client)
        create_resp = await client.post(
            "/api/chat/session", headers=_auth(token)
        )
        sid = create_resp.json()["session_id"]

        resp = await client.post(
            "/api/chat/message",
            json={"session_id": sid, "content": "你好"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        body = resp.text
        assert "event: token" in body
        assert "event: done" in body

    @patch("backend.api.chat.run_planner_stream")
    async def test_sse_tool_events(
        self, mock_stream: AsyncMock, client: AsyncClient
    ) -> None:
        mock_stream.side_effect = _make_fake_stream([
            {"type": "tool_call", "data": {"tool": "find_spots_tool"}},
            {"type": "tool_result", "data": {"output": "[{\"name\":\"故宫\"}]"}},
            {"type": "token", "data": "查到了"},
            {"type": "done", "data": {"text": "查到了"}},
        ])

        token = await _register_and_login(client)
        create_resp = await client.post(
            "/api/chat/session", headers=_auth(token)
        )
        sid = create_resp.json()["session_id"]

        resp = await client.post(
            "/api/chat/message",
            json={"session_id": sid, "content": "搜索景点"},
            headers=_auth(token),
        )
        body = resp.text
        assert "event: tool_call" in body
        assert "event: tool_result" in body

    @patch("backend.api.chat.run_planner_stream")
    async def test_sse_trip_plan_event(
        self, mock_stream: AsyncMock, client: AsyncClient
    ) -> None:
        plan = {"title": "北京三日游", "destination": "北京"}
        mock_stream.side_effect = _make_fake_stream([
            {"type": "token", "data": "行程如下"},
            {"type": "trip_plan", "data": plan},
            {"type": "done", "data": {"text": "行程如下"}},
        ])

        token = await _register_and_login(client)
        create_resp = await client.post(
            "/api/chat/session", headers=_auth(token)
        )
        sid = create_resp.json()["session_id"]

        resp = await client.post(
            "/api/chat/message",
            json={"session_id": sid, "content": "规划行程"},
            headers=_auth(token),
        )
        body = resp.text
        assert "event: trip_plan" in body
        assert "北京三日游" in body

    @patch("backend.api.chat.run_planner_stream")
    async def test_sse_error_event(
        self, mock_stream: AsyncMock, client: AsyncClient
    ) -> None:
        mock_stream.side_effect = _make_fake_stream([
            {"type": "error", "data": "LLM API error"},
        ])

        token = await _register_and_login(client)
        create_resp = await client.post(
            "/api/chat/session", headers=_auth(token)
        )
        sid = create_resp.json()["session_id"]

        resp = await client.post(
            "/api/chat/message",
            json={"session_id": sid, "content": "test"},
            headers=_auth(token),
        )
        body = resp.text
        assert "event: error" in body

    @patch("backend.api.chat.run_planner_stream")
    async def test_message_saves_to_history(
        self, mock_stream: AsyncMock, client: AsyncClient
    ) -> None:
        mock_stream.side_effect = _make_fake_stream([
            {"type": "token", "data": "回复内容"},
            {"type": "done", "data": {"text": "回复内容"}},
        ])

        token = await _register_and_login(client)
        create_resp = await client.post(
            "/api/chat/session", headers=_auth(token)
        )
        sid = create_resp.json()["session_id"]

        await client.post(
            "/api/chat/message",
            json={"session_id": sid, "content": "用户问题"},
            headers=_auth(token),
        )

        resp = await client.get(
            f"/api/chat/session/{sid}/history", headers=_auth(token)
        )
        messages = resp.json()["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "用户问题"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "回复内容"

    async def test_message_invalid_session(self, client: AsyncClient) -> None:
        token = await _register_and_login(client)
        resp = await client.post(
            "/api/chat/message",
            json={"session_id": 9999, "content": "test"},
            headers=_auth(token),
        )
        assert resp.status_code == 404

    async def test_message_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/chat/message",
            json={"session_id": 1, "content": "test"},
        )
        assert resp.status_code in (401, 403)
