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

/** The shapes the admin API returns. */

export interface AdminSession {
  username: string
  csrf_token: string
}

export interface AdminProduct {
  id: number
  slug: string
  title: string
  price: string
  source_price: string | null
  source_price_changed: boolean
  price_manually_edited: boolean
  compare_at_price: string | null
  currency: string
  stock: number
  vendor: string | null
  sku: string | null
  status: string
  image: string | null
  source_url: string | null
  source_platform: string | null
  source_fetched_at: string | null
  updated_at: string
}

export interface AdminImage {
  id: number
  local_path: string | null
  remote_url: string | null
  alt: string | null
  position: number
}

export interface AdminVariant {
  id: number
  title: string
  sku: string | null
  price: string
  compare_at_price: string | null
  stock: number
  options: Record<string, unknown>
}

export interface AdminProductDetail extends AdminProduct {
  description: string
  attributes: Record<string, unknown>
  images: AdminImage[]
  categories: Category[]
  variants: AdminVariant[]
}

export interface AdminProductListing {
  items: AdminProduct[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface AdminCategory {
  id: number
  slug: string
  name: string
  parent_id: number | null
  position: number
  product_count: number
}

export interface AdminCategoryListing {
  items: AdminCategory[]
}

export interface AdminOrder {
  code: string
  email: string
  name: string
  total: string
  currency: string
  status: string
  created_at: string
  item_count: number
}

export interface AdminOrderListing {
  items: AdminOrder[]
  total: number
}

export interface CrawlRun {
  id: number
  url: string
  platform: string | null
  status: string
  products_found: number
  products_imported: number
  pages_crawled: number
  error: string | null
  started_at: string | null
  finished_at: string | null
}

export interface CrawlRunListing {
  items: CrawlRun[]
  total: number
}

export interface PriceChange {
  id: number
  old_price: string
  new_price: string
  source: string
  changed_at: string
}

export interface BulkPriceResult {
  mode: string
  value: string
  factor: string | null
  updated: number
  products: PriceChange[]
}
