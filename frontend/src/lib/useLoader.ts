/** Loading data from the API with the three states a page has to handle. */

import { useCallback, useEffect, useState } from 'react'
import { ApiError } from './api'

export interface LoaderState<T> {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => void
}

export function useLoader<T>(
  load: () => Promise<T>,
  deps: readonly unknown[],
): LoaderState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    load()
      .then((result) => {
        if (cancelled) return
        setData(result)
        setError(null)
      })
      .catch((cause: unknown) => {
        if (cancelled) return
        setError(
          cause instanceof ApiError
            ? cause.message
            : 'Something went wrong while loading this page.',
        )
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [...deps, attempt])

  const reload = useCallback(() => setAttempt((value) => value + 1), [])

  return { data, error, loading, reload }
}
