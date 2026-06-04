from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.crud.user import create_user, get_user_by_email, get_user_by_username
from backend.database import get_db
from backend.schemas.user import UserCreate
from backend.utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterResponse(BaseModel):
    user_id: int
    username: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


@router.post(
    "/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_in: UserCreate, db: AsyncSession = Depends(get_db)
) -> RegisterResponse:
    existing = await get_user_by_username(db, user_in.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="用户名已存在"
        )
    existing_email = await get_user_by_email(db, user_in.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="邮箱已被注册"
        )
    hashed = hash_password(user_in.password)
    user = await create_user(db, user_in, password_hash=hashed)
    return RegisterResponse(user_id=user.id, username=user.username)


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    user = await get_user_by_username(db, login_data.username)
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
        )
    token = create_access_token(data={"sub": str(user.id)})
    return LoginResponse(access_token=token)


@router.post("/logout", response_model=MessageResponse)
async def logout() -> MessageResponse:
    return MessageResponse(message="已成功登出")
