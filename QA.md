# Dokumen QA: ITeC Procurement AI Copilot

Dokumen ini menjelaskan cara projek ini diuji. Pengujiannya dijalankan otomatis oleh `qa/run_qa.py` berdasarkan katalog di bagian 5.
Setiap ID di tabel (S-01, A-04, dst.) sama dengan ID di skrip dan di laporan hasil.

## 1. Tujuan dan ruang lingkup

Tujuan: memastikan aplikasi **aman, stabil, dan layak ditampilkan** saat presentasi, serta mendeteksi regresi setiap kali kode berubah.

| Diuji | Tidak diuji otomatis |
| :--- | :--- |
| Kualitas kode dan konsistensi skema database | **Mutu isi dokumen yang dihasilkan AI** (ketepatan pasal, angka, bahasa). Ini ranah tim AI dan dinilai manual. |
| Autentikasi, otorisasi per peran (RBAC), isolasi data antar pengguna | Tampilan piksel-per-piksel (hanya fungsi dan responsivitas dasar) |
| Ketahanan input (injeksi, token palsu, JSON rusak) | Data 86 aturan STK (belum ada sumbernya) |
| Alur chat dengan LLM sungguhan, termasuk bertahannya state agent setelah restart | Penetration test mendalam / audit pihak ketiga |
| Beban ringan (belasan pengguna serentak) | Beban besar (ratusan pengguna), karena tidak relevan untuk demo |
| Alur UI utama di browser | Kompatibilitas Safari/Firefox (hanya Chromium) |
| Konfigurasi deploy (compose valid) | Akses dari internet lewat Cloudflare: dicek manual lewat checklist di `deploy/cloudflare/README.md` |

## 2. Pendekatan: enam lapisan

Lapisan bawah murah dan cepat, lapisan atas lebih mahal dan lebih mirip pemakaian nyata. Semuanya berjalan otomatis berurutan.

| Lapisan | Alat | Isi | Memanggil layanan luar? |
| :--- | :--- | :--- | :--- |
| L1 Statis | ruff, alembic, oxlint, vite build | Gaya kode, skema DB sesuai model, frontend bisa dibangun | Tidak |
| L2 Pytest | pytest + PostgreSQL | 53 test: auth, RBAC, chat (agent palsu), dataset, housekeeping, penyesuaian backend | Tidak (LLM dan Qdrant dipalsukan) |
| L3 API & keamanan | httpx terhadap server sungguhan | Uji black-box lewat HTTP, termasuk serangan dasar | Tidak |
| L4 LLM nyata | httpx + SSE | Agent LangGraph, OpenRouter, dan Qdrant sungguhan | **Ya**: ±6 panggilan LLM |
| L5 Beban | thread paralel | Latensi p50/p95 dan jumlah galat | Tidak |
| L6 Browser | Playwright (Chromium) | Login, kirim pesan, responsif ponsel, keluar | Tidak |

## 3. Lingkungan dan data uji

- **Database terpisah `pertamina_qa`** pada PostgreSQL development (dibuat ulang tiap run). Data development (`pertamina_db`) tidak disentuh.
- Backend dijalankan runner pada `http://127.0.0.1:8000` dengan `DEBUG=false` (seperti produksi: Swagger mati) dan `AGENT_CHECKPOINTER=postgres`.
- Frontend hasil build disajikan `vite preview` di `http://127.0.0.1:4173`.
- Startup backend memuat agent lebih dulu (`AGENT_WARMUP`), jadi runner menunggu sampai 5 menit sampai server siap.
- Akun uji (password `Password-QA-12345`, hanya ada di database QA): `qa_admin`, `qa_procurement`, `qa_fpp`, `qa_approver`, `qa_auditor`, plus `qa_lockout` khusus uji pemblokiran login.
- LLM dan Qdrant memakai kunci di `.env`. Pada L4 Qdrant hanya **dibaca** (pencarian), tidak ada penulisan.
- Prasyarat: Docker Desktop menyala (PostgreSQL development), `uv`, Node.js 24. Chromium untuk Playwright diunduh otomatis (±300 MB).

## 4. Cara menjalankan

Dari root repo:

```bash
uv run --project backend python qa/run_qa.py                  # semua lapisan
uv run --project backend python qa/run_qa.py --skip-llm       # tanpa biaya LLM
uv run --project backend python qa/run_qa.py --skip-static --skip-load --skip-browser   # hanya pytest + API + LLM
```

Hasil: `qa/hasil/laporan_qa.md` (tabel lulus/gagal per pemeriksaan) dan `qa/hasil/laporan_qa.json`. Log server ada di `qa/hasil/server.log`.
Kode keluar `0` bila tidak ada pemeriksaan yang gagal (cocok dipakai di CI).

## 5. Katalog pemeriksaan

### L1 Statis

| ID | Pemeriksaan | Lulus bila |
| :-- | :-- | :-- |
| S-01 | `ruff check` pada `app` dan `tests` | Tanpa temuan |
| S-02 | `ruff format --check` | Tanpa berkas yang perlu diformat |
| S-03 | `alembic check` | Model ORM dan skema hasil migrasi identik |
| S-04 | `npm run lint` (oxlint) | Tanpa galat |
| S-05 | `npm run build` (vite) | Build sukses |

### L2 Pytest

| ID | Pemeriksaan | Lulus bila |
| :-- | :-- | :-- |
| P-01 | Seluruh suite `backend/tests` | Semua test lulus. Cakupan: login/refresh/lockout, RBAC, sesi chat dan draf, sinkron dataset, housekeeping, kesiapan layanan, batas laju, persistensi job, checkpointer. |

### L3 API dan keamanan

| ID | Pemeriksaan | Lulus bila |
| :-- | :-- | :-- |
| A-01 | `/api/health` dan `/api/health/ready` | Status ok, database `ok` |
| A-02 | Login kelima peran | 200 dan cookie refresh `HttpOnly` |
| A-03 | Login salah / akun tak ada | Keduanya 401 dengan pesan identik (tidak membocorkan keberadaan akun) |
| A-04 | Pemblokiran login | Setelah 5 gagal: 429 dengan `Retry-After`, kredensial benar pun tetap diblokir |
| A-05 | Injeksi SQL, string 5000 karakter, karakter null pada login | Tidak pernah 500 |
| A-06 | Semua endpoint `/api` (dari OpenAPI) tanpa token | 401 (kecuali login/refresh/logout/health) |
| A-07 | Token dirusak, `alg=none`, token refresh dipakai sebagai access | Semua 401 |
| A-08 | Matriks RBAC: buat sesi dan sinkron dataset per peran | AUDITOR/APPROVER tidak bisa membuat sesi; FPP/APPROVER/AUDITOR tidak bisa sinkron |
| A-09 | Isolasi data antar pengguna | Menulis ke sesi orang lain 404; daftar sesi tidak memuat sesi orang lain; AUDITOR boleh membaca |
| A-10 | Dokumentasi API pada mode produksi | `/docs`, `/openapi.json`, `/redoc` semuanya 404 |
| A-11 | CORS dari origin asing | Origin asing tidak diizinkan |
| A-12 | `dataset_file_id` berisi path traversal atau SQL | 422, dan UUID tak dikenal 400/404 |
| A-13 | Batas laju chat | 20 pesan pertama 200, setelahnya 429 (memakai mode Kontrak sehingga tanpa LLM) |
| A-14 | Body JSON rusak, field hilang, tipe dokumen tak dikenal | 422, bukan 500 |
| A-15 | Job tak dikenal | 404 |

### L4 LLM nyata

Batas biaya: 5 pemeriksaan, sekitar 6 panggilan LLM (model Qwen flash di OpenRouter), sehingga biayanya kecil.

| ID | Pemeriksaan | Lulus bila |
| :-- | :-- | :-- |
| L-01 | Pertanyaan umum ("Apa itu HPS?") lewat SSE | Ada event `progress`, `done`, balasan lebih dari 20 karakter, tanpa error |
| L-02 | Pertanyaan knowledge base | Dijawab tanpa error (Qdrant terjangkau) |
| L-03 | "Tolong buatkan RKS ..." | Agent berhenti menunggu BoQ (`awaiting = upload_boq`) |
| L-04 | **Restart server** lalu baca sesi yang sama | Baris checkpoint ada di PostgreSQL dan `awaiting` tetap `upload_boq` |
| L-05 | Balas "lewati" setelah restart | Agent melanjutkan dari titik berhenti, tanpa error, dan tidak lagi menunggu BoQ |

### L5 Beban ringan

| ID | Pemeriksaan | Lulus bila |
| :-- | :-- | :-- |
| B-01 | `/api/health`, 200 permintaan, 20 paralel | 0 galat, p95 < 500 ms |
| B-02 | Daftar sesi terautentikasi, 100 permintaan, 10 paralel | 0 galat, p95 < 800 ms |
| B-03 | Login (argon2 sengaja lambat), 20 login, 5 paralel | 0 galat, p95 < 3 detik |
| B-04 | Membuat 30 sesi serentak | 0 galat, semua sesi tercatat |

### L6 Browser

| ID | Pemeriksaan | Lulus bila |
| :-- | :-- | :-- |
| U-01 | Login dengan password salah | Pesan galat tampil, tidak masuk, kolom password dikosongkan |
| U-02 | Login benar, lalu pilih jenis dokumen pada pemilih yang muncul | Aplikasi terbuka dan tidak ada galat JavaScript di konsol |
| U-03 | Muat ulang halaman | Tetap login (cookie refresh bekerja) |
| U-04 | Kirim pesan di mode bawaan (Tender) | Gelembung pengguna dan balasan asisten tampil |
| U-05 | Layar ponsel 390 px | Tanpa gulir horizontal, kolom pesan tetap terpakai |
| U-06 | Keluar | Kembali ke login, dan tetap di login setelah reload |

## 6. Kriteria keluar (siap presentasi)

1. Tidak ada pemeriksaan **GAGAL** di L1–L3 dan L6. Itu syarat mutlak.
2. L4 lulus seluruhnya. Bila gagal karena OpenRouter atau Qdrant di luar kendali (kuota, jaringan), ulangi sekali; jika masih gagal, catat sebagai risiko demo dan siapkan rekaman cadangan.
3. L5 memenuhi batas p95. Angka aktual tercatat di kolom catatan laporan.
4. Checklist manual di `deploy/cloudflare/README.md` sudah dicentang di jaringan yang akan dipakai presentasi.
5. Tidak ada rahasia (`.env`, kunci API) yang ikut ter-commit: `git status` bersih dari `.env`.

## 7. Batasan yang perlu diketahui

- **Mutu isi dokumen** dinilai manual. Rekomendasi: satu kali uji alur penuh (informasi pekerjaan → draf RKS → ekspor `.docx`) dengan data dummy sebelum presentasi, lalu buka hasilnya di Word.
- Alur lengkap sampai ekspor `.docx` lewat LLM tidak diotomatisasi karena hasilnya tidak deterministik dan memakan banyak panggilan LLM. L4 membuktikan jalur agent, streaming, dan kelanjutan sesi, sedangkan pembuatan dan ekspor `.docx` diuji lewat agent palsu di L2.
- Perilaku LLM bisa berubah antar run. Asersi L4 sengaja longgar (ada balasan, tanpa error, status agent), tidak mencocokkan teks.
- Beban diuji pada satu mesin yang sama dengan penguji, sehingga angka p95 sedikit lebih baik daripada akses nyata lewat internet.
- Pembatas login dan pembatas chat disimpan di memori proses. Bila backend dijalankan dengan beberapa worker, hitungannya tidak dibagi (lihat catatan di `backend/app/core/rate_limit.py`).

## 8. Penanganan temuan

| Tingkat | Contoh | Tindakan |
| :-- | :-- | :-- |
| Kritis | Akses tanpa login, data bocor antar pengguna, rahasia ter-commit | Perbaiki segera, tambahkan test regresi, catat di `changelog.md` |
| Tinggi | Galat 500 pada input biasa, state agent hilang | Perbaiki sebelum presentasi |
| Sedang | Latensi di atas batas, pesan galat membingungkan | Jadwalkan |
| Ranah AI | Bug prompt/graph/generator | **Jangan diubah oleh tim web**; tulis di `pertanyaan penanggung jawab ai.md` |
