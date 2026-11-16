import { api } from '../lib/api'
import { useLoader } from '../lib/useLoader'
import { formatDate, formatMoney } from '../lib/format'
import type {
  AdminCategoryListing,
  AdminOrderListing,
  AdminProductListing,
  CrawlRunListing,
} from '../lib/types'

/** The first thing the owner sees. */
export function DashboardPage() {
  const products = useLoader(
    () => api.get<AdminProductListing>('/api/admin/products?page_size=1'),
    [],
  )
  const categories = useLoader(
    () => api.get<AdminCategoryListing>('/api/admin/categories'),
    [],
  )
  const orders = useLoader(() => api.get<AdminOrderListing>('/api/admin/orders'), [])
  const crawls = useLoader(() => api.get<CrawlRunListing>('/api/admin/crawls'), [])

  const recentCrawls = (crawls.data?.items ?? []).slice(0, 5)
  const recentOrders = (orders.data?.items ?? []).slice(0, 5)

  return (
    <div className="admin-dashboard">
      <h1>Dashboard</h1>

      <div className="stat-row">
        <div className="stat">
          <span className="muted">Products</span>
          <strong>{products.data?.total ?? '—'}</strong>
        </div>
        <div className="stat">
          <span className="muted">Categories</span>
          <strong>{categories.data?.items.length ?? '—'}</strong>
        </div>
        <div className="stat">
          <span className="muted">Orders</span>
          <strong>{orders.data?.total ?? '—'}</strong>
        </div>
        <div className="stat">
          <span className="muted">Crawl runs</span>
          <strong>{crawls.data?.total ?? '—'}</strong>
        </div>
      </div>

      <section className="admin-panel">
        <h2>Recent crawls</h2>
        {crawls.loading ? <p className="muted">Loading…</p> : null}
        {crawls.error ? <p className="error">{crawls.error}</p> : null}
        {recentCrawls.length > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th>Address</th>
                <th>Status</th>
                <th>Found</th>
                <th>Imported</th>
                <th>Started</th>
              </tr>
            </thead>
            <tbody>
              {recentCrawls.map((run) => (
                <tr key={run.id}>
                  <td className="cell-wrap">{run.url}</td>
                  <td>
                    <span className={`badge ${run.status === 'failed' ? 'warn' : ''}`}>
                      {run.status}
                    </span>
                  </td>
                  <td>{run.products_found}</td>
                  <td>{run.products_imported}</td>
                  <td>{formatDate(run.started_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">No crawl has run yet.</p>
        )}
      </section>

      <section className="admin-panel">
        <h2>Recent orders</h2>
        {orders.loading ? <p className="muted">Loading…</p> : null}
        {orders.error ? <p className="error">{orders.error}</p> : null}
        {recentOrders.length > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th>Order</th>
                <th>Customer</th>
                <th>Total</th>
                <th>Status</th>
                <th>Placed</th>
              </tr>
            </thead>
            <tbody>
              {recentOrders.map((order) => (
                <tr key={order.code}>
                  <td>{order.code}</td>
                  <td>
                    {order.name}
                    <br />
                    <span className="muted">{order.email}</span>
                  </td>
                  <td>{formatMoney(order.total, order.currency)}</td>
                  <td>
                    <span className="badge">{order.status}</span>
                  </td>
                  <td>{formatDate(order.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">No orders yet.</p>
        )}
      </section>
    </div>
  )
}
