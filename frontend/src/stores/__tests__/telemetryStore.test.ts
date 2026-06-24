import { describe, it, expect, vi, afterEach } from 'vitest'
import {
  metricsState,
  subscribeMetrics,
  refreshMetricsForce,
  daemonState,
  subscribeDaemon,
  schedulerState,
  subscribeScheduler,
} from '../telemetryStore'

vi.mock('../api/client', () => ({
  getMetrics: vi.fn().mockResolvedValue({ vitality: 0.5 }),
  getDaemonStatus: vi.fn().mockResolvedValue({ status: 'running' }),
  getSchedulerStatus: vi.fn().mockResolvedValue({ status: 'idle' }),
  getBeliefs: vi.fn().mockResolvedValue({ beliefs: [] }),
  getTokens: vi.fn().mockResolvedValue({ tokens: 0 }),
}))

afterEach(() => {
  vi.clearAllMocks()
})

function flushPromises() {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

describe('telemetryStore', () => {
  it('exports initial state', () => {
    expect(metricsState.data).toBeNull()
    expect(metricsState.loading).toBe(false)
    expect(metricsState.error).toBeNull()
  })

  it('subscribe returns an unsubscribe function', () => {
    const listener = vi.fn()
    const unsub = subscribeMetrics(listener)
    expect(typeof unsub).toBe('function')
    unsub()
  })

  it('starts polling and sets loading true on subscribe', async () => {
    const listener = vi.fn()
    const unsub = subscribeMetrics(listener)
    expect(metricsState.loading).toBe(true)
    await flushPromises()
    unsub()
  })

  it('resolves loading to false after fetch completes', async () => {
    const listener = vi.fn()
    const unsub = subscribeDaemon(listener)
    expect(daemonState.loading).toBe(true)
    await flushPromises()
    expect(daemonState.loading).toBe(false)
    unsub()
  })

  it('refreshMetricsForce triggers a fetch', async () => {
    await refreshMetricsForce()
    expect(metricsState.loading).toBe(false)
  })
})
