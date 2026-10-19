import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at_column, enum_column, uuid_pk
from app.models.enums import ChatRole


class ChatSession(Base):
    """Sesi percakapan Copilot per paket (masterplan 4.2 tabel 6)."""

    __tablename__ = "procurement_chat_session"

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procurement_tender_project.id", ondelete="CASCADE"), index=True
    )
    judul_sesi: Mapped[str] = mapped_column(
        String(150), default="Penyusunan Dokumen Tender", server_default="Penyusunan Dokumen Tender"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = created_at_column()

    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", passive_deletes=True)


class ChatMessage(Base):
    """Pesan chat, jejak tool-call, dan payload artifact (masterplan 4.2 tabel 7)."""

    __tablename__ = "procurement_chat_message"
    __table_args__ = (Index("ix_procurement_chat_message_session_created", "session_id", "created_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procurement_chat_session.id", ondelete="CASCADE")
    )
    role: Mapped[ChatRole] = mapped_column(enum_column(ChatRole, 20))
    content: Mapped[str] = mapped_column(Text)
    tool_calls: Mapped[dict | None] = mapped_column(JSONB)
    artifacts_payload: Mapped[dict | None] = mapped_column(JSONB)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = created_at_column()

    session: Mapped[ChatSession] = relationship(back_populates="messages")
