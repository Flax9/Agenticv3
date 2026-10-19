"""Entrypoint FastAPI: Pertamina Procurement AI Copilot (ITeC)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth_routes, health_routes, kb_routes, tender_routes
from app.config import settings

app = FastAPI(
    title="Pertamina Procurement AI Copilot — API",
    description="Ekstraksi metadata, generator dokumen Tender/RKS/Kontrak/Amendemen, dan Knowledge Base.",
    version="3.0.0",
    # Swagger hanya aktif saat DEBUG=True (lihat masterplan 8.4)
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.debug else None,
)

# Saat development frontend memakai proxy Vite (satu origin); CORS ini untuk akses langsung ke :8000
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,  # cookie refresh token
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(health_routes.router)
app.include_router(auth_routes.router)
app.include_router(tender_routes.router)
app.include_router(kb_routes.router)
