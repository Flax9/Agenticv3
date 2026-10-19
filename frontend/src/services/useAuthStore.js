import { create } from 'zustand'

// Access token hanya disimpan di memori (bukan localStorage) agar tidak bisa dicuri lewat XSS.
// Sesi dipulihkan saat halaman dimuat ulang lewat cookie refresh HttpOnly (/api/auth/refresh).

async function authRequest(path, options = {}) {
  const res = await fetch(path, { credentials: 'same-origin', ...options })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      /* respons bukan JSON */
    }
    throw new Error(typeof detail === 'string' ? detail : 'Permintaan gagal.')
  }
  return res.status === 204 ? null : res.json()
}

let refreshInFlight = null

export const useAuthStore = create((set, get) => ({
  status: 'checking', // 'checking' | 'anonymous' | 'authenticated'
  user: null,
  accessToken: null,

  _applyToken: (body) => set({ status: 'authenticated', user: body.user, accessToken: body.access_token }),
  _clear: () => set({ status: 'anonymous', user: null, accessToken: null }),

  // Dipanggil sekali saat aplikasi dimuat
  restoreSession: async () => {
    const ok = await get().refresh()
    if (!ok) get()._clear()
  },

  // Mengembalikan true bila access token baru berhasil didapat. Panggilan bersamaan berbagi satu request.
  refresh: () => {
    refreshInFlight ??= authRequest('/api/auth/refresh', { method: 'POST' })
      .then((body) => {
        get()._applyToken(body)
        return true
      })
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null
      })
    return refreshInFlight
  },

  login: async (username, password) => {
    const body = await authRequest('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    get()._applyToken(body)
  },

  logout: async () => {
    try {
      await authRequest('/api/auth/logout', { method: 'POST' })
    } finally {
      get()._clear()
    }
  },

  // Dipanggil api.js saat refresh gagal (sesi benar-benar berakhir)
  expireSession: () => get()._clear(),
}))
