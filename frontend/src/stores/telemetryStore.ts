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

export interface TelemetryStateSlice<T> {
  data: T | null
  loading: boolean
  error: string | null
}

import { createKeyedPollingChannel } from "./pollingChannel"
export { setTelemetrySession } from "./pollingChannel"
type Listener = () => void

function createPollingChannel<T>(name: string, fetcher: (signal?: AbortSignal) => Promise<T>, interval: number) {
  const channel = createKeyedPollingChannel<T>(name, (_, signal) => fetcher(signal), interval)
  return {
    subscribe: (get: () => TelemetryStateSlice<T>, set: (v: TelemetryStateSlice<T>) => void, listener: Listener) =>
      channel.subscribe("global", get, (_, value) => set(value), listener),
    refresh: (get: () => TelemetryStateSlice<T>, set: (v: TelemetryStateSlice<T>) => void) =>
      channel.refresh("global", get, (_, value) => set(value)),
  }
}

// --- Metrics ---
export const metricsState: Record<string, TelemetryStateSlice<MetricsResponse>> = {}

const metricsChan = createKeyedPollingChannel<MetricsResponse>(
  "metrics",
  (key, signal) => getMetrics(20, key && key !== "global" ? key : undefined, 30, signal),
  15000,
  key => { delete metricsState[key] },
)

export function subscribeMetrics(convId: string, listener: Listener) {
  const key = convId || "global"
  return metricsChan.subscribe(
    key,
    (k) => metricsState[k] || { data: null, loading: false, error: null },
    (k, v) => { metricsState[k] = v },
    listener,
  )
}

export function refreshMetricsForce(convId: string) {
  const key = convId || "global"
  return metricsChan.refresh(
    key,
    (k) => metricsState[k] || { data: null, loading: false, error: null },
    (k, v) => { metricsState[k] = v },
  )
}

// --- Beliefs ---
export const beliefsState: Record<string, TelemetryStateSlice<BeliefsResponse>> = {}

const beliefsChan = createKeyedPollingChannel<BeliefsResponse>("beliefs", (key, signal) => getBeliefs(key, "symbia", false, signal), 15000, key => { delete beliefsState[key] })

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

const tokensChan = createKeyedPollingChannel<TokenResponse>("tokens", (key, signal) => getTokens(key === "global" ? undefined : key, signal), 15000, key => { delete tokensState[key] })

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
