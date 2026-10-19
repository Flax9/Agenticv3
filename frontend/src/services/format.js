const rupiahFormatter = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 0 })

export function formatRupiah(value) {
  const num = Number(value)
  if (value === null || value === undefined || value === '' || Number.isNaN(num)) return '—'
  return `Rp ${rupiahFormatter.format(num)}`
}

// Persentase perubahan dari nilai lama ke nilai baru; null bila nilai lama kosong/nol
export function percentChange(oldValue, newValue) {
  if (!oldValue) return null
  return ((newValue - oldValue) / oldValue) * 100
}

export function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Format tanggal yang dipahami parser backend, mis. "19 Oktober 2026"
export function todayIndonesian() {
  return new Intl.DateTimeFormat('id-ID', { day: '2-digit', month: 'long', year: 'numeric' }).format(new Date())
}
