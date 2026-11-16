import { type FormEvent, useState } from 'react'
import { api, ApiError } from '../lib/api'
import { useLoader } from '../lib/useLoader'
import type { AdminCategory, AdminCategoryListing } from '../lib/types'

/** The categories of the shop. */
export function CategoriesPage() {
  const categories = useLoader(
    () => api.get<AdminCategoryListing>('/api/admin/categories'),
    [],
  )
  const [name, setName] = useState('')
  const [parent, setParent] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<number | null>(null)
  const [editName, setEditName] = useState('')

  const items = categories.data?.items ?? []

  const create = async (event: FormEvent) => {
    event.preventDefault()
    if (!name.trim()) return

    setBusy(true)
    setError(null)
    try {
      await api.post<AdminCategory>('/api/admin/categories', {
        name: name.trim(),
        parent_id: parent ? Number.parseInt(parent, 10) : null,
      })
      setName('')
      setParent('')
      categories.reload()
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : 'The category could not be created. Please try again.',
      )
    } finally {
      setBusy(false)
    }
  }

  const rename = async (id: number) => {
    if (!editName.trim()) return
    setError(null)
    try {
      await api.patch<AdminCategory>(`/api/admin/categories/${id}`, {
        name: editName.trim(),
      })
      setEditing(null)
      categories.reload()
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : 'The category could not be renamed. Please try again.',
      )
    }
  }

  return (
    <div className="admin-categories">
      <h1>Categories</h1>

      <form className="form admin-form-narrow" onSubmit={create}>
        <h2>Add a category</h2>

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
          Under
          <select value={parent} onChange={(event) => setParent(event.target.value)}>
            <option value="">Nothing — a top level category</option>
            {items.map((category) => (
              <option key={category.id} value={String(category.id)}>
                {category.name}
              </option>
            ))}
          </select>
        </label>

        {error ? <p className="error">{error}</p> : null}

        <button type="submit" className="primary" disabled={busy}>
          {busy ? 'Adding…' : 'Add the category'}
        </button>
      </form>

      {categories.loading ? <p className="muted">Loading…</p> : null}
      {categories.error ? <p className="error">{categories.error}</p> : null}

      {items.length > 0 ? (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Slug</th>
              <th>Under</th>
              <th>Products</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((category) => (
              <tr key={category.id}>
                <td>
                  {editing === category.id ? (
                    <span className="inline-edit">
                      <input
                        type="text"
                        value={editName}
                        onChange={(event) => setEditName(event.target.value)}
                      />
                      <button type="button" className="primary" onClick={() => void rename(category.id)}>
                        Save
                      </button>
                      <button type="button" onClick={() => setEditing(null)}>
                        Cancel
                      </button>
                    </span>
                  ) : (
                    category.name
                  )}
                </td>
                <td className="muted">{category.slug}</td>
                <td className="muted">
                  {category.parent_id
                    ? (items.find((item) => item.id === category.parent_id)?.name ?? '—')
                    : '—'}
                </td>
                <td>{category.product_count}</td>
                <td>
                  <button
                    type="button"
                    className="link"
                    onClick={() => {
                      setEditing(category.id)
                      setEditName(category.name)
                    }}
                  >
                    Rename
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="muted">There are no categories yet.</p>
      )}
    </div>
  )
}
