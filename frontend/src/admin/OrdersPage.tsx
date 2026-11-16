import { api } from '../lib/api'
import { useLoader } from '../lib/useLoader'
import { formatDate, formatMoney } from '../lib/format'
import type { AdminOrderListing } from '../lib/types'

/** Every order the shop has taken. */
export function OrdersPage() {
  const orders = useLoader(() => api.get<AdminOrderListing>('/api/admin/orders'), [])

  const items = orders.data?.items ?? []

  return (
    <div className="admin-orders">
      <h1>Orders</h1>

      {orders.loading ? <p className="muted">Loading…</p> : null}
      {orders.error ? <p className="error">{orders.error}</p> : null}

      {items.length > 0 ? (
        <table className="table">
          <thead>
            <tr>
              <th>Order</th>
              <th>Customer</th>
              <th>Items</th>
              <th>Total</th>
              <th>Status</th>
              <th>Placed</th>
            </tr>
          </thead>
          <tbody>
            {items.map((order) => (
              <tr key={order.code}>
                <td>{order.code}</td>
                <td>
                  {order.name}
                  <br />
                  <span className="muted">{order.email}</span>
                </td>
                <td>{order.item_count}</td>
                <td>
                  <strong>{formatMoney(order.total, order.currency)}</strong>
                </td>
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

      {orders.data ? (
        <p className="muted">
          {orders.data.total} {orders.data.total === 1 ? 'order' : 'orders'} in total.
        </p>
      ) : null}
    </div>
  )
}
