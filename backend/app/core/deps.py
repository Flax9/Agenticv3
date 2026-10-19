"""Dependency FastAPI untuk autentikasi & otorisasi berbasis peran (masterplan 4.4)."""

from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.database import get_session
from app.models import AppUser
from app.models.enums import Role

_bearer = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"}
    )


async def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AppUser:
    if credentials is None:
        raise _unauthorized("Silakan login terlebih dahulu.")
    try:
        user_id = decode_token(credentials.credentials, "access")
    except jwt.ExpiredSignatureError as e:
        raise _unauthorized("Sesi login telah berakhir.") from e
    except (jwt.InvalidTokenError, ValueError) as e:
        raise _unauthorized("Token tidak valid.") from e
    user = await session.get(AppUser, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("Akun tidak ditemukan atau nonaktif.")
    return user


CurrentUser = Annotated[AppUser, Depends(get_current_user)]


def require_role(*roles: Role) -> Callable:
    """Dependency yang menolak pengguna di luar peran yang diizinkan (HTTP 403)."""

    async def checker(user: CurrentUser) -> AppUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Peran Anda tidak memiliki akses ke fitur ini."
            )
        return user

    return checker


def client_ip(request: Request) -> str | None:
    """IP pengguna; di belakang Nginx diambil dari X-Real-IP (masterplan 4.2 tabel 9)."""
    return request.headers.get("x-real-ip") or (request.client.host if request.client else None)


# Kelompok peran sesuai matriks 4.4
DraftingUser = Annotated[AppUser, Depends(require_role(Role.ADMIN, Role.PROCUREMENT, Role.FPP))]
GeneratingUser = Annotated[AppUser, Depends(require_role(Role.ADMIN, Role.PROCUREMENT, Role.FPP, Role.APPROVER))]
KbManagerUser = Annotated[AppUser, Depends(require_role(Role.ADMIN, Role.PROCUREMENT))]
