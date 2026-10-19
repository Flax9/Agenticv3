"""Ekstraksi metadata dan pembuatan dokumen .docx (Tender, RKS, Kontrak, Amendemen)."""

import asyncio
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from app.api.uploads import PDF, PDF_OR_EXCEL, read_upload
from app.config import settings
from app.core.audit import record_audit
from app.core.deps import DraftingUser, GeneratingUser, SessionDep, client_ip
from app.models import AppUser, TenderProject
from app.models.enums import ModulTerkait, TipeAksi
from app.services.contract.amendment_generator import export_amendemen_to_docx, generate_amendemen_document
from app.services.contract.generator import export_kontrak_to_docx, generate_kontrak_document
from app.services.dataset.sync import DatasetUnavailableError, dataset_root, load_reference
from app.services.drafts import add_draft_version
from app.services.rag.summarizer import extract_tender_metadata_from_docs, extract_text_from_pdfs, summarize_context
from app.services.rag.tools import export_rks_to_docx, generate_rks_document
from app.services.tender.generator import export_tender_to_docx, generate_tender_document

router = APIRouter(prefix="/api", tags=["dokumen"])

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# Generator hasil porting menyimpan draf terakhir di variabel global modul, lalu tool export
# membaca dari sana. Lock per jenis dokumen mencegah dua request bersamaan saling menimpa
# draf. Akan dihapus saat generator direfaktor agar mengembalikan draf secara langsung.
_LOCKS = {kind: asyncio.Lock() for kind in ("tender", "rks", "kontrak", "amendemen")}


def _safe_name(text: str, limit: int = 40) -> str:
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in text)[:limit].strip().replace(" ", "_")


def _docx_path(export_result: str) -> Path:
    """Ambil path berkas dari keluaran tool export (baris '📄 File: ...')."""
    file_path = next(
        (line.split("📄 File:", 1)[1].strip() for line in export_result.splitlines() if "📄 File:" in line),
        "",
    )
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=500, detail="Dokumen dibuat tetapi berkas .docx tidak ditemukan.")
    return Path(file_path)


async def _owned_project(session: SessionDep, project_id: str, user: AppUser) -> TenderProject | None:
    """Paket milik user yang dirujuk form (kosong = tidak disimpan ke paket mana pun)."""
    if not project_id:
        return None
    try:
        pid = uuid.UUID(project_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail="project_id tidak valid.") from e
    project = await session.get(TenderProject, pid)
    if project is None or project.deleted_at is not None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Paket tidak ditemukan.")
    return project


async def _dataset_bytes(session: SessionDep, file_id: str, allowed_ext: set[str], label: str):
    """Isi berkas acuan dari folder dataset (pengganti unggah berkas)."""
    if not file_id:
        return None
    try:
        root = dataset_root(settings.dataset_dir)
        row, path = await load_reference(session, root, uuid.UUID(file_id))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"ID berkas {label} tidak valid.") from e
    except DatasetUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    if path.suffix.lower() not in allowed_ext:
        allowed = ", ".join(sorted(allowed_ext))
        raise HTTPException(status_code=415, detail=f"Berkas {label} harus berformat {allowed}.")
    return await run_in_threadpool(path.read_bytes), row.nama_file


async def _context_from_pdf(file: UploadFile | None) -> str:
    """Ringkasan konteks dari PDF acuan opsional (kosong bila tidak ada berkas)."""
    upload = await read_upload(file, PDF, "konteks")
    if upload is None:
        return ""
    raw_text = await run_in_threadpool(extract_text_from_pdfs, [upload[0]])
    return await run_in_threadpool(summarize_context, raw_text)


class _Actor:
    """Siapa yang memicu aksi, untuk dicatat ke audit trail."""

    def __init__(self, user: AppUser, session: SessionDep, request: Request):
        self.user, self.session, self.ip = user, session, client_ip(request)

    async def audit(
        self,
        tipe_aksi: TipeAksi,
        modul: ModulTerkait,
        rincian: str,
        snapshot: dict | None = None,
        project_id: uuid.UUID | None = None,
    ):
        await record_audit(
            self.session,
            tipe_aksi=tipe_aksi,
            modul=modul,
            rincian=rincian,
            user_id=self.user.id,
            project_id=project_id,
            snapshot=snapshot,
            ip_address=self.ip,
        )


async def _generate_and_export(
    actor: _Actor,
    kind: str,
    title: str,
    generator,
    gen_args: dict,
    exporter,
    filename: str,
    project_id: str = "",
) -> FileResponse:
    project = await _owned_project(actor.session, project_id, actor.user)
    async with _LOCKS[kind]:
        gen_result = await run_in_threadpool(generator.invoke, gen_args)
        if "Error" in gen_result or "Tidak ditemukan" in gen_result:
            raise HTTPException(status_code=400, detail=gen_result)
        export_result = await run_in_threadpool(exporter.invoke, {"output_filename": filename})
        if "Error" in export_result or "Tidak ada draft" in export_result:
            raise HTTPException(status_code=400, detail=export_result)
        path = _docx_path(export_result)
        draft = None
        if project is not None:
            # Disalin di dalam lock: request berikutnya bisa menimpa berkas dengan nama yang sama
            project.nama_pengadaan = title[:255] or project.nama_pengadaan
            draft = await add_draft_version(actor.session, project, Path(filename).stem, gen_args, path)
            path = Path(draft.file_docx_path)
    await actor.audit(
        TipeAksi.GENERATE_DOCX,
        ModulTerkait.EXPORTER,
        f"Generate dokumen {kind}: {title}",
        {"berkas": filename, "draft_id": str(draft.id) if draft else None},
        project_id=project.id if project else None,
    )
    response = FileResponse(path=path, filename=filename, media_type=DOCX_MEDIA_TYPE)
    if draft is not None:
        response.headers["X-Draft-Id"] = str(draft.id)
        response.headers["X-Draft-Versi"] = draft.versi
    return response


@router.post("/extract-tender-metadata", summary="Ekstraksi parameter pengadaan dari RKS & BoQ")
async def extract_tender_metadata(
    tanggal: str = Form(""),
    resiko_csms: str = Form("Tinggi"),
    file_rks: UploadFile | None = File(None, description="Dokumen RKS (PDF)"),
    file_boq: UploadFile | None = File(None, description="Dokumen BoQ (PDF atau Excel)"),
    rks_file_id: str = Form("", description="ID berkas RKS dari folder dataset (pengganti file_rks)"),
    boq_file_id: str = Form("", description="ID berkas BoQ dari folder dataset (pengganti file_boq)"),
    project_id: str = Form("", description="Paket tempat hasil ekstraksi disimpan (opsional)"),
    *,
    user: DraftingUser,
    session: SessionDep,
    request: Request,
):
    project = await _owned_project(session, project_id, user)
    rks = await read_upload(file_rks, PDF, "RKS") or await _dataset_bytes(session, rks_file_id, PDF, "RKS")
    boq = await read_upload(file_boq, PDF_OR_EXCEL, "BoQ") or await _dataset_bytes(
        session, boq_file_id, PDF_OR_EXCEL, "BoQ"
    )
    if rks is None and boq is None:
        raise HTTPException(status_code=400, detail="Pilih minimal satu berkas RKS atau BoQ.")
    try:
        data = await run_in_threadpool(
            extract_tender_metadata_from_docs,
            rks_bytes=rks[0] if rks else None,
            rks_filename=rks[1] if rks else None,
            boq_bytes=boq[0] if boq else None,
            boq_filename=boq[1] if boq else None,
            tanggal_str=tanggal,
            resiko_csms=resiko_csms,
        )
    except ValueError as e:  # berkas tidak berisi teks yang bisa dibaca
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    names = ", ".join(u[1] for u in (rks, boq) if u)
    if project is not None:
        project.metadata_ekstraksi = {"sumber": names, "hasil": data}
        if isinstance(data, dict) and data.get("nama_pengadaan"):
            project.nama_pengadaan = str(data["nama_pengadaan"])[:255]
    await _Actor(user, session, request).audit(
        TipeAksi.EKSTRAKSI,
        ModulTerkait.CHAT,
        f"Ekstraksi metadata dari {names}",
        project_id=project.id if project else None,
    )
    return {"status": "success", "data": data}


@router.post("/generate-tender", summary="Buat Dokumen Tender Versi 2.0 (.docx)")
async def generate_tender(
    nama_pengadaan: str = Form(...),
    nomor_tender: str = Form("No.Project/DT/PND970000/2026-S7"),
    tanggal: str = Form("04 Desember 2025"),
    prime_cost: float = Form(13283434534.0),
    total_dengan_kr: float = Form(14346100000.0),
    resiko_csms: str = Form("Tinggi"),
    tkdn_minimal: float = Form(20.12),
    metode_pemenuhan: str = Form("Tender Terbatas"),
    jenis_kontrak: str = Form("Gabungan Harga Satuan & Lumpsum"),
    pejabat_procurement_nama: str = Form(""),
    pejabat_procurement_jabatan: str = Form("Area Manager Procurement Kalimantan"),
    pejabat_berwenang: str = Form("Sr. Manager Opt. & Maint. Regional Kalimantan"),
    pengawas_pekerjaan: str = Form("Region Manager RPD Regional Kalimantan"),
    prebid_tanggal: str = Form("Senin, 08 Desember 2025"),
    prebid_waktu: str = Form("10.00 WITA"),
    prebid_tempat: str = Form(
        "Microsoft Teams Meeting dengan link yang disampaikan melalui email Undangan Prebid Meeting"
    ),
    pemasukan_mulai: str = Form("Senin, 08 Desember 2025"),
    pemasukan_selesai: str = Form("Senin, 15 Desember 2025"),
    context_summary: str = Form(""),
    file: UploadFile | None = File(None, description="PDF RKS/BoQ untuk konteks (opsional)"),
    project_id: str = Form("", description="Paket tempat draf disimpan (opsional)"),
    *,
    user: GeneratingUser,
    session: SessionDep,
    request: Request,
):
    if not context_summary:
        context_summary = await _context_from_pdf(file)
    gen_args = {
        "nama_pengadaan": nama_pengadaan,
        "nomor_tender": nomor_tender,
        "tanggal": tanggal,
        "prime_cost": prime_cost,
        "total_dengan_kr": total_dengan_kr,
        "resiko_csms": resiko_csms,
        "tkdn_minimal": tkdn_minimal,
        "metode_pemenuhan": metode_pemenuhan,
        "jenis_kontrak": jenis_kontrak,
        "pejabat_procurement_nama": pejabat_procurement_nama,
        "pejabat_procurement_jabatan": pejabat_procurement_jabatan,
        "pejabat_berwenang": pejabat_berwenang,
        "pengawas_pekerjaan": pengawas_pekerjaan,
        "prebid_tanggal": prebid_tanggal,
        "prebid_waktu": prebid_waktu,
        "prebid_tempat": prebid_tempat,
        "pemasukan_mulai": pemasukan_mulai,
        "pemasukan_selesai": pemasukan_selesai,
        "context_summary": context_summary,
    }
    return await _generate_and_export(
        _Actor(user, session, request),
        "tender",
        nama_pengadaan,
        generate_tender_document,
        gen_args,
        export_tender_to_docx,
        f"Dokumen_Tender_{_safe_name(nama_pengadaan)}.docx",
        project_id,
    )


@router.post("/generate-rks", summary="Buat Dokumen RKS (.docx)")
async def generate_rks(
    jenis_pekerjaan: str = Form(...),
    detail_pekerjaan: str = Form(...),
    lokasi: str = Form(""),
    resiko_csms: str = Form("MEDIUM"),
    nomor_dokumen: str = Form("RKS-[KODE]-[TAHUN]"),
    nama_perusahaan: str = Form("PT PERTAMINA"),
    file: UploadFile | None = File(None, description="PDF BoQ/konteks (opsional)"),
    project_id: str = Form("", description="Paket tempat draf disimpan (opsional)"),
    *,
    user: GeneratingUser,
    session: SessionDep,
    request: Request,
):
    gen_args = {
        "jenis_pekerjaan": jenis_pekerjaan,
        "detail_pekerjaan": detail_pekerjaan,
        "lokasi": lokasi,
        "context_summary": await _context_from_pdf(file),
        "resiko_csms": resiko_csms,
        "nomor_dokumen": nomor_dokumen,
        "nama_perusahaan": nama_perusahaan,
    }
    return await _generate_and_export(
        _Actor(user, session, request),
        "rks",
        jenis_pekerjaan,
        generate_rks_document,
        gen_args,
        export_rks_to_docx,
        f"RKS_{_safe_name(jenis_pekerjaan)}.docx",
        project_id,
    )


@router.post("/generate-kontrak", summary="Buat Rancangan Kontrak Definitif (.docx)")
async def generate_kontrak(
    nama_pekerjaan: str = Form(""),
    nomor_kontrak: str = Form(""),
    tanggal_kontrak: str = Form(""),
    lokasi_pekerjaan: str = Form(""),
    jenis_kontrak: str = Form(""),
    nama_vendor: str = Form(""),
    npwp_vendor: str = Form(""),
    nilai_kontrak: float = Form(0.0),
    sistem_pembayaran: str = Form(""),
    durasi_hari: str = Form("180"),
    masa_pemeliharaan: str = Form("90"),
    resiko_csms: str = Form(""),
    pejabat_ttd_pertamina: str = Form(""),
    file: UploadFile | None = File(None, description="PDF RKS/BoQ untuk konteks (opsional)"),
    project_id: str = Form("", description="Paket tempat draf disimpan (opsional)"),
    *,
    user: GeneratingUser,
    session: SessionDep,
    request: Request,
):
    gen_args = {
        "nama_pekerjaan": nama_pekerjaan,
        "nomor_kontrak": nomor_kontrak,
        "tanggal_kontrak": tanggal_kontrak,
        "lokasi_pekerjaan": lokasi_pekerjaan,
        "jenis_kontrak": jenis_kontrak,
        "nama_vendor": nama_vendor,
        "npwp_vendor": npwp_vendor,
        "nilai_kontrak": nilai_kontrak,
        "sistem_pembayaran": sistem_pembayaran,
        "durasi_hari": durasi_hari,
        "masa_pemeliharaan": masa_pemeliharaan,
        "resiko_csms": resiko_csms,
        "pejabat_ttd_pertamina": pejabat_ttd_pertamina,
        "context_summary": await _context_from_pdf(file),
    }
    return await _generate_and_export(
        _Actor(user, session, request),
        "kontrak",
        nama_pekerjaan,
        generate_kontrak_document,
        gen_args,
        export_kontrak_to_docx,
        f"Rancangan_Kontrak_{_safe_name(nama_pekerjaan, 30)}.docx",
        project_id,
    )


@router.post("/generate-amendemen", summary="Buat Draft Amendemen / Addendum (.docx)")
async def generate_amendemen(
    nomor_addendum: str = Form(""),
    tanggal_amendemen: str = Form(""),
    tanggal_berlaku_efektif: str = Form(""),
    nomor_kontrak_asal: str = Form(""),
    judul_pekerjaan: str = Form(""),
    tanggal_kontrak_asal: str = Form(""),
    nama_vendor: str = Form(""),
    nilai_kontrak_asal_str: str = Form(""),
    ttd_pertamina_nama: str = Form(""),
    ttd_pertamina_jabatan: str = Form(""),
    ttd_vendor_nama: str = Form(""),
    ttd_vendor_jabatan: str = Form(""),
    detail_perubahan_json: str = Form("[]"),
    file: UploadFile | None = File(None, description="PDF kontrak asal untuk konteks (opsional)"),
    project_id: str = Form("", description="Paket tempat draf disimpan (opsional)"),
    *,
    user: GeneratingUser,
    session: SessionDep,
    request: Request,
):
    try:
        detail_perubahan_list = json.loads(detail_perubahan_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail="detail_perubahan_json bukan JSON yang valid.") from e
    gen_args = {
        "nomor_addendum": nomor_addendum,
        "tanggal_amendemen": tanggal_amendemen,
        "tanggal_berlaku_efektif": tanggal_berlaku_efektif,
        "nomor_kontrak_asal": nomor_kontrak_asal,
        "judul_pekerjaan": judul_pekerjaan,
        "tanggal_kontrak_asal": tanggal_kontrak_asal,
        "nama_vendor": nama_vendor,
        "nilai_kontrak_asal_str": nilai_kontrak_asal_str,
        "ttd_pertamina_nama": ttd_pertamina_nama,
        "ttd_pertamina_jabatan": ttd_pertamina_jabatan,
        "ttd_vendor_nama": ttd_vendor_nama,
        "ttd_vendor_jabatan": ttd_vendor_jabatan,
        "detail_perubahan_list": detail_perubahan_list,
        "context_summary": await _context_from_pdf(file),
    }
    return await _generate_and_export(
        _Actor(user, session, request),
        "amendemen",
        judul_pekerjaan,
        generate_amendemen_document,
        gen_args,
        export_amendemen_to_docx,
        f"Draft_Amendemen_{_safe_name(judul_pekerjaan, 30)}.docx",
        project_id,
    )
