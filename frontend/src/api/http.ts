// Shared HTTP infrastructure — used by all API domain files.
// Protects against credential leakage by strictly validating origin and API path,
// and preserves Request headers and signals.

export const BASE = "/api"

/**
 * Checks whether an input URL target is strictly a same-origin API endpoint.
 * Disallows third-party domains (e.g. https://evil.com/api/...) from receiving credentials.
 */
export function isSameOriginApiRequest(input: RequestInfo | URL): boolean {
  try {
    let urlStr: string
    if (typeof input === "string") {
      urlStr = input
    } else if (input instanceof URL) {
      urlStr = input.toString()
    } else if (typeof Request !== "undefined" && input instanceof Request) {
      urlStr = input.url
    } else {
      return false
    }

    // Relative URLs starting with /api
    if (urlStr.startsWith("/api/") || urlStr === "/api") {
      return true
    }

    // Absolute URLs
    if (typeof window !== "undefined" && window.location?.origin) {
      const parsed = new URL(urlStr, window.location.origin)
      return (
        parsed.origin === window.location.origin &&
        (parsed.pathname.startsWith("/api/") || parsed.pathname === "/api")
      )
    }

    return false
  } catch {
    return false
  }
}

/**
 * Resolves input URL to an absolute URL string if needed, safe for both
 * browser and Node/jsdom test environments.
 */
export function resolveApiUrl(input: RequestInfo | URL): RequestInfo | URL {
  if (typeof input === "string" && input.startsWith("/")) {
    if (typeof window !== "undefined" && window.location?.origin) {
      return `${window.location.origin}${input}`
    }
  }
  return input
}

const originalFetch = typeof window !== "undefined" && window.fetch ? window.fetch.bind(window) : globalThis.fetch

/**
 * Explicit authenticated API fetch client.
 * Enforces same-origin verification, preserves Request headers, and passes abort signals.
 */
export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const isApi = isSameOriginApiRequest(input)
  const resolvedInput = resolveApiUrl(input)

  if (isApi) {
    const password = typeof localStorage !== "undefined" ? localStorage.getItem("aaa_password") : null
    const headers = new Headers()

    // 1. Inherit headers from Request object if passed
    if (typeof Request !== "undefined" && input instanceof Request) {
      input.headers.forEach((val, key) => headers.set(key, val))
    }

    // 2. Merge headers from init
    if (init?.headers) {
      new Headers(init.headers).forEach((val, key) => headers.set(key, val))
    }

    // 3. Inject Bearer token if password is set and not already specified
    if (password && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${password}`)
    }

    return originalFetch(resolvedInput, { ...init, headers })
  }

  return originalFetch(resolvedInput, init)
}

// Intercept global fetch as a safety membrane for any direct fetch calls across legacy components
if (typeof window !== "undefined") {
  window.fetch = apiFetch
}
