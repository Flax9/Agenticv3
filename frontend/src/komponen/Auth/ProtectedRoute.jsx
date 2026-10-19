import { useEffect } from 'react'
import { useAppStore } from '../../services/useAppStore'
import { useAuthStore } from '../../services/useAuthStore'
import LoginPage from './LoginPage'

// Menampilkan children hanya untuk pengguna yang sudah login; selain itu halaman login.
export default function ProtectedRoute({ children }) {
  const status = useAuthStore((s) => s.status)
  const restoreSession = useAuthStore((s) => s.restoreSession)

  useEffect(() => {
    restoreSession()
  }, [restoreSession])

  // Saat logout/sesi berakhir, bersihkan percakapan & draf agar tidak terlihat oleh pengguna berikutnya
  useEffect(() => {
    if (status === 'anonymous') useAppStore.setState(useAppStore.getInitialState(), true)
  }, [status])

  if (status === 'checking') {
    return (
      <div className="flex h-full items-center justify-center bg-pertamina-navy text-sm font-semibold text-white/80" aria-live="polite">
        Memulihkan sesi...
      </div>
    )
  }
  return status === 'authenticated' ? children : <LoginPage />
}
