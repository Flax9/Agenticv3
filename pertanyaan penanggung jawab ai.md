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
   **Hasil ukur web (19 Okt 2026, laptop CPU 4 core, model `qwen/qwen3.7-flash` via OpenRouter, agent RKS):**

   | Langkah | Durasi |
   |---|---|
   | Router + jawaban langsung | 5–14 detik |
   | Tanya-jawab KB (`retrieve_kb` + `kb_answer`) | ±46 detik (token pertama ±44 detik) |
   | Tiap pertanyaan klarifikasi | 12–29 detik |
   | `generate_rks_json` (draf penuh) | ±114 detik |
   | `upload_boq` (Docling, BoQ PDF 111 KB) | **±452 detik**, saat dua proses Docling berjalan bersamaan |
   | `export_docx` | <1 detik |

   **[Asumsi web]** chat memakai SSE dengan heartbeat 15 detik, sehingga proses panjang tidak terputus oleh timeout proxy, dan antrian Celery belum dibutuhkan. Apakah Docling untuk BoQ bisa dipercepat, misalnya ringkasan BoQ disiapkan saat sinkronisasi drive alih-alih di tengah percakapan, atau OCR dimatikan untuk PDF yang sudah berisi teks?

## E. Pertanyaan untuk Fase 3–5 (integrasi, streaming, deploy)

1. **Katalog 86 aturan STK:** siapa yang menyediakan datanya dan dalam format apa? Skrip seed web menerima JSON berisi `kode_stk`, `judul`, `kategori`, `deskripsi`, `teks_aturan`. Apakah aturan yang sama sudah ada di Qdrant (collection mana)? **[Asumsi web]** tabel `procurement_stk_rule` dibiarkan kosong sampai data resmi tersedia.
2. **Streaming chat:** apakah agent (LangGraph) bisa mengeluarkan token secara bertahap (`astream` / `astream_events`)? Bila belum, **[Asumsi web]** endpoint `/api/chat/stream` mengirim balasan utuh dalam satu event SSE, lalu diganti per token setelah agent siap.
3. **Retry LLM:** apakah *retry + exponential backoff* (maks. 3 kali) dipasang di dalam modul AI, atau web yang membungkus pemanggilannya? **[Asumsi web]** web tidak melakukan retry otomatis agar biaya token tidak berlipat; error dilaporkan ke user.
4. **Model internal / `LLM_PROVIDER`:** apakah ada rencana memakai model internal Pertamina selain OpenRouter? Variabel `.env` apa saja yang dibutuhkan (base URL, nama model, API key)?
5. **Qdrant produksi:** development memakai Qdrant Cloud. Bila produksi memakai Qdrant self-host di Docker, apakah collection perlu di-ingest ulang? Berapa dimensi vektor model embedding yang dipakai (`all-minilm-l6-v2` = 384)?
6. **Kebutuhan sumber daya:** model embedding berjalan lokal (sentence-transformers), begitu pula Docling untuk OCR. Berapa RAM/CPU (atau GPU) minimal yang disarankan untuk kontainer backend?
7. **Data yang dikirim ke LLM eksternal:** bagian mana dari RKS/BoQ (HPS, data vendor) yang boleh dikirim ke OpenRouter? Apakah perlu masking sebelum dikirim?

## F. Agent chat RKS (`agent.py` → `backend/app/services/agent/graph.py`)

Keputusan produk dari pemilik web (19 Okt 2026): produk akhir adalah **generator dokumen berbasis chatbot yang memberi arahan/feedback kepada pengguna yang belum berpengalaman**. Pengguna tidak lagi mengunggah BoQ; AI membaca knowledge base yang di-ingest dari folder drive eksternal (Google Drive/OneDrive). Untuk saat ini hanya pembuatan draf yang dibutuhkan (alur persetujuan belum dipakai). Ini menjawab sebagian pertanyaan B1 dan A2.

Sisi web memakai `agent.py` dari camp apa adanya (hanya import `RAG.` → `app.services.rag.` yang diubah). Satu sesi chat web = satu `thread_id`. Interrupt dijawab dengan `Command(resume=...)`, seperti di `main.py`.

| # | Temuan / pertanyaan | Lokasi | Dampak & penanganan sementara di web |
|---|---|---|---|
| 1 | Agent hanya ada untuk **RKS**. Belum ada agent untuk Tender, Kontrak, dan Amendemen. | `agent.py` | **[Asumsi web]** sesi non-RKS menjawab "asisten belum tersedia", dan dokumen dibuat lewat formulir kanvas + endpoint generate. Apakah agent untuk ketiga jenis itu akan dibuat? Apakah satu graph dengan parameter jenis dokumen, atau graph terpisah? |
| 2 | **Revisi tidak dipakai saat generate ulang.** Di `review_rks`, instruksi selain "setuju" mengulang `generate_rks_json`, tetapi prompt-nya hanya memakai `rks_fields` dan `kb_context`, bukan instruksi revisi user. | `review_rks`, `generate_rks_json` | Inti produk berbasis feedback tidak berjalan: draf hasil revisi tidak mengikuti permintaan user. |
| 3 | Persetujuan dideteksi dari *substring*: `"ya"`, `"ok"`, `"lanjut"`, dst. `"tidak setuju"` mengandung `"setuju"`, dan `"karyawan"` mengandung `"ya"`, sehingga dokumen bisa langsung diekspor. | `route_after_review` | Dokumen terekspor tanpa disetujui. |
| 4 | `upload_boq` menerima **path berkas lokal** dari teks user, dan pesan interrupt-nya meminta "ketik path lengkap". | `upload_boq` | Teks bebas bisa membuat agent membaca berkas apa pun di server. **Penanganan web:** saat agent menunggu BoQ, web hanya meneruskan kata "lewati/skip" atau path berkas yang dipilih dari folder dataset (sudah divalidasi berada di dalam `DATASET_DIR`). Mohon teks interrupt diganti, misalnya "pilih berkas BoQ dari drive atau ketik 'skip'". Apakah ke depan agent sebaiknya menerima ID berkas, bukan path? |
| 5 | `MemorySaver` menyimpan state di memori proses. | `build_graph` | Progres agent (field terkumpul, draf yang menunggu review) hilang saat server restart, sedangkan riwayat chat di database tetap ada. Apakah boleh dipindah ke `PostgresSaver` (paket `langgraph-checkpoint-postgres`) memakai database web? **Update 22 Okt 2026:** atas persetujuan pemilik web, satu baris di `build_graph` sudah diganti menjadi `make_checkpointer()` (`app/core/checkpointer.py`, memakai `PostgresSaver`). Logika node tidak berubah; mohon tim AI mengetahui perubahan ini dan memastikan state graph bisa diserialisasi (uji restart lulus di QA). |
| 6 | Path `.docx` hasil ekspor hanya tersedia di teks pesan (`` `path` ``), dan `rks_draft_json` dikosongkan setelah ekspor. | `export_docx` | Web mem-parsing path dari teks (rapuh, sama seperti C5). Usulan: simpan path di state, misalnya `docx_path`. |
| 7 | Model `qwen/qwen3.7-flash` ditulis langsung di kode (sama dengan C3), dan log memakai `print()` berisi emoji. | modul agent | Di Windows `print()` dengan emoji menggagalkan request (UnicodeEncodeError). Web sudah memaksa stdout UTF-8 di `main.py`. Usulan: memakai `logging`. |
| 8 | `retrieve_kb` dan `retrieve_examples` selalu memakai collection default `rks_kb`. | `agent.py` | Untuk Kontrak/Amendemen nanti, collection mana yang dipakai? |
| 9 | Streaming token (Fase 4): node `route_question` dan `clarify_rks` memakai *structured output*, sehingga token JSON-nya ikut ter-stream. | `agent.py` | **[Asumsi web]** web hanya meneruskan token dari node `direct_answer` dan `kb_answer`; node lain dikirim sebagai event progres. Mohon konfirmasi node mana yang aman di-stream. |

---

## G. Agent chat untuk Tender, Kontrak, dan Amendemen: apa yang sudah siap di web

Terakhir diperbarui: 23 Oktober 2026. Saat ini sesi non-RKS dijawab pesan tetap ("asisten belum tersedia") dan kolom ketik di UI dinonaktifkan. Bagian ini mencatat titik sambung yang **sudah ada di web** supaya agent baru tinggal dihubungkan.

**Titik sambung di web (sudah berjalan untuk RKS):**

| Hal | Keadaan sekarang |
|---|---|
| Penghubung | `backend/app/services/chat/agent_runner.py` (`RksAgentRunner`): satu sesi = satu `thread_id`, `interrupt()` dilanjutkan dengan `Command(resume=...)`, token dan progres node dikirim lewat SSE. |
| Pemilihan agent | `chat_routes.py` (`_prepare_turn`): `tipe_dokumen != RKS` langsung dijawab pesan tetap. Perlu pemetaan `tipe_dokumen` → runner bila agent baru ada. |
| Hasil yang dibaca web | `awaiting` (nama node interrupt), `fields` (field terkumpul), `new_draft` (JSON draf), dan path `.docx` di teks ekspor. Draf disimpan sebagai versi di tabel draf. |
| Lampiran | `dataset_file_id` dari folder drive diubah web menjadi path berkas lokal, hanya untuk RKS. |
| Checkpointer | PostgreSQL (`AGENT_CHECKPOINTER=postgres`), jadi sesi bisa dilanjutkan setelah restart. |

**Yang perlu diputuskan/disediakan tim AI per jenis dokumen (Tender, Kontrak, Amendemen):**

1. Apakah dibuat satu graph per jenis dokumen, atau satu graph dengan parameter jenis dokumen? Nama fungsi pembuatnya apa?
2. Field apa saja yang dikumpulkan agent (padanan `rks_fields`) dan field mana yang wajib. Untuk Tender, apakah ekstraksi BoQ/RKS yang sekarang di `/api/extract-tender-metadata` dipanggil sebagai node?
3. Bentuk draf yang dihasilkan: JSON seperti `rks_draft_json`, atau langsung parameter untuk generator yang ada (`/api/generate-tender|kontrak|amendemen`)? Web sudah menyimpan hasil generator itu sebagai versi draf per paket.
4. Node mana yang memakai `interrupt()` dan nama node-nya, supaya UI menampilkan petunjuk dan tombol yang tepat (seperti `upload_boq` dan `review_rks`).
5. Node mana yang aman di-stream tokennya (lihat F#9), dan collection Qdrant mana yang dipakai (`contract_kb`, `amendment_kb`; lihat F#8). Catatan: kedua collection itu saat ini **kosong** di Qdrant (cek 23 Okt 2026), jadi RAG kontrak/amendemen belum punya bahan.
6. Penanganan galat: web sekarang menerjemahkan galat LLM (kunci ditolak, kuota/rate limit, koneksi) menjadi pesan ramah. Agent cukup membiarkan exception naik, tidak perlu menangkapnya sendiri.

**Temuan operasional 23 Okt 2026 (bukan bug AI):** uji chat RKS langsung gagal karena `OPENROUTER_API_KEY` ditolak OpenRouter ("API key expired"). Perlu kunci baru dari pemilik akun OpenRouter.
