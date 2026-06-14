import { useState, useEffect, memo } from "react"
import { getSchedulerStatus } from "../../../api/client"
import type { SchedulerStatusResponse } from "../../../api/client"

function getStatusColor(s: string) {
  switch (s) { case "running": return "#facc15"; case "completed": return "#4ade80"; case "error": return "#ef4444"; case "pending": return "#60a5fa"; default: return "#555" }
}

export const StartupSection = memo(function StartupSection() {
  const [status, setStatus] = useState<SchedulerStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getSchedulerStatus().then(setStatus).catch(e => setError(e.message || "Failed"))
    const id = setInterval(() => { getSchedulerStatus().then(setStatus).catch(() => {}) }, 10000)
    return () => clearInterval(id)
  }, [])

  if (error && !status) return <div className="text-[#ef4444] font-mono">{error}</div>
  if (!status) return <div className="text-[#444] font-mono">waiting for data...</div>

  const { status: schedulerStatus, indexing_tasks_found, indexing_tasks_completed, indexing_tasks_failed, active_indexing_jobs, belief_turns_found, belief_turns_completed, belief_turns_failed, error_details } = status
  const color = getStatusColor(schedulerStatus)

  return (
    <div className="px-4 py-2">
      <div className="flex items-center gap-1.5 mb-3 font-mono">
        <span className="text-[9px] leading-none" style={{ color }}>●</span>
        <span className="text-[11px] text-[#888]">startup tasks</span>
        <span className="text-[10px] ml-auto" style={{ color }}>{schedulerStatus}</span>
      </div>

      <div className="font-mono text-[10px] space-y-2">
        {indexing_tasks_found > 0 ? (
          <div>
            <div className="text-[#888] flex justify-between">
              <span>File Resumption:</span>
              <span className="text-[#eee] font-bold">{indexing_tasks_completed + indexing_tasks_failed}/{indexing_tasks_found}</span>
            </div>
            <div className="flex gap-2 text-[9px] text-[#666]">
              <span className="text-[#4ade80]">ok: {indexing_tasks_completed}</span>
              <span className="text-[#ef4444]">fail: {indexing_tasks_failed}</span>
            </div>
          </div>
        ) : <div className="text-[#555] italic">No pending file index tasks</div>}

        {active_indexing_jobs.length > 0 && (
          <div>
            <span className="text-[#facc15] text-[9px] uppercase tracking-wider">⚡ Active Indexing:</span>
            {active_indexing_jobs.map(job => <div key={job} className="text-[#ccc] text-[9px] ml-2">• {job}</div>)}
          </div>
        )}

        {belief_turns_found > 0 ? (
          <div>
            <div className="text-[#888] flex justify-between">
              <span>Belief Catch-up:</span>
              <span className="text-[#eee] font-bold">{belief_turns_completed + belief_turns_failed}/{belief_turns_found}</span>
            </div>
            <div className="flex gap-2 text-[9px] text-[#666]">
              <span className="text-[#4ade80]">ok: {belief_turns_completed}</span>
              <span className="text-[#ef4444]">fail: {belief_turns_failed}</span>
            </div>
          </div>
        ) : <div className="text-[#555] italic">No belief turns to catch up</div>}

        {error_details && <div className="text-[#ef4444] text-[9px]">Error: {error_details}</div>}
      </div>
    </div>
  )
})
