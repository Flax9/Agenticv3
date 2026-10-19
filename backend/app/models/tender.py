import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at_column, enum_column, updated_at_column, uuid_pk
from app.models.enums import ResikoCsms, StatusApproval, StatusTahap, StatusVerifikasi, TipeDokumen


class TenderProject(Base):
    """Paket pengadaan, entitas utama (masterplan 4.2 tabel 2). Dihapus secara soft delete."""

    __tablename__ = "procurement_tender_project"
    __table_args__ = (
        CheckConstraint("hps_total >= 0", name="hps_total_non_negative"),
        CheckConstraint("current_step BETWEEN 1 AND 4", name="current_step_range"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL")
    )
    no_tender: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    nama_pengadaan: Mapped[str] = mapped_column(String(255))
    tipe_dokumen: Mapped[TipeDokumen] = mapped_column(
        enum_column(TipeDokumen, 50), default=TipeDokumen.TENDER, server_default=TipeDokumen.TENDER.value
    )
    hps_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, server_default="0")
    resiko_csms: Mapped[ResikoCsms] = mapped_column(
        enum_column(ResikoCsms, 20), default=ResikoCsms.TINGGI, server_default=ResikoCsms.TINGGI.value
    )
    status_tahap: Mapped[StatusTahap] = mapped_column(
        enum_column(StatusTahap, 50), default=StatusTahap.DRAFT, server_default=StatusTahap.DRAFT.value
    )
    current_step: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1")
    metadata_ekstraksi: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    drafts: Mapped[list["DocumentDraft"]] = relationship(back_populates="project", passive_deletes=True)


class DocumentDraft(Base):
    """Versi dokumen .docx per paket (masterplan 4.2 tabel 3)."""

    __tablename__ = "procurement_document_draft"
    __table_args__ = (
        UniqueConstraint("project_id", "versi", name="uq_procurement_document_draft_project_versi"),
        CheckConstraint("skor_kepatuhan_stk BETWEEN 0 AND 100", name="skor_range"),
        # Maksimal satu draf aktif per proyek
        Index(
            "uq_procurement_document_draft_one_active",
            "project_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procurement_tender_project.id", ondelete="CASCADE")
    )
    versi: Mapped[str] = mapped_column(String(20), default="v1.0", server_default="v1.0")
    judul_dokumen: Mapped[str] = mapped_column(String(255))
    file_docx_path: Mapped[str | None] = mapped_column(String(500))
    # Isi draf terstruktur: JSON RKS dari agent, atau parameter form untuk generator lain
    konten_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    # NULL = belum dinilai (sengaja tanpa default 100)
    skor_kepatuhan_stk: Mapped[int | None] = mapped_column(SmallInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    status_approval: Mapped[StatusApproval] = mapped_column(
        enum_column(StatusApproval, 30), default=StatusApproval.DRAFT, server_default=StatusApproval.DRAFT.value
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    project: Mapped[TenderProject] = relationship(back_populates="drafts")
    clauses: Mapped[list["DocumentClause"]] = relationship(back_populates="draft", passive_deletes=True)


class DocumentClause(Base):
    """Pasal/klausul granular per draf (masterplan 4.2 tabel 4)."""

    __tablename__ = "procurement_document_clause"
    __table_args__ = (UniqueConstraint("draft_id", "nomor_urut", name="uq_procurement_document_clause_draft_urut"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procurement_document_draft.id", ondelete="CASCADE")
    )
    stk_rule_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("procurement_stk_rule.id", ondelete="SET NULL"))
    nomor_urut: Mapped[int] = mapped_column(Integer)
    kode_pasal: Mapped[str] = mapped_column(String(50))
    judul_pasal: Mapped[str] = mapped_column(String(255))
    teks_original: Mapped[str] = mapped_column(Text)
    teks_revisi_ai: Mapped[str] = mapped_column(Text)
    is_edited_manual: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    status_verifikasi: Mapped[StatusVerifikasi] = mapped_column(
        enum_column(StatusVerifikasi, 30),
        default=StatusVerifikasi.BELUM_DICEK,
        server_default=StatusVerifikasi.BELUM_DICEK.value,
    )
    catatan_stk: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = updated_at_column()

    draft: Mapped[DocumentDraft] = relationship(back_populates="clauses")
