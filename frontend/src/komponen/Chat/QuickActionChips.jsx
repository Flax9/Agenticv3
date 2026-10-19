import { QUICK_CHIPS } from '../../services/modes'
import { useAppStore } from '../../services/useAppStore'

export default function QuickActionChips() {
  const mode = useAppStore((s) => s.mode)
  const isBusy = useAppStore((s) => s.isBusy)
  const sendMessage = useAppStore((s) => s.sendMessage)

  return (
    <div className="flex shrink-0 gap-2 overflow-x-auto px-5 pb-1 pt-2.5 no-scrollbar">
      {QUICK_CHIPS[mode].map((chip) => (
        <button
          key={chip.prompt}
          type="button"
          disabled={isBusy}
          onClick={() => sendMessage(chip.prompt)}
          className="flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border border-pertamina-gray-300 bg-pertamina-gray-100 px-3.5 py-1.5 text-[11.5px] font-semibold text-pertamina-gray-900 transition hover:-translate-y-px hover:border-pertamina-gray-400 hover:bg-pertamina-gray-200 disabled:opacity-50"
        >
          {chip.text}
        </button>
      ))}
    </div>
  )
}
