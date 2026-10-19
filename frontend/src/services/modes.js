// Metadata 5 mode kerja: 4 jenis dokumen pengadaan + Knowledge Base
export const MODE_META = {
  tender: {
    icon: '📄',
    title: 'Dokumen Tender (IKPP & Kontrak)',
    badge: 'Versi 2.0 (40 Poin & Kontrak)',
    stepper: ['Pilih BoQ/RKS dari Drive', 'Auto-Ekstraksi', 'Verifikasi Klausul', 'Terbitkan Dokumen'],
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
    stepper: ['Informasi Pekerjaan', 'BoQ & Referensi KB', 'Review Draf RKS', 'Export Word'],
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
    stepper: ['Isi Folder Drive', 'Sinkronkan', 'Chunking & Indexing', 'Kelola Dokumen'],
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

// Saran pesan cepat. Hanya mode RKS yang sudah punya agent chat dari tim AI;
// mode lain belum diberi saran agar user tidak mengira chat bisa mengubah dokumennya.
const RKS_CHIPS = [
  { text: '📝 Mulai Buat RKS', prompt: 'Saya ingin membuat dokumen RKS baru' },
  { text: '📋 Bab Wajib RKS', prompt: 'Apa saja bab yang wajib ada dalam dokumen RKS?' },
  { text: '🛡️ Persyaratan CSMS', prompt: 'Apa persyaratan CSMS untuk pekerjaan berisiko tinggi?' },
]

// Saran saat agent sedang menunggu jawaban tertentu (node interrupt)
const AWAITING_CHIPS = {
  upload_boq: [{ text: '⏭️ Lanjut Tanpa BoQ', prompt: 'lewati' }],
  review_rks: [{ text: '✅ Setuju & Ekspor .docx', prompt: 'setuju' }],
}

export function quickChips(mode, awaiting) {
  if (mode !== 'rks') return []
  return AWAITING_CHIPS[awaiting] ?? RKS_CHIPS
}

export const KB_COLLECTIONS = [
  { id: 'rks_kb', icon: '📋' },
  { id: 'contract_kb', icon: '📝' },
  { id: 'amendment_kb', icon: '📎' },
]
