# Draft Perencanaan Proyek ITeC: Pertamina Procurement AI Copilot & Live Canvas
**Arsitektur Modern Decoupled: Frontend React (Vite JavaScript) + Tailwind CSS v3 + Backend FastAPI (ASGI) + SQLAlchemy 2.0 + Nginx Reverse Proxy + CI/CD Docker (Celery + Redis opsional)**

> **Status dokumen:** Masterplan utama (*single source of truth*). Dokumen `draft_perencanaan_frontend.md` hanya berisi spesifikasi UI/UX & catatan porting dari prototipe `frontend_vanilla/`; bila terjadi perbedaan, dokumen ini yang berlaku.

---

## 1. Ringkasan Eksekutif & Tujuan Proyek

Proyek ini bertujuan mengintegrasikan antarmuka frontend modern berbasis **React + Vite (JavaScript)** dan styling **Tailwind CSS v3** dengan arsitektur komponen modular di dalam folder **`komponen/`**, terhubung ke backend **FastAPI (Python 3.12)** yang berkinerja tinggi (*high-concurrency async*).

Sistem ini mengadopsi **Opsi A (Nginx Reverse Proxy Decoupled)**, di mana:
1. **Frontend React (Vite JavaScript) & Tailwind CSS v3**: Seluruh elemen antarmuka (*Claude-style Live Canvas*, *Progress Drawer*, *Vertical Docked Tab*, *Chat & In-Chat Artifact Cards*, *Tool-calls Accordion*, dan *DocPicker Modal*) dibangun menggunakan utility-first classes dari **Tailwind CSS v3** (`tailwindcss@^3.4.x`, `postcss`, `autoprefixer`) yang dikonfigurasi dengan *design tokens* resmi PT Pertamina (Navy `#002D62`, Red `#ED1C24`, Green `#009A44`, Blue `#0072BC`, dan palet netral slate). Seluruh kode dipecah menjadi komponen-komponen independen dan dapat digunakan kembali (*reusable components*) di dalam direktori `frontend/src/komponen/`. Pada mode produksi, Vite mengompilasi bundel statis ke folder `dist/` yang dikemas ke dalam image Nginx dan disajikan langsung sebagai berkas statis.
2. **Backend FastAPI**: Beroperasi sebagai layanan ASGI mandiri di port internal 8000 untuk menangani autentikasi pengguna, komputasi AI, validasi Pydantic v2, *token streaming* (Server-Sent Events), koneksi Qdrant Vector DB, serta pembentukan dokumen resmi PT Pertamina Patra Niaga (IKPP Versi 2.0 40 Poin, RKS, Kontrak Definitif, dan Amendemen) yang patuh terhadap Pedoman No. A03-001/PNG200000/2024-S9.
3. **SQLAlchemy 2.0 (Async) + Alembic**: Menangani persistensi data relasional ke PostgreSQL untuk 9 tabel (1 tabel pengguna + 8 tabel pengadaan), riwayat chat, dan audit kepatuhan.
4. **Autentikasi & Otorisasi Berbasis Peran (RBAC)**: Setiap aksi (membuat paket, merevisi pasal, menyetujui dokumen, mengunduh) terikat pada akun pengguna dan perannya, sehingga jejak audit dapat dipertanggungjawabkan (lihat Bagian 4.4 & 9.3).

### 1.0 Revisi Arah Produk (19 Oktober 2026)
Keputusan pemilik proyek web:
1. **Produk akhir adalah generator dokumen berbasis chatbot** yang memberi arahan dan *feedback* kepada pengguna yang belum berpengalaman. Copilot menanyakan informasi satu per satu, menyusun draf, lalu menerima permintaan revisi sebelum ekspor `.docx`.
2. **Tidak ada lagi unggah BoQ dari browser.** AI membaca knowledge base yang di-ingest dari **folder drive eksternal** (Google Drive / OneDrive). Folder disinkronkan ke server oleh klien desktop resmi (atau di-mount) dan diarahkan lewat `DATASET_DIR`. Subfolder `rks_kb/`, `contract_kb/`, dan `amendment_kb/` di-ingest ke Qdrant; folder lain menjadi berkas acuan (mis. BoQ per paket) yang bisa dipilih di chat.
3. **Fokus saat ini hanya pembuatan draf.** Kolom & peran persetujuan (`status_approval`, `APPROVER`) tetap ada di skema, tetapi alur persetujuan belum dibangun.
4. Server masih berupa **laptop** (demo lokal); domain & sertifikat TLS belum ada, tetapi tempatnya disiapkan. Commit dilakukan lokal; push dilakukan sendiri oleh pemilik proyek.
5. Seluruh pertanyaan seputar AI dikumpulkan di `pertanyaan penanggung jawab ai.md`. Tim web tidak mengubah logika AI dan bekerja dengan asumsi yang ditandai **[Asumsi web]**.

### 1.1 Prinsip Pengembangan Bertahap
1. **Satu alur nyata lebih dulu**: Chat RKS → Agent menanyakan informasi (BoQ dipilih dari drive) → Draf tampil di Canvas → Revisi/Setuju → Unduh `.docx` harus berjalan *end-to-end* sebelum fitur lain ditambahkan.
2. **Infrastruktur menyusul kebutuhan**: Celery + Redis hanya diaktifkan bila proses generate dokumen terbukti melampaui batas timeout HTTP (lihat Fase 4). Hingga saat itu, cukup memakai `run_in_threadpool` / `BackgroundTasks` FastAPI seperti pada `api.py` saat ini.

---

## 2. Arsitektur Sistem Terpadu (Opsi A: Decoupled via Nginx)

```mermaid
graph TD
    Client["Browser Pengguna (React Vite UI)"] -->|HTTPS 443| Nginx["Nginx Edge Gateway & Reverse Proxy (TLS)"]
    
    subgraph "Ingress & Presentation Layer"
        Nginx -->|GET / & Static Assets| ViteDist["Vite Production Build (dikemas di image Nginx)"]
        Nginx -->|/api/... Timeout 300s, SSE unbuffered| FastAPI["FastAPI ASGI Server (Uvicorn)"]
    end

    subgraph "Application & Service Layer (FastAPI)"
        FastAPI --> Auth["Auth: JWT + RBAC (FastAPI Depends)"]
        FastAPI --> Routers["API Route Controllers (Pydantic V2)"]
        FastAPI --> ORM["SQLAlchemy 2.0 Async ORM"]
        FastAPI --> TaskDispatch["Background Dispatcher (Threadpool → Celery bila perlu)"]
    end

    subgraph "Worker & AI Engine Layer"
        TaskDispatch -.->|opsional| Redis["Redis Message Broker"]
        Redis -.-> Celery["Celery Worker + Beat"]
        TaskDispatch --> RAG["RAG Engine & Summarizer (pypdf/openpyxl)"]
        TaskDispatch --> DocxGen["Docx Generator (python-docx)"]
        RAG --> Qdrant["Qdrant Vector DB (86 STK Rules)"]
        RAG --> LLM["LLM Engine (OpenRouter Qwen / Internal)"]
    end

    subgraph "Storage Layer"
        DocxGen --> MediaDisk["Media Storage (BoQ Uploads & Generated .DOCX)"]
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
│       ├── ci.yml                         # Lint + build React, Ruff + Pytest FastAPI (jalan di setiap PR & push)
│       └── deploy.yml                     # Build & push image ke GHCR, lalu deploy via SSH (hanya main)
│
├── deploy/                                # Konfigurasi Server
│   └── nginx/
│       └── default.conf                   # Reverse proxy, static server dist/, TLS, timeout 300s
│
├── frontend/                              # [FRONTEND REACT + VITE JAVASCRIPT + TAILWIND CSS V3]
│   ├── Dockerfile                         # Multi-stage: Node build dist/ → image Nginx
│   ├── index.html                         # Entry point HTML Vite (lang="id", load font Plus Jakarta Sans & JetBrains Mono)
│   ├── package.json                       # Dependensi React, Vite, Tailwind CSS v3, PostCSS, Lucide-React, Axios
│   ├── vite.config.js                     # Konfigurasi build & proxy dev /api/ -> :8000
│   ├── tailwind.config.js                 # Konfigurasi Tailwind CSS v3 (Color tokens resmi Pertamina, dark mode, font)
│   ├── postcss.config.js                  # Konfigurasi PostCSS untuk Tailwind & Autoprefixer
│   ├── public/                            # Aset publik statis (favicon, logo Pertamina)
│   └── src/
│       ├── main.jsx                       # React DOM entry point
│       ├── App.jsx                        # Root Layout (Split-screen Chat & Live Canvas dengan Tailwind)
│       ├── index.css                      # Entry Tailwind directives (@tailwind base/components/utilities) & token Pertamina
│       │
│       ├── komponen/                      # [FOLDER KOMPONEN MODULAR BERBASIS TAILWIND CSS]
│       │   ├── Auth/
│       │   │   ├── LoginPage.jsx          # Form login (username/email + password)
│       │   │   └── ProtectedRoute.jsx     # Guard halaman berdasarkan sesi & peran
│       │   │
│       │   ├── Navbar/
│       │   │   ├── Navbar.jsx             # Topbar, Logo Pertamina, Ganti Dokumen, Step & Unduh
│       │   │   ├── HamburgerMenu.jsx      # Dropdown menu pengaturan & riwayat pengadaan
│       │   │   └── Navbar.css             # (Opsional) custom keyframes bila dibutuhkan
│       │   │
│       │   ├── Chat/
│       │   │   ├── ChatPanel.jsx          # Panel chat kiri (auto w-full saat canvas off, flex-1 saat active)
│       │   │   ├── ChatBubble.jsx         # Pesan percakapan user & balasan AI (Tailwind bubble styled)
│       │   │   ├── ToolCallCard.jsx       # Card interaktif eksekusi tool AI (klausul STK)
│       │   │   ├── ArtifactCard.jsx       # Card embed preview dokumen di dalam chat
│       │   │   ├── QuickActionChips.jsx   # Tombol saran prompt cepat (Jaminan, CSMS, HPS)
│       │   │   ├── ChatInput.jsx          # Textarea input, tombol lampiran & tombol kirim
│       │   │   └── Chat.css
│       │   │
│       │   ├── Canvas/
│       │   │   ├── CanvasReview.jsx       # Panel review dokumen kanan (Live Canvas)
│       │   │   ├── CanvasToolbar.jsx      # Tabs (Dokumen, Matriks CSMS, STK 86) & Icon Tools
│       │   │   ├── DocumentEditor.jsx     # Editor interaktif klausul / markdown dokumen
│       │   │   ├── MatrixView.jsx         # Matriks HPS/K&R (tender) & ringkasan nilai (RKS/kontrak/amendemen)
│       │   │   ├── KnowledgeBaseView.jsx  # Daftar dokumen per collection Qdrant
│       │   │   ├── StkComplianceView.jsx  # Checklist kepatuhan 86 aturan STK Pertamina
│       │   │   └── Canvas.css
│       │   │
│       │   ├── Common/
│       │   │   ├── VerticalRestoreTab.jsx # Tab vertikal samping kanan pembuka kembali canvas
│       │   │   ├── ProgressDrawer.jsx     # Drawer slide-out 'Step 1 of 4' & resource acuan
│       │   │   ├── DocPickerModal.jsx     # Modal popup pemilihan 4 paket dokumen tender
│       │   │   ├── ConfirmDialog.jsx      # Pengganti window.confirm() (reset sesi, hapus dokumen)
│       │   │   ├── Toast.jsx              # Notifikasi pop-up feedback status / error
│       │   │   └── Common.css
│       │   │
│       │   └── index.js                   # Barrel export seluruh komponen
│       │
│       ├── services/                      # Komunikasi API & State
│       │   ├── api.js                     # Axios/Fetch client ke endpoint FastAPI (base URL relatif "/api", sisip token)
│       │   ├── useAuthStore.js            # State sesi login (token, profil, peran)
│       │   └── useAppStore.js             # State management global (Zustand / Context)
│       │
│       └── assets/                        # Logo SVG, icon, dan styling tambahan
│
├── backend/                               # [BACKEND FASTAPI ASGI]
│   ├── Dockerfile                         # Image Python (dipakai bersama oleh web & celery_worker)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                        # Entrypoint FastAPI (CORS whitelist, routers, lifecycle)
│   │   ├── config.py                      # Pydantic BaseSettings (.env, Qdrant URL, DB URL, JWT secret, MEDIA_ROOT)
│   │   ├── database.py                    # SQLAlchemy Async Engine & session maker
│   │   │
│   │   ├── core/
│   │   │   ├── security.py                # Hash password (argon2), buat & verifikasi JWT
│   │   │   ├── deps.py                    # Dependency get_current_user & require_role(...)
│   │   │   ├── rate_limit.py              # Pembatas percobaan login gagal
│   │   │   └── audit.py                   # Helper pencatatan AuditTrail (kode web, sengaja di luar services/ AI)
│   │   │
│   │   ├── models/                        # SQLAlchemy 2.0 ORM Models (9 Tabel)
│   │   │   ├── __init__.py
│   │   │   ├── user.py                    # AppUser
│   │   │   ├── tender.py                  # TenderProject, DocumentDraft, DocumentClause
│   │   │   ├── attachment.py              # UploadedAttachment
│   │   │   ├── chat.py                    # ChatSession, ChatMessage
│   │   │   └── compliance.py              # StkRule, AuditTrail
│   │   │
│   │   ├── schemas/                       # Pydantic V2 Schemas (Request/Response validation)
│   │   │   ├── auth_schema.py             # Login request, token response, profil user
│   │   │   ├── tender_schema.py           # Validasi nilai HPS, tanggal, risiko CSMS
│   │   │   ├── chat_schema.py             # Format pesan & tool-calls
│   │   │   └── kb_schema.py               # Metadata ingest berkas STK
│   │   │
│   │   ├── api/                           # Route Handlers (/api/...)
│   │   │   ├── __init__.py
│   │   │   ├── auth_routes.py             # /api/auth/login, /api/auth/me, /api/auth/refresh
│   │   │   ├── tender_routes.py           # /api/extract-tender-metadata, /api/generate-tender, dll
│   │   │   ├── chat_routes.py             # /api/chat (Streaming SSE token per kata)
│   │   │   ├── kb_routes.py               # /api/kb/ingest, /api/kb/list
│   │   │   ├── uploads.py                 # Validasi berkas unggahan (ekstensi, ukuran, nama)
│   │   │   └── health_routes.py           # /api/health (status konfigurasi LLM & Qdrant)
│   │   │
│   │   └── services/                      # AI & RAG Pipeline (Porting dari Agentic_Rag_Pertamina_camp)
│   │       ├── rag/                       # summarizer (ekstraksi PDF/Excel), vector_store (Qdrant), tools (generator RKS)
│   │       ├── tender/                    # Generator & exporter Dokumen Tender 40 Poin IKPP
│   │       ├── contract/                  # Generator & exporter Kontrak Definitif & Amendemen
│   │       └── tasks.py                   # Celery tasks (opsional: export docx berat & housekeeping)
│   │
│   ├── alembic/                           # Database Migration Tool (Alembic)
│   │   ├── env.py
│   │   └── versions/                      # Berkas riwayat migrasi tabel
│   ├── alembic.ini
│   ├── assets/                            # Logo & doc_config.json untuk exporter .docx
│   ├── pyproject.toml + uv.lock           # Dependensi dikelola dengan uv (Python 3.12)
│   └── tests/                             # Pytest automated test suites
│       ├── test_auth.py
│       ├── test_api_tender.py
│       └── test_generator.py
│
├── media/                                 # Shared Storage (Uploads & Generated .DOCX) — tidak di-commit
│   ├── uploads/
│   └── generated_docs/
│
├── output/                                # Temporary scratch / processing files — tidak di-commit
├── .env                                   # API Keys & DB Credentials — tidak di-commit
├── .env.example
└── docker-compose.yml                     # Orkestrasi 5 kontainer inti (+2 opsional: redis, celery)
```

### 3.1 Konfigurasi & Design Tokens Tailwind CSS v3 (Resmi Pertamina)

Untuk menjamin konsistensi visual korporat PT Pertamina Patra Niaga dan kecepatan render antarmuka frontend, **Tailwind CSS v3** (`tailwindcss@^3.4.17`) digunakan sebagai styling engine utama. Konfigurasi resmi proyek ditetapkan sebagai berikut (sudah diterapkan di `frontend/tailwind.config.js`):

#### 1. Berkas `frontend/tailwind.config.js`
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        pertamina: {
          navy: '#002D62',       // Warna primer korporat (Header, tombol utama)
          'navy-dark': '#001D42', // Background navbar & sidebar hover
          'navy-light': '#0B4080',
          red: '#ED1C24',        // Aksen merah Pertamina (Badge resiko tinggi, danger, alert)
          'red-light': '#FDE8E9',
          green: '#009A44',      // Aksen hijau Pertamina (Status success, tombol unduh)
          'green-light': '#E6F5EC',
          blue: '#0072BC',       // Aksen biru secondary (Active tabs, highlight link)
          'blue-light': '#E8F1F9',
          gray: {
            50: '#F8FAFC',
            100: '#F1F5F9',
            200: '#E2E8F0',
            300: '#CBD5E1',
            400: '#94A3B8',
            500: '#64748B',
            600: '#475569',
            700: '#334155',
            800: '#1E293B',
            900: '#0F172A',
          }
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Menlo', 'monospace'],
      },
      boxShadow: {
        'pertamina-sm': '0 1px 3px 0 rgba(0, 45, 98, 0.08)',
        'pertamina-md': '0 4px 6px -1px rgba(0, 45, 98, 0.12), 0 2px 4px -2px rgba(0, 45, 98, 0.08)',
        'pertamina-lg': '0 10px 15px -3px rgba(0, 45, 98, 0.15), 0 4px 6px -4px rgba(0, 45, 98, 0.1)',
      }
    },
  },
  plugins: [],
}
```

> Font `Plus Jakarta Sans` & `JetBrains Mono` wajib dimuat di `frontend/index.html` (Google Fonts `<link>`) atau di-*self-host* via `@fontsource/*`; tanpa itu token `font-sans`/`font-mono` jatuh ke font sistem.

#### 2. Berkas `frontend/postcss.config.js`
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

#### 3. Berkas `frontend/src/index.css`
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-pertamina-gray-50 text-pertamina-gray-900 font-sans antialiased;
  }
}
```

#### 4. Berkas `frontend/vite.config.js` (Proxy Development)
Proxy ini membuat frontend dan backend tampil sebagai satu origin saat development, sehingga tidak ada masalah CORS dan `api.js` cukup memakai path relatif `/api/...`.
```javascript
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
```

---

## 4. Desain Database & Kamus Data Lengkap (SQLAlchemy 2.0 Specifications)

Basis data terdiri dari **9 tabel**:

| No | Tabel | Model SQLAlchemy | Fungsi Singkat |
| :---: | :--- | :--- | :--- |
| 1 | `app_user` | `AppUser` | Akun pegawai & peran (RBAC) |
| 2 | `procurement_tender_project` | `TenderProject` | Paket pengadaan (entitas utama) |
| 3 | `procurement_document_draft` | `DocumentDraft` | Versi dokumen `.docx` per paket |
| 4 | `procurement_document_clause` | `DocumentClause` | Pasal/klausul granular per draf |
| 5 | `procurement_uploaded_attachment` | `UploadedAttachment` | Berkas acuan (BoQ, RKS, TOR) |
| 6 | `procurement_chat_session` | `ChatSession` | Sesi percakapan per paket |
| 7 | `procurement_chat_message` | `ChatMessage` | Pesan chat, tool-calls, artifact |
| 8 | `procurement_stk_rule` | `StkRule` | Katalog 86 aturan STK (sinkron Qdrant) |
| 9 | `procurement_audit_trail` | `AuditTrail` | Jejak audit kepatuhan (*append-only*) |

### 4.1 Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    APP_USER ||--o{ PROCUREMENT_TENDER_PROJECT : "membuat / mengelola"
    APP_USER ||--o{ PROCUREMENT_AUDIT_TRAIL : "melakukan aksi"
    PROCUREMENT_TENDER_PROJECT ||--o{ PROCUREMENT_DOCUMENT_DRAFT : "memiliki riwayat versi"
    PROCUREMENT_TENDER_PROJECT ||--o{ PROCUREMENT_UPLOADED_ATTACHMENT : "memiliki berkas acuan"
    PROCUREMENT_TENDER_PROJECT ||--o{ PROCUREMENT_CHAT_SESSION : "memiliki sesi diskusi AI"
    PROCUREMENT_TENDER_PROJECT |o--o{ PROCUREMENT_AUDIT_TRAIL : "mencatat jejak aktivitas"
    
    PROCUREMENT_DOCUMENT_DRAFT ||--o{ PROCUREMENT_DOCUMENT_CLAUSE : "terdiri dari 40 pasal IKPP"
    
    PROCUREMENT_CHAT_SESSION ||--o{ PROCUREMENT_CHAT_MESSAGE : "berisi percakapan"
    
    PROCUREMENT_STK_RULE |o--o{ PROCUREMENT_DOCUMENT_CLAUSE : "menjadi dasar validasi kepatuhan"

    APP_USER {
        uuid id PK
        string username UK
        string email UK
        string nama_lengkap
        string jabatan
        string password_hash
        string role
        boolean is_active
        timestamp last_login_at
        timestamp created_at
    }

    PROCUREMENT_TENDER_PROJECT {
        uuid id PK
        uuid user_id FK
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
        timestamp deleted_at
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
        int stk_rule_id FK
        int nomor_urut
        string kode_pasal
        string judul_pasal
        text teks_original
        text teks_revisi_ai
        boolean is_edited_manual
        string status_verifikasi
        text catatan_stk
        timestamp updated_at
    }

    PROCUREMENT_UPLOADED_ATTACHMENT {
        uuid id PK
        uuid project_id FK
        string tipe_berkas
        string nama_file_asli
        string file_path
        bigint ukuran_bytes
        string hash_sha256
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
        string nomor_aturan UK
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
        uuid user_id FK
        string tipe_aksi
        string modul_terkait
        text rincian_perubahan
        jsonb snapshot_data
        string ip_address
        timestamp recorded_at
    }
```

### 4.2 Kamus Data & Spesifikasi Rinci Setiap Tabel

#### 1. Tabel: `app_user`
* **Deskripsi:** Menyimpan akun pegawai yang berhak mengakses sistem beserta perannya. Menjadi dasar otorisasi (RBAC) dan atribusi jejak audit.
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, Default: `gen_random_uuid()` | Pengenal unik pengguna |
| `username` | `VARCHAR(50)` | `UNIQUE`, `NOT NULL` | Nama login (misal: NIP / nomor pekerja) |
| `email` | `VARCHAR(255)` | `UNIQUE`, `NOT NULL` | Email korporat |
| `nama_lengkap` | `VARCHAR(150)` | `NOT NULL` | Nama yang tampil di UI & dokumen |
| `jabatan` | `VARCHAR(150)` | Nullable | Jabatan struktural (misal: Area Manager Procurement) |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | Hash argon2/bcrypt — **tidak pernah** menyimpan password asli |
| `role` | `VARCHAR(30)` | `NOT NULL`, `CHECK`, Default: `'FPP'` | Pilihan: `'ADMIN'`, `'PROCUREMENT'`, `'FPP'`, `'APPROVER'`, `'AUDITOR'` (lihat 4.4) |
| `is_active` | `BOOLEAN` | `NOT NULL`, Default: `TRUE` | Akun nonaktif tidak bisa login (pengganti hapus akun) |
| `last_login_at` | `TIMESTAMP WITH TIME ZONE` | Nullable | Waktu login terakhir |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu akun dibuat |

---

#### 2. Tabel: `procurement_tender_project`
* **Deskripsi:** Menyimpan entitas utama paket pekerjaan tender/pengadaan yang sedang disusun oleh Pejabat Pembuat Komitmen (PPK) atau Tim Pengadaan.
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, Default: `gen_random_uuid()` | Pengenal unik proyek tender |
| `user_id` | `UUID` | `FOREIGN KEY` -> `app_user.id`, `ON DELETE SET NULL`, Nullable | Akun pegawai / PPK pembuat proyek |
| `no_tender` | `VARCHAR(100)` | `UNIQUE`, `INDEX`, Nullable | Nomor resmi paket tender (misal: `PR-2026-PN-0042`) |
| `nama_pengadaan` | `VARCHAR(255)` | `NOT NULL` | Nama paket pengadaan barang/jasa |
| `tipe_dokumen` | `VARCHAR(50)` | `NOT NULL`, `CHECK`, Default: `'tender'` | Pilihan: `'tender'` (IKPP 2.0), `'rks'`, `'kontrak'`, `'amendemen'` |
| `hps_total` | `NUMERIC(18,2)`| `NOT NULL`, `CHECK (hps_total >= 0)`, Default: `0.00` | Nilai Total Harga Perkiraan Sendiri (Rupiah) |
| `resiko_csms` | `VARCHAR(20)` | `NOT NULL`, `CHECK`, Default: `'Tinggi'` | Tingkat risiko K3L: `'Ekstrim'`, `'Tinggi'`, `'Sedang'`, `'Rendah'` |
| `status_tahap` | `VARCHAR(50)` | `NOT NULL`, `CHECK`, Default: `'DRAFT'` | Status alur: `'DRAFT'`, `'EKSTRAKSI'`, `'REVIEW_CANVAS'`, `'PUBLISHED'` |
| `current_step` | `SMALLINT` | `NOT NULL`, `CHECK (current_step BETWEEN 1 AND 4)`, Default: `1` | Indikator tahap 1-4 pada Progress Drawer UI |
| `metadata_ekstraksi` | `JSONB` | Nullable, Default: `{}` | Parameter hasil parsing BoQ/TOR (jangka waktu, jaminan, denda) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu inisiasi sesi proyek |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu pembaruan terakhir |
| `deleted_at` | `TIMESTAMP WITH TIME ZONE` | Nullable, `INDEX` | *Soft delete*: terisi bila paket diarsipkan/dihapus dari UI; baris tidak dihapus fisik |

---

#### 3. Tabel: `procurement_document_draft`
* **Deskripsi:** Menyimpan versi dan draf dokumen Microsoft Word (`.docx`) yang dihasilkan oleh sistem AI / diekspor pengguna. Mendukung *versioning* (v1.0, v2.0, dll).
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, Default: `gen_random_uuid()` | Pengenal unik draf dokumen |
| `project_id` | `UUID` | `FOREIGN KEY` -> `procurement_tender_project.id`, `ON DELETE CASCADE` | Relasi ke paket tender pemilik |
| `versi` | `VARCHAR(20)` | `NOT NULL`, Default: `'v1.0'`, `UNIQUE (project_id, versi)` | Label versi dokumen (misal: `'v1.0'`, `'v2.0-revisi'`) |
| `judul_dokumen` | `VARCHAR(255)` | `NOT NULL` | Judul berkas formal (misal: `Dokumen_Tender_IKPP_v2.0.docx`) |
| `file_docx_path` | `VARCHAR(500)` | Nullable | Path relatif file Word di storage `media/generated_docs/` |
| `skor_kepatuhan_stk` | `SMALLINT` | Nullable, `CHECK (skor_kepatuhan_stk BETWEEN 0 AND 100)` | Skor kesesuaian terhadap 86 aturan STK. `NULL` = belum dinilai (tidak boleh default 100 agar tidak menyesatkan) |
| `is_active` | `BOOLEAN` | `NOT NULL`, Default: `TRUE` | Menandai versi draf yang sedang aktif di Live Canvas (maksimal satu per proyek — *partial unique index*) |
| `status_approval` | `VARCHAR(30)` | `NOT NULL`, `CHECK`, Default: `'DRAFT'` | Pilihan: `'DRAFT'`, `'MENUNGGU_REVIEW'`, `'DISETUJUI'`, `'DITOLAK'` |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu pembuatan versi dokumen |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu modifikasi terakhir |

---

#### 4. Tabel: `procurement_document_clause`
* **Deskripsi:** Menyimpan rincian tiap pasal/klausul (40 Poin IKPP & Kontrak) secara granular sehingga dapat diedit satu per satu di Live Canvas editor.
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, Default: `gen_random_uuid()` | Pengenal unik pasal/klausul |
| `draft_id` | `UUID` | `FOREIGN KEY` -> `procurement_document_draft.id`, `ON DELETE CASCADE` | Relasi ke draf dokumen induk |
| `stk_rule_id` | `INTEGER` | `FOREIGN KEY` -> `procurement_stk_rule.id`, `ON DELETE SET NULL`, Nullable | Aturan STK yang menjadi dasar validasi klausul |
| `nomor_urut` | `INTEGER` | `NOT NULL`, `UNIQUE (draft_id, nomor_urut)` | Urutan tampilan bab/pasal (1 s.d. 40+) |
| `kode_pasal` | `VARCHAR(50)` | `NOT NULL` | Kode referensi pasal (misal: `'IKPP-01'`, `'KONTRAK-PASAL-14'`) |
| `judul_pasal` | `VARCHAR(255)` | `NOT NULL` | Judul klausul (misal: `Masa Pemeliharaan & Garansi`) |
| `teks_original` | `TEXT` | `NOT NULL` | Teks acuan baku standar Pertamina |
| `teks_revisi_ai` | `TEXT` | `NOT NULL` | Teks hasil sintesis Copilot sesuai konteks proyek |
| `is_edited_manual` | `BOOLEAN` | `NOT NULL`, Default: `FALSE` | Menandai apakah klausul telah diedit manual oleh PPK di canvas |
| `status_verifikasi` | `VARCHAR(30)` | `NOT NULL`, `CHECK`, Default: `'BELUM_DICEK'` | Status kesesuaian: `'BELUM_DICEK'`, `'COMPLIANT'`, `'WARNING'`, `'DEVIATED'` |
| `catatan_stk` | `TEXT` | Nullable | Rujukan pasal Pedoman A03-001 yang mendasari klausul ini |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu pembaruan teks klausul |

---

#### 5. Tabel: `procurement_uploaded_attachment`
* **Deskripsi:** Menyimpan data berkas acuan yang diunggah pengguna (Bill of Quantities Excel, RKS teknis PDF, Kerangka Acuan Kerja).
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, Default: `gen_random_uuid()` | Pengenal unik berkas unggahan |
| `project_id` | `UUID` | `FOREIGN KEY` -> `procurement_tender_project.id`, `ON DELETE CASCADE` | Relasi ke paket pengadaan |
| `tipe_berkas` | `VARCHAR(30)` | `NOT NULL`, `CHECK` | Kategori: `'BOQ_EXCEL'`, `'BOQ_PDF'`, `'RKS_PDF'`, `'TOR_KAK'`, `'GAMBAR_TEKNIK'` |
| `nama_file_asli` | `VARCHAR(255)` | `NOT NULL` | Nama asli berkas saat diunggah (hanya untuk tampilan; selalu di-escape di UI) |
| `file_path` | `VARCHAR(500)` | `NOT NULL` | Lokasi fisik di `media/uploads/` dengan nama file acak (UUID), **bukan** nama asli |
| `ukuran_bytes` | `BIGINT` | `NOT NULL`, `CHECK (ukuran_bytes > 0)` | Ukuran berkas dalam byte (maks. 100 MB) |
| `hash_sha256` | `CHAR(64)` | `INDEX` | Hash checksum untuk mendeteksi duplikasi berkas identik |
| `hasil_ekstraksi_json` | `JSONB` | Nullable, Default: `{}` | Hasil pembacaan teks / tabel oleh parser `summarizer.py` |
| `uploaded_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu berkas selesai diunggah |

---

#### 6. Tabel: `procurement_chat_session`
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

#### 7. Tabel: `procurement_chat_message`
* **Deskripsi:** Menyimpan setiap baris percakapan chat, log *tool-calls* (seperti `check_stk_compliance`, `update_clause`), dan metadata artifact yang ditampilkan pada bubble chat.
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, Default: `gen_random_uuid()` | Pengenal unik pesan |
| `session_id` | `UUID` | `FOREIGN KEY` -> `procurement_chat_session.id`, `ON DELETE CASCADE`, `INDEX (session_id, created_at)` | Relasi ke sesi obrolan induk |
| `role` | `VARCHAR(20)` | `NOT NULL`, `CHECK` | Pengirim: `'user'`, `'assistant'`, `'system'`, `'tool'` |
| `content` | `TEXT` | `NOT NULL` | Teks isi pesan (disimpan mentah; dirender aman di frontend, lihat 9.4) |
| `tool_calls` | `JSONB` | Nullable | Parameter panggilan alat bantu AI (klausul yang diubah, query RAG) |
| `artifacts_payload` | `JSONB` | Nullable | Data card interaktif yang dirender di bubble chat |
| `prompt_tokens` | `INTEGER` | `NOT NULL`, Default: `0` | Jumlah token prompt input (untuk monitoring biaya LLM) |
| `completion_tokens` | `INTEGER` | `NOT NULL`, Default: `0` | Jumlah token respons (untuk monitoring throughput) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu pesan dikirimkan |

---

#### 8. Tabel: `procurement_stk_rule`
* **Deskripsi:** Katalog referensi aturan baku **Pedoman Pengadaan No. A03-001/PNG200000/2024-S9** (86 aturan STK) yang tersinkronisasi dengan Qdrant Vector Store.
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY`, Auto-increment | ID aturan |
| `kode_pedoman` | `VARCHAR(50)` | `NOT NULL`, Default: `'A03-001/PNG200000/2024-S9'` | Nomor surat pedoman pengadaan acuan |
| `nomor_aturan` | `VARCHAR(20)` | `UNIQUE`, `INDEX`, `NOT NULL` | Kode nomor aturan (misal: `'STK-01'`, `'STK-44'`) |
| `kategori_stk` | `VARCHAR(50)` | `NOT NULL` | Kategori (misal: `'Jaminan'`, `'K3L CSMS'`, `'Denda'`, `'TKDN'`) |
| `judul_aturan` | `VARCHAR(255)` | `NOT NULL` | Judul singkat aturan |
| `deskripsi_aturan` | `TEXT` | `NOT NULL` | Penjelasan ketentuan hukum & operasional pengadaan |
| `klausul_baku_docx` | `TEXT` | Nullable | Bunyi kalimat resmi yang wajib masuk ke dalam template Word |
| `level_kepatuhan` | `VARCHAR(20)` | `NOT NULL`, `CHECK`, Default: `'MANDATORY'` | Sifat aturan: `'MANDATORY'` (Wajib mutlak) atau `'OPTIONAL'` |
| `qdrant_point_id` | `VARCHAR(64)` | Nullable, `INDEX` | ID vektor embeddings terkait di koleksi Qdrant |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()` | Waktu pembaruan aturan |

---

#### 9. Tabel: `procurement_audit_trail`
* **Deskripsi:** Mencatat riwayat audit resmi (*compliance audit log*) dari seluruh tindakan penting pengguna dan perubahan pasal dokumen sesuai standar kepatuhan BUMN. Tabel ini bersifat **append-only**: aplikasi hanya boleh `INSERT`, tidak pernah `UPDATE`/`DELETE`, dan entri **tidak ikut terhapus** ketika proyek dihapus.
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `BIGINT` | `PRIMARY KEY`, Auto-increment | ID entri log |
| `project_id` | `UUID` | `FOREIGN KEY` -> `procurement_tender_project.id`, `ON DELETE SET NULL`, Nullable, `INDEX` | Relasi ke paket pengadaan (tetap tersimpan walau proyek dihapus) |
| `user_id` | `UUID` | `FOREIGN KEY` -> `app_user.id`, `ON DELETE SET NULL`, Nullable | Pengguna yang melakukan tindakan |
| `tipe_aksi` | `VARCHAR(50)` | `NOT NULL`, `INDEX` | Jenis aksi: `'LOGIN'`, `'UPLOAD_BOQ'`, `'GENERATE_DOCX'`, `'REVISI_PASAL'`, `'APPROVAL'`, `'EXPORT_DOKUMEN'`, `'HAPUS_PROYEK'` |
| `modul_terkait` | `VARCHAR(50)` | `NOT NULL` | Modul yang disentuh: `'CANVAS'`, `'CHAT'`, `'EXPORTER'`, `'AUTH'` |
| `rincian_perubahan` | `TEXT` | `NOT NULL` | Detail perubahan (misal: "Ubah Masa Pemeliharaan dari 90 menjadi 180 hari") |
| `snapshot_data` | `JSONB` | Nullable | Ringkasan identitas objek saat aksi terjadi (misal `no_tender`, `nama_pengadaan`) agar log tetap bermakna setelah proyek dihapus |
| `ip_address` | `VARCHAR(45)` | Nullable | Alamat IP jaringan pengguna (dari header `X-Real-IP` Nginx) |
| `recorded_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, ServerDefault: `now()`, `INDEX` | Waktu pencatatan jejak audit |

---

#### 10. Tabel: `procurement_dataset_file` (ditambahkan Fase 3, migrasi `8aca9b2ff148`)
* **Deskripsi:** Catatan setiap berkas di folder dataset drive (`DATASET_DIR`) beserta status ingest-nya ke Qdrant. Sinkronisasi membandingkan ukuran, waktu ubah, dan `hash_sha256`, sehingga berkas yang tidak berubah tidak di-ingest ulang.
* **Tabel Spesifikasi:**

| Nama Kolom | Tipe Data | Constraint | Keterangan & Aturan Bisnis |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY` | ID berkas (dipakai frontend saat memilih berkas acuan) |
| `relative_path` | `VARCHAR(1000)` | `NOT NULL`, `UNIQUE` | Path relatif terhadap `DATASET_DIR` (pemisah `/`) |
| `nama_file` | `VARCHAR(255)` | `NOT NULL` | Nama berkas; dipakai sebagai `source` di Qdrant |
| `collection` | `VARCHAR(50)` | Nullable, `INDEX` | `rks_kb` / `contract_kb` / `amendment_kb`; `NULL` = berkas acuan |
| `ukuran_bytes` | `BIGINT` | `NOT NULL`, `CHECK >= 0` | Ukuran berkas |
| `modified_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL` | Waktu ubah berkas di folder |
| `hash_sha256` | `VARCHAR(64)` | `NOT NULL`, `INDEX` | Sidik isi berkas |
| `status` | `VARCHAR(20)` | `NOT NULL`, `CHECK` | `TERINDEKS`, `REFERENSI`, `DILEWATI` (format belum didukung / nama ganda), `GAGAL` |
| `jumlah_chunk` | `INTEGER` | Default `0` | Jumlah chunk hasil ingest |
| `pesan` | `TEXT` | Nullable | Alasan dilewati / pesan error |
| `created_at`, `updated_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL` | Waktu pencatatan |

Perubahan lain pada migrasi yang sama: kolom **`konten_json` (`JSONB`)** di `procurement_document_draft` (JSON draf RKS dari agent, atau parameter formulir untuk generator lain) dan nilai `tipe_aksi` baru `SINKRON_DATASET`.

---

### 4.3 Aturan Integritas Data & Indeks (*Database Indexing*)
1. **Foreign Key Cascading & Soft Delete**:
   * Penghapusan paket dari UI menggunakan **soft delete** (`deleted_at` diisi), bukan `DELETE` fisik. Seluruh query daftar paket wajib memfilter `deleted_at IS NULL`.
   * Bila penghapusan fisik tetap dilakukan (misal oleh Admin untuk data uji), draf, klausul, lampiran, dan riwayat chat ikut terhapus (`ON DELETE CASCADE`), **tetapi** `procurement_audit_trail` dipertahankan (`ON DELETE SET NULL` + `snapshot_data`).
2. **Domain Nilai Terkontrol**:
   * Kolom status/pilihan (`role`, `tipe_dokumen`, `resiko_csms`, `status_tahap`, `status_approval`, `status_verifikasi`, `tipe_berkas`, `level_kepatuhan`) didefinisikan sebagai Python `enum.Enum` di model SQLAlchemy dan dikunci di database dengan `CHECK` constraint, sehingga nilai liar dari LLM atau frontend tertolak.
   * Pydantic schema memakai tipe `Literal[...]`/`Enum` yang sama, sehingga validasi request konsisten dengan database.
3. **Kueri Berkecepatan Tinggi (Indexing)**:
   * Kolom pencarian cepat seperti `no_tender`, `hash_sha256`, `qdrant_point_id`, `tipe_aksi`, dan `recorded_at` dilengkapi indeks B-Tree.
   * Indeks komposit `(session_id, created_at)` untuk memuat riwayat chat berurutan.
   * *Partial unique index* `(project_id) WHERE is_active` agar hanya ada satu draf aktif per proyek.
4. **Format Field JSONB**:
   * Digunakan untuk kolom `metadata_ekstraksi`, `tool_calls`, `artifacts_payload`, `hasil_ekstraksi_json`, dan `snapshot_data` pada PostgreSQL agar dapat dikueri langsung menggunakan operator JSON bawaan (`->`, `->>`). Bila diperlukan pencarian di dalam JSONB, tambahkan indeks GIN.
5. **Kolom `updated_at`**:
   * Diperbarui otomatis via `onupdate=func.now()` di SQLAlchemy (ServerDefault hanya berlaku saat insert).

### 4.4 Matriks Peran & Hak Akses (RBAC)

| Aksi | `ADMIN` | `PROCUREMENT` | `FPP` (User Peminta) | `APPROVER` | `AUDITOR` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Kelola akun pengguna | ✅ | – | – | – | – |
| Buat paket & upload BoQ/RKS | ✅ | ✅ | ✅ | – | – |
| Chat dengan Copilot & revisi pasal | ✅ | ✅ | ✅ (paket miliknya) | – | – |
| Generate & unduh `.docx` | ✅ | ✅ | ✅ (paket miliknya) | ✅ | – |
| Ubah `status_approval` (setujui/tolak) | ✅ | – | – | ✅ | – |
| Ingest / hapus Knowledge Base (Qdrant) | ✅ | ✅ | – | – | – |
| Lihat seluruh paket (read-only) | ✅ | ✅ | – | ✅ | ✅ |
| Lihat Audit Trail | ✅ | – | – | – | ✅ |

Penegakan dilakukan di backend melalui dependency `require_role(...)` pada setiap route; frontend hanya menyembunyikan tombol sebagai kenyamanan, **bukan** sebagai kontrol keamanan.

---

## 5. Tahapan Implementasi (Rencana Kerja 5 Fase)

### Fase 1: Inisialisasi Frontend React (Vite JavaScript) + Tailwind CSS v3 & Setup Backend FastAPI
- [x] Inisialisasi proyek React menggunakan Vite (JavaScript) di dalam folder `frontend/`.
- [x] Instalasi dan konfigurasi **Tailwind CSS v3** (`tailwindcss@^3.4.17`, `postcss`, `autoprefixer`).
- [x] Buat file `frontend/tailwind.config.js` dengan palet warna resmi korporat Pertamina (lihat 3.1).
- [x] Buat file `frontend/postcss.config.js` untuk integrasi plugin Tailwind CSS dan Autoprefixer.
- [x] Konfigurasi `frontend/src/index.css` dengan direktif `@tailwind base; @tailwind components; @tailwind utilities;`.
- [x] Bersihkan sisa template Vite (`App.css`, `assets/hero.png`, `assets/react.svg`, `assets/vite.svg`, `public/icons.svg`), ubah `<title>` dan `lang="id"` di `index.html`, serta muat font Plus Jakarta Sans & JetBrains Mono.
- [x] Konfigurasi `frontend/vite.config.js` untuk development proxy `/api` -> `http://127.0.0.1:8000` (lihat 3.1 butir 4).
- [x] Buat struktur folder komponen modular di `frontend/src/komponen/` (`Navbar/`, `Chat/`, `Canvas/`, `Common/`; `Auth/` menyusul di Fase 2).
- [x] Migrasikan antarmuka Claude-style UI dari `frontend_vanilla/` ke komponen React + utility classes Tailwind, sambil memperbaiki bug prototipe yang tercatat di `draft_perencanaan_frontend.md` Bagian 7.
- [x] Pindahkan `Agentic_Rag_Pertamina_camp/api.py` ke `backend/app/api/` (router per domain) dan kelola dependensi dengan `uv` (`backend/pyproject.toml`, versi disamakan dengan `uv.lock` camp). Paket database & auth (`sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pyjwt`, `pwdlib[argon2]`) ditambahkan di Fase 2.
- [x] Buat `backend/app/main.py` dengan `CORSMiddleware` (origin whitelist dari `.env`, **bukan** `*`) dan OpenAPI Swagger di `/docs` (hanya aktif bila `DEBUG=True`).
- [x] **Milestone Fase 1:** alur Upload BoQ → `/api/extract-tender-metadata` → kartu verifikasi → Canvas React berjalan nyata (tanpa data demo). Alur web terverifikasi 19 Okt 2026 dengan PDF BoQ nyata via proxy Vite; akurasi ekstraksi menunggu perbaikan bug LLM oleh tim AI (`pertanyaan penanggung jawab ai.md` C1).

### Fase 2: Database SQLAlchemy 2.0, Alembic & Autentikasi
- [x] Definisikan 9 model tabel deklaratif di `backend/app/models/` beserta enum & `CHECK` constraint (lihat 4.3).
- [x] Konfigurasi koneksi async database di `backend/app/database.py`. PostgreSQL development berjalan di Docker (`compose.dev.yml`, hanya terbuka di `127.0.0.1:5432`).
- [x] Inisialisasi Alembic (`alembic init -t async alembic`) dan buat migrasi awal (`alembic revision --autogenerate -m "initial_procurement_tables"`). Hasil review manual: CHECK constraint enum ganda dirapikan menjadi satu per kolom (`ck_<tabel>_<enum>`); `alembic check` bersih.
- [x] Jalankan migrasi ke PostgreSQL lokal / Docker (`alembic upgrade head`).
- [x] Implementasikan `core/security.py` (hash argon2, JWT access token 30 menit + refresh token) dan route `/api/auth/login`, `/api/auth/me`, `/api/auth/refresh`, `/api/auth/logout`, plus pembatas percobaan login (`core/rate_limit.py`, in-memory; pindah ke Redis bila multi-worker).
- [x] Terapkan `require_role(...)` pada seluruh route sesuai matriks 4.4, serta pencatatan `AuditTrail` untuk aksi penting (login, login gagal, ekstraksi, generate .docx, ingest/hapus KB) lewat `core/audit.py`.
- [x] Buat skrip seed `app/scripts/seed.py`: akun `ADMIN` awal (password dari `.env`), tambah akun per peran, dan impor katalog STK dari berkas JSON.
- [ ] Isi data 86 aturan STK (`uv run python -m app.scripts.seed stk <berkas.json>`): menunggu sumber data resmi katalog STK.
- [x] Frontend: `LoginPage`, `ProtectedRoute`, dan `api.js` yang menyisipkan header `Authorization: Bearer <token>` (access token hanya di memori, refresh lewat cookie HttpOnly, retry otomatis sekali saat 401), serta tombol yang disembunyikan sesuai peran (`services/permissions.js`).

### Fase 3: Integrasi Modul AI RAG ke Endpoint FastAPI & UI React
- [x] Pindahkan logic dari `Agentic_Rag_Pertamina_camp` (`RAG/`, `tender/`, `contract/`, dan `agent.py` → `services/agent/graph.py`) ke `backend/app/services/` (disalin; hanya import yang ditulis ulang ke `app.services.*`).
- [ ] Koordinasi dengan tim AI: generator mengembalikan draf secara langsung (bukan lewat variabel global modul) agar lock sementara di `tender_routes.py` bisa dihapus (`pertanyaan penanggung jawab ai.md` C4).
- [x] Router endpoint asinkron di `backend/app/api/` (seluruhnya membutuhkan login):
  - `POST /api/extract-tender-metadata`: berkas acuan dipilih dari folder drive (`rks_file_id` / `boq_file_id`); field unggah `file_rks`/`file_boq` tetap diterima API tetapi tidak lagi dipakai UI. Hasil disimpan ke `metadata_ekstraksi` paket bila `project_id` dikirim.
  - `POST /api/generate-tender|rks|kontrak|amendemen`: menerima `project_id` opsional, lalu menyimpan versi draf (`konten_json` + salinan `.docx` di `output/drafts/`).
  - `POST /api/kb/ingest`, `GET /api/kb/list`, `DELETE /api/kb/delete` (Qdrant).
  - **Baru:** `GET /api/dataset/files` & `POST /api/dataset/sync` (folder drive → Qdrant; tabel `procurement_dataset_file`).
  - **Baru:** `POST /api/chat/sessions`, `GET /api/chat/sessions[/{id}]`, `POST /api/chat/sessions/{id}/messages` (agent RKS; satu sesi = satu paket = satu `thread_id` LangGraph), `GET /api/drafts/{id}/download`.
- [x] Simpan hasil ekstraksi, percakapan, dan draf ke tabel terkait (`procurement_tender_project`, `procurement_chat_session/message`, `procurement_document_draft` berversi).
- [x] Hubungkan `ChatPanel`, `CanvasReview` (`RksDraftView` untuk JSON draf agent), `DatasetPickerModal` (pengganti unggah berkas), `KnowledgeBaseView` (status folder drive), dan riwayat sesi di `HamburgerMenu` ke FastAPI via `services/api.js`.
- [x] Pengaman web di sekitar agent: saat agent meminta BoQ, hanya "lewati" atau berkas dari `DATASET_DIR` yang diteruskan (agent menerima path berkas lokal); stdout dipaksa UTF-8 agar `print()` emoji di modul AI tidak menggagalkan request di Windows.
- [x] **Milestone Fase 3** (terverifikasi 19 Okt 2026 dengan LLM & Qdrant sungguhan): chat RKS → BoQ dipilih dari drive → 6 informasi dikumpulkan → draf v1.0 → "setuju" → `.docx` (60 KB) terunduh → riwayat 23 pesan tersimpan.
- Catatan: agent hanya tersedia untuk RKS. Sesi Tender/Kontrak/Amendemen menjawab "asisten belum tersedia" dan dokumen dibuat lewat kanvas + endpoint generate (`pertanyaan penanggung jawab ai.md` F1).

### Fase 4: Streaming Token AI (SSE) & Pemrosesan Latar Belakang
- [x] `POST /api/chat/sessions/{id}/stream` (SSE): event `progress` (label tiap node agent), `token` (hanya node `direct_answer` & `kb_answer`), `done` (isi sama dengan endpoint non-stream), `error`, plus komentar heartbeat `: ping` tiap 15 detik. Header `X-Accel-Buffering: no`. Frontend membaca via `fetch` + `ReadableStream` (`streamChatMessage`).
- [x] Ukur durasi (19 Okt 2026, laptop): klarifikasi 12–29 detik, draf RKS ±114 detik, Docling BoQ ±452 detik, ekstraksi Tender ±44 detik. **Keputusan:** chat tetap satu request SSE (heartbeat mencegah timeout proxy); sinkronisasi drive memakai pola *job* in-process (`core/jobs.py`: `POST /api/dataset/sync` → 202 + `job_id`, lalu `GET /api/jobs/{job_id}`). Celery + Redis belum diaktifkan, karena backend dijalankan satu proses. Aktifkan bila nanti multi-worker.
- [x] Status proses tampil di `ProgressDrawer` (bagian "Proses Berjalan") dan indikator kuning berkedip di `VerticalRestoreTab`; bubble chat sementara menampilkan tahap agent lalu token jawaban.
- [x] Housekeeping (masterplan 9.2) sebagai task periodik di *lifespan* FastAPI: berkas di `OUTPUT_DIR` yang lebih tua dari `TEMP_RETENTION_DAYS` (7 hari) dihapus, kecuali `output/drafts/`.

### Fase 5: Dockerization, Nginx Gateway, & Pipeline CI/CD
- [ ] Susun `backend/Dockerfile` (Python FastAPI + Uvicorn) dan `frontend/Dockerfile` (Node build → Nginx).
- [ ] Buat `docker-compose.yml` dengan service inti `nginx`, `web`, `qdrant`, `db` (+ `redis`, `celery_worker`, `celery_beat` sebagai profil opsional).
- [ ] Siapkan `.github/workflows/ci.yml` (setiap PR & push) dan `.github/workflows/deploy.yml` (hanya `main`).
- [ ] Pasang sertifikat TLS (Let's Encrypt / sertifikat korporat) di Nginx.
- [ ] Uji coba skenario *end-to-end* (Login → Upload BoQ → Ekstraksi AI → Edit Canvas di React → Generate Dokumen → Approval → Unduh .docx).

---

## 6. Matrix Mitigasi Risiko & Cadangan Solusi

| Potensi Kendala | Risiko | Solusi Mitigasi |
| :--- | :--- | :--- |
| **Ekstraksi BoQ Excel memakan waktu lama** | Browser mengalami timeout | Tahap awal: `run_in_threadpool` + timeout Nginx 300s. Bila tidak cukup: pola *job* dengan Celery worker yang melaporkan progres ke frontend. |
| **Koneksi LLM terputus di tengah jalan** | Dokumen gagal terbentuk utuh | Logika *retry* dengan *exponential backoff* (maksimal 3 kali) pada `services` sebelum melaporkan error ke chat window. |
| **Output LLM tidak valid / halusinasi nilai** | Nilai HPS, jaminan, atau denda salah masuk dokumen | Validasi output LLM dengan Pydantic schema; nilai kritikal wajib diverifikasi user di micro-card sebelum diterapkan ke canvas. |
| **CORS Blocking pada Pengujian Lokal** | Request frontend ditolak browser | Vite dev server menggunakan proxy `/api` -> `http://127.0.0.1:8000`; di produksi frontend & API berada di origin yang sama via Nginx. |
| **XSS dari nama berkas / output LLM** | Script berbahaya dieksekusi di browser pengguna lain | Render teks via JSX (auto-escape); Markdown disanitasi dengan DOMPurify (lihat 9.4). |
| **Kebocoran data pengadaan ke LLM eksternal** | Data rahasia vendor/HPS keluar dari jaringan korporat | Konfigurasi `LLM_PROVIDER` yang dapat dialihkan ke model internal; minimalkan data yang dikirim ke OpenRouter. |
| **Migrasi Skema Database di Produksi** | Kegagalan update tabel | Alembic versioning dengan verifikasi *dry-run* (`alembic upgrade head --sql`) dan backup `pg_dump` sebelum eksekusi riil. |

---

## 7. Strategi CI/CD & Alur Penambahan Fitur Baru

### 7.1 Diagram Siklus CI/CD
```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer (Laptop Lokal)
    participant Git as GitHub Repository
    participant CI as GitHub Actions (CI Runner)
    participant Reg as Container Registry (GHCR)
    participant Server as Server Deploy (Docker + Nginx)
    actor User as Pengguna (User Pertamina)

    Dev->>Git: 1. Push branch fitur & buka Pull Request
    Git->>CI: 2. Trigger ci.yml (lint, build, test)
    Note over CI: Lint & Build<br/>- oxlint + npm run build (React Vite)<br/>- Ruff + Pytest (FastAPI)
    Dev->>Git: 3. Merge PR ke main (setelah CI hijau)
    Git->>CI: 4. Trigger deploy.yml
    CI->>Reg: 5. Build & push image web + nginx (tag: commit SHA & latest)
    CI->>Server: 6. SSH: perintahkan update
    Note over Server: Server Mengeksekusi:<br/>- docker compose pull<br/>- alembic upgrade head<br/>- docker compose up -d
    Server-->>User: 7. Fitur baru tayang (minimal downtime, ±beberapa detik restart)
```

### 7.2 Siklus Penambahan Fitur Baru (Developer Workflow)
1. **Lokal (Branching & Development)**:
   - Developer membuat branch fitur baru: `git checkout -b feature/nama-fitur`.
   - Menambahkan komponen baru di `frontend/src/komponen/nama-fitur/`.
   - Mengubah model di `backend/app/models/`, menjalankan `alembic revision --autogenerate -m "add_new_feature"`.
   - Menjalankan pengujian lokal: `npm run lint && npm run build` di frontend dan `ruff check backend && pytest backend/tests/` di backend.
2. **Pull Request & Continuous Integration (CI)**:
   - Developer mem-push branch ke GitHub dan membuka Pull Request (PR) ke `main`.
   - GitHub Actions (`ci.yml`) otomatis menjalankan:
     - **Frontend**: `oxlint` dan `npm run build` memastikan JSX dan dependensi React valid.
     - **Backend**: `ruff check` dan Pytest (memverifikasi auth, validasi Pydantic, route FastAPI, dan generator `.docx`) dengan service PostgreSQL di CI.
   - Branch `main` diproteksi (*branch protection rule*): PR hanya dapat di-merge jika seluruh pengujian berstatus **HIJAU (PASS)**.
3. **Continuous Deployment (CD) ke Server**:
   - Setelah branch di-merge ke `main`, `deploy.yml`:
     - Mem-build image `web` dan `nginx`, lalu push ke GHCR dengan tag commit SHA dan `latest`.
     - Melakukan koneksi SSH ke server, lalu menjalankan:
       ```bash
       docker compose pull web nginx
       docker compose run --rm web alembic upgrade head
       docker compose up -d
       ```
     - Downtime yang terjadi hanya saat container di-restart (beberapa detik). *Zero downtime* sejati membutuhkan ≥2 replika di belakang load balancer dan belum menjadi target fase ini.
   - **Rollback**: deploy ulang image dengan tag SHA sebelumnya (`IMAGE_TAG=<sha> docker compose up -d`).

### 7.3 Manajemen Database & Ketahanan Data
- **Persistensi Data**: Database PostgreSQL, Qdrant, dan folder berkas upload (`media/`) disimpan pada **Docker Volume** di disk fisik server, terisolasi dari container aplikasi. Container dapat di-rebuild berulang kali tanpa kehilangan data pengadaan atau riwayat chat.
- **Backup Terjadwal**: `pg_dump` harian (cron host) ke direktori backup terpisah, retensi minimal 14 hari; uji restore minimal sekali per bulan.
- **Migrasi Non-Destruktif**: Migrasi schema via Alembic menerapkan penambahan kolom/tabel secara inkremental. Penghapusan/rename kolom dilakukan dalam dua tahap rilis (tambah kolom baru → migrasi data → hapus kolom lama).

### 7.4 Spesifikasi Konfigurasi GitHub Actions

#### `.github/workflows/ci.yml`
```yaml
name: CI ITeC Copilot (React Vite + FastAPI)

on:
  pull_request:
    branches: [ "main" ]
  push:
    branches: [ "main" ]

jobs:
  test-frontend:
    name: Lint & Build React Vite Frontend
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
          cache-dependency-path: 'frontend/package-lock.json'
      - run: npm ci
      - run: npm run lint
      - run: npm run build

  test-backend:
    name: Lint & Pytest Backend
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        ports: [ "5432:5432" ]
        options: >-
          --health-cmd "pg_isready -U test_user -d test_db"
          --health-interval 10s --health-timeout 5s --health-retries 5
    env:
      DATABASE_URL: postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db
      JWT_SECRET: ci-only-secret
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - uses: astral-sh/setup-uv@v6
      - name: Install Dependencies
        working-directory: backend
        run: uv sync --frozen
      - run: uv run ruff check .
        working-directory: backend
      - run: uv run pytest
        working-directory: backend
```

#### `.github/workflows/deploy.yml`
```yaml
name: Deploy ITeC Copilot

on:
  workflow_run:
    workflows: [ "CI ITeC Copilot (React Vite + FastAPI)" ]
    types: [ completed ]
    branches: [ "main" ]

permissions:
  contents: read
  packages: write

jobs:
  build-and-push:
    if: github.event.workflow_run.conclusion == 'success'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build & Push Backend Image
        uses: docker/build-push-action@v6
        with:
          context: ./backend
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/web:${{ github.sha }}
            ghcr.io/${{ github.repository }}/web:latest
      - name: Build & Push Nginx (Frontend) Image
        uses: docker/build-push-action@v6
        with:
          context: .
          file: ./frontend/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/nginx:${{ github.sha }}
            ghcr.io/${{ github.repository }}/nginx:latest

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.2.0   # versi dikunci, jangan @master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            cd /opt/pertamina-procurement
            export IMAGE_TAG=${{ github.sha }}
            docker compose pull web nginx
            docker compose run --rm web alembic upgrade head
            docker compose up -d
```

> Nama repositori di GHCR wajib huruf kecil; bila nama repo GitHub mengandung huruf besar, ganti `${{ github.repository }}` dengan nama image yang ditulis manual dalam huruf kecil.

---

## 8. Spesifikasi Infrastruktur Kontainerisasi (Docker & Docker Compose)

### 8.1 Arsitektur Multi-Kontainer

| Layanan (Service) | Image | Port Eksternal | Port Internal | Status | Peran & Tanggung Jawab |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **`nginx`** | Custom (`frontend/Dockerfile`, basis `nginx:1.27-alpine`) | `80`, `443` | `80`, `443` | Inti | Reverse proxy + TLS, menyajikan build React (`dist/` di dalam image), buffer upload 100MB, timeout AI 300s. |
| **`web`** | Custom (`backend/Dockerfile`, Python 3.12) | - | `8000` | Inti | FastAPI ASGI application (`uvicorn`), REST API + SSE. |
| **`db`** | `postgres:16-alpine` | - | `5432` | Inti | PostgreSQL untuk menyimpan pengguna, proyek, klausul, dan audit trail. |
| **`qdrant`** | `qdrant/qdrant:v1.12.4` | - | `6333` | Inti | Vector Database penyimpanan embeddings 86 Aturan Pedoman Pengadaan STK. Versi dikunci, jangan `latest`. |
| **`redis`** | `redis:7-alpine` | - | `6379` | Opsional (profil `worker`) | Message broker untuk antrean tugas Celery. |
| **`celery_worker`**| Sama dengan `web` | - | - | Opsional (profil `worker`) | Background worker generasi `.docx` & ekstraksi BoQ berat. |
| **`celery_beat`** | Sama dengan `web` | - | - | Opsional (profil `worker`) | Penjadwal tugas berkala (housekeeping 02.00 WIB, lihat 9.2). |

---

### 8.2 Spesifikasi Dockerfile

#### `backend/Dockerfile` (FastAPI + Celery)
Dependensi dipasang dari `pyproject.toml` + `uv.lock` (sama persis dengan lingkungan development).
```dockerfile
# Stage 1: Pasang dependensi dengan uv ke virtualenv /app/.venv
FROM python:3.12-slim AS backend-builder
COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1     UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Stage 2: Final Production Runtime Image
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends     libpq5     curl     && rm -rf /var/lib/apt/lists/*

# Akun pengguna non-root demi standar keamanan BUMN
RUN groupadd -r pertamina && useradd -r -g pertamina pertamina

COPY --from=backend-builder /app/.venv /app/.venv
COPY . .
RUN mkdir -p /app/media /app/output && chown -R pertamina:pertamina /app

USER pertamina
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s CMD curl -fs http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers", "--forwarded-allow-ips", "*"]
```

> Catatan: versi image `ghcr.io/astral-sh/uv` sebaiknya disamakan dengan versi uv yang dipakai saat membuat `uv.lock`, dan tambahkan `.dockerignore` berisi `.venv/`, `__pycache__/`, dan `.pytest_cache/` agar virtualenv lokal tidak ikut tersalin.

#### `frontend/Dockerfile` (Build React → Nginx)
Dibangun dengan *context* root repo agar konfigurasi `deploy/nginx/default.conf` ikut terbawa.
```dockerfile
# Stage 1: Build Frontend React dengan Vite
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Nginx menyajikan dist/ + reverse proxy
FROM nginx:1.27-alpine
COPY deploy/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html
```

Dengan pemisahan ini, build React hanya terjadi sekali (di image Nginx) dan server produksi tidak memerlukan Node.js maupun folder `frontend/dist` di host.

---

### 8.3 Blueprint `docker-compose.yml` (Opsi A: Decoupled Siap Deploy)

```yaml
services:
  # 1. Pangkalan Data Relasional
  db:
    image: postgres:16-alpine
    container_name: pertamina_postgres
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-pertamina_db}
      POSTGRES_USER: ${POSTGRES_USER:-pertamina_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD wajib diisi di .env}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - pertamina_internal_net

  # 2. Qdrant Vector Database (STK 86 Rules)
  qdrant:
    image: qdrant/qdrant:v1.12.4
    container_name: pertamina_qdrant
    restart: always
    environment:
      QDRANT__SERVICE__API_KEY: ${QDRANT_API_KEY:?QDRANT_API_KEY wajib diisi di .env}
    volumes:
      - qdrant_storage:/qdrant/storage
    networks:
      - pertamina_internal_net

  # 3. FastAPI ASGI Web Application
  web:
    image: ghcr.io/<org>/<repo>/web:${IMAGE_TAG:-latest}
    build:
      context: ./backend
    container_name: pertamina_fastapi
    restart: always
    volumes:
      - media_volume:/app/media
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      qdrant:
        condition: service_started
    networks:
      - pertamina_internal_net

  # 4. Nginx Edge Gateway & Frontend Server (berisi build React)
  nginx:
    image: ghcr.io/<org>/<repo>/nginx:${IMAGE_TAG:-latest}
    build:
      context: .
      dockerfile: frontend/Dockerfile
    container_name: pertamina_nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/certs:/etc/nginx/certs:ro
    depends_on:
      - web
    networks:
      - pertamina_internal_net

  # --- Layanan opsional: aktifkan dengan `docker compose --profile worker up -d` ---

  # 5. Redis Message Broker
  redis:
    image: redis:7-alpine
    container_name: pertamina_redis
    restart: always
    profiles: ["worker"]
    volumes:
      - redis_data:/data
    networks:
      - pertamina_internal_net

  # 6. Celery Worker (AI & Docx Generation)
  celery_worker:
    image: ghcr.io/<org>/<repo>/web:${IMAGE_TAG:-latest}
    container_name: pertamina_celery
    restart: always
    profiles: ["worker"]
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

  # 7. Celery Beat (Penjadwal Housekeeping)
  celery_beat:
    image: ghcr.io/<org>/<repo>/web:${IMAGE_TAG:-latest}
    container_name: pertamina_celery_beat
    restart: always
    profiles: ["worker"]
    command: celery -A app.services.tasks beat -l info
    env_file:
      - .env
    depends_on:
      - redis
    networks:
      - pertamina_internal_net

# Persistensi Data Fisik Server
volumes:
  pgdata:
  redis_data:
  qdrant_storage:
  media_volume:

networks:
  pertamina_internal_net:
    driver: bridge
```

Catatan perubahan dibanding draf sebelumnya:
- Atribut `version:` dihapus (sudah usang di Docker Compose v2).
- Password database & API key Qdrant **wajib** dari `.env` (sintaks `${VAR:?pesan}` membuat compose gagal bila kosong), tidak ada default seperti `pertamina_pass123`.
- Healthcheck memakai variabel lingkungan container (`$${POSTGRES_USER}`), tidak di-hardcode.
- Berkas `media/` **tidak** disajikan langsung oleh Nginx; unduhan `.docx` selalu melewati endpoint FastAPI yang memeriksa login & hak akses.

---

### 8.4 Konfigurasi `deploy/nginx/default.conf`

```nginx
# Redirect HTTP -> HTTPS
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    http2 on;
    server_name _;

    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    client_max_body_size 100M;
    server_tokens off;

    # Header keamanan dasar
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header Content-Security-Policy "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'" always;

    # 1. Sajikan Hasil Build React Vite (dist/)
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Aset hasil hashing Vite (nama file berubah setiap build) -> aman di-cache lama
    location /assets/ {
        root /usr/share/nginx/html;
        expires 1y;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    # 2. Teruskan API Call ke Backend FastAPI
    location /api/ {
        proxy_pass http://web:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Pengaturan khusus AI Streaming (SSE) & Dokumen Berat
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_connect_timeout 10s;
        proxy_buffering off;
        proxy_cache off;
    }

    # 3. Swagger (/docs, /openapi.json) TIDAK diekspos di produksi.
    #    FastAPI hanya mengaktifkannya bila DEBUG=True; untuk akses darurat gunakan
    #    SSH tunnel ke port 8000 container web.
}
```

Catatan: `index.html` sengaja **tidak** di-cache lama agar pengguna selalu mendapat versi terbaru setelah deploy; hanya folder `/assets/` (nama file ber-hash) yang di-cache `immutable`.

---

### 8.5 Perintah Operasional Docker (One-Command Startup)

```bash
# 1. Menjalankan ekosistem inti (nginx, web, db, qdrant)
docker compose up -d --build

# 1b. Bila pemrosesan latar belakang sudah dibutuhkan
docker compose --profile worker up -d

# 2. Menjalankan Migrasi Database di Dalam Kontainer
docker compose exec web alembic upgrade head

# 3. Membuat akun admin awal & seed 86 aturan STK
docker compose exec web python -m app.scripts.seed

# 4. Memeriksa Log Status Kontainer
docker compose logs -f web
```

---

## 9. Tata Kelola Keamanan Data & Pemeliharaan Sistem (Security Governance & Automated Housekeeping)

### 9.1 Manajemen Rahasia & Kebijakan Nol Kebocoran Kredensial (*Secrets Management*)

1. **Penegakan Aturan `.gitignore`**:
   * File `.env` yang berisi *kunci API produksi*, *password database*, *JWT secret*, dan *kredensial Qdrant* **dilarang keras** di-commit ke repositori Git.
   * File `.gitignore` wajib mencantumkan:
     ```text
     .env
     .env.local
     *.log
     media/
     output/
     deploy/certs/
     __pycache__/
     .pytest_cache/
     .venv/
     node_modules/
     dist/
     ```
2. **Penyediaan Berkas Acuan `.env.example`**:
   * Pengembang baru menyalin dari `.env.example`:
     ```env
     DEBUG=False
     POSTGRES_DB=pertamina_db
     POSTGRES_USER=pertamina_user
     POSTGRES_PASSWORD=ganti_dengan_password_kuat
     DATABASE_URL=postgresql+asyncpg://pertamina_user:ganti_dengan_password_kuat@db:5432/pertamina_db
     QDRANT_CLUSTER_ENDPOINT=http://qdrant:6333
     QDRANT_API_KEY=ganti_dengan_api_key_acak
     OPENROUTER_API_KEY=sk-or-v1-placeholder
     LLM_PROVIDER=openrouter
     JWT_SECRET=ganti_dengan_string_acak_minimal_32_karakter
     JWT_ACCESS_TTL_MINUTES=30
     CORS_ORIGINS=http://localhost:5173
     MEDIA_ROOT=/app/media
     OUTPUT_DIR=/app/output
     ADMIN_INITIAL_PASSWORD=ganti_saat_seed
     CELERY_BROKER_URL=redis://redis:6379/0
     CELERY_RESULT_BACKEND=redis://redis:6379/0
     ```
3. **Injeksi Kredensial CI/CD via GitHub Secrets**:
   * Seluruh kredensial akses server (`SERVER_HOST`, `SERVER_USER`, `SERVER_SSH_KEY`) diinjeksikan secara terenkripsi saat pipeline berjalan tanpa pernah terekspos di log pengujian. Gunakan *GitHub Environment* `production` dengan reviewer wajib agar deploy memerlukan persetujuan.
4. **Data Contoh / Dummy**:
   * Data demo di frontend, seed, dan test **hanya boleh berisi data fiktif** (nama pejabat, NPWP vendor, nomor kontrak). Data pengadaan asli tidak boleh masuk ke repositori.

---

### 9.2 Otomasi Pembersihan Berkas Sementara (*Automated Housekeeping Task*)

Aktivitas penyusunan dokumen tender menghasilkan berkas *scratch*, pecahan halaman PDF, dan draf revisi di folder `output/`. Jika dibiarkan, media penyimpanan server akan penuh (*disk saturation*).

1. **Jadwal Pembersihan Berkala via Celery Beat** (atau cron host bila profil `worker` belum aktif):
   * Menjadwalkan tugas otomatis yang berjalan setiap hari pukul **02.00 WIB**:
     ```python
     # backend/app/services/tasks.py
     import time
     from pathlib import Path

     from celery import Celery
     from celery.schedules import crontab

     from app.config import settings

     celery_app = Celery("pertamina", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)
     celery_app.conf.timezone = "Asia/Jakarta"
     celery_app.conf.beat_schedule = {
         "cleanup-output-harian": {
             "task": "app.services.tasks.cleanup_expired_temporary_files",
             "schedule": crontab(hour=2, minute=0),
         },
     }

     @celery_app.task
     def cleanup_expired_temporary_files():
         """
         Menghapus berkas sementara di OUTPUT_DIR yang berusia > 7 hari.
         Mencegah disk kepenuhan dan menjamin kepatuhan retensi data.
         """
         temp_dir = Path(settings.OUTPUT_DIR)  # path absolut dari .env, bukan relatif
         retention_seconds = 7 * 24 * 3600  # 7 Hari
         now = time.time()
         deleted_count = 0

         if temp_dir.is_dir():
             for filepath in temp_dir.rglob("*"):
                 if filepath.is_file() and now - filepath.stat().st_mtime > retention_seconds:
                     filepath.unlink(missing_ok=True)
                     deleted_count += 1
         return f"Housekeeping selesai: {deleted_count} file kedaluwarsa dibersihkan."
     ```
2. **Kepatuhan Privasi Data Pengadaan**:
   * Berkas sementara yang dihapus otomatis memastikan dokumen acuan vendor tidak tertimbun selamanya di disk server tanpa pengawasan.
   * Folder `media/` (upload & dokumen terbit) **tidak** ikut dibersihkan otomatis karena terikat pada data proyek dan audit; penghapusannya mengikuti kebijakan retensi arsip pengadaan.

---

### 9.3 Autentikasi & Otorisasi

1. **Login**: `POST /api/auth/login` menerima username + password, memverifikasi hash argon2, lalu mengembalikan *access token* JWT (masa berlaku 30 menit) dan *refresh token* (7 hari, disimpan di cookie `HttpOnly; Secure; SameSite=Strict`).
2. **Rate limiting**: maksimal 5 percobaan login gagal per 15 menit per username/IP untuk mencegah *brute force*.
3. **Otorisasi**: setiap route memakai dependency `get_current_user` + `require_role(...)` sesuai matriks 4.4. Untuk peran `FPP`, backend juga memeriksa kepemilikan (`project.user_id == current_user.id`).
4. **Unduhan dokumen**: file `.docx` hanya dapat diunduh lewat endpoint yang memeriksa hak akses; path file tidak pernah diterima langsung dari input user (mencegah *path traversal*).
5. **Integrasi SSO korporat** (opsional, tahap lanjut): skema JWT di atas dapat diganti/ditambah OIDC tanpa mengubah model `app_user` (tambahkan kolom `sso_subject`).

### 9.4 Keamanan Input & Output (Upload, XSS, LLM)

1. **Validasi upload di backend**: ekstensi & MIME (`.pdf`, `.xlsx`, `.xls`), ukuran maks. 100 MB, nama file disimpan sebagai UUID acak, hash SHA-256 untuk deteksi duplikat.
2. **Pencegahan XSS di frontend React**:
   * Teks user, nama berkas, dan output LLM **selalu** dirender via JSX (`{text}`) yang otomatis di-escape.
   * `dangerouslySetInnerHTML` dilarang, kecuali untuk Markdown balasan AI yang sudah dikonversi lalu disanitasi dengan **DOMPurify**.
   * Event handler memakai prop React (`onClick`), bukan atribut `onclick="..."` berisi string.
3. **Prompt injection**: isi dokumen yang diunggah dianggap data, bukan instruksi. Tool-call AI yang mengubah dokumen (misal `update_clause`) hanya diterapkan setelah dikonfirmasi user di canvas, dan setiap penerapan dicatat di `AuditTrail`.
4. **Logging**: jangan menulis isi dokumen, token JWT, atau API key ke log aplikasi.
