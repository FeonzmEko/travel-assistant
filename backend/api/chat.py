"""Agent 编排 / SSE 模块 — M5

提供聊天会话管理和流式消息接口，将规划 Agent 的输出转为 SSE 事件流。
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from backend.agents.planner import run_planner_stream
from backend.api.deps import get_current_user
from backend.crud.chat import (
    create_chat_message,
    create_chat_session,
    delete_chat_session,
    get_chat_session,
    get_messages_by_session,
    get_user_sessions,
)
from backend.database import get_db
from backend.models.user import User
from backend.schemas.chat import (
    ChatMessageCreate,
    ChatMessageOut,
    ChatSessionCreate,
    ChatSessionOut,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])

STREAM_TIMEOUT = 120.0


class SessionCreateResponse(BaseModel):
    session_id: int


class SessionListResponse(BaseModel):
    sessions: list[ChatSessionOut]


class HistoryResponse(BaseModel):
    messages: list[ChatMessageOut]


class MessageRequest(BaseModel):
    session_id: int
    content: str


# --------------- Session CRUD ---------------

@router.post("/session", response_model=SessionCreateResponse)
async def create_session(
    session_in: ChatSessionCreate | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionCreateResponse:
    if session_in is None:
        session_in = ChatSessionCreate()
    session = await create_chat_session(db, current_user.id, session_in)
    return SessionCreateResponse(session_id=session.id)


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    sessions = await get_user_sessions(db, current_user.id)
    return SessionListResponse(
        sessions=[ChatSessionOut.model_validate(s) for s in sessions]
    )


@router.get("/session/{session_id}/history", response_model=HistoryResponse)
async def get_history(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HistoryResponse:
    session = await get_chat_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    messages = await get_messages_by_session(db, session_id)
    return HistoryResponse(
        messages=[ChatMessageOut.model_validate(m) for m in messages]
    )


@router.delete("/session/{session_id}")
async def remove_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    session = await get_chat_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    await delete_chat_session(db, session)
    return {"message": "会话已删除"}


# --------------- SSE Message Endpoint ---------------

@router.post("/message")
async def send_message(
    msg: MessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    session = await get_chat_session(db, msg.session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")

    await create_chat_message(
        db,
        ChatMessageCreate(session_id=msg.session_id, role="user", content=msg.content),
    )

    db_messages = await get_messages_by_session(db, msg.session_id)
    history: list[dict[str, str]] = [
        {"role": m.role, "content": m.content}
        for m in db_messages[-10:]
    ]

    async def event_generator() -> AsyncGenerator[dict[str, str], None]:
        full_response = ""
        try:
            async for event in run_planner_stream(
                msg.content, history=history[:-1]
            ):
                event_type = str(event.get("type", ""))
                event_data = event.get("data", "")

                if event_type == "token":
                    full_response += str(event_data)
                    yield {"event": "token", "data": str(event_data)}
                elif event_type == "thinking":
                    yield {"event": "thinking", "data": str(event_data)}
                elif event_type == "tool_call":
                    yield {"event": "tool_call", "data": json.dumps(event_data, ensure_ascii=False)}
                elif event_type == "tool_result":
                    yield {"event": "tool_result", "data": json.dumps(event_data, ensure_ascii=False)}
                elif event_type == "trip_plan":
                    yield {"event": "trip_plan", "data": json.dumps(event_data, ensure_ascii=False)}
                elif event_type == "done":
                    done_data = event.get("data", {})
                    if isinstance(done_data, dict):
                        full_response = str(done_data.get("text", full_response))
                elif event_type == "error":
                    yield {"event": "error", "data": str(event_data)}

            await create_chat_message(
                db,
                ChatMessageCreate(
                    session_id=msg.session_id,
                    role="assistant",
                    content=full_response,
                ),
            )
            yield {"event": "done", "data": ""}

        except asyncio.TimeoutError:
            yield {"event": "error", "data": "请求超时，请重试"}
        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())
