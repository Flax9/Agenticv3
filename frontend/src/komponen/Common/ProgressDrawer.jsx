import { useCallback } from 'react'
import { MODE_META } from '../../services/modes'
import { useAppStore } from '../../services/useAppStore'
import useEscapeKey from './useEscapeKey'

const STAGE_STYLES = {
  completed: { item: 'border-emerald-100 bg-emerald-50/60', num: 'bg-emerald-500 text-white', desc: 'Selesai diverifikasi' },
  active: { item: 'border-pertamina-blue bg-[#F0F7FF]', num: 'bg-pertamina-blue text-white', desc: 'Sedang aktif diproses' },
  upcoming: { item: 'border-pertamina-gray-200 bg-white', num: 'bg-pertamina-gray-200 text-pertamina-gray-500', desc: 'Tahapan selanjutnya' },
}

function SectionHeader({ title, badge }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <span className="text-[11px] font-extrabold uppercase tracking-wider text-pertamina-gray-500">{title}</span>
      {badge && (
        <span className="rounded-full bg-pertamina-blue-light px-2 py-0.5 text-[11px] font-bold text-pertamina-blue">
          {badge}
        </span>
      )}
    </div>
  )
}

export default function ProgressDrawer() {
  const isOpen = useAppStore((s) => s.isDrawerOpen)
  const mode = useAppStore((s) => s.mode)
  const step = useAppStore((s) => s.step)
  const hasPackage = useAppStore((s) => Boolean(s.packages[s.mode]))
  const resources = useAppStore((s) => s.sessionResources)
  const toggleDrawer = useAppStore((s) => s.toggleDrawer)
  const showArtifactTab = useAppStore((s) => s.showArtifactTab)
  const close = useCallback(() => toggleDrawer(false), [toggleDrawer])
  useEscapeKey(close, isOpen)

  const meta = MODE_META[mode]
  const artifacts = mode === 'kb' || hasPackage ? meta.artifacts : []

  return (
    <>
      <div
        aria-hidden="true"
        onClick={close}
        className={`fixed inset-x-0 bottom-0 top-16 z-[99] bg-pertamina-navy-dark/35 backdrop-blur-[2px] transition-opacity duration-200 ${
          isOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
      />
      <aside
        aria-label="Progres & Konteks Sesi"
        aria-hidden={!isOpen}
        inert={!isOpen}
        className={`fixed bottom-0 top-16 z-[100] flex w-full max-w-[380px] flex-col border-l border-pertamina-gray-200 bg-white shadow-[-6px_0_24px_rgba(0,45,98,0.12)] transition-[right] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${
          isOpen ? 'right-0' : '-right-[420px]'
        }`}
      >
        <div className="flex items-center justify-between border-b border-pertamina-gray-200 bg-pertamina-gray-50 px-5 py-4">
          <div>
            <h3 className="mb-0.5 text-[14.5px] font-bold text-pertamina-navy">Progres & Konteks Sesi</h3>
            <span className="text-[11.5px] text-pertamina-gray-500">Pelacakan Tahapan Alur Kerja Dokumen</span>
          </div>
          <button
            type="button"
            onClick={close}
            aria-label="Tutup panel progres"
            className="flex h-[30px] w-[30px] items-center justify-center rounded-md border border-pertamina-gray-200 bg-white text-sm text-pertamina-gray-500 hover:bg-pertamina-gray-100 hover:text-pertamina-gray-900"
          >
            ✕
          </button>
        </div>

        <div className="flex flex-1 flex-col gap-6 overflow-y-auto p-5">
          <section>
            <SectionHeader title="Progress Tahapan" badge={`Tahap ${step} dari ${meta.stepper.length}`} />
            <ol className="flex flex-col gap-2.5">
              {meta.stepper.map((label, idx) => {
                const num = idx + 1
                const status = num < step ? 'completed' : num === step ? 'active' : 'upcoming'
                const style = STAGE_STYLES[status]
                return (
                  <li key={label} className={`flex items-start gap-3 rounded-lg border px-3 py-2.5 ${style.item}`}>
                    <span
                      className={`mt-0.5 flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${style.num}`}
                    >
                      {status === 'completed' ? '✓' : num}
                    </span>
                    <span className="flex flex-col">
                      <span className="text-[12.5px] font-bold leading-tight text-pertamina-gray-900">{label}</span>
                      <span className="mt-0.5 text-[11px] text-pertamina-gray-500">{style.desc}</span>
                    </span>
                  </li>
                )
              })}
            </ol>
          </section>

          <section>
            <SectionHeader title="Output Dokumen" badge={`${artifacts.length} Berkas Siap`} />
            {artifacts.length === 0 ? (
              <p className="rounded-md border border-dashed border-pertamina-gray-300 px-3 py-3 text-[11.5px] text-pertamina-gray-500">
                Belum ada output. Unggah berkas acuan atau muat data contoh.
              </p>
            ) : (
              <div className="flex flex-col gap-2.5">
                {artifacts.map((art) => (
                  <button
                    key={art.tab}
                    type="button"
                    onClick={() => showArtifactTab(art.tab)}
                    className="flex items-center justify-between gap-2.5 rounded-lg border border-pertamina-gray-200 bg-white p-3 text-left shadow-sm transition hover:-translate-y-px hover:border-pertamina-blue hover:shadow-[0_4px_12px_rgba(0,114,206,0.12)]"
                  >
                    <span className="flex items-center gap-2.5">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-blue-50 text-base">📄</span>
                      <span className="flex flex-col">
                        <span className="text-xs font-bold leading-tight text-pertamina-navy">{art.title}</span>
                        <span className="text-[10.5px] text-pertamina-gray-500">
                          {art.desc} · <strong className="text-pertamina-blue">{art.format}</strong>
                        </span>
                      </span>
                    </span>
                    <span className="whitespace-nowrap text-[11px] font-bold text-pertamina-blue">Lihat ↗</span>
                  </button>
                ))}
              </div>
            )}
          </section>

          <section>
            <SectionHeader title="Sumber Data Sesi Ini" />
            {resources.length === 0 ? (
              <p className="text-[11.5px] text-pertamina-gray-500">Belum ada berkas atau sumber data yang dipakai.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {resources.map((res) => (
                  <li
                    key={res.name}
                    className="flex items-center gap-2.5 rounded-md border border-pertamina-gray-200 bg-pertamina-gray-50 px-3 py-2 text-xs"
                  >
                    <span className="text-sm">{res.icon}</span>
                    <span className="flex min-w-0 flex-col">
                      <span className="truncate font-semibold text-pertamina-gray-900" title={res.name}>
                        {res.name}
                      </span>
                      <span className="text-[10.5px] text-pertamina-gray-500">{res.meta}</span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </aside>
    </>
  )
}
