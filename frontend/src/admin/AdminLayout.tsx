import { type ReactNode } from 'react'
import { useRoute } from '../lib/router'
import { useAdminSession } from './session'
import { LoginPage } from './LoginPage'

const LINKS = [
  { path: '/admin', label: 'Dashboard' },
  { path: '/admin/products', label: 'Products' },
  { path: '/admin/bulk-price', label: 'Bulk pricing' },
  { path: '/admin/categories', label: 'Categories' },
  { path: '/admin/orders', label: 'Orders' },
  { path: '/admin/crawls', label: 'Crawls' },
]

/** The chrome every admin page sits in. */
export function AdminLayout({ children }: { children: ReactNode }) {
  const session = useAdminSession()
  const { path, navigate } = useRoute()

  if (session.status === 'checking') {
    return <div className="admin-boot">Checking the session…</div>
  }

  if (session.status === 'signed-out') {
    return <LoginPage />
  }

  // The sign-in page stands on its own, without the panel around it.
  if (path === '/admin/login') {
    return <>{children}</>
  }

  const isActive = (link: string) =>
    path === link || (link !== '/admin' && path.startsWith(`${link}/`))

  return (
    <div className="admin">
      <aside className="admin-side">
        <a
          className="admin-brand"
          href="/admin"
          onClick={(event) => {
            event.preventDefault()
            navigate('/admin')
          }}
        >
          Catalog&nbsp;Forge
        </a>

        <nav className="admin-links">
          {LINKS.map((link) => (
            <a
              key={link.path}
              className={isActive(link.path) ? 'active' : ''}
              href={link.path}
              onClick={(event) => {
                event.preventDefault()
                navigate(link.path)
              }}
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="admin-account">
          <span className="muted">{session.username}</span>
          <button type="button" onClick={() => void session.logout()}>
            Sign out
          </button>
          <a
            className="muted"
            href="/"
            onClick={(event) => {
              event.preventDefault()
              navigate('/')
            }}
          >
            View the shop
          </a>
        </div>
      </aside>

      <main className="admin-main">{children}</main>
    </div>
  )
}
