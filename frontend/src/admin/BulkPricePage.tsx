import { type FormEvent, useMemo, useState } from 'react'
import { api, ApiError } from '../lib/api'
import { useRoute } from '../lib/router'
import { useLoader } from '../lib/useLoader'
import { formatMoney, fromCents, toCents } from '../lib/format'
import type {
  AdminCategoryListing,
  AdminProduct,
  AdminProductDetail,
  AdminProductListing,
  BulkPriceResult,
} from '../lib/types'

type Target = 'selected' | 'category' | 'all'

/** The number the change is built from, or `null` when it is not a number. */
function parseAmount(value: string): number | null {
  const text = value.trim().replace(/%/g, '').replace(/,/g, '')
  if (!text) return null
  const parsed = Number.parseFloat(text)
  return Number.isFinite(parsed) ? parsed : null
}

/** The factor the server will use for a markup, worked out the same way.
 *
 * A value between one and two that is written with a point is read as a
 * factor, and anything else is read as a percentage.
 */
function resolveFactor(mode: string, value: string, unit: string): number | null {
  if (mode !== 'markup') return null
  const amount = parseAmount(value)
  if (amount === null) return null

  const kind = unit.trim().toLowerCase()
  if (kind === 'factor') return amount
  if (kind === 'percent') return 1 + amount / 100
  if (value.trim().includes('.') && amount > 1 && amount < 2) return amount
  return 1 + amount / 100
}

/** The price a product would have after the change, in whole cents. */
function previewPrice(price: string, mode: string, amount: number, factor: number | null): string {
  const cents = toCents(price)
  let next = cents
  if (mode === 'set') next = Math.round(amount * 100)
  else if (mode === 'delta') next = cents + Math.round(amount * 100)
  else next = Math.round(cents * (factor ?? 1))
  if (next < 0) next = 0
  return fromCents(next)
}

/** Change the price of many products at once. */
export function BulkPricePage() {
  const { query } = useRoute()
  const idsParam = query.get('ids') ?? ''
  const ids = useMemo(
    () =>
      idsParam
        .split(',')
        .map((part) => Number.parseInt(part.trim(), 10))
        .filter((value) => Number.isFinite(value) && value > 0),
    [idsParam],
  )

  const [target, setTarget] = useState<Target>(ids.length > 0 ? 'selected' : 'category')
  const [categoryId, setCategoryId] = useState('')
  const [mode, setMode] = useState('markup')
  const [value, setValue] = useState('')
  const [unit, setUnit] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [applied, setApplied] = useState<BulkPriceResult | null>(null)

  const categories = useLoader(
    () => api.get<AdminCategoryListing>('/api/admin/categories'),
    [],
  )
  const targets = useLoader<AdminProduct[]>(async () => {
    if (target === 'selected' && ids.length > 0) {
      const details = await Promise.all(
        ids.map((id) => api.get<AdminProductDetail>(`/api/admin/products/${id}`)),
      )
      return details
    }
    if (target === 'category' && categoryId) {
      const search = new URLSearchParams()
      search.set('page_size', '200')
      search.set('category_id', categoryId)
      const listing = await api.get<AdminProductListing>(
        `/api/admin/products?${search.toString()}`,
      )
      return listing.items
    }
    const collected: AdminProduct[] = []
    let page = 1
    let pages = 1
    do {
      const search = new URLSearchParams()
      search.set('page', String(page))
      search.set('page_size', '200')
      const listing = await api.get<AdminProductListing>(
        `/api/admin/products?${search.toString()}`,
      )
      collected.push(...listing.items)
      pages = listing.pages
      page += 1
    } while (page <= pages)
    return collected
  }, [target, idsParam, categoryId])

  const amount = parseAmount(value)
  const factor = resolveFactor(mode, value, unit)
  const preview = useMemo(() => {
    if (amount === null || !targets.data) return []
    return targets.data.map((product) => ({
      id: product.id,
      title: product.title,
      oldPrice: product.price,
      newPrice: previewPrice(product.price, mode, amount, factor),
    }))
  }, [targets.data, mode, amount, factor])

  const apply = async (event: FormEvent) => {
    event.preventDefault()
    if (preview.length === 0) return

    setBusy(true)
    setError(null)
    setApplied(null)

    try {
      const result = await api.post<BulkPriceResult>('/api/admin/products/bulk-price', {
        mode,
        value: value.trim(),
        ...(unit.trim() ? { unit: unit.trim() } : {}),
        product_ids: preview.map((item) => item.id),
      })
      setApplied(result)
      targets.reload()
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : 'The prices could not be changed. Please try again.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="admin-bulk">
      <h1>Bulk pricing</h1>
      <p className="muted">
        The new prices are shown here first. Nothing changes until the change is
        applied.
      </p>

      <form className="form" onSubmit={apply}>
        <div className="field-row">
          <label>
            What to change
            <select
              value={target}
              onChange={(event) => setTarget(event.target.value as Target)}
            >
              {ids.length > 0 ? (
                <option value="selected">
                  The {ids.length} selected products
                </option>
              ) : null}
              <option value="category">A category</option>
              <option value="all">Every product</option>
            </select>
          </label>

          {target === 'category' ? (
            <label>
              Category
              <select
                value={categoryId}
                onChange={(event) => setCategoryId(event.target.value)}
              >
                <option value="">Choose a category</option>
                {(categories.data?.items ?? []).map((category) => (
                  <option key={category.id} value={String(category.id)}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          <label>
            How
            <select value={mode} onChange={(event) => setMode(event.target.value)}>
              <option value="markup">Raise or lower by a percentage</option>
              <option value="delta">Add or take away an amount</option>
              <option value="set">Set the same price on all of them</option>
            </select>
          </label>
        </div>

        <div className="field-row">
          <label>
            Value
            <input
              type="text"
              placeholder="10, 1.10 or 5.00"
              value={value}
              onChange={(event) => setValue(event.target.value)}
            />
          </label>

          <label>
            Read the value as
            <select value={unit} onChange={(event) => setUnit(event.target.value)}>
              <option value="">Work it out</option>
              <option value="percent">A percentage</option>
              <option value="factor">A factor</option>
            </select>
          </label>
        </div>

        {mode === 'markup' ? (
          <p className="muted">
            {factor === null
              ? 'Give a value to see the new prices.'
              : `The prices will be multiplied by ${factor.toFixed(4)}.`}
          </p>
        ) : null}

        {error ? <p className="error">{error}</p> : null}
        {applied ? (
          <p className="notice">
            {applied.updated} {applied.updated === 1 ? 'price' : 'prices'} changed.
            {applied.factor ? ` The factor was ${applied.factor}.` : ''}
          </p>
        ) : null}

        <button
          type="submit"
          className="primary"
          disabled={busy || preview.length === 0}
        >
          {busy ? 'Changing…' : `Change ${preview.length} prices`}
        </button>
      </form>

      {targets.loading ? <p className="muted">Working out the new prices…</p> : null}
      {targets.error ? <p className="error">{targets.error}</p> : null}

      {preview.length > 0 ? (
        <table className="table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Price now</th>
              <th>New price</th>
            </tr>
          </thead>
          <tbody>
            {preview.map((item) => (
              <tr key={item.id}>
                <td>{item.title}</td>
                <td>{formatMoney(item.oldPrice)}</td>
                <td>
                  <strong>{formatMoney(item.newPrice)}</strong>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  )
}
