import { memo } from "react"
import type { ResultRendererProps } from "./types"

export const PlanResult = memo(function PlanResult({ parsedResult }: ResultRendererProps) {
  if (parsedResult.queries.length === 0 && !parsedResult.goal) return null
  return (
    <div className="border-t border-ui-border pt-2 space-y-1">
      {parsedResult.goal && (
        <div>
          <div className="text-ui-dim text-[8px] uppercase">goal:</div>
          <div className="text-ui-secondary text-[9px] pl-2 font-mono">{parsedResult.goal}</div>
        </div>
      )}
      {parsedResult.queries.length > 0 && (
        <div>
          <div className="text-ui-dim text-[8px] mb-0.5 uppercase">search queries ({parsedResult.queries.length}):</div>
          {parsedResult.queries.map((q, i) => (
            <div key={i} className="text-semantic-green text-[9px] pl-2 leading-relaxed">{i + 1}. {q}</div>
          ))}
        </div>
      )}
    </div>
  )
})
