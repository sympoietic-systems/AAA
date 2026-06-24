import {
  getMetrics,
  getBeliefs,
  getDaemonStatus,
  getSchedulerStatus,
  getTokens,
  type MetricsResponse,
  type BeliefsResponse,
  type DaemonStatusResponse,
  type SchedulerStatusResponse,
  type TokenResponse
} from "../api/client"
import { addNotification } from "./notificationStore"

export interface TelemetryStateSlice<T> {
  data: T | null
  loading: boolean
  error: string | null
}

type Listener = () => void

// --- Simple (non-keyed) channel: single state variable ---

function createPollingChannel<T>(
  name: string,
  fetcher: () => Promise<T>,
  interval: number,
) {
  const listeners = new Set<Listener>()
  let timeout: ReturnType<typeof setTimeout> | null = null

  function emit() {
    listeners.forEach((l) => l())
  }

  async function poll(state: TelemetryStateSlice<T>, setState: (v: TelemetryStateSlice<T>) => void) {
    setState({ data: state.data, loading: !state.data, error: state.error })
    emit()
    try {
      const res = await fetcher()
      setState({ data: res, loading: false, error: null })
    } catch (err: any) {
      const errorMsg = err.message || `Failed to fetch ${name}`
      setState({ data: state.data, loading: false, error: errorMsg })
      addNotification({
        type: 'glitch',
        snippet: `Telemetry: ${name} polling failure: ${errorMsg}`,
        source: `Telemetry.${name}`
      })
    }
    emit()

    if (listeners.size > 0) {
      const delay = interval + (Math.random() - 0.5) * 1000
      timeout = setTimeout(() => {
        poll(state, setState)
      }, delay)
    } else {
      timeout = null
    }
  }

  function subscribe(
    getState: () => TelemetryStateSlice<T>,
    setState: (v: TelemetryStateSlice<T>) => void,
    listener: Listener,
  ) {
    listeners.add(listener)
    if (listeners.size === 1) {
      poll(getState(), setState)
    }
    return () => {
      listeners.delete(listener)
      if (listeners.size === 0 && timeout) {
        clearTimeout(timeout)
        timeout = null
      }
    }
  }

  async function refresh(
    getState: () => TelemetryStateSlice<T>,
    setState: (v: TelemetryStateSlice<T>) => void,
  ) {
    const current = getState()
    setState({ data: current.data, loading: true, error: current.error })
    emit()
    try {
      const res = await fetcher()
      setState({ data: res, loading: false, error: null })
    } catch (err: any) {
      const errorMsg = err.message || `Failed to fetch ${name}`
      setState({ data: current.data, loading: false, error: errorMsg })
      addNotification({
        type: 'glitch',
        snippet: `Telemetry: ${name} force refresh failure: ${errorMsg}`,
        source: `Telemetry.${name}`
      })
    }
    emit()
  }

  return { subscribe, refresh }
}

// --- Keyed channel: per-conversation state map ---

function createKeyedPollingChannel<T>(
  name: string,
  fetcher: (key: string) => Promise<T>,
  interval: number,
) {
  const listenersMap = new Map<string, Set<Listener>>()
  const timeoutMap = new Map<string, ReturnType<typeof setTimeout>>()

  function emit(key: string) {
    const list = listenersMap.get(key)
    if (list) list.forEach((l) => l())
  }

  async function poll(
    key: string,
    getState: (k: string) => TelemetryStateSlice<T>,
    setState: (k: string, v: TelemetryStateSlice<T>) => void,
  ) {
    const state = getState(key)
    setState(key, { data: state.data, loading: !state.data, error: state.error })
    emit(key)
    try {
      const res = await fetcher(key)
      setState(key, { data: res, loading: false, error: null })
    } catch (err: any) {
      const errorMsg = err.message || `Failed to fetch ${name}`
      setState(key, { data: getState(key)?.data ?? null, loading: false, error: errorMsg })
      addNotification({
        type: 'glitch',
        snippet: `Telemetry: ${name} polling failure for conversation ${key.slice(0, 8)}: ${errorMsg}`,
        source: `Telemetry.${name}`
      })
    }
    emit(key)

    const list = listenersMap.get(key)
    if (list && list.size > 0) {
      const delay = interval + (Math.random() - 0.5) * 1000
      const t = setTimeout(() => poll(key, getState, setState), delay)
      timeoutMap.set(key, t)
    } else {
      timeoutMap.delete(key)
    }
  }

  function subscribe(
    key: string,
    getState: (k: string) => TelemetryStateSlice<T>,
    setState: (k: string, v: TelemetryStateSlice<T>) => void,
    listener: Listener,
  ) {
    if (!key) return () => {}
    let list = listenersMap.get(key)
    if (!list) {
      list = new Set()
      listenersMap.set(key, list)
    }
    list.add(listener)
    if (list.size === 1) {
      poll(key, getState, setState)
    }
    return () => {
      const currentList = listenersMap.get(key)
      if (currentList) {
        currentList.delete(listener)
        if (currentList.size === 0) {
          listenersMap.delete(key)
          const t = timeoutMap.get(key)
          if (t) {
            clearTimeout(t)
            timeoutMap.delete(key)
          }
        }
      }
    }
  }

  async function refresh(
    key: string,
    getState: (k: string) => TelemetryStateSlice<T>,
    setState: (k: string, v: TelemetryStateSlice<T>) => void,
  ) {
    if (!key) return
    const current = getState(key)
    setState(key, { data: current.data, loading: true, error: current.error })
    emit(key)
    try {
      const res = await fetcher(key)
      setState(key, { data: res, loading: false, error: null })
    } catch (err: any) {
      const errorMsg = err.message || `Failed to fetch ${name}`
      setState(key, { data: getState(key)?.data ?? null, loading: false, error: errorMsg })
      addNotification({
        type: 'glitch',
        snippet: `Telemetry: ${name} force refresh failure for conversation ${key.slice(0, 8)}: ${errorMsg}`,
        source: `Telemetry.${name}`
      })
    }
    emit(key)
  }

  return { subscribe, refresh }
}

// --- Metrics ---
export let metricsState: TelemetryStateSlice<MetricsResponse> = { data: null, loading: false, error: null }

const metricsChan = createPollingChannel<MetricsResponse>("metrics", getMetrics, 15000)

export function subscribeMetrics(listener: Listener) {
  return metricsChan.subscribe(
    () => metricsState,
    (v) => { metricsState = v },
    listener,
  )
}

export function refreshMetricsForce() {
  return metricsChan.refresh(
    () => metricsState,
    (v) => { metricsState = v },
  )
}

// --- Beliefs ---
export const beliefsState: Record<string, TelemetryStateSlice<BeliefsResponse>> = {}

const beliefsChan = createKeyedPollingChannel<BeliefsResponse>("beliefs", getBeliefs, 15000)

export function subscribeBeliefs(convId: string, listener: Listener) {
  return beliefsChan.subscribe(
    convId,
    (k) => beliefsState[k] || { data: null, loading: false, error: null },
    (k, v) => { beliefsState[k] = v },
    listener,
  )
}

export function refreshBeliefsForce(convId: string) {
  return beliefsChan.refresh(
    convId,
    (k) => beliefsState[k] || { data: null, loading: false, error: null },
    (k, v) => { beliefsState[k] = v },
  )
}

// --- Tokens ---
export const tokensState: Record<string, TelemetryStateSlice<TokenResponse>> = {}

const tokensChan = createKeyedPollingChannel<TokenResponse>("tokens", (key) => getTokens(key || undefined), 15000)

export function subscribeTokens(convId: string, listener: Listener) {
  const key = convId || "global"
  return tokensChan.subscribe(
    key,
    (k) => tokensState[k] || { data: null, loading: false, error: null },
    (k, v) => { tokensState[k] = v },
    listener,
  )
}

export function refreshTokensForce(convId: string) {
  const key = convId || "global"
  return tokensChan.refresh(
    key,
    (k) => tokensState[k] || { data: null, loading: false, error: null },
    (k, v) => { tokensState[k] = v },
  )
}

// --- Daemon ---
export let daemonState: TelemetryStateSlice<DaemonStatusResponse> = { data: null, loading: false, error: null }

const daemonChan = createPollingChannel<DaemonStatusResponse>("daemon", getDaemonStatus, 10000)

export function subscribeDaemon(listener: Listener) {
  return daemonChan.subscribe(
    () => daemonState,
    (v) => { daemonState = v },
    listener,
  )
}

export function refreshDaemonForce() {
  return daemonChan.refresh(
    () => daemonState,
    (v) => { daemonState = v },
  )
}

// --- Scheduler ---
export let schedulerState: TelemetryStateSlice<SchedulerStatusResponse> = { data: null, loading: false, error: null }

const schedulerChan = createPollingChannel<SchedulerStatusResponse>("scheduler", getSchedulerStatus, 10000)

export function subscribeScheduler(listener: Listener) {
  return schedulerChan.subscribe(
    () => schedulerState,
    (v) => { schedulerState = v },
    listener,
  )
}

export function refreshSchedulerForce() {
  return schedulerChan.refresh(
    () => schedulerState,
    (v) => { schedulerState = v },
  )
}
