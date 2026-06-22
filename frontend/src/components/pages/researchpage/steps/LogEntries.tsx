import React, { memo, useState } from "react"
import { JsonBlock } from "../../../UI"

interface LogEntriesProps {
  entries: any[]
  loading: boolean
  emptyMsg: string
}

export const LogEntries = memo(function LogEntries({ entries, loading, emptyMsg }: LogEntriesProps) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({ 0: true })

  const toggleExpand = (idx: number) => {
    setExpanded(prev => ({ ...prev, [idx]: !prev[idx] }))
  }

  if (loading) return <div className="text-[#555] text-[9px] animate-pulse">loading…</div>
  if (entries.length === 0) return <div className="text-[#444] italic text-[9px]">{emptyMsg}</div>

  return (
    <div className="space-y-2 pr-1">
      {entries.map((entry, ei) => {
        const isExpanded = !!expanded[ei]
        return (
          <div key={ei} className="text-[9px] border-l border-[#222] pl-2 py-0.5">
            <button
              onClick={() => toggleExpand(ei)}
              className="flex items-center gap-1.5 cursor-pointer hover:text-[#bbb] text-left w-full select-none"
            >
              <span className="text-[#555] text-[7px] font-mono shrink-0">
                {isExpanded ? "▼" : "▶"}
              </span>
              <span className="text-[#f59e0b] font-mono font-bold shrink-0">{entry.event_type}</span>
              <span className="text-[#555] font-mono text-[8px]">{entry.created_at?.slice(11, 19)}</span>
            </button>

            {isExpanded && entry.event_data && typeof entry.event_data === "object" && (
              <div className="text-[#666] mt-1 space-y-2 pl-3 border-l border-[#1a1a1a]">
                {Object.entries(entry.event_data as Record<string, any>)
                  .filter(([k]) => k !== "raw_response")
                  .map(([k, v]) => {
                    if (typeof v === "string" && v.length > 8000) {
                      return <div key={k} className="text-[#444] italic">{k}: [too large to display]</div>
                    }
                    if (typeof v === "string") {
                      const isLongOrMultiline = v.includes("\n") || v.length > 120 || k.endsWith("_prompt") || k === "prompt"
                      if (isLongOrMultiline) {
                        const blockVariant = k.endsWith("_prompt") || k === "prompt" ? "prompt" : "raw"
                        return (
                          <div key={k} className="mt-1.5">
                            <JsonBlock
                              data={v.slice(0, 8000)}
                              variant={blockVariant}
                              maxHeight="max-h-[350px]"
                              collapsible={true}
                              defaultCollapsed={k.includes("system")}
                              label={k}
                            />
                          </div>
                        )
                      }
                      return (
                        <div key={k} className="text-[#777] leading-relaxed text-[9px]">
                          <span className="text-[#555]">{k}:</span>{" "}
                          {v.startsWith("http://") || v.startsWith("https://") ? (
                            <a href={v} target="_blank" rel="noopener noreferrer" className="text-[#4ade80] hover:text-[#6ee7b0] underline break-all">
                              {v}
                            </a>
                          ) : (
                            <span className="whitespace-pre-wrap break-all">{v}</span>
                          )}
                        </div>
                      )
                    }
                    // Object/array — use formatted JsonBlock
                    return (
                      <div key={k} className="mt-1.5">
                        <div className="text-[#555] mb-0.5 text-[8px] uppercase">{k}:</div>
                        <JsonBlock data={v} variant="json" maxHeight="max-h-64" />
                      </div>
                    )
                  })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
})
