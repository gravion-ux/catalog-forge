import { api } from '../lib/api'
import { useLoader } from '../lib/useLoader'
import type { CategoriesResponse, ProductListing } from '../lib/types'
import { ProductCard } from './ProductCard'

export function HomePage() {
  const categories = useLoader(
    () => api.get<CategoriesResponse>('/api/categories'),
    [],
  )
  const products = useLoader(
    () => api.get<ProductListing>('/api/products?page_size=8'),
    [],
  )

  return (
    <div className="home">
      <section className="hero">
        <h1>Everything the shop sells, in one place</h1>
        <p>
          This catalog is ours to run: our own pages, our own prices, our own
          stock.
        </p>
      </section>

      {categories.data && categories.data.items.length > 0 ? (
        <section className="block">
          <h2>Categories</h2>
          <div className="chips">
            {categories.data.items.map((category) => (
              <a key={category.id} className="chip" href={`/category/${category.slug}`}>
                {category.name}
                <span className="chip-count">{category.product_count}</span>
              </a>
            ))}
          </div>
        </section>
      ) : null}

      <section className="block">
        <h2>New in</h2>
        {products.loading ? <p className="muted">Loading…</p> : null}
        {products.error ? <p className="error">{products.error}</p> : null}
        {products.data ? (
          products.data.items.length > 0 ? (
            <div className="grid">
              {products.data.items.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          ) : (
            <p className="muted">
              Nothing here yet. Crawl a shop from the admin panel to fill this
              page.
            </p>
          )
        ) : null}
      </section>

      {products.data && products.data.total > 0 ? (
        <p className="muted">
          Showing {products.data.items.length} of {products.data.total} products.
        </p>
      ) : null}
    </div>
  )
}
