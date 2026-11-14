/** The cart.
 *
 * The cart lives in the browser so a page refresh does not empty it. The
 * prices here are what the shop last showed; the server works out the real
 * total when the order is placed.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { fromCents, toCents } from './format'

export interface CartItem {
  productId: number
  slug: string
  title: string
  price: string
  image: string | null
  quantity: number
}

export interface CartProduct {
  productId: number
  slug: string
  title: string
  price: string
  image: string | null
}

interface CartValue {
  items: CartItem[]
  count: number
  subtotal: string
  add: (product: CartProduct, quantity?: number) => void
  remove: (productId: number) => void
  setQuantity: (productId: number, quantity: number) => void
  clear: () => void
}

const STORAGE_KEY = 'catalog-forge.cart'

const CartContext = createContext<CartValue | null>(null)

function readStoredItems(): CartItem[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((item): item is CartItem => {
      if (typeof item !== 'object' || item === null) return false
      const candidate = item as Partial<CartItem>
      return typeof candidate.productId === 'number' && typeof candidate.quantity === 'number'
    })
  } catch {
    return []
  }
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>(readStoredItems)

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
    } catch {
      // A browser that refuses to store the cart is still a usable browser.
    }
  }, [items])

  const add = useCallback((product: CartProduct, quantity = 1) => {
    setItems((current) => {
      const existing = current.find((item) => item.productId === product.productId)
      if (existing) {
        return current.map((item) =>
          item.productId === product.productId
            ? { ...item, quantity: item.quantity + quantity }
            : item,
        )
      }
      return [...current, { ...product, quantity }]
    })
  }, [])

  const remove = useCallback((productId: number) => {
    setItems((current) => current.filter((item) => item.productId !== productId))
  }, [])

  const setQuantity = useCallback((productId: number, quantity: number) => {
    setItems((current) =>
      current
        .map((item) =>
          item.productId === productId ? { ...item, quantity: Math.max(0, quantity) } : item,
        )
        .filter((item) => item.quantity > 0),
    )
  }, [])

  const clear = useCallback(() => setItems([]), [])

  const value = useMemo<CartValue>(() => {
    const count = items.reduce((total, item) => total + item.quantity, 0)
    const cents = items.reduce(
      (total, item) => total + toCents(item.price) * item.quantity,
      0,
    )
    return {
      items,
      count,
      subtotal: fromCents(cents),
      add,
      remove,
      setQuantity,
      clear,
    }
  }, [items, add, remove, setQuantity, clear])

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}

export function useCart(): CartValue {
  const value = useContext(CartContext)
  if (value === null) {
    throw new Error('useCart has to be used inside a CartProvider.')
  }
  return value
}
