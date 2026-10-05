import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  metricsState,
  subscribeMetrics,
  refreshMetricsForce,
  daemonState,
  subscribeDaemon,
} from '../telemetryStore'

vi.mock('../notificationStore', () => ({
  addNotification: vi.fn(),
  dismissByMatch: vi.fn(),
}))

vi.mock('../../api/client', () => ({
  getMetrics: vi.fn().mockResolvedValue({ vitality: 0.5 }),
  getDaemonStatus: vi.fn().mockResolvedValue({ status: 'running' }),
  getSchedulerStatus: vi.fn().mockResolvedValue({ status: 'idle' }),
  getBeliefs: vi.fn().mockResolvedValue({ beliefs: [] }),
  getTokens: vi.fn().mockResolvedValue({ tokens: 0 }),
}))

function flushPromises() {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

beforeEach(() => {
  delete metricsState['conv-1']
  daemonState.data = null
  daemonState.loading = false
  daemonState.error = null
})

afterEach(async () => {
  vi.clearAllMocks()
  await flushPromises()
})

describe('telemetryStore', () => {
  it('exports initial state', () => {
    expect(metricsState['conv-1']).toBeUndefined()
  })

  it('subscribe returns an unsubscribe function', async () => {
    const listener = vi.fn()
    const unsub = subscribeMetrics('conv-1', listener)
    expect(typeof unsub).toBe('function')
    unsub()
    await flushPromises()
  })

  it('starts polling and sets loading true on subscribe', async () => {
    const listener = vi.fn()
    const unsub = subscribeMetrics('conv-1', listener)
    expect(metricsState['conv-1']?.loading).toBe(true)
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
    await refreshMetricsForce('conv-1')
    expect(metricsState['conv-1']?.loading).toBe(false)
  })
})
