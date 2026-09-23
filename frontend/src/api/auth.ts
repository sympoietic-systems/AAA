import { BASE } from "./http"

export type AuthStatus = "checking" | "authenticated" | "locked" | "disabled" | "unavailable"

export interface AuthCheckResult {
  status: AuthStatus
  authenticated: boolean
  authEnabled: boolean
  error?: string
}

export async function checkAuthStatus(): Promise<AuthCheckResult> {
  try {
    const res = await fetch(`${BASE}/auth/verify`)
    if (!res.ok) {
      if (res.status === 401 || res.status === 403) {
        return { status: "locked", authenticated: false, authEnabled: true }
      }
      return { status: "unavailable", authenticated: false, authEnabled: true }
    }
    const data = await res.json().catch(() => ({}))
    const authEnabled = !!data.auth_enabled
    const authenticated = data.status === "authenticated"

    if (!authEnabled) {
      return { status: "disabled", authenticated: true, authEnabled: false }
    }

    return {
      status: authenticated ? "authenticated" : "locked",
      authenticated,
      authEnabled: true,
    }
  } catch {
    // Network failure: fail CLOSED, never treat network errors as disabled auth
    return { status: "unavailable", authenticated: false, authEnabled: true }
  }
}

export async function verifyPassword(password: string): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/auth/verify`, {
      headers: { "Authorization": `Bearer ${password}` }
    })
    return res.ok
  } catch {
    return false
  }
}

export function logout(): void {
  localStorage.removeItem("aaa_password")
}
