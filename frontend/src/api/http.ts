export const BASE = "/api"
export const SESSION_EXPIRED_EVENT = "aaa:session-expired"

export function resolveApiUrl(input: RequestInfo | URL): RequestInfo | URL {
  return typeof input === "string" ? new URL(input, window.location.origin) : input
}

export function isSameOriginApiRequest(input: RequestInfo | URL): boolean {
  try {
    const url = new URL(input instanceof Request ? input.url : String(input), window.location.origin)
    return url.origin === window.location.origin && (url.pathname === BASE || url.pathname.startsWith(`${BASE}/`))
  } catch {
    return false
  }
}

/** Explicit transport; global fetch stays untouched and redirects cannot carry credentials. */
export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  if (!isSameOriginApiRequest(input)) throw new Error("API requests must target a same-origin /api endpoint")
  const headers = new Headers(input instanceof Request ? input.headers : undefined)
  new Headers(init?.headers).forEach((value, key) => headers.set(key, value))
  headers.set("X-AAA-CSRF", "1")
  const response = await globalThis.fetch(resolveApiUrl(input), {
    ...init, headers, credentials: "same-origin", redirect: "error",
  })
  const url = new URL(input instanceof Request ? input.url : String(input), window.location.origin)
  if (response.status === 401 && !url.pathname.startsWith("/api/auth/")) {
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT))
  }
  return response
}

export class ApiError extends Error {
  status: number
  kind?: string
  constructor(status: number, message: string, kind?: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.kind = kind
  }
}

export async function apiJson<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const response = await apiFetch(input, init)
  if (!response.ok) {
    const data: unknown = await response.json().catch(() => null)
    const body = data && typeof data === "object" ? data as Record<string, unknown> : {}
    throw new ApiError(response.status, typeof body.message === "string" ? body.message : `Request failed (${response.status})`,
      typeof body.kind === "string" ? body.kind : undefined)
  }
  return response.json() as Promise<T>
}
