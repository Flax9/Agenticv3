import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, enum_column, updated_at_column, uuid_pk
from app.models.enums import StatusDataset


class DatasetFile(Base):
    """Berkas di folder dataset (drive eksternal) beserta status ingest-nya ke Qdrant.
    `hash_sha256` menentukan apakah berkas berubah sejak sinkronisasi terakhir."""

    __tablename__ = "procurement_dataset_file"
    __table_args__ = (CheckConstraint("ukuran_bytes >= 0", name="ukuran_non_negative"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    # Path relatif terhadap DATASET_DIR, selalu dengan pemisah '/'
    relative_path: Mapped[str] = mapped_column(String(1000), unique=True)
    nama_file: Mapped[str] = mapped_column(String(255))
    # NULL = berkas acuan (tidak di-ingest)
    collection: Mapped[str | None] = mapped_column(String(50), index=True)
    ukuran_bytes: Mapped[int] = mapped_column(BigInteger)
    modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    hash_sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[StatusDataset] = mapped_column(enum_column(StatusDataset, 20))
    jumlah_chunk: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    pesan: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
