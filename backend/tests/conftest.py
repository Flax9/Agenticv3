"""Fixture test: database PostgreSQL terpisah (TEST_DATABASE_URL), skema dibangun lewat migrasi Alembic.

Environment variable mengalahkan isi .env (baik untuk load_dotenv maupun pydantic-settings),
jadi nilai di bawah harus diset SEBELUM modul `app` diimpor.
"""

import asyncio
import os
from pathlib import Path

import pytest
from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parent.parent
_env = dotenv_values(BACKEND_DIR.parent / ".env")
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or _env.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL belum diisi (lihat .env.example).")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DEBUG"] = "false"
os.environ["COOKIE_SECURE"] = "false"  # TestClient memakai http://
os.environ["HOUSEKEEPING_ENABLED"] = "false"  # jangan sentuh folder output development
os.environ.setdefault("JWT_SECRET", "test-secret-" + "x" * 40)

from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.rate_limit import login_limiter
from app.core.security import hash_password
from app.main import app
from app.models.enums import Role

PASSWORD = "Password-Uji-123"
USERS = {role: f"uji_{role.value.lower()}" for role in Role}


def _alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL.replace("%", "%%"))
    return cfg


async def _run_sql(statements: list[tuple[str, dict]]) -> None:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        for sql, params in statements:
            await conn.execute(text(sql), params)
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def database():
    """Skema bersih lewat migrasi (downgrade base → upgrade head), lalu satu akun per peran."""
    cfg = _alembic_config()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    password_hash = hash_password(PASSWORD)
    asyncio.run(
        _run_sql(
            [
                (
                    (
                        "INSERT INTO app_user (username, email, nama_lengkap, password_hash, role) "
                        "VALUES (:u, :e, :n, :p, :r)"
                    ),
                    {
                        "u": username,
                        "e": f"{username}@uji.local",
                        "n": f"Pengguna {role.value}",
                        "p": password_hash,
                        "r": role.value,
                    },
                )
                for role, username in USERS.items()
            ]
        )
    )
    yield
    command.downgrade(cfg, "base")


@pytest.fixture(scope="session")
def client(database):
    # Satu TestClient (satu event loop) untuk seluruh sesi agar pool asyncpg tidak berpindah loop
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_state(client):
    login_limiter._failures.clear()
    client.cookies.clear()


def login(client: TestClient, role: Role) -> dict[str, str]:
    res = client.post("/api/auth/login", json={"username": USERS[role], "password": PASSWORD})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _fetch(sql: str, params: dict) -> list:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as conn:
        rows = (await conn.execute(text(sql), params)).all()
    await engine.dispose()
    return rows


def query(sql: str, **params) -> list:
    """Baca langsung dari database test (untuk memeriksa audit trail, dll.)."""
    return asyncio.run(_fetch(sql, params))


def execute(sql: str, **params) -> None:
    """Jalankan perintah tulis langsung ke database test (mis. membersihkan tabel)."""
    asyncio.run(_run_sql([(sql, params)]))
