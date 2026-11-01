import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { createKeyedPollingChannel, setTelemetrySession } from "../pollingChannel"
import { addNotification } from "../notificationStore"

vi.mock("../notificationStore", () => ({ addNotification: vi.fn() }))
type State = { data: number | null; loading: boolean; error: string | null }
let dispose: () => void
let visibility: ReturnType<typeof vi.spyOn>
const flush = () => vi.advanceTimersByTimeAsync(0)
function deferred() {
  let resolve!: (value: number) => void
  const promise = new Promise<number>(done => { resolve = done })
  return { promise, resolve }
}
function setup(fetcher: (key: string, signal: AbortSignal) => Promise<number>) {
  const states: Record<string, State> = {}
  const get = (key: string) => states[key] ?? { data: null, loading: false, error: null }
  const set = (key: string, state: State) => { states[key] = state }
  const channel = createKeyedPollingChannel("fixture", fetcher, 15000, key => { delete states[key] })
  dispose = channel.dispose
  return { states, subscribe: (key = "a") => channel.subscribe(key, get, set, vi.fn()), refresh: (key = "a") => channel.refresh(key, get, set) }
}
beforeEach(() => {
  vi.useFakeTimers(); vi.spyOn(Math, "random").mockReturnValue(.5)
  visibility = vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible")
  setTelemetrySession(true)
})
afterEach(() => { dispose?.(); vi.restoreAllMocks(); vi.useRealTimers(); vi.clearAllMocks() })

it("coalesces pending resubscriptions without parallel requests or timer chains", async () => {
  const first = deferred(), second = deferred()
  const fetch = vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
  const channel = setup(fetch)
  const stop = channel.subscribe(); await flush(); stop()
  const stopAgain = channel.subscribe(); await flush()
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(fetch.mock.calls[0][1].aborted).toBe(true)
  first.resolve(1); await flush()
  expect(fetch).toHaveBeenCalledTimes(2)
  second.resolve(2); await flush()
  expect(channel.states.a.data).toBe(2)
  expect(vi.getTimerCount()).toBe(1)
  stopAgain(); expect(vi.getTimerCount()).toBe(0)
})

it("queues one fresh manual request and waits for that result", async () => {
  const first = deferred(), second = deferred()
  const fetch = vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
  const channel = setup(fetch); channel.subscribe(); await flush()
  let completed = false
  const refresh = channel.refresh().then(() => { completed = true })
  const another = channel.refresh()
  first.resolve(1); await flush()
  expect(fetch).toHaveBeenCalledTimes(2); expect(completed).toBe(false)
  second.resolve(2); await flush(); await refresh; await another
  expect(channel.states.a.data).toBe(2); expect(vi.getTimerCount()).toBe(1)
})

it("pauses hidden polling and resumes once", async () => {
  const fetch = vi.fn().mockResolvedValue(3)
  const channel = setup(fetch); channel.subscribe(); await flush()
  visibility.mockReturnValue("hidden"); document.dispatchEvent(new Event("visibilitychange"))
  await vi.advanceTimersByTimeAsync(60000); expect(fetch).toHaveBeenCalledTimes(1)
  visibility.mockReturnValue("visible"); document.dispatchEvent(new Event("visibilitychange")); await flush()
  expect(fetch).toHaveBeenCalledTimes(2); expect(vi.getTimerCount()).toBe(1)
})

it("preserves the last good snapshot after later polling fails", async () => {
  const fetch = vi.fn().mockResolvedValueOnce(4).mockRejectedValueOnce(new Error("offline"))
  const channel = setup(fetch); channel.subscribe(); await flush()
  await vi.advanceTimersByTimeAsync(15000)
  expect(channel.states.a).toEqual({ data: 4, loading: false, error: "offline" })
})

it("invalidates old-session results even when abort is ignored", async () => {
  const old = deferred(), fresh = deferred()
  const fetch = vi.fn().mockReturnValueOnce(old.promise).mockReturnValueOnce(fresh.promise)
  const channel = setup(fetch); channel.subscribe(); await flush()
  setTelemetrySession(false); expect(channel.states.a.data).toBeNull()
  setTelemetrySession(true); old.resolve(9); await flush()
  expect(channel.states.a.data).toBeNull()
  fresh.resolve(7); await flush(); expect(channel.states.a.data).toBe(7)
  expect(addNotification).not.toHaveBeenCalled()
})

it("keeps conversation keys isolated and retains at most twenty idle snapshots", async () => {
  const channel = setup(async key => Number(key))
  for (let i = 0; i < 25; i++) { const stop = channel.subscribe(String(i)); await flush(); stop() }
  expect(Object.keys(channel.states)).toHaveLength(20)
  expect(channel.states["0"]).toBeUndefined(); expect(channel.states["24"].data).toBe(24)
})

it("does not dispatch an automatic request unsubscribed before dispatch", async () => {
  const fetch = vi.fn().mockResolvedValue(1)
  const channel = setup(fetch); const stop = channel.subscribe(); stop(); await flush()
  expect(fetch).not.toHaveBeenCalled(); expect(vi.getTimerCount()).toBe(0)
})
