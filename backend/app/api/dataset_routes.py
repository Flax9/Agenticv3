"""Dataset dari drive eksternal: daftar berkas dan sinkronisasi ke Knowledge Base."""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.config import settings
from app.core.audit import record_audit
from app.core.deps import CurrentUser, KbManagerUser, SessionDep, client_ip
from app.core.jobs import Job, jobs
from app.database import SessionLocal
from app.models import DatasetFile
from app.models.enums import ModulTerkait, TipeAksi
from app.schemas.dataset_schema import DatasetListResponse
from app.services.dataset.sync import REFERENCE_EXT, DatasetUnavailableError, dataset_root, sync_dataset
from app.services.rag.vector_store import Vector_Store

router = APIRouter(prefix="/api/dataset", tags=["dataset"])

SYNC_JOB = "sinkron_dataset"


@router.get("/files", response_model=DatasetListResponse, summary="Daftar berkas di folder dataset")
async def list_files(_user: CurrentUser, session: SessionDep, acuan: bool = False):
    """`acuan=true` hanya mengembalikan berkas yang bisa dipilih sebagai acuan (PDF/Excel yang masih ada)."""
    rows = (await session.scalars(select(DatasetFile).order_by(DatasetFile.relative_path))).all()
    if acuan:
        rows = [r for r in rows if any(r.nama_file.lower().endswith(ext) for ext in REFERENCE_EXT)]
    return {"configured": settings.dataset_dir is not None, "files": rows}


@router.post("/sync", status_code=202, summary="Mulai sinkronisasi folder dataset (job latar belakang)")
async def sync(user: KbManagerUser, request: Request):
    """Ingest bisa memakan waktu beberapa menit per berkas, jadi dijalankan sebagai job.
    Pantau hasilnya lewat `GET /api/jobs/{job_id}`."""
    try:
        root = dataset_root(settings.dataset_dir)
    except DatasetUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    # Satu sinkronisasi pada satu waktu (ingest ke Qdrant tidak boleh berjalan ganda)
    if running := jobs.running(SYNC_JOB):
        raise HTTPException(
            status_code=409, detail=f"Sinkronisasi sedang berjalan (job {running.id}). Tunggu hingga selesai."
        )
    user_id, ip = user.id, client_ip(request)

    async def work(job: Job) -> dict:
        def on_progress(done: int, total: int, berkas: str) -> None:
            job.progress = {"selesai": done, "total": total, "berkas": berkas}

        async with SessionLocal() as session:
            report = await sync_dataset(session, root, Vector_Store, on_progress)
            result = report.as_dict()
            await record_audit(
                session,
                tipe_aksi=TipeAksi.SINKRON_DATASET,
                modul=ModulTerkait.KNOWLEDGE_BASE,
                rincian=(
                    f"Sinkron dataset: {len(report.ditambah)} baru, {len(report.diperbarui)} diperbarui, "
                    f"{len(report.dihapus)} dihapus, {len(report.gagal)} gagal"
                ),
                user_id=user_id,
                snapshot=result,
                ip_address=ip,
            )
        return result

    return jobs.start(SYNC_JOB, user.id, work).as_dict()
