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
  activeSections: TelemetryActiveSections,
  trigger?: any
) {
  // Metrics (Vitality & Diffraction)
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null)
  const [metricsError, setMetricsError] = useState<string | null>(null)
  const [metricsLoading, setMetricsLoading] = useState(false)

  // Beliefs
  const [beliefs, setBeliefs] = useState<BeliefsResponse | null>(null)
  const [beliefsError, setBeliefsError] = useState<string | null>(null)
  const [beliefsLoading, setBeliefsLoading] = useState(false)

  // Daemon (Dreaming)
  const [daemon, setDaemon] = useState<DaemonStatusResponse | null>(null)
  const [daemonError, setDaemonError] = useState<string | null>(null)
  const [daemonLoading, setDaemonLoading] = useState(false)

  // Scheduler (Startup)
  const [scheduler, setScheduler] = useState<SchedulerStatusResponse | null>(null)
  const [schedulerError, setSchedulerError] = useState<string | null>(null)
  const [schedulerLoading, setSchedulerLoading] = useState(false)

  // Tokens
  const [tokens, setTokens] = useState<TokenResponse | null>(null)
  const [tokensError, setTokensError] = useState<string | null>(null)
  const [tokensLoading, setTokensLoading] = useState(false)

  // --- MANUAL REFRESH FUNCTIONS ---
  const refreshMetrics = useCallback(async () => {
    setMetricsLoading(true)
    try {
      const res = await getMetrics()
      setMetrics(res)
      setMetricsError(null)
    } catch (e: any) {
      setMetricsError(e.message || "Failed to fetch metrics")
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
    } catch (e: any) {
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
    } catch (e: any) {
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
    } catch (e: any) {
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
    } catch (e: any) {
      setTokensError(e.message || "Failed to fetch tokens")
    } finally {
      setTokensLoading(false)
    }
  }, [conversationId])

  // --- POLLING LOGIC ---

  // 1. Metrics (Health & Diffraction) - Polls every 15 seconds with jitter
  useEffect(() => {
    if (collapsed || (!activeSections.health && !activeSections.diffraction)) return

    let active = true
    let timeoutId: ReturnType<typeof setTimeout>

    const tick = async () => {
      if (!active) return
      try {
        const res = await getMetrics()
        if (active) {
          setMetrics(res)
          setMetricsError(null)
        }
      } catch (e: any) {
        if (active) {
          setMetricsError(e.message || "Failed to fetch metrics")
        }
      }

      if (active) {
        const delay = 15000 + (Math.random() - 0.5) * 1000 // 15s ± 500ms
        timeoutId = setTimeout(tick, delay)
      }
    }

    tick()

    return () => {
      active = false
      clearTimeout(timeoutId)
    }
  }, [collapsed, activeSections.health, activeSections.diffraction, trigger])

  // 2. Beliefs - Polls every 15 seconds with jitter
  useEffect(() => {
    if (collapsed || !activeSections.beliefs || !conversationId) return

    let active = true
    let timeoutId: ReturnType<typeof setTimeout>

    const tick = async () => {
      if (!active) return
      try {
        const res = await getBeliefs(conversationId)
        if (active) {
          setBeliefs(res)
          setBeliefsError(null)
        }
      } catch (e: any) {
        if (active) {
          setBeliefsError(e.message || "Failed to fetch beliefs")
        }
      }

      if (active) {
        const delay = 15000 + (Math.random() - 0.5) * 1000 // 15s ± 500ms
        timeoutId = setTimeout(tick, delay)
      }
    }

    tick()

    return () => {
      active = false
      clearTimeout(timeoutId)
    }
  }, [collapsed, activeSections.beliefs, conversationId, trigger])

  // 3. Dreaming (Daemon) - Polls every 10 seconds with jitter
  useEffect(() => {
    if (collapsed || !activeSections.dreaming) return

    let active = true
    let timeoutId: ReturnType<typeof setTimeout>

    const tick = async () => {
      if (!active) return
      try {
        const res = await getDaemonStatus()
        if (active) {
          setDaemon(res)
          setDaemonError(null)
        }
      } catch (e: any) {
        if (active) {
          setDaemonError(e.message || "Failed to fetch daemon status")
        }
      }

      if (active) {
        const delay = 10000 + (Math.random() - 0.5) * 1000 // 10s ± 500ms
        timeoutId = setTimeout(tick, delay)
      }
    }

    tick()

    return () => {
      active = false
      clearTimeout(timeoutId)
    }
  }, [collapsed, activeSections.dreaming, trigger])

  // 4. Scheduler (Startup) - Polls every 10 seconds with jitter
  useEffect(() => {
    if (collapsed || !activeSections.scheduler) return

    let active = true
    let timeoutId: ReturnType<typeof setTimeout>

    const tick = async () => {
      if (!active) return
      try {
        const res = await getSchedulerStatus()
        if (active) {
          setScheduler(res)
          setSchedulerError(null)
        }
      } catch (e: any) {
        if (active) {
          setSchedulerError(e.message || "Failed to fetch scheduler status")
        }
      }

      if (active) {
        const delay = 10000 + (Math.random() - 0.5) * 1000 // 10s ± 500ms
        timeoutId = setTimeout(tick, delay)
      }
    }

    tick()

    return () => {
      active = false
      clearTimeout(timeoutId)
    }
  }, [collapsed, activeSections.scheduler, trigger])

  // 5. Tokens - Polls every 15 seconds with jitter
  useEffect(() => {
    if (collapsed || !activeSections.tokens) return

    let active = true
    let timeoutId: ReturnType<typeof setTimeout>

    const tick = async () => {
      if (!active) return
      try {
        const res = await getTokens(conversationId || undefined)
        if (active) {
          setTokens(res)
          setTokensError(null)
        }
      } catch (e: any) {
        if (active) {
          setTokensError(e.message || "Failed to fetch tokens")
        }
      }

      if (active) {
        const delay = 15000 + (Math.random() - 0.5) * 1000 // 15s ± 500ms
        timeoutId = setTimeout(tick, delay)
      }
    }

    tick()

    return () => {
      active = false
      clearTimeout(timeoutId)
    }
  }, [collapsed, activeSections.tokens, conversationId, trigger])

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
