/** Formatting helpers.
 *
 * Prices arrive as strings with two decimals and stay that way. The only
 * arithmetic here is done in whole cents, so a cart total never picks up a
 * rounding error.
 */

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$',
  EUR: '€',
  GBP: '£',
  INR: '₹',
}

/** A price in whole cents. */
export function toCents(value: string | number | null | undefined): number {
  if (value === null || value === undefined) return 0
  const parsed = typeof value === 'number' ? value : Number.parseFloat(value)
  if (!Number.isFinite(parsed)) return 0
  return Math.round(parsed * 100)
}

/** A price in cents, written with two decimals. */
export function fromCents(cents: number): string {
  return (cents / 100).toFixed(2)
}

/** A price for a person to read. */
export function formatMoney(
  value: string | number | null | undefined,
  currency = 'USD',
): string {
  const cents = toCents(value)
  const symbol = CURRENCY_SYMBOLS[currency.toUpperCase()]
  const amount = (cents / 100).toFixed(2)
  return symbol ? `${symbol}${amount}` : `${amount} ${currency.toUpperCase()}`
}

/** A date, written the way a shop receipt writes one. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

/** A percentage, written with one decimal when it needs one. */
export function formatPercent(value: string | number): string {
  const parsed = typeof value === 'number' ? value : Number.parseFloat(value)
  if (!Number.isFinite(parsed)) return '0%'
  const rounded = Math.round(parsed * 10) / 10
  return `${rounded}%`
}

/** A short label for the stock of a product. */
export function stockLabel(stock: number): string {
  if (stock <= 0) return 'Out of stock'
  if (stock <= 3) return `Only ${stock} left`
  return 'In stock'
}
