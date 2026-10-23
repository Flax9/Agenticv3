import { useRef, useState } from 'react'
import { useAppStore } from '../../services/useAppStore'

// Berkas acuan dipilih dari folder drive: BoQ saat agent RKS memintanya, atau BoQ/RKS untuk ekstraksi Tender
function attachPurpose(mode, awaiting) {
  if (mode === 'rks' && awaiting === 'upload_boq') return 'agent_boq'
  if (mode === 'tender') return 'extract'
  return null
}

export default function ChatInput() {
  const [text, setText] = useState('')
  const mode = useAppStore((s) => s.mode)
  const awaiting = useAppStore((s) => s.awaiting)
  const isBusy = useAppStore((s) => s.isBusy)
  const sendMessage = useAppStore((s) => s.sendMessage)
  const openDatasetPicker = useAppStore((s) => s.openDatasetPicker)
  const textareaRef = useRef(null)
  const purpose = attachPurpose(mode, awaiting)
  // Hanya RKS yang punya agent percakapan; mode lain bekerja lewat kanvas dan berkas dari drive
  const chatEnabled = mode === 'rks'

  // Satu handler untuk tombol Kirim maupun tombol Enter
  const handleSubmit = (e) => {
    e?.preventDefault()
    if (!chatEnabled || !text.trim() || isBusy) return
    sendMessage(text)
    setText('')
    textareaRef.current?.focus()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) handleSubmit(e)
  }

  const placeholder = !chatEnabled
    ? 'Chat belum tersedia untuk jenis dokumen ini. Isi parameter di kanvas atau pilih berkas dari drive (📎).'
    : awaiting === 'review_rks'
      ? 'Ketik "setuju" untuk ekspor, atau tulis bagian yang perlu direvisi...'
      : awaiting === 'upload_boq'
        ? 'Pilih BoQ dari drive (📎) atau ketik "lewati"...'
        : 'Ketik pertanyaan atau ceritakan dokumen yang ingin dibuat...'

  return (
    <form onSubmit={handleSubmit} className="flex shrink-0 flex-col gap-2 border-t border-pertamina-gray-200 bg-white px-5 py-3.5">
      <div className="flex items-end rounded-lg border-[1.5px] border-pertamina-gray-200 bg-pertamina-gray-50 px-2.5 py-1.5 transition focus-within:border-pertamina-blue focus-within:bg-white focus-within:ring-[3px] focus-within:ring-pertamina-blue/15">
        <button
          type="button"
          onClick={() => openDatasetPicker(purpose)}
          disabled={isBusy || !purpose}
          aria-label="Pilih berkas acuan dari drive"
          title={purpose ? 'Pilih berkas acuan dari folder drive' : 'Lampiran berkas tersedia saat Copilot memintanya'}
          className="mb-0.5 flex items-center justify-center rounded-md px-2 py-1.5 text-pertamina-gray-500 transition hover:bg-pertamina-gray-200 hover:text-pertamina-navy disabled:opacity-40 disabled:hover:bg-transparent"
        >
          <svg className="h-[15px] w-[15px] fill-current" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5a2.5 2.5 0 0 1 5 0v10.5c0 .83-.67 1.5-1.5 1.5s-1.5-.67-1.5-1.5V6H9v9.5a3 3 0 0 0 6 0V5a4 4 0 0 0-8 0v12.5c0 3.04 2.46 5.5 5.5 5.5s5.5-2.46 5.5-5.5V6h-1.5z" />
          </svg>
        </button>

        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          disabled={!chatEnabled}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          aria-label="Pesan untuk AI Copilot"
          className="max-h-32 min-h-[36px] flex-1 resize-none bg-transparent px-2 py-2 text-[13.5px] text-pertamina-gray-900 outline-none [field-sizing:content] disabled:cursor-not-allowed disabled:text-pertamina-gray-500"
        />

        <button
          type="submit"
          disabled={!chatEnabled || !text.trim() || isBusy}
          aria-label="Kirim pesan"
          title="Kirim Pesan"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-pertamina-navy text-white transition hover:scale-105 hover:bg-pertamina-navy-light disabled:scale-100 disabled:opacity-40"
        >
          <svg className="h-[15px] w-[15px] fill-current" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-x-3 px-1 text-[10.5px] text-pertamina-gray-400">
        <span>
          <strong>Enter</strong> untuk kirim · <strong>Shift+Enter</strong> baris baru
        </span>
        <span>Jawaban AI dapat keliru. Periksa kembali nilai penting sebelum dipakai.</span>
      </div>
    </form>
  )
}
