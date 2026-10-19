# Pertanyaan untuk Penanggung Jawab AI

Berkas ini mengumpulkan semua hal yang menyangkut **mekanisme AI** (prompt, LLM, RAG, ingest/chunking/embedding, generator dokumen) untuk didiskusikan dengan tim AI.
Tim web (arsitek & pengurus web) **tidak mengubah logika AI**. Modul AI di `backend/app/services/{rag,tender,contract}` adalah salinan dari `Agentic_Rag_Pertamina_camp`. Perbedaannya hanya pada:
- path import (`RAG.` → `app.services.rag.`, `config` → `app.config`);
- path `./assets` dan `./output` yang dijadikan absolut lewat `app.config` (agar tidak bergantung pada direktori kerja server).

Pemilik proyek web adalah arsitek & pengelola web, bukan penanggung jawab konfigurasi AI. Karena itu semua pertanyaan seputar AI dikumpulkan di sini. Pekerjaan web tetap berjalan dengan asumsi sementara yang ditandai **[Asumsi web]**.

Terakhir diperbarui: 19 Oktober 2026

---

## A. Revisi: dataset/knowledge dibaca dari drive eksternal

Rencana di sisi web: drive disinkronkan menjadi folder lokal (`DATASET_DIR`). Job sinkronisasi lalu memanggil fungsi yang **sudah ada**, yaitu `Vector_Store.ingest_bytes()` untuk berkas baru/berubah dan `delete_source()` untuk berkas yang hilang, tanpa mengubah cara kerjanya.

1. Drive yang dimaksud jenis apa: Google Drive, OneDrive/SharePoint, network drive kantor, atau hardisk eksternal?
2. Dataset dipakai untuk apa: knowledge base RAG (pengganti `RAG/Data`), berkas acuan per paket (BoQ/RKS), atau keduanya?
3. Apakah struktur subfolder per collection bisa diterima: `rks_kb/`, `contract_kb/`, `amendment_kb/`?
4. Ingest dipicu manual (tombol di UI), terjadwal, atau otomatis saat berkas berubah?
5. Format yang harus didukung: hanya PDF, atau juga Excel, Word, dan PDF hasil scan?
6. **Bentrok nama berkas:** `Vector_Store` mencatat sumber hanya dari nama berkas (`Path(filename).name`), bukan path lengkap. Dua berkas `RKS.pdf` di folder berbeda akan saling menimpa. Apakah metadata `source` bisa memakai path relatif? Untuk sementara, tim web akan menolak nama ganda saat sinkronisasi.
7. **PDF hasil scan saat ingest:** ingest memakai `PyPDFLoader`, sehingga PDF hasil scan kemungkinan tidak menghasilkan teks/chunk. Apakah perlu fallback OCR (Docling) seperti di `summarizer.extract_text_from_pdfs`?
8. Saat model embedding diganti, apakah collection perlu di-ingest ulang dari awal? Prosedurnya bagaimana?

## B. Revisi: proyek berbasis feedback seperti chatbot (Claude)

1. "Berbasis feedback" artinya apa:
   - (a) percakapan bolak-balik untuk merevisi dokumen (chat + canvas);
   - (b) penilaian 👍/👎 atau komentar pada jawaban AI;
   - (c) feedback dipakai untuk memperbaiki prompt atau model;
   - atau gabungan ketiganya?
2. **Kontrak endpoint chat** yang dibutuhkan frontend (saat ini balasan chat di UI masih simulasi):
   - path, misalnya `POST /api/chat/stream`;
   - format request: pesan, `session_id`, mode dokumen (`tender`/`rks`/`contract`/`amendment`), dan data paket aktif;
   - format respons: SSE per token atau sekaligus;
   - format *tool call* untuk mengubah dokumen, misalnya `{"tool": "update_clause", "field": "masa_pemeliharaan_hari", "value": 180}`, agar canvas bisa memperbarui dan menyorot perubahan.
3. Riwayat percakapan disimpan di mana: database web (tabel `ChatSession`/`ChatMessage` di Fase 2) atau memori agent (LangGraph)? Berapa pesan terakhir yang dikirim ke LLM?
4. Kalau ada feedback 👍/👎: field apa saja yang dibutuhkan tim AI (misalnya `message_id`, `rating`, `komentar`, `prompt_version`) dan bagaimana cara mereka mengambil datanya?
5. Perubahan dokumen dari chat langsung diterapkan, atau tetap menunggu konfirmasi user? Desain web saat ini mewajibkan konfirmasi untuk nilai kritikal (HPS, jaminan, denda, masa pemeliharaan).

## C. Temuan bug di modul AI (perlu ditindaklanjuti tim AI)

| # | Temuan | Lokasi | Dampak |
|---|---|---|---|
| 1 | Variabel `llm` **tidak didefinisikan** di `extract_tender_metadata_from_docs`. Error-nya ditangkap lalu fungsi mengembalikan `defaults`. | `rag/summarizer.py` (sekitar baris 325) | **Ekstraksi metadata tidak pernah memakai LLM.** Hasilnya selalu angka default (Rp 13.283.434.534, dll.) tanpa tanda error. Terverifikasi dengan BoQ nyata: log menunjukkan `name 'llm' is not defined`. |
| 2 | Bila teks tidak terbaca atau LLM gagal, fungsi diam-diam mengembalikan nilai default. | `rag/summarizer.py` | User mengira nilai default adalah hasil ekstraksi dari berkasnya. |
| 3 | Nama model tidak konsisten: `qwen/qwen3.7-flash` ditulis langsung di kode, sedangkan `LLM_MODEL_NAME` default-nya `qwen/qwen3-7b-flash`. | `summarizer.py`, `tools.py`, `tender/generator.py` vs `contract/*.py` | Generator kontrak/amendemen memakai model yang berbeda, dan mungkin tidak valid di OpenRouter. Mohon dicek. |
| 4 | Draf disimpan di variabel global modul (`_active_*_store`), lalu tool export membacanya dari sana. | `rag/tools.py`, `tender/generator.py`, `contract/*generator.py` | Dua user yang generate bersamaan bisa saling menimpa draf. Tim web memasang **lock per jenis dokumen** di `tender_routes.py` sebagai pengaman sementara, tetapi akibatnya request diproses satu per satu (latensi). Usulan: generator langsung mengembalikan draf/path berkas. |
| 5 | Path berkas `.docx` diambil dengan mem-parsing teks keluaran (`"📄 File: ..."`). | semua tool export | Rapuh bila format teks berubah. Usulan: kembalikan path atau objek terstruktur. |
| 6 | Default dan prompt memuat nama pejabat sungguhan ("Rigga Widar Atmagi"). | `rag/summarizer.py` | Data pribadi ikut di repo dan bisa masuk ke dokumen bila tidak ditemukan di berkas. |
| 7 | `langchain-community` dan `langchain-experimental` sudah *deprecated* (muncul peringatan saat test). | `rag/vector_store.py` | Perlu rencana migrasi. |

### Usulan perbaikan untuk temuan 1–3 (sudah diuji)

Perbaikan ini sempat dicoba lalu **dikembalikan** karena ranahnya tim AI. Dengan perbaikan ini, ekstraksi BoQ nyata (`boq-tangki-siantar`) menghasilkan nama paket "PEMBANGUNAN TANGKI AIR KAPASITAS 1.000 KL" dan prime cost Rp 7.140.710.058 dalam ±44 detik.

```diff
--- asli/rag/summarizer.py
+++ usulan/rag/summarizer.py
@@ import
+from app.config import LLM_MODEL_NAME
@@ def summarize_context
-    llm = ChatOpenRouter(model="qwen/qwen3.7-flash", temperature=0)
+    llm = ChatOpenRouter(model=LLM_MODEL_NAME, temperature=0)
@@ def extract_tender_metadata_from_docs
     if not rks_text.strip() and not boq_text.strip():
-        return defaults
+        raise ValueError("Tidak ada teks yang dapat dibaca dari berkas RKS/BoQ yang diunggah.")
@@
+    llm = ChatOpenRouter(model=LLM_MODEL_NAME, temperature=0)
     try:
         response = llm.invoke([SystemMessage(content=prompt)])
@@
     except Exception as e:
         print(f"Error extracting tender metadata with LLM: {e}")
-        return defaults
+        raise RuntimeError(f"LLM gagal mengekstrak parameter: {e}") from e
```

Penggantian `model="qwen/qwen3.7-flash"` → `model=LLM_MODEL_NAME` juga berlaku di `rag/tools.py` dan `tender/generator.py`, disertai penyesuaian default `LLM_MODEL_NAME` sesuai model yang benar.

> Endpoint `/api/extract-tender-metadata` di sisi web sudah siap menerima kedua error itu: `ValueError` → HTTP 422 dan error lain → HTTP 502. Frontend akan menampilkan pesan yang jelas kepada user.

## D. Kebutuhan dari sisi web (latensi & duplikasi)

Hal-hal berikut dikerjakan tim web. Tim AI cukup mengetahuinya atau memberi masukan.

1. **Cache hasil ekstraksi per hash berkas (SHA-256):** berkas yang sama tidak akan dikirim ulang ke LLM. Mohon konfirmasi bahwa hasil ekstraksi untuk berkas yang sama boleh dipakai ulang (deterministik, `temperature=0`).
2. **Dedup upload dan ingest berdasarkan hash:** berkas identik tidak di-ingest dua kali ke Qdrant.
3. **Pemrosesan di background untuk proses lama** (ekstraksi ±44 detik, generate dokumen): pola *job* + status progres di UI.
4. Mohon estimasi waktu proses tiap generator (Tender/RKS/Kontrak/Amendemen) untuk menentukan batas timeout Nginx dan kebutuhan antrian.

## E. Pertanyaan untuk Fase 3–5 (integrasi, streaming, deploy)

1. **Katalog 86 aturan STK:** siapa yang menyediakan datanya dan dalam format apa? Skrip seed web menerima JSON berisi `kode_stk`, `judul`, `kategori`, `deskripsi`, `teks_aturan`. Apakah aturan yang sama sudah ada di Qdrant (collection mana)? **[Asumsi web]** tabel `procurement_stk_rule` dibiarkan kosong sampai data resmi tersedia.
2. **Streaming chat:** apakah agent (LangGraph) bisa mengeluarkan token secara bertahap (`astream` / `astream_events`)? Bila belum, **[Asumsi web]** endpoint `/api/chat/stream` mengirim balasan utuh dalam satu event SSE, lalu diganti per token setelah agent siap.
3. **Retry LLM:** apakah *retry + exponential backoff* (maks. 3 kali) dipasang di dalam modul AI, atau web yang membungkus pemanggilannya? **[Asumsi web]** web tidak melakukan retry otomatis agar biaya token tidak berlipat; error dilaporkan ke user.
4. **Model internal / `LLM_PROVIDER`:** apakah ada rencana memakai model internal Pertamina selain OpenRouter? Variabel `.env` apa saja yang dibutuhkan (base URL, nama model, API key)?
5. **Qdrant produksi:** development memakai Qdrant Cloud. Bila produksi memakai Qdrant self-host di Docker, apakah collection perlu di-ingest ulang? Berapa dimensi vektor model embedding yang dipakai (`all-minilm-l6-v2` = 384)?
6. **Kebutuhan sumber daya:** model embedding berjalan lokal (sentence-transformers), begitu pula Docling untuk OCR. Berapa RAM/CPU (atau GPU) minimal yang disarankan untuk kontainer backend?
7. **Data yang dikirim ke LLM eksternal:** bagian mana dari RKS/BoQ (HPS, data vendor) yang boleh dikirim ke OpenRouter? Apakah perlu masking sebelum dikirim?
