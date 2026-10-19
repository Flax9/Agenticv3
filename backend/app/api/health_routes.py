from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", summary="Status layanan backend")
async def health():
    # Hanya melaporkan apakah konfigurasi terisi, tidak pernah nilai rahasianya
    return {
        "status": "ok",
        "llm_configured": bool(settings.openrouter_api_key),
        "qdrant_configured": bool(settings.qdrant_cluster_endpoint),
    }
