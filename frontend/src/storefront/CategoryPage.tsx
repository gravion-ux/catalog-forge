import { api } from '../lib/api'
import { useRoute } from '../lib/router'
import { useLoader } from '../lib/useLoader'
import type { CategoriesResponse, ProductListing } from '../lib/types'
import { ProductCard } from './ProductCard'

const PAGE_SIZE = 12

/** The products of one category, or of the whole shop. */
export function CategoryPage({ slug }: { slug: string }) {
  const { query, navigate } = useRoute()
  const term = query.get('q') ?? ''
  const page = Math.max(1, Number.parseInt(query.get('page') ?? '1', 10) || 1)
  const all = slug === 'all'

  const categories = useLoader(
    () => api.get<CategoriesResponse>('/api/categories'),
    [],
  )
  const listing = useLoader(
    () => {
      const search = new URLSearchParams()
      search.set('page', String(page))
      search.set('page_size', String(PAGE_SIZE))
      if (!all) search.set('category', slug)
      if (term) search.set('q', term)
      return api.get<ProductListing>(`/api/products?${search.toString()}`)
    },
    [slug, term, page],
  )

  const category = categories.data?.items.find((item) => item.slug === slug)
  const title = all ? (term ? `Results for “${term}”` : 'Everything') : category?.name ?? slug

  const goToPage = (next: number) => {
    const search = new URLSearchParams(query)
    search.set('page', String(next))
    navigate(`/category/${slug}?${search.toString()}`)
  }

  return (
    <div className="listing">
      <div className="listing-head">
        <h1>{title}</h1>
        {listing.data ? (
          <p className="muted">
            {listing.data.total} {listing.data.total === 1 ? 'product' : 'products'}
          </p>
        ) : null}
      </div>

      {listing.loading ? <p className="muted">Loading…</p> : null}
      {listing.error ? <p className="error">{listing.error}</p> : null}

      {listing.data ? (
        listing.data.items.length > 0 ? (
          <>
            <div className="grid">
              {listing.data.items.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>

            {listing.data.pages > 1 ? (
              <div className="pagination">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => goToPage(page - 1)}
                >
                  Previous
                </button>
                <span className="muted">
                  Page {listing.data.page} of {listing.data.pages}
                </span>
                <button
                  type="button"
                  disabled={page >= listing.data.pages}
                  onClick={() => goToPage(page + 1)}
                >
                  Next
                </button>
              </div>
            ) : null}
          </>
        ) : (
          <p className="muted">No products here yet.</p>
        )
      ) : null}
    </div>
  )
}
