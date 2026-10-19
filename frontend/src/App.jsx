import { useEffect } from 'react'
import {
  CanvasReview,
  ChatPanel,
  ConfirmDialog,
  DocPickerModal,
  Navbar,
  ProgressDrawer,
  ToastStack,
  VerticalRestoreTab,
} from './komponen'
import { checkHealth } from './services/api'
import { useAppStore } from './services/useAppStore'

const HEALTH_INTERVAL_MS = 30000

function useBackendHealth() {
  const setBackendStatus = useAppStore((s) => s.setBackendStatus)
  useEffect(() => {
    let cancelled = false
    const probe = async () => {
      const health = await checkHealth()
      if (!cancelled) setBackendStatus(health ? 'online' : 'offline')
    }
    probe()
    const timer = setInterval(probe, HEALTH_INTERVAL_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [setBackendStatus])
}

export default function App() {
  const isCanvasVisible = useAppStore((s) => s.isCanvasVisible)
  const isCanvasFullscreen = useAppStore((s) => s.isCanvasFullscreen)
  useBackendHealth()

  const chatHidden = isCanvasVisible && isCanvasFullscreen

  // ≥1280px: split-view berdampingan. <1280px: canvas tampil sebagai overlay di atas chat.
  const canvasClass = isCanvasFullscreen
    ? 'absolute inset-0 z-20 w-full'
    : 'absolute inset-y-0 right-0 z-20 w-full shadow-[-8px_0_30px_rgba(0,45,98,0.18)] md:w-[85%] xl:static xl:z-auto xl:w-[56%] xl:shadow-none'

  const chatClass = isCanvasVisible
    ? 'w-full xl:w-[44%] xl:min-w-[480px] xl:border-r xl:border-pertamina-gray-200'
    : 'w-full [&>*]:mx-auto [&>*]:w-full [&>*]:max-w-[1100px]'

  return (
    <div className="flex h-full flex-col">
      <Navbar />
      <main className="relative flex flex-1 overflow-hidden">
        {!chatHidden && <ChatPanel className={chatClass} />}
        {isCanvasVisible && <CanvasReview className={canvasClass} />}
      </main>

      <VerticalRestoreTab />
      <ProgressDrawer />
      <DocPickerModal />
      <ConfirmDialog />
      <ToastStack />
    </div>
  )
}
