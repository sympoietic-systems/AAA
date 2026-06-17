import { useState, useEffect, useCallback } from "react"
import type { ResearchTask } from "../../../../api/research"
import { getResearchTask, getTaskPhase } from "../../../../api/research"

/** Visibility-aware polling hook for live task status */
export function useTaskPolling(taskId: string, taskStatus: string, initialTask: ResearchTask) {
  const [liveTask, setLiveTask] = useState(initialTask)
  const [orchPhase, setOrchPhase] = useState(initialTask.status === "queued" ? "planning" : "")

  useEffect(() => {
    if (taskStatus !== "active" && taskStatus !== "queued") return
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
  }, [taskId, taskStatus])

  const refreshAll = useCallback(() => {
    getResearchTask(taskId).then(t => { if (t) setLiveTask(t) }).catch(() => {})
    getTaskPhase(taskId).then(p => {
      if (p.phase && p.phase !== "not_started") setOrchPhase(p.phase)
    }).catch(() => {})
  }, [taskId])

  const current = liveTask || initialTask

  return { current, orchPhase, refreshAll }
}
