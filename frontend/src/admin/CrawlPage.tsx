import { type FormEvent, useEffect, useState } from 'react'
import { api, ApiError } from '../lib/api'
import { useLoader } from '../lib/useLoader'
import { formatDate } from '../lib/format'
import type { CrawlRun, CrawlRunListing } from '../lib/types'

/** Start a crawl and watch it work. */
export function CrawlPage() {
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const runs = useLoader(() => api.get<CrawlRunListing>('/api/admin/crawls'), [])
  const detail = useLoader<CrawlRun | null>(
    () =>
      selectedId === null
        ? Promise.resolve(null)
        : api.get<CrawlRun>(`/api/admin/crawls/${selectedId}`),
    [selectedId],
  )

  const items = runs.data?.items ?? []
  const running = items.some((run) => run.status === 'running')

  // While a crawl is working, keep the list fresh.
  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => runs.reload(), 2000)
    return () => window.clearInterval(timer)
  }, [running, runs.reload])

  // The crawl that is being watched is refreshed on its own.
  useEffect(() => {
    if (selectedId === null) return
    if (detail.data?.status !== 'running') return
    const timer = window.setInterval(() => detail.reload(), 2000)
    return () => window.clearInterval(timer)
  }, [selectedId, detail.data?.status, detail.reload])

  const start = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const run = await api.post<CrawlRun>('/api/admin/crawls', { url: url.trim() })
      setSelectedId(run.id)
      setUrl('')
      runs.reload()
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : 'The crawl could not be started. Please try again.',
      )
    } finally {
      setBusy(false)
    }
  }

  const watched = detail.data

  return (
    <div className="admin-crawls">
      <h1>Crawls</h1>

      <form className="form admin-form-narrow" onSubmit={start}>
        <h2>Crawl a shop</h2>
        <label>
          Address of the shop
          <input
            type="text"
            required
            placeholder="https://example.com"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
          />
        </label>
        <p className="muted">
          The crawler reads the robots.txt of the shop, keeps to the pages it
          allows, and never touches a private address.
        </p>
        {error ? <p className="error">{error}</p> : null}
        <button type="submit" className="primary" disabled={busy}>
          {busy ? 'Starting…' : 'Start the crawl'}
        </button>
      </form>

      {watched ? (
        <div className="admin-panel">
          <h2>Run #{watched.id}</h2>
          <p className="cell-wrap">{watched.url}</p>
          <dl className="facts">
            <dt>Status</dt>
            <dd>
              <span className={`badge ${watched.status === 'failed' ? 'warn' : ''}`}>
                {watched.status}
              </span>
            </dd>
            <dt>Platform</dt>
            <dd>{watched.platform ?? 'not known yet'}</dd>
            <dt>Pages crawled</dt>
            <dd>{watched.pages_crawled}</dd>
            <dt>Products found</dt>
            <dd>{watched.products_found}</dd>
            <dt>Products imported</dt>
            <dd>{watched.products_imported}</dd>
            <dt>Started</dt>
            <dd>{formatDate(watched.started_at)}</dd>
            <dt>Finished</dt>
            <dd>{formatDate(watched.finished_at)}</dd>
          </dl>
          {watched.error ? <p className="error">{watched.error}</p> : null}
        </div>
      ) : null}

      {runs.loading ? <p className="muted">Loading…</p> : null}
      {runs.error ? <p className="error">{runs.error}</p> : null}

      {items.length > 0 ? (
        <table className="table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Address</th>
              <th>Status</th>
              <th>Found</th>
              <th>Imported</th>
              <th>Started</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((run) => (
              <tr key={run.id}>
                <td>#{run.id}</td>
                <td className="cell-wrap">{run.url}</td>
                <td>
                  <span className={`badge ${run.status === 'failed' ? 'warn' : ''}`}>
                    {run.status}
                  </span>
                </td>
                <td>{run.products_found}</td>
                <td>{run.products_imported}</td>
                <td>{formatDate(run.started_at)}</td>
                <td>
                  <button
                    type="button"
                    className="link"
                    onClick={() => setSelectedId(run.id)}
                  >
                    Watch
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="muted">No crawl has run yet.</p>
      )}
    </div>
  )
}
