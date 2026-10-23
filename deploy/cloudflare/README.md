# Deploy presentasi: laptop + Cloudflare Tunnel + Cloudflare Access

Aplikasi tetap berjalan di laptop Anda (Docker). Cloudflare Tunnel membuat sambungan **keluar** dari laptop ke Cloudflare,
sehingga tidak ada port yang dibuka di router. Cloudflare Access meminta login email sebelum halaman aplikasi bisa dibuka.
Biaya: gratis (paket Free Cloudflare, sampai 50 pengguna Access).

```text
Browser ──HTTPS──▶ Cloudflare (Access: login email) ──tunnel──▶ cloudflared ──▶ nginx ──▶ web (FastAPI) ──▶ db, qdrant
```

## Yang perlu disiapkan

| Kebutuhan | Keterangan |
| :--- | :--- |
| Akun Cloudflare (gratis) | https://dash.cloudflare.com/sign-up |
| Domain yang DNS-nya dikelola Cloudflare | Named Tunnel butuh domain. Domain murah (±Rp 150 ribu/tahun) atau domain kampus yang bisa dipindah nameserver-nya. |
| Docker Desktop, RAM ≥ 8 GB | Sama seperti Cara A di README utama. |
| `.env` terisi lengkap | Lihat README utama bagian 4. Pastikan `JWT_SECRET`, `POSTGRES_PASSWORD`, dan `QDRANT_LOCAL_API_KEY` bukan nilai contoh. |

## Langkah 1 — Buat tunnel (di dashboard, sekali saja)

1. Buka **Zero Trust → Networks → Tunnels → Create a tunnel** → pilih **Cloudflared** → beri nama `itec-demo`.
2. Pada langkah *Install connector*, pilih **Docker** dan **salin token-nya** (teks panjang setelah `--token`). Jangan jalankan perintah yang ditampilkan; compose kita yang menjalankannya.
3. Tab **Public Hostname** → **Add**:
   - Subdomain/Domain: misalnya `itec.domainanda.com`
   - Service: **HTTP**, URL `nginx:80`
4. Simpan.

## Langkah 2 — Kunci dengan Cloudflare Access (wajib sebelum dibagikan)

1. **Zero Trust → Access → Applications → Add an application → Self-hosted**.
2. Application domain: `itec.domainanda.com` (sama dengan hostname di atas).
3. Policy: **Allow**, *Include → Emails* → isi email dosen, penguji, dan email Anda sendiri.
   Pilih **One-time PIN** sebagai metode login (tanpa perlu akun tambahan).
4. Simpan. Sesudah ini, siapa pun yang membuka alamat itu harus memasukkan email yang diizinkan dan kode PIN yang dikirim ke emailnya.

Login Access ini **tambahan** dari login aplikasi (JWT + RBAC). Pengguna perlu dua langkah: PIN email, lalu akun ITeC.

## Langkah 3 — Jalankan

Tambahkan token ke `.env`:

```text
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoi...
```

Lalu:

```bash
docker compose -f docker-compose.yml -f compose.tunnel.yml up -d --build
docker compose -f docker-compose.yml -f compose.tunnel.yml exec web python -m app.scripts.seed admin
```

Buat akun untuk penguji (satu per peran bila perlu) dengan `seed user ...` seperti di README utama.
Port Nginx di laptop hanya dibuka ke `127.0.0.1`, jadi perangkat lain di Wi-Fi yang sama tidak bisa mengaksesnya langsung.

Cek:

```bash
docker compose -f docker-compose.yml -f compose.tunnel.yml ps          # cloudflared harus Up
docker compose -f docker-compose.yml -f compose.tunnel.yml logs cloudflared | tail   # cari "Registered tunnel connection"
```

Buka `https://itec.domainanda.com` dari HP (data seluler, bukan Wi-Fi laptop) untuk memastikan akses dari luar benar-benar jalan.

## Checklist sebelum presentasi

- [ ] Laptop tersambung ke listrik, mode tidur dimatikan, Docker Desktop menyala.
- [ ] Sinkronisasi knowledge base sudah dijalankan (menu **Knowledge Base → Sinkronkan Sekarang**) dan model embedding sudah terunduh.
- [ ] Satu kali percobaan chat penuh sudah berhasil **di jaringan yang akan dipakai presentasi**. Pertanyaan pertama setelah restart bisa ±3 menit karena model dimuat.
- [ ] `https://itec.domainanda.com/api/health/ready` menunjukkan `"database": "ok"` dan `"qdrant": "ok"` (setelah login Access).
- [ ] Saldo/kuota OpenRouter cukup. Pembatas `CHAT_RATE_LIMIT_PER_MINUTE` (default 20/menit per pengguna) menjaga agar satu akun tidak menghabiskan kuota.
- [ ] Akun `admin` memakai password kuat, dan akun uji dihapus atau dinonaktifkan setelah presentasi.

## Setelah presentasi

```bash
docker compose -f docker-compose.yml -f compose.tunnel.yml down      # data tetap di volume
```

Lalu hapus aplikasi Access dan tunnel dari dashboard, atau cabut email penguji dari policy, agar alamat itu tidak lagi bisa dibuka.

## Catatan privasi (baca sebelum memasukkan data asli)

- **Data tersimpan di laptop Anda** (PostgreSQL, Qdrant, draf `.docx`). Tidak ada yang diunggah ke penyimpanan Cloudflare.
- Cloudflare **mengakhiri TLS di server mereka**, jadi lalu lintas terenkripsi sampai Cloudflare lalu diteruskan lewat tunnel terenkripsi ke laptop. Secara teknis Cloudflare dapat melihat isi lalu lintas saat transit. Kebijakan dan sertifikasi privasinya ada di situs Cloudflare; bila dokumen internal Pertamina yang asli tidak boleh melewati pihak ketiga, **gunakan data dummy untuk demo**.
- Teks RKS/BoQ yang diproses agent **dikirim ke OpenRouter** (LLM eksternal), terlepas dari tempat deploy. Ini pertanyaan E7 di `pertanyaan penanggung jawab ai.md`.
- Header IP pengguna (`CF-Connecting-IP`) hanya dipercaya karena Nginx hanya dapat dijangkau cloudflared di jaringan Docker internal. Jangan membuka port Nginx ke jaringan umum pada mode ini.

## Pemecahan masalah

| Gejala | Penyebab / solusi |
| :--- | :--- |
| Error 1033 / 502 dari Cloudflare | `cloudflared` tidak jalan atau Service di Public Hostname salah. Pastikan `nginx:80` dan token benar. |
| Login berhasil lalu langsung keluar | `COOKIE_SECURE` harus `true` dan akses harus lewat `https://`. `compose.tunnel.yml` sudah mengaturnya; jangan menimpanya di `.env` dengan `false` untuk akses lewat tunnel. |
| Respons chat terputus di tengah | Cloudflare memutus koneksi tanpa data ±100 detik. Stream chat mengirim heartbeat tiap 15 detik, jadi bila terjadi, periksa log `web` apakah backend crash. |
| `ports: !override` tidak dikenali | Docker Compose terlalu lama. Perbarui Docker Desktop (butuh Compose ≥ 2.24). |
