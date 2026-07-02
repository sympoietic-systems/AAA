import { memo } from "react"
import type { ResultRendererProps } from "./types"
import { parseStatus } from "./helpers"

export const ParseResult = memo(function ParseResult({ selectedResults }: ResultRendererProps) {
  if (selectedResults.length === 0) {
    return <div className="text-ui-dim italic text-[9px] border-t border-ui-border pt-2 font-mono">no parsed results</div>
  }

  return (
    <div className="border-t border-ui-border pt-2 space-y-1">
      <div className="text-ui-dim text-[8px] uppercase mb-1">parsed pages ({selectedResults.length})</div>
      {selectedResults.map(r => {
        const errorMsg = (r as any).error
        const st = errorMsg
          ? { icon: "✗", label: "error", color: "var(--color-semantic-red)" }
          : parseStatus(r.content_preview)
        return (
          <div key={r.id} className="pl-2 flex items-start gap-1.5 py-0.5">
            <span style={{ color: st.color }} className="text-[9px] shrink-0">{st.icon}</span>
            <div className="min-w-0">
              <a href={r.source_url || "#"} target="_blank" rel="noopener noreferrer"
                className="text-ui-secondary hover:text-action-hover underline break-all text-[9px] transition-colors">
                {r.source_title || r.source_url?.slice(0, 100) || "—"}
              </a>
              {errorMsg ? (
                <div className="text-semantic-red text-[7.5px] font-mono leading-tight pl-1">{errorMsg}</div>
              ) : (
                r.raw_file_path && <div className="text-ui-dim text-[7px] truncate">saved: {r.raw_file_path}</div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
})
