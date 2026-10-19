"""
LLM Generator & Orchestrator for Rancangan Kontrak Definitif Pertamina.
Extracts project parameters, performs RAG retrieval from contract_kb,
prompts LLM for strict JSON schema output, merges form overrides,
and stores the active draft.
"""

import json
import os
from typing import Dict, Any, Optional
import logging

from langchain_core.messages import SystemMessage
from langchain_openrouter import ChatOpenRouter
from dotenv import load_dotenv

from app.services.contract.schema import KONTRAK_JSON_SCHEMA
from app.services.rag.vector_store import Vector_Store
from app.config import COLLECTION_CONTRACT, LLM_MODEL_NAME

load_dotenv()
logger = logging.getLogger(__name__)

# Global store for active contract draft
_active_kontrak_store: Dict[str, Any] = {}

def _format_rupiah(val: float) -> str:
    """Format numeric float to Rupiah string."""
    try:
        val_int = int(val)
        formatted = f"{val_int:,}".replace(",", ".")
        return f"Rp{formatted},00"
    except Exception:
        return f"Rp{val}"


class GenerateKontrakTool:
    """Tool that generates a complete Kontrak Definitif JSON payload using LLM."""

    def invoke(self, kwargs: dict) -> str:
        judul_pekerjaan = kwargs.get("nama_pekerjaan", "Pekerjaan Konstruksi")
        nomor_kontrak = kwargs.get("nomor_kontrak", "KTR-001/PND/2026")
        tanggal_kontrak = kwargs.get("tanggal_kontrak", "01 Januari 2026")
        lokasi_pekerjaan = kwargs.get("lokasi_pekerjaan", "Balikpapan")
        jenis_kontrak = kwargs.get("jenis_kontrak", "Gabungan Harga Satuan & Lumpsum")
        
        nama_vendor = kwargs.get("nama_vendor", "PT Vendor Contoh")
        npwp_vendor = kwargs.get("npwp_vendor", "00.000.000.0-000.000")
        
        nilai_kontrak = float(kwargs.get("nilai_kontrak", 1000000000.0))
        sistem_pembayaran = kwargs.get("sistem_pembayaran", "Monthly Progress")
        
        durasi_hari = int(kwargs.get("durasi_hari", 180))
        masa_pemeliharaan = int(kwargs.get("masa_pemeliharaan", 90))
        resiko_csms = kwargs.get("resiko_csms", "Tinggi")
        
        pejabat_ttd_pertamina = kwargs.get("pejabat_ttd_pertamina", "Executive General Manager")
        
        context_summary = kwargs.get("context_summary", "")

        # RAG Retrieval from contract_kb to get similar clause examples
        rag_context = ""
        try:
            vs = Vector_Store(collection_name=COLLECTION_CONTRACT)
            results = vs.retrieve(f"Rancangan Kontrak {judul_pekerjaan} {jenis_kontrak}", k=3)
            if results:
                rag_context = "\n\n".join([f"[Referensi Kontrak]: {doc.page_content}" for doc in results])
        except Exception as e:
            logger.warning(f"Failed to retrieve from {COLLECTION_CONTRACT}: {e}")

        llm = ChatOpenRouter(model=LLM_MODEL_NAME, temperature=0)

        system_prompt = f"""
Kamu adalah Legal Counsel PT Pertamina Patra Niaga yang ahli dalam penyusunan Rancangan Kontrak Definitif pengadaan barang/jasa berdasarkan Pedoman Pengadaan No. A03-001/PNG200000/2024-S9.

Tugas kamu adalah menyusun isi dari 20 pasal kontrak secara spesifik untuk pekerjaan berikut:
- Judul Pekerjaan        : {judul_pekerjaan}
- Nomor Kontrak          : {nomor_kontrak}
- Tanggal                : {tanggal_kontrak}
- Lokasi Pekerjaan       : {lokasi_pekerjaan}
- Jenis Kontrak          : {jenis_kontrak}
- Nama Penyedia (Vendor) : {nama_vendor}
- NPWP Penyedia          : {npwp_vendor}
- Nilai Kontrak          : {_format_rupiah(nilai_kontrak)}
- Sistem Pembayaran      : {sistem_pembayaran}
- Durasi Pekerjaan       : {durasi_hari} hari kalender
- Masa Pemeliharaan      : {masa_pemeliharaan} hari kalender
- Risiko CSMS            : {resiko_csms}
- Pejabat TTD Pertamina  : {pejabat_ttd_pertamina}

Konteks Lingkup Pekerjaan (Dari RKS/BOQ jika ada):
{context_summary}

Referensi Kontrak Serupa (Gunakan sebagai acuan gaya bahasa dan pasal jika relevan):
{rag_context}

Fokus Tugas Khusus:
1. Isi setiap 'ayat' di dalam ke-20 pasal dengan bahasa hukum yang formal, mengikat, dan spesifik sesuai jenis pekerjaan '{judul_pekerjaan}'. Jangan gunakan template kosong.
2. Pastikan Pasal 2 (Lingkup Pekerjaan) merincikan garis besar pekerjaan berdasarkan konteks yang diberikan.
3. Pastikan Pasal 4 mencantumkan nilai kontrak dan mekanisme {sistem_pembayaran}.
4. Pastikan Pasal 7 memuat ketentuan K3LL/CSMS tingkat {resiko_csms}.

Output HARUS berupa JSON valid persis sesuai dengan schema berikut:
{KONTRAK_JSON_SCHEMA}

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
            
            kontrak_json = json.loads(clean.strip())

            # Fallback & overwrite crucial deterministic form fields
            kontrak_json["judul_pekerjaan"] = judul_pekerjaan
            kontrak_json["nomor_kontrak"] = nomor_kontrak
            kontrak_json["tanggal_kontrak"] = tanggal_kontrak
            kontrak_json["lokasi_pekerjaan"] = lokasi_pekerjaan
            kontrak_json["jenis_kontrak"] = jenis_kontrak
            
            pihak_pertamina = kontrak_json.setdefault("pihak_pertamina", {})
            pihak_pertamina["diwakili_oleh"] = "____________________" # Can be updated if we pass name
            pihak_pertamina["jabatan"] = pejabat_ttd_pertamina
            
            pihak_vendor = kontrak_json.setdefault("pihak_vendor", {})
            pihak_vendor["nama_perusahaan"] = nama_vendor
            pihak_vendor["npwp"] = npwp_vendor
            
            nilai_k = kontrak_json.setdefault("nilai_kontrak", {})
            nilai_k["nilai_kontrak"] = nilai_kontrak
            nilai_k["nilai_kontrak_str"] = _format_rupiah(nilai_kontrak)
            nilai_k["sistem_pembayaran"] = sistem_pembayaran
            
            waktu_k = kontrak_json.setdefault("jangka_waktu", {})
            waktu_k["durasi_hari_kalender"] = durasi_hari
            waktu_k["masa_pemeliharaan_hari"] = masa_pemeliharaan
            
            kontrak_json["tingkat_risiko_csms"] = resiko_csms

            # Store in active draft store
            _active_kontrak_store["current_draft"] = kontrak_json

            return f"Draft Rancangan Kontrak berhasil di-generate! ({len(kontrak_json.get('pasal', []))} pasal disusun)"

        except Exception as e:
            return f"Error saat generate JSON Rancangan Kontrak: {e}"


class ExportKontrakToDocxTool:
    """Tool that exports the active kontrak draft into a formatted DOCX file."""

    def invoke(self, kwargs: dict) -> str:
        output_filename = kwargs.get("output_filename", "")
        draft = _active_kontrak_store.get("current_draft")
        if not draft:
            return "Error: Tidak ada draft Rancangan Kontrak yang aktif. Silakan generate draft terlebih dahulu."

        try:
            from app.services.contract.docx_builder import render_kontrak_to_docx
            output_path = render_kontrak_to_docx(draft, output_filename)
            return f"📄 File: {output_path}"
        except Exception as e:
            return f"Error saat export Rancangan Kontrak ke docx: {e}"


# Tool instances ready to be imported
generate_kontrak_document = GenerateKontrakTool()
export_kontrak_to_docx = ExportKontrakToDocxTool()
