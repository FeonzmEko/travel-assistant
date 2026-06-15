"""Agent 编排 / SSE 模块 — M5

提供聊天会话管理和流式消息接口，将规划 Agent 的输出转为 SSE 事件流。
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from backend.agents.planner import run_planner_stream
from backend.api.deps import get_current_user
from backend.config import settings
from backend.crud.chat import (
    create_chat_message,
    create_chat_session,
    delete_chat_session,
    get_chat_session,
    get_messages_by_session,
    get_user_sessions,
    update_chat_session,
)
from backend.database import get_db
from backend.models.user import User
from backend.schemas.chat import (
    ChatMessageCreate,
    ChatMessageOut,
    ChatSessionCreate,
    ChatSessionOut,
    ChatSessionUpdate,
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


# --------------- Title Generation ---------------


TITLE_SYSTEM_PROMPT = (
    "根据用户的旅游需求，生成一个极其简短的对话标题（不超过10个字）。"
    "只输出标题，不要引号、不要解释、不要标点。"
    "例如：北京三日游、杭州周末行、西藏十日自驾、成都美食之旅"
)


async def _generate_title(user_message: str) -> str | None:
    """调用 LLM 根据用户首条消息生成简短标题。"""
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )
    try:
        response = await client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": TITLE_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=20,
            temperature=0.3,
        )
        title = response.choices[0].message.content
        if title:
            return title.strip()[:20]
    except Exception:
        pass
    return None


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
        {"role": m.role, "content": m.content} for m in db_messages[-10:]
    ]

    async def event_generator() -> AsyncGenerator[dict[str, str], None]:
        full_response = ""
        clean_text = ""
        try:
            async for event in run_planner_stream(msg.content, history=history[:-1]):
                event_type = str(event.get("type", ""))
                event_data = event.get("data", "")

                if event_type == "token":
                    full_response += str(event_data)
                    yield {"event": "token", "data": str(event_data)}
                elif event_type == "trip_plan":
                    yield {
                        "event": "trip_plan",
                        "data": json.dumps(event_data, ensure_ascii=False),
                    }
                elif event_type == "done":
                    done_data = event.get("data", {})
                    if isinstance(done_data, dict):
                        # 使用 planner 清洗后的展示文本（已去除 TripPlan JSON 代码块）
                        clean_text = str(done_data.get("text", full_response))
                        full_response = clean_text
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

            # 首轮对话自动生成标题
            done_payload: dict[str, str] = {}
            # 将清洗后的展示文本转发给前端，用于替换流式累积的原始内容
            if clean_text:
                done_payload["text"] = clean_text
            if session.title == "新对话":
                new_title = await _generate_title(msg.content)
                if new_title:
                    await update_chat_session(
                        db, session, ChatSessionUpdate(title=new_title)
                    )
                    done_payload["title"] = new_title

            yield {
                "event": "done",
                "data": json.dumps(done_payload, ensure_ascii=False),
            }

        except TimeoutError:
            yield {"event": "error", "data": "请求超时，请重试"}
        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())
