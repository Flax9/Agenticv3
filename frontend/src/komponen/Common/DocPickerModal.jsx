import { useCallback } from 'react'
import { DOC_CHOICES } from '../../services/modes'
import { useAppStore } from '../../services/useAppStore'
import useEscapeKey from './useEscapeKey'

export default function DocPickerModal() {
  const isOpen = useAppStore((s) => s.isDocPickerOpen)
  const mode = useAppStore((s) => s.mode)
  const closeDocPicker = useAppStore((s) => s.closeDocPicker)
  const selectDocument = useAppStore((s) => s.selectDocument)
  const close = useCallback(() => closeDocPicker(), [closeDocPicker])
  useEscapeKey(close, isOpen)

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-[1000] flex animate-fade-in items-center justify-center bg-pertamina-navy-dark/65 p-4 backdrop-blur-md sm:p-6"
      onClick={close}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="doc-picker-title"
        className="max-h-full w-full max-w-[680px] animate-scale-in overflow-y-auto rounded-2xl border-[1.5px] border-pertamina-gray-300 bg-white shadow-[0_24px_48px_rgba(0,26,61,0.3)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between bg-gradient-to-br from-pertamina-navy to-pertamina-navy-dark px-5 py-4 text-white">
          <div className="flex flex-col">
            <h3 id="doc-picker-title" className="text-[14.5px] font-extrabold tracking-tight">
              Pilih Jenis Dokumen Pengadaan
            </h3>
            <span className="mt-0.5 text-[11px] text-blue-300">Pedoman PBJ No. A03-001/PNG200000/2024-S9</span>
          </div>
          <button
            type="button"
            onClick={close}
            aria-label="Tutup pilihan dokumen"
            className="flex h-7 w-7 items-center justify-center rounded-full bg-white/15 text-sm font-bold hover:bg-white/30"
          >
            ✕
          </button>
        </div>

        <div className="bg-pertamina-gray-50 px-5 pb-5 pt-4">
          <p className="mb-3.5 text-xs leading-snug text-pertamina-gray-500">
            Silakan pilih paket dokumen yang ingin Anda susun. Sistem AI akan memuat alur kerja dan format klausul
            hukum yang sesuai:
          </p>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {DOC_CHOICES.map((choice) => {
              const selected = choice.mode === mode
              return (
                <button
                  key={choice.mode}
                  type="button"
                  onClick={() => selectDocument(choice.mode)}
                  aria-pressed={selected}
                  className={`flex min-h-[145px] flex-col gap-2.5 rounded-2xl border-[1.5px] p-4 text-left transition duration-200 hover:-translate-y-0.5 hover:border-pertamina-blue hover:bg-[#F0F7FF] hover:shadow-[0_10px_22px_rgba(0,114,206,0.16)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pertamina-blue ${
                    selected
                      ? 'border-pertamina-navy bg-pertamina-blue-light ring-2 ring-pertamina-navy'
                      : 'border-pertamina-gray-200 bg-white'
                  }`}
                >
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-xl shadow-sm">
                    {choice.icon}
                  </span>
                  <span className="text-[13.5px] font-extrabold leading-tight text-pertamina-navy">{choice.title}</span>
                  <span className="text-[11.5px] leading-snug text-pertamina-gray-500">{choice.desc}</span>
                  <span className="mt-auto self-start rounded-md bg-pertamina-gray-100 px-1.5 py-0.5 text-[9.5px] font-bold uppercase tracking-wide text-pertamina-gray-500">
                    {choice.tag}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
