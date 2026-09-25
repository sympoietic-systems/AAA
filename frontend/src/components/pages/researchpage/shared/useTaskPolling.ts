import { useState, useEffect, useCallback } from "react"
import { getResearchTask, getTaskPhase, type ResearchTask } from "../../../../api/research"

/** Each polling generation owns its requests and one completion-scheduled timer. */
export function useTaskPolling(taskId: string, _taskStatus: string, initialTask: ResearchTask) {
  const [state, setState] = useState({ task: initialTask, phase: "", error: "" })
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout> | undefined
    let busy = false
    let active = true
    const poll = async () => {
      if (busy || controller.signal.aborted || document.hidden) return
      clearTimeout(timer)
      busy = true
      try {
        const [task, phase] = await Promise.all([
          getResearchTask(taskId, controller.signal), getTaskPhase(taskId, controller.signal),
        ])
        if (controller.signal.aborted) return
        active = task.status === "active" || task.status === "queued"
        setState({ task, phase: phase.phase === "not_started" ? "" : phase.phase, error: "" })
      } catch (error) {
        if (!controller.signal.aborted) setState(previous => ({ ...previous, error: error instanceof Error ? error.message : "Task polling failed" }))
      } finally {
        busy = false
        if (!controller.signal.aborted && active) timer = setTimeout(poll, 5000)
      }
    }
    void poll()
    const onVisible = () => { if (!document.hidden) void poll() }
    document.addEventListener("visibilitychange", onVisible)
    return () => {
      controller.abort()
      clearTimeout(timer)
      document.removeEventListener("visibilitychange", onVisible)
    }
  }, [taskId, revision])
  const refreshAll = useCallback(() => setRevision(value => value + 1), [])
  return { current: state.task.id === taskId ? state.task : initialTask, orchPhase: state.task.id === taskId ? state.phase : "", error: state.error, refreshAll }
}
