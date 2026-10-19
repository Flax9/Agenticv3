import { useEffect } from 'react'

// Menjalankan handler saat tombol Esc ditekan, hanya ketika `active` bernilai true
export default function useEscapeKey(handler, active = true) {
  useEffect(() => {
    if (!active) return
    const onKeyDown = (e) => {
      if (e.key === 'Escape') handler()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [handler, active])
}
