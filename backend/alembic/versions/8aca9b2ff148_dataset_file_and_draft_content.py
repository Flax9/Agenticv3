"""dataset_file_and_draft_content

Tabel berkas dataset (drive eksternal), kolom konten_json pada draf, dan nilai baru
tipe_aksi SINKRON_DATASET. Seperti migrasi awal, CHECK constraint enum ditulis eksplisit
(create_constraint=False) agar tidak ada constraint ganda.

Revision ID: 8aca9b2ff148
Revises: dd7ef6b08174
Create Date: 2026-10-19 20:32:48.238420

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8aca9b2ff148"
down_revision: str | Sequence[str] | None = "dd7ef6b08174"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIPE_AKSI_LAMA = (
    "LOGIN",
    "LOGIN_GAGAL",
    "UPLOAD_BOQ",
    "EKSTRAKSI",
    "GENERATE_DOCX",
    "REVISI_PASAL",
    "APPROVAL",
    "EXPORT_DOKUMEN",
    "HAPUS_PROYEK",
    "KB_INGEST",
    "KB_HAPUS",
    "KELOLA_USER",
)
_TIPE_AKSI_BARU = (*_TIPE_AKSI_LAMA, "SINKRON_DATASET")


def _tipe_aksi_check(values: tuple[str, ...]) -> str:
    return "tipe_aksi IN (" + ", ".join(f"'{v}'" for v in values) + ")"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "procurement_dataset_file",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("relative_path", sa.String(length=1000), nullable=False),
        sa.Column("nama_file", sa.String(length=255), nullable=False),
        sa.Column("collection", sa.String(length=50), nullable=True),
        sa.Column("ukuran_bytes", sa.BigInteger(), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hash_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "TERINDEKS",
                "REFERENSI",
                "DILEWATI",
                "GAGAL",
                name="statusdataset",
                native_enum=False,
                create_constraint=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("jumlah_chunk", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pesan", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('TERINDEKS', 'REFERENSI', 'DILEWATI', 'GAGAL')",
            name=op.f("ck_procurement_dataset_file_statusdataset"),
        ),
        sa.CheckConstraint("ukuran_bytes >= 0", name=op.f("ck_procurement_dataset_file_ukuran_non_negative")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_procurement_dataset_file")),
        sa.UniqueConstraint("relative_path", name=op.f("uq_procurement_dataset_file_relative_path")),
    )
    op.create_index(
        op.f("ix_procurement_dataset_file_collection"), "procurement_dataset_file", ["collection"], unique=False
    )
    op.create_index(
        op.f("ix_procurement_dataset_file_hash_sha256"), "procurement_dataset_file", ["hash_sha256"], unique=False
    )
    op.add_column(
        "procurement_document_draft",
        sa.Column(
            "konten_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.drop_constraint(op.f("ck_procurement_audit_trail_tipeaksi"), "procurement_audit_trail", type_="check")
    op.create_check_constraint(
        op.f("ck_procurement_audit_trail_tipeaksi"), "procurement_audit_trail", _tipe_aksi_check(_TIPE_AKSI_BARU)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM procurement_audit_trail WHERE tipe_aksi = 'SINKRON_DATASET'")
    op.drop_constraint(op.f("ck_procurement_audit_trail_tipeaksi"), "procurement_audit_trail", type_="check")
    op.create_check_constraint(
        op.f("ck_procurement_audit_trail_tipeaksi"), "procurement_audit_trail", _tipe_aksi_check(_TIPE_AKSI_LAMA)
    )
    op.drop_column("procurement_document_draft", "konten_json")
    op.drop_index(op.f("ix_procurement_dataset_file_hash_sha256"), table_name="procurement_dataset_file")
    op.drop_index(op.f("ix_procurement_dataset_file_collection"), table_name="procurement_dataset_file")
    op.drop_table("procurement_dataset_file")
