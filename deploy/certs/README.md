# Tempat sertifikat TLS

Letakkan dua berkas berikut di folder ini. Folder ini tidak ikut di-commit, kecuali README ini.

| Berkas | Isi |
|---|---|
| `fullchain.pem` | Sertifikat server beserta rantai CA perantara |
| `privkey.pem` | Private key sertifikat (jangan dibagikan) |

Sumber sertifikat yang bisa dipakai:
- **Sertifikat korporat** dari tim IT: minta dalam format PEM, atau konversi dari `.pfx` dengan
  `openssl pkcs12 -in sertifikat.pfx -nokeys -out fullchain.pem` dan
  `openssl pkcs12 -in sertifikat.pfx -nocerts -nodes -out privkey.pem`.
- **Let's Encrypt** (butuh domain publik yang mengarah ke server): salin `fullchain.pem` dan `privkey.pem`
  dari `/etc/letsencrypt/live/<domain>/`.

Lalu jalankan:

```bash
# .env: COOKIE_SECURE=true
docker compose -f docker-compose.yml -f compose.https.yml up -d --build
```

Bila server berada di belakang gateway/load balancer korporat yang sudah menangani HTTPS, mode ini tidak
diperlukan: tetap pakai `docker-compose.yml` (HTTP) dan biarkan gateway meneruskan trafik ke port Nginx.
