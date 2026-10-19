import { useEffect, useRef } from 'react'
import { MODE_META } from '../../services/modes'
import { can } from '../../services/permissions'
import { useAuthStore } from '../../services/useAuthStore'
import { useAppStore } from '../../services/useAppStore'
import ChatBubble from './ChatBubble'
import ChatInput from './ChatInput'
import QuickActionChips from './QuickActionChips'
import WorkflowStepper from './WorkflowStepper'

function WelcomeMessage({ onUpload }) {
  const mode = useAppStore((s) => s.mode)
  const isBusy = useAppStore((s) => s.isBusy)
  const loadDemo = useAppStore((s) => s.loadDemo)
  const canDraft = useAuthStore((s) => can(s.user, 'draft'))
  const meta = MODE_META[mode]

  return (
    <ChatBubble message={{ sender: 'ai' }}>
      <p>
        Halo! Saya siap membantu Anda menyusun <strong>{meta.title}</strong> ({meta.badge}) sesuai Pedoman Pengadaan PT
        Pertamina Patra Niaga No. <code>A03-001/PNG200000/2024-S9</code>.
      </p>
      {mode !== 'kb' && !canDraft && (
        <p className="mt-2.5 rounded-md border border-pertamina-gray-200 bg-pertamina-gray-50 px-3 py-2 text-xs text-pertamina-gray-600">
          Peran Anda bersifat <strong>tinjau saja</strong>: Anda dapat melihat dokumen, tetapi tidak dapat mengunggah berkas atau
          merevisi draf.
        </p>
      )}
      {mode !== 'kb' && canDraft && (
        <div className="mt-2.5 rounded-lg border-2 border-dashed border-blue-300 bg-pertamina-gray-50 p-5 text-center transition hover:border-pertamina-blue hover:bg-blue-50">
          <div className="mb-2 text-[32px]">📁</div>
          <div className="mb-1 text-[13.5px] font-bold text-pertamina-navy">Mulai Sesi Penyusunan Dokumen</div>
          <div className="mb-3.5 text-[11.5px] text-pertamina-gray-500">
            Unggah berkas acuan (BoQ / RKS, PDF atau Excel) untuk ekstraksi parameter otomatis, atau gunakan data contoh
            untuk demonstrasi.
          </div>
          <div className="flex flex-wrap justify-center gap-2.5">
            <button
              type="button"
              onClick={onUpload}
              disabled={isBusy}
              className="flex items-center gap-1.5 rounded-md bg-pertamina-blue px-4 py-1.5 text-xs font-semibold text-white transition hover:bg-[#005FA8] disabled:opacity-50"
            >
              ☁️ Unggah Berkas PDF/Excel
            </button>
            <button
              type="button"
              onClick={loadDemo}
              disabled={isBusy}
              className="flex items-center gap-1.5 rounded-md border border-pertamina-gray-300 bg-white px-4 py-1.5 text-xs font-semibold text-pertamina-navy transition hover:border-pertamina-gray-400 hover:bg-pertamina-gray-100 disabled:opacity-50"
            >
              ✨ Muat Data Contoh (Demo)
            </button>
          </div>
        </div>
      )}
    </ChatBubble>
  )
}

export default function ChatPanel({ className = '' }) {
  const messages = useAppStore((s) => s.messages)
  const isBusy = useAppStore((s) => s.isBusy)
  const canDraft = useAuthStore((s) => can(s.user, 'draft'))
  const streamRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    const el = streamRef.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages, isBusy])

  return (
    <section aria-label="AI Copilot Chat" className={`flex h-full flex-col overflow-hidden bg-white ${className}`}>
      <WorkflowStepper />

      <div ref={streamRef} className="flex flex-1 flex-col gap-[18px] overflow-y-auto p-5" aria-live="polite">
        <WelcomeMessage onUpload={() => fileInputRef.current?.click()} />
        {messages.map((m) => (
          <ChatBubble key={m.id} message={m} />
        ))}
        {isBusy && !messages.some((m) => m.pending) && (
          <div className="flex items-center gap-1 pl-12 text-pertamina-gray-400" aria-label="AI sedang mengetik">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.3s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.15s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current" />
          </div>
        )}
      </div>

      {canDraft && (
        <>
          <QuickActionChips />
          <ChatInput fileInputRef={fileInputRef} />
        </>
      )}
    </section>
  )
}
