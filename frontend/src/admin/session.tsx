/** The admin session.
 *
 * The server keeps the session in an HttpOnly cookie. The browser only holds
 * the CSRF token that every change has to carry, and that token is what the
 * API client sends on every request that changes something.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api, setCsrfToken } from '../lib/api'
import type { AdminSession } from '../lib/types'

export type SessionStatus = 'checking' | 'signed-in' | 'signed-out'

interface AdminSessionValue {
  status: SessionStatus
  username: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AdminSessionContext = createContext<AdminSessionValue | null>(null)

export function AdminSessionProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<SessionStatus>('checking')
  const [username, setUsername] = useState<string | null>(null)

  const applySession = useCallback((session: AdminSession) => {
    setCsrfToken(session.csrf_token)
    setUsername(session.username)
    setStatus('signed-in')
  }, [])

  const clearSession = useCallback(() => {
    setCsrfToken(null)
    setUsername(null)
    setStatus('signed-out')
  }, [])

  useEffect(() => {
    let cancelled = false
    api
      .get<AdminSession>('/api/admin/session')
      .then((session) => {
        if (!cancelled) applySession(session)
      })
      .catch(() => {
        if (!cancelled) clearSession()
      })
    return () => {
      cancelled = true
    }
  }, [applySession, clearSession])

  const login = useCallback(
    async (name: string, password: string) => {
      const session = await api.post<AdminSession>('/api/admin/login', {
        username: name,
        password,
      })
      applySession(session)
    },
    [applySession],
  )

  const logout = useCallback(async () => {
    try {
      await api.post<{ ok: boolean }>('/api/admin/logout')
    } finally {
      clearSession()
    }
  }, [clearSession])

  const value = useMemo(
    () => ({ status, username, login, logout }),
    [status, username, login, logout],
  )

  return (
    <AdminSessionContext.Provider value={value}>{children}</AdminSessionContext.Provider>
  )
}

export function useAdminSession(): AdminSessionValue {
  const value = useContext(AdminSessionContext)
  if (value === null) {
    throw new Error('useAdminSession has to be used inside an AdminSessionProvider.')
  }
  return value
}
