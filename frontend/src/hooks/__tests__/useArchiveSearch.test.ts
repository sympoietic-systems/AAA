import { act, renderHook } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import { useArchiveSearch } from "../useArchiveSearch"
import { searchArchive, type SearchMatch } from "../../api/search"
vi.mock("../../api/search", () => ({ searchArchive: vi.fn() }))
afterEach(() => { vi.useRealTimers(); vi.clearAllMocks() })

it("V39 ignores older searches and results arriving after clear", async () => {
  vi.useFakeTimers()
  let resolveOld!: (value: SearchMatch[]) => void
  let resolveNew!: (value: SearchMatch[]) => void
  vi.mocked(searchArchive).mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve }))
    .mockImplementationOnce(() => new Promise(resolve => { resolveNew = resolve }))
  const { result, rerender } = renderHook(({ q }) => useArchiveSearch({ q }), { initialProps: { q: "old" } })
  await act(() => vi.advanceTimersByTimeAsync(250))
  rerender({ q: "new" })
  await act(() => vi.advanceTimersByTimeAsync(250))
  await act(async () => resolveNew([{ id: "new" } as SearchMatch]))
  await act(async () => resolveOld([{ id: "old" } as SearchMatch]))
  expect(result.current.results[0].id).toBe("new")
  rerender({ q: "" })
  expect(result.current.results).toEqual([])
  expect(result.current.loading).toBe(false)
})
