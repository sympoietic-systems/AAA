// useResearch — hook for research task CRUD + polling.
// Works with the Autonomous Research Engine API.

import { useState, useEffect, useCallback, useRef } from "react"
import {
  getResearchTasks,
  getResearchSummary,
  getResearchTask,
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
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchTasks = useCallback(async () => {
    try {
      const data = await getResearchTasks({ limit: 50 })
      setTasks(data)
      setError(null)
    } catch (e: any) {
      setError(e.message || "Failed to fetch research tasks")
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
    refresh()
    timerRef.current = setInterval(refresh, POLL_INTERVAL)
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
  }, [enabled, refresh])

  const dispatch = useCallback(async (payload: DispatchPayload): Promise<string | null> => {
    try {
      setLoading(true)
      const result = await dispatchResearch(payload)
      await refresh()
      return result.task_id
    } catch (e: any) {
      setError(e.message || "Failed to dispatch research")
      return null
    } finally {
      setLoading(false)
    }
  }, [refresh])

  const approve = useCallback(async (taskId: string) => {
    try {
      await approveProposal(taskId)
      await refresh()
    } catch (e: any) {
      setError(e.message || "Failed to approve proposal")
    }
  }, [refresh])

  const reject = useCallback(async (taskId: string) => {
    try {
      await rejectProposal(taskId)
      await refresh()
    } catch (e: any) {
      setError(e.message || "Failed to reject proposal")
    }
  }, [refresh])

  const cancel = useCallback(async (taskId: string) => {
    try {
      await cancelTask(taskId)
      await refresh()
    } catch (e: any) {
      setError(e.message || "Failed to cancel task")
    }
  }, [refresh])

  return { tasks, summary, loading, error, dispatch, approve, reject, cancel, refresh }
}
