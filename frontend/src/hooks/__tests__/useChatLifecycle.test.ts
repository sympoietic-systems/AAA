import { act, renderHook, waitFor } from "@testing-library/react"
import { expect, it, vi } from "vitest"
import { useChat } from "../useChat"
import { getHistory, getMessagePath, type ChatMessage } from "../../api/client"

vi.mock("../../api/client", () => ({
  getAgent: vi.fn().mockResolvedValue({ name: "agent" }),
  getHistory: vi.fn(), getMessagePath: vi.fn(),
  getConversationTree: vi.fn().mockResolvedValue({ nodes: [], links: [] }),
  saveMessage: vi.fn(), generateResponse: vi.fn(), commitBranch: vi.fn(),
}))
vi.mock("../../stores/notificationStore", () => ({ addNotification: vi.fn(), dismissByMatch: vi.fn() }))
vi.mock("../useConversationFiles", () => ({ useConversationFiles: () => ({ files: [], isIndexing: false, error: null }) }))

it("V39 rejects message-path completion from the previous conversation", async () => {
  window.history.replaceState(null, "", "/?c=a")
  const message = (id: number) => ({ id, speaker: "human", content: "text" } as ChatMessage)
  vi.mocked(getHistory).mockImplementation(async (_limit, _offset, id) => ({ messages: [message(id === "a" ? 1 : 2)] } as Awaited<ReturnType<typeof getHistory>>))
  let complete!: (messages: ChatMessage[]) => void
  vi.mocked(getMessagePath).mockImplementation(() => new Promise(resolve => { complete = resolve }))
  const { result, rerender, unmount } = renderHook(({ id }) => useChat(id), { initialProps: { id: "a" } })
  await waitFor(() => expect(result.current.activeMessageId).toBe(1))
  let navigation!: Promise<void>
  act(() => { navigation = result.current.navigateToMessage(9) })
  window.history.replaceState(null, "", "/?c=b")
  rerender({ id: "b" })
  await waitFor(() => expect(result.current.activeMessageId).toBe(2))
  await act(async () => { complete([message(9)]); await navigation })
  expect(result.current.fullTreeMessages.map(item => item.id)).toEqual([2])
  expect(result.current.activeMessageId).toBe(2)
  unmount()
})
