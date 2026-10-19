# ITeC: Copilot Penyusunan Dokumen Pengadaan

Aplikasi web berbasis chat untuk menyusun draf dokumen pengadaan (RKS, Tender, Kontrak, Amendemen).
Pengguna yang belum berpengalaman cukup menjawab pertanyaan asisten, lalu draf `.docx` dibuat otomatis.
Asisten membaca knowledge base dari folder Google Drive / OneDrive.

| Bagian | Teknologi |
| :--- | :--- |
| Frontend | React 19 + Vite + Tailwind + Zustand (`frontend/`) |
| Backend | FastAPI + SQLAlchemy async + Alembic + LangGraph (`backend/`) |
| Database | PostgreSQL 16 |
| Knowledge base | Qdrant (vector store) |
| Gateway | Nginx (menyajikan frontend & meneruskan `/api` ke backend) |

Panduan ini untuk menyiapkan aplikasi di laptop baru. Ada dua cara:

- **[Cara A: Docker penuh](#cara-a-docker-penuh-disarankan)** (disarankan). Cocok untuk menjalankan atau mendemokan aplikasi. Tidak perlu memasang Python maupun Node.
- **[Cara B: Mode development](#cara-b-mode-development)**. Cocok untuk mengubah kode, karena hasil perubahan langsung terlihat (hot reload).

Rancangan lengkap ada di `draft_perencanaan_proyek_ITeC.md`, dan pertanyaan untuk tim AI ada di `pertanyaan penanggung jawab ai.md`.

---

## 1. Kebutuhan laptop

| Kebutuhan | Minimum | Catatan |
| :--- | :--- | :--- |
| RAM | 16 GB | Docker Desktop perlu jatah ±8 GB. Model embedding & pembaca dokumen (Docling) cukup berat. |
| Disk kosong | ±15 GB | Image backend ±3,2 GB + model yang diunduh saat pertama kali dipakai. |
| OS | Windows 10/11, macOS, atau Linux | Di Windows, Docker Desktop memakai WSL 2. |
| Internet | Wajib | Untuk LLM (OpenRouter) dan unduhan model pertama kali. |

Perangkat lunak:

| Perangkat | Cara A | Cara B | Unduh |
| :--- | :---: | :---: | :--- |
| Git | ✅ | ✅ | https://git-scm.com/downloads |
| Docker Desktop | ✅ | ✅ (hanya untuk PostgreSQL) | https://www.docker.com/products/docker-desktop/ |
| uv (pengelola Python, sekaligus memasang Python 3.12) | – | ✅ | https://docs.astral.sh/uv/getting-started/installation/ |
| Node.js 24 | – | ✅ | https://nodejs.org/ |
| Klien Google Drive / OneDrive untuk desktop | ✅ | ✅ | Untuk menyinkronkan folder dataset ke laptop |

> **Windows:** setelah memasang Docker Desktop, buka **Settings → Resources** dan pastikan memori minimal 8 GB.
> Bila memakai WSL 2 tanpa pengaturan itu, batasnya diatur di `%UserProfile%\.wslconfig` (`[wsl2]` → `memory=8GB`).

Minta kepada pemilik proyek:
1. Akses ke repository GitHub `Flax9/Agenticv3`.
2. **API key OpenRouter** (`OPENROUTER_API_KEY`). Kunci ini jangan dikirim lewat chat publik.
3. Akses ke **folder dataset** di Google Drive / OneDrive.
4. Bila memakai Cara B: endpoint & API key **Qdrant Cloud** yang dipakai tim, atau jalankan Qdrant lokal (lihat B.2).

---

## 2. Ambil kode

```bash
git clone https://github.com/Flax9/Agenticv3.git
cd Agenticv3
```

> Jangan ubah `.gitattributes`. Berkas `backend/docker-entrypoint.sh` harus tetap berakhiran baris LF, karena dijalankan di container Linux.
> Bila container `web` gagal start dengan pesan `exec ... no such file or directory`, jalankan `git config core.autocrlf input`, hapus folder repo, lalu clone ulang.

---

## 3. Siapkan folder dataset (Google Drive / OneDrive)

1. Pasang klien desktop Google Drive atau OneDrive, lalu login dengan akun yang punya akses ke folder dataset.
2. Pastikan folder dataset **tersedia offline** (Google Drive: klik kanan → *Available offline*; OneDrive: *Always keep on this device*).
   Docker tidak bisa membaca berkas yang hanya berupa placeholder online.
3. Catat path lengkapnya, misalnya `C:/Users/nama/Google Drive/ITeC Dataset`. Gunakan garis miring `/`, bukan `\`.

Struktur yang diharapkan:

```text
ITeC Dataset/
├── rks_kb/          → masuk knowledge base RKS
├── contract_kb/     → masuk knowledge base Kontrak
├── amendment_kb/    → masuk knowledge base Amendemen
└── (folder lain)/   → berkas acuan, misalnya BoQ, yang dipilih lewat tombol 📎 di chat
```

Bila folder dataset belum tersedia, lewati langkah ini. Aplikasi tetap berjalan memakai folder kosong `./dataset`.

---

## 4. Buat berkas `.env`

Salin contoh konfigurasi di root repo:

```bash
# Windows PowerShell
Copy-Item .env.example .env
# macOS / Linux / Git Bash
cp .env.example .env
```

Buka `.env`, lalu isi minimal nilai berikut. **Jangan pernah meng-commit `.env`**, karena sudah masuk `.gitignore`.

| Variabel | Isi |
| :--- | :--- |
| `OPENROUTER_API_KEY` | API key dari pemilik proyek |
| `POSTGRES_PASSWORD` | Password bebas, minimal 12 karakter. Samakan juga di `DATABASE_URL` & `TEST_DATABASE_URL`. |
| `JWT_SECRET` | String acak minimal 32 karakter (lihat cara membuatnya di bawah) |
| `ADMIN_INITIAL_PASSWORD` | Password awal akun `admin`, minimal 10 karakter |
| `QDRANT_LOCAL_API_KEY` | String acak (Cara A) |
| `DATASET_HOST_DIR` | Path folder dataset dari langkah 3 (Cara A). Hapus tanda `#` di depannya. |
| `DATASET_DIR` | Path folder dataset yang sama (Cara B). Hapus tanda `#` di depannya. |
| `HTTP_PORT` | Port aplikasi. Ganti ke `8088` bila port 80 sudah terpakai. |
| `QDRANT_CLUSTER_ENDPOINT`, `QDRANT_API_KEY` | Qdrant Cloud tim (Cara B saja; di Cara A nilai ini diabaikan) |

Membuat string acak:

```powershell
# Windows PowerShell
-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 40 | ForEach-Object {[char]$_})
```
```bash
# macOS / Linux / Git Bash
openssl rand -hex 32
```

---

## Cara A: Docker penuh (disarankan)

Semua layanan berjalan di container: `nginx` (frontend + gateway), `web` (FastAPI), `db` (PostgreSQL), `qdrant`.

### A.1 Build & jalankan

Pastikan Docker Desktop sudah menyala, lalu dari root repo jalankan:

```bash
docker compose up -d --build
```

Build pertama butuh sekitar 10–20 menit tergantung internet. Tutup aplikasi berat lain selama build, karena build backend memakan banyak memori.
Migrasi database berjalan otomatis saat container `web` start.

Cek status:

```bash
docker compose ps
```

Keempat container harus berstatus `Up`, dan `db` serta `web` harus `(healthy)`.

### A.2 Buat akun

```bash
# Akun admin (username: admin, password: ADMIN_INITIAL_PASSWORD di .env)
docker compose exec web python -m app.scripts.seed admin

# Akun lain (role: ADMIN, PROCUREMENT, FPP, APPROVER, AUDITOR)
docker compose exec web python -m app.scripts.seed user --username budi --email budi@contoh.id --nama "Budi" --role FPP
```

### A.3 Buka aplikasi

- Buka `http://localhost` di browser. Bila `HTTP_PORT` diganti, tambahkan portnya, misalnya `http://localhost:8088`.
- Login sebagai `admin`.
- Buka menu **Knowledge Base → Sinkronkan Sekarang** untuk memasukkan isi folder dataset ke Qdrant.
  Qdrant di Docker awalnya **kosong**; isinya hanya dari sinkronisasi ini.

> **Pertanyaan chat pertama butuh ±3 menit**, karena model embedding diunduh dulu. Unduhan ini hanya sekali dan tersimpan di volume `model_cache`.
> Pertanyaan berikutnya ±30 detik. Membaca BoQ Excel yang besar bisa memakan waktu hingga ±8 menit.

### A.4 Perintah sehari-hari

```bash
docker compose ps                  # status
docker compose logs -f web         # log backend (Ctrl+C untuk keluar)
docker compose stop                # matikan sementara
docker compose start               # nyalakan lagi
docker compose down                # hapus container (data tetap ada di volume)
git pull && docker compose up -d --build   # perbarui ke versi terbaru
```

> `docker compose down -v` **menghapus seluruh data** (database, knowledge base, draf, model). Jangan dipakai kecuali memang ingin mulai dari nol.

Backup database:

```bash
docker compose exec db pg_dump -U pertamina_user pertamina_db > backup.sql
```

### A.5 Mode HTTPS (nanti, setelah ada domain)

Ikuti `deploy/certs/README.md`: letakkan `fullchain.pem` & `privkey.pem` di `deploy/certs/`, set `COOKIE_SECURE=true`, lalu jalankan:

```bash
docker compose -f docker-compose.yml -f compose.https.yml up -d --build
```

---

## Cara B: Mode development

Backend dan frontend dijalankan langsung di laptop, dan perubahan kode langsung terlihat.
Hanya PostgreSQL yang berjalan di Docker.

### B.1 PostgreSQL

```bash
docker compose -f compose.dev.yml --env-file .env up -d
```

Perintah ini membuat database `pertamina_db` dan `pertamina_test` (untuk test). Database hanya bisa diakses dari laptop itu sendiri (`127.0.0.1:5432`).

### B.2 Qdrant

Pilih salah satu:
- **Qdrant Cloud tim:** isi `QDRANT_CLUSTER_ENDPOINT` dan `QDRANT_API_KEY` di `.env`.
- **Qdrant lokal:**
  ```bash
  docker run -d --name itec_dev_qdrant -p 127.0.0.1:6333:6333 -e QDRANT__SERVICE__API_KEY=isi_string_acak qdrant/qdrant:v1.19.2
  ```
  Lalu di `.env` isi `QDRANT_CLUSTER_ENDPOINT=http://localhost:6333` dan `QDRANT_API_KEY=isi_string_acak`.

### B.3 Backend

```bash
cd backend
uv sync                                         # memasang Python 3.12 + dependensi (pertama kali ±5–10 menit)
uv run alembic upgrade head                     # migrasi database
uv run python -m app.scripts.seed admin         # akun admin
uv run uvicorn app.main:app --reload --port 8000
```

Backend membaca `.env` dari root repo, bukan dari `backend/`.
Cek dengan membuka `http://127.0.0.1:8000/api/health`.
Saat `DEBUG=True`, dokumentasi API tersedia di `http://127.0.0.1:8000/docs`.

### B.4 Frontend

Buka terminal baru:

```bash
cd frontend
npm ci
npm run dev
```

Buka `http://localhost:5173`. Vite meneruskan `/api` ke backend di port 8000.

### B.5 Pemeriksaan sebelum commit

Langkah ini sama dengan yang dijalankan GitHub Actions (`.github/workflows/ci.yml`):

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

## 5. Masalah yang sering muncul

| Gejala | Penyebab & solusi |
| :--- | :--- |
| `POSTGRES_PASSWORD wajib diisi di .env` / `QDRANT_LOCAL_API_KEY wajib diisi` | `.env` belum dibuat atau nilainya kosong. Ulangi langkah 4. |
| `Bind for 0.0.0.0:80 failed: port is already allocated` | Port 80 dipakai aplikasi lain (IIS, Skype, XAMPP). Isi `HTTP_PORT=8088` di `.env`, lalu jalankan `docker compose up -d` lagi. |
| Build berhenti / Docker Desktop macet | Memori kurang. Tutup aplikasi lain, naikkan memori Docker (lihat bagian 1), lalu ulangi `docker compose up -d --build`. Cache build tetap terpakai. |
| Container `web` terus restart | Lihat `docker compose logs web`. Penyebab umumnya `.env` salah atau masalah CRLF pada `docker-entrypoint.sh` (lihat langkah 2). |
| Daftar berkas dataset kosong | `DATASET_HOST_DIR` belum diisi atau path-nya salah, atau berkas di Drive belum tersedia offline. Setelah mengubah `.env`, jalankan `docker compose up -d` lagi. |
| Jawaban chat hanya umum, tidak merujuk dokumen | Knowledge base belum disinkronkan. Buka Knowledge Base → **Sinkronkan Sekarang**. |
| Chat lama sekali di pertanyaan pertama | Normal: model sedang diunduh (±3 menit, hanya sekali). |
| `llm_configured: false` di `/api/health` | `OPENROUTER_API_KEY` kosong. |
| Login ditolak terus setelah beberapa kali salah | Akun dikunci 15 menit (`LOGIN_LOCKOUT_MINUTES`). Tunggu, atau restart container `web`. |
| Percakapan agent mulai dari awal setelah restart | Batasan saat ini: progres agent disimpan di memori. Riwayat pesan tetap ada. |

---

## 6. Struktur folder

```text
.
├── backend/                 FastAPI, model database, migrasi Alembic, modul AI (app/services/)
├── frontend/                React + Vite
├── deploy/
│   ├── nginx/               konfigurasi Nginx (HTTP & HTTPS)
│   ├── certs/               tempat sertifikat TLS (tidak di-commit)
│   └── postgres/            skrip pembuatan database test
├── docker-compose.yml       Cara A: semua layanan
├── compose.https.yml        tambahan untuk mode HTTPS
├── compose.dev.yml          Cara B: PostgreSQL saja
├── .env.example             contoh konfigurasi
└── .github/workflows/ci.yml pemeriksaan otomatis di GitHub
```
