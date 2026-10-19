"""
LLM Generator & Orchestrator for Draft Amendemen (Addendum) Kontrak.
Extracts amendment parameters, performs RAG retrieval from amendment_kb,
prompts LLM for strict JSON schema output (Konsideran & Pasal Perubahan),
merges form overrides, and stores the active draft.
"""

import json
import os
from typing import Dict, Any, List
import logging

from langchain_core.messages import SystemMessage
from langchain_openrouter import ChatOpenRouter
from dotenv import load_dotenv

from app.services.contract.amendment_schema import AMENDEMEN_JSON_SCHEMA
from app.services.rag.vector_store import Vector_Store
from app.config import COLLECTION_AMENDMENT, LLM_MODEL_NAME

load_dotenv()
logger = logging.getLogger(__name__)

# Global store for active amendment draft
_active_amendment_store: Dict[str, Any] = {}


class GenerateAmendemenTool:
    """Tool that generates a complete Draft Amendemen JSON payload using LLM."""

    def invoke(self, kwargs: dict) -> str:
        # Cover & Basic Info
        nomor_addendum = kwargs.get("nomor_addendum", "Addendum Ke-1")
        tanggal_amendemen = kwargs.get("tanggal_amendemen", "Belum Ditentukan")
        tanggal_berlaku_efektif = kwargs.get("tanggal_berlaku_efektif", "Belum Ditentukan")
        
        # Original Contract Info
        nomor_kontrak_asal = kwargs.get("nomor_kontrak_asal", "KTR-XXX")
        judul_pekerjaan = kwargs.get("judul_pekerjaan", "Pekerjaan Konstruksi")
        tanggal_kontrak_asal = kwargs.get("tanggal_kontrak_asal", "01 Januari 2026")
        nama_vendor = kwargs.get("nama_vendor", "PT Vendor Contoh")
        nilai_kontrak_asal_str = kwargs.get("nilai_kontrak_asal_str", "-")
        
        # Signatories
        ttd_pertamina_nama = kwargs.get("ttd_pertamina_nama", "____________________")
        ttd_pertamina_jabatan = kwargs.get("ttd_pertamina_jabatan", "Executive General Manager")
        ttd_vendor_nama = kwargs.get("ttd_vendor_nama", "____________________")
        ttd_vendor_jabatan = kwargs.get("ttd_vendor_jabatan", "Direktur Utama")
        
        # Changes (Expected as a list of dicts: [{'jenis_perubahan': ..., 'isi_lama': ..., 'isi_baru': ..., 'alasan': ...}])
        detail_perubahan_list = kwargs.get("detail_perubahan_list", [])
        
        # Context from PDF (if uploaded)
        context_summary = kwargs.get("context_summary", "")

        # RAG Retrieval from amendment_kb to get similar amendment examples (especially Konsideran)
        rag_context = ""
        try:
            vs = Vector_Store(collection_name=COLLECTION_AMENDMENT)
            results = vs.retrieve(f"{nomor_addendum} amendemen perubahan kontrak {judul_pekerjaan}", k=3)
            if results:
                rag_context = "\n\n".join([f"[Referensi Amendemen]: {doc.page_content}" for doc in results])
        except Exception as e:
            logger.warning(f"Failed to retrieve from {COLLECTION_AMENDMENT}: {e}")

        llm = ChatOpenRouter(model=LLM_MODEL_NAME, temperature=0)

        # Format the changes as a string for the prompt
        changes_str = ""
        for i, change in enumerate(detail_perubahan_list, 1):
            changes_str += f"\nPerubahan {i}:\n"
            changes_str += f"- Jenis: {change.get('jenis_perubahan', 'Lainnya')}\n"
            changes_str += f"- Kondisi Lama: {change.get('isi_lama', '')}\n"
            changes_str += f"- Kondisi Baru: {change.get('isi_baru', '')}\n"
            changes_str += f"- Alasan/Justifikasi: {change.get('alasan', '')}\n"

        system_prompt = f"""
Kamu adalah Legal Counsel PT Pertamina Patra Niaga yang ahli dalam penyusunan Draft Amendemen (Addendum) Kontrak.

Tugas kamu adalah menyusun isi Draft Amendemen berdasarkan parameter berikut:
- Nomor Addendum         : {nomor_addendum}
- Tanggal Addendum       : {tanggal_amendemen}
- Tanggal Efektif        : {tanggal_berlaku_efektif}

Info Kontrak Asal:
- Judul Pekerjaan        : {judul_pekerjaan}
- Nomor Kontrak Asal     : {nomor_kontrak_asal}
- Tanggal Kontrak Asal   : {tanggal_kontrak_asal}
- Nama Penyedia          : {nama_vendor}
- Nilai Kontrak Asal     : {nilai_kontrak_asal_str}

Detail Perubahan yang Disepakati:
{changes_str if detail_perubahan_list else "Tidak ada rincian perubahan spesifik yang diberikan."}

Konteks Dokumen Tambahan (Kontrak Asal/Surat Permohonan):
{context_summary}

Referensi Amendemen Serupa (Gunakan sebagai acuan penulisan konsideran dan rumusan pasal perubahan):
{rag_context}

Fokus Tugas Khusus:
1. Susun bagian 'Konsideran' (Menimbang, Mengingat, Memperhatikan). Pastikan 'Menimbang' memuat alasan spesifik dari detail perubahan yang disepakati di atas.
2. Rumuskan setiap 'perubahan' ke dalam bentuk bahasa pasal (legal drafting) yang membandingkan klausul lama ("semula berbunyi") dengan klausul baru ("diubah menjadi"). Jika pasal lama tidak spesifik, buatkan rumusan wajar yang mengisyaratkan poin yang diubah.

Output HARUS berupa JSON valid persis sesuai dengan schema berikut:
{AMENDEMEN_JSON_SCHEMA}

Jawab HANYA dengan JSON valid, tanpa teks pengantar atau markdown tambahan di luar blok JSON.
"""

        try:
            raw_response = llm.invoke([SystemMessage(content=system_prompt)])
            raw_text = raw_response.content

            # Clean JSON formatting
            clean = raw_text.strip()
            if clean.startswith("```"):
                clean = clean.split("```", 2)[1]
                if clean.startswith("json"):
                    clean = clean[4:]
                clean = clean.rsplit("```", 1)[0]
            
            amendemen_json = json.loads(clean.strip())

            # Fallback & overwrite crucial deterministic form fields
            amendemen_json["nomor_addendum"] = nomor_addendum
            amendemen_json["tanggal_amendemen"] = tanggal_amendemen
            amendemen_json["tanggal_berlaku_efektif"] = tanggal_berlaku_efektif
            
            asal = amendemen_json.setdefault("kontrak_asal", {})
            asal["nomor_kontrak"] = nomor_kontrak_asal
            asal["judul_pekerjaan"] = judul_pekerjaan
            asal["tanggal_kontrak_asal"] = tanggal_kontrak_asal
            asal["nama_vendor"] = nama_vendor
            asal["nilai_kontrak_asal_str"] = nilai_kontrak_asal_str
            
            amendemen_json["ttd_pertamina_nama"] = ttd_pertamina_nama
            amendemen_json["ttd_pertamina_jabatan"] = ttd_pertamina_jabatan
            amendemen_json["ttd_vendor_nama"] = ttd_vendor_nama
            amendemen_json["ttd_vendor_jabatan"] = ttd_vendor_jabatan

            # Store in active draft store
            _active_amendment_store["current_draft"] = amendemen_json

            return f"Draft Amendemen berhasil di-generate! ({len(amendemen_json.get('perubahan', []))} poin perubahan dirumuskan)"

        except Exception as e:
            return f"Error saat generate JSON Draft Amendemen: {e}"


class ExportAmendemenToDocxTool:
    """Tool that exports the active amendment draft into a formatted DOCX file."""

    def invoke(self, kwargs: dict) -> str:
        output_filename = kwargs.get("output_filename", "")
        draft = _active_amendment_store.get("current_draft")
        if not draft:
            return "Error: Tidak ada draft Amendemen yang aktif. Silakan generate draft terlebih dahulu."

        try:
            from app.services.contract.docx_builder import render_amendemen_to_docx
            output_path = render_amendemen_to_docx(draft, output_filename)
            return f"📄 File: {output_path}"
        except Exception as e:
            return f"Error saat export Amendemen ke docx: {e}"


# Tool instances ready to be imported
generate_amendemen_document = GenerateAmendemenTool()
export_amendemen_to_docx = ExportAmendemenToDocxTool()
