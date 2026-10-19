"""Job latar belakang di dalam proses (masterplan Fase 4).

Untuk satu proses Uvicorn (laptop/demo) cukup memakai asyncio task. Status job disimpan di
memori, jadi hilang saat server restart dan tidak terlihat oleh worker lain. Bila backend
dijalankan multi-worker, pindahkan ke Celery + Redis (profil compose `worker`).
"""

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

# Job yang sudah selesai dibuang dari memori setelah sekian lama
_KEEP_FINISHED = timedelta(hours=1)


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


class JobManager:
    def __init__(self):
        self._jobs: dict[uuid.UUID, Job] = {}
        # Referensi task disimpan agar tidak dibersihkan garbage collector sebelum selesai
        self._tasks: set[asyncio.Task] = set()

    def get(self, job_id: uuid.UUID) -> Job | None:
        return self._jobs.get(job_id)

    def running(self, kind: str) -> Job | None:
        return next((j for j in self._jobs.values() if j.kind == kind and j.status == "berjalan"), None)

    def start(self, kind: str, user_id: uuid.UUID, work: Callable[[Job], Awaitable[dict]]) -> Job:
        self._prune()
        job = Job(kind=kind, user_id=user_id)
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

    def _prune(self) -> None:
        cutoff = datetime.now(UTC) - _KEEP_FINISHED
        for job_id, job in list(self._jobs.items()):
            if job.finished_at and job.finished_at < cutoff:
                del self._jobs[job_id]


jobs = JobManager()
