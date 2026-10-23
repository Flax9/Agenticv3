import { create } from 'zustand'
import { DEMO_PACKAGES } from '../demo/demoData'
import { demoOpening } from '../demo/demoConversation'
import {
  ApiError,
  MODE_TO_TIPE,
  TIPE_TO_MODE,
  createChatSession,
  downloadDraft,
  extractTenderMetadata,
  generateDocument,
  getChatSession,
  startDatasetSync,
  streamChatMessage,
  waitForJob,
} from './api'
import { formatFileSize, todayIndonesian } from './format'
import { MODE_META } from './modes'

let nextId = 1
const newId = () => nextId++
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const isWideScreen = () => typeof window !== 'undefined' && window.matchMedia('(min-width: 1280px)').matches

let highlightTimer
let pendingSession = null

// Pesan dari backend → bentuk pesan yang dipakai ChatBubble
function fromServerMessage(m) {
  return {
    id: m.id,
    sender: m.role === 'user' ? 'user' : 'ai',
    text: m.content,
    error: Boolean(m.artifacts_payload?.error),
    artifact: m.artifacts_payload?.draft_id
      ? { icon: '📋', title: `Draf RKS ${m.artifacts_payload.versi}`, sub: 'Klik untuk meninjau di kanvas', tab: 'previewTab' }
      : undefined,
  }
}

// Posisi stepper RKS diturunkan dari state agent
function rksStep(draft, awaiting) {
  if (draft?.has_docx) return 4
  if (draft || awaiting === 'review_rks') return 3
  if (awaiting === 'upload_boq') return 2
  return 1
}

const emptySession = { session: null, draft: null, awaiting: null }

export const useAppStore = create((set, get) => ({
  // ── Tampilan ──────────────────────────────────────────────
  mode: 'tender',
  step: 1,
  activeTab: 'previewTab',
  isDocPickerOpen: true,
  isDrawerOpen: false,
  isCanvasVisible: isWideScreen(),
  isCanvasFullscreen: false,
  // Pemilih berkas dari folder dataset (drive): null | 'agent_boq' | 'extract'
  datasetPicker: null,

  // ── Data ─────────────────────────────────────────────────
  // Paket per mode; null = belum ada data (canvas menampilkan empty state)
  packages: { tender: null, rks: null, contract: null, amendment: null },
  // Hasil ekstraksi yang belum dikonfirmasi user; baru masuk ke packages.tender setelah "Terapkan"
  pendingExtraction: null,
  messages: [],
  sessionResources: [],
  // Sesi chat aktif di backend: { id, project_id, nama_pengadaan, tipe_dokumen }
  session: null,
  // Draf aktif hasil agent (RKS): { id, versi, konten_json, has_docx }
  draft: null,
  // Node agent yang menunggu jawaban: null | 'upload_boq' | 'review_rks'
  awaiting: null,
  highlight: null, // { key } field yang baru berubah lewat chat
  isBusy: false,
  isDownloading: false,
  // Proses yang sedang berjalan (ditampilkan di Progress Drawer & tab canvas):
  // null | { kind: 'agent' | 'sync', label, detail }
  activity: null,
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
      ...emptySession,
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
  openDatasetPicker: (purpose) => set({ datasetPicker: purpose }),
  closeDatasetPicker: () => set({ datasetPicker: null }),

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
    const id = message.id ?? newId()
    set((s) => ({ messages: [...s.messages, { ...message, id }] }))
    return id
  },
  updateMessage: (id, patch) =>
    set((s) => ({ messages: s.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)) })),
  removeMessage: (id) => set((s) => ({ messages: s.messages.filter((m) => m.id !== id) })),

  updateField: (key, value) => {
    const { mode, packages } = get()
    if (!packages[mode]) return
    set({ packages: { ...packages, [mode]: { ...packages[mode], [key]: value } }, highlight: { key } })
    clearTimeout(highlightTimer)
    highlightTimer = setTimeout(() => set({ highlight: null }), 3000)
  },

  // Sesi backend dibuat saat pesan/aksi pertama, agar membuka Doc Picker saja tidak membuat paket kosong
  ensureSession: async () => {
    const { session, mode } = get()
    if (session) return session
    if (!MODE_TO_TIPE[mode]) return null
    // Dua aksi bersamaan (mis. kirim pesan & unduh) tidak boleh membuat dua paket
    pendingSession ??= createChatSession(mode).finally(() => {
      pendingSession = null
    })
    const created = await pendingSession
    // User bisa berganti mode selama request berjalan; sesi yang terlambat tidak dipakai
    if (get().mode !== mode) return null
    set({ session: created })
    return created
  },

  sendMessage: async (text, { datasetFile = null } = {}) => {
    const trimmed = text.trim()
    if ((!trimmed && !datasetFile) || get().isBusy) return
    if (get().mode !== 'rks') return // agent percakapan baru tersedia untuk RKS
    const { appendMessage, updateMessage, removeMessage, pushToast } = get()
    const userMsgId = appendMessage({
      sender: 'user',
      text: datasetFile ? `📎 Memakai BoQ dari drive: ${datasetFile.relative_path}` : trimmed,
    })
    set({ isBusy: true })
    // Bubble sementara: menampilkan tahap agent yang sedang berjalan, lalu token jawaban
    const pendingId = appendMessage({ sender: 'ai', pending: true, text: 'Copilot sedang memproses...' })
    let streamed = ''
    const onEvent = (kind, data) => {
      if (kind === 'progress') {
        set({ activity: { kind: 'agent', label: data.label, detail: 'Copilot sedang bekerja' } })
        if (!streamed) updateMessage(pendingId, { text: `${data.label}...` })
      } else if (kind === 'token') {
        streamed += data.text
        updateMessage(pendingId, { pending: false, text: streamed })
      }
    }
    try {
      const session = await get().ensureSession()
      if (!session) throw new ApiError('Mode ini tidak memiliki sesi percakapan.', 400)
      const turn = await streamChatMessage(session.id, { content: trimmed, datasetFileId: datasetFile?.id }, onEvent)
      removeMessage(pendingId)
      if (get().session?.id !== session.id) return // user sudah pindah sesi
      const [userMsg, ...replies] = turn.messages.map(fromServerMessage)
      updateMessage(userMsgId, { text: userMsg?.text ?? trimmed })
      replies.forEach((m) => appendMessage(m))

      const draftChanged = turn.draft && turn.draft.id !== get().draft?.id
      const exported = turn.draft?.has_docx && !get().draft?.has_docx
      set({
        draft: turn.draft,
        awaiting: turn.awaiting,
        session: { ...session, nama_pengadaan: turn.nama_pengadaan },
        step: get().mode === 'rks' ? rksStep(turn.draft, turn.awaiting) : get().step,
      })
      if (draftChanged) get().showArtifactTab('previewTab')
      if (exported) pushToast('Dokumen RKS sudah diekspor. Klik Unduh .docx di menu untuk menyimpannya.', 'success')
    } catch (err) {
      removeMessage(pendingId)
      removeMessage(userMsgId)
      appendMessage({ sender: 'ai', error: true, text: `Pesan tidak terkirim: ${err.message}` })
    } finally {
      set({ isBusy: false, activity: null })
    }
  },

  // Sinkronisasi folder drive → Knowledge Base sebagai job latar belakang
  runDatasetSync: async () => {
    const { pushToast } = get()
    if (get().activity?.kind === 'sync') return null
    set({ activity: { kind: 'sync', label: 'Sinkronisasi folder drive', detail: 'Memulai...' } })
    try {
      const job = await startDatasetSync()
      const r = await waitForJob(job.id, ({ progress }) => {
        if (progress?.total) {
          set({
            activity: {
              kind: 'sync',
              label: 'Sinkronisasi folder drive',
              detail: `${progress.selesai}/${progress.total} berkas${progress.berkas ? ` · ${progress.berkas}` : ''}`,
            },
          })
        }
      })
      const problems = r.gagal.length + r.dilewati.length
      pushToast(
        `Sinkron selesai: ${r.ditambah.length} baru, ${r.diperbarui.length} diperbarui, ${r.dihapus.length} dihapus${problems ? `, ${problems} perlu dicek` : ''}.`,
        problems ? 'info' : 'success',
      )
      return r
    } catch (err) {
      pushToast(`Sinkron gagal: ${err.message}`, 'error')
      return null
    } finally {
      set({ activity: null })
    }
  },

  // Membuka kembali sesi lama dari riwayat
  openSession: async (sessionId) => {
    if (get().isBusy) return
    set({ isBusy: true })
    try {
      const detail = await getChatSession(sessionId)
      const mode = TIPE_TO_MODE[detail.tipe_dokumen] ?? 'tender'
      get().setMode(mode)
      const { messages, draft, awaiting, ...session } = detail
      set({
        isDocPickerOpen: false,
        session,
        draft,
        awaiting,
        messages: messages.map(fromServerMessage),
        step: mode === 'rks' ? rksStep(draft, awaiting) : 1,
      })
      if (draft) get().showArtifactTab('previewTab')
    } catch (err) {
      get().pushToast(`Gagal membuka sesi: ${err.message}`, 'error')
    } finally {
      set({ isBusy: false })
    }
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

  // Berkas dipilih dari pemilih dataset: BoQ untuk agent RKS, atau BoQ/RKS untuk ekstraksi Tender
  pickDatasetFile: async (file) => {
    const purpose = get().datasetPicker
    set({ datasetPicker: null })
    if (purpose === 'agent_boq') return get().sendMessage('', { datasetFile: file })
    if (purpose === 'extract') return get().extractFromDataset(file)
  },

  extractFromDataset: async (file) => {
    const { mode, appendMessage, updateMessage, pushToast } = get()
    if (get().isBusy || mode !== 'tender') return
    const isExcel = /\.xlsx?$/i.test(file.nama_file)
    // Excel selalu BoQ; PDF dianggap BoQ bila namanya mengandung "boq", selain itu RKS
    const kind = isExcel || /boq/i.test(file.nama_file) ? 'boq' : 'rks'
    appendMessage({
      sender: 'user',
      text: 'Gunakan berkas acuan dari drive.',
      attachment: { name: file.relative_path, size: formatFileSize(file.ukuran_bytes) },
    })
    set({ isBusy: true, step: 2 })
    const progressId = appendMessage({
      sender: 'ai',
      pending: true,
      text: `Berkas \`${file.nama_file}\` sedang dibaca sebagai **${kind === 'boq' ? 'BoQ' : 'RKS'}** dan diekstraksi oleh LLM di backend...`,
    })

    try {
      const session = await get().ensureSession()
      const res = await extractTenderMetadata({
        rksFileId: kind === 'rks' ? file.id : null,
        boqFileId: kind === 'boq' ? file.id : null,
        projectId: session?.project_id,
        tanggal: todayIndonesian(),
      })
      const data = res?.data ?? {}
      set({
        // Field yang tidak dihasilkan ekstraksi diisi nilai standar agar naskah tetap lengkap
        pendingExtraction: { keuntungan_risiko_persen: 8, masa_pemeliharaan_hari: 90, jaminan_pelaksanaan_persen: 5, ...data },
        sessionResources: [
          { icon: '📄', name: file.relative_path, meta: `${formatFileSize(file.ukuran_bytes)} · ${kind === 'boq' ? 'Bill of Quantities' : 'RKS'}` },
        ],
      })
      updateMessage(progressId, {
        pending: false,
        text: `Ekstraksi berkas \`${file.nama_file}\` selesai. Periksa parameter berikut sebelum diterapkan ke dokumen.`,
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
    const { mode, packages, draft, pushToast } = get()
    if (mode === 'kb') return pushToast('Mode Knowledge Base tidak menghasilkan dokumen .docx.', 'info')
    if (mode === 'rks' && draft) {
      if (!draft.has_docx) {
        return pushToast('Draf RKS belum diekspor. Ketik "setuju" di chat agar Copilot membuat berkas .docx.', 'info')
      }
      set({ isDownloading: true })
      try {
        await downloadDraft(draft.id)
      } catch (err) {
        pushToast(`Gagal mengunduh dokumen: ${err.message}`, 'error')
      } finally {
        set({ isDownloading: false })
      }
      return
    }
    if (!packages[mode]) return pushToast('Belum ada draf. Pilih berkas acuan dari drive atau muat data contoh terlebih dahulu.', 'info')
    set({ isDownloading: true })
    try {
      // Data demo tidak disimpan sebagai draf paket
      const isDemo = get().sessionResources.some((r) => r.name === 'Data Contoh (Demo)')
      const session = isDemo ? null : await get().ensureSession()
      await generateDocument(mode, packages[mode], session?.project_id ?? '')
      set({ step: 4 })
      pushToast('Dokumen .docx berhasil dibuat dan diunduh.', 'success')
    } catch (err) {
      pushToast(`Gagal membuat dokumen: ${err.message}`, 'error')
    } finally {
      set({ isDownloading: false })
    }
  },
}))
