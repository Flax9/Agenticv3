import json
from app.services.rag.vector_store import Vector_Store
from app.services.rag.docx_exporter import render_to_docx
from langchain_core.messages import SystemMessage
from langchain_openrouter import ChatOpenRouter
from dotenv import load_dotenv

load_dotenv()

# Global dictionary to act as the active draft storage, simulating the old behavior
_active_draft_store = {}

_RKS_JSON_SCHEMA = """
{
  "cover_page": {
    "judul_pekerjaan": "<string>",
    "resiko_csms": "<HIGH|MIDDLE|LOW>",
    "nama_perusahaan": "<string>"
  },
  "metadata": {
    "nomor_dokumen": "<string>",
    "tahun": "<string>"
  },
  "pengesahan": {
    "disusun_oleh":  {"nama": "<string>", "jabatan": "<string>"},
    "diperiksa_oleh":{"nama": "<string>", "jabatan": "<string>"},
    "disetujui_oleh":{"nama": "<string>", "jabatan": "<string>"}
  },
  "bab": [
    {
      "nomor": "I",
      "judul": "<string>",
      "sub_bab": [
        {
          "nomor": "1.1",
          "judul": "<string>",
          "tipe": "<paragraf|numbered_list|bullet_list|table|heading_only>",
          "konten": "<string or list or table dict>"
        }
      ]
    }
  ]
}
"""

class GenerateRKSDocumentTool:
    def invoke(self, kwargs: dict) -> str:
        # 1. Search vector store
        try:
            vs = Vector_Store()
            query = f"Struktur dan isi RKS untuk pekerjaan {kwargs.get('jenis_pekerjaan', '')}"
            docs = vs.doc_store.similarity_search(query, k=5)
            context_text = "\n\n".join(f"[Referensi {i+1}]\n{doc.page_content}" for i, doc in enumerate(docs))
        except Exception as e:
            return f"Error saat search KB: {e}"

        # 2. Call LLM
        llm = ChatOpenRouter(model="qwen/qwen3.7-flash", temperature=0)
        
        system = SystemMessage(content=f"""
Kamu adalah generator dokumen RKS (Rencana Kerja dan Syarat-Syarat) Pertamina.

Buatlah dokumen RKS yang lengkap dan formal berdasarkan informasi berikut.
Gunakan referensi dokumen yang diberikan untuk menentukan struktur bab yang sesuai.

Informasi Dokumen:
- Judul Pekerjaan : {kwargs.get('jenis_pekerjaan', '')} - {kwargs.get('detail_pekerjaan', '')}
- Risiko CSMS     : {kwargs.get('resiko_csms', 'HIGH')}
- Nama Perusahaan : {kwargs.get('nama_perusahaan', 'PT PERTAMINA (PERSERO)')}
- Nomor Dokumen   : {kwargs.get('nomor_dokumen', '')}
- Lokasi          : {kwargs.get('lokasi', '')}

Konteks Tambahan (Ringkasan BOQ/Spesifikasi):
{kwargs.get('context_summary', '')}

Referensi RKS Sejenis:
{context_text}

Output HARUS berupa JSON valid dengan schema berikut:
{_RKS_JSON_SCHEMA}

Buat minimal 5 bab (BAB I hingga BAB V atau lebih sesuai jenis pekerjaan).
Setiap bab harus memiliki konten yang relevan dan substantif.
Jawab HANYA dengan JSON, tanpa teks lain.
""")
        try:
            raw_response = llm.invoke([system])
            raw_text = raw_response.content
            
            # parse JSON
            clean = raw_text.strip()
            if clean.startswith("```"):
                clean = clean.split("```", 2)[1]
                if clean.startswith("json"):
                    clean = clean[4:]
                clean = clean.rsplit("```", 1)[0]
            draft_json = json.loads(clean.strip())
            
            # STORE in global variable for the export tool to pick up!
            _active_draft_store["current_draft"] = draft_json
            
            return f"Draft RKS berhasil di-generate! ({len(draft_json.get('bab', []))} bab)"
        except Exception as e:
            return f"Error saat generate JSON: {e}"

generate_rks_document = GenerateRKSDocumentTool()


class ExportRKSToDocxTool:
    def invoke(self, kwargs: dict) -> str:
        output_filename = kwargs.get("output_filename", "")
        draft = _active_draft_store.get("current_draft")
        if not draft:
            return "Error: Tidak ada draft RKS yang aktif. Silakan generate draft terlebih dahulu."
        
        try:
            output_path = render_to_docx(draft, output_filename)
            return f"📄 File: {output_path}"
        except Exception as e:
            return f"Error saat export ke docx: {e}"

export_rks_to_docx = ExportRKSToDocxTool()

