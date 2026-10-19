// Metadata 5 mode kerja: 4 jenis dokumen pengadaan + Knowledge Base
export const MODE_META = {
  tender: {
    icon: '📄',
    title: 'Dokumen Tender (IKPP & Kontrak)',
    badge: 'Versi 2.0 (40 Poin & Kontrak)',
    stepper: ['Upload BOQ/RKS', 'Auto-Ekstraksi', 'Verifikasi Klausul', 'Terbitkan Dokumen'],
    matrixLabel: '📊 Matriks HPS',
    artifacts: [
      { tab: 'previewTab', title: 'Dokumen Tender Versi 2.0 (IKPP & Kontrak)', format: '.docx', desc: '40 Poin Ketentuan Khusus & Kontrak' },
      { tab: 'matrixTab', title: 'Matriks HPS, K&R & Komposisi TKDN', format: 'Sheet', desc: 'Kalkulasi Prime Cost + K&R (8%)' },
      { tab: 'checklistTab', title: 'Checklist STK Mandatory (86 Butir)', format: 'Matrix', desc: 'Kepatuhan Pra-Tender Regional' },
    ],
  },
  rks: {
    icon: '📋',
    title: 'Dokumen RKS',
    badge: 'Spesifikasi Teknis (Bab I-V)',
    stepper: ['Input Lingkup & BoQ', 'Pencarian KB', 'Review Bab RKS', 'Export Word'],
    matrixLabel: '📊 Ringkasan',
    artifacts: [
      { tab: 'previewTab', title: 'Spesifikasi Teknis RKS (Bab I - V)', format: '.docx', desc: 'Naskah 5 Bab Spesifikasi Teknis & K3' },
    ],
  },
  contract: {
    icon: '📝',
    title: 'Rancangan Kontrak Definitif',
    badge: '20 Pasal Standar Pertamina',
    stepper: ['Identitas Para Pihak', 'Nilai & Waktu', 'Review 20 Pasal', 'Finalisasi Kontrak'],
    matrixLabel: '📊 Ringkasan',
    artifacts: [
      { tab: 'previewTab', title: 'Naskah Rancangan Kontrak (20 Pasal)', format: '.docx', desc: 'Perjanjian Definitif Korporat Pertamina' },
    ],
  },
  amendment: {
    icon: '📎',
    title: 'Draft Amendemen / Addendum',
    badge: 'Legal Drafting & Komparasi',
    stepper: ['Referensi Kontrak Asal', 'Item Perubahan', 'Konsideran Hukum', 'Export Addendum'],
    matrixLabel: '📊 Komparasi',
    artifacts: [
      { tab: 'previewTab', title: 'Draft Addendum Kontrak (Lama vs Baru)', format: '.docx', desc: 'Konsideran Hukum & Komparasi Klausul' },
    ],
  },
  kb: {
    icon: '🗄️',
    title: 'Knowledge Base Management',
    badge: 'Qdrant Vector Store',
    stepper: ['Pilih Collection', 'Upload Referensi', 'Chunking & Indexing', 'Kelola Dokumen'],
    matrixLabel: null,
    artifacts: [
      { tab: 'previewTab', title: 'Indeks Koleksi Qdrant', format: 'Vector DB', desc: 'Knowledge Base Regulasi Pengadaan' },
    ],
  },
}

// Pilihan pada Doc Picker (mode 'kb' dibuka lewat menu, bukan dari sini)
export const DOC_CHOICES = [
  { mode: 'tender', icon: '📄', title: 'Dokumen Tender Lengkap', desc: 'Paket resmi IKPP 40 Poin, Lampiran 1A–8, dan Bagian B Kontrak.', tag: 'Versi 2.0' },
  { mode: 'rks', icon: '📋', title: 'Dokumen RKS', desc: 'Rencana Kerja & Syarat teknis, spesifikasi material, & K3 CSMS.', tag: '5 Bab Teknis' },
  { mode: 'contract', icon: '📝', title: 'Kontrak Definitif', desc: 'Perjanjian pemborongan pekerjaan mandiri 20 pasal definitif siap cetak.', tag: '20 Pasal Standar' },
  { mode: 'amendment', icon: '📎', title: 'Draft Amendemen', desc: 'Addendum perubahan nilai/waktu dengan tabel komparasi lama vs baru.', tag: 'Legal Drafting' },
]

export const QUICK_CHIPS = {
  tender: [
    { text: '⏱️ Ubah Pemeliharaan 180 Hari', prompt: 'Atur Masa Pemeliharaan menjadi 180 hari kalender' },
    { text: '🏦 Jaminan Pelaksanaan 5%', prompt: 'Wajibkan Jaminan Pelaksanaan 5% dari Nilai Kontrak' },
    { text: '📊 Cek Skor Kepatuhan STK', prompt: 'Tampilkan skor kepatuhan checklist mandatory' },
    { text: '💰 Lihat Rincian HPS', prompt: 'Lihat rincian kalkulasi HPS dan K&R' },
  ],
  rks: [
    { text: '➕ Tambah Spesifikasi Material Baja', prompt: 'Tambahkan rincian teknis plat baja ASTM A36 pada Bab II' },
    { text: '🛡️ Standar CSMS Kategori Tinggi', prompt: 'Pastikan persyaratan CSMS minimal kategori High Risk' },
    { text: '📋 Lihat Struktur 5 Bab', prompt: 'Tampilkan draft struktur bab RKS lengkap' },
  ],
  contract: [
    { text: '🏢 Ganti Vendor', prompt: 'Ganti pihak kedua / vendor menjadi PT Contoh Energi Utama' },
    { text: '💰 Nilai Kontrak Rp 9.5 Miliar', prompt: 'Ubah total nilai kontrak menjadi Rp 9.500.000.000' },
    { text: '⚖️ Denda 1 per mil per hari', prompt: 'Terapkan ketentuan denda keterlambatan 1 permil per hari (maks 5%)' },
  ],
  amendment: [
    { text: '📈 Tambah Nilai Kontrak 12%', prompt: 'Buatkan addendum penambahan nilai kontrak sebesar 12% karena volume bertambah' },
    { text: '⏱️ Perpanjang Waktu 45 Hari', prompt: 'Tambahkan klausul perpanjangan waktu pelaksanaan selama 45 hari kalender' },
    { text: '📜 Lihat Tabel Komparasi', prompt: 'Tampilkan tabel perbandingan kondisi lama vs kondisi baru' },
  ],
  kb: [
    { text: '📂 Lihat Dokumen rks_kb', prompt: 'Tampilkan daftar berkas terindeks di collection rks_kb' },
    { text: '📝 Lihat contract_kb', prompt: 'Tampilkan daftar berkas di collection contract_kb' },
  ],
}

export const KB_COLLECTIONS = [
  { id: 'rks_kb', icon: '📋' },
  { id: 'contract_kb', icon: '📝' },
  { id: 'amendment_kb', icon: '📎' },
]
