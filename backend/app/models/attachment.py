import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, enum_column, uuid_pk
from app.models.enums import TipeBerkas


class UploadedAttachment(Base):
    """Berkas acuan yang diunggah per paket (masterplan 4.2 tabel 5).
    `hash_sha256` dipakai untuk mendeteksi duplikat dan menggunakan ulang hasil ekstraksi."""

    __tablename__ = "procurement_uploaded_attachment"
    __table_args__ = (CheckConstraint("ukuran_bytes > 0", name="ukuran_positive"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procurement_tender_project.id", ondelete="CASCADE"), index=True
    )
    tipe_berkas: Mapped[TipeBerkas] = mapped_column(enum_column(TipeBerkas, 30))
    nama_file_asli: Mapped[str] = mapped_column(String(255))
    # Nama berkas fisik acak (UUID), bukan nama asli dari user
    file_path: Mapped[str] = mapped_column(String(500))
    ukuran_bytes: Mapped[int] = mapped_column(BigInteger)
    hash_sha256: Mapped[str] = mapped_column(String(64), index=True)
    hasil_ekstraksi_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    uploaded_at: Mapped[datetime] = created_at_column()
