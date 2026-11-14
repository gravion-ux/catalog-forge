/** The shapes the API returns. */

export interface Category {
  id: number
  slug: string
  name: string
  product_count: number
}

export interface CategoriesResponse {
  items: Category[]
}

export interface Product {
  id: number
  slug: string
  title: string
  price: string
  compare_at_price: string | null
  currency: string
  stock: number
  vendor: string | null
  image: string | null
}

export interface ProductListing {
  items: Product[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface Image {
  id: number
  local_path: string | null
  remote_url: string | null
  alt: string | null
  position: number
}

export interface ProductDetail extends Product {
  description: string
  sku: string | null
  source_url: string | null
  source_platform: string | null
  source_price: string | null
  source_fetched_at: string | null
  price_manually_edited: boolean
  attributes: Record<string, unknown>
  images: Image[]
  categories: Category[]
}

export interface CartLine {
  product_id: number
  title: string
  unit_price: string
  quantity: number
  line_total: string
  currency: string
}

export interface Quote {
  lines: CartLine[]
  subtotal: string
  total: string
  currency: string
}

export interface OrderItem {
  product_id: number | null
  title: string
  unit_price: string
  quantity: number
}

export interface Order {
  code: string
  email: string
  name: string
  address: Record<string, string>
  subtotal: string
  shipping: string
  discount: string
  total: string
  currency: string
  status: string
  created_at: string
  items: OrderItem[]
}

export interface CheckoutPayload {
  email: string
  name: string
  address: Record<string, string>
  items: { product_id: number; quantity: number }[]
}
