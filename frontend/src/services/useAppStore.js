import { create } from 'zustand'
import { DEMO_PACKAGES } from '../demo/demoData'
import { demoOpening, simulatedReply } from '../demo/demoConversation'
import { ApiError, extractTenderMetadata, generateDocument } from './api'
import { formatFileSize, todayIndonesian } from './format'
import { MODE_META } from './modes'
import { classifyUpload } from './upload'

let nextId = 1
const newId = () => nextId++
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const isWideScreen = () => typeof window !== 'undefined' && window.matchMedia('(min-width: 1280px)').matches

let highlightTimer

export const useAppStore = create((set, get) => ({
  // ── Tampilan ──────────────────────────────────────────────
  mode: 'tender',
  step: 1,
  activeTab: 'previewTab',
  isDocPickerOpen: true,
  isDrawerOpen: false,
  isCanvasVisible: isWideScreen(),
  isCanvasFullscreen: false,

  // ── Data ─────────────────────────────────────────────────
  // Paket per mode; null = belum ada data (canvas menampilkan empty state)
  packages: { tender: null, rks: null, contract: null, amendment: null },
  // Hasil ekstraksi yang belum dikonfirmasi user; baru masuk ke packages.tender setelah "Terapkan"
  pendingExtraction: null,
  messages: [],
  sessionResources: [],
  highlight: null, // { key } field yang baru berubah lewat chat
  isBusy: false,
  isDownloading: false,
  backendStatus: 'checking', // 'checking' | 'online' | 'offline'

  // ── Overlay ──────────────────────────────────────────────
  toasts: [],
  confirm: null, // { title, message, confirmLabel, onConfirm }

  // ── Aksi tampilan ────────────────────────────────────────
  setMode: (mode) => {
    if (!MODE_META[mode]) return
    set({
      mode,
      step: 1,
      activeTab: 'previewTab',
      messages: [],
      sessionResources: [],
      highlight: null,
      pendingExtraction: null,
    })
  },
  openDocPicker: () => set({ isDocPickerOpen: true }),
  closeDocPicker: () => set({ isDocPickerOpen: false }),
  selectDocument: (mode) => {
    get().setMode(mode)
    set({ isDocPickerOpen: false })
  },
  setActiveTab: (activeTab) => set({ activeTab }),
  showArtifactTab: (tab) => set({ activeTab: tab, isCanvasVisible: true, isDrawerOpen: false }),
  toggleDrawer: (force) => set((s) => ({ isDrawerOpen: typeof force === 'boolean' ? force : !s.isDrawerOpen })),
  toggleCanvasVisible: (force) =>
    set((s) => {
      const isCanvasVisible = typeof force === 'boolean' ? force : !s.isCanvasVisible
      return { isCanvasVisible, isCanvasFullscreen: isCanvasVisible && s.isCanvasFullscreen }
    }),
  toggleCanvasFullscreen: () => set((s) => ({ isCanvasFullscreen: !s.isCanvasFullscreen })),
  setBackendStatus: (backendStatus) => set({ backendStatus }),

  // ── Overlay ──────────────────────────────────────────────
  pushToast: (message, tone = 'info') => {
    const id = newId()
    set((s) => ({ toasts: [...s.toasts, { id, message, tone }] }))
    setTimeout(() => get().dismissToast(id), 5000)
  },
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
  askConfirm: (confirm) => set({ confirm }),
  closeConfirm: () => set({ confirm: null }),

  // ── Chat ─────────────────────────────────────────────────
  appendMessage: (message) => {
    const id = newId()
    set((s) => ({ messages: [...s.messages, { id, ...message }] }))
    return id
  },
  updateMessage: (id, patch) =>
    set((s) => ({ messages: s.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)) })),

  updateField: (key, value) => {
    const { mode, packages } = get()
    if (!packages[mode]) return
    set({ packages: { ...packages, [mode]: { ...packages[mode], [key]: value } }, highlight: { key } })
    clearTimeout(highlightTimer)
    highlightTimer = setTimeout(() => set({ highlight: null }), 3000)
  },

  sendMessage: async (text) => {
    const trimmed = text.trim()
    if (!trimmed || get().isBusy) return
    const { appendMessage } = get()
    appendMessage({ sender: 'user', text: trimmed })
    set({ isBusy: true })
    await delay(600)

    const { mode, packages } = get()
    const reply = simulatedReply(trimmed, mode)
    const data = packages[mode]
    if (reply.update && !data) {
      appendMessage({
        sender: 'ai',
        text: 'Belum ada draf dokumen untuk diubah. Unggah berkas acuan atau muat data contoh terlebih dahulu.',
      })
    } else {
      if (reply.update) {
        const { key, value } = reply.update
        get().updateField(key, typeof value === 'function' ? value(data) : value)
      }
      if (reply.tab) get().showArtifactTab(reply.tab)
      appendMessage({ sender: 'ai', text: reply.text, simulated: true })
    }
    set({ isBusy: false })
  },

  updatePendingField: (key, value) =>
    set((s) => (s.pendingExtraction ? { pendingExtraction: { ...s.pendingExtraction, [key]: value } } : {})),

  loadDemo: async () => {
    const { mode, packages, appendMessage } = get()
    const demo = DEMO_PACKAGES[mode]
    if (!demo || get().isBusy) return
    // Mode tender melewati kartu verifikasi seperti hasil ekstraksi nyata
    const viaVerification = mode === 'tender'
    set({
      packages: viaVerification ? packages : { ...packages, [mode]: structuredClone(demo) },
      pendingExtraction: viaVerification ? structuredClone(demo) : null,
      step: viaVerification ? 2 : 3,
      sessionResources: [
        { icon: '✨', name: 'Data Contoh (Demo)', meta: 'Data fiktif untuk demonstrasi alur' },
        { icon: '🗄️', name: 'Qdrant: rks_kb & contract_kb', meta: 'Vector DB Pedoman PBJ A03-001/2024' },
      ],
    })
    const script = demoOpening(mode, demo)
    appendMessage({ sender: 'user', ...script.user })
    set({ isBusy: true })
    await delay(500)
    appendMessage({ sender: 'ai', ...script.ai })
    set({ isBusy: false })
  },

  uploadReference: async (file) => {
    const { mode, appendMessage, updateMessage, pushToast } = get()
    if (get().isBusy) return
    appendMessage({
      sender: 'user',
      text: 'Saya melampirkan berkas acuan pengadaan.',
      attachment: { name: file.name, size: formatFileSize(file.size) },
    })

    if (mode !== 'tender') {
      appendMessage({
        sender: 'ai',
        text: `Ekstraksi otomatis saat ini baru tersedia untuk **${MODE_META.tender.title}**. Untuk mode ini, gunakan data contoh atau isi parameter lewat chat.`,
      })
      return
    }

    const kind = classifyUpload(file)
    set({ isBusy: true, step: 2 })
    const progressId = appendMessage({
      sender: 'ai',
      pending: true,
      text: `Berkas \`${file.name}\` sedang dipindai sebagai **${kind === 'boq' ? 'BoQ' : 'RKS'}** dan diekstraksi oleh LLM di backend...`,
    })

    try {
      const res = await extractTenderMetadata({
        rksFile: kind === 'rks' ? file : null,
        boqFile: kind === 'boq' ? file : null,
        tanggal: todayIndonesian(),
      })
      const data = res?.data ?? {}
      set({
        // Field yang tidak dihasilkan ekstraksi diisi nilai standar agar naskah tetap lengkap
        pendingExtraction: { keuntungan_risiko_persen: 8, masa_pemeliharaan_hari: 90, jaminan_pelaksanaan_persen: 5, ...data },
        sessionResources: [
          { icon: '📄', name: file.name, meta: `${formatFileSize(file.size)} · ${kind === 'boq' ? 'Bill of Quantities' : 'RKS'}` },
        ],
      })
      updateMessage(progressId, {
        pending: false,
        text: `Ekstraksi berkas \`${file.name}\` selesai. Periksa parameter berikut sebelum diterapkan ke dokumen.`,
        extractionCard: true,
        artifact: { icon: '📄', title: 'Draft Dokumen Tender v2.0', sub: 'Naskah Resmi Pertamina · IKPP 40 Poin & Kontrak' },
      })
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Terjadi kesalahan tak terduga.'
      set({ step: 1 })
      updateMessage(progressId, { pending: false, error: true, text: `Ekstraksi gagal: ${detail}` })
      pushToast('Ekstraksi berkas gagal. Periksa koneksi backend.', 'error')
    } finally {
      set({ isBusy: false })
    }
  },

  confirmExtraction: () => {
    const { pendingExtraction } = get()
    if (!pendingExtraction) return
    set((s) => ({ packages: { ...s.packages, tender: pendingExtraction }, pendingExtraction: null, step: 3 }))
    get().appendMessage({
      sender: 'ai',
      text: '✅ **Parameter telah diterapkan ke dokumen.** Data HPS, CSMS, TKDN, dan pejabat sudah tercermin pada kanvas. Dokumen siap diunduh dalam format Word (.docx).',
    })
    get().showArtifactTab('previewTab')
  },

  downloadDocx: async () => {
    const { mode, packages, pushToast } = get()
    if (mode === 'kb') return pushToast('Mode Knowledge Base tidak menghasilkan dokumen .docx.', 'info')
    if (!packages[mode]) return pushToast('Belum ada draf. Unggah berkas acuan atau muat data contoh terlebih dahulu.', 'info')
    set({ isDownloading: true })
    try {
      await generateDocument(mode, packages[mode])
      set({ step: 4 })
      pushToast('Dokumen .docx berhasil dibuat dan diunduh.', 'success')
    } catch (err) {
      pushToast(`Gagal membuat dokumen: ${err.message}`, 'error')
    } finally {
      set({ isDownloading: false })
    }
  },
}))
