import { useSyncExternalStore } from "react"
import {
  subscribeMetrics,
  subscribeBeliefs,
  subscribeTokens,
  subscribeDaemon,
  subscribeScheduler,
  refreshMetricsForce,
  refreshBeliefsForce,
  refreshTokensForce,
  refreshDaemonForce,
  refreshSchedulerForce,
  metricsState,
  beliefsState,
  tokensState,
  daemonState,
  schedulerState,
  type TelemetryStateSlice
} from "../stores/telemetryStore"
import type {
  MetricsResponse,
  BeliefsResponse,
  DaemonStatusResponse,
  SchedulerStatusResponse,
  TokenResponse
} from "../api/client"

// Module-level stable empty state constants to maintain reference equality
const EMPTY_METRICS: TelemetryStateSlice<MetricsResponse> = { data: null, loading: false, error: null }
const EMPTY_BELIEFS: TelemetryStateSlice<BeliefsResponse> = { data: null, loading: false, error: null }
const EMPTY_TOKENS: TelemetryStateSlice<TokenResponse> = { data: null, loading: false, error: null }
const EMPTY_DAEMON: TelemetryStateSlice<DaemonStatusResponse> = { data: null, loading: false, error: null }
const EMPTY_SCHEDULER: TelemetryStateSlice<SchedulerStatusResponse> = { data: null, loading: false, error: null }
const NOOP_SUBSCRIBE = () => () => {}

// 1. Metrics Hook
export function useTelemetryMetrics(enabled: boolean) {
  const state = useSyncExternalStore(
    enabled ? subscribeMetrics : NOOP_SUBSCRIBE,
    () => metricsState
  )
  const effectiveState = enabled ? state : EMPTY_METRICS

  return {
    metrics: effectiveState.data,
    metricsLoading: effectiveState.loading,
    metricsError: effectiveState.error,
    refreshMetrics: refreshMetricsForce
  }
}

// 2. Beliefs Hook
export function useTelemetryBeliefs(conversationId: string | null, enabled: boolean) {
  const activeId = conversationId || ""

  const state = useSyncExternalStore(
    (enabled && activeId) ? (onStoreChange: () => void) => subscribeBeliefs(activeId, onStoreChange) : NOOP_SUBSCRIBE,
    () => (beliefsState[activeId] || EMPTY_BELIEFS) as TelemetryStateSlice<BeliefsResponse>
  )

  return {
    beliefs: state.data,
    beliefsLoading: state.loading,
    beliefsError: state.error,
    refreshBeliefs: () => refreshBeliefsForce(activeId)
  }
}

// 3. Tokens Hook
export function useTelemetryTokens(conversationId: string | null, enabled: boolean) {
  const activeId = conversationId || ""
  const key = activeId || "global"

  const state = useSyncExternalStore(
    enabled ? (onStoreChange: () => void) => subscribeTokens(activeId, onStoreChange) : NOOP_SUBSCRIBE,
    () => (tokensState[key] || EMPTY_TOKENS) as TelemetryStateSlice<TokenResponse>
  )

  return {
    tokens: state.data,
    tokensLoading: state.loading,
    tokensError: state.error,
    refreshTokens: () => refreshTokensForce(activeId)
  }
}

// 4. Daemon Hook
export function useTelemetryDaemon(enabled: boolean) {
  const state = useSyncExternalStore(
    enabled ? subscribeDaemon : NOOP_SUBSCRIBE,
    () => daemonState
  )
  const effectiveState = enabled ? state : EMPTY_DAEMON

  return {
    daemon: effectiveState.data,
    daemonLoading: effectiveState.loading,
    daemonError: effectiveState.error,
    refreshDaemon: refreshDaemonForce
  }
}

// 5. Scheduler Hook
export function useTelemetryScheduler(enabled: boolean) {
  const state = useSyncExternalStore(
    enabled ? subscribeScheduler : NOOP_SUBSCRIBE,
    () => schedulerState
  )
  const effectiveState = enabled ? state : EMPTY_SCHEDULER

  return {
    scheduler: effectiveState.data,
    schedulerLoading: effectiveState.loading,
    schedulerError: effectiveState.error,
    refreshScheduler: refreshSchedulerForce
  }
}
