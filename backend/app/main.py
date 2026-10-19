"""Entrypoint FastAPI: Pertamina Procurement AI Copilot (ITeC)."""

import asyncio
import contextlib
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth_routes, chat_routes, dataset_routes, health_routes, job_routes, kb_routes, tender_routes
from app.config import settings
from app.services.housekeeping import housekeeping_loop

# Modul AI mencetak log berisi emoji/Unicode lewat print(). Di Windows konsol default-nya cp1252
# sehingga print() melempar UnicodeEncodeError dan menggagalkan request.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(housekeeping_loop()) if settings.housekeeping_enabled else None
    yield
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    lifespan=lifespan,
    title="Pertamina Procurement AI Copilot — API",
    description="Chat Copilot, generator dokumen Tender/RKS/Kontrak/Amendemen, dataset drive, dan Knowledge Base.",
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
app.include_router(dataset_routes.router)
app.include_router(chat_routes.router)
app.include_router(job_routes.router)
