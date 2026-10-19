export const ACCEPTED_UPLOAD_EXT = ['.pdf', '.xlsx', '.xls']
const MAX_UPLOAD_BYTES = 100 * 1024 * 1024

// Validasi awal di browser; backend tetap wajib memvalidasi ulang
export function validateUpload(file) {
  const name = file.name.toLowerCase()
  if (!ACCEPTED_UPLOAD_EXT.some((ext) => name.endsWith(ext))) return 'Format berkas harus PDF atau Excel (.xlsx/.xls).'
  if (file.size > MAX_UPLOAD_BYTES) return 'Ukuran berkas melebihi batas 100 MB.'
  return null
}

// Berkas .xlsx/.xls selalu BoQ; PDF dianggap BoQ bila namanya mengandung "boq", selain itu RKS
export function classifyUpload(file) {
  const name = file.name.toLowerCase()
  if (name.endsWith('.xlsx') || name.endsWith('.xls')) return 'boq'
  return name.includes('boq') ? 'boq' : 'rks'
}
