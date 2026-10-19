import { useState } from 'react'
import { formatRupiah } from '../../services/format'
import { useAppStore } from '../../services/useAppStore'

// Field hasil ekstraksi yang ditampilkan; `edit` menentukan jenis input saat mode edit
const FIELDS = [
  { key: 'nama_pengadaan', label: 'Nama Pengadaan', edit: 'text', wide: true },
  { key: 'resiko_csms', label: 'Tingkat Risiko CSMS', format: (v) => `🛡️ ${String(v ?? '—').toUpperCase()}` },
  { key: 'jenis_kontrak', label: 'Jenis Kontrak' },
  { key: 'prime_cost', label: 'Prime Cost (HPS Riil)', edit: 'number', format: formatRupiah },
  { key: 'total_dengan_kr', label: 'Total HPS (+ K&R 8%)', edit: 'number', format: formatRupiah, highlight: true },
  { key: 'tkdn_minimal', label: 'Target Minimal TKDN', edit: 'number', format: (v) => `${v ?? '—'} %` },
]

// Micro-card verifikasi: nilai kritikal wajib dikonfirmasi user sebelum masuk ke dokumen
export default function ExtractionCard() {
  const pending = useAppStore((s) => s.pendingExtraction)
  const applied = useAppStore((s) => s.packages.tender)
  const updatePendingField = useAppStore((s) => s.updatePendingField)
  const confirmExtraction = useAppStore((s) => s.confirmExtraction)
  const [editing, setEditing] = useState(false)

  const data = pending ?? applied
  if (!data) return null
  const isPending = Boolean(pending)

  const handleChange = (field, raw) => {
    const value = field.edit === 'number' ? (raw === '' ? '' : Number(raw)) : raw
    updatePendingField(field.key, value)
  }

  return (
    <div className="mt-2.5 rounded-lg border border-pertamina-gray-300 bg-white p-3.5 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-2 border-b border-dashed border-pertamina-gray-200 pb-2">
        <span className="text-xs font-bold text-pertamina-navy">📋 Ringkasan Parameter Pengadaan Terdeteksi</span>
        <span
          className={`rounded-md px-1.5 py-0.5 font-mono text-[10px] ${
            isPending ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'
          }`}
        >
          {isPending ? 'Menunggu Verifikasi' : 'Sudah Diterapkan'}
        </span>
      </div>

      <dl className="mb-3.5 grid grid-cols-1 gap-x-3.5 gap-y-2.5 sm:grid-cols-2">
        {FIELDS.map((field) => (
          <div key={field.key} className={`flex flex-col ${field.wide ? 'sm:col-span-2' : ''}`}>
            <dt className="text-[10.5px] font-medium text-pertamina-gray-500">{field.label}</dt>
            {editing && isPending && field.edit ? (
              <input
                type={field.edit}
                value={data[field.key] ?? ''}
                min={field.edit === 'number' ? 0 : undefined}
                step="any"
                onChange={(e) => handleChange(field, e.target.value)}
                aria-label={field.label}
                className="mt-0.5 rounded border border-pertamina-gray-300 px-2 py-1 font-mono text-xs focus:border-pertamina-blue focus:outline-none focus:ring-2 focus:ring-pertamina-blue/20"
              />
            ) : (
              <dd
                className={`font-mono text-xs ${field.highlight ? 'font-bold text-pertamina-navy' : 'font-semibold text-pertamina-gray-900'}`}
              >
                {field.format ? field.format(data[field.key]) : (data[field.key] ?? '—')}
              </dd>
            )}
          </div>
        ))}
      </dl>

      {isPending ? (
        <div className="mt-2.5 flex gap-2">
          <button
            type="button"
            onClick={() => {
              setEditing(false)
              confirmExtraction()
            }}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-md bg-pertamina-navy px-3.5 py-2 text-[11.5px] font-semibold text-white transition hover:bg-pertamina-navy-light"
          >
            ✓ Terapkan ke Dokumen Canvas
          </button>
          <button
            type="button"
            onClick={() => setEditing((v) => !v)}
            aria-pressed={editing}
            className="rounded-md border border-pertamina-gray-300 bg-pertamina-gray-100 px-3.5 py-2 text-[11.5px] font-semibold text-pertamina-gray-900 transition hover:bg-pertamina-gray-200"
          >
            {editing ? '✓ Selesai Edit' : '✏️ Edit Nilai'}
          </button>
        </div>
      ) : (
        <p className="text-[11px] text-pertamina-gray-500">Perubahan selanjutnya dapat dilakukan lewat instruksi chat.</p>
      )}
    </div>
  )
}
