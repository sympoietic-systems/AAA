import { useState, useEffect, useCallback } from "react"
import {
  getMetrics,
  getBeliefs,
  getDaemonStatus,
  getSchedulerStatus,
  getTokens,
} from "../api/client"
import type {
  MetricsResponse,
  BeliefsResponse,
  DaemonStatusResponse,
  SchedulerStatusResponse,
  TokenResponse,
} from "../api/client"

interface TelemetryActiveSections {
  health: boolean
  diffraction: boolean
  beliefs: boolean
  dreaming: boolean
  scheduler: boolean
  tokens: boolean
}

export function useTelemetry(
  collapsed: boolean,
  conversationId: string | null,
  activeSections: TelemetryActiveSections
) {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null)
  const [metricsError, setMetricsError] = useState<string | null>(null)
  const [metricsLoading, setMetricsLoading] = useState(false)

  const [beliefs, setBeliefs] = useState<BeliefsResponse | null>(null)
  const [beliefsError, setBeliefsError] = useState<string | null>(null)
  const [beliefsLoading, setBeliefsLoading] = useState(false)

  const [daemon, setDaemon] = useState<DaemonStatusResponse | null>(null)
  const [daemonError, setDaemonError] = useState<string | null>(null)
  const [daemonLoading, setDaemonLoading] = useState(false)

  const [scheduler, setScheduler] = useState<SchedulerStatusResponse | null>(null)
  const [schedulerError, setSchedulerError] = useState<string | null>(null)
  const [schedulerLoading, setSchedulerLoading] = useState(false)

  const [tokens, setTokens] = useState<TokenResponse | null>(null)
  const [tokensError, setTokensError] = useState<string | null>(null)
  const [tokensLoading, setTokensLoading] = useState(false)

  const refreshMetrics = useCallback(async () => {
    setMetricsLoading(true)
    try {
      const res = await getMetrics()
      setMetrics(res)
      setMetricsError(null)
    } catch (e: unknown) {
      setMetricsError(e instanceof Error ? e.message : "Failed to fetch metrics")
    } finally {
      setMetricsLoading(false)
    }
  }, [])

  const refreshBeliefs = useCallback(async () => {
    if (!conversationId) return
    setBeliefsLoading(true)
    try {
      const res = await getBeliefs(conversationId)
      setBeliefs(res)
      setBeliefsError(null)
    } catch (e: unknown) {
      setBeliefsError(e.message || "Failed to fetch beliefs")
    } finally {
      setBeliefsLoading(false)
    }
  }, [conversationId])

  const refreshDaemon = useCallback(async () => {
    setDaemonLoading(true)
    try {
      const res = await getDaemonStatus()
      setDaemon(res)
      setDaemonError(null)
    } catch (e: unknown) {
      setDaemonError(e.message || "Failed to fetch daemon status")
    } finally {
      setDaemonLoading(false)
    }
  }, [])

  const refreshScheduler = useCallback(async () => {
    setSchedulerLoading(true)
    try {
      const res = await getSchedulerStatus()
      setScheduler(res)
      setSchedulerError(null)
    } catch (e: unknown) {
      setSchedulerError(e.message || "Failed to fetch scheduler status")
    } finally {
      setSchedulerLoading(false)
    }
  }, [])

  const refreshTokens = useCallback(async () => {
    setTokensLoading(true)
    try {
      const res = await getTokens(conversationId || undefined)
      setTokens(res)
      setTokensError(null)
    } catch (e: unknown) {
      setTokensError(e.message || "Failed to fetch tokens")
    } finally {
      setTokensLoading(false)
    }
  }, [conversationId])

  // Consolidated polling — single tick loop batches all enabled endpoint calls
  useEffect(() => {
    if (collapsed) return

    const needsMetrics = activeSections.health || activeSections.diffraction
    const needsBeliefs = activeSections.beliefs && !!conversationId
    const needsDaemon = activeSections.dreaming
    const needsScheduler = activeSections.scheduler
    const needsTokens = activeSections.tokens
    const anyActive = needsMetrics || needsBeliefs || needsDaemon || needsScheduler || needsTokens

    if (!anyActive) return

    let active = true
    let timeoutId: ReturnType<typeof setTimeout>

    const tick = async () => {
      if (!active) return

      const promises: Promise<void>[] = []

      if (needsMetrics) {
        promises.push(
          getMetrics()
            .then((res) => { if (active) { setMetrics(res); setMetricsError(null) } })
            .catch((e: unknown) => { if (active) setMetricsError(e.message || "Failed to fetch metrics") })
        )
      }
      if (needsBeliefs && conversationId) {
        promises.push(
          getBeliefs(conversationId)
            .then((res) => { if (active) { setBeliefs(res); setBeliefsError(null) } })
            .catch((e: unknown) => { if (active) setBeliefsError(e.message || "Failed to fetch beliefs") })
        )
      }
      if (needsDaemon) {
        promises.push(
          getDaemonStatus()
            .then((res) => { if (active) { setDaemon(res); setDaemonError(null) } })
            .catch((e: unknown) => { if (active) setDaemonError(e.message || "Failed to fetch daemon status") })
        )
      }
      if (needsScheduler) {
        promises.push(
          getSchedulerStatus()
            .then((res) => { if (active) { setScheduler(res); setSchedulerError(null) } })
            .catch((e: unknown) => { if (active) setSchedulerError(e.message || "Failed to fetch scheduler status") })
        )
      }
      if (needsTokens) {
        promises.push(
          getTokens(conversationId || undefined)
            .then((res) => { if (active) { setTokens(res); setTokensError(null) } })
            .catch((e: unknown) => { if (active) setTokensError(e.message || "Failed to fetch tokens") })
        )
      }

      await Promise.allSettled(promises)

      if (active) {
        const delay = 15000 + (Math.random() - 0.5) * 1000
        timeoutId = setTimeout(tick, delay)
      }
    }

    tick()

    return () => {
      active = false
      clearTimeout(timeoutId)
    }
  }, [
    collapsed,
    conversationId,
    activeSections.health,
    activeSections.diffraction,
    activeSections.beliefs,
    activeSections.dreaming,
    activeSections.scheduler,
    activeSections.tokens,
  ])

  return {
    metrics,
    metricsError,
    metricsLoading,
    refreshMetrics,

    beliefs,
    beliefsError,
    beliefsLoading,
    refreshBeliefs,

    daemon,
    daemonError,
    daemonLoading,
    refreshDaemon,

    scheduler,
    schedulerError,
    schedulerLoading,
    refreshScheduler,

    tokens,
    tokensError,
    tokensLoading,
    refreshTokens,
  }
}
