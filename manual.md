# Manual Setup dari Awal: ITeC (Pertamina Procurement AI Copilot)

Dokumen ini menjelaskan langkah demi langkah memasang dan menjalankan aplikasi ITeC di komputer baru, mulai dari nol.

**Stack:** React 19 + Vite + Tailwind + Zustand (frontend) · FastAPI + SQLAlchemy async + Alembic + LangGraph (backend) · PostgreSQL 16 · Qdrant · Nginx · Docker.

Ada dua cara menjalankan:

| Cara | Untuk apa | Yang perlu dipasang |
| :--- | :--- | :--- |
| **A. Docker penuh** (disarankan) | Menjalankan / demo aplikasi | Git, Docker Desktop |
| **B. Mode development** | Mengubah kode (hot reload) | Git, Docker Desktop, uv, Node.js 24 |

---

## Daftar Isi

1. [Persiapan perangkat](#1-persiapan-perangkat)
2. [Instalasi perangkat lunak](#2-instalasi-perangkat-lunak)
3. [Ambil kode](#3-ambil-kode)
4. [Siapkan folder dataset](#4-siapkan-folder-dataset)
5. [Buat berkas `.env`](#5-buat-berkas-env)
6. [Cara A: Docker penuh](#6-cara-a-docker-penuh)
7. [Cara B: Mode development](#7-cara-b-mode-development)
8. [Verifikasi instalasi](#8-verifikasi-instalasi)
9. [Perintah harian](#9-perintah-harian)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Persiapan perangkat

| Kebutuhan | Minimum | Catatan |
| :--- | :--- | :--- |
| RAM | 16 GB | Docker perlu jatah ±8 GB (model embedding & Docling berat) |
| Disk kosong | ±15 GB | Image backend ±3,2 GB + model yang diunduh saat pertama dipakai |
| OS | Windows 10/11, macOS, Linux | Windows memakai WSL 2 untuk Docker Desktop |
| Internet | Wajib | LLM (OpenRouter) dan unduhan model |

Yang harus diminta ke pemilik proyek:

1. Akses repository GitHub `Flax9/Agenticv3`.
2. **API key OpenRouter** (`OPENROUTER_API_KEY`). Jangan dibagikan lewat chat publik.
3. Akses ke **folder dataset** (Google Drive / OneDrive).
4. Cara B saja: endpoint & API key **Qdrant Cloud** tim, atau pakai Qdrant lokal.

---

## 2. Instalasi perangkat lunak

### 2.1 Git
Unduh dari https://git-scm.com/downloads, lalu verifikasi:
```bash
git --version
```

### 2.2 Docker Desktop
1. Unduh dari https://www.docker.com/products/docker-desktop/ dan pasang.
2. Windows: aktifkan WSL 2 bila diminta, lalu restart.
3. Buka **Settings → Resources**, set memori minimal **8 GB**.
   (Bila WSL 2 tanpa pengaturan itu, edit `%UserProfile%\.wslconfig`: `[wsl2]` lalu `memory=8GB`.)
4. Pastikan Docker menyala, lalu verifikasi:
```bash
docker --version
docker compose version
```

### 2.3 uv dan Node.js (khusus Cara B)
- **uv** (sekaligus memasang Python 3.12): https://docs.astral.sh/uv/getting-started/installation/
  ```powershell
  # Windows PowerShell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
  ```bash
  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Node.js 24**: https://nodejs.org/

Verifikasi:
```bash
uv --version
node --version
npm --version
```

### 2.4 Klien Google Drive / OneDrive Desktop
Dipakai untuk menyinkronkan folder dataset ke laptop.

---

## 3. Ambil kode

```bash
git clone https://github.com/Flax9/Agenticv3.git
cd Agenticv3
```

> **Jangan ubah `.gitattributes`.** Berkas `backend/docker-entrypoint.sh` harus berakhiran baris **LF** karena berjalan di container Linux.
> Jika container `web` gagal start dengan `exec ... no such file or directory`: jalankan `git config core.autocrlf input`, hapus folder repo, lalu clone ulang.

---

## 4. Siapkan folder dataset

1. Pasang & login klien Google Drive / OneDrive dengan akun yang punya akses.
2. Jadikan folder dataset **tersedia offline** (Google Drive: klik kanan → *Available offline*; OneDrive: *Always keep on this device*). Docker tidak bisa membaca berkas placeholder online.
3. Catat path lengkapnya, mis. `C:/Users/nama/Google Drive/ITeC Dataset`. Gunakan garis miring `/`.

Struktur yang diharapkan:

```text
ITeC Dataset/
├── rks_kb/          → knowledge base RKS
├── contract_kb/     → knowledge base Kontrak
├── amendment_kb/    → knowledge base Amendemen
└── (folder lain)/   → berkas acuan (mis. BoQ), dipilih lewat tombol 📎 di chat
```

Jika dataset belum tersedia, lewati langkah ini. Aplikasi memakai folder kosong `./dataset`.

---

## 5. Buat berkas `.env`

Dari root repo:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```
```bash
# macOS / Linux / Git Bash
cp .env.example .env
```

Edit `.env`, isi minimal:

| Variabel | Isi |
| :--- | :--- |
| `OPENROUTER_API_KEY` | API key dari pemilik proyek |
| `POSTGRES_PASSWORD` | Password bebas, min. 12 karakter. **Samakan** di `DATABASE_URL` & `TEST_DATABASE_URL` |
| `JWT_SECRET` | String acak min. 32 karakter |
| `ADMIN_INITIAL_PASSWORD` | Password awal akun `admin`, min. 10 karakter |
| `QDRANT_LOCAL_API_KEY` | String acak (Cara A) |
| `DATASET_HOST_DIR` | Path dataset dari langkah 4 (Cara A). Hapus `#` di depannya |
| `DATASET_DIR` | Path dataset yang sama (Cara B). Hapus `#` di depannya |
| `HTTP_PORT` | Ganti ke `8088` bila port 80 terpakai |
| `QDRANT_CLUSTER_ENDPOINT`, `QDRANT_API_KEY` | Qdrant Cloud tim (Cara B saja) |
| `COOKIE_SECURE` | `false` untuk http://localhost; `true` jika HTTPS |

Membuat string acak:

```powershell
# Windows PowerShell
-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 40 | ForEach-Object {[char]$_})
```
```bash
# macOS / Linux / Git Bash
openssl rand -hex 32
```

> **Jangan pernah meng-commit `.env`.** Sudah masuk `.gitignore`.

---

## 6. Cara A: Docker penuh

Layanan: `nginx` (frontend + gateway), `web` (FastAPI), `db` (PostgreSQL), `qdrant`.

### 6.1 Build & jalankan
Pastikan Docker Desktop menyala, lalu dari root repo:

```bash
docker compose up -d --build
```

Build pertama ±10–20 menit. Tutup aplikasi berat lain selama build. Migrasi database berjalan otomatis saat `web` start.

Cek status:
```bash
docker compose ps
```
Keempat container harus `Up`; `db` dan `web` harus `(healthy)`.

### 6.2 Buat akun
```bash
# Admin (username: admin, password: ADMIN_INITIAL_PASSWORD)
docker compose exec web python -m app.scripts.seed admin

# Akun lain (role: ADMIN, PROCUREMENT, FPP, APPROVER, AUDITOR)
docker compose exec web python -m app.scripts.seed user --username budi --email budi@contoh.id --nama "Budi" --role FPP
```

### 6.3 Buka aplikasi
1. Buka `http://localhost` (atau `http://localhost:8088` bila `HTTP_PORT` diganti).
2. Login sebagai `admin`.
3. Buka **Knowledge Base → Sinkronkan Sekarang** untuk memasukkan isi dataset ke Qdrant. Qdrant awalnya **kosong**.

> Pertanyaan chat pertama ±3 menit (unduh model embedding, hanya sekali, disimpan di volume `model_cache`). Berikutnya ±30 detik. Membaca BoQ Excel besar bisa ±8 menit.

### 6.4 Mode HTTPS (opsional, setelah punya domain)
Ikuti `deploy/certs/README.md`: taruh `fullchain.pem` & `privkey.pem` di `deploy/certs/`, set `COOKIE_SECURE=true`, lalu:
```bash
docker compose -f docker-compose.yml -f compose.https.yml up -d --build
```

---

## 7. Cara B: Mode development

Backend & frontend jalan langsung di laptop; hanya PostgreSQL di Docker.

### 7.1 PostgreSQL
```bash
docker compose -f compose.dev.yml --env-file .env up -d
```
Membuat database `pertamina_db` dan `pertamina_test`, hanya diakses dari `127.0.0.1:5432`.

### 7.2 Qdrant (pilih salah satu)
- **Qdrant Cloud tim:** isi `QDRANT_CLUSTER_ENDPOINT` dan `QDRANT_API_KEY` di `.env`.
- **Qdrant lokal:**
  ```bash
  docker run -d --name itec_dev_qdrant -p 127.0.0.1:6333:6333 -e QDRANT__SERVICE__API_KEY=isi_string_acak qdrant/qdrant:v1.19.2
  ```
  Di `.env`: `QDRANT_CLUSTER_ENDPOINT=http://localhost:6333` dan `QDRANT_API_KEY=isi_string_acak`.

### 7.3 Backend
```bash
cd backend
uv sync                                          # pasang Python 3.12 + dependensi (±5–10 menit)
uv run alembic upgrade head                      # migrasi database
uv run python -m app.scripts.seed admin          # buat akun admin
uv run uvicorn app.main:app --reload --port 8000
```
Backend membaca `.env` dari **root repo**, bukan `backend/`.
Dokumentasi API (saat `DEBUG=True`): `http://127.0.0.1:8000/docs`.

### 7.4 Frontend
Di terminal baru:
```bash
cd frontend
npm ci
npm run dev
```
Buka `http://localhost:5173`. Vite meneruskan `/api` ke backend port 8000.

### 7.5 Pemeriksaan sebelum commit (sama dengan CI)
```bash
# backend (PostgreSQL dev harus menyala)
cd backend
uv run ruff check .
uv run ruff format --check .
uv run alembic check
uv run pytest

# frontend
cd ../frontend
npm run lint
npm run build
```

---

## 8. Verifikasi instalasi

| Pemeriksaan | Cara | Hasil yang diharapkan |
| :--- | :--- | :--- |
| Health backend | Buka `/api/health` (A: `http://localhost/api/health`; B: `http://127.0.0.1:8000/api/health`) | JSON status OK, `llm_configured: true` |
| Login | Masuk sebagai `admin` | Masuk ke halaman Copilot |
| Daftar dataset | Klik tombol 📎 di chat | Berkas dari folder dataset tampil |
| Knowledge base | Knowledge Base → Sinkronkan Sekarang | Sinkronisasi sukses |
| Chat | Kirim pertanyaan | Jawaban merujuk dokumen |

---

## 9. Perintah harian

Cara A:
```bash
docker compose ps                  # status
docker compose logs -f web         # log backend (Ctrl+C keluar)
docker compose stop                # matikan sementara
docker compose start               # nyalakan lagi
docker compose down                # hapus container (data tetap di volume)
git pull && docker compose up -d --build   # update ke versi terbaru
```

> `docker compose down -v` **menghapus seluruh data** (database, knowledge base, draf, model). Gunakan hanya untuk mulai dari nol.

Backup database:
```bash
docker compose exec db pg_dump -U pertamina_user pertamina_db > backup.sql
```

---

## 10. Troubleshooting

| Gejala | Penyebab & solusi |
| :--- | :--- |
| `POSTGRES_PASSWORD wajib diisi` / `QDRANT_LOCAL_API_KEY wajib diisi` | `.env` belum dibuat/kosong. Ulangi langkah 5. |
| `port is already allocated` (port 80) | Isi `HTTP_PORT=8088` di `.env`, jalankan `docker compose up -d` lagi. |
| Build berhenti / Docker macet | Memori kurang. Tutup aplikasi lain, naikkan memori Docker, ulangi build (cache terpakai). |
| Container `web` terus restart | Lihat `docker compose logs web`. Biasanya `.env` salah atau CRLF di `docker-entrypoint.sh` (lihat langkah 3). |
| Daftar dataset kosong | `DATASET_HOST_DIR` salah/kosong, atau berkas belum offline. Jalankan `docker compose up -d` setelah ubah `.env`. |
| Jawaban chat umum, tak merujuk dokumen | Knowledge base belum disinkronkan. |
| Chat pertama sangat lama | Normal: model diunduh (±3 menit, sekali). |
| `llm_configured: false` di `/api/health` | `OPENROUTER_API_KEY` kosong. |
| Login ditolak berulang | Akun dikunci 15 menit (`LOGIN_LOCKOUT_MINUTES`). Tunggu atau restart `web`. |
| Agent mulai dari awal setelah restart | Batasan saat ini: progres agent di memori. Riwayat pesan tetap ada. |
| `uv sync` gagal di Windows | Pastikan koneksi internet stabil dan jalankan ulang; torch versi CPU dari PyPI. |
| Frontend tidak bisa memanggil API (Cara B) | Pastikan backend jalan di port 8000 dan `.env` ada di root repo. |

---

## Struktur folder

```text
.
├── backend/                 FastAPI, model DB, migrasi Alembic, modul AI (app/services/)
├── frontend/                React + Vite
├── frontend_vanilla/        Prototipe HTML/CSS/JS (acuan visual)
├── deploy/
│   ├── nginx/               konfigurasi Nginx (HTTP & HTTPS)
│   ├── certs/               sertifikat TLS (tidak di-commit)
│   └── postgres/            skrip pembuatan database test
├── docker-compose.yml       Cara A: semua layanan
├── compose.https.yml        tambahan mode HTTPS
├── compose.dev.yml          Cara B: PostgreSQL saja
├── .env.example             contoh konfigurasi
└── .github/workflows/ci.yml pemeriksaan otomatis GitHub
```
