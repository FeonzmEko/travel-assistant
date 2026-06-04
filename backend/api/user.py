from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.crud.user import get_user_by_email, get_user_by_username, update_user
from backend.database import get_db
from backend.models.user import User
from backend.schemas.user import UserOut, UserUpdate

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/profile", response_model=UserOut)
async def get_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.put("/profile", response_model=UserOut)
async def update_profile(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if user_in.username and user_in.username != current_user.username:
        existing = await get_user_by_username(db, user_in.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="用户名已存在"
            )
    if user_in.email and user_in.email != current_user.email:
        existing = await get_user_by_email(db, user_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="邮箱已被注册"
            )
    return await update_user(db, current_user, user_in)
