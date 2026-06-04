from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.chat import ChatMessage, ChatSession
from backend.schemas.chat import ChatMessageCreate, ChatSessionCreate, ChatSessionUpdate


async def create_chat_session(
    db: AsyncSession, user_id: int, session_in: ChatSessionCreate
) -> ChatSession:
    session = ChatSession(user_id=user_id, title=session_in.title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_chat_session(db: AsyncSession, session_id: int) -> ChatSession | None:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id)
        .options(selectinload(ChatSession.messages))
    )
    return result.scalar_one_or_none()


async def get_user_sessions(db: AsyncSession, user_id: int) -> list[ChatSession]:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
    )
    return list(result.scalars().all())


async def update_chat_session(
    db: AsyncSession, session: ChatSession, session_in: ChatSessionUpdate
) -> ChatSession:
    update_data = session_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(session, field, value)
    await db.commit()
    await db.refresh(session)
    return session


async def delete_chat_session(db: AsyncSession, session: ChatSession) -> None:
    await db.delete(session)
    await db.commit()


async def create_chat_message(
    db: AsyncSession, message_in: ChatMessageCreate
) -> ChatMessage:
    message = ChatMessage(
        session_id=message_in.session_id,
        role=message_in.role,
        content=message_in.content,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_messages_by_session(
    db: AsyncSession, session_id: int
) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    return list(result.scalars().all())
