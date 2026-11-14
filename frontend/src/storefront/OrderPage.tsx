import { api } from '../lib/api'
import { useLoader } from '../lib/useLoader'
import { formatDate, formatMoney, fromCents, toCents } from '../lib/format'
import type { Order } from '../lib/types'

/** The confirmation of one order. */
export function OrderPage({ code }: { code: string }) {
  const order = useLoader(
    () => api.get<Order>(`/api/orders/${encodeURIComponent(code)}`),
    [code],
  )

  if (order.loading) return <p className="muted">Loading…</p>
  if (order.error) return <p className="error">{order.error}</p>
  if (!order.data) return <p className="muted">This order is not here.</p>

  const placed = order.data
  const address = placed.address ?? {}
  const addressLines = [
    address.line1,
    address.city,
    address.postcode,
    address.country,
  ].filter((value) => Boolean(value))

  return (
    <div className="order">
      <h1>Thank you — your order is in</h1>
      <p className="muted">
        Order <strong>{placed.code}</strong> was placed on {formatDate(placed.created_at)}.
      </p>

      <div className="panel">
        <h2>Items</h2>
        <ul className="plain">
          {placed.items.map((line, index) => (
            <li key={`${line.product_id ?? 'item'}-${index}`}>
              <span>
                {line.title} × {line.quantity}
              </span>
              <span>
                {formatMoney(
                  fromCents(toCents(line.unit_price) * line.quantity),
                  placed.currency,
                )}
              </span>
            </li>
          ))}
        </ul>

        <div className="cart-summary">
          <span>Subtotal</span>
          <strong>{formatMoney(placed.subtotal, placed.currency)}</strong>
        </div>
        <div className="cart-summary">
          <span>Total</span>
          <strong>{formatMoney(placed.total, placed.currency)}</strong>
        </div>
      </div>

      <div className="panel">
        <h2>Where it goes</h2>
        <p>{placed.name}</p>
        <p className="muted">{placed.email}</p>
        {addressLines.length > 0 ? (
          <p className="muted">{addressLines.join(', ')}</p>
        ) : null}
        <p className="muted">Status: {placed.status}</p>
      </div>
    </div>
  )
}
