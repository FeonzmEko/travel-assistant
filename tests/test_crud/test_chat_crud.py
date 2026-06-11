import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.crud.chat import (
    create_chat_message,
    create_chat_session,
    delete_chat_session,
    get_chat_session,
    get_messages_by_session,
    get_user_sessions,
    update_chat_session,
)
from backend.crud.user import create_user
from backend.schemas.chat import ChatMessageCreate, ChatSessionCreate, ChatSessionUpdate
from backend.schemas.user import UserCreate


@pytest.fixture
async def user_id(db: AsyncSession) -> int:
    user = await create_user(
        db,
        UserCreate(
            username="chatuser", password="password123", email="chat@example.com"
        ),
        password_hash="hashed",
    )
    return user.id


async def test_create_session(db: AsyncSession, user_id: int) -> None:
    session = await create_chat_session(
        db, user_id, ChatSessionCreate(title="测试对话")
    )
    assert session.id is not None
    assert session.title == "测试对话"
    assert session.user_id == user_id


async def test_get_session(db: AsyncSession, user_id: int) -> None:
    session = await create_chat_session(db, user_id, ChatSessionCreate(title="测试"))
    found = await get_chat_session(db, session.id)
    assert found is not None
    assert found.title == "测试"


async def test_get_user_sessions(db: AsyncSession, user_id: int) -> None:
    await create_chat_session(db, user_id, ChatSessionCreate(title="对话1"))
    await create_chat_session(db, user_id, ChatSessionCreate(title="对话2"))
    sessions = await get_user_sessions(db, user_id)
    assert len(sessions) == 2


async def test_update_session(db: AsyncSession, user_id: int) -> None:
    session = await create_chat_session(db, user_id, ChatSessionCreate(title="旧标题"))
    updated = await update_chat_session(db, session, ChatSessionUpdate(title="新标题"))
    assert updated.title == "新标题"


async def test_delete_session(db: AsyncSession, user_id: int) -> None:
    session = await create_chat_session(
        db, user_id, ChatSessionCreate(title="删除测试")
    )
    await delete_chat_session(db, session)
    found = await get_chat_session(db, session.id)
    assert found is None


async def test_create_and_get_messages(db: AsyncSession, user_id: int) -> None:
    session = await create_chat_session(
        db, user_id, ChatSessionCreate(title="消息测试")
    )
    await create_chat_message(
        db, ChatMessageCreate(session_id=session.id, role="user", content="你好")
    )
    await create_chat_message(
        db,
        ChatMessageCreate(session_id=session.id, role="assistant", content="你好！"),
    )
    messages = await get_messages_by_session(db, session.id)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"


async def test_cascade_delete_messages(db: AsyncSession, user_id: int) -> None:
    session = await create_chat_session(
        db, user_id, ChatSessionCreate(title="级联删除")
    )
    await create_chat_message(
        db, ChatMessageCreate(session_id=session.id, role="user", content="test")
    )
    await delete_chat_session(db, session)
    messages = await get_messages_by_session(db, session.id)
    assert len(messages) == 0
