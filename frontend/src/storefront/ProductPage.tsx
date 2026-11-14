import { useState } from 'react'
import { api, assetUrl } from '../lib/api'
import { useCart } from '../lib/cart'
import { useLoader } from '../lib/useLoader'
import { formatMoney, stockLabel } from '../lib/format'
import type { ProductDetail } from '../lib/types'

/** One product, with everything needed to buy it. */
export function ProductPage({ slug }: { slug: string }) {
  const cart = useCart()
  const product = useLoader(
    () => api.get<ProductDetail>(`/api/products/${encodeURIComponent(slug)}`),
    [slug],
  )
  const [quantity, setQuantity] = useState(1)
  const [added, setAdded] = useState(false)

  if (product.loading) return <p className="muted">Loading…</p>
  if (product.error) return <p className="error">{product.error}</p>
  if (!product.data) return <p className="muted">This product is not here.</p>

  const item = product.data
  const images = item.images
    .map((image) => assetUrl(image.local_path))
    .filter((value): value is string => value !== null)
  const cover = images[0] ?? assetUrl(item.image)
  const soldOut = item.stock <= 0

  const addToCart = () => {
    cart.add(
      {
        productId: item.id,
        slug: item.slug,
        title: item.title,
        price: item.price,
        image: cover,
      },
      quantity,
    )
    setAdded(true)
  }

  return (
    <div className="product">
      <div className="product-media">
        {cover ? <img src={cover} alt={item.title} /> : <div className="no-image" />}
        {images.length > 1 ? (
          <div className="thumbs">
            {images.map((image) => (
              <img key={image} src={image} alt={item.title} />
            ))}
          </div>
        ) : null}
      </div>

      <div className="product-info">
        <h1>{item.title}</h1>
        {item.vendor ? <p className="muted">Sold by {item.vendor}</p> : null}

        <p className="product-price">
          {formatMoney(item.price, item.currency)}
          {item.compare_at_price ? (
            <span className="was">
              {formatMoney(item.compare_at_price, item.currency)}
            </span>
          ) : null}
        </p>

        <p className={soldOut ? 'error' : 'muted'}>{stockLabel(item.stock)}</p>

        {item.description ? (
          <p className="description">{item.description}</p>
        ) : null}

        {item.categories.length > 0 ? (
          <p className="muted">
            {item.categories.map((category) => category.name).join(', ')}
          </p>
        ) : null}

        <div className="buy">
          <label>
            Quantity
            <input
              type="number"
              min={1}
              max={Math.max(1, item.stock)}
              value={quantity}
              onChange={(event) =>
                setQuantity(Math.max(1, Number.parseInt(event.target.value, 10) || 1))
              }
            />
          </label>
          <button type="button" className="primary" disabled={soldOut} onClick={addToCart}>
            {soldOut ? 'Out of stock' : 'Add to cart'}
          </button>
          {added ? <span className="muted">Added to your cart.</span> : null}
        </div>
      </div>
    </div>
  )
}
