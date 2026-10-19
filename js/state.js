/**
 * ================================================================
 * STATE MANAGEMENT (CENTRAL STORE) - agenticv3
 * ================================================================
 * Coordinates reactive updates between Chat Feed and Document Canvas
 * across 5 Document Modes:
 *   1. 'tender'    : Dokumen Tender Lengkap (IKPP + Kontrak)
 *   2. 'rks'       : Dokumen RKS (Rencana Kerja & Syarat)
 *   3. 'contract'  : Rancangan Kontrak Definitif (20 Pasal)
 *   4. 'amendment' : Draft Amendemen / Addendum
 *   5. 'kb'        : Knowledge Base Management (Qdrant Cloud)
 */

class AppStateManager {
  constructor() {
    this.subscribers = [];
    
    this.modeMeta = {
      tender: {
        title: "Dokumen Tender (IKPP & Kontrak)",
        badge: "Versi 2.0 (40 Poin & Kontrak)",
        stepper: ["Upload BOQ/RKS", "Auto-Ekstraksi", "Verifikasi Klausul", "Terbitkan Dokumen"]
      },
      rks: {
        title: "Dokumen RKS",
        badge: "Spesifikasi Teknis (Bab I-V)",
        stepper: ["Input Lingkup & BoQ", "Pencarian KB", "Review Bab RKS", "Export Word"]
      },
      contract: {
        title: "Rancangan Kontrak Definitif",
        badge: "20 Pasal Standar Pertamina",
        stepper: ["Identitas Para Pihak", "Nilai & Waktu", "Review 20 Pasal", "Finalisasi Kontrak"]
      },
      amendment: {
        title: "Draft Amendemen / Addendum",
        badge: "Legal Drafting & Komparasi",
        stepper: ["Referensi Kontrak Asal", "Item Perubahan", "Konsideran Hukum", "Export Addendum"]
      },
      kb: {
        title: "Knowledge Base Management",
        badge: "Qdrant Cloud Vector Store",
        stepper: ["Pilih Collection", "Upload Referensi", "Chunking & Indexing", "Kelola Dokumen"]
      }
    };

    // Initialize Default State
    this.state = {
      currentMode: 'tender',
      currentStep: 1, // Start on step 1 (Upload/Start)
      activeCanvasTab: 'previewTab',
      isSessionStarted: false,
      apiBaseUrl: "http://127.0.0.1:8000",

      // Tender Package Data
      tenderData: {
        nama_pengadaan: "Pekerjaan Overhaul Tangki 41T-313 Fuel Terminal Balikpapan",
        nomor_tender: "No.Project/DT/PND970000/2026-S7",
        tanggal: "04 Desember 2025",
        pejabat_procurement_nama: "Rigga Widar Atmagi",
        pejabat_procurement_jabatan: "Area Manager Procurement Kalimantan",
        pejabat_berwenang: "Sr. Manager Opt. & Maint. Regional Kalimantan",
        pengawas_pekerjaan: "Region Manager RPD Regional Kalimantan",
        jenis_kontrak: "Gabungan Harga Satuan & Lumpsum",
        resiko_csms: "Tinggi",
        csms_grade: "≥ 70 (Kategori High Risk)",
        tkdn_minimal: 20.12,
        prime_cost: 13283434534,
        keuntungan_risiko_persen: 8,
        total_dengan_kr: 14346100000,
        masa_pemeliharaan_hari: 90,
        jaminan_pelaksanaan_persen: 5,
        lingkup_pekerjaan: "Restorasi shell tangki, hydrotest tangki, penggantian plat baja ASTM A36 12mm, internal coating epoxy sesuai standar API 650 & API 653."
      },

      // RKS Package Data
      rksData: {
        jenis_pekerjaan: "Pembangunan Fasilitas Tangki Air 1000 KL",
        detail_pekerjaan: "Pengadaan material, fabrikasi shell tangki, instalasi perpipaan, dan testing commissioning.",
        lokasi: "Fuel Terminal Balikpapan",
        resiko_csms: "HIGH",
        nomor_dokumen: "RKS-FT-BPP-2026",
        nama_perusahaan: "PT PERTAMINA PATRA NIAGA",
        bab_count: 5
      },

      // Contract Package Data
      contractData: {
        nama_pekerjaan: "Pekerjaan Penggantian Pipa Transmisi BBM Balikpapan",
        nomor_kontrak: "SP-041/PND970000/2026-S7",
        tanggal_kontrak: "15 Januari 2026",
        lokasi_pekerjaan: "Fuel Terminal Balikpapan",
        jenis_kontrak: "Harga Satuan",
        nama_vendor: "PT Rekayasa Industri Energi",
        npwp_vendor: "01.234.567.8-012.000",
        nilai_kontrak: 8750000000,
        durasi_hari: 180,
        masa_pemeliharaan: 90,
        resiko_csms: "Tinggi",
        pejabat_ttd_pertamina: "Sr. Manager Opt. & Maint. Regional Kalimantan"
      },

      // Amendment Data
      amendmentData: {
        nomor_addendum: "ADD-01/SP-041/2026",
        tanggal_amendemen: "20 Februari 2026",
        nomor_kontrak_asal: "SP-041/PND970000/2026-S7",
        judul_pekerjaan: "Pekerjaan Penggantian Pipa Transmisi BBM Balikpapan",
        nama_vendor: "PT Rekayasa Industri Energi",
        nilai_kontrak_asal: 8750000000,
        nilai_kontrak_baru: 9450000000,
        alasan: "Perubahan jalur pipa akibat penyesuaian kontur tanah dan utilitas eksisting (volume bertambah 12%)."
      },

      // Knowledge Base State
      kbState: {
        selectedCollection: "rks_kb",
        documents: {
          "RKS-041T304-PEKERJAAN OVERHAUL TANKI.pdf": 34,
          "RKS-36T102-PEKERJAAN RESTORASI TANGKI.pdf": 48,
          "RKS_Pembangunan Tangki Air Kapasitas 1_000 KL.pdf": 26
        }
      },

      messages: []
    };
  }

  subscribe(callback) {
    this.subscribers.push(callback);
  }

  notify(changedKey, payload) {
    this.subscribers.forEach(cb => cb(this.state, changedKey, payload));
  }

  setMode(newMode) {
    if (!this.modeMeta[newMode]) return;
    this.state.currentMode = newMode;
    this.state.currentStep = 1;
    this.state.isSessionStarted = false;
    this.state.messages = [];
    this.notify('modeChange', newMode);
  }

  setStep(stepNumber) {
    this.state.currentStep = stepNumber;
    this.notify('stepChange', stepNumber);
  }

  setCanvasTab(tabId) {
    this.state.activeCanvasTab = tabId;
    this.notify('activeCanvasTab', tabId);
  }

  updatePackageField(key, value) {
    const mode = this.state.currentMode;
    if (mode === 'tender') this.state.tenderData[key] = value;
    else if (mode === 'rks') this.state.rksData[key] = value;
    else if (mode === 'contract') this.state.contractData[key] = value;
    else if (mode === 'amendment') this.state.amendmentData[key] = value;

    this.notify('packageData', { mode, key, value });
  }

  getActiveData() {
    const mode = this.state.currentMode;
    if (mode === 'tender') return this.state.tenderData;
    if (mode === 'rks') return this.state.rksData;
    if (mode === 'contract') return this.state.contractData;
    if (mode === 'amendment') return this.state.amendmentData;
    return {};
  }

  formatRupiah(num) {
    try {
      return "Rp " + Number(num).toLocaleString('id-ID');
    } catch (e) {
      return "Rp " + num;
    }
  }
}

window.appState = new AppStateManager();
