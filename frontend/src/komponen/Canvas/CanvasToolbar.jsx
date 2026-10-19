import { useEffect, useState } from 'react'
import { MODE_META } from '../../services/modes'
import { useAppStore } from '../../services/useAppStore'

function IconButton({ label, onClick, children, variant = 'outline' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className={`flex h-[30px] w-[30px] items-center justify-center rounded-md text-[13px] transition ${
        variant === 'outline'
          ? 'border border-pertamina-gray-200 bg-white text-pertamina-gray-600 hover:border-pertamina-gray-300 hover:bg-pertamina-gray-50 hover:text-pertamina-navy active:bg-blue-50'
          : 'border border-transparent text-pertamina-gray-500 hover:border-pertamina-gray-200 hover:bg-pertamina-gray-100 hover:text-pertamina-gray-900'
      }`}
    >
      {children}
    </button>
  )
}

export default function CanvasToolbar({ onCopy }) {
  const mode = useAppStore((s) => s.mode)
  const activeTab = useAppStore((s) => s.activeTab)
  const isFullscreen = useAppStore((s) => s.isCanvasFullscreen)
  const setActiveTab = useAppStore((s) => s.setActiveTab)
  const toggleCanvasFullscreen = useAppStore((s) => s.toggleCanvasFullscreen)
  const toggleCanvasVisible = useAppStore((s) => s.toggleCanvasVisible)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!copied) return
    const timer = setTimeout(() => setCopied(false), 1800)
    return () => clearTimeout(timer)
  }, [copied])

  const meta = MODE_META[mode]
  const tabs =
    mode === 'kb'
      ? [{ id: 'previewTab', label: '🗄️ Collections' }]
      : [
          { id: 'previewTab', label: '📄 Dokumen' },
          { id: 'matrixTab', label: meta.matrixLabel },
          { id: 'checklistTab', label: '✅ STK (86)' },
        ]

  const handleCopy = async () => {
    if (await onCopy()) setCopied(true)
  }

  return (
    <div className="z-10 flex min-h-[50px] shrink-0 flex-wrap items-center justify-between gap-2.5 border-b border-pertamina-gray-200 bg-white px-4 py-2 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
      <div className="flex min-w-0 shrink items-center gap-2">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-[#D0E1F4] bg-pertamina-blue-light text-sm">
          {meta.icon}
        </span>
        <span className="flex min-w-0 flex-col">
          <span className="max-w-[160px] truncate text-[12.5px] font-bold leading-tight text-pertamina-navy">{meta.title}</span>
          <span className="flex items-center gap-1 whitespace-nowrap text-[10px] text-pertamina-gray-500">
            <span className="inline-block h-1.5 w-1.5 animate-pulse-dot rounded-full bg-emerald-500" /> Live Bi-directional Sync
          </span>
        </span>
      </div>

      <div role="tablist" aria-label="Tampilan canvas" className="flex shrink-0 gap-0.5 rounded-lg border border-pertamina-gray-200 bg-pertamina-gray-100 p-0.5">
        {tabs.map((tab) => {
          const active = activeTab === tab.id
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setActiveTab(tab.id)}
              className={`whitespace-nowrap rounded-md px-2.5 py-1 text-[11px] transition ${
                active
                  ? 'bg-white font-bold text-pertamina-navy shadow-sm'
                  : 'font-semibold text-pertamina-gray-500 hover:bg-white/60 hover:text-pertamina-gray-900'
              }`}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      <div className="flex shrink-0 items-center gap-1">
        <IconButton label={copied ? 'Tersalin' : 'Salin isi naskah ke clipboard'} onClick={handleCopy}>
          {copied ? <span className="text-emerald-500">✓</span> : '📋'}
        </IconButton>
        <IconButton label={isFullscreen ? 'Keluar layar penuh' : 'Layar penuh'} onClick={toggleCanvasFullscreen}>
          {isFullscreen ? '🗗' : '⛶'}
        </IconButton>
        <IconButton label="Tutup review dokumen" onClick={() => toggleCanvasVisible(false)} variant="ghost">
          ✕
        </IconButton>
      </div>
    </div>
  )
}
