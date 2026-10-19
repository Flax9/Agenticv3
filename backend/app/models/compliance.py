import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, enum_column, updated_at_column
from app.models.enums import LevelKepatuhan, ModulTerkait, TipeAksi


class StkRule(Base):
    """Katalog 86 aturan STK Pedoman A03-001 (masterplan 4.2 tabel 8)."""

    __tablename__ = "procurement_stk_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kode_pedoman: Mapped[str] = mapped_column(
        String(50), default="A03-001/PNG200000/2024-S9", server_default="A03-001/PNG200000/2024-S9"
    )
    nomor_aturan: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    kategori_stk: Mapped[str] = mapped_column(String(50))
    judul_aturan: Mapped[str] = mapped_column(String(255))
    deskripsi_aturan: Mapped[str] = mapped_column(Text)
    klausul_baku_docx: Mapped[str | None] = mapped_column(Text)
    level_kepatuhan: Mapped[LevelKepatuhan] = mapped_column(
        enum_column(LevelKepatuhan, 20), default=LevelKepatuhan.MANDATORY, server_default=LevelKepatuhan.MANDATORY.value
    )
    qdrant_point_id: Mapped[str | None] = mapped_column(String(64), index=True)
    updated_at: Mapped[datetime] = updated_at_column()


class AuditTrail(Base):
    """Jejak audit append-only (masterplan 4.2 tabel 9). Tidak ikut terhapus bersama proyek."""

    __tablename__ = "procurement_audit_trail"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procurement_tender_project.id", ondelete="SET NULL"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL")
    )
    tipe_aksi: Mapped[TipeAksi] = mapped_column(enum_column(TipeAksi, 50), index=True)
    modul_terkait: Mapped[ModulTerkait] = mapped_column(enum_column(ModulTerkait, 50))
    rincian_perubahan: Mapped[str] = mapped_column(Text)
    snapshot_data: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
