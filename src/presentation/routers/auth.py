from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.schemas import AuthUserDTO, TokenResponseDTO, UserRegisterDTO
from src.infrastructure.config import settings
from src.infrastructure.database.models.tables import UserModel
from src.infrastructure.database.session import get_db_session

router = APIRouter(tags=["Auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def _create_access_token(data: dict) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=settings.access_token_expire_hours)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    body: UserRegisterDTO,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    raw_role = (body.role or "member").strip().lower()
    role = "member" if raw_role == "user" else raw_role
    allowed_roles = {"member", "viewer", "admin"}
    if role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    existing_stmt = select(UserModel).where(
        or_(UserModel.username == body.username, UserModel.email == str(body.email))
    )
    existing = (await session.execute(existing_stmt)).scalars().first()
    if existing:
        if existing.username == body.username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    new_user = UserModel(
        username=body.username,
        email=str(body.email),
        hashed_password=pwd_context.hash(body.password),
        role=role,
    )
    session.add(new_user)
    await session.commit()
    return {"msg": "User registered successfully"}


@router.post("/token", response_model=TokenResponseDTO)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponseDTO:
    stmt = select(UserModel).where(UserModel.username == form_data.username)
    user = (await session.execute(stmt)).scalars().first()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    token = _create_access_token(
        {
            "sub": user.username,
            "email": user.email,
            "role": user.role,
        }
    )
    return TokenResponseDTO(access_token=token, token_type="bearer")


@router.get("/me", response_model=AuthUserDTO)
async def read_users_me(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> AuthUserDTO:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        username = payload.get("sub")
        role = payload.get("role")
        if not isinstance(username, str) or not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        if not isinstance(role, str) or not role:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    stmt = select(UserModel).where(UserModel.username == username)
    user = (await session.execute(stmt)).scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return AuthUserDTO(username=username, email=user.email, role=role)


@router.get("/admin")
async def admin_endpoint(token: str = Depends(oauth2_scheme)) -> dict[str, str]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        role = payload.get("role")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return {"msg": "Welcome, admin!"}
