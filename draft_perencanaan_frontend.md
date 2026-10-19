# 📋 Draft Perencanaan Front-End: `agenticv3`
### Pertamina Procurement AI Copilot & Live Canvas (Versi 3.0) — Spesifikasi UI/UX & Catatan Porting

**Dokumen Spesifikasi UI/UX Front-End**  
*Tanggal awal:* 18 Oktober 2026 · *Revisi:* 19 Oktober 2026  
*Prototipe:* `agenticv3/frontend_vanilla/` (HTML + CSS + JS vanilla, **dibekukan** sebagai acuan visual)  
*Implementasi target:* `agenticv3/frontend/` (React + Vite + Tailwind CSS v3)  
*Basis Sistem Backend:* `Agentic_Rag_Pertamina_camp/api.py` (FastAPI @ Port 8000) → akan dipindah ke `backend/app/`  
*Acuan Regulasi:* Pedoman Pengadaan No. `A03-001/PNG200000/2024-S9` Rev. 1  

> **Hubungan dengan masterplan:** Arsitektur, struktur direktori, database, keamanan, dan deployment diatur di `draft_perencanaan_proyek_ITeC.md`. Dokumen ini hanya mengatur **tampilan, perilaku UI, dan pemetaan prototipe vanilla → komponen React**. Bila ada perbedaan, masterplan yang berlaku.

> **Revisi alur (19 Okt 2026, masterplan 1.0):** unggah berkas dari browser tidak dipakai lagi. Tombol 📎 di `ChatInput` dan tombol "Pilih Berkas dari Drive" membuka `DatasetPickerModal`, yang menampilkan berkas di folder drive (`GET /api/dataset/files`). Mode RKS memakai chat agent sungguhan: SSE dengan progres per tahap, saran cepat sesuai node yang menunggu ("Lanjut Tanpa BoQ", "Setuju & Ekspor"), dan draf tampil di `RksDraftView`. Riwayat sesi ada di `HamburgerMenu`, sedangkan status proses tampil di `ProgressDrawer` dan `VerticalRestoreTab`. Penyebutan "upload" di bawah ini adalah catatan desain prototipe awal.

---

## 1. 🎯 Tujuan & Visi Front-End `agenticv3`

Mentransformasikan sistem pengadaan dari antarmuka formulir bertingkat yang kaku (*form-based*) menjadi antarmuka **Generative AI Copilot + Live Document Canvas** yang modern, responsif, dan interaktif:
1. **Percakapan Terarah (Guided Dialogue):** Pengguna dapat berdialog secara natural, mengunggah dokumen acuan (BoQ/TOR), dan meminta revisi klausul secara selektif.
2. **Sinkronisasi Dua Arah (*Bi-directional Sync*):** Setiap perubahan pada chat langsung tercermin secara visual di kanvas dokumen sebelah kanan dengan penanda *highlight*.
3. **Kartu Interaktif Cerdas (*Generative Micro-Cards*):** Ekstraksi parameter otomatis langsung tersaji dalam kartu verifikasi yang bisa di-*inline edit* tanpa membuat user mengetik puluhan butir data manual. Nilai kritikal (HPS, jaminan, denda, masa pemeliharaan) **wajib dikonfirmasi user** sebelum diterapkan ke canvas.
4. **Kepatuhan Terukur (*Compliance Scorecard*):** Menyediakan visibilitas terhadap pemenuhan 86 butir checklist mandatory pra-tender secara *real-time*.

---

## 2. 🏛️ Arsitektur Tampilan: *Split-View Canvas Model*

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🔴 TOPBAR: Branding | Doc Picker (Paket Aktif) | Step x/4 (buka Drawer) | Unduh .DOCX | ☰  │
├──────────────────────────────────────────────┬──────────────────────────────────────────────┤
│ 💬 LEFT PANE (42% - 45%): AI COPILOT CHAT    │ 📄 RIGHT PANE (55% - 58%): LIVE CANVAS       │
│                                              │                                              │
│ 1. Workflow Stepper Bar                      │ 1. Canvas Toolbar: Tab Pill + Icon Tools     │
│    [Upload] -> [Ekstrak] -> [Verif] -> [Doc] │    [📄 Dokumen] [📊 Matriks] [✅ STK 86]      │
│ 2. Chat Feed Stream:                         │    [⧉ Salin] [⛶ Fullscreen] [✕ Tutup]        │
│    • Pesan AI & User Bubbles                 │                                              │
│    • Reasoning Collapsible Box               │ 2. Sheet Canvas Body:                        │
│    • Tool-call Accordion                     │    • Naskah Resmi Pertamina (Header Navy)    │
│    • In-Chat Extraction / Artifact Card      │    • Tabel 40 Poin Ketentuan Khusus IKPP     │
│ 3. Quick Action Chips                        │    • Draft 20 Pasal Kontrak Definitif        │
│ 4. Lampiran + Input Box + Tombol Kirim       │    • Real-time Highlight saat Diperbarui     │
│    (Support: PDF RKS/TOR, XLSX/PDF BoQ)      │                                              │
└──────────────────────────────────────────────┴──────────────────────────────────────────────┘
  Saat canvas ditutup: chat melebar 100% dan muncul Vertical Restore Tab di tepi kanan.
  Progress Drawer (slide-out): tahapan sesi, daftar artifact, dan resource acuan yang dipakai.
```

**Perilaku responsif (wajib di versi React):**
- `≥ 1280px`: split-view seperti diagram di atas.
- `768–1279px`: canvas menjadi panel *overlay* yang dibuka lewat Vertical Restore Tab.
- `< 768px`: satu kolom; canvas dibuka sebagai halaman penuh dengan tombol kembali ke chat.

---

## 3. 📂 Struktur Direktori

### 3.1 Prototipe (dibekukan, hanya acuan)
```text
agenticv3/frontend_vanilla/
├── index.html          # Layout lengkap: topbar, chat, canvas, drawer, popup Doc Picker
├── css/
│   ├── main.css        # Design tokens, topbar, layout, drawer, dropdown
│   ├── chat.css        # Chat feed, bubble, micro-card, tool foldout, stepper, chips
│   └── canvas.css      # Naskah dokumen formal, tabel IKPP, matriks HPS, scorecard
└── js/
    ├── state.js        # AppStateManager (pub/sub sederhana) + data demo 5 mode
    ├── api.js          # ApiService (fetch ke FastAPI)
    ├── chat.js         # ChatController (render pesan, respons AI simulasi)
    ├── canvas.js       # CanvasController (template dokumen, tab, highlight)
    └── app.js          # Bootstrap + fungsi global window.* untuk onclick
```

### 3.2 Implementasi React (target)
Struktur lengkap ada di masterplan Bagian 3 (`frontend/src/komponen/` dan `frontend/src/services/`). Pemetaan dari prototipe ada di Bagian 6 dokumen ini.

---

## 4. 🔌 Integrasi Endpoint Backend

Di React, seluruh request memakai **path relatif** `/api/...`. Saat development, Vite mem-proxy ke `http://127.0.0.1:8000`; di produksi, Nginx meneruskan ke container `web`. Semua endpoint (kecuali login & health) membutuhkan header `Authorization: Bearer <token>`.

| Modul / Fitur | Endpoint Backend | Method | Payload / Fungsi |
| :--- | :--- | :---: | :--- |
| **Login** | `/api/auth/login`, `/api/auth/me` | `POST/GET` | Autentikasi & profil + peran pengguna |
| **Health** | `/api/health` | `GET` | Status backend (dipakai indikator titik status di topbar) |
| **Ekstraksi Otomatis** | `/api/extract-tender-metadata` | `POST` | `file_rks` (PDF) dan/atau `file_boq` (PDF/XLSX), `tanggal`, `resiko_csms` → JSON `{status, data}` |
| **Chat Streaming** | `/api/chat/stream` | `POST` | Pesan user → token balasan AI via SSE |
| **Generate Tender** | `/api/generate-tender` | `POST` | Paket lengkap Dokumen Tender Versi 2.0 (`.docx`) |
| **Generate RKS** | `/api/generate-rks` | `POST` | Dokumen RKS teknis spesifik (`.docx`) |
| **Generate Kontrak** | `/api/generate-kontrak` | `POST` | Naskah Rancangan Kontrak Definitif 20 Pasal (`.docx`) |
| **Generate Amendemen**| `/api/generate-amendemen` | `POST` | Draft Addendum dengan tabel lama vs baru (`.docx`) |
| **Knowledge Base** | `/api/kb/list`, `/api/kb/ingest` | `GET/POST`| Mengelola berkas referensi RAG pada Qdrant |

**Aturan penanganan respons:**
- Error HTTP ditampilkan lewat `Toast` dengan pesan berbahasa Indonesia; detail teknis hanya ke `console`.
- **Tidak ada fallback diam-diam ke data demo.** Jika backend gagal, UI menampilkan error yang jelas. Mode demo hanya aktif bila dipilih eksplisit oleh user (tombol "Coba Demo").
- Indikator backend memakai `GET /api/health` dengan `fetch` biasa (bukan `mode: 'no-cors'`, yang selalu "berhasil" walau respons tidak terbaca).

---

## 5. 🎨 Standar Visual & Palet Warna (Pertamina Corporate Identity)

Token resmi **mengikuti `frontend/tailwind.config.js`** (masterplan 3.1). Nilai lama di prototipe (`#ED1B24`, `#0072CE`, `#F4F6F9`) tidak dipakai lagi.

| Token Tailwind | Hex | Penggunaan |
| :--- | :--- | :--- |
| `pertamina-navy` | `#002D62` | Header, tombol primer, judul naskah resmi |
| `pertamina-navy-dark` | `#001D42` | Background navbar, hover |
| `pertamina-red` | `#ED1C24` | Aksen dinamis, border navbar bawah, badge risiko tinggi, cap confidential |
| `pertamina-green` | `#009A44` | Status sukses, tombol unduh |
| `pertamina-blue` | `#0072BC` | Tab aktif, link, fokus input |
| `pertamina-gray-50` | `#F8FAFC` | Background canvas & aplikasi |
| `shadow-pertamina-lg` | – | Bayangan lembar dokumen (sheet `#FFFFFF`) |

* **Tipografi:**
  * Naskah & Antarmuka: `Plus Jakarta Sans` → `Inter` → system-ui (token `font-sans`)
  * Angka Rupiah & Nilai Finansial: `JetBrains Mono` dengan `tabular-nums` (token `font-mono`)
* **Aksesibilitas minimum:** kontras teks ≥ 4.5:1, semua tombol ikon punya `aria-label`, fokus keyboard terlihat (`focus-visible:ring-2 ring-pertamina-blue`), modal & drawer dapat ditutup dengan `Esc`.

---

## 6. 🔁 Pemetaan Prototipe Vanilla → Komponen React

| Elemen / Fungsi di `frontend_vanilla/` | Komponen React (`frontend/src/komponen/`) | Catatan Porting |
| :--- | :--- | :--- |
| Topbar, `activeDocPickerBtn`, `btnStepProgress`, tombol Unduh | `Navbar/Navbar.jsx` | Judul paket dari store, bukan `innerText` manual |
| `navDropdownMenu` + `toggleNavMenu()` | `Navbar/HamburgerMenu.jsx` | Tutup saat klik di luar & tombol `Esc` |
| `chatStream`, `appendMessage()` | `Chat/ChatPanel.jsx` + `Chat/ChatBubble.jsx` | Render teks via JSX (auto-escape), **bukan** `innerHTML` |
| `.chat-tool-foldout`, `toggleToolFold()` | `Chat/ToolCallCard.jsx` | State buka/tutup lokal (`useState`) |
| Embed card "Lihat di Canvas / Unduh .DOCX" | `Chat/ArtifactCard.jsx` | Aksi via props/store, bukan `window.switchCanvasTab` |
| `quickChipsWrapper`, `sendQuickPrompt()` | `Chat/QuickActionChips.jsx` | Prompt dikirim sebagai argumen fungsi, bukan string di `onclick` |
| `userInput`, `btn-attach`, `btn-send`, `hiddenFileInput` | `Chat/ChatInput.jsx` | Enter = kirim, Shift+Enter = baris baru; tombol kirim memanggil handler yang sama |
| `workflowStepper`, `renderStepper()` | `Chat/WorkflowStepper.jsx` (tambahan) | Langkah per mode dari `modeMeta` |
| Tab pill `previewTab/matrixTab/checklistTab` | `Canvas/CanvasToolbar.jsx` | Tab aktif disimpan di store |
| `getTenderTemplate()`, `getRKSTemplate()`, dll. | `Canvas/DocumentEditor.jsx` | Template jadi komponen JSX per jenis dokumen; data dari store/API |
| Matriks HPS, K&R, TKDN | `Canvas/MatrixView.jsx` | Format Rupiah via `Intl.NumberFormat('id-ID')` |
| Checklist 86 STK | `Canvas/StkComplianceView.jsx` | Data dari tabel `procurement_stk_rule` |
| Vertical docked restore tab | `Common/VerticalRestoreTab.jsx` | – |
| Progress drawer (`renderDrawer()`) | `Common/ProgressDrawer.jsx` | – |
| Popup 4 pilihan dokumen (`chatPopupOverlay`) | `Common/DocPickerModal.jsx` | Fokus terkunci di dalam modal |
| `confirm()` reset sesi, `alert()` regulasi/hapus KB | `Common/ConfirmDialog.jsx`, `Common/Toast.jsx` | Ganti seluruh `alert`/`confirm` bawaan browser |
| `AppStateManager` (`state.js`) | `services/useAppStore.js` (Zustand) | Data demo dipindah ke `src/demo/` & berisi **data fiktif** |
| `ApiService` (`api.js`) | `services/api.js` | Base URL relatif, token otomatis, tanpa fallback demo diam-diam |

---

## 7. 🐞 Bug & Utang Teknis Prototipe yang Wajib Diperbaiki Saat Porting

| # | Masalah di `frontend_vanilla/` | Lokasi | Penanganan di React |
| :---: | :--- | :--- | :--- |
| 1 | Tombol **Kirim** memanggil `sendUserMessage()` yang tidak pernah didefinisikan; pesan hanya terkirim lewat Enter. | `index.html:172` | `ChatInput` memakai satu handler `onSubmit` untuk tombol & Enter. |
| 2 | **XSS**: teks user dan nama berkas dimasukkan ke `innerHTML`. | `js/chat.js:418`, `:423` | Render via JSX; Markdown AI disanitasi DOMPurify. |
| 3 | Backend `api.py` belum memasang CORS dan health check memakai `mode: 'no-cors'` (selalu dianggap hidup), sehingga ekstraksi gagal lalu diam-diam jatuh ke data demo. | `js/api.js:21`, `api.py` | Proxy Vite `/api` + `GET /api/health`; error ditampilkan ke user. |
| 4 | Berkas `.xlsx` BoQ dikirim sebagai `file_rks`; tanggal `"04 Desember 2025"` di-hardcode. | `js/app.js` (`handleFileSelected`) | Tentukan field dari ekstensi/pilihan user; tanggal dari input user / hari ini. |
| 5 | Data demo memuat nama pejabat & NPWP yang tampak asli. | `js/state.js` | Ganti dengan data fiktif. |
| 6 | `URL.revokeObjectURL` dipanggil segera setelah `click()`; di beberapa browser unduhan bisa batal. | `js/api.js` (`_downloadBlob`) | Revoke dengan `setTimeout(..., 0)` atau setelah event selesai. |
| 7 | Pola `onclick="fungsiGlobal('${string}')"` rawan pecah bila string berisi tanda kutip dan mengotori `window`. | `js/chat.js`, `js/canvas.js`, `index.html` | Event handler React (`onClick={() => ...}`). |
| 8 | `alert()`/`confirm()` bawaan browser untuk regulasi, reset, dan hapus KB. | `js/app.js`, `js/canvas.js:544` | `ConfirmDialog` & `Toast`. |

---

## 8. 🚀 Rencana Pentahapan Eksekusi (Roadmap Front-End)

Roadmap ini merupakan rincian sisi UI dari Fase 1–4 masterplan.

### Tahap A: Prototipe Vanilla ✅ (Selesai)
* [x] Pembuatan draft arsitektur `draft_perencanaan_frontend.md`
* [x] Struktur `frontend_vanilla/` (`css/`, `js/`) & design tokens
* [x] Chat feed, micro-card, reasoning box, tool-call accordion, stepper, quick chips
* [x] Live canvas (preview dokumen, tab matriks HPS, tab checklist STK), fullscreen, vertical restore tab
* [x] Progress drawer, hamburger menu, Doc Picker modal 4 pilihan

### Tahap B: Fondasi React (masterplan Fase 1)
* [x] Scaffold Vite + React + Tailwind CSS v3 + token Pertamina
* [x] Bersihkan template Vite, set `<title>`, `lang="id"`, muat font
* [x] Proxy `/api` di `vite.config.js`
* [x] Store global (`useAppStore`) + layout split-view responsif di `App.jsx`

### Tahap C: Porting Komponen (masterplan Fase 1 & 3)
* [x] Navbar, HamburgerMenu, DocPickerModal
* [x] ChatPanel, ChatBubble, ChatInput (perbaiki bug #1, #2, #4), QuickActionChips, ToolCallCard, ArtifactCard, ExtractionCard
* [x] CanvasReview, CanvasToolbar, DocumentEditor (pratinjau; edit per klausul menyusul), MatrixView, StkComplianceView, KnowledgeBaseView
* [x] ProgressDrawer, VerticalRestoreTab, ConfirmDialog, Toast

### Tahap D: Integrasi Data & API (masterplan Fase 2–4)
* [ ] LoginPage + ProtectedRoute + penyisipan token di `api.js`
* [x] Upload & ekstraksi nyata → micro-card verifikasi → terapkan ke canvas
* [x] Fitur *Real-time Highlighting* saat ada perubahan nilai dari percakapan (balasan chat masih simulasi sampai `/api/chat/stream` tersedia)
* [ ] Streaming balasan AI (SSE) dengan indikator mengetik
* [ ] Unduh `.docx` dari endpoint generate

### Tahap E: Validasi & Polishing UI/UX
* [ ] Uji responsif (desktop, tablet, ponsel) & aksesibilitas keyboard
* [ ] Penyempurnaan micro-animations (transisi tab, badge sync), hormati `prefers-reduced-motion`
* [ ] Setelah seluruh fitur terporting dan diverifikasi, `frontend_vanilla/` dapat dihapus dari repo (tetap ada di riwayat Git)

---
*Dokumen ini menjadi acuan UI/UX untuk pembuatan front-end di `agenticv3/frontend/`. Arsitektur sistem secara keseluruhan mengacu pada `draft_perencanaan_proyek_ITeC.md`.*
