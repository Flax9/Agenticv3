import { useRef } from 'react'
import { MODE_META } from '../../services/modes'
import { useAppStore } from '../../services/useAppStore'
import CanvasToolbar from './CanvasToolbar'
import DocumentEditor from './DocumentEditor'
import KnowledgeBaseView from './KnowledgeBaseView'
import MatrixView from './MatrixView'
import RksDraftView from './RksDraftView'
import StkComplianceView from './StkComplianceView'

function EmptyCanvas({ mode }) {
  return (
    <div className="flex min-h-[420px] flex-col items-center justify-center rounded-lg border-2 border-dashed border-pertamina-gray-300 bg-white/60 p-8 text-center">
      <div className="mb-3 text-4xl opacity-70">{MODE_META[mode].icon}</div>
      <div className="mb-1 text-sm font-bold text-pertamina-navy">Draf belum tersedia</div>
      <p className="max-w-sm text-xs text-pertamina-gray-500">
        Mulai percakapan atau pilih berkas acuan dari drive di panel chat. Setelah draf tersusun, naskah{' '}
        {MODE_META[mode].title} akan tampil di sini.
      </p>
    </div>
  )
}

export default function CanvasReview({ className = '' }) {
  const mode = useAppStore((s) => s.mode)
  const activeTab = useAppStore((s) => s.activeTab)
  const data = useAppStore((s) => s.packages[s.mode])
  const agentDraft = useAppStore((s) => (s.mode === 'rks' ? s.draft : null))
  const pushToast = useAppStore((s) => s.pushToast)
  const bodyRef = useRef(null)

  const copyContent = async () => {
    const text = bodyRef.current?.innerText?.trim()
    if (!text) return false
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      pushToast('Browser menolak akses clipboard. Salin teks secara manual.', 'error')
      return false
    }
  }

  let content
  if (mode === 'kb') content = <KnowledgeBaseView />
  else if (activeTab === 'checklistTab') content = <StkComplianceView />
  else if (agentDraft && activeTab === 'previewTab') content = <RksDraftView draft={agentDraft} />
  else if (!data) content = <EmptyCanvas mode={mode} />
  else if (activeTab === 'matrixTab') content = <MatrixView mode={mode} data={data} />
  else content = <DocumentEditor mode={mode} data={data} />

  return (
    <section aria-label="Live Canvas Review Dokumen" className={`flex h-full flex-col overflow-hidden bg-pertamina-gray-200 ${className}`}>
      <CanvasToolbar onCopy={copyContent} />
      <div className="flex flex-1 justify-center overflow-y-auto p-3 sm:p-6">
        <div ref={bodyRef} key={`${mode}-${activeTab}`} className="w-full max-w-[860px] animate-fade-in">
          {content}
        </div>
      </div>
    </section>
  )
}
