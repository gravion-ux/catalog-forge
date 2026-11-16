import { type FormEvent, useEffect, useState } from 'react'
import { api, assetUrl } from '../lib/api'
import { useRoute } from '../lib/router'
import { useLoader } from '../lib/useLoader'
import { formatDate, formatMoney } from '../lib/format'
import type { AdminCategoryListing, AdminProductListing } from '../lib/types'

const PAGE_SIZE = 25

/** Every product, with the live price beside the price the source last had. */
export function ProductsPage() {
  const { query, navigate } = useRoute()
  const term = query.get('q') ?? ''
  const status = query.get('status') ?? ''
  const category = query.get('category') ?? ''
  const page = Math.max(1, Number.parseInt(query.get('page') ?? '1', 10) || 1)
  const [selected, setSelected] = useState<number[]>([])
  const [termInput, setTermInput] = useState(term)

  useEffect(() => {
    setTermInput(term)
  }, [term])

  const categories = useLoader(
    () => api.get<AdminCategoryListing>('/api/admin/categories'),
    [],
  )
  const listing = useLoader(
    () => {
      const search = new URLSearchParams()
      search.set('page', String(page))
      search.set('page_size', String(PAGE_SIZE))
      if (term) search.set('q', term)
      if (status) search.set('status', status)
      if (category) search.set('category_id', category)
      return api.get<AdminProductListing>(`/api/admin/products?${search.toString()}`)
    },
    [term, status, category, page],
  )

  const items = listing.data?.items ?? []
  const everySelected = items.length > 0 && items.every((product) => selected.includes(product.id))

  const goTo = (changes: Record<string, string>) => {
    const search = new URLSearchParams(query)
    for (const [key, value] of Object.entries(changes)) {
      if (value) search.set(key, value)
      else search.delete(key)
    }
    search.set('page', '1')
    navigate(`/admin/products?${search.toString()}`)
  }

  const goToPage = (next: number) => {
    const search = new URLSearchParams(query)
    search.set('page', String(next))
    navigate(`/admin/products?${search.toString()}`)
  }

  const toggle = (id: number) => {
    setSelected((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    )
  }

  const togglePage = () => {
    const onPage = items.map((product) => product.id)
    setSelected((current) => {
      if (everySelected) {
        const ids = new Set(onPage)
        return current.filter((id) => !ids.has(id))
      }
      return [...new Set([...current, ...onPage])]
    })
  }

  const search = (event: FormEvent) => {
    event.preventDefault()
    goTo({ q: termInput.trim() })
  }

  return (
    <div className="admin-products">
      <div className="admin-head">
        <h1>Products</h1>
        {selected.length > 0 ? (
          <div className="admin-actions">
            <span className="muted">{selected.length} selected</span>
            <button
              type="button"
              className="primary"
              onClick={() => navigate(`/admin/bulk-price?ids=${selected.join(',')}`)}
            >
              Change the price of the selected
            </button>
            <button type="button" onClick={() => setSelected([])}>
              Clear
            </button>
          </div>
        ) : null}
      </div>

      <form className="admin-filters" onSubmit={search}>
        <input
          type="search"
          aria-label="Search products"
          placeholder="Search by title or slug"
          value={termInput}
          onChange={(event) => setTermInput(event.target.value)}
        />

        <select
          aria-label="Status"
          value={status}
          onChange={(event) => goTo({ status: event.target.value })}
        >
          <option value="">Every status</option>
          <option value="active">Active</option>
          <option value="hidden">Hidden</option>
          <option value="draft">Draft</option>
        </select>

        <select
          aria-label="Category"
          value={category}
          onChange={(event) => goTo({ category: event.target.value })}
        >
          <option value="">Every category</option>
          {(categories.data?.items ?? []).map((item) => (
            <option key={item.id} value={String(item.id)}>
              {item.name}
            </option>
          ))}
        </select>

        <button type="submit">Search</button>
      </form>

      {listing.loading ? <p className="muted">Loading…</p> : null}
      {listing.error ? <p className="error">{listing.error}</p> : null}

      {listing.data ? (
        <>
          <p className="muted">
            {listing.data.total} {listing.data.total === 1 ? 'product' : 'products'}
          </p>

          {items.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>
                    <input
                      type="checkbox"
                      aria-label="Select every product on this page"
                      checked={everySelected}
                      onChange={togglePage}
                    />
                  </th>
                  <th>Product</th>
                  <th>Price</th>
                  <th>Source price</th>
                  <th>Stock</th>
                  <th>Status</th>
                  <th>Updated</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {items.map((product) => (
                  <tr key={product.id}>
                    <td>
                      <input
                        type="checkbox"
                        aria-label={`Select ${product.title}`}
                        checked={selected.includes(product.id)}
                        onChange={() => toggle(product.id)}
                      />
                    </td>
                    <td>
                      <div className="cell-product">
                        {product.image ? (
                          <img src={assetUrl(product.image) ?? ''} alt="" />
                        ) : null}
                        <span>
                          {product.title}
                          <br />
                          <span className="muted">{product.slug}</span>
                        </span>
                      </div>
                    </td>
                    <td>
                      <strong>{formatMoney(product.price, product.currency)}</strong>
                      {product.price_manually_edited ? (
                        <span className="badge">Set by hand</span>
                      ) : null}
                    </td>
                    <td>
                      {product.source_price ? (
                        <>
                          {formatMoney(product.source_price, product.currency)}
                          {product.source_price_changed ? (
                            <span className="badge warn">Source changed</span>
                          ) : null}
                        </>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>{product.stock}</td>
                    <td>
                      <span className="badge">{product.status}</span>
                    </td>
                    <td>{formatDate(product.updated_at)}</td>
                    <td>
                      <a
                        className="link"
                        href={`/admin/products/${product.id}`}
                        onClick={(event) => {
                          event.preventDefault()
                          navigate(`/admin/products/${product.id}`)
                        }}
                      >
                        Edit
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="muted">No products match these filters.</p>
          )}

          {listing.data.pages > 1 ? (
            <div className="pagination">
              <button type="button" disabled={page <= 1} onClick={() => goToPage(page - 1)}>
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
      ) : null}
    </div>
  )
}
