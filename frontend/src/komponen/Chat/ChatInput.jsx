import { useRef, useState } from 'react'
import { ACCEPTED_UPLOAD_EXT, validateUpload } from '../../services/upload'
import { useAppStore } from '../../services/useAppStore'

export default function ChatInput({ fileInputRef }) {
  const [text, setText] = useState('')
  const isBusy = useAppStore((s) => s.isBusy)
  const sendMessage = useAppStore((s) => s.sendMessage)
  const uploadReference = useAppStore((s) => s.uploadReference)
  const pushToast = useAppStore((s) => s.pushToast)
  const textareaRef = useRef(null)

  // Satu handler untuk tombol Kirim maupun tombol Enter
  const handleSubmit = (e) => {
    e?.preventDefault()
    if (!text.trim() || isBusy) return
    sendMessage(text)
    setText('')
    textareaRef.current?.focus()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) handleSubmit(e)
  }

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    e.target.value = '' // izinkan memilih berkas yang sama lagi
    if (!file) return
    const error = validateUpload(file)
    if (error) return pushToast(error, 'error')
    uploadReference(file)
  }

  return (
    <form onSubmit={handleSubmit} className="flex shrink-0 flex-col gap-2 border-t border-pertamina-gray-200 bg-white px-5 py-3.5">
      <input ref={fileInputRef} type="file" hidden accept={ACCEPTED_UPLOAD_EXT.join(',')} onChange={handleFileChange} />

      <div className="flex items-end rounded-lg border-[1.5px] border-pertamina-gray-200 bg-pertamina-gray-50 px-2.5 py-1.5 transition focus-within:border-pertamina-blue focus-within:bg-white focus-within:ring-[3px] focus-within:ring-pertamina-blue/15">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isBusy}
          aria-label="Unggah berkas BoQ / RKS"
          title="Unggah berkas BoQ / RKS (PDF atau Excel)"
          className="mb-0.5 flex items-center justify-center rounded-md px-2 py-1.5 text-pertamina-gray-500 transition hover:bg-pertamina-gray-200 hover:text-pertamina-navy disabled:opacity-50"
        >
          <svg className="h-[15px] w-[15px] fill-current" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5a2.5 2.5 0 0 1 5 0v10.5c0 .83-.67 1.5-1.5 1.5s-1.5-.67-1.5-1.5V6H9v9.5a3 3 0 0 0 6 0V5a4 4 0 0 0-8 0v12.5c0 3.04 2.46 5.5 5.5 5.5s5.5-2.46 5.5-5.5V6h-1.5z" />
          </svg>
        </button>

        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ketik instruksi revisi klausul atau pertanyaan..."
          aria-label="Pesan untuk AI Copilot"
          className="max-h-32 min-h-[36px] flex-1 resize-none bg-transparent px-2 py-2 text-[13.5px] text-pertamina-gray-900 outline-none [field-sizing:content]"
        />

        <button
          type="submit"
          disabled={!text.trim() || isBusy}
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
        <span>Balasan chat masih simulasi (endpoint chat: Fase 4)</span>
      </div>
    </form>
  )
}
