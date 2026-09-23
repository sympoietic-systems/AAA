// useResearch — hook for research task CRUD + polling.
// Works with the Autonomous Research Engine API.

import { useState, useEffect, useCallback } from "react"
import {
  getResearchTasks,
  getResearchSummary,
  dispatchResearch,
  approveProposal,
  rejectProposal,
  cancelTask,
  type ResearchTask,
  type ResearchSummary,
  type DispatchPayload,
} from "../api/research"

export interface UseResearchState {
  tasks: ResearchTask[]
  summary: ResearchSummary
  loading: boolean
  error: string | null
  dispatch: (payload: DispatchPayload) => Promise<string | null>
  approve: (taskId: string) => Promise<void>
  reject: (taskId: string) => Promise<void>
  cancel: (taskId: string) => Promise<void>
  refresh: () => Promise<void>
}

const POLL_INTERVAL = 5000 // 5 seconds

export function useResearch(enabled: boolean = true): UseResearchState {
  const [tasks, setTasks] = useState<ResearchTask[]>([])
  const [summary, setSummary] = useState<ResearchSummary>({ active_count: 0, queued_count: 0, pending_proposals: 0 })
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState<string | null>(null)

  const fetchTasks = useCallback(async () => {
    try {
      const data = await getResearchTasks({ limit: 50 })
      setTasks(data)
      setError(null)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to fetch research tasks"
      setError(msg)
    }
  }, [])

  const fetchSummary = useCallback(async () => {
    try {
      const data = await getResearchSummary()
      setSummary(data)
    } catch { /* silent */ }
  }, [])

  const refresh = useCallback(async () => {
    setLoading(true)
    await Promise.all([fetchTasks(), fetchSummary()])
    setLoading(false)
  }, [fetchTasks, fetchSummary])

  // Start/stop polling based on enabled flag
  useEffect(() => {
    if (!enabled) return

    let isMounted = true

    const poll = async () => {
      try {
        const [tasksData, summaryData] = await Promise.all([
          getResearchTasks({ limit: 50 }),
          getResearchSummary().catch(() => null),
        ])
        if (isMounted) {
          setTasks(tasksData)
          if (summaryData) setSummary(summaryData)
          setError(null)
          setLoading(false)
        }
      } catch (e: unknown) {
        if (isMounted) {
          const msg = e instanceof Error ? e.message : "Failed to fetch research tasks"
          setError(msg)
          setLoading(false)
        }
      }
    }

    poll()
    const timer = setInterval(poll, POLL_INTERVAL)

    return () => {
      isMounted = false
      clearInterval(timer)
    }
  }, [enabled])

  const dispatch = useCallback(async (payload: DispatchPayload): Promise<string | null> => {
    try {
      setLoading(true)
      const result = await dispatchResearch(payload)
      await refresh()
      return result.task_id
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to dispatch research"
      setError(msg)
      return null
    } finally {
      setLoading(false)
    }
  }, [refresh])

  const approve = useCallback(async (taskId: string): Promise<void> => {
    try {
      setLoading(true)
      await approveProposal(taskId)
      await refresh()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to approve proposal"
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [refresh])

  const reject = useCallback(async (taskId: string): Promise<void> => {
    try {
      setLoading(true)
      await rejectProposal(taskId)
      await refresh()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to reject proposal"
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [refresh])

  const cancel = useCallback(async (taskId: string): Promise<void> => {
    try {
      setLoading(true)
      await cancelTask(taskId)
      await refresh()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to cancel task"
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [refresh])

  return {
    tasks,
    summary,
    loading,
    error,
    dispatch,
    approve,
    reject,
    cancel,
    refresh,
  }
}
