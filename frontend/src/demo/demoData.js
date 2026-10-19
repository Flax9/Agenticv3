// Data contoh untuk tombol "Muat Data Contoh (Demo)".
// SELURUH nama orang, vendor, NPWP, dan nomor dokumen di sini FIKTIF.
// Jangan memasukkan data pengadaan asli ke repositori.

export const DEMO_PACKAGES = {
  tender: {
    nama_pengadaan: 'Pekerjaan Overhaul Tangki 41T-313 Fuel Terminal Balikpapan',
    nomor_tender: 'DEMO/DT/0001/2026',
    tanggal: '04 Desember 2025',
    pejabat_procurement_nama: 'Andi Pratama (Contoh)',
    pejabat_procurement_jabatan: 'Area Manager Procurement Kalimantan',
    pejabat_berwenang: 'Sr. Manager Opt. & Maint. Regional Kalimantan',
    pengawas_pekerjaan: 'Region Manager RPD Regional Kalimantan',
    metode_pemenuhan: 'Tender Terbatas',
    jenis_kontrak: 'Gabungan Harga Satuan & Lumpsum',
    resiko_csms: 'Tinggi',
    csms_grade: '≥ 70 (Kategori High Risk)',
    tkdn_minimal: 20.12,
    prime_cost: 13283434534,
    keuntungan_risiko_persen: 8,
    total_dengan_kr: 14346100000,
    masa_pemeliharaan_hari: 90,
    jaminan_pelaksanaan_persen: 5,
    lingkup_pekerjaan:
      'Restorasi shell tangki, hydrotest tangki, penggantian plat baja ASTM A36 12mm, internal coating epoxy sesuai standar API 650 & API 653.',
    boq_items: [
      { uraian: 'Mobilisasi & Demobilisasi Peralatan Hydrotest', volume: 1, satuan: 'Lot', harga: 350000000 },
      { uraian: 'Penggantian Plat Tangki Baja ASTM A36 12mm', volume: 45, satuan: 'Ton', harga: 32000000 },
      { uraian: 'Blasting & Protective Internal Coating Epoxy', volume: 3200, satuan: 'm²', harga: 420000 },
      { uraian: 'Mechanical Calibration & NDT Inspection', volume: 1, satuan: 'Paket', harga: 580000000 },
    ],
  },

  rks: {
    jenis_pekerjaan: 'Pembangunan Fasilitas Tangki Air 1000 KL',
    detail_pekerjaan: 'Pengadaan material, fabrikasi shell tangki, instalasi perpipaan, dan testing commissioning.',
    lokasi: 'Fuel Terminal Balikpapan',
    resiko_csms: 'HIGH',
    nomor_dokumen: 'DEMO-RKS-0001-2026',
    nama_perusahaan: 'PT PERTAMINA PATRA NIAGA',
    bab_count: 5,
  },

  contract: {
    nama_pekerjaan: 'Pekerjaan Penggantian Pipa Transmisi BBM Balikpapan',
    nomor_kontrak: 'DEMO-SP-0001/2026',
    tanggal_kontrak: '15 Januari 2026',
    lokasi_pekerjaan: 'Fuel Terminal Balikpapan',
    jenis_kontrak: 'Harga Satuan',
    nama_vendor: 'PT Contoh Rekayasa Energi',
    npwp_vendor: '00.000.000.0-000.000',
    nilai_kontrak: 8750000000,
    durasi_hari: 180,
    masa_pemeliharaan: 90,
    resiko_csms: 'Tinggi',
    pejabat_ttd_pertamina: 'Sr. Manager Opt. & Maint. Regional Kalimantan',
  },

  amendment: {
    nomor_addendum: 'DEMO-ADD-01/2026',
    tanggal_amendemen: '20 Februari 2026',
    nomor_kontrak_asal: 'DEMO-SP-0001/2026',
    judul_pekerjaan: 'Pekerjaan Penggantian Pipa Transmisi BBM Balikpapan',
    nama_vendor: 'PT Contoh Rekayasa Energi',
    nilai_kontrak_asal: 8750000000,
    nilai_kontrak_baru: 9450000000,
    alasan: 'Perubahan jalur pipa akibat penyesuaian kontur tanah dan utilitas eksisting (volume bertambah 12%).',
  },
}

// Contoh isi checklist STK sebelum katalog 86 aturan tersedia dari database (Fase 2)
export const DEMO_STK_ITEMS = [
  { status: 'done', title: "Item 6: Judul Pekerjaan tanpa 'Gabungan Barang & Jasa'", note: 'TKO B3.2.4-03 Lamp. 3 — Otomatis tervalidasi di cover dan IKPP.' },
  { status: 'done', title: 'Item 10: General Terms & Conditions (GTC) 30 Pasal', note: 'Pedoman A03-001 — Terkompilasi penuh di BAB II naskah tender.' },
  { status: 'done', title: 'Item 15: Komposisi HPS (Prime Cost + Keuntungan & Risiko)', note: 'TKI C3.2.3-01 — Rumus otomatis pembulatan rupiah.' },
  { status: 'partial', title: 'Item 2: Lingkup kerja bebas dari bias merek tertutup', note: 'Perlu konfirmasi AI guardrail untuk nama brand/vendor spesifik.' },
  { status: 'pending', title: 'Item 16: Verifikasi Purchase Requisition (PR) ter-release di SAP', note: 'Tahap integrasi API SAP Enterprise Pertamina.' },
]

export const DEMO_STK_SUMMARY = { done: 32, partial: 10, pending: 44, total: 86 }

export const DEMO_ATTACHMENT = {
  tender: { name: 'BOQ_Overhaul_Tangki_41T313.pdf', size: '352 KB' },
  rks: { name: 'Spesifikasi_Teknis_Tangki.pdf', size: '187 KB' },
}
