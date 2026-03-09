"""Users router: current user profile endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from jose import JWTError, jwt

from src.application.dtos.schemas import UserResponseDTO
from src.infrastructure.config import settings
from src.presentation.dependencies.deps import get_current_user_id

router = APIRouter(prefix="/users", tags=["Users"])

_bearer_scheme = HTTPBearer()


@router.get(
    "/me",
    response_model=UserResponseDTO,
    responses={
        401: {"description": "Invalid or missing token"},
    },
)
async def get_current_user(
    owner_id: str = Depends(get_current_user_id),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> UserResponseDTO:
    """Retrieve the current authenticated user's profile from the JWT."""
    email: str | None = None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        email = payload.get("email")
    except JWTError:
        pass
    return UserResponseDTO(id=owner_id, email=email)
