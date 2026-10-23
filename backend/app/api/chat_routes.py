"""Sesi chat Copilot: setiap sesi adalah satu paket (draf dokumen) yang disusun lewat percakapan."""

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select

from app.config import settings
from app.core.audit import record_audit
from app.core.deps import CurrentUser, DraftingUser, SessionDep, client_ip
from app.core.rate_limit import chat_limiter
from app.database import SessionLocal
from app.models import AppUser, ChatMessage, ChatSession, DocumentDraft, TenderProject
from app.models.enums import ChatRole, ModulTerkait, Role, TipeAksi, TipeDokumen
from app.schemas.chat_schema import DraftOut, MessageCreate, SessionCreate, SessionDetail, SessionOut, TurnResponse
from app.services.chat.agent_runner import RksAgentRunner, rks_runner
from app.services.dataset.sync import DatasetUnavailableError, dataset_root, load_reference
from app.services.drafts import active_draft, add_draft_version, attach_docx, draft_docx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DOC_LABELS = {
    TipeDokumen.TENDER: "Dokumen Tender",
    TipeDokumen.RKS: "Dokumen RKS",
    TipeDokumen.KONTRAK: "Kontrak Definitif",
    TipeDokumen.AMENDEMEN: "Draft Amendemen",
}
# Matriks 4.4: "Lihat seluruh paket (read-only)" dan "Generate & unduh .docx"
VIEW_ALL_ROLES = {Role.ADMIN, Role.PROCUREMENT, Role.APPROVER, Role.AUDITOR}
DOWNLOAD_ROLES = {Role.ADMIN, Role.PROCUREMENT, Role.APPROVER}

AGENT_UNAVAILABLE = (
    "Asisten percakapan untuk **{label}** belum tersedia dari tim AI. Untuk sementara, isi parameter langsung "
    "di kanvas lalu klik **Unduh .docx**."
)
LLM_KEY_REJECTED = (
    "Kunci API layanan LLM (OpenRouter) ditolak atau sudah kedaluwarsa. Hubungi administrator untuk memperbarui "
    "`OPENROUTER_API_KEY` di server."
)
LLM_BUSY = "Layanan LLM sedang sibuk atau kuota habis. Tunggu beberapa saat lalu kirim ulang pesan Anda."
LLM_UNREACHABLE = "Tidak dapat terhubung ke layanan LLM atau knowledge base. Periksa koneksi server lalu coba lagi."
BOQ_HINT = (
    "Agent sedang menunggu berkas **BoQ**. Pilih berkas dari drive lewat tombol 📎, atau ketik **lewati** "
    "untuk melanjutkan tanpa BoQ."
)

# Satu giliran agent per sesi pada satu waktu (state LangGraph per thread tidak aman diakses paralel)
_session_locks: defaultdict[uuid.UUID, asyncio.Lock] = defaultdict(asyncio.Lock)
_last_stamp: dict[uuid.UUID, datetime] = {}


def get_rks_runner() -> RksAgentRunner:
    return rks_runner


RunnerDep = Annotated[RksAgentRunner, Depends(get_rks_runner)]


def _draft_out(draft: DocumentDraft | None) -> DraftOut | None:
    if draft is None:
        return None
    return DraftOut(
        id=draft.id,
        versi=draft.versi,
        judul_dokumen=draft.judul_dokumen,
        konten_json=draft.konten_json or {},
        has_docx=draft_docx(draft) is not None,
        created_at=draft.created_at,
    )


def _session_out(chat: ChatSession, project: TenderProject) -> SessionOut:
    return SessionOut(
        id=chat.id,
        project_id=project.id,
        judul_sesi=chat.judul_sesi,
        tipe_dokumen=project.tipe_dokumen,
        nama_pengadaan=project.nama_pengadaan,
        created_at=chat.created_at,
    )


async def _load_session(session: SessionDep, session_id: uuid.UUID, user: AppUser, *, write: bool):
    row = (
        await session.execute(
            select(ChatSession, TenderProject)
            .join(TenderProject, ChatSession.project_id == TenderProject.id)
            .where(ChatSession.id == session_id, TenderProject.deleted_at.is_(None))
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan.")
    chat, project = row
    is_owner = project.user_id == user.id
    if not is_owner and (write or user.role not in VIEW_ALL_ROLES):
        # 404 agar keberadaan sesi milik orang lain tidak bocor
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan.")
    return chat, project


@router.post("/chat/sessions", response_model=SessionOut, status_code=201, summary="Mulai sesi penyusunan dokumen")
async def create_session(body: SessionCreate, user: DraftingUser, session: SessionDep):
    label = DOC_LABELS[body.tipe_dokumen]
    project = TenderProject(user_id=user.id, nama_pengadaan=f"{label} (draf baru)", tipe_dokumen=body.tipe_dokumen)
    session.add(project)
    await session.flush()
    chat = ChatSession(project_id=project.id, judul_sesi=f"Penyusunan {label}")
    session.add(chat)
    await session.commit()
    return _session_out(chat, project)


@router.get("/chat/sessions", response_model=list[SessionOut], summary="Riwayat sesi milik pengguna")
async def list_sessions(user: CurrentUser, session: SessionDep, limit: int = 30):
    rows = (
        await session.execute(
            select(ChatSession, TenderProject)
            .join(TenderProject, ChatSession.project_id == TenderProject.id)
            .where(TenderProject.user_id == user.id, TenderProject.deleted_at.is_(None))
            .order_by(ChatSession.created_at.desc())
            .limit(min(max(limit, 1), 100))
        )
    ).all()
    return [_session_out(chat, project) for chat, project in rows]


@router.get("/chat/sessions/{session_id}", response_model=SessionDetail, summary="Isi sesi: pesan & draf aktif")
async def get_session(session_id: uuid.UUID, user: CurrentUser, session: SessionDep, runner: RunnerDep):
    chat, project = await _load_session(session, session_id, user, write=False)
    messages = (
        await session.scalars(
            select(ChatMessage).where(ChatMessage.session_id == chat.id).order_by(ChatMessage.created_at)
        )
    ).all()
    awaiting = None
    if project.tipe_dokumen == TipeDokumen.RKS and messages:
        awaiting = await run_in_threadpool(runner.awaiting, str(chat.id))
    return SessionDetail(
        **_session_out(chat, project).model_dump(),
        messages=messages,
        draft=_draft_out(await active_draft(session, project.id)),
        awaiting=awaiting,
    )


def _add_message(session: SessionDep, chat: ChatSession, role: ChatRole, content: str, payload: dict | None = None):
    # created_at diisi di sini: now() PostgreSQL bernilai sama untuk semua pesan dalam satu transaksi,
    # sehingga urutan user → assistant bisa tertukar saat dimuat ulang
    stamp = datetime.now(UTC)
    last = _last_stamp.get(chat.id)
    if last is not None and stamp <= last:
        stamp = last + timedelta(microseconds=1)
    _last_stamp[chat.id] = stamp
    msg = ChatMessage(session_id=chat.id, role=role, content=content, artifacts_payload=payload, created_at=stamp)
    session.add(msg)
    return msg


async def _resolve_attachment(session: SessionDep, body: MessageCreate, awaiting: str | None) -> tuple[str, str]:
    """Berkas dataset terlampir → (teks untuk agent, teks yang ditampilkan di chat)."""
    if awaiting != "upload_boq":
        raise HTTPException(status_code=400, detail="Berkas acuan hanya bisa dilampirkan saat agent meminta BoQ.")
    try:
        root = dataset_root(settings.dataset_dir)
        row, path = await load_reference(session, root, body.dataset_file_id)
    except DatasetUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    if path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=415, detail="Agent RKS saat ini hanya dapat membaca BoQ berformat PDF.")
    # Agent menerima path berkas lokal; path ini sudah dipastikan berada di dalam DATASET_DIR
    return str(path), f"📎 Memakai BoQ dari drive: {row.relative_path}"


@dataclass
class _PreparedTurn:
    """Hasil validasi pesan sebelum agent dijalankan."""

    shown: str  # teks pesan user yang disimpan & ditampilkan
    agent_text: str | None  # teks untuk agent; None = agent tidak dijalankan
    fixed_reply: str | None  # balasan tetap bila agent tidak dijalankan


def _agent_error_message(e: Exception) -> str:
    """Pesan galat agent yang ramah pengguna. Detail teknis hanya masuk log, bukan ke layar."""
    detail = f"{type(e).__name__} {e}".lower()
    if any(k in detail for k in ("unauthorized", "api key", "401", "403", "forbidden")):
        reply = LLM_KEY_REJECTED
    elif any(k in detail for k in ("rate limit", "ratelimit", "429", "quota", "402", "credit", "overloaded")):
        reply = LLM_BUSY
    elif any(k in detail for k in ("connect", "timeout", "timed out", "unreachable", "dns", "ssl")):
        reply = LLM_UNREACHABLE
    else:
        reply = "Copilot gagal memproses pesan ini. Coba kirim ulang; bila terus berulang, hubungi administrator."
    return f"⚠️ {reply}"


async def _prepare_turn(
    session: SessionDep, project: TenderProject, chat: ChatSession, body: MessageCreate, runner: RksAgentRunner
) -> _PreparedTurn:
    text = body.content.strip()
    if project.tipe_dokumen != TipeDokumen.RKS:
        return _PreparedTurn(text, None, AGENT_UNAVAILABLE.format(label=DOC_LABELS[project.tipe_dokumen]))
    awaiting = await run_in_threadpool(runner.awaiting, str(chat.id))
    if body.dataset_file_id is not None:
        agent_text, shown = await _resolve_attachment(session, body, awaiting)
        return _PreparedTurn(shown, agent_text, None)
    if awaiting == "upload_boq" and not runner.is_skip_answer(text):
        # Jangan teruskan teks bebas: agent akan memperlakukannya sebagai path berkas di server
        return _PreparedTurn(text, None, BOQ_HINT)
    return _PreparedTurn(text, text, None)


async def _complete_turn(
    session: SessionDep,
    chat: ChatSession,
    project: TenderProject,
    user_id: uuid.UUID,
    ip: str | None,
    prep: _PreparedTurn,
    runner: RksAgentRunner,
    on_event=None,
) -> TurnResponse:
    """Simpan pesan user, jalankan agent (bila perlu), simpan balasan & draf, lalu commit."""
    new_messages = [_add_message(session, chat, ChatRole.USER, prep.shown)]
    draft = fields = awaiting = None

    if prep.agent_text is None:
        new_messages.append(_add_message(session, chat, ChatRole.ASSISTANT, prep.fixed_reply))
        if project.tipe_dokumen == TipeDokumen.RKS:
            awaiting = await run_in_threadpool(runner.awaiting, str(chat.id))
    else:
        try:
            turn = await run_in_threadpool(runner.run_turn, str(chat.id), prep.agent_text, on_event)
        except Exception as e:  # kegagalan LLM/Qdrant dilaporkan ke user sebagai pesan
            logger.exception("Agent gagal pada sesi %s", chat.id)
            reply = _agent_error_message(e)
            new_messages.append(_add_message(session, chat, ChatRole.ASSISTANT, reply, {"error": True}))
        else:
            awaiting, fields = turn.awaiting, turn.fields
            if fields and fields.get("judul_pekerjaan"):
                project.nama_pengadaan = str(fields["judul_pekerjaan"])[:255]
            if turn.new_draft is not None:
                draft = await add_draft_version(session, project, f"RKS {project.nama_pengadaan}", turn.new_draft)
            if turn.docx_path is not None:
                draft = draft or await active_draft(session, project.id)
                if draft is None:
                    draft = await add_draft_version(session, project, f"RKS {project.nama_pengadaan}", {})
                await attach_docx(draft, turn.docx_path)
                await record_audit(
                    session,
                    tipe_aksi=TipeAksi.GENERATE_DOCX,
                    modul=ModulTerkait.CHAT,
                    rincian=f"Agent mengekspor RKS: {project.nama_pengadaan}",
                    user_id=user_id,
                    project_id=project.id,
                    snapshot={"draft_id": str(draft.id), "versi": draft.versi},
                    ip_address=ip,
                    commit=False,
                )
            payload = {"draft_id": str(draft.id), "versi": draft.versi} if draft else None
            for i, reply in enumerate(turn.replies):
                last = i == len(turn.replies) - 1
                new_messages.append(_add_message(session, chat, ChatRole.ASSISTANT, reply, payload if last else None))

    await session.commit()
    return TurnResponse(
        messages=new_messages,
        draft=_draft_out(draft or await active_draft(session, project.id)),
        awaiting=awaiting,
        fields=fields,
        nama_pengadaan=project.nama_pengadaan,
    )


async def _validated_session(session: SessionDep, session_id: uuid.UUID, user: AppUser, body: MessageCreate):
    chat, project = await _load_session(session, session_id, user, write=True)
    if wait := chat_limiter.hit(str(user.id)):
        raise HTTPException(
            status_code=429,
            detail=f"Terlalu banyak pesan dalam waktu singkat. Coba lagi dalam {wait} detik.",
            headers={"Retry-After": str(wait)},
        )
    if not body.content.strip() and body.dataset_file_id is None:
        raise HTTPException(status_code=422, detail="Pesan tidak boleh kosong.")
    if body.dataset_file_id is not None and project.tipe_dokumen != TipeDokumen.RKS:
        raise HTTPException(status_code=400, detail="Lampiran berkas hanya didukung pada sesi Dokumen RKS.")
    return chat, project


@router.post("/chat/sessions/{session_id}/messages", response_model=TurnResponse, summary="Kirim pesan ke Copilot")
async def send_message(
    session_id: uuid.UUID,
    body: MessageCreate,
    user: DraftingUser,
    session: SessionDep,
    request: Request,
    runner: RunnerDep,
):
    chat, project = await _validated_session(session, session_id, user, body)
    async with _session_locks[chat.id]:
        prep = await _prepare_turn(session, project, chat, body, runner)
        return await _complete_turn(session, chat, project, user.id, client_ip(request), prep, runner)


# Jeda maksimum tanpa data sebelum komentar SSE dikirim (di bawah timeout baca proxy/Nginx)
HEARTBEAT_SECONDS = 15


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


# Label progres untuk node agent (ditampilkan di chat & Progress Drawer)
NODE_LABELS = {
    "route_question": "Memahami pertanyaan",
    "direct_answer": "Menyusun jawaban",
    "retrieve_kb": "Mencari di knowledge base",
    "kb_answer": "Menyusun jawaban dari knowledge base",
    "upload_boq": "Membaca dan meringkas BoQ",
    "clarify_rks": "Memeriksa informasi pekerjaan",
    "retrieve_examples": "Mencari contoh RKS serupa",
    "generate_rks_json": "Menyusun draf RKS",
    "review_rks": "Menyiapkan tinjauan draf",
    "export_docx": "Mengekspor dokumen .docx",
}


@router.post("/chat/sessions/{session_id}/stream", summary="Kirim pesan ke Copilot (Server-Sent Events)")
async def stream_message(
    session_id: uuid.UUID,
    body: MessageCreate,
    user: DraftingUser,
    session: SessionDep,
    request: Request,
    runner: RunnerDep,
):
    """Seperti `/messages`, tetapi melaporkan progres node (`progress`), token jawaban (`token`),
    lalu hasil akhir (`done`, isi sama dengan TurnResponse) atau `error`."""
    chat, project = await _validated_session(session, session_id, user, body)
    lock = _session_locks[chat.id]
    await lock.acquire()
    try:
        # Validasi lampiran dll. masih bisa mengembalikan HTTP error biasa sebelum stream dimulai
        prep = await _prepare_turn(session, project, chat, body, runner)
    except BaseException:
        lock.release()
        raise
    user_id, ip, chat_id = user.id, client_ip(request), chat.id
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def on_event(kind: str, data: dict) -> None:  # dipanggil dari thread agent
        if kind == "progress":
            data = {**data, "label": NODE_LABELS.get(data["node"], data["node"])}
        loop.call_soon_threadsafe(queue.put_nowait, (kind, data))

    async def work() -> TurnResponse:
        # Session database sendiri: session dari dependency tidak dijamin hidup selama stream
        async with SessionLocal() as db:
            chat_db = await db.get(ChatSession, chat_id)
            project_db = await db.get(TenderProject, chat_db.project_id)
            return await _complete_turn(db, chat_db, project_db, user_id, ip, prep, runner, on_event)

    async def events():
        task = asyncio.create_task(work())
        try:
            while True:
                getter = asyncio.create_task(queue.get())
                done, _ = await asyncio.wait(
                    {getter, task}, timeout=HEARTBEAT_SECONDS, return_when=asyncio.FIRST_COMPLETED
                )
                if getter in done:
                    kind, data = getter.result()
                    yield _sse(kind, data)
                    continue
                getter.cancel()
                if not done:
                    # Node bisa diam beberapa menit (mis. Docling membaca BoQ); komentar SSE menjaga koneksi
                    yield ": ping\n\n"
                    continue
                while not queue.empty():
                    kind, data = queue.get_nowait()
                    yield _sse(kind, data)
                break
            try:
                yield _sse("done", (await task).model_dump(mode="json"))
            except Exception as e:
                logger.exception("Stream gagal pada sesi %s", chat_id)
                yield _sse("error", {"detail": _agent_error_message(e)})
        finally:
            lock.release()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        # Nginx tidak boleh menahan (buffer) respons agar token langsung sampai ke browser
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/drafts/{draft_id}/download", summary="Unduh .docx sebuah draf")
async def download_draft(draft_id: uuid.UUID, user: CurrentUser, session: SessionDep, request: Request):
    draft = await session.get(DocumentDraft, draft_id)
    project = await session.get(TenderProject, draft.project_id) if draft else None
    if draft is None or project is None or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Draf tidak ditemukan.")
    if project.user_id != user.id and user.role not in DOWNLOAD_ROLES:
        raise HTTPException(status_code=404, detail="Draf tidak ditemukan.")
    path = draft_docx(draft)
    if path is None:
        raise HTTPException(status_code=404, detail="Draf ini belum diekspor ke .docx.")
    await record_audit(
        session,
        tipe_aksi=TipeAksi.EXPORT_DOKUMEN,
        modul=ModulTerkait.EXPORTER,
        rincian=f"Unduh {draft.judul_dokumen} {draft.versi}",
        user_id=user.id,
        project_id=project.id,
        ip_address=client_ip(request),
    )
    filename = "".join(c if c.isalnum() or c in " -_" else "_" for c in draft.judul_dokumen)[:60].strip()
    return FileResponse(path, filename=f"{filename}_{draft.versi}.docx", media_type=DOCX_MEDIA_TYPE)
