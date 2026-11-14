import { useState } from 'react'
import { api, assetUrl } from '../lib/api'
import { useCart } from '../lib/cart'
import { useRoute } from '../lib/router'
import { formatMoney } from '../lib/format'

/** The cart, with the totals the server confirms. */
export function CartPage() {
  const cart = useCart()
  const { navigate } = useRoute()
  const [confirmedTotal, setConfirmedTotal] = useState<string | null>(null)
  const [checking, setChecking] = useState(false)

  if (cart.items.length === 0) {
    return (
      <div className="panel">
        <h1>Your cart is empty</h1>
        <p>Pick something from the shop and it will show up here.</p>
        <button
          type="button"
          className="primary"
          onClick={() => navigate('/category/all')}
        >
          Browse the shop
        </button>
      </div>
    )
  }

  const checkTotal = async () => {
    setChecking(true)
    try {
      const result = await api.post<{ total: string }>('/api/orders/quote', {
        items: cart.items.map((item) => ({
          product_id: item.productId,
          quantity: item.quantity,
        })),
      })
      setConfirmedTotal(result.total)
    } catch {
      setConfirmedTotal(null)
    } finally {
      setChecking(false)
    }
  }

  return (
    <div className="cart">
      <h1>Your cart</h1>

      <table className="table">
        <thead>
          <tr>
            <th>Product</th>
            <th>Price</th>
            <th>Quantity</th>
            <th>Total</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {cart.items.map((item) => {
            const line = Number.parseFloat(item.price) * item.quantity
            return (
              <tr key={item.productId}>
                <td>
                  <div className="cart-product">
                    {item.image ? (
                      <img src={assetUrl(item.image) ?? ''} alt={item.title} />
                    ) : null}
                    <button
                      type="button"
                      className="link"
                      onClick={() => navigate(`/product/${item.slug}`)}
                    >
                      {item.title}
                    </button>
                  </div>
                </td>
                <td>{formatMoney(item.price)}</td>
                <td>
                  <input
                    type="number"
                    min={0}
                    value={item.quantity}
                    aria-label={`Quantity of ${item.title}`}
                    onChange={(event) =>
                      cart.setQuantity(
                        item.productId,
                        Number.parseInt(event.target.value, 10) || 0,
                      )
                    }
                  />
                </td>
                <td>{formatMoney(line.toFixed(2))}</td>
                <td>
                  <button
                    type="button"
                    className="link"
                    onClick={() => cart.remove(item.productId)}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div className="cart-summary">
        <span>Subtotal</span>
        <strong>{formatMoney(cart.subtotal)}</strong>
      </div>

      {confirmedTotal !== null ? (
        <p className="muted">
          The server confirms a total of {formatMoney(confirmedTotal)}.
        </p>
      ) : null}

      <div className="cart-actions">
        <button type="button" onClick={() => navigate('/category/all')}>
          Keep shopping
        </button>
        <button type="button" className="primary" onClick={() => navigate('/checkout')}>
          Check out
        </button>
      </div>

      <p className="muted">
        The server works out the final total when the order is placed.
      </p>
      <button type="button" className="link" disabled={checking} onClick={() => void checkTotal()}>
        {checking ? 'Checking…' : 'Check the total with the server'}
      </button>
    </div>
  )
}
