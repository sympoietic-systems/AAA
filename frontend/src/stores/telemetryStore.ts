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

// Define states
export interface TelemetryStateSlice<T> {
  data: T | null
  loading: boolean
  error: string | null
}

export const metricsState: TelemetryStateSlice<MetricsResponse> = {
  data: null,
  loading: false,
  error: null
}

export const beliefsState: Record<string, TelemetryStateSlice<BeliefsResponse>> = {}
export const tokensState: Record<string, TelemetryStateSlice<TokenResponse>> = {}

export const daemonState: TelemetryStateSlice<DaemonStatusResponse> = {
  data: null,
  loading: false,
  error: null
}

export const schedulerState: TelemetryStateSlice<SchedulerStatusResponse> = {
  data: null,
  loading: false,
  error: null
}

// Listeners pools
type Listener = () => void

const metricsListeners = new Set<Listener>()
const beliefsListeners = new Map<string, Set<Listener>>()
const tokensListeners = new Map<string, Set<Listener>>()
const daemonListeners = new Set<Listener>()
const schedulerListeners = new Set<Listener>()

// Timers
let metricsTimeout: ReturnType<typeof setTimeout> | null = null
const beliefsTimeoutMap = new Map<string, ReturnType<typeof setTimeout>>()
const tokensTimeoutMap = new Map<string, ReturnType<typeof setTimeout>>()
let daemonTimeout: ReturnType<typeof setTimeout> | null = null
let schedulerTimeout: ReturnType<typeof setTimeout> | null = null

// --- Metrics Pub-Sub ---
function emitMetricsChange() {
  metricsListeners.forEach(l => l())
}

async function pollMetrics() {
  metricsState.loading = !metricsState.data
  emitMetricsChange()
  try {
    const res = await getMetrics()
    metricsState.data = res
    metricsState.error = null
  } catch (err: any) {
    metricsState.error = err.message || "Failed to fetch metrics"
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Metrics polling failure: ${metricsState.error}`,
      source: 'Telemetry.metrics'
    })
  } finally {
    metricsState.loading = false
    emitMetricsChange()
  }

  if (metricsListeners.size > 0) {
    const delay = 15000 + (Math.random() - 0.5) * 1000
    metricsTimeout = setTimeout(pollMetrics, delay)
  } else {
    metricsTimeout = null
  }
}

export function subscribeMetrics(listener: Listener) {
  metricsListeners.add(listener)
  if (metricsListeners.size === 1) {
    pollMetrics()
  }
  return () => {
    metricsListeners.delete(listener)
    if (metricsListeners.size === 0 && metricsTimeout) {
      clearTimeout(metricsTimeout)
      metricsTimeout = null
    }
  }
}

export async function refreshMetricsForce() {
  metricsState.loading = true
  emitMetricsChange()
  try {
    const res = await getMetrics()
    metricsState.data = res
    metricsState.error = null
  } catch (err: any) {
    metricsState.error = err.message || "Failed to fetch metrics"
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Metrics force refresh failure: ${metricsState.error}`,
      source: 'Telemetry.metrics'
    })
  } finally {
    metricsState.loading = false
    emitMetricsChange()
  }
}

// --- Beliefs Pub-Sub ---
function emitBeliefsChange(convId: string) {
  const list = beliefsListeners.get(convId)
  if (list) {
    list.forEach(l => l())
  }
}

async function pollBeliefs(convId: string) {
  let state = beliefsState[convId]
  if (!state) {
    state = { data: null, loading: true, error: null }
    beliefsState[convId] = state
  } else {
    state.loading = !state.data
  }
  emitBeliefsChange(convId)

  try {
    const res = await getBeliefs(convId)
    state.data = res
    state.error = null
  } catch (err: any) {
    state.error = err.message || "Failed to fetch beliefs"
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Beliefs polling failure for conversation ${convId.slice(0, 8)}: ${state.error}`,
      source: 'Telemetry.beliefs'
    })
  } finally {
    state.loading = false
    emitBeliefsChange(convId)
  }

  const list = beliefsListeners.get(convId)
  if (list && list.size > 0) {
    const delay = 15000 + (Math.random() - 0.5) * 1000
    const timeout = setTimeout(() => pollBeliefs(convId), delay)
    beliefsTimeoutMap.set(convId, timeout)
  } else {
    beliefsTimeoutMap.delete(convId)
  }
}

export function subscribeBeliefs(convId: string, listener: Listener) {
  if (!convId) return () => {}
  let list = beliefsListeners.get(convId)
  if (!list) {
    list = new Set()
    beliefsListeners.set(convId, list)
  }
  list.add(listener)
  if (list.size === 1) {
    pollBeliefs(convId)
  }
  return () => {
    const currentList = beliefsListeners.get(convId)
    if (currentList) {
      currentList.delete(listener)
      if (currentList.size === 0) {
        beliefsListeners.delete(convId)
        const timeout = beliefsTimeoutMap.get(convId)
        if (timeout) {
          clearTimeout(timeout)
          beliefsTimeoutMap.delete(convId)
        }
      }
    }
  }
}

export async function refreshBeliefsForce(convId: string) {
  if (!convId) return
  let state = beliefsState[convId]
  if (!state) {
    state = { data: null, loading: true, error: null }
    beliefsState[convId] = state
  } else {
    state.loading = true
  }
  emitBeliefsChange(convId)

  try {
    const res = await getBeliefs(convId)
    state.data = res
    state.error = null
  } catch (err: any) {
    state.error = err.message || "Failed to fetch beliefs"
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Beliefs force refresh failure for conversation ${convId.slice(0, 8)}: ${state.error}`,
      source: 'Telemetry.beliefs'
    })
  } finally {
    state.loading = false
    emitBeliefsChange(convId)
  }
}

// --- Tokens Pub-Sub ---
function emitTokensChange(convId: string) {
  const list = tokensListeners.get(convId)
  if (list) {
    list.forEach(l => l())
  }
}

async function pollTokens(convId: string) {
  let state = tokensState[convId]
  if (!state) {
    state = { data: null, loading: true, error: null }
    tokensState[convId] = state
  } else {
    state.loading = !state.data
  }
  emitTokensChange(convId)

  try {
    const res = await getTokens(convId || undefined)
    state.data = res
    state.error = null
  } catch (err: any) {
    state.error = err.message || "Failed to fetch tokens"
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Tokens polling failure: ${state.error}`,
      source: 'Telemetry.tokens'
    })
  } finally {
    state.loading = false
    emitTokensChange(convId)
  }

  const list = tokensListeners.get(convId)
  if (list && list.size > 0) {
    const delay = 15000 + (Math.random() - 0.5) * 1000
    const timeout = setTimeout(() => pollTokens(convId), delay)
    tokensTimeoutMap.set(convId, timeout)
  } else {
    tokensTimeoutMap.delete(convId)
  }
}

export function subscribeTokens(convId: string, listener: Listener) {
  const key = convId || "global"
  let list = tokensListeners.get(key)
  if (!list) {
    list = new Set()
    tokensListeners.set(key, list)
  }
  list.add(listener)
  if (list.size === 1) {
    pollTokens(convId)
  }
  return () => {
    const currentList = tokensListeners.get(key)
    if (currentList) {
      currentList.delete(listener)
      if (currentList.size === 0) {
        tokensListeners.delete(key)
        const timeout = tokensTimeoutMap.get(key)
        if (timeout) {
          clearTimeout(timeout)
          tokensTimeoutMap.delete(key)
        }
      }
    }
  }
}

export async function refreshTokensForce(convId: string) {
  const key = convId || "global"
  let state = tokensState[key]
  if (!state) {
    state = { data: null, loading: true, error: null }
    tokensState[key] = state
  } else {
    state.loading = true
  }
  emitTokensChange(key)

  try {
    const res = await getTokens(convId || undefined)
    state.data = res
    state.error = null
  } catch (err: any) {
    state.error = err.message || "Failed to fetch tokens"
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Tokens force refresh failure: ${state.error}`,
      source: 'Telemetry.tokens'
    })
  } finally {
    state.loading = false
    emitTokensChange(key)
  }
}

// --- Daemon Pub-Sub ---
function emitDaemonChange() {
  daemonListeners.forEach(l => l())
}

async function pollDaemon() {
  daemonState.loading = !daemonState.data
  emitDaemonChange()
  try {
    const res = await getDaemonStatus()
    daemonState.data = res
    daemonState.error = null
  } catch (err: any) {
    daemonState.error = err.message || "Failed to fetch daemon status"
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Daemon polling failure: ${daemonState.error}`,
      source: 'Telemetry.daemon'
    })
  } finally {
    daemonState.loading = false
    emitDaemonChange()
  }

  if (daemonListeners.size > 0) {
    const delay = 10000 + (Math.random() - 0.5) * 1000
    daemonTimeout = setTimeout(pollDaemon, delay)
  } else {
    daemonTimeout = null
  }
}

export function subscribeDaemon(listener: Listener) {
  daemonListeners.add(listener)
  if (daemonListeners.size === 1) {
    pollDaemon()
  }
  return () => {
    daemonListeners.delete(listener)
    if (daemonListeners.size === 0 && daemonTimeout) {
      clearTimeout(daemonTimeout)
      daemonTimeout = null
    }
  }
}

export async function refreshDaemonForce() {
  daemonState.loading = true
  emitDaemonChange()
  try {
    const res = await getDaemonStatus()
    daemonState.data = res
    daemonState.error = null
  } catch (err: any) {
    daemonState.error = err.message || "Failed to fetch daemon status"
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Daemon force refresh failure: ${daemonState.error}`,
      source: 'Telemetry.daemon'
    })
  } finally {
    daemonState.loading = false
    emitDaemonChange()
  }
}

// --- Scheduler Pub-Sub ---
function emitSchedulerChange() {
  schedulerListeners.forEach(l => l())
}

async function pollScheduler() {
  schedulerState.loading = !schedulerState.data
  emitSchedulerChange()
  try {
    const res = await getSchedulerStatus()
    schedulerState.data = res
    schedulerState.error = null
  } catch (err: any) {
    schedulerState.error = err.message || "Failed to fetch scheduler status"
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Scheduler polling failure: ${schedulerState.error}`,
      source: 'Telemetry.scheduler'
    })
  } finally {
    schedulerState.loading = false
    emitSchedulerChange()
  }

  if (schedulerListeners.size > 0) {
    const delay = 10000 + (Math.random() - 0.5) * 1000
    schedulerTimeout = setTimeout(pollScheduler, delay)
  } else {
    schedulerTimeout = null
  }
}

export function subscribeScheduler(listener: Listener) {
  schedulerListeners.add(listener)
  if (schedulerListeners.size === 1) {
    pollScheduler()
  }
  return () => {
    schedulerListeners.delete(listener)
    if (schedulerListeners.size === 0 && schedulerTimeout) {
      clearTimeout(schedulerTimeout)
      schedulerTimeout = null
    }
  }
}

export async function refreshSchedulerForce() {
  schedulerState.loading = true
  emitSchedulerChange()
  try {
    const res = await getSchedulerStatus()
    schedulerState.data = res
    schedulerState.error = null
  } catch (err: any) {
    schedulerState.error = err.message || "Failed to fetch scheduler status"
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Scheduler force refresh failure: ${schedulerState.error}`,
      source: 'Telemetry.scheduler'
    })
  } finally {
    schedulerState.loading = false
    emitSchedulerChange()
  }
}
