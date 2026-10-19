"""Basis deklaratif SQLAlchemy 2.0 dan tipe kolom bersama."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, MetaData, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Nama constraint yang konsisten agar migrasi Alembic dapat diulang dan dibaca
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def enum_column(enum_cls: type[enum.Enum], length: int):
    """Enum disimpan sebagai VARCHAR + CHECK constraint (bukan tipe ENUM PostgreSQL),
    sehingga menambah pilihan cukup lewat migrasi biasa (masterplan 4.3 butir 2)."""
    return Enum(
        enum_cls,
        native_enum=False,
        create_constraint=True,
        length=length,
        values_callable=lambda e: [m.value for m in e],
        name=enum_cls.__name__.lower(),
        validate_strings=True,
    )


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))


def created_at_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def updated_at_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
