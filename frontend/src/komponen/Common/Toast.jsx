import { useAppStore } from '../../services/useAppStore'

const TONES = {
  info: 'border-pertamina-blue bg-pertamina-blue-light text-pertamina-navy',
  success: 'border-emerald-500 bg-emerald-50 text-emerald-900',
  error: 'border-pertamina-red bg-pertamina-red-light text-red-900',
}

export default function ToastStack() {
  const toasts = useAppStore((s) => s.toasts)
  const dismissToast = useAppStore((s) => s.dismissToast)

  return (
    <div className="pointer-events-none fixed bottom-4 left-1/2 z-[1100] flex w-[min(92vw,420px)] -translate-x-1/2 flex-col gap-2" aria-live="polite">
      {toasts.map((t) => (
        <div
          key={t.id}
          role={t.tone === 'error' ? 'alert' : 'status'}
          className={`pointer-events-auto flex animate-fade-in items-start justify-between gap-3 rounded-lg border-l-4 px-4 py-3 text-[12.5px] font-medium shadow-pertamina-lg ${TONES[t.tone] ?? TONES.info}`}
        >
          <span>{t.message}</span>
          <button
            type="button"
            onClick={() => dismissToast(t.id)}
            aria-label="Tutup notifikasi"
            className="shrink-0 rounded px-1 text-current opacity-60 hover:opacity-100"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
