import { useState } from 'react'
import { useAuthStore } from '../../services/useAuthStore'

export default function LoginPage() {
  const login = useAuthStore((s) => s.login)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username.trim() || !password || submitting) return
    setSubmitting(true)
    setError(null)
    try {
      await login(username.trim(), password)
    } catch (err) {
      setError(err.message)
      setPassword('')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex h-full items-center justify-center overflow-y-auto bg-gradient-to-br from-pertamina-navy via-pertamina-navy-dark to-pertamina-gray-900 p-4">
      <div className="w-full max-w-sm animate-scale-in overflow-hidden rounded-2xl bg-white shadow-[0_24px_48px_rgba(0,26,61,0.35)]">
        <div className="border-b-2 border-pertamina-red bg-pertamina-navy px-6 py-5 text-white">
          <div className="flex items-center gap-2.5 text-base font-extrabold tracking-tight">
            <span className="inline-block h-7 w-7 rounded-md bg-[linear-gradient(135deg,#ED1C24_30%,#0072BC_30%_70%,#009A44_70%)]" />
            PERTAMINA
          </div>
          <div className="mt-1 text-[13px] font-semibold text-white/85">Procurement AI Copilot</div>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 px-6 py-6" noValidate>
          <div>
            <h1 className="text-[15px] font-extrabold text-pertamina-navy">Masuk ke akun Anda</h1>
            <p className="mt-0.5 text-[11.5px] text-pertamina-gray-500">Gunakan akun yang diberikan administrator sistem.</p>
          </div>

          <label className="flex flex-col gap-1 text-xs font-semibold text-pertamina-gray-700">
            Username
            <input
              type="text"
              autoComplete="username"
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="rounded-md border-[1.5px] border-pertamina-gray-200 bg-pertamina-gray-50 px-3 py-2 text-[13px] font-normal text-pertamina-gray-900 outline-none transition focus:border-pertamina-blue focus:bg-white focus:ring-[3px] focus:ring-pertamina-blue/15"
            />
          </label>

          <label className="flex flex-col gap-1 text-xs font-semibold text-pertamina-gray-700">
            Password
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-md border-[1.5px] border-pertamina-gray-200 bg-pertamina-gray-50 px-3 py-2 text-[13px] font-normal text-pertamina-gray-900 outline-none transition focus:border-pertamina-blue focus:bg-white focus:ring-[3px] focus:ring-pertamina-blue/15"
            />
          </label>

          {error && (
            <p role="alert" className="rounded-md border border-red-200 bg-pertamina-red-light px-3 py-2 text-xs text-red-900">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={!username.trim() || !password || submitting}
            className="rounded-lg bg-pertamina-navy py-2.5 text-[13px] font-bold text-white transition hover:bg-pertamina-navy-light disabled:opacity-50"
          >
            {submitting ? 'Memeriksa...' : 'Masuk'}
          </button>
        </form>
      </div>
    </div>
  )
}
