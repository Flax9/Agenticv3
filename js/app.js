/**
 * ================================================================
 * APPLICATION BOOTSTRAPPER (MAIN ENTRY POINT) - agenticv3
 * ================================================================
 */

document.addEventListener('DOMContentLoaded', async () => {
  console.log("🚀 Initializing Pertamina Procurement AI Copilot (agenticv3)...");

  // 1. Initialize Controllers
  const chatCtrl = new window.ChatController(window.appState, window.apiService);
  const canvasCtrl = new window.CanvasController(window.appState, window.apiService);

  chatCtrl.init();
  canvasCtrl.init();

  // Expose global helper bridges for inline HTML click events
  window.sendQuickPrompt = (text) => chatCtrl.sendQuickPrompt(text);
  window.applyToCanvas = () => chatCtrl.applyCardToCanvas();
  window.editParameterQuick = () => chatCtrl.editCardQuick();
  window.loadSandboxDemo = () => chatCtrl.loadSandboxDemo();
  
  window.switchCanvasTab = (tabId, btn) => canvasCtrl.switchTab(tabId, btn);
  window.downloadWord = () => canvasCtrl.triggerDownloadDocx();

  window.toggleReasoning = (el) => {
    const details = el.nextElementSibling;
    if (details.style.display === "none" || !details.style.display) {
      details.style.display = "block";
    } else {
      details.style.display = "none";
    }
  };

  // Popup Management: 4-Box Modal inside Chat Window
  const popupOverlay = document.getElementById('chatPopupOverlay');

  window.openDocPopup = () => {
    if (popupOverlay) {
      popupOverlay.style.display = 'flex';
    }
  };

  window.closeDocPopup = () => {
    if (popupOverlay) {
      popupOverlay.style.display = 'none';
    }
  };

  window.selectDocumentChoice = (mode) => {
    // 1. Highlight selected card in popup
    document.querySelectorAll('.doc-choice-card').forEach(c => c.classList.remove('selected'));
    const targetCard = document.getElementById(`choice-${mode}`);
    if (targetCard) targetCard.classList.add('selected');

    // 2. Set mode in reactive state
    window.appState.setMode(mode);

    // 3. Update navbar active document pill
    const docTitleEl = document.getElementById('activeDocTitle');
    if (docTitleEl) {
      docTitleEl.innerText = window.appState.modeMeta[mode].title;
    }

    // 4. Close the popup
    window.closeDocPopup();
  };

  window.openKnowledgeBase = () => {
    window.appState.setMode('kb');
    const docTitleEl = document.getElementById('activeDocTitle');
    if (docTitleEl) {
      docTitleEl.innerText = "🗄️ Knowledge Base Management";
    }
  };

  // Trigger File Upload
  window.triggerFileUpload = () => {
    const fileInput = document.getElementById('hiddenFileInput');
    if (fileInput) fileInput.click();
  };

  window.handleFileSelected = async (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      const sizeKb = Math.round(file.size / 1024);

      // Add user message
      chatCtrl.appendMessage({
        sender: 'user',
        text: `Saya melampirkan berkas acuan pengadaan: <strong>${file.name}</strong>.`,
        attachment: { name: file.name, size: `${sizeKb} KB` }
      });

      // Try Backend Extraction API if Tender mode
      const isAlive = await window.apiService.checkBackendHealth();
      if (isAlive && window.appState.state.currentMode === 'tender') {
        chatCtrl.appendMessage({
          sender: 'ai',
          text: `⏳ Berkas <strong>${file.name}</strong> sedang dipindai menggunakan model Docling dan ekstraksi LLM di backend...`
        });

        try {
          const res = await window.apiService.extractTenderMetadata(file, null, "04 Desember 2025", "Tinggi");
          if (res && res.data) {
            Object.assign(window.appState.state.tenderData, res.data);
            chatCtrl.loadSandboxDemo();
          }
        } catch (err) {
          console.warn("Backend extraction error, falling back to local demo:", err);
          chatCtrl.loadSandboxDemo();
        }
      } else {
        setTimeout(() => {
          chatCtrl.loadSandboxDemo();
        }, 700);
      }
    }
  };

  window.resetChatSession = () => {
    const mode = window.appState.state.currentMode;
    const modeTitle = window.appState.modeMeta[mode].title;
    if (confirm(`Mulai sesi baru untuk ${modeTitle}? Draf saat ini akan dibersihkan.`)) {
      window.appState.setMode(mode);
      window.openDocPopup(); // Re-open the popup on reset!
    }
  };

  window.openRegulasiGuide = () => {
    alert("📖 Dasar Regulasi Pengadaan Aktif:\n\n1. Pedoman PBJ No. A03-001/PNG200000/2024-S9 Rev. 1\n2. TKO No. B3.2.4-03/PNG200000/2024-S9 (Lampiran 3, 4, 5, 6)\n3. TKI No. C3.2.3-01/PNG200000/2024-S9 (Lampiran 3, 5)\n4. TKI Penentuan Besaran Denda No. C5-001/I30000/2021-S9");
  };

  // 2. Check Backend Health
  const isBackendAlive = await window.apiService.checkBackendHealth();
  const statusDot = document.querySelector('.status-dot');
  if (statusDot) {
    if (isBackendAlive) {
      statusDot.style.backgroundColor = "var(--status-success)";
      statusDot.setAttribute('title', 'Terhubung ke FastAPI Backend (Port 8000)');
    } else {
      statusDot.style.backgroundColor = "#F59E0B";
      statusDot.setAttribute('title', 'Mode Mandiri / Sandbox (Backend offline)');
    }
  }

  // Ensure popup is open when first entering!
  window.openDocPopup();

  console.log("✅ Pertamina Procurement AI Copilot Front-End Ready.");
});
