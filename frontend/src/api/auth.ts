import { BASE } from "./http"

export async function checkAuthStatus(): Promise<{ authenticated: boolean; authEnabled: boolean }> {
  try {
    const res = await fetch(`${BASE}/auth/verify`)
    const data = await res.json().catch(() => ({}))
    const authEnabled = !!data.auth_enabled
    const authenticated = data.status === "authenticated"
    return { authenticated, authEnabled }
  } catch {
    return { authenticated: true, authEnabled: false }
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
