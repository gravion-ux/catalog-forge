import { RouterProvider, useRoute } from './lib/router'
import { CartProvider } from './lib/cart'
import { StorefrontLayout } from './storefront/Layout'
import { HomePage } from './storefront/HomePage'
import { CategoryPage } from './storefront/CategoryPage'
import { ProductPage } from './storefront/ProductPage'
import { CartPage } from './storefront/CartPage'
import { CheckoutPage } from './storefront/CheckoutPage'
import { OrderPage } from './storefront/OrderPage'
import { AdminSessionProvider } from './admin/session'
import { AdminLayout } from './admin/AdminLayout'
import { LoginPage } from './admin/LoginPage'
import { DashboardPage } from './admin/DashboardPage'
import { ProductsPage } from './admin/ProductsPage'
import { ProductEditorPage } from './admin/ProductEditorPage'
import { BulkPricePage } from './admin/BulkPricePage'
import { CategoriesPage } from './admin/CategoriesPage'
import { OrdersPage } from './admin/OrdersPage'
import { CrawlPage } from './admin/CrawlPage'

const PATTERNS = [
  '/',
  '/category/:slug',
  '/product/:slug',
  '/cart',
  '/checkout',
  '/order/:code',
  '/admin',
  '/admin/login',
  '/admin/products',
  '/admin/products/:id',
  '/admin/bulk-price',
  '/admin/categories',
  '/admin/orders',
  '/admin/crawls',
]

function StorefrontPages() {
  const { path, params } = useRoute()

  switch (path) {
    case '/':
      return <HomePage />
    case '/category/:slug':
      return <CategoryPage slug={params.slug} />
    case '/product/:slug':
      return <ProductPage slug={params.slug} />
    case '/cart':
      return <CartPage />
    case '/checkout':
      return <CheckoutPage />
    case '/order/:code':
      return <OrderPage code={params.code} />
    default:
      return (
        <div className="panel">
          <h1>Page not found</h1>
          <p>There is nothing at this address.</p>
        </div>
      )
  }
}

function AdminPages() {
  const { path, params } = useRoute()

  switch (path) {
    case '/admin/login':
      return <LoginPage />
    case '/admin':
      return <DashboardPage />
    case '/admin/products':
      return <ProductsPage />
    case '/admin/products/:id':
      return <ProductEditorPage id={Number.parseInt(params.id, 10) || 0} />
    case '/admin/bulk-price':
      return <BulkPricePage />
    case '/admin/categories':
      return <CategoriesPage />
    case '/admin/orders':
      return <OrdersPage />
    case '/admin/crawls':
      return <CrawlPage />
    default:
      return (
        <div className="admin-panel">
          <h1>Page not found</h1>
          <p className="muted">There is nothing at this address.</p>
        </div>
    )
  }
}

/** The storefront and the admin panel are two different worlds. */
function Shell() {
  const { path } = useRoute()
  const isAdmin = path === '/admin' || path.startsWith('/admin/')

  if (isAdmin) {
    return (
      <AdminSessionProvider>
        <AdminLayout>
          <AdminPages />
        </AdminLayout>
      </AdminSessionProvider>
    )
  }

  return (
    <CartProvider>
      <StorefrontLayout>
        <StorefrontPages />
      </StorefrontLayout>
    </CartProvider>
  )
}

export default function App() {
  return (
    <RouterProvider patterns={PATTERNS}>
      <Shell />
    </RouterProvider>
  )
}
