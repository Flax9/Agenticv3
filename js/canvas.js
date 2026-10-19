/**
 * ================================================================
 * CANVAS CONTROLLER - agenticv3
 * ================================================================
 * Dynamically renders the live document sheet according to the active mode:
 *   - 'tender'    : Dokumen Tender (IKPP 40 Poin & Bagian B Kontrak)
 *   - 'rks'       : RKS Spesifikasi Teknis (Bab I - V)
 *   - 'contract'  : Rancangan Kontrak Definitif (20 Pasal)
 *   - 'amendment' : Draft Addendum (Tabel Lama vs Baru)
 *   - 'kb'        : Knowledge Base Browser & Manager
 */

class CanvasController {
  constructor(state, api) {
    this.state = state;
    this.api = api;
    this.canvasBody = document.querySelector('.canvas-body');
  }

  init() {
    this.state.subscribe((currentState, changedKey, payload) => {
      if (changedKey === 'modeChange' || changedKey === 'activeCanvasTab') {
        this.renderCanvas();
      } else if (changedKey === 'packageData') {
        this.handleFieldUpdate(payload);
      }
    });

    this.renderCanvas();
  }

  switchTab(tabId, btnElement) {
    document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.tab-pill').forEach(b => b.classList.remove('active'));

    const targetTab = document.getElementById(tabId);
    if (targetTab) targetTab.classList.add('active');
    if (btnElement) btnElement.classList.add('active');

    this.state.state.activeCanvasTab = tabId;
  }

  renderCanvas() {
    const mode = this.state.state.currentMode;
    const tab = this.state.state.activeCanvasTab;

    // Update tab bar visibility
    const previewTabBtn = document.querySelector('.tab-pill[data-tab="previewTab"]');
    const matrixTabBtn = document.querySelector('.tab-pill[data-tab="matrixTab"]');
    const checklistTabBtn = document.querySelector('.tab-pill[data-tab="checklistTab"]');

    if (mode === 'kb') {
      if (previewTabBtn) previewTabBtn.innerText = "🗄️ Collections Qdrant";
      if (matrixTabBtn) matrixTabBtn.style.display = "none";
      if (checklistTabBtn) checklistTabBtn.style.display = "none";
    } else {
      if (previewTabBtn) previewTabBtn.innerText = "📄 Pratinjau Dokumen (.DOCX)";
      if (matrixTabBtn) {
        matrixTabBtn.style.display = "flex";
        matrixTabBtn.innerText = mode === 'tender' ? "📊 Matriks HPS & TKDN" : (mode === 'amendment' ? "📊 Tabel Komparasi" : "📊 Rincian Teknis");
      }
      if (checklistTabBtn) {
        checklistTabBtn.style.display = "flex";
      }
    }

    // Render Preview Tab Content based on mode
    const previewContainer = document.getElementById('previewTab');
    if (previewContainer) {
      if (mode === 'tender') {
        previewContainer.innerHTML = this.getTenderTemplate();
      } else if (mode === 'rks') {
        previewContainer.innerHTML = this.getRKSTemplate();
      } else if (mode === 'contract') {
        previewContainer.innerHTML = this.getContractTemplate();
      } else if (mode === 'amendment') {
        previewContainer.innerHTML = this.getAmendmentTemplate();
      } else if (mode === 'kb') {
        previewContainer.innerHTML = this.getKBTemplate();
      }
    }
  }

  handleFieldUpdate({ mode, key, value }) {
    if (key === 'masa_pemeliharaan_hari') {
      const el = document.getElementById('tablePemeliharaan');
      if (el) {
        el.innerHTML = `<strong>${value} hari kalender</strong> sejak Serah Terima Pertama (BAST-1)`;
        this.flashHighlight(el);
      }
    } else if (key === 'jaminan_pelaksanaan_persen') {
      const el = document.getElementById('tableJaminan');
      if (el) {
        el.innerHTML = `Sebesar <strong>${value}%</strong> dari total nilai kontrak diterbitkan oleh Bank BUMN/Swasta Kelas A`;
        this.flashHighlight(el);
      }
    } else if (key === 'total_dengan_kr') {
      const el = document.getElementById('tablePasalNilai');
      if (el) {
        el.innerHTML = `Total nilai kontrak definitif adalah sebesar ${this.state.formatRupiah(value)} sudah termasuk PPN.`;
        this.flashHighlight(el);
      }
    }
  }

  flashHighlight(element) {
    element.classList.add('highlight-change');
    setTimeout(() => {
      element.classList.remove('highlight-change');
    }, 3000);
  }

  // 1. Dokumen Tender Template
  getTenderTemplate() {
    const t = this.state.state.tenderData;
    return `
      <div class="document-page-sheet">
        <div class="doc-formal-header">
          <div>
            <div class="doc-pertamina-title">PT PERTAMINA PATRA NIAGA</div>
            <div class="doc-unit-title">REGIONAL KALIMANTAN — FUNGSI PROCUREMENT</div>
          </div>
          <div class="doc-confidential-stamp">CONFIDENTIAL / RAHASIA</div>
        </div>

        <div class="doc-title-block">
          <div class="doc-main-heading">DOKUMEN TENDER (DT) — VERSI 2.0</div>
          <div class="doc-sub-heading">${t.nama_pengadaan.toUpperCase()}</div>
          <div class="doc-number-badge">Nomor: ${t.nomor_tender}</div>
        </div>

        <div class="doc-section-title">
          BAGIAN A: BAB I — KETENTUAN KHUSUS INSTRUKSI KEPADA PESERTA PENGADAAN (IKPP)
        </div>

        <table class="doc-table">
          <thead>
            <tr>
              <th style="width: 35px;">NO</th>
              <th style="width: 220px;">BUTIR KETENTUAN</th>
              <th>KETENTUAN KHUSUS PADA PAKET INI</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="col-no">1</td>
              <td class="col-item">Nama Pengadaan</td>
              <td>${t.nama_pengadaan}</td>
            </tr>
            <tr>
              <td class="col-no">2</td>
              <td class="col-item">Pejabat Berwenang</td>
              <td>${t.pejabat_berwenang}</td>
            </tr>
            <tr>
              <td class="col-no">3</td>
              <td class="col-item">Pengawas Pekerjaan</td>
              <td>${t.pengawas_pekerjaan}</td>
            </tr>
            <tr>
              <td class="col-no">4</td>
              <td class="col-item">Jenis Kontrak</td>
              <td>${t.jenis_kontrak}</td>
            </tr>
            <tr>
              <td class="col-no">5</td>
              <td class="col-item">Tingkat Risiko CSMS (HSSE)</td>
              <td><strong>${t.resiko_csms}</strong> (${t.csms_grade})</td>
            </tr>
            <tr>
              <td class="col-no">6</td>
              <td class="col-item">Komitmen Minimal TKDN</td>
              <td>Minimal <strong>${t.tkdn_minimal} %</strong> (Form A3/A4/A5 Kemenperin)</td>
            </tr>
            <tr>
              <td class="col-no">7</td>
              <td class="col-item">Masa Pemeliharaan / Retensi</td>
              <td id="tablePemeliharaan"><strong>${t.masa_pemeliharaan_hari} hari kalender</strong> sejak Serah Terima Pertama (BAST-1)</td>
            </tr>
            <tr>
              <td class="col-no">8</td>
              <td class="col-item">Jaminan Pelaksanaan</td>
              <td id="tableJaminan">Sebesar <strong>${t.jaminan_pelaksanaan_persen}%</strong> dari total nilai kontrak</td>
            </tr>
          </tbody>
        </table>

        <div class="doc-section-title" style="background:#0F172A; margin-top:28px;">
          BAGIAN B: RANCANGAN KONTRAK DEFINITIF (20 PASAL)
        </div>

        <table class="doc-table">
          <thead>
            <tr>
              <th style="width: 150px;">PASAL</th>
              <th>SUBSTANSI PASAL DALAM NASKAH KONTRAK</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style="font-weight:700;">Pasal 2: Lingkup Kerja</td>
              <td>${t.lingkup_pekerjaan}</td>
            </tr>
            <tr>
              <td style="font-weight:700;">Pasal 3: Nilai Kontrak</td>
              <td id="tablePasalNilai">Total nilai kontrak definitif adalah sebesar ${this.state.formatRupiah(t.total_dengan_kr)} sudah termasuk PPN.</td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
  }

  // 2. Dokumen RKS Template
  getRKSTemplate() {
    const r = this.state.state.rksData;
    return `
      <div class="document-page-sheet">
        <div class="doc-formal-header">
          <div>
            <div class="doc-pertamina-title">${r.nama_perusahaan}</div>
            <div class="doc-unit-title">FUNGSI PEMINTA PENGADAAN (FPP)</div>
          </div>
          <div class="doc-confidential-stamp">RKS TEKNIS</div>
        </div>

        <div class="doc-title-block">
          <div class="doc-main-heading">RENCANA KERJA DAN SYARAT-SYARAT (RKS)</div>
          <div class="doc-sub-heading">${r.jenis_pekerjaan.toUpperCase()}</div>
          <div class="doc-number-badge">Nomor: ${r.nomor_dokumen} | Lokasi: ${r.lokasi}</div>
        </div>

        <div class="doc-section-title">LEMBAR PENGESAHAN DOKUMEN</div>
        <table class="doc-table">
          <tr><th>Fungsi</th><th>Nama Pejabat</th><th>Jabatan</th><th>Status</th></tr>
          <tr><td>Disusun Oleh</td><td>Junior Engineer Project</td><td>FPP Kalimantan</td><td>✅ Selesai</td></tr>
          <tr><td>Diperiksa Oleh</td><td>Sr. Supervisor Maintenance</td><td>RPD Kalimantan</td><td>✅ Selesai</td></tr>
          <tr><td>Disetujui Oleh</td><td>Region Manager RPD</td><td>Regional Kalimantan</td><td>⏳ Menunggu TTD</td></tr>
        </table>

        <div class="doc-section-title">STRUKTUR BAB RKS (5 BAB)</div>
        <table class="doc-table">
          <tr><th style="width:120px;">BAB</th><th>JUDUL DAN URAIAN SUBSTANSI</th></tr>
          <tr><td style="font-weight:700;">BAB I</td><td><strong>UMUM & LATAR BELAKANG:</strong> Dasar pelaksanaan pengadaan, lokasi, dan ringkasan fasilitas eksisting.</td></tr>
          <tr><td style="font-weight:700;">BAB II</td><td><strong>LINGKUP PEKERJAAN:</strong> Detail pengadaan material, instalasi, dan konstruksi fisik sesuai BoQ.</td></tr>
          <tr><td style="font-weight:700;">BAB III</td><td><strong>SPESIFIKASI TEKNIS & MUTU:</strong> Standar API 650/653, ASTM A36, pengujian hydrotest dan NDT.</td></tr>
          <tr><td style="font-weight:700;">BAB IV</td><td><strong>PERSYARATAN K3L & CSMS:</strong> Kategori Risiko CSMS HIGH dengan passing grade 70.</td></tr>
          <tr><td style="font-weight:700;">BAB V</td><td><strong>JADWAL & SERAH TERIMA:</strong> Durasi pelaksanaan, inspeksi bersama BAST-1 dan BAST-2.</td></tr>
        </table>
      </div>
    `;
  }

  // 3. Rancangan Kontrak Definitif Template
  getContractTemplate() {
    const c = this.state.state.contractData;
    return `
      <div class="document-page-sheet">
        <div class="doc-formal-header">
          <div>
            <div class="doc-pertamina-title">PT PERTAMINA PATRA NIAGA</div>
            <div class="doc-unit-title">PERJANJIAN PEMBORONGAN PEKERJAAN</div>
          </div>
          <div class="doc-confidential-stamp">DEFINITIF</div>
        </div>

        <div class="doc-title-block">
          <div class="doc-main-heading">SURAT PERJANJIAN (KONTRAK)</div>
          <div class="doc-sub-heading">${c.nama_pekerjaan.toUpperCase()}</div>
          <div class="doc-number-badge">Nomor Kontrak: ${c.nomor_kontrak}</div>
        </div>

        <div class="doc-section-title">PARA PIHAK PENANDATANGAN</div>
        <table class="doc-table">
          <tr><td style="width:160px; font-weight:700;">Pihak Pertama:</td><td><strong>PT PERTAMINA PATRA NIAGA</strong> (Diwakili oleh ${c.pejabat_ttd_pertamina})</td></tr>
          <tr><td style="font-weight:700;">Pihak Kedua (Vendor):</td><td><strong>${c.nama_vendor}</strong> (NPWP: ${c.npwp_vendor})</td></tr>
        </table>

        <div class="doc-section-title">PASAL KUNCI PERJANJIAN (20 PASAL STANDAR)</div>
        <table class="doc-table">
          <tr><th style="width:130px;">PASAL</th><th>ISI KLAUSUL RESMI</th></tr>
          <tr><td style="font-weight:700;">Pasal 3 (Nilai)</td><td>Nilai pekerjaan adalah <strong>${this.state.formatRupiah(c.nilai_kontrak)}</strong> termasuk PPN. Jenis Kontrak: ${c.jenis_kontrak}.</td></tr>
          <tr><td style="font-weight:700;">Pasal 4 (Jangka Waktu)</td><td>Jangka waktu pelaksanaan adalah <strong>${c.durasi_hari} hari kalender</strong> sejak diterbitkannya SPMK.</td></tr>
          <tr><td style="font-weight:700;">Pasal 5 (Pemeliharaan)</td><td>Masa pemeliharaan ditetapkan selama <strong>${c.masa_pemeliharaan} hari kalender</strong> sejak BAST-1. Retensi 5%.</td></tr>
          <tr><td style="font-weight:700;">Pasal 10 (Sanksi)</td><td>Denda keterlambatan 1‰ (satu per mil) per hari dengan batas maksimal denda 5%.</td></tr>
        </table>
      </div>
    `;
  }

  // 4. Draft Amendemen / Addendum Template
  getAmendmentTemplate() {
    const a = this.state.state.amendmentData;
    return `
      <div class="document-page-sheet">
        <div class="doc-formal-header">
          <div>
            <div class="doc-pertamina-title">PT PERTAMINA PATRA NIAGA</div>
            <div class="doc-unit-title">ADDENDUM PERJANJIAN PEMBORONGAN</div>
          </div>
          <div class="doc-confidential-stamp">AMENDEMEN</div>
        </div>

        <div class="doc-title-block">
          <div class="doc-main-heading">SURAT AMENDEMEN / ADDENDUM KONTRAK</div>
          <div class="doc-sub-heading">${a.judul_pekerjaan.toUpperCase()}</div>
          <div class="doc-number-badge">Nomor: ${a.nomor_addendum} | Atas Kontrak: ${a.nomor_kontrak_asal}</div>
        </div>

        <div class="doc-section-title">KONSIDERAN HUKUM</div>
        <p style="font-size:12px; line-height:1.6; margin-bottom:14px; text-align:justify;">
          <strong>Menimbang:</strong> Bahwa terdapat penyesuaian volume dan kondisi lapangan pada pelaksanaan pekerjaan.<br>
          <strong>Mengingat:</strong> Ketentuan Pasal 18 (Perubahan Pekerjaan) pada Kontrak Asal No. ${a.nomor_kontrak_asal}.<br>
          <strong>Memperhatikan:</strong> Berita Acara Rapat Evaluasi Teknis Bersama Tanggal ${a.tanggal_amendemen}.
        </p>

        <div class="doc-section-title">TABEL KOMPARASI PERUBAHAN PASAL (LAMA VS BARU)</div>
        <table class="doc-table">
          <thead>
            <tr><th style="width:140px;">PASAL</th><th>KONDISI LAMA (SEBELUM)</th><th>KONDISI BARU (ADDENDUM)</th></tr>
          </thead>
          <tbody>
            <tr>
              <td style="font-weight:700;">Pasal 3: Nilai Kontrak</td>
              <td>${this.state.formatRupiah(a.nilai_kontrak_asal)}</td>
              <td style="background:#ECFDF5; color:#065F46; font-weight:700;">${this.state.formatRupiah(a.nilai_kontrak_baru)} (+8%)</td>
            </tr>
            <tr>
              <td style="font-weight:700;">Dasar Justifikasi</td>
              <td colspan="2">${a.alasan}</td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
  }

  // 5. Knowledge Base View Template
  getKBTemplate() {
    const kb = this.state.state.kbState;
    return `
      <div class="kb-card">
        <div class="matrix-card-title">
          <span>🗄️ Manajemen Knowledge Base Qdrant Cloud</span>
          <span class="badge-source">all-minilm-l6-v2 (384 Dim)</span>
        </div>
        <p style="font-size:12px; color:#64748B; margin-bottom:16px;">
          Dokumen acuan yang terindeks digunakan oleh LLM untuk melakukan pencarian semantik (RAG) saat merumuskan klausul RKS, Kontrak, dan Amendemen.
        </p>

        <div class="kb-collection-grid">
          <div class="kb-col-item active">
            <div class="kb-col-title">📋 rks_kb</div>
            <div class="kb-col-count">3 Berkas PDF Terindeks (108 Chunks)</div>
          </div>
          <div class="kb-col-item">
            <div class="kb-col-title">📝 contract_kb</div>
            <div class="kb-col-count">2 Berkas PDF Terindeks (84 Chunks)</div>
          </div>
          <div class="kb-col-item">
            <div class="kb-col-title">📎 amendment_kb</div>
            <div class="kb-col-count">1 Berkas PDF Terindeks (32 Chunks)</div>
          </div>
        </div>

        <table class="doc-table">
          <thead>
            <tr><th>Nama Berkas PDF</th><th>Jumlah Chunks</th><th>Status Qdrant</th><th>Aksi</th></tr>
          </thead>
          <tbody>
            ${Object.entries(kb.documents).map(([name, chunks]) => `
              <tr>
                <td>📄 ${name}</td>
                <td><code>${chunks} chunks</code></td>
                <td><span style="color:#059669; font-weight:700;">✓ Synced</span></td>
                <td><button style="border:none; background:#FEE2E2; color:#DC2626; padding:3px 8px; border-radius:4px; cursor:pointer;" onclick="alert('Hapus ${name}?')">Hapus</button></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  async triggerDownloadDocx() {
    const mode = this.state.state.currentMode;
    const isAlive = await this.api.checkBackendHealth();

    try {
      if (isAlive) {
        if (mode === 'tender') await this.api.generateTender(this.state.state.tenderData);
        else if (mode === 'rks') await this.api.generateRKS(this.state.state.rksData);
        else if (mode === 'contract') await this.api.generateKontrak(this.state.state.contractData);
        else if (mode === 'amendment') await this.api.generateAmendemen(this.state.state.amendmentData);
        return;
      }
    } catch (e) {
      console.warn("Backend error, fallback to simulated download:", e);
    }

    const modeTitle = this.state.modeMeta[mode].title;
    alert(`📥 Mengunduh Berkas Microsoft Word (.DOCX):\n\nDokumen: ${modeTitle}\nStatus: Siap Cetak format resmi Pertamina.`);
  }
}

window.CanvasController = CanvasController;
