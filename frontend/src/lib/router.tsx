/** A very small router.
 *
 * The app has a handful of pages, so it does not need a routing library. This
 * matches the address against a list of patterns and hands the matched
 * parameters to the page.
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

export interface RouteMatch {
  /** The pattern that matched, such as `/product/:slug`. */
  path: string
  /** The values taken from the address, such as `{ slug: 'blue-shirt' }`. */
  params: Record<string, string>
  /** The query string of the address. */
  query: URLSearchParams
}

interface RouterValue {
  route: RouteMatch
  navigate: (path: string) => void
}

const RouterContext = createContext<RouterValue | null>(null)

/** Match a pathname against a pattern such as `/product/:slug`. */
export function matchPattern(
  pattern: string,
  pathname: string,
): Record<string, string> | null {
  const expected = pattern.split('/').filter(Boolean)
  const actual = pathname.split('/').filter(Boolean)
  if (expected.length !== actual.length) return null

  const params: Record<string, string> = {}
  for (let index = 0; index < expected.length; index += 1) {
    const part = expected[index]
    const value = actual[index]
    if (part.startsWith(':')) {
      params[part.slice(1)] = decodeURIComponent(value)
    } else if (part !== value) {
      return null
    }
  }
  return params
}

export function RouterProvider({
  patterns,
  children,
}: {
  patterns: string[]
  children: ReactNode
}) {
  const [pathname, setPathname] = useState(() => window.location.pathname)
  const [search, setSearch] = useState(() => window.location.search)

  useEffect(() => {
    const onPop = () => {
      setPathname(window.location.pathname)
      setSearch(window.location.search)
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const navigate = useCallback((path: string) => {
    window.history.pushState({}, '', path)
    setPathname(window.location.pathname)
    setSearch(window.location.search)
    window.scrollTo(0, 0)
  }, [])

  const route = useMemo<RouteMatch>(() => {
    for (const pattern of patterns) {
      const params = matchPattern(pattern, pathname)
      if (params) {
        return { path: pattern, params, query: new URLSearchParams(search) }
      }
    }
    return { path: pathname, params: {}, query: new URLSearchParams(search) }
  }, [patterns, pathname, search])

  const value = useMemo(() => ({ route, navigate }), [route, navigate])

  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>
}

/** The page that matches the address, and the way to change the address. */
export function useRoute(): RouteMatch & { navigate: (path: string) => void } {
  const value = useContext(RouterContext)
  if (value === null) {
    throw new Error('useRoute has to be used inside a RouterProvider.')
  }
  return { ...value.route, navigate: value.navigate }
}
