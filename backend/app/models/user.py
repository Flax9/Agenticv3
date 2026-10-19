import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, enum_column, uuid_pk
from app.models.enums import Role


class AppUser(Base):
    """Akun pegawai beserta perannya (masterplan 4.2 tabel 1)."""

    __tablename__ = "app_user"

    id: Mapped[uuid.UUID] = uuid_pk()
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    nama_lengkap: Mapped[str] = mapped_column(String(150))
    jabatan: Mapped[str | None] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(enum_column(Role, 30), default=Role.FPP, server_default=Role.FPP.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_column()
