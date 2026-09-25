import { act, renderHook, waitFor } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import { useConversationFiles } from "../useConversationFiles"
import { getConversationFiles, uploadFiles } from "../../api/conversations"
vi.mock("../../api/conversations", () => ({ getConversationFiles: vi.fn(), uploadFiles: vi.fn(), deleteConversationFile: vi.fn(), reprocessFile: vi.fn() }))
vi.mock("../../stores/notificationStore", () => ({ addNotification: vi.fn() }))
afterEach(() => vi.clearAllMocks())

it("V39 keeps a pending upload out of the next conversation", async () => {
  type Files = Awaited<ReturnType<typeof getConversationFiles>>
  vi.mocked(getConversationFiles).mockResolvedValue({ files: [] } as unknown as Files)
  let finish!: (value: Awaited<ReturnType<typeof uploadFiles>>) => void
  vi.mocked(uploadFiles).mockImplementation(() => new Promise(resolve => { finish = resolve }))
  const { result, rerender } = renderHook(({ id }) => useConversationFiles(id, vi.fn()), { initialProps: { id: "a" } })
  await waitFor(() => expect(getConversationFiles).toHaveBeenCalled())
  let operation!: Promise<string | null>
  act(() => { operation = result.current.upload([new File(["text"], "note.txt")]) })
  expect(result.current.isIndexing).toBe(true)
  rerender({ id: "b" })
  await act(async () => {
    finish({ conversation_id: "a", files: [{ file_name: "a.txt", status: "ready" }] } as Awaited<ReturnType<typeof uploadFiles>>)
    await operation
  })
  expect(result.current.files).toEqual([])
  expect(result.current.isIndexing).toBe(false)
})
