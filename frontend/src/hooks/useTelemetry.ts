import { useState, useEffect } from "react"
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

// 1. Metrics Hook
export function useTelemetryMetrics(enabled: boolean) {
  const [state, setState] = useState<TelemetryStateSlice<MetricsResponse>>(() => metricsState)

  useEffect(() => {
    if (!enabled) return
    setState(metricsState)
    const unsubscribe = subscribeMetrics(() => {
      setState({ ...metricsState })
    })
    return unsubscribe
  }, [enabled])

  return {
    metrics: state.data,
    metricsLoading: state.loading,
    metricsError: state.error,
    refreshMetrics: refreshMetricsForce
  }
}

// 2. Beliefs Hook
export function useTelemetryBeliefs(conversationId: string | null, enabled: boolean) {
  const activeId = conversationId || ""
  const getBeliefsState = () => (beliefsState[activeId] || { data: null, loading: false, error: null }) as TelemetryStateSlice<BeliefsResponse>
  const [state, setState] = useState<TelemetryStateSlice<BeliefsResponse>>(getBeliefsState)

  useEffect(() => {
    setState(getBeliefsState())
    if (!enabled || !activeId) return
    const unsubscribe = subscribeBeliefs(activeId, () => {
      setState({ ...getBeliefsState() })
    })
    return unsubscribe
  }, [enabled, activeId])

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
  const getTokensState = () => (tokensState[key] || { data: null, loading: false, error: null }) as TelemetryStateSlice<TokenResponse>
  const [state, setState] = useState<TelemetryStateSlice<TokenResponse>>(getTokensState)

  useEffect(() => {
    setState(getTokensState())
    if (!enabled) return
    const unsubscribe = subscribeTokens(activeId, () => {
      setState({ ...getTokensState() })
    })
    return unsubscribe
  }, [enabled, activeId])

  return {
    tokens: state.data,
    tokensLoading: state.loading,
    tokensError: state.error,
    refreshTokens: () => refreshTokensForce(activeId)
  }
}

// 4. Daemon Hook
export function useTelemetryDaemon(enabled: boolean) {
  const [state, setState] = useState<TelemetryStateSlice<DaemonStatusResponse>>(() => daemonState)

  useEffect(() => {
    if (!enabled) return
    setState(daemonState)
    const unsubscribe = subscribeDaemon(() => {
      setState({ ...daemonState })
    })
    return unsubscribe
  }, [enabled])

  return {
    daemon: state.data,
    daemonLoading: state.loading,
    daemonError: state.error,
    refreshDaemon: refreshDaemonForce
  }
}

// 5. Scheduler Hook
export function useTelemetryScheduler(enabled: boolean) {
  const [state, setState] = useState<TelemetryStateSlice<SchedulerStatusResponse>>(() => schedulerState)

  useEffect(() => {
    if (!enabled) return
    setState(schedulerState)
    const unsubscribe = subscribeScheduler(() => {
      setState({ ...schedulerState })
    })
    return unsubscribe
  }, [enabled])

  return {
    scheduler: state.data,
    schedulerLoading: state.loading,
    schedulerError: state.error,
    refreshScheduler: refreshSchedulerForce
  }
}


