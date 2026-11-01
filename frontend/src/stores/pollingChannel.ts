import { addNotification } from "./notificationStore"

interface Snapshot<T> { data: T | null; loading: boolean; error: string | null }
type Listener = () => void
interface Entry<T> {
  key: string; listeners: Set<Listener>; get: () => Snapshot<T>; set: (value: Snapshot<T>) => void
  timer?: ReturnType<typeof setTimeout>; controller?: AbortController; flight?: Promise<void>
  manual: boolean; automatic: boolean; resume: boolean; epoch: number; touched: number
}
let active = true
const resets = new Set<() => void>()

export function setTelemetrySession(enabled: boolean) {
  if (enabled === active) return
  active = enabled
  resets.forEach(reset => reset())
}

/** Request ownership is retained until settlement, even when a transport ignores abort. */
export function createKeyedPollingChannel<T>(
  name: string, fetcher: (key: string, signal: AbortSignal) => Promise<T>, interval: number,
  evict: (key: string) => void = () => {},
) {
  const entries = new Map<string, Entry<T>>()
  let clock = 0
  const visible = () => document.visibilityState !== "hidden"
  const emit = (entry: Entry<T>) => entry.listeners.forEach(listener => listener())
  const clearTimer = (entry: Entry<T>) => { clearTimeout(entry.timer); entry.timer = undefined }

  function trim() {
    const idle = [...entries.values()].filter(entry => !entry.listeners.size && !entry.flight)
      .sort((a, b) => a.touched - b.touched)
    for (const entry of idle.slice(0, Math.max(0, idle.length - 20))) {
      entries.delete(entry.key); evict(entry.key)
    }
  }

  function schedule(entry: Entry<T>) {
    clearTimer(entry)
    if (!active || !visible() || !entry.listeners.size) return
    entry.timer = setTimeout(() => { entry.timer = undefined; void request(entry, false) }, interval + (Math.random() - .5) * 1000)
  }

  function request(entry: Entry<T>, manual: boolean): Promise<void> {
    clearTimer(entry)
    if (!active) return Promise.resolve()
    if (entry.flight) {
      if (manual) entry.manual = true
      else if (entry.controller?.signal.aborted) entry.resume = true
      return entry.flight
    }
    entry.manual = manual
    entry.flight = Promise.resolve().then(async () => {
      do {
        if (!active || (!entry.manual && (!visible() || !entry.listeners.size))) return
        entry.automatic = !entry.manual; entry.manual = false; entry.resume = false
        const epoch = entry.epoch
        const controller = new AbortController()
        entry.controller = controller
        const current = entry.get()
        entry.set({ ...current, loading: !entry.automatic || !current.data }); emit(entry)
        try {
          const data = await fetcher(entry.key, controller.signal)
          if (!controller.signal.aborted && active && entry.epoch === epoch) {
            entry.set({ data, loading: false, error: null }); emit(entry)
          }
        } catch (error) {
          if (!controller.signal.aborted && active && entry.epoch === epoch) {
            const message = error instanceof Error ? error.message : `Failed to fetch ${name}`
            entry.set({ data: entry.get().data, loading: false, error: message }); emit(entry)
            addNotification({ type: "glitch", snippet: `Telemetry: ${name}: ${message}`, source: `Telemetry.${name}` })
          }
        } finally {
          entry.controller = undefined
          if (entry.epoch === epoch && controller.signal.aborted) {
            entry.set({ ...entry.get(), loading: false }); emit(entry)
          }
        }
      } while (active && (entry.manual || (entry.resume && visible() && entry.listeners.size > 0)))
    }).finally(() => {
      entry.flight = undefined; entry.touched = ++clock
      schedule(entry); trim()
    })
    return entry.flight
  }

  function bind(key: string, get: (key: string) => Snapshot<T>, set: (key: string, value: Snapshot<T>) => void) {
    let entry = entries.get(key)
    if (!entry) {
      entry = { key, get: () => get(key), set: value => set(key, value), listeners: new Set(),
        manual: false, automatic: true, resume: false, epoch: 0, touched: ++clock }
      entries.set(key, entry)
    }
    entry.touched = ++clock
    return entry
  }

  function visibility() {
    for (const entry of entries.values()) {
      clearTimer(entry)
      if (!visible()) {
        entry.resume = false
        if (entry.automatic) entry.controller?.abort()
      } else if (active && entry.listeners.size) {
        if (entry.flight) entry.resume = true
        else void request(entry, false)
      }
    }
  }

  function reset() {
    for (const entry of entries.values()) {
      entry.epoch++; clearTimer(entry); entry.controller?.abort()
      entry.manual = false; entry.resume = active && entry.listeners.size > 0
      entry.set({ data: null, loading: false, error: null }); emit(entry)
      if (active && visible() && entry.listeners.size && !entry.flight) void request(entry, false)
    }
  }
  resets.add(reset)
  document.addEventListener("visibilitychange", visibility)

  return {
    subscribe(key: string, get: (key: string) => Snapshot<T>, set: (key: string, value: Snapshot<T>) => void, listener: Listener) {
      if (!key) return () => {}
      const entry = bind(key, get, set)
      entry.listeners.add(listener)
      if (entry.listeners.size === 1 && active && visible()) {
        void request(entry, false)
        // Publish the initial loading snapshot synchronously for existing subscribers.
        if (!entry.get().data) { entry.set({ ...entry.get(), loading: true }); emit(entry) }
      }
      return () => {
        entry.listeners.delete(listener)
        if (!entry.listeners.size) {
          clearTimer(entry); entry.resume = false
          if (entry.automatic) entry.controller?.abort()
          entry.touched = ++clock; trim()
        }
      }
    },
    refresh(key: string, get: (key: string) => Snapshot<T>, set: (key: string, value: Snapshot<T>) => void) {
      return key ? request(bind(key, get, set), true) : Promise.resolve()
    },
    dispose() {
      resets.delete(reset); document.removeEventListener("visibilitychange", visibility)
      for (const entry of entries.values()) { entry.epoch++; clearTimer(entry); entry.controller?.abort(); entry.listeners.clear(); entry.manual = false; entry.resume = false }
      entries.clear()
    },
  }
}
