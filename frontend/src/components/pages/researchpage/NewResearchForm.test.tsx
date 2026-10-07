import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react"
import { afterEach, describe, it, expect, vi } from "vitest"
import { NewResearchForm } from "./NewResearchForm"

vi.mock("../../../api/research", () => ({ listIndexedFiles: vi.fn().mockResolvedValue({ files: [] }) }))
vi.mock("../../../api/conversations", () => ({
  listConversations: vi.fn().mockResolvedValue({ conversations: [] }),
  uploadFiles: vi.fn(), getConversationFiles: vi.fn(),
}))
afterEach(cleanup)
describe("dispatch branching consent", () => {
  it.each([false, true])("uses the checkbox choice %s", async (enabled) => {
    const dispatch = vi.fn().mockResolvedValue("task")
    render(<NewResearchForm onDispatch={dispatch} onClose={vi.fn()} />)
    const checkbox = screen.getByRole("checkbox", { name: "Allow branching" })
    expect(checkbox).not.toBeChecked()
    if (enabled) fireEvent.click(checkbox)
    fireEvent.change(screen.getByPlaceholderText("What should we investigate?"), { target: { value: "Compare evidence" } })
    fireEvent.submit(checkbox.closest("form")!)
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith(expect.objectContaining({
      subresearch_policy: enabled ? "bounded_auto" : "off",
    })))
  })
})
