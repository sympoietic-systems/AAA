import { afterEach, describe, expect, it, vi } from "vitest"
import { checkAuthStatus, parseAuthStatus, verifyPassword } from "../auth"
import { apiFetch } from "../http"

afterEach(() => vi.unstubAllGlobals())
describe("V36 authentication contract", () => {
  it.each([{}, null, { auth_enabled: 0 }, { auth_enabled: false }, { auth_enabled: "false", status: "authenticated" }])("fails closed for malformed status %j", data => {
    expect(parseAuthStatus(data).authenticated).toBe(false)
  })
  it("requires an explicit valid disabled response", () => {
    expect(parseAuthStatus({ auth_enabled: false, status: "authenticated" }).status).toBe("disabled")
  })
  it("rejects HTTP 200 unauthenticated without storing the password", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ auth_enabled: true, status: "unauthenticated" }))))
    expect(await verifyPassword("wrong")).toBe(false)
    expect(localStorage.getItem("aaa_password")).toBeNull()
  })
  it("fails closed on HTML and removes legacy credentials", async () => {
    localStorage.setItem("aaa_password", "legacy")
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>")))
    expect((await checkAuthStatus()).status).toBe("unavailable")
    expect(localStorage.getItem("aaa_password")).toBeNull()
  })
})
describe("V40 explicit transport", () => {
  it("preserves Request headers and cancellation without replacing fetch", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response("{}"))
    vi.stubGlobal("fetch", fetch)
    const controller = new AbortController()
    const request = new Request(`${window.location.origin}/api/test`, { headers: { "X-Test": "yes" }, signal: controller.signal })
    await apiFetch(request)
    expect(globalThis.fetch).toBe(fetch)
    const [input, options] = fetch.mock.calls[0]
    expect(input.signal).toBe(request.signal)
    expect(options.headers.get("X-Test")).toBe("yes")
    expect(options.headers.get("Authorization")).toBeNull()
    expect(options.credentials).toBe("same-origin")
    expect(options.redirect).toBe("error")
  })
  it.each(["https://evil.test/api/x", "/api/../outside", "//evil.test/api/x"])("rejects %s before fetch", async url => {
    const fetch = vi.fn()
    vi.stubGlobal("fetch", fetch)
    await expect(apiFetch(url)).rejects.toThrow("same-origin")
    expect(fetch).not.toHaveBeenCalled()
  })
})
