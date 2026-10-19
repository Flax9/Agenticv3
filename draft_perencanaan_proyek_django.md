# Draft Perencanaan Proyek: Pertamina Procurement AI Copilot & Live Canvas
**Arsitektur Modern Django Monolith (Template & Static) + ASGI + Celery Worker + Nginx**

---

## 1. Ringkasan Eksekutif & Tujuan Proyek

Proyek ini bertujuan mengintegrasikan antarmuka frontend modern **`agenticv3`** (berbasis *Claude-style Live Canvas*, *Progress Drawer*, dan *Vertical Docked Tab*) dengan backend **Django 5.x** modern. Sistem ini menggabungkan mesin RAG dan generator dokumen pengadaan dari `Agentic_Rag_Pertamina_camp` untuk menghasilkan dokumen pengadaan resmi PT Pertamina Patra Niaga (IKPP Versi 2.0 40 Poin, RKS, Kontrak Definitif, dan Amendemen) yang patuh terhadap Pedoman No. A03-001/PNG200000/2024-S9.

---

## 2. Arsitektur Sistem Terpadu

```mermaid
graph TD
    Client["Browser Pengguna (agenticv3 UI)"] -->|Port 80/443| Nginx["Nginx Reverse Proxy & Static Cache"]
    
    subgraph "Edge / Ingress Layer"
        Nginx -->|Static Assets CSS/JS| StaticDisk["Static Files Cache (sendfile)"]
        Nginx -->|Proxy Buffering & SSL| ASGI["Django 5 ASGI Server (Uvicorn)"]
    end

    subgraph "Application Layer (Django 5)"
        ASGI --> Views["View & API Controllers"]
        Views --> Auth["Django Auth & Permissions"]
        Views --> ORM["Django ORM (PostgreSQL / SQLite)"]
        Views --> TaskQueue["Celery Task Dispatcher"]
    end

    subgraph "Worker & AI Engine Layer"
        TaskQueue --> Redis["Redis Message Broker & Cache"]
        Redis --> Celery["Celery Worker"]
        Celery --> RAG["RAG Engine & Summarizer"]
        Celery --> DocxGen["Docx Generator (python-docx)"]
        RAG --> Qdrant["Qdrant Vector DB (86 STK Rules)"]
        RAG --> LLM["LLM API (OpenRouter Qwen / Internal)"]
    end

    subgraph "Storage Layer"
        Celery --> MediaDisk["Media Storage (BoQ Uploads & Generated .DOCX)"]
        ORM --> DB[(Database)]
    end
```

---

## 3. Struktur Direktori Proyek Target

```text
pertamina_procurement/
│
├── manage.py                              # Entrypoint Django
├── requirements.txt                       # Dependensi Python
├── .env                                   # Kunci API, Qdrant, Redis, Database
├── Dockerfile                             # Build image Django + Worker
├── docker-compose.yml                     # Orkestrasi Nginx, Web, Celery, Redis, Qdrant
│
├── deploy/                                # Konfigurasi Server
│   ├── nginx/
│   │   └── default.conf                   # Reverse proxy, buffer upload besar, timeout 300s
│   └── supervisord.conf                   # (Opsional) jika multi-process dalam satu VM
│
├── core/                                  # Django Project Root
│   ├── __init__.py
│   ├── settings.py                        # ASGI, WhiteNoise (Plan B), Database, Celery
│   ├── urls.py                            # Master URL Routing
│   ├── asgi.py                            # ASGI Handler untuk Async & Streaming
│   └── wsgi.py
│
├── templates/                             # Integrasi Frontend agenticv3
│   └── index.html                         # Template utama (dengan tag {% load static %})
│
├── static/                                # Aset Frontend agenticv3
│   ├── css/
│   │   ├── main.css                       # Layout, topbar, restore tab vertikal
│   │   ├── canvas.css                     # Live Canvas review dokumen
│   │   └── chat.css                       # Chat bubble, cards, drawer
│   ├── js/
│   │   ├── state.js                       # Store reactive state
│   │   ├── api.js                         # Fetch client (dengan CSRF token helper)
│   │   ├── chat.js                        # Controller interaksi chat & drawer
│   │   ├── canvas.js                      # Controller editor review dokumen
│   │   └── app.js                         # Bootstrap aplikasi
│   └── images/
│
├── apps/                                  # Modul Aplikasi Bisnis
│   ├── procurement/                       # Modul Manajemen Tender & API Endpoints
│   │   ├── models.py                      # TenderProject, DocumentDraft, ChatHistory
│   │   ├── views.py                       # def index(request)
│   │   ├── api_views.py                   # Async views untuk ekstraksi & ekspor
│   │   ├── urls.py
│   │   └── admin.py                       # Panel administrasi dokumen & kepatuhan
│   │
│   └── rag_engine/                        # Modul AI & RAG Pipeline (Porting)
│       ├── config.py                      # Konfigurasi model & koleksi STK
│       ├── vector_store.py                # Wrapper Qdrant
│       ├── summarizer.py                  # Parser PDF & BoQ Excel
│       ├── tender_generator.py            # Generator 40 Poin IKPP
│       ├── rks_generator.py               # Generator RKS & CSMS
│       ├── contract_generator.py          # Generator Kontrak & Amendemen
│       └── tasks.py                       # Celery tasks untuk background generation
│
└── media/                                 # Penyimpanan Berkas Dinamis
    ├── uploads/                           # Berkas BoQ / RKS acuan
    └── generated_docs/                    # Berkas .docx hasil generate
```

---

## 4. Skema Database (Django ORM Models)

1. **`TenderProject`**:
   - `id`: UUID (Primary Key)
   - `nama_pengadaan`: CharField(255)
   - `tipe_dokumen`: CharField (`tender`, `rks`, `kontrak`, `amendemen`)
   - `hps_total`: DecimalField
   - `resiko_csms`: CharField (`Tinggi`, `Sedang`, `Rendah`)
   - `current_step`: IntegerField (1: BoQ, 2: Ekstraksi, 3: Verifikasi, 4: Terbit)
   - `created_at`, `updated_at`: DateTimeField

2. **`DocumentDraft`**:
   - `project`: ForeignKey(`TenderProject`)
   - `versi`: CharField (`v1.0`, `v2.0`)
   - `file_docx`: FileField(upload_to='generated_docs/')
   - `content_json`: JSONField (Struktur 40 pasal IKPP & matriks)
   - `skor_kepatuhan_stk`: IntegerField (0 - 100)
   - `is_active`: BooleanField

3. **`ChatMessage`**:
   - `project`: ForeignKey(`TenderProject`)
   - `role`: CharField (`user`, `assistant`, `system`)
   - `content`: TextField
   - `tool_calls`: JSONField (menyimpan jejak revisi klausul otomatis)
   - `created_at`: DateTimeField

4. **`KnowledgeReference`**:
   - `kode_pedoman`: CharField (`A03-001/PNG200000/2024-S9`)
   - `nama_aturan`: CharField
   - `qdrant_point_id`: CharField

---

## 5. Tahapan Implementasi (Rencana Kerja 5 Fase)

### Fase 1: Inisialisasi & Skafolding Django Monolith
- [ ] Inisialisasi Django 5 project (`pertamina_procurement`) dengan dependensi inti.
- [ ] Pindahkan `agenticv3/index.html` ke `templates/index.html`, tambahkan tag `{% load static %}`.
- [ ] Pindahkan folder `css/` dan `js/` ke `static/`.
- [ ] Pasang **WhiteNoise** di `settings.py` sebagai *Plan B* (garansi static files berjalan instan tanpa Nginx).
- [ ] Sesuaikan `api.js` agar secara otomatis membaca cookie `csrftoken` dan menyuntikkannya ke header `X-CSRFToken`.

### Fase 2: Implementasi Database & Model ORM
- [ ] Definisikan skema model `TenderProject`, `DocumentDraft`, dan `ChatMessage` di `apps/procurement/models.py`.
- [ ] Jalankan migrasi awal (`python manage.py makemigrations && python manage.py migrate`).
- [ ] Daftarkan model ke Django Admin (`admin.py`) untuk kemudahan audit dan inspeksi data dokumen.

### Fase 3: Porting Modul AI & RAG Pipeline
- [ ] Pindahkan logic dari `Agentic_Rag_Pertamina_camp` (`RAG/`, `tender/`, `contract/`) ke `apps/rag_engine/`.
- [ ] Implementasikan endpoint Async di `apps/procurement/api_views.py`:
  - `POST /api/extract-tender-metadata/`
  - `POST /api/generate-tender/`
  - `POST /api/generate-rks/`
  - `POST /api/generate-kontrak/`
  - `POST /api/generate-amendemen/`
  - `GET /api/health/`
- [ ] Verifikasi format unduhan `.docx` dengan template styling resmi Pertamina.

### Fase 4: Konfigurasi Celery Worker & Streaming Token
- [ ] Pasang Celery dengan Redis broker untuk pemrosesan file `.docx` berat.
- [ ] Hubungkan indikator progres frontend (*Progress Drawer* & *Live Sync Badge*) dengan status task worker.
- [ ] (Opsional) Implementasikan `StreamingHttpResponse` untuk streaming token jawaban AI per kata.

### Fase 5: Dockerization & Konfigurasi Nginx Siap Deploy
- [ ] Susun `Dockerfile` multi-stage untuk Django ASGI & Celery.
- [ ] Buat file konfigurasi `nginx.conf`:
  - `client_max_body_size 100M;` (upload BoQ besar aman).
  - `proxy_read_timeout 300s;` (mencegah timeout saat LLM berpikir).
  - `proxy_buffering off;` (mendukung streaming AI instan).
- [ ] Buat `docker-compose.yml` yang menghubungkan service: `nginx`, `web`, `celery_worker`, `redis`, dan `qdrant`.
- [ ] Uji coba skenario *end-to-end* (Upload BoQ -> Ekstraksi AI -> Edit Canvas -> Generate Dokumen -> Unduh .docx).

---

## 6. Matrix Mitigasi Risiko & Cadangan Solusi

| Potensi Kendala | Risiko | Solusi Mitigasi |
| :--- | :--- | :--- |
| **Server belum siap Docker** | Deployment tertunda | Aktifkan **WhiteNoise + Gzip/Brotli** di `settings.py`. Aplikasi langsung bisa dijalankan dengan `python manage.py runserver` atau Gunicorn/Uvicorn tunggal. |
| **Ekstraksi BoQ Excel memakan waktu lama** | Browser mengalami timeout | Celery worker menangani parsing di background dan mengirimkan sinyal progres ke frontend. |
| **CSRF Token Blocking pada AJAX Fetch** | Request `POST` ditolak (HTTP 403) | `api.js` dilengkapi helper fungsi ekstraksi cookie CSRF Django secara otomatis. |
| **Koneksi LLM terputus di tengah jalan** | Dokumen gagal terbentuk utuh | Logika *retry mechanism* (maksimal 3 kali) pada `rag_engine` sebelum melaporkan error ke chat window. |
