"""Seluruh model ORM diimpor di sini agar terdaftar di Base.metadata (dipakai Alembic autogenerate)."""

from app.models.attachment import UploadedAttachment
from app.models.base import Base
from app.models.chat import ChatMessage, ChatSession
from app.models.compliance import AuditTrail, StkRule
from app.models.dataset import DatasetFile
from app.models.job import BackgroundJob
from app.models.tender import DocumentClause, DocumentDraft, TenderProject
from app.models.user import AppUser

__all__ = [
    "AppUser",
    "AuditTrail",
    "BackgroundJob",
    "Base",
    "ChatMessage",
    "ChatSession",
    "DatasetFile",
    "DocumentClause",
    "DocumentDraft",
    "StkRule",
    "TenderProject",
    "UploadedAttachment",
]
