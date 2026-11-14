import { type FormEvent, useState } from 'react'
import { api, ApiError } from '../lib/api'
import { useCart } from '../lib/cart'
import { useRoute } from '../lib/router'
import { formatMoney } from '../lib/format'
import type { Order } from '../lib/types'

/** The checkout form. */
export function CheckoutPage() {
  const cart = useCart()
  const { navigate } = useRoute()
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [line1, setLine1] = useState('')
  const [city, setCity] = useState('')
  const [postcode, setPostcode] = useState('')
  const [country, setCountry] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [placing, setPlacing] = useState(false)

  if (cart.items.length === 0) {
    return (
      <div className="panel">
        <h1>There is nothing to check out</h1>
        <button type="button" className="primary" onClick={() => navigate('/category/all')}>
          Browse the shop
        </button>
      </div>
    )
  }

  const placeOrder = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setPlacing(true)

    try {
      const order = await api.post<Order>('/api/checkout', {
        email: email.trim(),
        name: name.trim(),
        address: {
          line1: line1.trim(),
          city: city.trim(),
          postcode: postcode.trim(),
          country: country.trim(),
        },
        items: cart.items.map((item) => ({
          product_id: item.productId,
          quantity: item.quantity,
        })),
      })
      cart.clear()
      navigate(`/order/${order.code}`)
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : 'The order could not be placed. Please try again.',
      )
    } finally {
      setPlacing(false)
    }
  }

  return (
    <div className="checkout">
      <h1>Check out</h1>

      <div className="checkout-grid">
        <form className="form" onSubmit={placeOrder}>
          <h2>Where to send it</h2>

          <label>
            Email
            <input
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>

          <label>
            Name
            <input
              type="text"
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>

          <label>
            Address
            <input
              type="text"
              required
              value={line1}
              onChange={(event) => setLine1(event.target.value)}
            />
          </label>

          <label>
            City
            <input
              type="text"
              required
              value={city}
              onChange={(event) => setCity(event.target.value)}
            />
          </label>

          <label>
            Postcode
            <input
              type="text"
              required
              value={postcode}
              onChange={(event) => setPostcode(event.target.value)}
            />
          </label>

          <label>
            Country
            <input
              type="text"
              required
              value={country}
              onChange={(event) => setCountry(event.target.value)}
            />
          </label>

          {error ? <p className="error">{error}</p> : null}

          <button type="submit" className="primary" disabled={placing}>
            {placing ? 'Placing the order…' : 'Place the order'}
          </button>
        </form>

        <aside className="panel">
          <h2>Your order</h2>
          <ul className="plain">
            {cart.items.map((item) => (
              <li key={item.productId}>
                <span>
                  {item.title} × {item.quantity}
                </span>
                <span>{formatMoney(Number.parseFloat(item.price) * item.quantity)}</span>
              </li>
            ))}
          </ul>
          <div className="cart-summary">
            <span>Total</span>
            <strong>{formatMoney(cart.subtotal)}</strong>
          </div>
        </aside>
      </div>
    </div>
  )
}
