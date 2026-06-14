import { BASE } from "./http"

export async function checkAuthStatus(): Promise<{ authenticated: boolean; authEnabled: boolean }> {
  try {
    const res = await fetch(`${BASE}/auth/verify`)
    if (res.status === 401) {
      return { authenticated: false, authEnabled: true }
    }
    const data = await res.json().catch(() => ({}))
    return {
      authenticated: res.ok,
      authEnabled: !!data.auth_enabled,
    }
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
