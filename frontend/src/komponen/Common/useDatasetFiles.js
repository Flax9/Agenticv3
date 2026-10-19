import { useCallback, useEffect, useState } from 'react'
import { listDatasetFiles } from '../../services/api'

// Daftar berkas folder dataset (drive). Status "loading" diturunkan dari hasil terakhir,
// sama seperti KnowledgeBaseView, agar effect tidak memanggil setState secara sinkron.
export default function useDatasetFiles({ acuan = false, enabled = true } = {}) {
  const [reloadKey, setReloadKey] = useState(0)
  const [result, setResult] = useState(null)

  useEffect(() => {
    if (!enabled) return
    let cancelled = false
    listDatasetFiles({ acuan })
      .then((res) => !cancelled && setResult({ reloadKey, files: res.files, configured: res.configured, error: null }))
      .catch((err) => !cancelled && setResult({ reloadKey, files: [], configured: true, error: err.message }))
    return () => {
      cancelled = true
    }
  }, [acuan, enabled, reloadKey])

  const reload = useCallback(() => setReloadKey((k) => k + 1), [])

  if (!result || result.reloadKey !== reloadKey) return { status: 'loading', files: [], configured: true, reload }
  if (result.error) return { status: 'error', files: [], configured: true, error: result.error, reload }
  return { status: 'ready', files: result.files, configured: result.configured, reload }
}
