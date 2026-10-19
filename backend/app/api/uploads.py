"""Validasi berkas unggahan sebelum diteruskan ke parser/LLM."""

from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings

PDF = {".pdf"}
PDF_OR_EXCEL = {".pdf", ".xlsx", ".xls"}


async def read_upload(file: UploadFile | None, allowed_ext: set[str], label: str) -> tuple[bytes, str] | None:
    """Kembalikan (isi, nama_file) atau None bila tidak ada berkas. Tolak format/ukuran yang tidak sah."""
    if file is None or not file.filename:
        return None
    filename = Path(file.filename).name  # buang komponen path dari nama berkas
    ext = Path(filename).suffix.lower()
    if ext not in allowed_ext:
        allowed = ", ".join(sorted(allowed_ext))
        raise HTTPException(status_code=415, detail=f"Berkas {label} harus berformat {allowed}.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail=f"Berkas {label} kosong.")
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Berkas {label} melebihi batas {settings.max_upload_mb} MB.")
    return content, filename
