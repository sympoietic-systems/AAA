import { act, renderHook, waitFor } from "@testing-library/react"
import { beforeEach, expect, it, vi } from "vitest"
import { useNotes } from "../useNotes"
import { createNote, getNotes, type NoteInfo } from "../../api/notes"
vi.mock("../../api/notes", () => ({ getNotes: vi.fn(), createNote: vi.fn(), updateNote: vi.fn(), deleteNote: vi.fn() }))
vi.mock("../../stores/notificationStore", () => ({ addNotification: vi.fn() }))
beforeEach(() => { vi.clearAllMocks(); vi.mocked(getNotes).mockResolvedValue([]) })

it("V39 does not append a completed mutation to a different asset", async () => {
  let complete!: (note: NoteInfo) => void
  vi.mocked(createNote).mockImplementation(() => new Promise(resolve => { complete = resolve }))
  const { result, rerender } = renderHook(({ id }) => useNotes("research_task", id), { initialProps: { id: "a" } })
  await waitFor(() => expect(result.current.loading).toBe(false))
  let operation!: Promise<NoteInfo | null>
  act(() => { operation = result.current.addNote("text") })
  rerender({ id: "b" })
  await waitFor(() => expect(result.current.loading).toBe(false))
  await act(async () => { complete({ id: "a-note" } as NoteInfo); await operation })
  expect(result.current.notes).toEqual([])
})

it("V39 ignores an older read after a successful note mutation", async () => {
  let completeRead!: (notes: NoteInfo[]) => void
  vi.mocked(getNotes).mockImplementation(() => new Promise(resolve => { completeRead = resolve }))
  vi.mocked(createNote).mockResolvedValue({ id: "new" } as NoteInfo)
  const { result } = renderHook(() => useNotes("research_task", "a"))
  await waitFor(() => expect(getNotes).toHaveBeenCalled())
  await act(() => result.current.addNote("text"))
  await act(async () => completeRead([]))
  expect(result.current.notes.map(note => note.id)).toEqual(["new"])
})
