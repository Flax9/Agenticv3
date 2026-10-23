import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, uuid_pk


class BackgroundJob(Base):
    """Catatan job latar belakang (mis. sinkronisasi dataset). Progres langsung hanya ada di memori
    proses yang menjalankannya; yang disimpan di sini adalah awal dan hasil akhir job, sehingga
    statusnya tetap bisa dilihat setelah server restart."""

    __tablename__ = "background_job"

    id: Mapped[uuid.UUID] = uuid_pk()
    kind: Mapped[str] = mapped_column(String(50), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20))  # berjalan | selesai | gagal
    result: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
