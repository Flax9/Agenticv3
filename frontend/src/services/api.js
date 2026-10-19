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

// BoQ boleh PDF/Excel, RKS harus PDF
export async function extractTenderMetadata({ rksFile, boqFile, tanggal = '', resikoCsms = 'Tinggi' }) {
  const form = new FormData()
  if (rksFile) form.append('file_rks', rksFile)
  if (boqFile) form.append('file_boq', boqFile)
  form.append('tanggal', tanggal)
  form.append('resiko_csms', resikoCsms)
  const res = await request('/api/extract-tender-metadata', { method: 'POST', body: form })
  return res.json()
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

export async function generateDocument(mode, data) {
  const endpoint = GENERATE_ENDPOINTS[mode]
  if (!endpoint) throw new ApiError(`Mode "${mode}" tidak memiliki generator dokumen.`, 400)
  const fields = endpoint.payload ? endpoint.payload(data) : data
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
