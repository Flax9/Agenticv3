import { MODE_META } from '../../services/modes'
import { can } from '../../services/permissions'
import { useAuthStore } from '../../services/useAuthStore'
import { useAppStore } from '../../services/useAppStore'
import HamburgerMenu from './HamburgerMenu'

const STATUS_DOT = {
  checking: { color: 'bg-pertamina-gray-400', label: 'Memeriksa koneksi backend...' },
  online: { color: 'bg-emerald-500', label: 'Terhubung ke backend FastAPI' },
  offline: { color: 'bg-amber-500', label: 'Backend tidak terhubung' },
}

export default function Navbar() {
  const mode = useAppStore((s) => s.mode)
  const step = useAppStore((s) => s.step)
  const backendStatus = useAppStore((s) => s.backendStatus)
  const isDownloading = useAppStore((s) => s.isDownloading)
  const openDocPicker = useAppStore((s) => s.openDocPicker)
  const toggleDrawer = useAppStore((s) => s.toggleDrawer)
  const downloadDocx = useAppStore((s) => s.downloadDocx)
  const canGenerate = useAuthStore((s) => can(s.user, 'generate'))

  const meta = MODE_META[mode]
  const status = STATUS_DOT[backendStatus]

  return (
    <header className="z-50 flex h-16 shrink-0 items-center justify-between gap-3 border-b-2 border-pertamina-red bg-pertamina-navy px-4 text-white shadow-pertamina-md lg:px-6">
      <div className="flex min-w-0 items-center gap-4">
        <div className="flex items-center gap-2.5 text-base font-extrabold tracking-tight">
          <span className="relative inline-block h-7 w-7 shrink-0 rounded-md bg-[linear-gradient(135deg,#ED1C24_30%,#0072BC_30%_70%,#009A44_70%)] shadow-[0_2px_4px_rgba(0,0,0,0.2)]">
            <span
              className={`absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-pertamina-navy ${status.color}`}
              title={status.label}
              aria-label={status.label}
              role="img"
            />
          </span>
          <span className="hidden sm:inline">PERTAMINA</span>
        </div>
        <div className="hidden h-6 w-px bg-white/20 lg:block" />
        <span className="hidden text-[14.5px] font-bold lg:inline">Procurement AI Copilot</span>
      </div>

      <button
        type="button"
        onClick={openDocPicker}
        title="Klik untuk mengganti jenis dokumen"
        className="flex min-w-0 items-center gap-2.5 rounded-full border-[1.5px] border-white/25 bg-white/10 px-3 py-1.5 text-[12.5px] font-semibold transition hover:-translate-y-px hover:border-white/45 hover:bg-white/20 sm:px-4"
      >
        <span className="truncate">
          {meta.icon} <span className="hidden md:inline">{meta.title}</span>
        </span>
        <span className="shrink-0 rounded-full bg-pertamina-red px-2 py-0.5 text-[10.5px] font-bold tracking-wide">Ganti ▾</span>
      </button>

      <div className="flex shrink-0 items-center gap-2">
        <button
          type="button"
          onClick={() => toggleDrawer()}
          title="Buka Progres & Konteks Sesi"
          className="hidden items-center gap-2 rounded-full border border-white/30 bg-white/10 px-3.5 py-1.5 text-xs font-semibold transition hover:-translate-y-px hover:border-white/50 hover:bg-white/25 md:flex"
        >
          <span className="rounded-full bg-pertamina-blue px-2 py-0.5 text-[11px] font-bold">
            Step <strong>{step}</strong> of {meta.stepper.length}
          </span>
          <span className="hidden max-w-[130px] truncate font-medium text-white/90 xl:inline">{meta.stepper[step - 1]}</span>
          <span className="text-xs opacity-85">📊</span>
        </button>

        {mode !== 'kb' && canGenerate && (
          <button
            type="button"
            onClick={downloadDocx}
            disabled={isDownloading}
            title="Unduh Berkas Word (.DOCX) Resmi"
            className="flex items-center gap-2 rounded-lg bg-pertamina-red px-3 py-2 text-[12.5px] font-bold shadow-[0_2px_6px_rgba(237,28,36,0.3)] transition hover:-translate-y-px hover:bg-red-700 disabled:cursor-wait disabled:opacity-70 sm:px-[18px]"
          >
            {isDownloading ? '⏳' : '📥'}
            <span className="hidden sm:inline">{isDownloading ? 'Membuat...' : 'Unduh (.DOCX)'}</span>
          </button>
        )}

        <HamburgerMenu />
      </div>
    </header>
  )
}
