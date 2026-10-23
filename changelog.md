# Changelog

Semua perubahan pada backend, mesin AI (pembungkus), QA, dan deploy dicatat di sini, yang terbaru di atas.
Format tanggal: YYYY-MM-DD. Mekanisme AI (prompt, graph, generator) tidak diubah, kecuali satu baris
yang disebut jelas di bawah.

## 2026-10-23 — Perbaikan fungsi chat bot

Baseline sebelum perubahan: 53 test pytest lolos. Sesudah: 59 lolos. Mekanisme AI (prompt, graph, generator) tidak diubah.

### Temuan uji langsung (stack Docker, `http://localhost`)

- Chat **RKS** gagal pada pesan pertama: OpenRouter menolak kunci (`UnauthorizedResponseError: API key expired`). Ini masalah konfigurasi, bukan kode; `OPENROUTER_API_KEY` di `.env` perlu diganti. Setelah itu server perlu dimulai ulang (`docker compose up -d`).
- Chat **Tender/Kontrak/Amendemen** menjawab "asisten ... belum tersedia dari tim AI". Itu perilaku yang disengaja, karena agent hanya ada untuk RKS (dicatat sebagai G di `pertanyaan penanggung jawab ai.md`).
- `/api/health` melaporkan `llm_configured: true` walau kunci sudah mati, karena hanya memeriksa kunci terisi.

### Backend

- **Pesan galat chat yang ramah pengguna** (`chat_routes.py`, `_agent_error_message`).
  - Alasan: balasan sebelumnya menampilkan teks exception mentah (nama kelas, isi galat) kepada pengguna.
  - Kini galat dipetakan: kunci ditolak/kedaluwarsa, kuota/rate limit, koneksi, dan galat umum. Detail teknis hanya di log server. Berlaku untuk `/messages` dan `/stream`.
- **`GET /api/health/ready` kini memeriksa kunci LLM** (field baru `llm`, ke `https://openrouter.ai/api/v1/key`, batas waktu 5 detik, tidak memakai kuota model). Hasil `kunci ditolak atau kedaluwarsa` tidak membuat layanan 503, karena hanya fitur chat yang terdampak.

### Frontend

- **Kolom chat dinonaktifkan untuk Tender, Kontrak, dan Amendemen** (`ChatInput.jsx`), dengan petunjuk di placeholder. Tombol 📎 untuk memilih berkas dari drive (ekstraksi Tender) tetap aktif. `sendMessage` di `useAppStore.js` juga menolak mode non-RKS sebagai pengaman kedua.
  - Alasan: pengguna mengetik lalu menerima balasan "belum tersedia", seolah chat rusak.

### Test

- `test_hardening.py`: kunci LLM ditolak tidak membuat `ready` gagal; `_agent_error_message` (4 kasus, termasuk memastikan detail teknis tidak bocor). `test_ready_*` kini memalsukan pengecekan LLM agar tidak menyentuh jaringan.
- `test_chat.py`: `test_agent_error_is_saved_as_message` menyesuaikan pesan ramah, bukan teks galat mentah.
- `test_api.py`: `test_kb_list_documents_is_filename_to_chunk_count` (kontrak `/api/kb/list`, sudah di-commit sebelumnya).

### Catatan untuk tim AI

- Bagian G ditambahkan di `pertanyaan penanggung jawab ai.md`: titik sambung web yang sudah siap untuk agent Tender/Kontrak/Amendemen dan pertanyaan yang perlu dijawab. Collection `contract_kb` dan `amendment_kb` saat ini kosong di Qdrant.

## 2026-10-22 — Penyesuaian backend, QA otomatis, dan persiapan deploy

Baseline sebelum perubahan: 44 test pytest lolos.

### Backend

- **Checkpointer agent disimpan di PostgreSQL.**
  - Alasan: `MemorySaver` membuat sesi yang sedang menunggu BoQ atau persetujuan draf tidak bisa dilanjutkan setelah server restart, padahal riwayat chat tetap ada.
  - File baru: `backend/app/core/checkpointer.py`. Memakai satu koneksi `psycopg` dengan keepalive, karena `psycopg_pool` gagal start di lingkungan pengembangan Windows. Bila PostgreSQL tidak terjangkau saat agent dimuat, dipakai `MemorySaver` dan peringatannya dicatat di log.
  - `backend/app/services/agent/graph.py`: **satu-satunya perubahan di file AI**, yaitu `MemorySaver()` menjadi `make_checkpointer()` (disetujui pemilik proyek). Logika node tidak berubah.
  - Konfigurasi baru: `AGENT_CHECKPOINTER` (`postgres` | `memory`, default `postgres`).
  - `backend/alembic/env.py`: tabel `checkpoint*` milik LangGraph diabaikan oleh `alembic check`.
  - Dependensi baru: `langgraph-checkpoint-postgres`, `psycopg[binary]`.
- **Job latar belakang tersimpan di database.**
  - Alasan: status job hilang saat restart.
  - Tabel baru `background_job` (migrasi `3c3e3289b229`). `JobManager.start()` dan `get()` kini async. Job yang masih "berjalan" saat startup ditandai "gagal" dengan pesan restart.
  - Progres langsung tetap di memori proses (tidak ditulis ke DB tiap langkah).
- **Pembatas laju chat per pengguna.**
  - Alasan: melindungi kuota/biaya OpenRouter, terutama karena aplikasi akan terbuka lewat internet saat presentasi.
  - Respons `429` dengan header `Retry-After`. Konfigurasi `CHAT_RATE_LIMIT_PER_MINUTE` (default 20, `0` = tanpa batas). Berlaku di `/messages` dan `/stream`.
- **Endpoint kesiapan `GET /api/health/ready`.**
  - Memeriksa koneksi PostgreSQL (wajib) dan Qdrant (informasi) dengan batas waktu 5 detik. Mengembalikan 503 bila database gagal. Hanya jenis galat yang ditampilkan, bukan pesan aslinya, supaya alamat dan kredensial tidak bocor. `/api/health` tetap sebagai pemeriksaan hidup yang ringan.

### Test

- Baru: `backend/tests/test_hardening.py` (9 test): kesiapan layanan, batas laju, job bertahan setelah restart, job terputus, dan checkpointer (Postgres, memory, fallback).
- `backend/tests/conftest.py`: pembatas laju chat direset di setiap test.

### Tidak diubah (disengaja)

- Lock per jenis dokumen di `tender_routes.py` tetap ada. Penyebabnya variabel global di generator AI, jadi lock hanya bisa dilepas setelah tim AI mengubah generator.
- Timeout dan retry LLM tidak ditambahkan di web: klien LLM dibuat di `graph.py` dan tidak bisa dibatalkan dari thread. Pertanyaannya ada di `pertanyaan penanggung jawab ai.md`, bagian E3.

### Temuan QA yang diperbaiki (ditemukan oleh `qa/run_qa.py`)

- **Karakter NUL (`\x00`) pada username/password login atau isi pesan chat menyebabkan HTTP 500** (PostgreSQL menolak NUL). Sekarang 422. Perbaikan di `schemas/auth_schema.py` dan `schemas/chat_schema.py`; test `test_nul_character_is_rejected_not_500`. (A-05)
- **Request pertama ke sesi RKS menggantung selamanya** setelah checkpointer Postgres dipasang.
  - Sebab: `PostgresSaver.setup()` menjalankan `CREATE INDEX CONCURRENTLY` yang menunggu semua transaksi lain selesai, padahal agent dimuat (lazy) di dalam request yang sedang memegang transaksi database sendiri, sehingga request menunggu dirinya sendiri. Terbukti dari `pg_stat_activity` (query menunggu `virtualxid`). Test pytest tidak menangkapnya karena tidak ada transaksi terbuka.
  - Perbaikan: agent dimuat saat startup server sebelum ada request (`AGENT_WARMUP`, default `true`, `rks_runner.warm()` di `main.py`), dan `setup()` diberi `statement_timeout` 30 detik sehingga bila terjadi lagi gagal dengan galat (fallback `MemorySaver`), bukan menggantung. Efek samping yang menguntungkan: pertanyaan chat pertama tidak lagi menanggung waktu muat agent. Konsekuensinya startup server lebih lama (puluhan detik). (A-12, L-01)
- Konfigurasi baru: `AGENT_WARMUP` (test mematikannya).

### QA

- Baru: `QA.md` (strategi, lingkungan, katalog 40 pemeriksaan, kriteria keluar), `qa/run_qa.py` (runner otomatis enam lapisan), `qa/browser_checks.py` (Playwright). Hasil ada di `qa/hasil/` (tidak di-commit).
- Hasil terakhir (22 Okt 2026): L1 statis 5/5, L2 pytest lulus (53 test), L3 API/keamanan 15/15, L5 beban 4/4, L6 browser 6/6. **L4 LLM nyata belum bisa lulus**: OpenRouter menjawab `API key expired`; menunggu kunci baru.
- Catatan lingkungan: koneksi ke `localhost` di Windows kadang menggantung (teralihkan ke IPv6); runner memakai `127.0.0.1` dan `connect_timeout`.

### Deploy

- Baru: `compose.tunnel.yml` (cloudflared + cookie Secure + port Nginx hanya ke 127.0.0.1), `deploy/nginx/tunnel.conf` (IP asli dari `CF-Connecting-IP`, HSTS), `deploy/cloudflare/README.md` (langkah Named Tunnel + Access, checklist presentasi, catatan privasi). Konfigurasi divalidasi dengan `docker compose config`; belum dijalankan terhadap akun Cloudflare sungguhan.
- `.env.example`: `CLOUDFLARE_TUNNEL_TOKEN`, `CHAT_RATE_LIMIT_PER_MINUTE`, `AGENT_CHECKPOINTER`.
