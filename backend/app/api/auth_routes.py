"""Login, refresh token, logout, dan profil pengguna (masterplan 9.3)."""

from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from sqlalchemy import select

from app.config import settings
from app.core.audit import record_audit
from app.core.deps import CurrentUser, SessionDep, client_ip
from app.core.rate_limit import login_limiter
from app.core.security import create_token, decode_token, verify_password
from app.models import AppUser
from app.models.enums import ModulTerkait, TipeAksi
from app.schemas.auth_schema import LoginRequest, TokenResponse, UserProfile

router = APIRouter(prefix="/api/auth", tags=["auth"])

REFRESH_COOKIE = "itec_refresh"
REFRESH_COOKIE_PATH = "/api/auth"


def _set_refresh_cookie(response: Response, user: AppUser) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        create_token(user.id, "refresh"),
        max_age=settings.jwt_refresh_ttl_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )


def _token_response(user: AppUser) -> TokenResponse:
    return TokenResponse(
        access_token=create_token(user.id, "access"),
        expires_in=settings.jwt_access_ttl_minutes * 60,
        user=UserProfile.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse, summary="Login dengan username & password")
async def login(body: LoginRequest, request: Request, response: Response, session: SessionDep):
    username = body.username.strip().lower()
    ip = client_ip(request)
    limiter_key = f"{username}|{ip}"

    wait = login_limiter.retry_after(limiter_key)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Terlalu banyak percobaan login gagal. Coba lagi dalam {max(1, wait // 60)} menit.",
            headers={"Retry-After": str(wait)},
        )

    user = await session.scalar(select(AppUser).where(AppUser.username == username))
    password_ok = verify_password(body.password, user.password_hash if user else None)
    if not user or not password_ok or not user.is_active:
        login_limiter.record_failure(limiter_key)
        await record_audit(
            session,
            tipe_aksi=TipeAksi.LOGIN_GAGAL,
            modul=ModulTerkait.AUTH,
            rincian=f"Login gagal untuk username '{username}'",
            user_id=user.id if user else None,
            ip_address=ip,
        )
        # Pesan sama untuk semua kasus agar tidak membocorkan username mana yang terdaftar
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Username atau password salah.")

    login_limiter.reset(limiter_key)
    user.last_login_at = datetime.now(UTC)
    await record_audit(
        session,
        tipe_aksi=TipeAksi.LOGIN,
        modul=ModulTerkait.AUTH,
        rincian="Login berhasil",
        user_id=user.id,
        ip_address=ip,
    )
    _set_refresh_cookie(response, user)
    return _token_response(user)


@router.post("/refresh", response_model=TokenResponse, summary="Perbarui access token dari cookie refresh")
async def refresh(response: Response, session: SessionDep, itec_refresh: str | None = Cookie(default=None)):
    if not itec_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesi login tidak ditemukan.")
    try:
        user_id = decode_token(itec_refresh, "refresh")
    except (jwt.InvalidTokenError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesi login telah berakhir.") from e
    user = await session.get(AppUser, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Akun tidak ditemukan atau nonaktif.")
    _set_refresh_cookie(response, user)  # rotasi: masa berlaku refresh diperpanjang selama user aktif
    return _token_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Hapus cookie refresh")
async def logout(response: Response):
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


@router.get("/me", response_model=UserProfile, summary="Profil pengguna yang sedang login")
async def me(user: CurrentUser):
    return user
