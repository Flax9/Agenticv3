import { useCallback, useEffect, useRef, useState } from 'react'
import { TIPE_TO_MODE, listChatSessions } from '../../services/api'
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
  const openSession = useAppStore((s) => s.openSession)
  const activeSessionId = useAppStore((s) => s.session?.id)
  const user = useAuthStore((s) => s.user)
  // Riwayat sesi dimuat setiap kali menu dibuka: null = sedang memuat
  const [history, setHistory] = useState(null)
  const logout = useAuthStore((s) => s.logout)

  const close = useCallback(() => setOpen(false), [])
  useEscapeKey(close, open)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    listChatSessions(5)
      .then((rows) => !cancelled && setHistory(rows))
      .catch(() => !cancelled && setHistory([]))
    return () => {
      cancelled = true
      setHistory(null)
    }
  }, [open])

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
      title: 'Mulai sesi baru?',
      message: `Mulai sesi baru untuk ${MODE_META[mode].title}? Sesi saat ini tetap tersimpan di Riwayat Sesi.`,
      confirmLabel: 'Sesi Baru',
      onConfirm: () => {
        setMode(mode)
        openDocPicker()
      },
    })

  const confirmLogout = () =>
    askConfirm({
      title: 'Keluar dari akun?',
      message: 'Percakapan dan draf tetap tersimpan dan bisa dibuka lagi dari Riwayat Sesi.',
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
          <MenuHeader>Riwayat Sesi</MenuHeader>
          <div className="max-h-[210px] overflow-y-auto p-1">
            {history === null && <p className="px-3 py-2 text-[11px] text-pertamina-gray-500">Memuat...</p>}
            {history?.length === 0 && <p className="px-3 py-2 text-[11px] text-pertamina-gray-500">Belum ada sesi tersimpan.</p>}
            {history?.map((h) => {
              const meta = MODE_META[TIPE_TO_MODE[h.tipe_dokumen]]
              return (
                <MenuItem
                  key={h.id}
                  icon={meta?.icon ?? '💬'}
                  title={h.nama_pengadaan}
                  sub={new Date(h.created_at).toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' })}
                  onClick={run(() => openSession(h.id))}
                  right={
                    h.id === activeSessionId && (
                      <span className="rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-extrabold text-emerald-800">AKTIF</span>
                    )
                  }
                />
              )
            })}
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
              title="Mulai Sesi Baru"
              sub="Sesi lama tetap ada di riwayat"
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
