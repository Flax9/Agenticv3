# 📋 Draft Perencanaan Pengembangan Front-End: `agenticv3`
### Pertamina Procurement AI Copilot & Live Canvas (Versi 3.0)

**Dokumen Perencanaan Teknis & Arsitektur Front-End**  
*Tanggal:* 18 Oktober 2026  
*Folder Target:* `agenticv3/`  
*Basis Sistem Backend:* `Agentic_Rag_Pertamina_camp/api.py` (FastAPI @ Port 8000)  
*Acuan Regulasi:* Pedoman Pengadaan No. `A03-001/PNG200000/2024-S9` Rev. 1  

---

## 1. 🎯 Tujuan & Visi Front-End `agenticv3`

Mentransformasikan sistem pengadaan dari antarmuka formulir bertingkat yang kaku (*form-based*) menjadi antarmuka **Generative AI Copilot + Live Document Canvas** yang modern, responsif, dan interaktif:
1. **Percakapan Terarah (Guided Dialogue):** Pengguna dapat berdialog secara natural, mengunggah dokumen acuan (BoQ/TOR), dan meminta revisi klausul secara selektif.
2. **Sinkronisasi Dua Arah (*Bi-directional Sync*):** Setiap perubahan pada chat langsung tercermin secara visual di kanvas dokumen sebelah kanan dengan penanda *highlight*.
3. **Kartu Interaktif Cerdas (*Generative Micro-Cards*):** Ekstraksi parameter otomatis langsung tersaji dalam kartu verifikasi yang bisa di-*inline edit* tanpa membuat user mengetik puluhan butir data manual.
4. **Kepatuhan Terukur (*Compliance Scorecard*):** Menyediakan visibilitas terhadap pemenuhan 86 butir checklist mandatory pra-tender secara *real-time*.

---

## 2. 🏛️ Arsitektur Tampilan: *Split-View Canvas Model*

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🔴 TOPBAR: Branding Pertamina | Context Pill (Paket Aktif) | Pedoman PBJ | Unduh .DOCX     │
├──────────────────────────────────────────────┬──────────────────────────────────────────────┤
│ 💬 LEFT PANE (42% - 45%): AI COPILOT CHAT    │ 📄 RIGHT PANE (55% - 58%): DYNAMIC CANVAS    │
│                                              │                                              │
│ 1. Workflow Stepper Bar                      │ 1. Canvas Topbar: Tab Switcher               │
│    [Upload] -> [Ekstrak] -> [Verif] -> [Doc] │    [📄 Pratinjau Dokumen (.DOCX)]            │
│ 2. Chat Feed Stream:                         │    [📊 Matriks HPS, K&R & TKDN]              │
│    • Pesan AI & User Bubbles                 │    [✅ Checklist STK Mandatory (86 Poin)]    │
│    • Reasoning Collapsible Box               │                                              │
│    • In-Chat Extraction Card                 │ 2. Sheet Canvas Body:                        │
│    • Status Step Indicators                  │    • Naskah Resmi Pertamina (Header Navy)    │
│ 3. Quick Action Chips                        │    • Tabel 40 Poin Ketentuan Khusus IKPP     │
│ 4. File Drag & Drop + Input Box              │    • Draft 20 Pasal Kontrak Definitif        │
│    (Support: PDF BoQ, TOR, XLSX)             │    • Real-time Highlight saat Diperbarui     │
└──────────────────────────────────────────────┴──────────────────────────────────────────────┘
```

---

## 3. 📂 Rencana Struktur Direktori `agenticv3/`

```text
agenticv3/
├── draft_perencanaan_frontend.md   # Dokumen rancangan & roadmap ini
├── index.html                      # Entry point utama aplikasi front-end
│
├── css/
│   ├── main.css                    # Design system (variabel warna Pertamina, typography, layout)
│   ├── chat.css                    # Styling chat feed, bubble, in-chat card, stepper, quick chips
│   └── canvas.css                  # Styling naskah dokumen formal, tabel IKPP, matrix HPS, scorecard
│
├── js/
│   ├── state.js                    # State management (session, metadata paket, chat messages, canvas)
│   ├── api.js                      # Service koneksi REST ke FastAPI backend (localhost:8000)
│   ├── chat.js                     # Handler pesan chat, rendering micro-cards, quick chips
│   ├── canvas.js                   # Handler rendering dokumen, tab switcher, inline editor, highlighting
│   └── app.js                      # Inisialisasi aplikasi & event listener global
│
└── assets/
    ├── icons/                      # SVG icons (upload, send, download, check, warning, etc.)
    └── img/                        # Logo resmi Pertamina & placeholder
```

---

## 4. 🔌 Integrasi Endpoint Backend (`api.py`)

Front-end `agenticv3` dirancang untuk terhubung langsung ke backend FastAPI di `http://127.0.0.1:8000`:

| Modul / Fitur | Endpoint Backend | Method | Payload / Fungsi |
| :--- | :--- | :---: | :--- |
| **Ekstraksi Otomatis** | `/api/extract-tender-metadata` | `POST` | Mengunggah file PDF BoQ & RKS → mengembalikan JSON ringkasan metadata |
| **Generate Tender** | `/api/generate-tender` | `POST` | Menghasilkan paket lengkap Dokumen Tender Versi 2.0 (`.docx`) |
| **Generate RKS** | `/api/generate-rks` | `POST` | Menghasilkan Dokumen RKS teknis spesifik (`.docx`) |
| **Generate Kontrak** | `/api/generate-kontrak` | `POST` | Menghasilkan naskah Rancangan Kontrak Definitif 20 Pasal (`.docx`) |
| **Generate Amendemen**| `/api/generate-amendemen` | `POST` | Menghasilkan draft Addendum dengan tabel lama vs baru (`.docx`) |
| **Knowledge Base** | `/api/kb/list`, `/api/kb/ingest` | `GET/POST`| Mengelola berkas referensi RAG pada Qdrant Cloud |

---

## 5. 🎨 Standar Visual & Palet Warna (Pertamina Corporate Identity)

* **Pertamina Navy:** `#002D62` (Warna utama header, tombol primer, dan judul naskah resmi)
* **Pertamina Red:** `#ED1B24` (Aksen dinamis, border navbar bawah, dan cap confidential)
* **Pertamina Light Blue:** `#0072CE` (Hover state, link, dan fokus input form)
* **Background Canvas:** `#F4F6F9` (Abu-abu lembut standar korporat enterprise)
* **Sheet Background:** `#FFFFFF` dengan shadow kontur tipis `0 8px 30px rgba(0, 0, 0, 0.08)`
* **Tipografi:** 
  * Naskah & Antarmuka: `Plus Jakarta Sans` / `Inter` (bersih, formal, mudah dibaca)
  * Angka Rupiah & Nilai Finansial: `JetBrains Mono` (digit presisi, tabular monospaced)

---

## 6. 🚀 Rencana Pentahapan Eksekusi (Roadmap)

### Fase 1: Kerangka Struktur & Design System (Selesai pada langkah ini)
* [x] Pembuatan draft arsitektur `draft_perencanaan_frontend.md`
* [ ] Penyiapan struktur folder `css/`, `js/`, `assets/`
* [ ] Implementasi `css/main.css` (Design tokens & base grid layout)

### Fase 2: Komponen Interaktif (Chat & Canvas Engine)
* [ ] Implementasi `js/state.js` sebagai pusat reaktifitas data
* [ ] Implementasi `js/chat.js` & `css/chat.css` (Feed, Micro-Card Parameter, Reasoning Box, Stepper)
* [ ] Implementasi `js/canvas.js` & `css/canvas.css` (Dokumen preview dinamis, tab HPS, tab Checklist STK)

### Fase 3: Integrasi Data & API Bridge
* [ ] Implementasi `js/api.js` (penanganan upload `multipart/form-data`, error handling, download direct file response)
* [ ] Fitur *Real-time Highlighting* saat ada perubahan nilai dari percakapan

### Fase 4: Validasi & Polishing UI/UX
* [ ] Pengujian responsivitas dan rendering pada browser
* [ ] Penyempurnaan micro-animations (indikator pengetikan, transisi tab mulus, badge sync)

---
*Dokumen ini menjadi acuan kerja utama untuk pembuatan front-end di direktori `agenticv3`.*
