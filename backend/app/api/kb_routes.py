"""Manajemen Knowledge Base (Qdrant): ingest, daftar, dan hapus dokumen per collection."""

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.api.uploads import PDF, read_upload
from app.config import KB_COLLECTIONS
from app.core.audit import record_audit
from app.core.deps import CurrentUser, KbManagerUser, SessionDep, client_ip
from app.models.enums import ModulTerkait, TipeAksi
from app.services.rag.vector_store import Vector_Store

router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])


def _require_collection(collection: str) -> None:
    if collection not in KB_COLLECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Collection '{collection}' tidak valid. Pilihan: {list(KB_COLLECTIONS)}",
        )


@router.post("/ingest", summary="Ingest PDF ke Knowledge Base")
async def kb_ingest(
    collection: str = Form(..., description="rks_kb | contract_kb | amendment_kb"),
    files: list[UploadFile] = File(..., description="Satu atau lebih berkas PDF"),
    *,
    user: KbManagerUser,
    session: SessionDep,
    request: Request,
):
    """Mengunggah PDF ke collection Qdrant. Nama berkas yang sama menggantikan chunk lamanya."""
    _require_collection(collection)
    vs = Vector_Store(collection_name=collection)
    results = []
    for file in files:
        try:
            upload = await read_upload(file, PDF, "Knowledge Base")
        except HTTPException as e:
            results.append({"filename": file.filename, "status": "skipped", "reason": e.detail})
            continue
        if upload is None:
            continue
        content, filename = upload
        try:
            n_chunks = await run_in_threadpool(vs.ingest_bytes, content, filename)
            results.append({"filename": filename, "status": "success", "chunks": n_chunks})
        except Exception as e:  # noqa: BLE001 — satu berkas gagal tidak boleh menggagalkan berkas lain
            results.append({"filename": filename, "status": "error", "reason": str(e)})
    ingested = [r["filename"] for r in results if r["status"] == "success"]
    if ingested:
        await record_audit(
            session,
            tipe_aksi=TipeAksi.KB_INGEST,
            modul=ModulTerkait.KNOWLEDGE_BASE,
            rincian=f"Ingest {len(ingested)} berkas ke {collection}",
            user_id=user.id,
            snapshot={"collection": collection, "berkas": ingested},
            ip_address=client_ip(request),
        )
    return {"collection": collection, "results": results}


@router.get("/list", summary="Daftar dokumen dalam collection")
async def kb_list(collection: str, _user: CurrentUser):
    _require_collection(collection)
    try:
        sources = await run_in_threadpool(Vector_Store(collection_name=collection).list_sources)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gagal menghubungi Qdrant: {e}") from e
    return {"collection": collection, "documents": sources, "total": len(sources)}


@router.delete("/delete", summary="Hapus dokumen dari collection")
async def kb_delete(
    user: KbManagerUser,
    session: SessionDep,
    request: Request,
    collection: str = Form(...),
    filename: str = Form(...),
):
    _require_collection(collection)
    try:
        await run_in_threadpool(Vector_Store(collection_name=collection).delete_source, filename)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gagal menghapus dari Qdrant: {e}") from e
    await record_audit(
        session,
        tipe_aksi=TipeAksi.KB_HAPUS,
        modul=ModulTerkait.KNOWLEDGE_BASE,
        rincian=f"Hapus {filename} dari {collection}",
        user_id=user.id,
        ip_address=client_ip(request),
    )
    return {"status": "success", "deleted": filename, "collection": collection}
