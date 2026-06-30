import { useState, useEffect, useCallback } from "react"
import type { ResearchTask } from "../../../../api/research"
import { getResearchTask, getTaskPhase } from "../../../../api/research"

/** Visibility-aware polling hook for live task status */
export function useTaskPolling(taskId: string, _taskStatus: string, initialTask: ResearchTask) {
  const [liveTask, setLiveTask] = useState(initialTask)
  const [orchPhase, setOrchPhase] = useState(initialTask.status === "queued" ? "planning" : "")

  // Track live status so we can detect the active→completed transition
  const liveStatus = liveTask.status

  useEffect(() => {
    // Poll while the task is active or queued (using the live status, not the stale prop)
    if (liveStatus !== "active" && liveStatus !== "queued") return
    const poll = () => {
      if (document.hidden) return
      getResearchTask(taskId).then(t => { if (t) setLiveTask(t) }).catch(() => {})
      getTaskPhase(taskId).then(p => {
        if (p.phase && p.phase !== "not_started") setOrchPhase(p.phase)
      }).catch(() => {})
    }
    poll()
    const timer = setInterval(poll, 5000)
    const onVisible = () => { poll() }
    document.addEventListener("visibilitychange", onVisible)
    return () => {
      clearInterval(timer)
      document.removeEventListener("visibilitychange", onVisible)
    }
  }, [taskId, liveStatus])

  // One-shot final fetch when the task transitions from active → terminal
  // This ensures the result_summary (synthesis report) is captured after synthesis completes
  useEffect(() => {
    if (liveStatus === "completed" || liveStatus === "failed" || liveStatus === "cancelled") {
      getResearchTask(taskId).then(t => { if (t) setLiveTask(t) }).catch(() => {})
    }
  }, [taskId, liveStatus])

  const refreshAll = useCallback(() => {
    getResearchTask(taskId).then(t => { if (t) setLiveTask(t) }).catch(() => {})
    getTaskPhase(taskId).then(p => {
      if (p.phase && p.phase !== "not_started") setOrchPhase(p.phase)
    }).catch(() => {})
  }, [taskId])

  const current = liveTask || initialTask

  return { current, orchPhase, refreshAll }
}
