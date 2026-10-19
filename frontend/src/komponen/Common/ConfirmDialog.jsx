import { useCallback } from 'react'
import { useAppStore } from '../../services/useAppStore'
import useEscapeKey from './useEscapeKey'

// Pengganti window.confirm(). Dibuka lewat useAppStore.getState().askConfirm({...})
export default function ConfirmDialog() {
  const confirm = useAppStore((s) => s.confirm)
  const closeConfirm = useAppStore((s) => s.closeConfirm)
  const close = useCallback(() => closeConfirm(), [closeConfirm])
  useEscapeKey(close, Boolean(confirm))

  if (!confirm) return null

  const handleConfirm = () => {
    closeConfirm()
    confirm.onConfirm()
  }

  return (
    <div
      className="fixed inset-0 z-[1050] flex animate-fade-in items-center justify-center bg-pertamina-navy-dark/60 p-6 backdrop-blur-sm"
      onClick={close}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        className="w-full max-w-sm animate-scale-in rounded-2xl border border-pertamina-gray-300 bg-white p-5 shadow-pertamina-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="confirm-title" className="text-[14.5px] font-extrabold text-pertamina-navy">
          {confirm.title}
        </h3>
        <p className="mt-2 text-[12.5px] leading-relaxed text-pertamina-gray-600">{confirm.message}</p>
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={close}
            className="rounded-md border border-pertamina-gray-300 bg-pertamina-gray-100 px-4 py-2 text-xs font-semibold text-pertamina-gray-700 hover:bg-pertamina-gray-200"
          >
            Batal
          </button>
          <button
            type="button"
            autoFocus
            onClick={handleConfirm}
            className="rounded-md bg-pertamina-red px-4 py-2 text-xs font-bold text-white hover:bg-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pertamina-red/40"
          >
            {confirm.confirmLabel ?? 'Ya, lanjutkan'}
          </button>
        </div>
      </div>
    </div>
  )
}
