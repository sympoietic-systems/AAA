import React, { memo } from "react"

interface LogEntriesProps {
  entries: any[]
  loading: boolean
  emptyMsg: string
}

export const LogEntries = memo(function LogEntries({ entries, loading, emptyMsg }: LogEntriesProps) {
  if (loading) return <div className="text-[#555] text-[9px] animate-pulse">loading…</div>
  if (entries.length === 0) return <div className="text-[#444] italic text-[9px]">{emptyMsg}</div>
  return (
    <div className="space-y-1 max-h-80 overflow-y-auto">
      {entries.map((entry, ei) => (
        <div key={ei} className="text-[9px] border-l border-[#222] pl-2">
          <div className="flex gap-1">
            <span className="text-[#f59e0b] shrink-0">{entry.event_type}</span>
            <span className="text-[#555]">{entry.created_at?.slice(11, 19)}</span>
          </div>
          {entry.event_data && typeof entry.event_data === "object" && (
            <div className="text-[#666] mt-0.5 break-all space-y-0.5">
              {Object.entries(entry.event_data as Record<string, any>)
                .filter(([k]) => k !== "raw_response")
                .map(([k, v]) => {
                  const val = typeof v === "string" ? v : JSON.stringify(v)
                  if (val.length > 8000) return <div key={k} className="text-[#444] italic">{k}: [too large to display]</div>
                  return <div key={k} className="text-[#777]"><span className="text-[#555]">{k}:</span> <span className="whitespace-pre-wrap break-all">{val.slice(0, 2000)}</span></div>
                })}
            </div>
          )}
        </div>
      ))}
    </div>
  )
})
