"""Job latar belakang di dalam proses (masterplan Fase 4).

Untuk satu proses Uvicorn (laptop/demo) cukup memakai asyncio task. Progres langsung hanya ada
di memori proses yang menjalankan job. Awal dan hasil akhir job disimpan di tabel `background_job`,
jadi statusnya tetap terbaca setelah server restart (job yang terputus ditandai gagal saat startup).
Bila backend dijalankan multi-worker, pindahkan ke Celery + Redis (profil compose `worker`).
"""

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from app.database import SessionLocal
from app.models import BackgroundJob

logger = logging.getLogger(__name__)

# Job yang sudah selesai dibuang dari memori setelah sekian lama (catatan di database tetap ada)
_KEEP_FINISHED = timedelta(hours=1)
INTERRUPTED_MESSAGE = "Server dimulai ulang saat job berjalan."


@dataclass
class Job:
    kind: str
    user_id: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: str = "berjalan"  # berjalan | selesai | gagal
    progress: dict = field(default_factory=dict)
    result: dict | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None

    def as_dict(self) -> dict:
        return {
            "id": str(self.id),
            "kind": self.kind,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


def _from_row(row: BackgroundJob) -> Job:
    return Job(
        kind=row.kind,
        user_id=row.user_id,
        id=row.id,
        status=row.status,
        result=row.result,
        error=row.error,
        created_at=row.created_at,
        finished_at=row.finished_at,
    )


class JobManager:
    def __init__(self):
        self._jobs: dict[uuid.UUID, Job] = {}
        # Referensi task disimpan agar tidak dibersihkan garbage collector sebelum selesai
        self._tasks: set[asyncio.Task] = set()

    async def get(self, job_id: uuid.UUID) -> Job | None:
        if job := self._jobs.get(job_id):
            return job
        async with SessionLocal() as session:
            row = await session.get(BackgroundJob, job_id)
        return _from_row(row) if row else None

    def running(self, kind: str) -> Job | None:
        return next((j for j in self._jobs.values() if j.kind == kind and j.status == "berjalan"), None)

    async def start(self, kind: str, user_id: uuid.UUID, work: Callable[[Job], Awaitable[dict]]) -> Job:
        self._prune()
        job = Job(kind=kind, user_id=user_id)
        async with SessionLocal() as session:
            session.add(
                BackgroundJob(id=job.id, kind=kind, user_id=user_id, status=job.status, created_at=job.created_at)
            )
            await session.commit()
        self._jobs[job.id] = job
        task = asyncio.create_task(self._run(job, work))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return job

    async def _run(self, job: Job, work: Callable[[Job], Awaitable[dict]]) -> None:
        try:
            job.result = await work(job)
            job.status = "selesai"
        except Exception as e:
            logger.exception("Job %s (%s) gagal", job.id, job.kind)
            job.status, job.error = "gagal", str(e)
        finally:
            job.finished_at = datetime.now(UTC)
            await self._save_outcome(job)

    async def _save_outcome(self, job: Job) -> None:
        try:
            async with SessionLocal() as session:
                await session.execute(
                    update(BackgroundJob)
                    .where(BackgroundJob.id == job.id)
                    .values(status=job.status, result=job.result, error=job.error, finished_at=job.finished_at)
                )
                await session.commit()
        except Exception:
            # Hasil tetap terbaca dari memori selama proses hidup; hanya riwayat permanennya yang hilang
            logger.exception("Hasil job %s gagal disimpan ke database", job.id)

    async def fail_interrupted(self) -> int:
        """Dipanggil saat startup: job 'berjalan' di database milik proses sebelumnya tidak akan selesai."""
        async with SessionLocal() as session:
            result = await session.execute(
                update(BackgroundJob)
                .where(BackgroundJob.status == "berjalan")
                .values(status="gagal", error=INTERRUPTED_MESSAGE, finished_at=datetime.now(UTC))
            )
            await session.commit()
        return result.rowcount

    def _prune(self) -> None:
        cutoff = datetime.now(UTC) - _KEEP_FINISHED
        for job_id, job in list(self._jobs.items()):
            if job.finished_at and job.finished_at < cutoff:
                del self._jobs[job_id]


jobs = JobManager()
