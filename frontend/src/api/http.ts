// Shared HTTP infrastructure — used by all API domain files.
// This file is imported by client.ts which re-exports everything
// for backward compatibility.

export const BASE = "/api"

// Intercept global fetch to automatically inject AAA_PASSWORD header for API requests
const originalFetch = window.fetch
window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
  const urlStr = typeof input === "string" ? input : input instanceof URL ? input.toString() : (input as Request).url
  if (urlStr.includes("/api/")) {
    const password = localStorage.getItem("aaa_password")
    if (password) {
      const headers = new Headers(init?.headers || {})
      if (!headers.has("Authorization")) {
        headers.set("Authorization", `Bearer ${password}`)
      }
      return originalFetch(input, { ...init, headers })
    }
  }
  return originalFetch(input, init)
}
