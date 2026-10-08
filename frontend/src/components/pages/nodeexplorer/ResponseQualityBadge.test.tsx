import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { ResponseQualityBadge } from "./ResponseQualityBadge"
import { apiFetch } from "../../../api/http"

vi.mock("../../../api/http", () => ({ BASE: "/api", apiFetch: vi.fn() }))
vi.mock("../../../stores/notificationStore", () => ({ syncNotifications: vi.fn() }))
afterEach(() => { cleanup(); vi.resetAllMocks() })
const quality = { status: "degraded" as const, content_hash: "a".repeat(64), source: "jev", reason: "jev_assessment", confidence: .95, excluded_from_context: true }

describe("response quality review", () => {
  it("shows a visible warning when a degraded status has no quality receipt", () => {
    render(<ResponseQualityBadge messageId={3996} status="degraded" />)
    expect(screen.getByRole("note", { name: "Degraded response warning" })).toBeTruthy()
    expect(screen.getByText("Excluded from generation context")).toBeTruthy()
  })

  it("shows exclusion and restores context only after a successful manual review", async () => {
    vi.mocked(apiFetch).mockResolvedValue(new Response(JSON.stringify({ ...quality, status: "sound", source: "manual", excluded_from_context: false })))
    render(<ResponseQualityBadge messageId={3996} quality={quality} />)
    expect(screen.getByText("Excluded from generation context")).toBeTruthy()
    fireEvent.click(screen.getByRole("button", { name: "Mark sound and include" }))
    await waitFor(() => expect(screen.getByText("Available to generation context")).toBeTruthy())
    expect(apiFetch).toHaveBeenCalledWith("/api/messages/3996/quality", expect.objectContaining({ method: "PATCH", body: expect.stringContaining(quality.content_hash) }))
    expect(screen.getByRole("button", { name: "Mark degraded and exclude" })).toBeTruthy()
  })
  it("retains exclusion when the content hash is stale", async () => {
    vi.mocked(apiFetch).mockResolvedValue(new Response("", { status: 409 }))
    render(<ResponseQualityBadge messageId={3996} quality={quality} />)
    fireEvent.click(screen.getByRole("button", { name: "Mark sound and include" }))
    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy())
    expect(screen.getByText("Excluded from generation context")).toBeTruthy()
  })
})
