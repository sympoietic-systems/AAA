import { useState, useEffect, memo } from "react"
import { getSchedulerStatus } from "../../api/client"
import type { SchedulerStatusResponse } from "../../api/client"

function getStatusColor(s: string) {
  switch (s) {
    case "running": return "#facc15"
    case "completed": return "#4ade80"
    case "error": return "#ef4444"
    case "pending": return "#60a5fa"
    default: return "#555"
  }
}

function StartupSectionComponent() {
  const [status, setStatus] = useState<SchedulerStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getSchedulerStatus()
      .then(setStatus)
      .catch(e => setError(e.message || "Failed"))
    const id = setInterval(() => {
      getSchedulerStatus()
        .then(setStatus)
        .catch(() => {})
    }, 10000)
    return () => clearInterval(id)
  }, [])

  if (error && !status) {
    return <p className="text-[10px] text-[#ef4444] font-mono">{error}</p>
  }

  if (!status) {
    return <p className="text-[10px] text-[#444] font-mono">waiting for data...</p>
  }

  const {
    status: schedulerStatus,
    indexing_tasks_found,
    indexing_tasks_completed,
    indexing_tasks_failed,
    active_indexing_jobs,
    belief_turns_found,
    belief_turns_completed,
    belief_turns_failed,
    error_details
  } = status

  const color = getStatusColor(schedulerStatus)

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2">
      <div className="flex items-center gap-1.5 mb-2 font-mono">
        <span className="text-[9px] leading-none" style={{ color }}>●</span>
        <span className="text-[11px] text-[#888]">startup tasks</span>
        <span className="text-[10px] ml-auto" style={{ color }}>
          {schedulerStatus}
        </span>
      </div>

      <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded p-2 font-mono text-[10px] leading-relaxed space-y-1.5">
        {indexing_tasks_found > 0 ? (
          <div>
            <div className="text-[#888] flex justify-between">
              <span>File Resumption:</span>
              <span className="text-[#eee] font-bold">
                {indexing_tasks_completed + indexing_tasks_failed}/{indexing_tasks_found}
              </span>
            </div>
            <div className="flex gap-2 text-[9px] text-[#666] pl-1">
              <span className="text-[#4ade80]">ok: {indexing_tasks_completed}</span>
              <span className="text-[#ef4444]">fail: {indexing_tasks_failed}</span>
            </div>
          </div>
        ) : (
          <div className="text-[#555] italic">No pending file index tasks resumed</div>
        )}

        {active_indexing_jobs.length > 0 && (
          <div className="border-t border-[#222]/30 pt-1">
            <span className="text-[#facc15] text-[9px] uppercase tracking-wider block">⚡ Active Indexing:</span>
            <ul className="list-disc list-inside text-[9px] text-[#ccc] space-y-0.5 mt-0.5">
              {active_indexing_jobs.map((job) => (
                <li key={job} className="truncate" title={job}>
                  {job}
                </li>
              ))}
            </ul>
          </div>
        )}

        {belief_turns_found > 0 ? (
          <div className="border-t border-[#222]/30 pt-1">
            <div className="text-[#888] flex justify-between">
              <span>Belief Catch-up:</span>
              <span className="text-[#eee] font-bold">
                {belief_turns_completed + belief_turns_failed}/{belief_turns_found}
              </span>
            </div>
            <div className="flex gap-2 text-[9px] text-[#666] pl-1">
              <span className="text-[#4ade80]">ok: {belief_turns_completed}</span>
              <span className="text-[#ef4444]">fail: {belief_turns_failed}</span>
            </div>
          </div>
        ) : (
          <div className="border-t border-[#222]/30 pt-1 text-[#555] italic">No belief turns to catch up</div>
        )}

        {error_details && (
          <div className="text-[#ef4444] text-[9px] border-t border-[#3a1a1a] pt-1">
            Error: {error_details}
          </div>
        )}
      </div>
    </div>
  )
}

export const StartupSection = memo(StartupSectionComponent)
