import { useAppStore } from '../../services/useAppStore'

// Tab vertikal di tepi kanan untuk membuka kembali canvas yang ditutup
export default function VerticalRestoreTab() {
  const isCanvasVisible = useAppStore((s) => s.isCanvasVisible)
  const toggleCanvasVisible = useAppStore((s) => s.toggleCanvasVisible)
  const activity = useAppStore((s) => s.activity)

  if (isCanvasVisible) return null

  return (
    <button
      type="button"
      onClick={() => toggleCanvasVisible(true)}
      title="Buka Kembali Review Dokumen (Canvas)"
      className="group fixed right-0 top-1/2 z-[98] flex -translate-y-1/2 select-none flex-col items-center gap-2 rounded-l-lg border-[1.5px] border-r-0 border-white/25 bg-pertamina-navy px-[7px] pb-3 pt-3.5 text-[11.5px] font-bold text-white shadow-[-4px_0_16px_rgba(0,45,98,0.22)] transition hover:-translate-x-[3px] hover:border-white/45 hover:bg-pertamina-navy-light hover:shadow-[-6px_0_22px_rgba(0,45,98,0.35)]"
    >
      <span className="text-[9px] text-blue-300 transition group-hover:-translate-x-0.5">◀</span>
      <span className="text-[13px]">📄</span>
      <span className="rotate-180 whitespace-nowrap text-[11px] font-bold tracking-wide text-pertamina-gray-50 [writing-mode:vertical-rl]">
        Review Dokumen
      </span>
      {/* Kuning berkedip selama agent/sinkronisasi berjalan, agar user tahu draf bisa berubah */}
      {activity ? (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400 shadow-[0_0_6px_#FBBF24]" title={activity.label} />
      ) : (
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shadow-[0_0_6px_#10B981]" title="Live Sync Aktif" />
      )}
    </button>
  )
}
