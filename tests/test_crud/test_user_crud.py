import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.crud.user import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    update_user,
)
from backend.schemas.user import UserCreate, UserUpdate


@pytest.fixture
def user_data() -> UserCreate:
    return UserCreate(username="testuser", password="password123", email="test@example.com")


async def test_create_user(db: AsyncSession, user_data: UserCreate) -> None:
    user = await create_user(db, user_data, password_hash="hashed_pw")
    assert user.id is not None
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.password_hash == "hashed_pw"


async def test_get_user_by_id(db: AsyncSession, user_data: UserCreate) -> None:
    user = await create_user(db, user_data, password_hash="hashed_pw")
    found = await get_user_by_id(db, user.id)
    assert found is not None
    assert found.username == "testuser"


async def test_get_user_by_id_not_found(db: AsyncSession) -> None:
    found = await get_user_by_id(db, 999)
    assert found is None


async def test_get_user_by_username(db: AsyncSession, user_data: UserCreate) -> None:
    await create_user(db, user_data, password_hash="hashed_pw")
    found = await get_user_by_username(db, "testuser")
    assert found is not None
    assert found.email == "test@example.com"


async def test_get_user_by_email(db: AsyncSession, user_data: UserCreate) -> None:
    await create_user(db, user_data, password_hash="hashed_pw")
    found = await get_user_by_email(db, "test@example.com")
    assert found is not None
    assert found.username == "testuser"


async def test_update_user(db: AsyncSession, user_data: UserCreate) -> None:
    user = await create_user(db, user_data, password_hash="hashed_pw")
    updated = await update_user(db, user, UserUpdate(username="newname"))
    assert updated.username == "newname"
    assert updated.email == "test@example.com"
