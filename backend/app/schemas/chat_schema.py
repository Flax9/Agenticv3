import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ChatRole, TipeDokumen


class SessionCreate(BaseModel):
    tipe_dokumen: TipeDokumen


class MessageCreate(BaseModel):
    content: str = Field(default="", max_length=8000)
    # Berkas dari folder dataset yang dilampirkan (mis. BoQ saat agent memintanya)
    dataset_file_id: uuid.UUID | None = None


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: ChatRole
    content: str
    artifacts_payload: dict | None
    created_at: datetime


class DraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    versi: str
    judul_dokumen: str
    konten_json: dict
    has_docx: bool
    created_at: datetime


class SessionOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    judul_sesi: str
    tipe_dokumen: TipeDokumen
    nama_pengadaan: str
    created_at: datetime


class SessionDetail(SessionOut):
    messages: list[ChatMessageOut]
    draft: DraftOut | None
    # Node agent yang sedang menunggu jawaban (mis. "upload_boq", "review_rks")
    awaiting: str | None


class TurnResponse(BaseModel):
    messages: list[ChatMessageOut]
    draft: DraftOut | None
    awaiting: str | None
    fields: dict | None
    nama_pengadaan: str
