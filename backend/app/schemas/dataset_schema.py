import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import StatusDataset


class DatasetFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    relative_path: str
    nama_file: str
    collection: str | None
    ukuran_bytes: int
    modified_at: datetime
    status: StatusDataset
    jumlah_chunk: int
    pesan: str | None


class DatasetListResponse(BaseModel):
    configured: bool
    files: list[DatasetFileOut]
