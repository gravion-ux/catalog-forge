import { RouterProvider, useRoute } from './lib/router'
import { CartProvider } from './lib/cart'
import { StorefrontLayout } from './storefront/Layout'
import { HomePage } from './storefront/HomePage'
import { CategoryPage } from './storefront/CategoryPage'
import { ProductPage } from './storefront/ProductPage'
import { CartPage } from './storefront/CartPage'
import { CheckoutPage } from './storefront/CheckoutPage'
import { OrderPage } from './storefront/OrderPage'

const PATTERNS = [
  '/',
  '/category/:slug',
  '/product/:slug',
  '/cart',
  '/checkout',
  '/order/:code',
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

export default function App() {
  return (
    <RouterProvider patterns={PATTERNS}>
      <CartProvider>
        <StorefrontLayout>
          <StorefrontPages />
        </StorefrontLayout>
      </CartProvider>
    </RouterProvider>
  )
}
