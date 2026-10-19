import { useCallback, useEffect, useRef, useState } from 'react'
import { MODE_META } from '../../services/modes'
import { ROLE_LABELS } from '../../services/permissions'
import { useAuthStore } from '../../services/useAuthStore'
import { useAppStore } from '../../services/useAppStore'
import useEscapeKey from '../Common/useEscapeKey'

const REGULASI = [
  'Pedoman PBJ No. A03-001/PNG200000/2024-S9 Rev. 1',
  'TKO No. B3.2.4-03/PNG200000/2024-S9 (Lampiran 3, 4, 5, 6)',
  'TKI No. C3.2.3-01/PNG200000/2024-S9 (Lampiran 3, 5)',
  'TKI Penentuan Besaran Denda No. C5-001/I30000/2021-S9',
]

function MenuItem({ icon, title, sub, right, danger, onClick }) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      className="flex w-full items-center justify-between rounded-md px-3 py-2 text-left transition hover:bg-pertamina-gray-100 focus-visible:bg-pertamina-gray-100 focus-visible:outline-none"
    >
      <span className="flex items-center gap-2.5">
        <span className="flex w-[22px] justify-center text-[15px]">{icon}</span>
        <span className="flex flex-col">
          <span className={`text-[12.5px] font-bold leading-tight ${danger ? 'text-red-500' : 'text-pertamina-gray-900'}`}>
            {title}
          </span>
          <span className="text-[10.5px] text-pertamina-gray-500">{sub}</span>
        </span>
      </span>
      {right}
    </button>
  )
}

function MenuHeader({ children }) {
  return (
    <div className="bg-pertamina-gray-50 px-3.5 pb-1.5 pt-2.5 text-[10.5px] font-extrabold uppercase tracking-wide text-pertamina-gray-500">
      {children}
    </div>
  )
}

export default function HamburgerMenu() {
  const [open, setOpen] = useState(false)
  const wrapperRef = useRef(null)
  const isCanvasVisible = useAppStore((s) => s.isCanvasVisible)
  const mode = useAppStore((s) => s.mode)
  const toggleCanvasVisible = useAppStore((s) => s.toggleCanvasVisible)
  const toggleDrawer = useAppStore((s) => s.toggleDrawer)
  const setMode = useAppStore((s) => s.setMode)
  const openDocPicker = useAppStore((s) => s.openDocPicker)
  const askConfirm = useAppStore((s) => s.askConfirm)
  const pushToast = useAppStore((s) => s.pushToast)
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  const close = useCallback(() => setOpen(false), [])
  useEscapeKey(close, open)

  useEffect(() => {
    if (!open) return
    const onPointerDown = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [open])

  const run = (action) => () => {
    setOpen(false)
    action()
  }

  const resetSession = () =>
    askConfirm({
      title: 'Reset sesi percakapan?',
      message: `Mulai sesi baru untuk ${MODE_META[mode].title}? Percakapan saat ini akan dibersihkan.`,
      confirmLabel: 'Reset Sesi',
      onConfirm: () => {
        setMode(mode)
        openDocPicker()
      },
    })

  const confirmLogout = () =>
    askConfirm({
      title: 'Keluar dari akun?',
      message: 'Percakapan dan draf yang belum diunduh pada sesi ini akan dibersihkan.',
      confirmLabel: 'Keluar',
      onConfirm: logout,
    })

  const showRegulasi = () => pushToast(`Dasar regulasi aktif: ${REGULASI.join(' · ')}`, 'info')

  return (
    <div className="relative" ref={wrapperRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Buka menu navigasi"
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex h-[38px] w-[38px] items-center justify-center rounded-lg border border-white/30 bg-white/10 text-white transition hover:-translate-y-px hover:border-white/50 hover:bg-white/25"
      >
        <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
        </svg>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-[calc(100%+10px)] z-[200] flex w-[285px] animate-dropdown-pop flex-col overflow-hidden rounded-lg border border-pertamina-gray-200 bg-white shadow-[0_12px_35px_rgba(0,26,61,0.22)]"
        >
          {user && (
            <div className="border-b border-pertamina-gray-200 px-3.5 py-3">
              <div className="truncate text-[12.5px] font-bold text-pertamina-gray-900">{user.nama_lengkap}</div>
              <div className="text-[10.5px] text-pertamina-gray-500">
                {user.username} · <span className="font-semibold text-pertamina-blue">{ROLE_LABELS[user.role] ?? user.role}</span>
              </div>
            </div>
          )}
          <MenuHeader>Kontrol Tampilan & Review</MenuHeader>
          <div className="p-1">
            <MenuItem
              icon="📄"
              title="Review Dokumen (Canvas)"
              sub={isCanvasVisible ? 'Sedang Terbuka (Split View)' : 'Tertutup (Fokus Chat)'}
              onClick={run(() => toggleCanvasVisible())}
              right={
                <span
                  className={`rounded-full px-1.5 py-0.5 text-[10px] font-extrabold ${
                    isCanvasVisible ? 'bg-emerald-100 text-emerald-800' : 'bg-pertamina-gray-100 text-pertamina-gray-500'
                  }`}
                >
                  {isCanvasVisible ? 'ON' : 'OFF'}
                </span>
              }
            />
            <MenuItem
              icon="📊"
              title="Panel Progres & Konteks"
              sub="Tahapan Alur & Berkas Sesi"
              onClick={run(() => toggleDrawer(true))}
              right={
                <span className="rounded-full bg-pertamina-blue-light px-1.5 py-0.5 text-[10px] font-bold text-pertamina-blue">
                  Drawer
                </span>
              }
            />
          </div>

          <div className="h-px bg-pertamina-gray-200" />
          <MenuHeader>Referensi & Manajemen</MenuHeader>
          <div className="p-1">
            <MenuItem icon="🗄️" title="Knowledge Base" sub="Qdrant Vector Database" onClick={run(() => setMode('kb'))} />
            <MenuItem icon="📖" title="Pedoman PBJ Pertamina" sub="No. A03-001/PNG200000/2024-S9" onClick={run(showRegulasi)} />
          </div>

          <div className="h-px bg-pertamina-gray-200" />
          <div className="p-1">
            <MenuItem
              icon="🔄"
              title="Reset Sesi Percakapan"
              sub="Bersihkan percakapan & mulai ulang"
              danger
              onClick={run(resetSession)}
            />
            <MenuItem icon="🚪" title="Keluar" sub="Akhiri sesi login" danger onClick={run(confirmLogout)} />
          </div>
        </div>
      )}
    </div>
  )
}
