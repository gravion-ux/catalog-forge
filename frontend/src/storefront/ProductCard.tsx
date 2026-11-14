import { assetUrl } from '../lib/api'
import { useRoute } from '../lib/router'
import { formatMoney, stockLabel } from '../lib/format'
import type { Product } from '../lib/types'

/** One product in a grid. */
export function ProductCard({ product }: { product: Product }) {
  const { navigate } = useRoute()
  const image = assetUrl(product.image)

  return (
    <a
      className="card"
      href={`/product/${product.slug}`}
      onClick={(event) => {
        event.preventDefault()
        navigate(`/product/${product.slug}`)
      }}
    >
      <div className="card-image">
        {image ? <img src={image} alt={product.title} loading="lazy" /> : null}
      </div>
      <h3>{product.title}</h3>
      <div className="card-meta">
        <span className="price">{formatMoney(product.price, product.currency)}</span>
        {product.stock <= 0 ? <span className="muted">Out of stock</span> : null}
        {product.stock > 0 && product.stock <= 3 ? (
          <span className="warn">{stockLabel(product.stock)}</span>
        ) : null}
      </div>
    </a>
  )
}
