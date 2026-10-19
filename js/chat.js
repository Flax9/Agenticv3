/**
 * ================================================================
 * CHAT CONTROLLER & CONVERSATION MANAGER - agenticv3
 * ================================================================
 */

class ChatController {
  constructor(state, api) {
    this.state = state;
    this.api = api;
    this.chatStream = document.getElementById('chatStream');
    this.userInput = document.getElementById('userInput');
    this.stepperContainer = document.getElementById('workflowStepper');
    this.chipsContainer = document.getElementById('quickChipsWrapper');
  }

  init() {
    this.bindEvents();
    this.state.subscribe((currentState, changedKey, payload) => {
      if (changedKey === 'modeChange') {
        this.renderModeWelcome();
        this.renderStepper();
        this.renderQuickChips();
      } else if (changedKey === 'stepChange') {
        this.renderStepper();
      }
    });

    // Render initial mode
    this.renderStepper();
    this.renderModeWelcome();
    this.renderQuickChips();
  }

  bindEvents() {
    if (this.userInput) {
      this.userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          this.handleSendMessage();
        }
      });
    }
  }

  renderStepper() {
    if (!this.stepperContainer) return;
    const mode = this.state.state.currentMode;
    const meta = this.state.modeMeta[mode];
    const steps = meta ? meta.stepper : ["Tahap 1", "Tahap 2", "Tahap 3", "Tahap 4"];
    const currentStep = this.state.state.currentStep;

    let html = '';
    steps.forEach((stepText, idx) => {
      const stepNum = idx + 1;
      let statusClass = '';
      let numContent = `${stepNum}`;

      if (stepNum < currentStep) {
        statusClass = 'completed';
        numContent = '✓';
      } else if (stepNum === currentStep) {
        statusClass = 'active';
      }

      html += `
        <div class="step-item ${statusClass}">
          <div class="step-number">${numContent}</div>
          <span>${stepText}</span>
        </div>
      `;

      if (idx < steps.length - 1) {
        const connClass = stepNum < currentStep ? 'completed' : '';
        html += `<div class="step-connector ${connClass}"></div>`;
      }
    });

    this.stepperContainer.innerHTML = html;
  }

  renderQuickChips() {
    if (!this.chipsContainer) return;
    const mode = this.state.state.currentMode;
    let chips = [];

    if (mode === 'tender') {
      chips = [
        { text: "⏱️ Ubah Pemeliharaan 180 Hari", prompt: "Atur Masa Pemeliharaan menjadi 180 hari kalender" },
        { text: "🏦 Jaminan Pelaksanaan 5%", prompt: "Wajibkan Jaminan Pelaksanaan 5% dari Nilai Kontrak" },
        { text: "📊 Cek Skor Kepatuhan STK", prompt: "Tampilkan skor kepatuhan checklist mandatory" },
        { text: "💰 Lihat Rincian HPS", prompt: "Lihat rincian kalkulasi HPS dan K&R" }
      ];
    } else if (mode === 'rks') {
      chips = [
        { text: "➕ Tambah Spesifikasi Material Baja", prompt: "Tambahkan rincian teknis plat baja ASTM A36 pada Bab II" },
        { text: "🛡️ Standar CSMS Kategori Tinggi", prompt: "Pastikan persyaratan CSMS minimal kategori High Risk" },
        { text: "📋 Lihat Struktur 5 Bab", prompt: "Tampilkan draft struktur bab RKS lengkap" }
      ];
    } else if (mode === 'contract') {
      chips = [
        { text: "🏢 Ganti Vendor: PT Rekayasa Energi", prompt: "Ganti pihak kedua / vendor menjadi PT Rekayasa Energi Utama" },
        { text: "💰 Nilai Kontrak Rp 9.5 Miliar", prompt: "Ubah total nilai kontrak menjadi Rp 9.500.000.000" },
        { text: "⚖️ Denda 1 per mil per hari", prompt: "Terapkan ketentuan denda keterlambatan 1 permil per hari (maks 5%)" }
      ];
    } else if (mode === 'amendment') {
      chips = [
        { text: "📈 Tambah Nilai Kontrak 12%", prompt: "Buatkan addendum penambahan nilai kontrak sebesar 12% karena volume bertambah" },
        { text: "⏱️ Perpanjang Waktu 45 Hari", prompt: "Tambahkan klausul perpanjangan waktu pelaksanaan selama 45 hari kalender" },
        { text: "📜 Lihat Tabel Komparasi", prompt: "Tampilkan tabel perbandingan kondisi lama vs kondisi baru" }
      ];
    } else {
      chips = [
        { text: "📂 Lihat Dokumen rks_kb", prompt: "Tampilkan daftar berkas terindeks di collection rks_kb" },
        { text: "📝 Lihat contract_kb", prompt: "Tampilkan daftar berkas di collection contract_kb" }
      ];
    }

    this.chipsContainer.innerHTML = chips.map(c => `
      <button class="chip-btn" onclick="sendQuickPrompt('${c.prompt}')">
        ${c.text}
      </button>
    `).join('');
  }

  renderModeWelcome() {
    this.chatStream.innerHTML = '';
    const mode = this.state.state.currentMode;
    const meta = this.state.modeMeta[mode];

    // Initial AI message with Fresh Dropzone Card
    const welcomeHtml = `
      Halo! Saya siap membantu Anda menyusun <strong>${meta.title}</strong> (${meta.badge}) sesuai Pedoman Pengadaan PT Pertamina Patra Niaga No. <code>A03-001/PNG200000/2024-S9</code>.
      
      <div class="welcome-dropzone-box">
        <div class="dropzone-icon">📁</div>
        <div class="dropzone-title">Mulai Sesi Penyusunan Dokumen</div>
        <div class="dropzone-desc">Unggah berkas acuan (BoQ / TOR / PDF) untuk ekstraksi parameter otomatis, atau gunakan data contoh untuk demonstrasi.</div>
        <div class="dropzone-actions">
          <button class="btn-upload-file" onclick="triggerFileUpload()">
            <svg class="icon" viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/></svg>
            Unggah Berkas PDF/Excel
          </button>
          <button class="btn-sandbox-demo" onclick="loadSandboxDemo()">
            ✨ Muat Data Contoh (Demo)
          </button>
        </div>
      </div>
    `;

    this.appendMessage({
      sender: 'ai',
      text: welcomeHtml
    });
  }

  loadSandboxDemo() {
    const mode = this.state.state.currentMode;
    this.state.state.isSessionStarted = true;
    this.state.setStep(3); // Move to review step

    if (mode === 'tender') {
      const tender = this.state.state.tenderData;
      // Add simulated user message
      this.appendMessage({
        sender: 'user',
        text: `Tolong buatkan Dokumen Tender lengkap untuk ${tender.nama_pengadaan}. Berikut berkas BoQ acuan.`,
        attachment: { name: "BOQ_Overhaul_Tangki_41T313.pdf", size: "352 KB" }
      });

      // Add AI parsed card message
      setTimeout(() => {
        const cardHtml = `
          Saya telah memindai berkas <code>BOQ_Overhaul_Tangki_41T313.pdf</code> menggunakan model Docling dan RAG vector store.
          
          <div class="ai-thought-box">
            <div class="thought-toggle" onclick="toggleReasoning(this)">
              <span>⚡ AI Reasoning & RAG Retrieval</span> ▾
            </div>
            <div class="thought-details">
              • Ditemukan 14 rincian item pekerjaan overhaul tangki bahan bakar minyak.<br>
              • Mengaplikasikan formula Keuntungan & Risiko (K&R) sebesar 8% standar Regional Kalimantan.<br>
              • Merujuk kualifikasi CSMS Tinggi (Passing grade 70) sesuai TKO B3.2.4-03.
            </div>
          </div>

          <div class="interactive-card">
            <div class="card-header-badge">
              <span class="badge-card-title">📋 Ringkasan Parameter Pengadaan Terdeteksi</span>
              <span class="badge-source">Auto-Extracted</span>
            </div>

            <div class="parameter-grid">
              <div class="param-item">
                <span class="param-label">Nama Pengadaan:</span>
                <span class="param-value" id="cardNamaPengadaan">${tender.nama_pengadaan}</span>
              </div>
              <div class="param-item">
                <span class="param-label">Tingkat Risiko CSMS:</span>
                <span class="param-value" style="color:#059669;">🛡️ TINGGI (Grade ≥ 70)</span>
              </div>
              <div class="param-item">
                <span class="param-label">Prime Cost (HPS Riil):</span>
                <span class="param-value" id="cardPrimeCost">${this.state.formatRupiah(tender.prime_cost)}</span>
              </div>
              <div class="param-item">
                <span class="param-label">Total HPS (+ K&R 8%):</span>
                <span class="param-value highlight" id="cardTotalHPS">${this.state.formatRupiah(tender.total_dengan_kr)}</span>
              </div>
              <div class="param-item">
                <span class="param-label">Target Minimal TKDN:</span>
                <span class="param-value" id="cardTKDN">${tender.tkdn_minimal} %</span>
              </div>
              <div class="param-item">
                <span class="param-label">Jenis Kontrak:</span>
                <span class="param-value" id="cardJenisKontrak">${tender.jenis_kontrak}</span>
              </div>
            </div>

            <div class="card-actions-row">
              <button class="btn-card-primary" onclick="applyToCanvas()">
                ✓ Terapkan ke Dokumen Canvas
              </button>
              <button class="btn-card-secondary" onclick="editParameterQuick()">
                ✏️ Edit Nilai
              </button>
            </div>
          </div>

          Silakan tinjau draf pada kanvas sebelah kanan, atau berikan instruksi penyesuaian klausul.
        `;

        this.appendMessage({ sender: 'ai', text: cardHtml });
      }, 500);
    }
    else if (mode === 'rks') {
      const rks = this.state.state.rksData;
      this.appendMessage({
        sender: 'user',
        text: `Tolong susunkan draf RKS untuk ${rks.jenis_pekerjaan} di ${rks.lokasi}.`,
        attachment: { name: "Spesifikasi_Teknis_Tangki.pdf", size: "187 KB" }
      });
      setTimeout(() => {
        this.appendMessage({
          sender: 'ai',
          text: `Draf RKS telah disusun berdasarkan referensi KB Qdrant. Terdiri dari <strong>${rks.bab_count} Bab Teknis</strong> lengkap dengan Lembar Pengesahan dan Matriks CSMS. Silakan periksa pada kanvas kanan.`
        });
      }, 500);
    }
    else if (mode === 'contract') {
      const c = this.state.state.contractData;
      this.appendMessage({
        sender: 'user',
        text: `Tolong susunkan Rancangan Kontrak Definitif untuk ${c.nama_pekerjaan}. Pemenang tender: ${c.nama_vendor}.`
      });
      setTimeout(() => {
        this.appendMessage({
          sender: 'ai',
          text: `Naskah Kontrak Definitif 20 Pasal telah disusun dengan nilai <strong>${this.state.formatRupiah(c.nilai_kontrak)}</strong> dan durasi <strong>${c.durasi_hari} hari kalender</strong>.`
        });
      }, 500);
    }
    else if (mode === 'amendment') {
      const a = this.state.state.amendmentData;
      this.appendMessage({
        sender: 'user',
        text: `Tolong susunkan draf Addendum untuk kontrak ${a.nomor_kontrak_asal} karena ada penambahan nilai dan volume pekerjaan.`
      });
      setTimeout(() => {
        this.appendMessage({
          sender: 'ai',
          text: `Draft Addendum telah dibuat lengkap dengan konsideran Menimbang, Mengingat, Memperhatikan, serta tabel komparasi kondisi lama vs baru.`
        });
      }, 500);
    }
  }

  handleSendMessage() {
    const text = this.userInput.value.trim();
    if (!text) return;

    this.appendMessage({
      sender: 'user',
      author: 'Fungsi Peminta Pengadaan (User)',
      text: text
    });

    this.userInput.value = '';

    setTimeout(() => {
      this.processAiResponse(text);
    }, 600);
  }

  sendQuickPrompt(promptText) {
    this.userInput.value = promptText;
    this.handleSendMessage();
  }

  appendMessage({ sender, author, text, attachment }) {
    const row = document.createElement('div');
    row.className = `message-row ${sender}`;

    const avatar = document.createElement('div');
    avatar.className = `message-avatar ${sender === 'user' ? 'avatar-user' : 'avatar-ai'}`;
    avatar.innerText = sender === 'user' ? 'Anda' : 'AI';

    const content = document.createElement('div');
    content.className = 'message-content';

    const authorSpan = document.createElement('span');
    authorSpan.className = 'message-author';
    authorSpan.innerText = author || (sender === 'user' ? 'FPP (User)' : 'Pertamina AI Copilot');

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = text;

    if (attachment) {
      const pill = document.createElement('div');
      pill.className = 'file-attachment-pill';
      pill.innerHTML = `📎 <strong>${attachment.name}</strong> (${attachment.size})`;
      bubble.appendChild(pill);
    }

    content.appendChild(authorSpan);
    content.appendChild(bubble);
    row.appendChild(avatar);
    row.appendChild(content);

    this.chatStream.appendChild(row);
    this.chatStream.scrollTop = this.chatStream.scrollHeight;
  }

  processAiResponse(userText) {
    const lower = userText.toLowerCase();

    if (lower.includes('pemeliharaan') || lower.includes('180') || lower.includes('hari')) {
      this.state.updatePackageField('masa_pemeliharaan_hari', 180);
      this.appendMessage({
        sender: 'ai',
        text: 'Baik, saya telah memperbarui <strong>Masa Pemeliharaan</strong> menjadi <strong>180 (seratus delapan puluh) hari kalender</strong> pada <em>Tabel Ketentuan Khusus Butir 7</em> di dokumen canvas sebelah kanan.<br><br>Klausul ini sudah diselaraskan dengan standar garansi pekerjaan pemborongan Pertamina.'
      });
    }
    else if (lower.includes('jaminan') || lower.includes('5%')) {
      this.state.updatePackageField('jaminan_pelaksanaan_persen', 5);
      this.appendMessage({
        sender: 'ai',
        text: 'Ketentuan <strong>Jaminan Pelaksanaan sebesar 5% dari Nilai Kontrak</strong> telah diterapkan pada Butir 8 IKPP dan Pasal 6 Rancangan Kontrak Definitif.<br><br>Jaminan wajib diterbitkan oleh Bank BUMN atau Bank Swasta Devisa Nasional.'
      });
    }
    else if (lower.includes('skor') || lower.includes('kepatuhan') || lower.includes('stk')) {
      this.state.setCanvasTab('checklistTab');
      this.appendMessage({
        sender: 'ai',
        text: 'Saya telah membuka tab <strong>Checklist STK Mandatory Pra-Tender</strong> pada kanvas sebelah kanan.<br><br>Saat ini paket dokumen memenuhi <strong>32 poin (37.2%)</strong> mandatory otomatis, dengan 10 butir memerlukan konfirmasi spesifik.'
      });
    }
    else if (lower.includes('hps') || lower.includes('biaya') || lower.includes('matriks')) {
      this.state.setCanvasTab('matrixTab');
      this.appendMessage({
        sender: 'ai',
        text: 'Saya telah mengalihkan kanvas ke tab <strong>Matriks HPS & TKDN</strong> untuk memeriksa rincian Prime Cost vs Keuntungan & Risiko (8%).'
      });
    }
    else {
      this.appendMessage({
        sender: 'ai',
        text: `Saya telah mencatat instruksi Anda: "<em>${userText}</em>". Seluruh perubahan klausul sedang diselaraskan secara *real-time* ke naskah dokumen pada kanvas kanan.`
      });
    }
  }

  applyCardToCanvas() {
    this.appendMessage({
      sender: 'ai',
      text: '✅ <strong>Parameter Telah Disinkronkan Penuh!</strong><br>Seluruh data HPS, CSMS, TKDN, dan Pejabat telah diterapkan ke naskah dokumen pada kanvas kanan. Dokumen siap diunduh dalam format Word (.docx).'
    });
  }

  editCardQuick() {
    const current = this.state.state.tenderData.total_dengan_kr;
    const newVal = prompt("Masukkan Nilai Total HPS Baru (+K&R):", current);
    if (newVal) {
      const num = Number(newVal);
      if (!isNaN(num) && num > 0) {
        this.state.updatePackageField('total_dengan_kr', num);
        
        const cardVal = document.getElementById('cardTotalHPS');
        if (cardVal) cardVal.innerText = this.state.formatRupiah(num);

        this.appendMessage({
          sender: 'ai',
          text: `Total HPS telah berhasil dikoreksi menjadi <strong>${this.state.formatRupiah(num)}</strong> dan langsung tercermin pada kanvas dokumen.`
        });
      }
    }
  }
}

window.ChatController = ChatController;
