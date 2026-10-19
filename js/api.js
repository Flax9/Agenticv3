/**
 * ================================================================
 * API CLIENT SERVICE - agenticv3
 * ================================================================
 * Bridges front-end actions to the Pertamina AI FastAPI backend
 * (runs locally on http://127.0.0.1:8000 via api.py).
 */

class ApiService {
  constructor(baseUrl) {
    this.baseUrl = baseUrl || (window.appState ? window.appState.state.apiBaseUrl : "http://127.0.0.1:8000");
  }

  /**
   * Health Check backend connection
   */
  async checkBackendHealth() {
    try {
      const controller = new AbortController();
      const id = setTimeout(() => controller.abort(), 2000);
      const res = await fetch(`${this.baseUrl}/docs`, { method: 'GET', signal: controller.signal, mode: 'no-cors' });
      clearTimeout(id);
      return true;
    } catch (e) {
      console.warn("[ApiService] Backend unreachable at:", this.baseUrl);
      return false;
    }
  }

  /**
   * Scan & Auto-Extract Metadata from RKS & BOQ files
   * Endpoint: POST /api/extract-tender-metadata
   */
  async extractTenderMetadata(rksFile, boqFile, tanggal, resikoCsms) {
    const formData = new FormData();
    if (rksFile) formData.append('file_rks', rksFile);
    if (boqFile) formData.append('file_boq', boqFile);
    formData.append('tanggal', tanggal || '');
    formData.append('resiko_csms', resikoCsms || 'Tinggi');

    const res = await fetch(`${this.baseUrl}/api/extract-tender-metadata`, {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      throw new Error(`Ekstraksi gagal: HTTP ${res.status}`);
    }
    return await res.json();
  }

  /**
   * Generate Dokumen Tender Versi 2.0 (.docx)
   * Endpoint: POST /api/generate-tender
   */
  async generateTender(payload, file) {
    const formData = new FormData();
    for (const [k, v] of Object.entries(payload)) {
      formData.append(k, v);
    }
    if (file) formData.append('file', file);

    const res = await fetch(`${this.baseUrl}/api/generate-tender`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error(await res.text());

    const blob = await res.blob();
    this._downloadBlob(blob, `Dokumen_Tender_${(payload.nama_pengadaan || 'Paket').substring(0, 30)}.docx`);
  }

  /**
   * Generate Dokumen RKS (.docx)
   * Endpoint: POST /api/generate-rks
   */
  async generateRKS(payload, file) {
    const formData = new FormData();
    for (const [k, v] of Object.entries(payload)) {
      formData.append(k, v);
    }
    if (file) formData.append('file', file);

    const res = await fetch(`${this.baseUrl}/api/generate-rks`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error(await res.text());

    const blob = await res.blob();
    this._downloadBlob(blob, `RKS_${(payload.jenis_pekerjaan || 'Proyek').substring(0, 30)}.docx`);
  }

  /**
   * Generate Kontrak Definitif (.docx)
   * Endpoint: POST /api/generate-kontrak
   */
  async generateKontrak(payload, file) {
    const formData = new FormData();
    for (const [k, v] of Object.entries(payload)) {
      formData.append(k, v);
    }
    if (file) formData.append('file', file);

    const res = await fetch(`${this.baseUrl}/api/generate-kontrak`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error(await res.text());

    const blob = await res.blob();
    this._downloadBlob(blob, `Rancangan_Kontrak_${(payload.nama_pekerjaan || 'Definitif').substring(0, 30)}.docx`);
  }

  /**
   * Generate Amendemen (.docx)
   * Endpoint: POST /api/generate-amendemen
   */
  async generateAmendemen(payload, file) {
    const formData = new FormData();
    for (const [k, v] of Object.entries(payload)) {
      formData.append(k, v);
    }
    if (file) formData.append('file', file);

    const res = await fetch(`${this.baseUrl}/api/generate-amendemen`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error(await res.text());

    const blob = await res.blob();
    this._downloadBlob(blob, `Draft_Amendemen_${(payload.judul_pekerjaan || 'Addendum').substring(0, 30)}.docx`);
  }

  /**
   * Internal helper to trigger browser download
   */
  _downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
  }
}

window.apiService = new ApiService();
