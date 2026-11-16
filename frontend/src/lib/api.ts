/** The API client.
 *
 * Every call goes to the backend through `VITE_API_BASE`, and every failure
 * becomes an `ApiError` carrying the message the server sent, so a page can
 * show the server's own words.
 *
 * Every call that changes something carries the CSRF token of the admin
 * session. The server checks it against the session before it changes
 * anything, so a page never has to think about it.
 */

const API_BASE = (import.meta.env.VITE_API_BASE ?? 'http://localhost:8000').replace(
  /\/+$/,
  '',
)

/** The CSRF token of the admin session, when there is one. */
let csrfToken: string | null = null

/** Remember the CSRF token of the admin session, or forget it with `null`. */
export function setCsrfToken(token: string | null): void {
  csrfToken = token
}

/** The CSRF token of the admin session, if there is one. */
export function getCsrfToken(): string | null {
  return csrfToken
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

/** The absolute address of an API path. */
export function apiUrl(path: string): string {
  return `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`
}

/** The absolute address of a file the server holds, such as an image. */
export function assetUrl(path: string | null | undefined): string | null {
  if (!path) return null
  if (/^https?:\/\//i.test(path)) return path
  return apiUrl(path)
}

interface ErrorPayload {
  error?: { code?: string; message?: string }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (method !== 'GET' && csrfToken !== null) headers['X-CSRF-Token'] = csrfToken

  let response: Response
  try {
    response = await fetch(apiUrl(path), {
      method,
      credentials: 'include',
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'network_error', 'The server could not be reached.')
  }

  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = null
    }
  }

  if (!response.ok) {
    const error = (payload as ErrorPayload | null)?.error
    throw new ApiError(
      response.status,
      error?.code ?? 'request_failed',
      error?.message ?? `The request failed with status ${response.status}.`,
    )
  }

  return payload as T
}

export const api = {
  get: <T>(path: string): Promise<T> => request<T>('GET', path),
  post: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>('POST', path, body),
  patch: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>('PATCH', path, body),
  delete: <T>(path: string): Promise<T> => request<T>('DELETE', path),
}
