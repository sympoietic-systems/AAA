import { memo } from "react"
import type { ResultRendererProps } from "./types"

export const DocumentDigestionResult = memo(function DocumentDigestionResult({
  selected, parsedResult,
}: ResultRendererProps) {
  let fileId = ""
  let mode = ""
  try {
    const d = selected.step_data ? JSON.parse(selected.step_data) : null
    fileId = d?.file_id || ""
    mode = d?.mode || ""
  } catch {}

  const parseField = (key: string): string[] => {
    try {
      const d = selected.step_data ? JSON.parse(selected.step_data) : null
      return d?.[key] || []
    } catch { return [] }
  }
  const docLearnings: string[] = parsedResult.learnings.length > 0 ? parsedResult.learnings : parseField("learnings")
  const ddFollowups: string[] = parseField("followups")
  const ddGaps: string[] = parseField("gaps")

  return (
    <div className="border-t border-ui-border pt-2 space-y-3">
      {fileId && (
        <div className="flex items-center gap-2">
          <span className="text-semantic-purple text-[8px] font-mono">▪ file</span>
          <span className="text-ui-secondary text-[9px] truncate">{fileId}{mode ? ` (${mode})` : ""}</span>
        </div>
      )}
      {docLearnings.length > 0 && (
        <div>
          <div className="text-ui-dim text-[8px] uppercase mb-1 font-mono">learnings ({docLearnings.length})</div>
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {docLearnings.map((l, i) => (
              <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-semantic-green/30 leading-relaxed">
                <span className="text-ui-dim">{i + 1}.</span> {l}
              </div>
            ))}
          </div>
        </div>
      )}
      {ddFollowups.length > 0 && (
        <div>
          <div className="text-ui-dim text-[8px] uppercase mb-1 font-mono">followups ({ddFollowups.length})</div>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {ddFollowups.map((f, i) => (
              <div key={i} className="text-semantic-purple text-[9px] pl-2 border-l border-semantic-purple/30 leading-relaxed">
                → {f}
              </div>
            ))}
          </div>
        </div>
      )}
      {ddGaps.length > 0 && (
        <div>
          <div className="text-ui-dim text-[8px] uppercase mb-1 font-mono">gaps ({ddGaps.length})</div>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {ddGaps.map((g, i) => (
              <div key={i} className="text-semantic-gold text-[9px] pl-2 border-l border-semantic-gold/30 leading-relaxed">
                ◇ {g}
              </div>
            ))}
          </div>
        </div>
      )}
      {docLearnings.length === 0 && ddFollowups.length === 0 && ddGaps.length === 0 && (
        <div className="text-ui-dim italic text-[9px]">
          {selected.result_summary || "no document analysis results"}
        </div>
      )}
    </div>
  )
})
