import { useState } from 'react'
import RichText from '../Common/RichText'

// Accordion jejak eksekusi tool AI (RAG retrieval, legal drafting, dll.)
export function ToolCallCard({ title, lines }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mb-2 overflow-hidden rounded-md border border-pertamina-gray-200 bg-[#FAFCFE]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full select-none items-center justify-between bg-pertamina-gray-50 px-3 py-1.5 text-left text-[11.5px] font-semibold text-pertamina-gray-600 transition hover:bg-pertamina-gray-100 hover:text-pertamina-navy"
      >
        <span className="flex items-center gap-2">
          <span className="text-xs text-pertamina-blue">⚡</span>
          <span>
            <RichText text={title} />
          </span>
        </span>
        <span className={`text-[10px] text-pertamina-gray-500 transition-transform ${open ? 'rotate-90' : ''}`}>▶</span>
      </button>
      {open && (
        <ul className="list-disc border-t border-pertamina-gray-200 bg-white py-2.5 pl-8 pr-3.5 text-[11.5px] leading-relaxed text-pertamina-gray-500">
          {lines.map((line) => (
            <li key={line}>
              <RichText text={line} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// Kotak "AI Reasoning" yang bisa dilipat
export function ReasoningBox({ lines }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mb-2.5 mt-1.5 rounded-r-md border-l-[3px] border-blue-500 bg-pertamina-gray-50 px-3 py-2 text-[11.5px] text-pertamina-gray-500">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex items-center gap-1.5 font-semibold text-blue-600"
      >
        ⚡ AI Reasoning & RAG Retrieval {open ? '▴' : '▾'}
      </button>
      {open && (
        <ul className="mt-1.5 list-disc pl-4 text-[11px] leading-normal">
          {lines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
