import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import { listConversations } from "../../../api/client"
import { CreasesDropdown } from "./CreasesDropdown"

vi.mock("../../../api/client", () => ({
  listConversations: vi.fn().mockResolvedValue({ conversations: [] }),
}))
vi.mock("../../../stores/notificationStore", () => ({
  useNotifications: () => [], dismissNotification: vi.fn(), clearNotificationsByType: vi.fn(),
}))
afterEach(() => { cleanup(); vi.clearAllMocks() })

it("requests conversation titles when opened, not when the page mounts", async () => {
  render(<CreasesDropdown />)
  expect(listConversations).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole("button", { name: "[creases]" }))
  await waitFor(() => expect(listConversations).toHaveBeenCalledOnce())
})

it("uses supplied conversations without an extra request", () => {
  render(<CreasesDropdown conversations={[]} />)
  fireEvent.click(screen.getByRole("button", { name: "[creases]" }))
  expect(listConversations).not.toHaveBeenCalled()
})
