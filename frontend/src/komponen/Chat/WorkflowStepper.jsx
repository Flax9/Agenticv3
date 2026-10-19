import { Fragment } from 'react'
import { MODE_META } from '../../services/modes'
import { useAppStore } from '../../services/useAppStore'

export default function WorkflowStepper() {
  const mode = useAppStore((s) => s.mode)
  const step = useAppStore((s) => s.step)
  const steps = MODE_META[mode].stepper

  return (
    <ol className="flex shrink-0 items-center justify-between gap-2 overflow-x-auto border-b border-pertamina-gray-200 bg-pertamina-gray-50 px-5 py-3 no-scrollbar">
      {steps.map((label, idx) => {
        const num = idx + 1
        const done = num < step
        const active = num === step
        return (
          <Fragment key={label}>
            <li
              aria-current={active ? 'step' : undefined}
              className={`flex shrink-0 items-center gap-1.5 text-[11px] font-semibold ${
                done ? 'text-emerald-500' : active ? 'font-bold text-pertamina-navy' : 'text-pertamina-gray-500'
              }`}
            >
              <span
                className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
                  done
                    ? 'bg-emerald-100 text-emerald-500'
                    : active
                      ? 'bg-pertamina-navy text-white'
                      : 'bg-pertamina-gray-200 text-pertamina-gray-500'
                }`}
              >
                {done ? '✓' : num}
              </span>
              <span className={active ? '' : 'hidden sm:inline'}>{label}</span>
            </li>
            {idx < steps.length - 1 && (
              <li aria-hidden="true" className={`h-0.5 min-w-3 flex-1 ${done ? 'bg-emerald-500' : 'bg-pertamina-gray-200'}`} />
            )}
          </Fragment>
        )
      })}
    </ol>
  )
}
