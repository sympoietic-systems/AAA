import { apiFetch, BASE } from "./http"

export type AuthStatus = "checking" | "authenticated" | "locked" | "disabled" | "unavailable"
export interface AuthCheckResult {
  status: AuthStatus
  authenticated: boolean
  authEnabled: boolean
  error?: string
}
const unavailable: AuthCheckResult = { status: "unavailable", authenticated: false, authEnabled: true }

export function parseAuthStatus(data: unknown): AuthCheckResult {
  if (!data || typeof data !== "object") return unavailable
  const body = data as Record<string, unknown>
  if (typeof body.auth_enabled !== "boolean" || !["authenticated", "unauthenticated"].includes(String(body.status))) return unavailable
  if (!body.auth_enabled) {
    return body.status === "authenticated" ? { status: "disabled", authenticated: true, authEnabled: false } : unavailable
  }
  const authenticated = body.status === "authenticated"
  return { status: authenticated ? "authenticated" : "locked", authenticated, authEnabled: true }
}

export async function checkAuthStatus(): Promise<AuthCheckResult> {
  localStorage.removeItem("aaa_password")
  try {
    const res = await apiFetch(`${BASE}/auth/verify`, { cache: "no-store" })
    if (res.status === 401 || res.status === 403) return { status: "locked", authenticated: false, authEnabled: true }
    return res.ok ? parseAuthStatus(await res.json()) : unavailable
  } catch {
    return unavailable
  }
}

export async function verifyPassword(password: string): Promise<boolean> {
  const res = await apiFetch(`${BASE}/auth/session`, { method: "POST", headers: { Authorization: `Bearer ${password}` } })
  if (res.status === 401 || res.status === 403) return false
  if (!res.ok) throw new Error("Unable to reach the authentication service")
  const result = parseAuthStatus(await res.json())
  if (result.status === "unavailable") throw new Error("Invalid authentication response")
  return result.authenticated
}

export async function logout(): Promise<void> {
  const res = await apiFetch(`${BASE}/auth/session`, { method: "DELETE" })
  if (!res.ok && res.status !== 401) throw new Error("Unable to end the session. Please retry.")
  localStorage.removeItem("aaa_password")
}
