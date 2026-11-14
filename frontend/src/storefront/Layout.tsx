import { type FormEvent, type ReactNode, useState } from 'react'
import { api } from '../lib/api'
import { useCart } from '../lib/cart'
import { useRoute } from '../lib/router'
import { useLoader } from '../lib/useLoader'
import type { CategoriesResponse } from '../lib/types'

/** The chrome every storefront page sits in. */
export function StorefrontLayout({ children }: { children: ReactNode }) {
  const cart = useCart()
  const { navigate } = useRoute()
  const { data: categories } = useLoader(
    () => api.get<CategoriesResponse>('/api/categories'),
    [],
  )
  const [term, setTerm] = useState('')

  const search = (event: FormEvent) => {
    event.preventDefault()
    const query = term.trim()
    navigate(query ? `/category/all?q=${encodeURIComponent(query)}` : '/category/all')
  }

  return (
    <div className="shell">
      <header className="masthead">
        <a
          className="brand"
          href="/"
          onClick={(event) => {
            event.preventDefault()
            navigate('/')
          }}
        >
          Catalog&nbsp;Forge
        </a>

        <form className="search" onSubmit={search}>
          <input
            type="search"
            value={term}
            placeholder="Search the shop"
            aria-label="Search products"
            onChange={(event) => setTerm(event.target.value)}
          />
          <button type="submit">Search</button>
        </form>

        <a
          className="cart-link"
          href="/cart"
          onClick={(event) => {
            event.preventDefault()
            navigate('/cart')
          }}
        >
          Cart
          {cart.count > 0 ? <span className="cart-count">{cart.count}</span> : null}
        </a>
      </header>

      {categories && categories.items.length > 0 ? (
        <nav className="categories" aria-label="Categories">
          <a
            href="/category/all"
            onClick={(event) => {
              event.preventDefault()
              navigate('/category/all')
            }}
          >
            Everything
          </a>
          {categories.items.map((category) => (
            <a
              key={category.id}
              href={`/category/${category.slug}`}
              onClick={(event) => {
                event.preventDefault()
                navigate(`/category/${category.slug}`)
              }}
            >
              {category.name}
            </a>
          ))}
        </nav>
      ) : null}

      <main className="content">{children}</main>

      <footer className="footer">
        <p>
          Catalog Forge runs this shop from its own catalog. Prices and stock
          are set by the shop that sells them.
        </p>
      </footer>
    </div>
  )
}
