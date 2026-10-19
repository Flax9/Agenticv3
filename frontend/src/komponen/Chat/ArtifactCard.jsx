import { can } from '../../services/permissions'
import { useAuthStore } from '../../services/useAuthStore'
import { useAppStore } from '../../services/useAppStore'

// Kartu embed dokumen di dalam bubble chat (gaya "artifact")
export default function ArtifactCard({ icon, title, sub }) {
  const showArtifactTab = useAppStore((s) => s.showArtifactTab)
  const downloadDocx = useAppStore((s) => s.downloadDocx)
  const isDownloading = useAppStore((s) => s.isDownloading)
  const hasPackage = useAppStore((s) => Boolean(s.packages[s.mode]))
  const canGenerate = useAuthStore((s) => can(s.user, 'generate'))

  return (
    <div className="mt-2.5 flex flex-wrap items-center justify-between gap-3 rounded-lg border-[1.5px] border-[#D0E1F4] bg-pertamina-gray-50 px-3.5 py-3 shadow-[0_2px_6px_rgba(0,45,98,0.05)] transition hover:border-pertamina-blue hover:bg-white hover:shadow-[0_6px_16px_rgba(0,114,206,0.1)]">
      <div className="flex min-w-0 items-center gap-2.5">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-blue-200 bg-blue-50 text-lg">
          {icon}
        </span>
        <span className="flex min-w-0 flex-col">
          <span className="truncate text-[13px] font-bold leading-tight text-pertamina-navy">{title}</span>
          <span className="text-[11px] text-pertamina-gray-500">{sub}</span>
        </span>
      </div>
      <div className="flex shrink-0 items-center gap-1.5">
        <button
          type="button"
          onClick={() => showArtifactTab('previewTab')}
          className="rounded-md bg-pertamina-blue px-3 py-1.5 text-[11.5px] font-bold text-white transition hover:-translate-y-px hover:bg-[#005FA8]"
        >
          Lihat di Canvas ↗
        </button>
        {canGenerate && (
          <button
            type="button"
            onClick={downloadDocx}
            disabled={!hasPackage || isDownloading}
            title={hasPackage ? 'Unduh dokumen .docx' : 'Terapkan parameter terlebih dahulu'}
            className="rounded-md border border-pertamina-gray-200 bg-pertamina-gray-100 px-3 py-1.5 text-[11.5px] font-bold text-pertamina-gray-600 transition hover:bg-pertamina-gray-200 hover:text-pertamina-navy disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isDownloading ? 'Membuat...' : 'Unduh .DOCX'}
          </button>
        )}
      </div>
    </div>
  )
}
