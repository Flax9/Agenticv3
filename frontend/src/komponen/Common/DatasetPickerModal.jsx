import { useCallback, useMemo, useState } from 'react'
import { formatFileSize } from '../../services/format'
import { can } from '../../services/permissions'
import { useAuthStore } from '../../services/useAuthStore'
import { useAppStore } from '../../services/useAppStore'
import useDatasetFiles from './useDatasetFiles'
import useEscapeKey from './useEscapeKey'

// Pengganti unggah berkas: user memilih berkas yang sudah ada di folder drive (DATASET_DIR)
const PURPOSES = {
  agent_boq: { title: 'Pilih BoQ dari Drive', hint: 'Agent RKS saat ini hanya dapat membaca BoQ berformat PDF.', ext: ['.pdf'] },
  extract: { title: 'Pilih Berkas Acuan dari Drive', hint: 'BoQ (PDF/Excel) atau RKS (PDF) untuk ekstraksi parameter.', ext: ['.pdf', '.xlsx', '.xls'] },
}

export default function DatasetPickerModal() {
  const purpose = useAppStore((s) => s.datasetPicker)
  const close = useAppStore((s) => s.closeDatasetPicker)
  const pickDatasetFile = useAppStore((s) => s.pickDatasetFile)
  const runDatasetSync = useAppStore((s) => s.runDatasetSync)
  const syncing = useAppStore((s) => s.activity?.kind === 'sync')
  const canSync = useAuthStore((s) => can(s.user, 'manageKb'))
  const state = useDatasetFiles({ acuan: true, enabled: Boolean(purpose) })
  const [search, setSearch] = useState('')
  const onClose = useCallback(() => close(), [close])
  useEscapeKey(onClose, Boolean(purpose))

  const config = PURPOSES[purpose]
  const files = useMemo(() => {
    if (!config) return []
    const q = search.trim().toLowerCase()
    return state.files.filter(
      (f) => config.ext.some((ext) => f.nama_file.toLowerCase().endsWith(ext)) && (!q || f.relative_path.toLowerCase().includes(q)),
    )
  }, [state.files, config, search])

  if (!purpose) return null

  const runSync = async () => {
    if (await runDatasetSync()) state.reload()
  }

  return (
    <div
      className="fixed inset-0 z-[1000] flex animate-fade-in items-center justify-center bg-pertamina-navy-dark/65 p-4 backdrop-blur-md sm:p-6"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="dataset-picker-title"
        className="flex max-h-full w-full max-w-[640px] animate-scale-in flex-col overflow-hidden rounded-2xl border-[1.5px] border-pertamina-gray-300 bg-white shadow-[0_24px_48px_rgba(0,26,61,0.3)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between bg-gradient-to-br from-pertamina-navy to-pertamina-navy-dark px-5 py-4 text-white">
          <div className="flex flex-col">
            <h3 id="dataset-picker-title" className="text-[14.5px] font-extrabold tracking-tight">
              {config.title}
            </h3>
            <span className="mt-0.5 text-[11px] text-blue-300">{config.hint}</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup pemilih berkas"
            className="flex h-7 w-7 items-center justify-center rounded-full bg-white/15 text-sm font-bold hover:bg-white/30"
          >
            ✕
          </button>
        </div>

        <div className="flex items-center gap-2 border-b border-pertamina-gray-200 bg-pertamina-gray-50 px-5 py-3">
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Cari nama berkas atau folder..."
            aria-label="Cari berkas"
            className="flex-1 rounded-md border border-pertamina-gray-300 bg-white px-3 py-1.5 text-xs outline-none focus:border-pertamina-blue"
          />
          {canSync && (
            <button
              type="button"
              onClick={runSync}
              disabled={syncing}
              className="shrink-0 rounded-md border border-pertamina-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-pertamina-navy hover:bg-pertamina-gray-100 disabled:opacity-50"
            >
              {syncing ? '⏳ Menyinkronkan...' : '🔄 Sinkronkan Drive'}
            </button>
          )}
        </div>

        <div className="min-h-[220px] flex-1 overflow-y-auto p-3">
          {state.status === 'loading' && <p className="p-3 text-xs text-pertamina-gray-500">⏳ Memuat daftar berkas...</p>}
          {state.status === 'error' && (
            <p className="rounded-md border border-red-200 bg-pertamina-red-light p-3 text-xs text-red-900">
              Gagal memuat berkas: {state.error}
            </p>
          )}
          {state.status === 'ready' && !state.configured && (
            <p className="p-3 text-xs text-pertamina-gray-600">
              Folder drive belum diatur di server (<code>DATASET_DIR</code>). Hubungi administrator.
            </p>
          )}
          {state.status === 'ready' && state.configured && files.length === 0 && (
            <p className="p-3 text-xs text-pertamina-gray-600">
              {search ? 'Tidak ada berkas yang cocok.' : 'Belum ada berkas yang cocok di folder drive.'}{' '}
              {canSync ? 'Klik Sinkronkan Drive setelah menambah berkas.' : 'Minta tim Procurement menyinkronkan drive.'}
            </p>
          )}
          <ul className="flex flex-col gap-1.5">
            {files.map((f) => (
              <li key={f.id}>
                <button
                  type="button"
                  onClick={() => pickDatasetFile(f)}
                  className="flex w-full items-center justify-between gap-3 rounded-lg border border-pertamina-gray-200 bg-white px-3 py-2.5 text-left transition hover:border-pertamina-blue hover:bg-blue-50"
                >
                  <span className="flex min-w-0 flex-col">
                    <span className="truncate text-[12.5px] font-bold text-pertamina-navy">
                      {f.nama_file.toLowerCase().endsWith('.pdf') ? '📄' : '📊'} {f.nama_file}
                    </span>
                    <span className="truncate text-[10.5px] text-pertamina-gray-500">{f.relative_path}</span>
                  </span>
                  <span className="shrink-0 text-[10.5px] text-pertamina-gray-500">{formatFileSize(f.ukuran_bytes)}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
