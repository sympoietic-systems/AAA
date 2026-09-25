import { act, renderHook } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import { useTaskPolling } from "../../components/pages/researchpage/shared/useTaskPolling"
import { getResearchTask, getTaskPhase, type ResearchTask } from "../../api/research"
vi.mock("../../api/research", () => ({ getResearchTask: vi.fn(), getTaskPhase: vi.fn() }))
afterEach(() => { vi.useRealTimers(); vi.clearAllMocks() })

it("V39 polls single-flight and ignores the old task on navigation", async () => {
  vi.useFakeTimers()
  Object.defineProperty(document, "hidden", { value: false, configurable: true })
  const task = (id: string) => ({ id, status: "active" } as ResearchTask)
  let oldComplete!: (value: ResearchTask) => void
  vi.mocked(getResearchTask).mockImplementationOnce(() => new Promise(resolve => { oldComplete = resolve }))
    .mockResolvedValue(task("b"))
  vi.mocked(getTaskPhase).mockResolvedValue({ task_id: "b", phase: "planning" })
  const { result, rerender, unmount } = renderHook(({ id }) => useTaskPolling(id, "active", task(id)), { initialProps: { id: "a" } })
  await act(() => vi.advanceTimersByTimeAsync(20000))
  expect(getResearchTask).toHaveBeenCalledTimes(1)
  const firstSignal = vi.mocked(getResearchTask).mock.calls[0][1]
  rerender({ id: "b" })
  await act(async () => { oldComplete(task("a")) })
  expect(firstSignal?.aborted).toBe(true)
  expect(result.current.current.id).toBe("b")
  unmount()
  const count = vi.mocked(getResearchTask).mock.calls.length
  await act(() => vi.advanceTimersByTimeAsync(20000))
  expect(getResearchTask).toHaveBeenCalledTimes(count)
})
