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

export let metricsState: TelemetryStateSlice<MetricsResponse> = {
  data: null,
  loading: false,
  error: null
}

export const beliefsState: Record<string, TelemetryStateSlice<BeliefsResponse>> = {}
export const tokensState: Record<string, TelemetryStateSlice<TokenResponse>> = {}

export let daemonState: TelemetryStateSlice<DaemonStatusResponse> = {
  data: null,
  loading: false,
  error: null
}

export let schedulerState: TelemetryStateSlice<SchedulerStatusResponse> = {
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
  metricsState = { data: metricsState.data, loading: !metricsState.data, error: metricsState.error }
  emitMetricsChange()
  try {
    const res = await getMetrics()
    metricsState = { data: res, loading: false, error: null }
  } catch (err: any) {
    const errorMsg = err.message || "Failed to fetch metrics"
    metricsState = { data: metricsState.data, loading: false, error: errorMsg }
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Metrics polling failure: ${errorMsg}`,
      source: 'Telemetry.metrics'
    })
  }
  emitMetricsChange()

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
  metricsState = { data: metricsState.data, loading: true, error: metricsState.error }
  emitMetricsChange()
  try {
    const res = await getMetrics()
    metricsState = { data: res, loading: false, error: null }
  } catch (err: any) {
    const errorMsg = err.message || "Failed to fetch metrics"
    metricsState = { data: metricsState.data, loading: false, error: errorMsg }
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Metrics force refresh failure: ${errorMsg}`,
      source: 'Telemetry.metrics'
    })
  }
  emitMetricsChange()
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
  }
  beliefsState[convId] = { data: state.data, loading: !state.data, error: state.error }
  emitBeliefsChange(convId)

  try {
    const res = await getBeliefs(convId)
    beliefsState[convId] = { data: res, loading: false, error: null }
  } catch (err: any) {
    const errorMsg = err.message || "Failed to fetch beliefs"
    beliefsState[convId] = { data: beliefsState[convId]?.data ?? null, loading: false, error: errorMsg }
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Beliefs polling failure for conversation ${convId.slice(0, 8)}: ${errorMsg}`,
      source: 'Telemetry.beliefs'
    })
  }
  emitBeliefsChange(convId)

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
  }
  beliefsState[convId] = { data: state.data, loading: true, error: state.error }
  emitBeliefsChange(convId)

  try {
    const res = await getBeliefs(convId)
    beliefsState[convId] = { data: res, loading: false, error: null }
  } catch (err: any) {
    const errorMsg = err.message || "Failed to fetch beliefs"
    beliefsState[convId] = { data: beliefsState[convId]?.data ?? null, loading: false, error: errorMsg }
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Beliefs force refresh failure for conversation ${convId.slice(0, 8)}: ${errorMsg}`,
      source: 'Telemetry.beliefs'
    })
  }
  emitBeliefsChange(convId)
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
  }
  tokensState[convId] = { data: state.data, loading: !state.data, error: state.error }
  emitTokensChange(convId)

  try {
    const res = await getTokens(convId || undefined)
    tokensState[convId] = { data: res, loading: false, error: null }
  } catch (err: any) {
    const errorMsg = err.message || "Failed to fetch tokens"
    tokensState[convId] = { data: tokensState[convId]?.data ?? null, loading: false, error: errorMsg }
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Tokens polling failure: ${errorMsg}`,
      source: 'Telemetry.tokens'
    })
  }
  emitTokensChange(convId)

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
  }
  tokensState[key] = { data: state.data, loading: true, error: state.error }
  emitTokensChange(key)

  try {
    const res = await getTokens(convId || undefined)
    tokensState[key] = { data: res, loading: false, error: null }
  } catch (err: any) {
    const errorMsg = err.message || "Failed to fetch tokens"
    tokensState[key] = { data: tokensState[key]?.data ?? null, loading: false, error: errorMsg }
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Tokens force refresh failure: ${errorMsg}`,
      source: 'Telemetry.tokens'
    })
  }
  emitTokensChange(key)
}

// --- Daemon Pub-Sub ---
function emitDaemonChange() {
  daemonListeners.forEach(l => l())
}

async function pollDaemon() {
  daemonState = { data: daemonState.data, loading: !daemonState.data, error: daemonState.error }
  emitDaemonChange()
  try {
    const res = await getDaemonStatus()
    daemonState = { data: res, loading: false, error: null }
  } catch (err: any) {
    const errorMsg = err.message || "Failed to fetch daemon status"
    daemonState = { data: daemonState.data, loading: false, error: errorMsg }
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Daemon polling failure: ${errorMsg}`,
      source: 'Telemetry.daemon'
    })
  }
  emitDaemonChange()

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
  daemonState = { data: daemonState.data, loading: true, error: daemonState.error }
  emitDaemonChange()
  try {
    const res = await getDaemonStatus()
    daemonState = { data: res, loading: false, error: null }
  } catch (err: any) {
    const errorMsg = err.message || "Failed to fetch daemon status"
    daemonState = { data: daemonState.data, loading: false, error: errorMsg }
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Daemon force refresh failure: ${errorMsg}`,
      source: 'Telemetry.daemon'
    })
  }
  emitDaemonChange()
}

// --- Scheduler Pub-Sub ---
function emitSchedulerChange() {
  schedulerListeners.forEach(l => l())
}

async function pollScheduler() {
  schedulerState = { data: schedulerState.data, loading: !schedulerState.data, error: schedulerState.error }
  emitSchedulerChange()
  try {
    const res = await getSchedulerStatus()
    schedulerState = { data: res, loading: false, error: null }
  } catch (err: any) {
    const errorMsg = err.message || "Failed to fetch scheduler status"
    schedulerState = { data: schedulerState.data, loading: false, error: errorMsg }
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Scheduler polling failure: ${errorMsg}`,
      source: 'Telemetry.scheduler'
    })
  }
  emitSchedulerChange()

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
  schedulerState = { data: schedulerState.data, loading: true, error: schedulerState.error }
  emitSchedulerChange()
  try {
    const res = await getSchedulerStatus()
    schedulerState = { data: res, loading: false, error: null }
  } catch (err: any) {
    const errorMsg = err.message || "Failed to fetch scheduler status"
    schedulerState = { data: schedulerState.data, loading: false, error: errorMsg }
    addNotification({
      type: 'glitch',
      snippet: `Telemetry: Scheduler force refresh failure: ${errorMsg}`,
      source: 'Telemetry.scheduler'
    })
  }
  emitSchedulerChange()
}
