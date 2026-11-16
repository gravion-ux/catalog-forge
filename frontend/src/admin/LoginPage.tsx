import { type FormEvent, useState } from 'react'
import { ApiError } from '../lib/api'
import { useRoute } from '../lib/router'
import { useAdminSession } from './session'

/** The sign-in form. */
export function LoginPage() {
  const session = useAdminSession()
  const { navigate } = useRoute()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await session.login(username, password)
      navigate('/admin')
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : 'The admin panel could not be opened. Please try again.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="admin-login">
      <form className="form" onSubmit={submit}>
        <h1>Sign in</h1>
        <p className="muted">The admin panel is where the catalog is edited.</p>

        <label>
          Username
          <input
            type="text"
            required
            autoFocus
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>

        <label>
          Password
          <input
            type="password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>

        {error ? <p className="error">{error}</p> : null}

        <button type="submit" className="primary" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}
