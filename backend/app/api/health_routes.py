import asyncio

import httpx
from fastapi import APIRouter, Response
from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal

router = APIRouter(prefix="/api", tags=["health"])

# Batas waktu tiap pemeriksaan agar probe tidak menggantung bila dependensi macet
CHECK_TIMEOUT_SECONDS = 5


@router.get("/health", summary="Status layanan backend")
async def health():
    # Hanya melaporkan apakah konfigurasi terisi, tidak pernah nilai rahasianya
    return {
        "status": "ok",
        "llm_configured": bool(settings.openrouter_api_key),
        "qdrant_configured": bool(settings.qdrant_cluster_endpoint),
    }


async def _check_database() -> str:
    async with SessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return "ok"


async def _check_qdrant() -> str:
    if not settings.qdrant_cluster_endpoint:
        return "belum dikonfigurasi"
    from qdrant_client import AsyncQdrantClient

    client = AsyncQdrantClient(url=settings.qdrant_cluster_endpoint, api_key=settings.qdrant_api_key or None)
    try:
        await client.get_collections()
    finally:
        await client.close()
    return "ok"


async def _check_llm() -> str:
    """Kunci OpenRouter benar-benar diterima (bukan hanya terisi). Mengecek kunci, tidak memakai kuota model."""
    if not settings.openrouter_api_key:
        return "belum dikonfigurasi"
    async with httpx.AsyncClient(timeout=CHECK_TIMEOUT_SECONDS) as client:
        res = await client.get(
            "https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {settings.openrouter_api_key}"}
        )
    if res.status_code in (401, 403):
        return "kunci ditolak atau kedaluwarsa"
    res.raise_for_status()
    return "ok"


async def _run_check(check) -> str:
    try:
        return await asyncio.wait_for(check(), CHECK_TIMEOUT_SECONDS)
    except Exception as e:  # noqa: BLE001
        # Hanya jenis galat yang dikembalikan; pesan aslinya bisa memuat alamat/kredensial
        return f"gagal ({type(e).__name__})"


@router.get("/health/ready", summary="Kesiapan layanan: database, Qdrant, dan kunci LLM benar-benar bisa dipakai")
async def ready(response: Response):
    database, qdrant, llm = await asyncio.gather(
        _run_check(_check_database), _run_check(_check_qdrant), _run_check(_check_llm)
    )
    # Database wajib; Qdrant dan LLM hanya memengaruhi fitur knowledge base/chat, jadi tidak membuat layanan "tidak siap"
    ok = database == "ok"
    if not ok:
        response.status_code = 503
    return {"status": "ok" if ok else "tidak siap", "database": database, "qdrant": qdrant, "llm": llm}
