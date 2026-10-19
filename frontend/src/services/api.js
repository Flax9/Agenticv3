// Klien API ke backend FastAPI.
// Selalu memakai path relatif "/api/...": saat development diteruskan oleh proxy Vite,
// di produksi oleh Nginx. Tidak ada fallback diam-diam ke data demo.
import { formatRupiah } from './format'
import { useAuthStore } from './useAuthStore'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function readError(res) {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
    return JSON.stringify(body.detail ?? body)
  } catch {
    return res.statusText || `HTTP ${res.status}`
  }
}

async function send(path, { timeoutMs, ...options }) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const token = useAuthStore.getState().accessToken
  const headers = { ...options.headers, ...(token ? { Authorization: `Bearer ${token}` } : {}) }
  try {
    return await fetch(path, { ...options, headers, signal: controller.signal })
  } catch (err) {
    if (err.name === 'AbortError') throw new ApiError('Permintaan ke server melebihi batas waktu.', 0)
    throw new ApiError('Tidak dapat terhubung ke server backend.', 0)
  } finally {
    clearTimeout(timer)
  }
}

async function request(path, { timeoutMs = 300000, ...options } = {}) {
  let res = await send(path, { timeoutMs, ...options })
  // Access token kedaluwarsa: perbarui sekali lewat cookie refresh, lalu ulangi request
  if (res.status === 401) {
    const auth = useAuthStore.getState()
    if (await auth.refresh()) {
      res = await send(path, { timeoutMs, ...options })
    } else {
      auth.expireSession()
      throw new ApiError('Sesi login telah berakhir. Silakan login kembali.', 401)
    }
  }
  if (!res.ok) throw new ApiError(await readError(res), res.status)
  return res
}

function toFormData(fields) {
  const form = new FormData()
  for (const [key, value] of Object.entries(fields)) {
    // Hanya nilai skalar yang dikirim; array/objek (mis. boq_items) khusus tampilan
    if (value === null || value === undefined || typeof value === 'object') continue
    form.append(key, String(value))
  }
  return form
}

function filenameFromResponse(res, fallback) {
  const header = res.headers.get('Content-Disposition') || ''
  const utf8 = header.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8) return decodeURIComponent(utf8[1])
  const plain = header.match(/filename="?([^";]+)"?/i)
  return plain ? plain[1] : fallback
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  // Revoke ditunda agar unduhan sempat dimulai di semua browser
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export async function checkHealth() {
  try {
    const res = await request('/api/health', { timeoutMs: 3000 })
    return await res.json()
  } catch {
    return null
  }
}

function jsonBody(body) {
  return { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
}

// Berkas acuan dipilih dari folder dataset (drive); BoQ boleh PDF/Excel, RKS harus PDF
export async function extractTenderMetadata({ rksFileId, boqFileId, projectId, tanggal = '', resikoCsms = 'Tinggi' }) {
  const form = toFormData({
    rks_file_id: rksFileId ?? '',
    boq_file_id: boqFileId ?? '',
    project_id: projectId ?? '',
    tanggal,
    resiko_csms: resikoCsms,
  })
  const res = await request('/api/extract-tender-metadata', { method: 'POST', body: form })
  return res.json()
}

// ── Sesi chat Copilot ───────────────────────────────────────
// Nama mode di UI → tipe_dokumen di backend
export const MODE_TO_TIPE = { tender: 'tender', rks: 'rks', contract: 'kontrak', amendment: 'amendemen' }
export const TIPE_TO_MODE = Object.fromEntries(Object.entries(MODE_TO_TIPE).map(([mode, tipe]) => [tipe, mode]))

export async function createChatSession(mode) {
  const res = await request('/api/chat/sessions', { method: 'POST', timeoutMs: 15000, ...jsonBody({ tipe_dokumen: MODE_TO_TIPE[mode] }) })
  return res.json()
}

export async function listChatSessions(limit = 8) {
  const res = await request(`/api/chat/sessions?limit=${limit}`, { timeoutMs: 15000 })
  return res.json()
}

export async function getChatSession(sessionId) {
  const res = await request(`/api/chat/sessions/${sessionId}`, { timeoutMs: 15000 })
  return res.json()
}

// Satu giliran agent bisa berlangsung beberapa menit (mis. Docling membaca BoQ di CPU)
const STREAM_TIMEOUT_MS = 20 * 60 * 1000

function parseSseBlock(block) {
  let event = 'message'
  const data = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) data.push(line.slice(5).trimStart())
  }
  return data.length ? { event, data: JSON.parse(data.join('\n')) } : null
}

// Versi streaming dari sendChatMessage (SSE lewat fetch + ReadableStream agar bisa mengirim
// body & header Authorization). onEvent menerima ('progress' | 'token', data); hasil akhir
// (isi event 'done') dikembalikan sebagai nilai fungsi.
export async function streamChatMessage(sessionId, { content = '', datasetFileId = null }, onEvent) {
  const body = { content, ...(datasetFileId ? { dataset_file_id: datasetFileId } : {}) }
  const res = await request(`/api/chat/sessions/${sessionId}/stream`, {
    method: 'POST',
    timeoutMs: STREAM_TIMEOUT_MS,
    ...jsonBody(body),
  })
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += value.replace(/\r\n/g, '\n')
    let boundary
    while ((boundary = buffer.indexOf('\n\n')) >= 0) {
      const parsed = parseSseBlock(buffer.slice(0, boundary))
      buffer = buffer.slice(boundary + 2)
      if (!parsed) continue
      if (parsed.event === 'done') return parsed.data
      if (parsed.event === 'error') throw new ApiError(parsed.data.detail ?? 'Gagal memproses pesan.', 500)
      onEvent?.(parsed.event, parsed.data)
    }
  }
  throw new ApiError('Koneksi ke server terputus sebelum jawaban selesai.', 0)
}

export async function downloadDraft(draftId) {
  const res = await request(`/api/drafts/${draftId}/download`, { timeoutMs: 60000 })
  downloadBlob(await res.blob(), filenameFromResponse(res, 'Draf_RKS.docx'))
}

// ── Dataset (drive eksternal) ───────────────────────────────
export async function listDatasetFiles({ acuan = false } = {}) {
  const res = await request(`/api/dataset/files${acuan ? '?acuan=true' : ''}`, { timeoutMs: 15000 })
  return res.json()
}

// Memulai sinkronisasi sebagai job latar belakang; kembalian berisi { id, status, progress }
export async function startDatasetSync() {
  const res = await request('/api/dataset/sync', { method: 'POST', timeoutMs: 15000 })
  return res.json()
}

export async function getJob(jobId) {
  const res = await request(`/api/jobs/${jobId}`, { timeoutMs: 15000 })
  return res.json()
}

// Pantau job sampai selesai; onProgress menerima objek job setiap kali status diperiksa
export async function waitForJob(jobId, onProgress, intervalMs = 1500) {
  for (;;) {
    const job = await getJob(jobId)
    onProgress?.(job)
    if (job.status === 'selesai') return job.result
    if (job.status === 'gagal') throw new ApiError(job.error || 'Job gagal.', 500)
    await new Promise((resolve) => setTimeout(resolve, intervalMs))
  }
}

// Data amendemen di UI → field form yang diharapkan /api/generate-amendemen
function amendmentPayload(d) {
  const { nilai_kontrak_asal, nilai_kontrak_baru, alasan, ...rest } = d
  return {
    ...rest,
    nilai_kontrak_asal_str: formatRupiah(nilai_kontrak_asal),
    detail_perubahan_json: JSON.stringify([
      {
        jenis_perubahan: 'Nilai Kontrak',
        pasal_referensi: 'Pasal 3 – Nilai Kontrak',
        isi_lama: `Nilai kontrak sebesar ${formatRupiah(nilai_kontrak_asal)} termasuk PPN.`,
        isi_baru: `Nilai kontrak menjadi ${formatRupiah(nilai_kontrak_baru)} termasuk PPN.`,
        alasan_perubahan: alasan,
      },
    ]),
  }
}

const GENERATE_ENDPOINTS = {
  tender: { path: '/api/generate-tender', name: (d) => `Dokumen_Tender_${d.nama_pengadaan || 'Paket'}` },
  rks: { path: '/api/generate-rks', name: (d) => `RKS_${d.jenis_pekerjaan || 'Proyek'}` },
  contract: { path: '/api/generate-kontrak', name: (d) => `Rancangan_Kontrak_${d.nama_pekerjaan || 'Definitif'}` },
  amendment: {
    path: '/api/generate-amendemen',
    name: (d) => `Draft_Amendemen_${d.judul_pekerjaan || 'Addendum'}`,
    payload: amendmentPayload,
  },
}

// projectId (opsional) menyimpan hasilnya sebagai versi draf paket di database
export async function generateDocument(mode, data, projectId = '') {
  const endpoint = GENERATE_ENDPOINTS[mode]
  if (!endpoint) throw new ApiError(`Mode "${mode}" tidak memiliki generator dokumen.`, 400)
  const fields = { ...(endpoint.payload ? endpoint.payload(data) : data), project_id: projectId }
  const res = await request(endpoint.path, { method: 'POST', body: toFormData(fields) })
  const contentType = res.headers.get('Content-Type') || ''
  if (contentType.includes('application/json')) {
    // Backend mengembalikan JSON bila draft dibuat tetapi berkas .docx tidak ditemukan
    const body = await res.json()
    throw new ApiError(body.message || 'Dokumen tidak berhasil diekspor ke .docx.', res.status)
  }
  const fallback = `${endpoint.name(data).substring(0, 40)}.docx`
  downloadBlob(await res.blob(), filenameFromResponse(res, fallback))
}

export async function listKnowledgeBase(collection) {
  const res = await request(`/api/kb/list?collection=${encodeURIComponent(collection)}`, { timeoutMs: 30000 })
  return res.json()
}
