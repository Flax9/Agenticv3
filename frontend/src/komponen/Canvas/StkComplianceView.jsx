import { DEMO_STK_ITEMS, DEMO_STK_SUMMARY } from '../../demo/demoData'

const TAG = {
  done: { label: 'Covered', tag: 'bg-emerald-100 text-emerald-800', result: 'OK', resultTone: 'text-emerald-600' },
  partial: { label: 'Parsial', tag: 'bg-amber-100 text-amber-800', result: 'Review', resultTone: 'text-amber-600' },
  pending: { label: 'Hulu', tag: 'bg-pertamina-gray-100 text-pertamina-gray-600', result: 'Manual', resultTone: 'text-pertamina-gray-500' },
}

const pct = (n) => `${((n / DEMO_STK_SUMMARY.total) * 100).toFixed(1)}%`

// Checklist kepatuhan 86 butir STK. Sementara memakai data contoh sampai
// katalog procurement_stk_rule tersedia dari backend (masterplan Fase 2).
export default function StkComplianceView() {
  const score = [
    { icon: '✓', badge: 'bg-emerald-50 text-emerald-600', tone: 'text-emerald-600', count: DEMO_STK_SUMMARY.done, sub: 'Sudah Dicover Sistem' },
    { icon: '!', badge: 'bg-amber-50 text-amber-600', tone: 'text-amber-600', count: DEMO_STK_SUMMARY.partial, sub: 'Parsial / Perlu Konfirmasi' },
    { icon: '○', badge: 'bg-pertamina-gray-100 text-pertamina-gray-500', tone: 'text-pertamina-gray-500', count: DEMO_STK_SUMMARY.pending, sub: 'Administrasi Hulu / SAP' },
  ]

  return (
    <div>
      <p className="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-[11.5px] text-amber-800">
        Data contoh — skor nyata akan dihitung dari katalog 86 aturan STK setelah database tersedia.
      </p>

      <div className="mb-5 grid grid-cols-1 gap-3.5 sm:grid-cols-3">
        {score.map((s) => (
          <div key={s.sub} className="flex items-center gap-3 rounded-lg border border-pertamina-gray-200 bg-white p-3.5 shadow-sm">
            <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-lg ${s.badge}`}>{s.icon}</span>
            <span className="flex flex-col">
              <span className={`text-lg font-extrabold leading-tight ${s.tone}`}>
                {s.count} Butir ({pct(s.count)})
              </span>
              <span className="text-[11px] font-semibold text-pertamina-gray-500">{s.sub}</span>
            </span>
          </div>
        ))}
      </div>

      <ul>
        {DEMO_STK_ITEMS.map((item) => {
          const t = TAG[item.status]
          return (
            <li
              key={item.title}
              className="mb-2 flex items-center justify-between gap-3 rounded-md border border-pertamina-gray-200 bg-white px-4 py-3 text-[12.5px] transition hover:border-pertamina-gray-400"
            >
              <div className="flex items-center gap-3">
                <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${t.tag}`}>{t.label}</span>
                <div>
                  <strong>{item.title}</strong>
                  <div className="text-[11px] text-pertamina-gray-500">{item.note}</div>
                </div>
              </div>
              <span className={`shrink-0 font-bold ${t.resultTone}`}>{t.result}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
