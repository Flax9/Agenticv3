"""Status job latar belakang (pola job Fase 4)."""

import uuid

from fastapi import APIRouter, HTTPException

from app.core.deps import CurrentUser
from app.core.jobs import jobs
from app.models.enums import Role

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", summary="Status job latar belakang")
async def get_job(job_id: uuid.UUID, user: CurrentUser):
    job = await jobs.get(job_id)
    # Hanya pemicu job atau ADMIN; selain itu 404 agar ID job orang lain tidak bisa ditebak-tebak
    if job is None or (job.user_id != user.id and user.role != Role.ADMIN):
        raise HTTPException(status_code=404, detail="Job tidak ditemukan atau sudah kedaluwarsa.")
    return job.as_dict()
