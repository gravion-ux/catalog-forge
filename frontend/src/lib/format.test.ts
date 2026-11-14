/** Checks for the formatting helpers.
 *
 * These run through the type checker only: the money logic itself is covered
 * by the backend tests. This file is here so the helpers stay honest about the
 * types they promise.
 */

import { formatMoney, formatPercent, fromCents, stockLabel, toCents } from './format'

function check(actual: unknown, expected: unknown, label: string): void {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${String(expected)}, got ${String(actual)}`)
  }
}

check(toCents('12.34'), 1234, 'toCents reads a string price')
check(toCents(12.34), 1234, 'toCents reads a number price')
check(toCents(null), 0, 'toCents treats nothing as zero')
check(toCents('not a price'), 0, 'toCents rejects rubbish')
check(fromCents(1234), '12.34', 'fromCents writes two decimals')
check(fromCents(0), '0.00', 'fromCents writes zero with decimals')
check(formatMoney('12.34', 'USD'), '$12.34', 'formatMoney writes a dollar sign')
check(formatMoney('12.34', 'EUR'), '€12.34', 'formatMoney writes a euro sign')
check(formatMoney('12.34', 'GBP'), '£12.34', 'formatMoney writes a pound sign')
check(formatMoney('12.34', 'INR'), '₹12.34', 'formatMoney writes a rupee sign')
check(formatMoney('12.34', 'JPY'), '12.34 JPY', 'formatMoney falls back to the code')
check(formatPercent('12.34'), '12.3%', 'formatPercent keeps one decimal')
check(formatPercent('12'), '12%', 'formatPercent drops a whole decimal')
check(stockLabel(0), 'Out of stock', 'stockLabel says out of stock')
check(stockLabel(2), 'Only 2 left', 'stockLabel says only a few left')
check(stockLabel(10), 'In stock', 'stockLabel says in stock')
