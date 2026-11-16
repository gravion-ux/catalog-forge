import { type FormEvent, useEffect, useState } from 'react'
import { api, ApiError, assetUrl } from '../lib/api'
import { useRoute } from '../lib/router'
import { useLoader } from '../lib/useLoader'
import { formatDate, formatMoney } from '../lib/format'
import type { AdminCategoryListing, AdminProductDetail } from '../lib/types'

interface EditorForm {
  title: string
  description: string
  vendor: string
  sku: string
  price: string
  compare_at_price: string
  currency: string
  stock: string
  status: string
  category_ids: number[]
  images: string
}

/** Edit one product: its words, its price, its stock and its pictures. */
export function ProductEditorPage({ id }: { id: number }) {
  const { navigate } = useRoute()
  const product = useLoader(
    () => api.get<AdminProductDetail>(`/api/admin/products/${id}`),
    [id],
  )
  const categories = useLoader(
    () => api.get<AdminCategoryListing>('/api/admin/categories'),
    [],
  )
  const [form, setForm] = useState<EditorForm | null>(null)
  const [originalPrice, setOriginalPrice] = useState<string>('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const item = product.data
    if (!item) return
    setForm({
      title: item.title,
      description: item.description,
      vendor: item.vendor ?? '',
      sku: item.sku ?? '',
      price: item.price,
      compare_at_price: item.compare_at_price ?? '',
      currency: item.currency,
      stock: String(item.stock),
      status: item.status,
      category_ids: item.categories.map((category) => category.id),
      images: item.images
        .map((image) => image.local_path ?? '')
        .filter((path) => path.length > 0)
        .join('\n'),
    })
    setOriginalPrice(item.price)
  }, [product.data])

  if (product.loading) return <p className="muted">Loading…</p>
  if (product.error) return <p className="error">{product.error}</p>
  if (!product.data || !form) return <p className="muted">This product is not here.</p>

  const item = product.data
  const set = <K extends keyof EditorForm>(key: K, value: EditorForm[K]) => {
    setForm((current) => (current ? { ...current, [key]: value } : current))
  }

  const toggleCategory = (categoryId: number) => {
    setForm((current) => {
      if (!current) return current
      const has = current.category_ids.includes(categoryId)
      return {
        ...current,
        category_ids: has
          ? current.category_ids.filter((value) => value !== categoryId)
          : [...current.category_ids, categoryId],
      }
    })
  }

  const save = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setMessage(null)
    setError(null)

    // The price is only sent when it really changed. Sending it every time
    // would mark the product as hand-priced even when only the text changed,
    // and a hand-set price is never overwritten by a crawl.
    const payload: Record<string, unknown> = {
      title: form.title,
      description: form.description,
      vendor: form.vendor,
      sku: form.sku,
      compare_at_price: form.compare_at_price.trim() === '' ? null : form.compare_at_price.trim(),
      currency: form.currency,
      stock: Number.parseInt(form.stock, 10) || 0,
      status: form.status,
      category_ids: form.category_ids,
      images: form.images
        .split('\n')
        .map((path) => path.trim())
        .filter((path) => path.length > 0),
    }
    if (form.price.trim() !== originalPrice) {
      payload.price = form.price.trim()
    }

    try {
      await api.patch<AdminProductDetail>(`/api/admin/products/${id}`, payload)
      setMessage('Saved.')
      product.reload()
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : 'The product could not be saved. Please try again.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="admin-editor">
      <div className="admin-head">
        <h1>{item.title}</h1>
        <button type="button" onClick={() => navigate('/admin/products')}>
          Back to the products
        </button>
      </div>

      <div className="editor-grid">
        <form className="form" onSubmit={save}>
          <h2>Details</h2>

          <label>
            Title
            <input
              type="text"
              required
              value={form.title}
              onChange={(event) => set('title', event.target.value)}
            />
          </label>

          <label>
            Description
            <textarea
              rows={6}
              value={form.description}
              onChange={(event) => set('description', event.target.value)}
            />
          </label>

          <label>
            Vendor
            <input
              type="text"
              value={form.vendor}
              onChange={(event) => set('vendor', event.target.value)}
            />
          </label>

          <label>
            SKU
            <input
              type="text"
              value={form.sku}
              onChange={(event) => set('sku', event.target.value)}
            />
          </label>

          <div className="field-row">
            <label>
              Price
              <input
                type="text"
                value={form.price}
                onChange={(event) => set('price', event.target.value)}
              />
            </label>
            <label>
              Compare-at price
              <input
                type="text"
                value={form.compare_at_price}
                onChange={(event) => set('compare_at_price', event.target.value)}
              />
            </label>
          </div>

          <div className="field-row">
            <label>
              Currency
              <input
                type="text"
                value={form.currency}
                onChange={(event) => set('currency', event.target.value)}
              />
            </label>
            <label>
              Stock
              <input
                type="number"
                min={0}
                value={form.stock}
                onChange={(event) => set('stock', event.target.value)}
              />
            </label>
          </div>

          <label>
            Status
            <select
              value={form.status}
              onChange={(event) => set('status', event.target.value)}
            >
              <option value="active">Active</option>
              <option value="hidden">Hidden</option>
              <option value="draft">Draft</option>
            </select>
          </label>

          <label>
            Images
            <textarea
              rows={4}
              value={form.images}
              placeholder="One stored image path per line"
              onChange={(event) => set('images', event.target.value)}
            />
          </label>

          <fieldset className="fieldset">
            <legend>Categories</legend>
            {(categories.data?.items ?? []).length === 0 ? (
              <p className="muted">There are no categories yet.</p>
            ) : (
              (categories.data?.items ?? []).map((category) => (
                <label key={category.id} className="check">
                  <input
                    type="checkbox"
                    checked={form.category_ids.includes(category.id)}
                    onChange={() => toggleCategory(category.id)}
                  />
                  {category.name}
                </label>
              ))
            )}
          </fieldset>

          {error ? <p className="error">{error}</p> : null}
          {message ? <p className="notice">{message}</p> : null}

          <button type="submit" className="primary" disabled={saving}>
            {saving ? 'Saving…' : 'Save the product'}
          </button>
        </form>

        <aside className="editor-side">
          <div className="admin-panel">
            <h2>Where it came from</h2>
            <dl className="facts">
              <dt>Source</dt>
              <dd>{item.source_platform ?? '—'}</dd>
              <dt>Source price</dt>
              <dd>
                {item.source_price
                  ? formatMoney(item.source_price, item.currency)
                  : '—'}
              </dd>
              <dt>Last crawled</dt>
              <dd>{formatDate(item.source_fetched_at)}</dd>
              <dt>Price</dt>
              <dd>
                {item.price_manually_edited
                  ? 'Set by hand — a crawl will not change it'
                  : 'Follows the source'}
              </dd>
            </dl>
            {item.source_url ? (
              <a className="link" href={item.source_url} target="_blank" rel="noreferrer">
                Open the source page
              </a>
            ) : null}
          </div>

          {item.images.length > 0 ? (
            <div className="admin-panel">
              <h2>Images</h2>
              <div className="editor-images">
                {item.images.map((image) => (
                  <img
                    key={image.id}
                    src={assetUrl(image.local_path) ?? ''}
                    alt={image.alt ?? item.title}
                  />
                ))}
              </div>
            </div>
          ) : null}

          {item.variants.length > 0 ? (
            <div className="admin-panel">
              <h2>Variants</h2>
              <table className="table">
                <thead>
                  <tr>
                    <th>Variant</th>
                    <th>Price</th>
                    <th>Stock</th>
                  </tr>
                </thead>
                <tbody>
                  {item.variants.map((variant) => (
                    <tr key={variant.id}>
                      <td>{variant.title || variant.sku || '—'}</td>
                      <td>{formatMoney(variant.price, item.currency)}</td>
                      <td>{variant.stock}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </aside>
      </div>
    </div>
  )
}
