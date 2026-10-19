import { useEffect, useState } from 'react'
import { listKnowledgeBase } from '../../services/api'
import { KB_COLLECTIONS } from '../../services/modes'
import { can } from '../../services/permissions'
import { useAuthStore } from '../../services/useAuthStore'
import { useAppStore } from '../../services/useAppStore'
import useDatasetFiles from '../Common/useDatasetFiles'

const DATASET_STATUS = {
  TERINDEKS: { label: '✓ Terindeks', className: 'text-emerald-600' },
  REFERENSI: { label: 'Berkas acuan', className: 'text-pertamina-blue' },
  DILEWATI: { label: '⚠ Dilewati', className: 'text-amber-600' },
  GAGAL: { label: '✕ Gagal', className: 'text-red-600' },
}

// Isi folder drive (DATASET_DIR) dan status sinkronisasinya ke Qdrant
function DatasetSection({ onSynced }) {
  const canSync = useAuthStore((s) => can(s.user, 'manageKb'))
  const runDatasetSync = useAppStore((s) => s.runDatasetSync)
  const syncActivity = useAppStore((s) => (s.activity?.kind === 'sync' ? s.activity : null))
  const state = useDatasetFiles()
  const syncing = Boolean(syncActivity)

  const runSync = async () => {
    if (await runDatasetSync()) {
      state.reload()
      onSynced()
    }
  }

  return (
    <div className="mb-4 rounded-lg border border-pertamina-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-sm font-bold text-pertamina-navy">
        <span>☁️ Folder Drive (Google Drive / OneDrive)</span>
        {canSync && (
          <button
            type="button"
            onClick={runSync}
            disabled={syncing || !state.configured}
            className="rounded-md bg-pertamina-blue px-3 py-1.5 text-[11.5px] font-bold text-white transition hover:bg-[#005FA8] disabled:opacity-50"
          >
            {syncing ? `⏳ ${syncActivity.detail}` : '🔄 Sinkronkan Sekarang'}
          </button>
        )}
      </div>
      <p className="mb-4 text-xs text-pertamina-gray-500">
        Berkas di subfolder <code>rks_kb/</code>, <code>contract_kb/</code>, dan <code>amendment_kb/</code> di-ingest ke
        Knowledge Base. Folder lain (mis. BoQ per paket) hanya menjadi berkas acuan yang bisa dipilih di chat.
      </p>

      {state.status === 'loading' && <p className="text-xs text-pertamina-gray-500">⏳ Memuat isi folder...</p>}
      {state.status === 'error' && <p className="text-xs text-red-700">Gagal memuat isi folder: {state.error}</p>}
      {state.status === 'ready' && !state.configured && (
        <p className="text-xs text-pertamina-gray-600">
          Folder drive belum diatur di server. Isi <code>DATASET_DIR</code> di <code>.env</code> dengan folder yang
          disinkronkan oleh Google Drive for Desktop atau OneDrive.
        </p>
      )}
      {state.status === 'ready' && state.configured && state.files.length === 0 && (
        <p className="text-xs text-pertamina-gray-600">Belum ada berkas tercatat. Jalankan sinkronisasi setelah folder terisi.</p>
      )}
      {state.status === 'ready' && state.files.length > 0 && (
        <div className="max-h-[320px] overflow-auto">
          <table className="doc-table">
            <thead>
              <tr>
                <th>Berkas</th>
                <th>Collection</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {state.files.map((f) => {
                const st = DATASET_STATUS[f.status] ?? { label: f.status, className: '' }
                return (
                  <tr key={f.id}>
                    <td className="break-all">{f.relative_path}</td>
                    <td>{f.collection ? <code>{f.collection}</code> : '—'}</td>
                    <td className={`font-bold ${st.className}`} title={f.pesan ?? undefined}>
                      {st.label}
                      {f.status === 'TERINDEKS' && <span className="font-normal text-pertamina-gray-500"> · {f.jumlah_chunk} chunks</span>}
                      {f.pesan && <div className="text-[10.5px] font-normal text-pertamina-gray-500">{f.pesan}</div>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// Daftar dokumen per collection Qdrant, diambil langsung dari GET /api/kb/list
export default function KnowledgeBaseView() {
  const [collection, setCollection] = useState(KB_COLLECTIONS[0].id)
  const [reloadKey, setReloadKey] = useState(0)
  // Hasil terakhir beserta collection & percobaan asalnya; status "loading" diturunkan dari sini
  const [result, setResult] = useState(null)

  useEffect(() => {
    let cancelled = false
    listKnowledgeBase(collection)
      .then((res) => !cancelled && setResult({ collection, reloadKey, documents: res.documents ?? {}, error: null }))
      .catch((err) => !cancelled && setResult({ collection, reloadKey, documents: {}, error: err.message }))
    return () => {
      cancelled = true
    }
  }, [collection, reloadKey])

  const isCurrent = result && result.collection === collection && result.reloadKey === reloadKey
  const state = !isCurrent
    ? { status: 'loading', documents: {} }
    : result.error
      ? { status: 'error', documents: {}, error: result.error }
      : { status: 'ready', documents: result.documents }
  const docs = Object.entries(state.documents)

  return (
    <>
      <DatasetSection onSynced={() => setReloadKey((k) => k + 1)} />
      <div className="mb-4 rounded-lg border border-pertamina-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2 text-sm font-bold text-pertamina-navy">
          <span>🗄️ Manajemen Knowledge Base Qdrant</span>
          <span className="rounded-md bg-pertamina-gray-100 px-1.5 py-0.5 font-mono text-[10px] font-normal text-pertamina-gray-500">
            all-minilm-l6-v2 (384 Dim)
          </span>
        </div>
        <p className="mb-4 text-xs text-pertamina-gray-500">
          Dokumen acuan yang terindeks digunakan oleh LLM untuk pencarian semantik (RAG) saat merumuskan klausul RKS,
          Kontrak, dan Amendemen.
        </p>
  
        <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-3" role="tablist" aria-label="Collection Qdrant">
          {KB_COLLECTIONS.map((c) => (
            <button
              key={c.id}
              type="button"
              role="tab"
              aria-selected={collection === c.id}
              onClick={() => setCollection(c.id)}
              className={`rounded-lg border-[1.5px] p-3.5 text-left transition hover:border-pertamina-blue hover:bg-blue-50 ${
                collection === c.id ? 'border-pertamina-blue bg-blue-50' : 'border-pertamina-gray-200 bg-pertamina-gray-50'
              }`}
            >
              <div className="mb-1 text-[13px] font-bold text-pertamina-navy">
                {c.icon} {c.id}
              </div>
              <div className="text-[11px] text-pertamina-gray-500">
                {collection === c.id && state.status === 'ready' ? `${docs.length} berkas terindeks` : 'Klik untuk melihat'}
              </div>
            </button>
          ))}
        </div>
  
        {state.status === 'loading' && <p className="text-xs text-pertamina-gray-500">⏳ Memuat daftar dokumen...</p>}
  
        {state.status === 'error' && (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-red-200 bg-pertamina-red-light px-3 py-2 text-xs text-red-900">
            <span>Gagal memuat Knowledge Base: {state.error}</span>
            <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="font-bold underline">
              Coba lagi
            </button>
          </div>
        )}
  
        {state.status === 'ready' &&
          (docs.length === 0 ? (
            <p className="text-xs text-pertamina-gray-500">Belum ada dokumen di collection ini.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="doc-table">
                <thead>
                  <tr>
                    <th>Nama Berkas PDF</th>
                    <th>Jumlah Chunks</th>
                    <th>Status Qdrant</th>
                  </tr>
                </thead>
                <tbody>
                  {docs.map(([name, chunks]) => (
                    <tr key={name}>
                      <td>📄 {name}</td>
                      <td>
                        <code>{chunks} chunks</code>
                      </td>
                      <td className="font-bold text-emerald-600">✓ Synced</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
      </div>
    </>
  )
}
