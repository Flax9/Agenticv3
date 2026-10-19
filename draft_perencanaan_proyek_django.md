# Draft Perencanaan Proyek: Pertamina Procurement AI Copilot & Live Canvas
**Arsitektur Modern Decoupled: Frontend agenticv3 + Backend FastAPI (ASGI) + SQLAlchemy 2.0 + Celery + Nginx Reverse Proxy + CI/CD Docker**

---

## 1. Ringkasan Eksekutif & Tujuan Proyek

Proyek ini bertujuan mengintegrasikan antarmuka frontend modern **`agenticv3`** (berbasis *Claude-style Live Canvas*, *Progress Drawer*, dan *Vertical Docked Tab*) dengan backend **FastAPI (Python 3.11/3.12)** yang berkinerja tinggi (*high-concurrency async*). 

Sistem ini mengadopsi **Opsi A (Nginx Reverse Proxy Decoupled)**, di mana:
1. **Nginx** menyajikan berkas antarmuka frontend `agenticv3` (HTML5, Vanilla CSS, Vanilla JS) secara langsung ke pengguna dengan latensi ultra-rendah (< 2 ms) melalui *caching* dan Linux `sendfile`.
2. **FastAPI** beroperasi secara terdedikasi sebagai backend ASGI di port internal 8000 untuk menangani komputasi AI, validasi Pydantic v2, *token streaming* (Server-Sent Events), koneksi Qdrant Vector DB, serta pembentukan dokumen resmi PT Pertamina Patra Niaga (IKPP Versi 2.0 40 Poin, RKS, Kontrak Definitif, dan Amendemen) yang patuh terhadap Pedoman No. A03-001/PNG200000/2024-S9.
3. **SQLAlchemy 2.0 (Async) + Alembic** menangani persistensi data relasional ke PostgreSQL untuk 8 tabel pengadaan, riwayat chat, dan audit kepatuhan.

---

## 2. Arsitektur Sistem Terpadu (Opsi A: Decoupled via Nginx)

```mermaid
graph TD
    Client["Browser Pengguna (agenticv3 UI)"] -->|Port 80/443| Nginx["Nginx Edge Gateway & Reverse Proxy"]
    
    subgraph "Ingress & Presentation Layer"
        Nginx -->|GET / & Static Assets| FrontendDisk["Frontend Web Root (agenticv3 HTML/CSS/JS)"]
        Nginx -->|POST/GET /api/... Buffering & Timeout 300s| FastAPI["FastAPI ASGI Server (Uvicorn)"]
    end

    subgraph "Application & Service Layer (FastAPI)"
        FastAPI --> Routers["API Route Controllers (Pydantic V2)"]
        FastAPI --> Auth["Token Validation & Security"]
        FastAPI --> ORM["SQLAlchemy 2.0 Async ORM"]
        FastAPI --> TaskDispatch["Celery / Background Dispatcher"]
    end

    subgraph "Worker & AI Engine Layer"
        TaskDispatch --> Redis["Redis Message Broker & Cache"]
        Redis --> Celery["Celery Worker"]
        Celery --> RAG["RAG Engine & Summarizer (pypdf/openpyxl)"]
        Celery --> DocxGen["Docx Generator (python-docx)"]
        RAG --> Qdrant["Qdrant Vector DB (86 STK Rules)"]
        RAG --> LLM["LLM Engine (OpenRouter Qwen / Internal)"]
    end

    subgraph "Storage Layer"
        Celery --> MediaDisk["Media Storage (BoQ Uploads & Generated .DOCX)"]
        ORM --> DB[(PostgreSQL 16 Database)]
    end
```

---

## 3. Struktur Direktori Proyek Target

```text
pertamina_procurement/
│
├── .github/                               # [CI/CD] Otomasi Pipeline
│   └── workflows/
│       ├── ci.yml                         # Uji otomatis (flake8, pytest, docker build test)
│       └── deploy.yml                     # Deploy otomatis via SSH ke server produksi
│
├── deploy/                                # Konfigurasi Server
│   └── nginx/
│       └── default.conf                   # Reverse proxy, buffer upload 100MB, timeout 300s
│
├── frontend/                              # [DARI AGENTICV3] Static Single Page Interface
│   ├── index.html                         # Antarmuka utama (Live Canvas, Chat, Drawer)
│   ├── css/
│   │   ├── main.css                       # Layout, topbar, restore tab vertikal
│   │   ├── canvas.css                     # Review dokumen editor & tabs
│   │   └── chat.css                       # Chat bubble, cards, drawer
│   ├── js/
│   │   ├── state.js                       # Store reactive state
│   │   ├── api.js                         # Fetch client ke endpoint FastAPI /api/...
│   │   ├── chat.js                        # Controller chat & drawer
│   │   ├── canvas.js                      # Controller editor review dokumen
│   │   └── app.js                         # Bootstrap aplikasi
│   └── images/                            # Logo Pertamina & icons
│
├── backend/                               # [FASTAPI ASGI BACKEND]
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                        # Entrypoint FastAPI (CORS, routers, lifecycle)
│   │   ├── config.py                      # Pydantic BaseSettings (.env, Qdrant URL, DB URL)
│   │   ├── database.py                    # SQLAlchemy Async Engine & session maker
│   │   │
│   │   ├── models/                        # SQLAlchemy 2.0 ORM Models (8 Tabel)
│   │   │   ├── __init__.py
│   │   │   ├── tender.py                  # TenderProject, DocumentDraft, DocumentClause
│   │   │   ├── attachment.py              # UploadedAttachment
│   │   │   ├── chat.py                    # ChatSession, ChatMessage
│   │   │   └── compliance.py              # StkRule, AuditTrail
│   │   │
│   │   ├── schemas/                       # Pydantic V2 Schemas (Request/Response validation)
│   │   │   ├── tender_schema.py           # Validasi nilai HPS, tanggal, risiko CSMS
│   │   │   ├── chat_schema.py             # Format pesan & tool-calls
│   │   │   └── kb_schema.py               # Metadata ingest berkas STK
│   │   │
│   │   ├── api/                           # Route Handlers (/api/...)
│   │   │   ├── __init__.py
│   │   │   ├── tender_routes.py           # /api/extract-metadata, /api/generate-tender, dll
│   │   │   ├── chat_routes.py             # /api/chat (Streaming SSE token per kata)
│   │   │   ├── kb_routes.py               # /api/kb/ingest, /api/kb/list
│   │   │   └── health_routes.py           # /api/health
│   │   │
│   │   └── services/                      # AI & RAG Pipeline (Porting dari Python Camp)
│   │       ├── summarizer.py              # Ekstraksi PDF acuan & BoQ Excel
│   │       ├── vector_store.py            # Wrapper Qdrant Vector Store
│   │       ├── tender_generator.py        # Generator 40 Poin IKPP Dokumen Tender
│   │       ├── rks_generator.py           # Generator RKS & CSMS
│   │       ├── contract_generator.py      # Generator Kontrak Definitif & Amendemen
│   │       └── tasks.py                   # Celery tasks (export docx berat & housekeeping)
│   │
│   ├── alembic/                           # Database Migration Tool (Alembic)
│   │   ├── env.py
│   │   └── versions/                      # Berkas riwayat migrasi tabel
│   ├── alembic.ini
│   ├── requirements.txt                   # fastapi, uvicorn, sqlalchemy, qdrant-client, docx
│   └── tests/                             # Pytest automated test suites
│       ├── test_api_tender.py
│       └── test_generator.py
│
├── media/                                 # Penyimpanan Berkas Bersama (Docker Volume)
│   ├── uploads/                           # Berkas BoQ / RKS acuan yang diunggah
│   └── generated_docs/                    # Berkas .docx hasil generate siap unduh
│
├── output/                                # Folder scratch/temp untuk pemrosesan file
├── .env                                   # API Keys, Qdrant URL, DB Credentials
├── .env.example                           # Template variabel lingkungan bebas rahasia
├── Dockerfile                             # Multi-stage Docker build untuk FastAPI & Celery
└── docker-compose.yml                     # Orkestrasi 6 kontainer terpadu
```

---

## 4. Desain Database & Kamus Data Lengkap (SQLAlchemy 2.0 Specifications)

1. **`TenderProject`**:
   - `id`: UUID (Primary Key)
   - `nama_pengadaan`: String(255)
   - `tipe_dokumen`: String (`tender`, `rks`, `kontrak`, `amendemen`)
   - `hps_total`: Numeric(18,2)
   - `resiko_csms`: String (`Tinggi`, `Sedang`, `Rendah`)
   - `current_step`: Integer (1: BoQ, 2: Ekstraksi, 3: Verifikasi, 4: Terbit)
   - `created_at`, `updated_at`: DateTime(timezone=True)

2. **`DocumentDraft`**:
   - `project_id`: ForeignKey(`TenderProject.id`)
   - `versi`: String (`v1.0`, `v2.0`)
   - `file_docx_path`: String(500)
   - `content_json`: JSONB (Struktur 40 pasal IKPP & matriks)
   - `skor_kepatuhan_stk`: Integer (0 - 100)
   - `is_active`: Boolean

3. **`ChatMessage`**:
   - `session_id`: ForeignKey(`ChatSession.id`)
   - `role`: String (`user`, `assistant`, `system`)
   - `content`: Text
   - `tool_calls`: JSONB (menyimpan jejak revisi klausul otomatis)
   - `created_at`: DateTime(timezone=True)

4. **`KnowledgeReference`**:
   - `kode_pedoman`: String (`A03-001/PNG200000/2024-S9`)
   - `nomor_aturan`: String (`STK-01` s.d. `STK-86`)
   - `qdrant_point_id`: String(64)

### 4.1 Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    AUTH_USER ||--o{ PROCUREMENT_TENDER_PROJECT : "membuat / mengelola"
    PROCUREMENT_TENDER_PROJECT ||--o{ PROCUREMENT_DOCUMENT_DRAFT : "memiliki riwayat versi"
    PROCUREMENT_TENDER_PROJECT ||--o{ PROCUREMENT_UPLOADED_ATTACHMENT : "memiliki berkas acuan"
    PROCUREMENT_TENDER_PROJECT ||--o{ PROCUREMENT_CHAT_SESSION : "memiliki sesi diskusi AI"
    PROCUREMENT_TENDER_PROJECT ||--o{ PROCUREMENT_AUDIT_TRAIL : "mencatat jejak aktivitas"
    
    PROCUREMENT_DOCUMENT_DRAFT ||--o{ PROCUREMENT_DOCUMENT_CLAUSE : "terdiri dari 40 pasal IKPP"
    
    PROCUREMENT_CHAT_SESSION ||--o{ PROCUREMENT_CHAT_MESSAGE : "berisi percakapan"
    
    PROCUREMENT_STK_RULE ||--o{ PROCUREMENT_DOCUMENT_CLAUSE : "menjadi dasar validasi kepatuhan"

    AUTH_USER {
        int id PK
        string username
        string email
        string first_name
        string last_name
        boolean is_active
    }

    PROCUREMENT_TENDER_PROJECT {
        uuid id PK
        int user_id FK
        string no_tender UK
        string nama_pengadaan
        string tipe_dokumen
        decimal hps_total
        string resiko_csms
        string status_tahap
        int current_step
        jsonb metadata_ekstraksi
        timestamp created_at
        timestamp updated_at
    }

    PROCUREMENT_DOCUMENT_DRAFT {
        uuid id PK
        uuid project_id FK
        string versi
        string judul_dokumen
        string file_docx_path
        int skor_kepatuhan_stk
        boolean is_active
        string status_approval
        timestamp created_at
        timestamp updated_at
    }

    PROCUREMENT_DOCUMENT_CLAUSE {
        uuid id PK
        uuid draft_id FK
        int nomor_urut
        string kode_pasal
        string judul_pasal
        text teks_original
        text teks_revisi_ai
        boolean is_edited_manual
        string status_verifikasi
        string catatan_stk
        timestamp updated_at
    }

    PROCUREMENT_UPLOADED_ATTACHMENT {
        uuid id PK
        uuid project_id FK
        string tipe_berkas
        string nama_file_asli
        string file_path
        bigint ukuran_bytes
        string hash_md5
        jsonb hasil_ekstraksi_json
        timestamp uploaded_at
    }

    PROCUREMENT_CHAT_SESSION {
        uuid id PK
        uuid project_id FK
        string judul_sesi
        boolean is_active
        timestamp created_at
    }

    PROCUREMENT_CHAT_MESSAGE {
        uuid id PK
        uuid session_id FK
        string role
        text content
        jsonb tool_calls
        jsonb artifacts_payload
        int prompt_tokens
        int completion_tokens
        timestamp created_at
    }

    PROCUREMENT_STK_RULE {
        int id PK
        string kode_pedoman
        string nomor_aturan
        string kategori_stk
        string judul_aturan
        text deskripsi_aturan
        text klausul_baku_docx
        string level_kepatuhan
        string qdrant_point_id
        timestamp updated_at
    }

    PROCUREMENT_AUDIT_TRAIL {
        bigint id PK
        uuid project_id FK
        int user_id FK
        string tipe_aksi
        string modul_terkait
        text rincian_perubahan
        string ip_address
        timestamp recorded_at
    }
```

### 4.2 Kamus Data & Spesifikasi Rinci Setiap Tabel

#### 1. Tabel: `procurement_tender_project`
* **Deskripsi:** Menyimpan entitas utama paket pekerjaan tender/pengadaan yang sedang disusun oleh Pejabat Pembuat Komitmen (PPK) atau Tim Pengadaan.
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, Default: `gen_random_uuid()` | Pengenal unik proyek tender |
| `user_id` | `INTEGER` | `FOREIGN KEY` -> `auth_user.id`, `ON DELETE SET NULL`, Nullable | Akun pegawai / PPK pembuat proyek |
| `no_tender` | `VARCHAR(100)` | `UNIQUE`, `INDEX`, Nullable | Nomor resmi paket tender (misal: `PR-2026-PN-0042`) |
| `nama_pengadaan` | `VARCHAR(255)` | `NOT NULL` | Nama paket pengadaan barang/jasa |
| `tipe_dokumen` | `VARCHAR(50)` | `NOT NULL`, Default: `'tender'` | Pilihan: `'tender'` (IKPP 2.0), `'rks'`, `'kontrak'`, `'amendemen'` |
| `hps_total` | `NUMERIC(18,2)`| `NOT NULL`, Default: `0.00` | Nilai Total Harga Perkiraan Sendiri (Rupiah) |
| `resiko_csms` | `VARCHAR(20)` | `NOT NULL`, Default: `'Tinggi'` | Tingkat risiko K3L: `'Ekstrim'`, `'Tinggi'`, `'Sedang'`, `'Rendah'` |
| `status_tahap` | `VARCHAR(50)` | `NOT NULL`, Default: `'DRAFT'` | Status alur: `'DRAFT'`, `'EKSTRAKSI'`, `'REVIEW_CANVAS'`, `'PUBLISHED'` |
| `current_step` | `SMALLINT` | `NOT NULL`, Default: `1` | Indikator tahap 1-4 pada Progress Drawer UI |
| `metadata_ekstraksi` | `JSONB` | Nullable, Default: `{}` | Parameter hasil parsing BoQ/TOR (jangka waktu, jaminan, denda) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu inisiasi sesi proyek |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu pembaruan terakhir |

---

#### 2. Tabel: `procurement_document_draft`
* **Deskripsi:** Menyimpan versi dan draf dokumen Microsoft Word (`.docx`) yang dihasilkan oleh sistem AI / diekspor pengguna. Mendukung *versioning* (v1.0, v2.0, dll).
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, Default: `gen_random_uuid()` | Pengenal unik draf dokumen |
| `project_id` | `UUID` | `FOREIGN KEY` -> `procurement_tender_project.id`, `ON DELETE CASCADE` | Relasi ke paket tender pemilik |
| `versi` | `VARCHAR(20)` | `NOT NULL`, Default: `'v1.0'` | Label versi dokumen (misal: `'v1.0'`, `'v2.0-revisi'`) |
| `judul_dokumen` | `VARCHAR(255)` | `NOT NULL` | Judul berkas formal (misal: `Dokumen_Tender_IKPP_v2.0.docx`) |
| `file_docx_path` | `VARCHAR(500)` | Nullable | Path relatif file Word di storage `media/generated_docs/` |
| `skor_kepatuhan_stk` | `SMALLINT` | `NOT NULL`, Default: `100` | Skor kesesuaian terhadap 86 aturan STK (rentang 0 - 100) |
| `is_active` | `BOOLEAN` | `NOT NULL`, Default: `TRUE` | Menandai versi draf yang sedang aktif di Live Canvas |
| `status_approval` | `VARCHAR(30)` | `NOT NULL`, Default: `'DRAFT'` | Pilihan: `'DRAFT'`, `'MENUNGGU_REVIEW'`, `'DISETUJUI'`, `'DITOLAK'` |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu pembuatan versi dokumen |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu modifikasi terakhir |

---

#### 3. Tabel: `procurement_document_clause`
* **Deskripsi:** Menyimpan rincian tiap pasal/klausul (40 Poin IKPP & Kontrak) secara granular sehingga dapat diedit satu per satu di Live Canvas editor.
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, Default: `gen_random_uuid()` | Pengenal unik pasal/klausul |
| `draft_id` | `UUID` | `FOREIGN KEY` -> `procurement_document_draft.id`, `ON DELETE CASCADE` | Relasi ke draf dokumen induk |
| `nomor_urut` | `INTEGER` | `NOT NULL` | Urutan tampilan bab/pasal (1 s.d. 40+) |
| `kode_pasal` | `VARCHAR(50)` | `NOT NULL` | Kode referensi pasal (misal: `'IKPP-01'`, `'KONTRAK-PASAL-14'`) |
| `judul_pasal` | `VARCHAR(255)` | `NOT NULL` | Judul klausul (misal: `Masa Pemeliharaan & Garansi`) |
| `teks_original` | `TEXT` | `NOT NULL` | Teks acuan baku standar Pertamina |
| `teks_revisi_ai` | `TEXT` | `NOT NULL` | Teks hasil sintesis Copilot sesuai konteks proyek |
| `is_edited_manual` | `BOOLEAN` | `NOT NULL`, Default: `FALSE` | Menandai apakah klausul telah diedit manual oleh PPK di canvas |
| `status_verifikasi` | `VARCHAR(30)` | `NOT NULL`, Default: `'COMPLIANT'` | Status kesesuaian: `'COMPLIANT'`, `'WARNING'`, `'DEVIATED'` |
| `catatan_stk` | `TEXT` | Nullable | Rujukan pasal Pedoman A03-001 yang mendasari klausul ini |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu pembaruan teks klausul |

---

#### 4. Tabel: `procurement_uploaded_attachment`
* **Deskripsi:** Menyimpan data berkas acuan yang diunggah pengguna (Bill of Quantities Excel, RKS teknis PDF, Kerangka Acuan Kerja).
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, Default: `gen_random_uuid()` | Pengenal unik berkas unggahan |
| `project_id` | `UUID` | `FOREIGN KEY` -> `procurement_tender_project.id`, `ON DELETE CASCADE` | Relasi ke paket pengadaan |
| `tipe_berkas` | `VARCHAR(30)` | `NOT NULL` | Kategori: `'BOQ_EXCEL'`, `'RKS_PDF'`, `'TOR_KAK'`, `'GAMBAR_TEKNIK'` |
| `nama_file_asli` | `VARCHAR(255)` | `NOT NULL` | Nama asli berkas saat diunggah oleh pengguna |
| `file_path` | `VARCHAR(500)` | `NOT NULL` | Lokasi fisik berkas di storage `media/uploads/` |
| `ukuran_bytes` | `BIGINT` | `NOT NULL` | Ukuran berkas dalam byte |
| `hash_md5` | `VARCHAR(32)` | `INDEX` | Hash checksum untuk mencegah duplikasi berkas identik |
| `hasil_ekstraksi_json` | `JSONB` | Nullable, Default: `{}` | Hasil pembacaan teks / tabel oleh parser `summarizer.py` |
| `uploaded_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu berkas selesai diunggah |

---

#### 5. Tabel: `procurement_chat_session`
* **Deskripsi:** Mewadahi satu sesi interaksi tanya jawab antara pengguna dengan Copilot AI untuk suatu proyek pengadaan.
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, Default: `gen_random_uuid()` | Pengenal unik sesi chat |
| `project_id` | `UUID` | `FOREIGN KEY` -> `procurement_tender_project.id`, `ON DELETE CASCADE` | Relasi ke proyek pengadaan terkait |
| `judul_sesi` | `VARCHAR(150)` | `NOT NULL`, Default: `'Penyusunan Dokumen Tender'` | Judul topik sesi obrolan |
| `is_active` | `BOOLEAN` | `NOT NULL`, Default: `TRUE` | Menandai sesi percakapan yang sedang terbuka di UI |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu inisiasi sesi percakapan |

---

#### 6. Tabel: `procurement_chat_message`
* **Deskripsi:** Menyimpan setiap baris percakapan chat, log *tool-calls* (seperti `check_stk_compliance`, `update_clause`), dan metadata artifact yang ditampilkan pada bubble chat.
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, Default: `gen_random_uuid()` | Pengenal unik pesan |
| `session_id` | `UUID` | `FOREIGN KEY` -> `procurement_chat_session.id`, `ON DELETE CASCADE` | Relasi ke sesi obrolan induk |
| `role` | `VARCHAR(20)` | `NOT NULL` | Pengirim: `'user'`, `'assistant'`, `'system'` |
| `content` | `TEXT` | `NOT NULL` | Teks isi pesan |
| `tool_calls` | `JSONB` | Nullable | Parameter panggilan alat bantu AI (klausul yang diubah, query RAG) |
| `artifacts_payload` | `JSONB` | Nullable | Data card interaktif yang dirender di bubble chat |
| `prompt_tokens` | `INTEGER` | Nullable, Default: `0` | Jumlah token prompt input (untuk monitoring biaya LLM) |
| `completion_tokens` | `INTEGER` | Nullable, Default: `0` | Jumlah token respons (untuk monitoring throughput) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu pesan dikirimkan |

---

#### 7. Tabel: `procurement_stk_rule`
* **Deskripsi:** Katalog referensi aturan baku **Pedoman Pengadaan No. A03-001/PNG200000/2024-S9** (86 aturan STK) yang tersinkronisasi dengan Qdrant Vector Store.
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY`, Auto-increment | ID aturan |
| `kode_pedoman` | `VARCHAR(50)` | `NOT NULL`, Default: `'A03-001/2024-S9'` | Nomor surat pedoman pengadaan acuan |
| `nomor_aturan` | `VARCHAR(20)` | `UNIQUE`, `INDEX` | Kode nomor aturan (misal: `'STK-01'`, `'STK-44'`) |
| `kategori_stk` | `VARCHAR(50)` | `NOT NULL` | Kategori (misal: `'Jaminan'`, `'K3L CSMS'`, `'Denda'`, `'TKDN'`) |
| `judul_aturan` | `VARCHAR(255)` | `NOT NULL` | Judul singkat aturan |
| `deskripsi_aturan` | `TEXT` | `NOT NULL` | Penjelasan ketentuan hukum & operasional pengadaan |
| `klausul_baku_docx` | `TEXT` | Nullable | Bunyi kalimat resmi yang wajib masuk ke dalam template Word |
| `level_kepatuhan` | `VARCHAR(20)` | `NOT NULL`, Default: `'MANDATORY'` | Sifat aturan: `'MANDATORY'` (Wajib mutlak) atau `'OPTIONAL'` |
| `qdrant_point_id` | `VARCHAR(64)` | Nullable, `INDEX` | ID vektor embeddings terkait di koleksi Qdrant |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu pembaruan aturan |

---

#### 8. Tabel: `procurement_audit_trail`
* **Deskripsi:** Mencatat riwayat audit resmi (*compliance audit log*) dari seluruh tindakan penting pengguna dan perubahan pasal dokumen sesuai standar kepatuhan BUMN.
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `BIGINT` | `PRIMARY KEY`, Auto-increment | ID entri log |
| `project_id` | `UUID` | `FOREIGN KEY` -> `procurement_tender_project.id`, `ON DELETE CASCADE` | Relasi ke paket pengadaan |
| `user_id` | `INTEGER` | `FOREIGN KEY` -> `auth_user.id`, Nullable | Pengguna yang melakukan tindakan |
| `tipe_aksi` | `VARCHAR(50)` | `NOT NULL`, `INDEX` | Jenis aksi: `'UPLOAD_BOQ'`, `'GENERATE_DOCX'`, `'REVISI_PASAL'`, `'EXPORT_DOKUMEN'` |
| `modul_terkait` | `VARCHAR(50)` | `NOT NULL` | Modul yang disentuh: `'CANVAS'`, `'CHAT'`, `'EXPORTER'`, `'AUTH'` |
| `rincian_perubahan` | `TEXT` | `NOT NULL` | Detail perubahan (misal: "Ubah Masa Pemeliharaan dari 90 menjadi 180 hari") |
| `ip_address` | `VARCHAR(45)` | Nullable | Alamat IP jaringan pengguna |
| `recorded_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu pencatatan jejak audit |

---

### 4.3 Aturan Integritas Data & Indeks (*Database Indexing*)
1. **Foreign Key Cascading**:
   * Jika proyek tender (`procurement_tender_project`) dihapus, seluruh draf dokumen, klausul, riwayat chat, dan catatan audit otomatis terhapus bersih (`ON DELETE CASCADE`).
2. **Kueri Berkecepatan Tinggi (Indexing)**:
   * Kolom pencarian cepat seperti `no_tender`, `hash_md5`, `qdrant_point_id`, dan `tipe_aksi` dilengkapi indeks database B-Tree.
3. **Format Field JSONB**:
   * Digunakan untuk kolom `metadata_ekstraksi`, `tool_calls`, dan `hasil_ekstraksi_json` pada PostgreSQL agar dapat dikueri langsung menggunakan operator JSON bawaan (`->`, `->>`) dengan latensi < 1 ms.

---

## 5. Tahapan Implementasi (Rencana Kerja 5 Fase)

### Fase 1: Penataan Struktur Decoupled & Setup FastAPI
- [ ] Buat struktur folder decoupled: `frontend/` (memuat `agenticv3`) dan `backend/` (FastAPI application).
- [ ] Siapkan file `requirements.txt` untuk FastAPI (`fastapi`, `uvicorn[standard]`, `pydantic-settings`, `sqlalchemy[asyncio]`, `asyncpg`, `python-docx`, `qdrant-client`).
- [ ] Buat `backend/app/main.py` dengan CORS middleware aktif dan OpenAPI Swagger di `/docs`.
- [ ] Buat file konfigurasi `deploy/nginx/default.conf` untuk menghubungkan frontend statis dan proxy `/api/`.

### Fase 2: Implementasi Database SQLAlchemy 2.0 & Alembic
- [ ] Definisikan 8 model tabel deklaratif di `backend/app/models/`.
- [ ] Konfigurasi koneksi async database di `backend/app/database.py`.
- [ ] Inisialisasi Alembic (`alembic init -t async alembic`) dan buat migrasi awal (`alembic revision --autogenerate -m "initial_procurement_tables"`).
- [ ] Jalankan migrasi ke PostgreSQL lokal / Docker (`alembic upgrade head`).

### Fase 3: Integrasi Modul AI RAG ke Endpoint FastAPI
- [ ] Pindahkan logic dari `Agentic_Rag_Pertamina_camp` (`RAG/`, `tender/`, `contract/`) ke `backend/app/services/`.
- [ ] Implementasikan router endpoint asinkron di `backend/app/api/`:
  - `POST /api/extract-tender-metadata` (Ekstraksi BoQ Excel & RKS PDF acuan).
  - `POST /api/generate-tender` (Export 40 Poin IKPP .docx).
  - `POST /api/generate-rks` (Export RKS .docx).
  - `POST /api/generate-kontrak` (Export Kontrak .docx).
  - `POST /api/generate-amendemen` (Export Amendemen .docx).
  - `POST /api/kb/ingest` & `GET /api/kb/list` (Koneksi Qdrant Vector Store).
- [ ] Verifikasi format unduhan `.docx` dengan template styling resmi Pertamina (`doc_config.json`).

### Fase 4: Konfigurasi Celery Worker & Streaming Token AI (SSE)
- [ ] Hubungkan Celery dengan Redis broker untuk pemrosesan file `.docx` masif di latar belakang.
- [ ] Implementasikan endpoint `GET /api/chat/stream` menggunakan `EventSourceResponse` (Server-Sent Events) untuk streaming token jawaban AI per kata.
- [ ] Sinkronkan status task worker dengan indikator progres frontend (*Progress Drawer* & *Live Sync Badge*).

### Fase 5: Dockerization, Nginx Gateway, & Pipeline CI/CD
- [ ] Susun `Dockerfile` multi-stage untuk FastAPI & Celery.
- [ ] Buat `docker-compose.yml` yang menghubungkan service: `nginx`, `web`, `celery_worker`, `redis`, `qdrant`, dan `db`.
- [ ] Siapkan workflow `.github/workflows/deploy.yml` dengan automated tests (Pytest).
- [ ] Uji coba skenario *end-to-end* (Upload BoQ -> Ekstraksi AI -> Edit Canvas -> Generate Dokumen -> Unduh .docx).

---

## 6. Matrix Mitigasi Risiko & Cadangan Solusi

| Potensi Kendala | Risiko | Solusi Mitigasi |
| :--- | :--- | :--- |
| **Ekstraksi BoQ Excel memakan waktu lama** | Browser mengalami timeout | Celery worker menangani parsing di background dan mengirimkan sinyal progres ke frontend. |
| **Koneksi LLM terputus di tengah jalan** | Dokumen gagal terbentuk utuh | Logika *retry mechanism* (maksimal 3 kali) pada `services` sebelum melaporkan error ke chat window. |
| **CORS Blocking pada Pengujian Lokal** | Request frontend ditolak browser | FastAPI mengaktifkan `CORSMiddleware` dengan whitelist origin yang fleksibel saat `DEBUG=True`. |
| **Migrasi Skema Database di Produksi** | Kegagalan update tabel | Menggunakan Alembic versioning dengan verifikasi *dry-run* (`alembic upgrade --sql`) sebelum eksekusi riil. |

---

## 7. Strategi CI/CD & Alur Penambahan Fitur Baru

### 7.1 Diagram Siklus CI/CD
```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer (Laptop Lokal)
    participant Git as GitHub Repository
    participant CI as GitHub Actions (CI Runner)
    participant Reg as Container Registry (GHCR / Docker Hub)
    participant Server as Server Deploy (Docker + Nginx)
    actor User as Pengguna (User Pertamina)

    Dev->>Git: 1. Push Fitur Baru (git push origin main)
    Git->>CI: 2. Trigger Workflow Otomatis
    Note over CI: Run Tests & Linter<br/>- Pytest API FastAPI<br/>- Tes Ekspor .DOCX<br/>- Build Docker Image Test
    CI->>Reg: 3. Jika Tes Lolos: Push Image Baru (:latest)
    CI->>Server: 4. Kirim Sinyal Update (via SSH / Webhook)
    Note over Server: Server Mengeksekusi:<br/>- docker compose pull<br/>- alembic upgrade head<br/>- docker compose up -d (Rolling Update)
    Server-->>User: 5. Fitur Baru Langsung Tayang (Zero Downtime!)
```

### 7.2 Siklus Penambahan Fitur Baru (Developer Workflow)
1. **Lokal (Branching & Development)**:
   - Developer membuat branch fitur baru: `git checkout -b feature/nama-fitur`.
   - Mengubah model di `backend/app/models/`, menjalankan `alembic revision --autogenerate -m "add_new_feature"`.
   - Menulis/memperbarui komponen UI di `frontend/`.
   - Menjalankan unit test lokal: `pytest backend/tests/`.
2. **Pull Request & Continuous Integration (CI)**:
   - Developer mem-push branch ke GitHub dan membuka Pull Request (PR) ke `main`.
   - GitHub Actions otomatis menjalankan:
     - **Linting & Code Style**: Flake8 / Ruff.
     - **Pytest**: Memverifikasi validasi Pydantic, route FastAPI, dan generator `.docx`.
     - **Docker Build Check**: Memastikan image Docker berhasil di-build tanpa missing dependency.
   - PR hanya dapat di-merge jika seluruh pengujian berstatus **HIJAU (PASS)**.
3. **Continuous Deployment (CD) ke Server**:
   - Setelah branch di-merge ke `main`, GitHub Actions mentrigger proses deployment:
     - Mem-build image final dengan tag versi rilis (`v1.2.0` dan `latest`).
     - Melakukan koneksi SSH aman ke server staging/production.
     - Menjalankan rolling update:
       ```bash
       docker compose pull web celery_worker
       docker compose run --rm web alembic upgrade head
       docker compose up -d --no-deps web celery_worker
       ```
     - Nginx secara mulus meneruskan request baru ke container versi anyar (*zero-downtime*).

### 7.3 Manajemen Database & Ketahanan Data (Zero Data Loss)
- **Persistensi Data**: Database PostgreSQL dan folder berkas upload (`media/`) disimpan pada **Docker Volume** di disk fisik server, terisolasi dari container aplikasi. Container dapat di-rebuild berulang kali tanpa risiko kehilangan data pengadaan atau riwayat chat.
- **Migrasi Non-Destruktif**: Migrasi schema via Alembic menerapkan penambahan kolom/tabel secara inkremental tanpa menghapus data yang sudah ada.

### 7.4 Spesifikasi Konfigurasi GitHub Actions (`.github/workflows/deploy.yml`)
```yaml
name: CI/CD Pertamina Copilot (FastAPI)

on:
  push:
    branches: [ "main" ]

jobs:
  test:
    name: Run Automated Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install Dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install pytest httpx
      - name: Run Pytest Suites
        run: |
          pytest backend/tests/

  deploy:
    name: Deploy to Server
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            cd /opt/pertamina-procurement
            git pull origin main
            docker compose build
            docker compose run --rm web alembic upgrade head
            docker compose up -d
```

---

## 8. Spesifikasi Infrastruktur Kontainerisasi (Docker & Docker Compose)

### 8.1 Arsitektur Multi-Kontainer (6 Layanan Terisolasi)

| Layanan (Service) | Base Image | Port Eksternal | Port Internal | Peran & Tanggung Jawab |
| :--- | :--- | :--- | :--- | :--- |
| **`nginx`** | `nginx:1.25-alpine` | `80`, `443` | `80`, `443` | Reverse proxy, static server `frontend/`, buffer upload 100MB, timeout AI 300s. |
| **`web`** | Custom Python 3.11 | - | `8000` | FastAPI ASGI application (`uvicorn`), melayani OpenAPI Swagger & REST API. |
| **`celery_worker`**| Custom Python 3.11 | - | - | Background worker untuk generasi dokumen Word (`.docx`) & ekstraksi BoQ berat. |
| **`redis`** | `redis:7-alpine` | - | `6379` | Message broker untuk antrean tugas Celery & caching session. |
| **`qdrant`** | `qdrant/qdrant:latest`| - | `6333` | Vector Database penyimpanan embeddings 86 Aturan Pedoman Pengadaan STK. |
| **`db`** | `postgres:16-alpine` | - | `5432` | Pangkalan data relasional (PostgreSQL) untuk menyimpan proyek, klausul, dan audit trail. |

---

### 8.2 Spesifikasi `Dockerfile` (Multi-Stage Production Build)

```dockerfile
# Stage 1: Build & Compile Dependencies
FROM python:3.11-slim as builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Final Minimal Runtime Image
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Akun pengguna non-root demi standar keamanan BUMN
RUN groupadd -r pertamina && useradd -r -g pertamina pertamina

COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

COPY backend/ .
RUN chown -R pertamina:pertamina /app

USER pertamina
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### 8.3 Blueprint `docker-compose.yml` (Opsi A: Decoupled Siap Deploy)

```yaml
version: '3.8'

services:
  # 1. Pangkalan Data Relasional
  db:
    image: postgres:16-alpine
    container_name: pertamina_postgres
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-pertamina_db}
      POSTGRES_USER: ${POSTGRES_USER:-pertamina_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-pertamina_pass123}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pertamina_user -d pertamina_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - pertamina_internal_net

  # 2. Redis Message Broker & Cache
  redis:
    image: redis:7-alpine
    container_name: pertamina_redis
    restart: always
    volumes:
      - redis_data:/data
    networks:
      - pertamina_internal_net

  # 3. Qdrant Vector Database (STK 86 Rules)
  qdrant:
    image: qdrant/qdrant:latest
    container_name: pertamina_qdrant
    restart: always
    volumes:
      - qdrant_storage:/qdrant/storage
    networks:
      - pertamina_internal_net

  # 4. FastAPI ASGI Web Application
  web:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: pertamina_fastapi
    restart: always
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    volumes:
      - media_volume:/app/media
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
      qdrant:
        condition: service_started
    networks:
      - pertamina_internal_net

  # 5. Celery Asynchronous Worker (AI & Docx Generation)
  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: pertamina_celery
    restart: always
    command: celery -A app.services.tasks worker -l info --concurrency=4
    volumes:
      - media_volume:/app/media
    env_file:
      - .env
    depends_on:
      redis:
        condition: service_started
      db:
        condition: service_healthy
    networks:
      - pertamina_internal_net

  # 6. Nginx Edge Gateway & Frontend Server
  nginx:
    image: nginx:1.25-alpine
    container_name: pertamina_nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - ./frontend:/usr/share/nginx/html:ro
      - media_volume:/usr/share/nginx/html/media:ro
    depends_on:
      - web
    networks:
      - pertamina_internal_net

# Persistensi Data Fisik Server (Zero Data Loss)
volumes:
  pgdata:
    driver: local
  redis_data:
    driver: local
  qdrant_storage:
    driver: local
  media_volume:
    driver: local

networks:
  pertamina_internal_net:
    driver: bridge
```

---

### 8.4 Konfigurasi `deploy/nginx/default.conf`

```nginx
server {
    listen 80;
    server_name localhost;
    client_max_body_size 100M;

    # 1. Sajikan Frontend Statis agenticv3 secara langsung
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
        
        # Cache aset statis
        location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 7d;
            add_header Cache-Control "public, no-transform";
        }
    }

    # 2. Teruskan API Call ke Backend FastAPI
    location /api/ {
        proxy_pass http://web:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Pengaturan khusus AI Streaming & Dokumen Berat
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
        proxy_cache off;
    }

    # 3. Akses Swagger Documentation
    location /docs {
        proxy_pass http://web:8000/docs;
        proxy_set_header Host $host;
    }
    location /openapi.json {
        proxy_pass http://web:8000/openapi.json;
        proxy_set_header Host $host;
    }
}
```

---

### 8.5 Perintah Operasional Docker (One-Command Startup)

```bash
# 1. Menjalankan Seluruh Ekosistem Kontainer
docker compose up -d --build

# 2. Menjalankan Migrasi Database di Dalam Kontainer
docker compose exec web alembic upgrade head

# 3. Memeriksa Log Status Kontainer
docker compose logs -f web celery_worker
```

---

## 9. Tata Kelola Keamanan Data & Pemeliharaan Sistem (Security Governance & Automated Housekeeping)

### 9.1 Manajemen Rahasia & Kebijakan Nol Kebocoran Kredensial (*Secrets Management*)

1. **Penegakan Aturan `.gitignore`**:
   * File `.env` yang berisi *kunci API produksi*, *password database*, dan *kredensial Qdrant* **dilarang keras** di-commit ke repositori Git.
   * File `.gitignore` wajib mencantumkan:
     ```text
     .env
     .env.local
     *.log
     media/
     output/
     __pycache__/
     .pytest_cache/
     ```
2. **Penyediaan Berkas Acuan `.env.example`**:
   * Pengembang baru menyalin dari `.env.example`:
     ```env
     DEBUG=False
     DATABASE_URL=postgresql+asyncpg://pertamina_user:secure_password@db:5432/pertamina_db
     QDRANT_URL=http://qdrant:6333
     OPENROUTER_API_KEY=sk-or-v1-placeholder
     CELERY_BROKER_URL=redis://redis:6379/0
     CELERY_RESULT_BACKEND=redis://redis:6379/0
     ```
3. **Injeksi Kredensial CI/CD via GitHub Secrets**:
   * Seluruh kredensial akses server (`SERVER_HOST`, `SERVER_USER`, `SERVER_SSH_KEY`) diinjeksikan secara terenkripsi saat pipeline berjalan tanpa pernah terekspos di log pengujian.

---

### 9.2 Otomasi Pembersihan Berkas Sementara (*Automated Housekeeping Task*)

Aktivitas penyusunan dokumen tender menghasilkan berkas *scratch*, pecahan halaman PDF, dan draf revisi di folder `output/`. Jika dibiarkan, media penyimpanan server akan penuh (*disk saturation*).

1. **Jadwal Pembersihan Berkala via Celery Beat**:
   * Menjadwalkan tugas otomatis (*cron job*) yang berjalan setiap hari pukul **02.00 WIB**:
     ```python
     # backend/app/services/tasks.py
     from celery import shared_task
     import os, time

     @shared_task
     def cleanup_expired_temporary_files():
         """
         Menghapus berkas sementara di folder output/ yang berusia > 7 hari.
         Mencegah disk kepenuhan dan menjamin kepatuhan retensi data.
         """
         temp_dir = 'output/'
         retention_seconds = 7 * 24 * 3600  # 7 Hari
         now = time.time()
         deleted_count = 0

         if os.path.exists(temp_dir):
             for filename in os.listdir(temp_dir):
                 filepath = os.path.join(temp_dir, filename)
                 if os.path.isfile(filepath):
                     file_age = now - os.path.getmtime(filepath)
                     if file_age > retention_seconds:
                         os.remove(filepath)
                         deleted_count += 1
         return f"Housekeeping selesai: {deleted_count} file kedaluwarsa dibersihkan."
     ```
2. **Kepatuhan Privasi Data Pengadaan**:
   * Berkas sementara yang dihapus otomatis memastikan dokumen acuan vendor tidak tertimbun selamanya di disk server tanpa pengawasan.
