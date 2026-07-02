import { memo } from "react"
import { NotableContent } from "../../../../shared/NotableContent"
import type { ResultRendererProps } from "./types"

export const ReflectResult = memo(function ReflectResult({ parsedResult, noteHook }: ResultRendererProps) {
  return (
    <div className="border-t border-ui-border pt-2 space-y-3">
      {parsedResult.completeness > 0 && (
        <div>
          <div className="text-ui-dim text-[8px] uppercase">completeness score:</div>
          <div className="flex items-center gap-2 mt-1">
            <div className="flex-1 h-2 bg-ui-border overflow-hidden">
              <div className="h-full bg-semantic-green" style={{ width: `${Math.round(parsedResult.completeness * 100)}%` }} />
            </div>
            <span className="text-semantic-green text-[9px] font-mono">{Math.round(parsedResult.completeness * 100)}%</span>
          </div>
        </div>
      )}

      {parsedResult.reflection && (
        <NotableContent hooks={noteHook} title="consolidated analysis">
          <div className="text-ui-secondary text-[9.5px] leading-relaxed whitespace-pre-wrap">
            {parsedResult.reflection}
          </div>
        </NotableContent>
      )}

      {parsedResult.key_insights && parsedResult.key_insights.length > 0 && (
        <NotableContent hooks={noteHook} title={`key insights (${parsedResult.key_insights.length})`}>
          <div className="space-y-0.5 max-h-36 overflow-y-auto pr-1">
            {parsedResult.key_insights.map((insight, i) => (
              <div key={i} className="text-semantic-green text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                ✓ {insight}
              </div>
            ))}
          </div>
        </NotableContent>
      )}

      {parsedResult.remaining_gaps && parsedResult.remaining_gaps.length > 0 && (
        <NotableContent hooks={noteHook} title={`remaining gaps (${parsedResult.remaining_gaps.length})`}>
          <div className="space-y-0.5 max-h-36 overflow-y-auto pr-1">
            {parsedResult.remaining_gaps.map((gap, i) => (
              <div key={i} className="text-semantic-gold text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                ◇ {gap}
              </div>
            ))}
          </div>
        </NotableContent>
      )}

      {parsedResult.next_queries && parsedResult.next_queries.length > 0 && (
        <NotableContent hooks={noteHook} title={`planned next search queries (${parsedResult.next_queries.length})`}>
          <div className="space-y-0.5 pl-2">
            {parsedResult.next_queries.map((q, i) => (
              <div key={i} className="text-ui-secondary text-[9px]">· {q}</div>
            ))}
          </div>
        </NotableContent>
      )}

      {parsedResult.next_direct_urls && parsedResult.next_direct_urls.length > 0 && (
        <div>
          <div className="text-ui-dim text-[8px] mb-1 uppercase font-mono font-semibold">planned direct URLs to parse ({parsedResult.next_direct_urls.length})</div>
          <div className="space-y-0.5 pl-2 font-mono">
            {parsedResult.next_direct_urls.map((u, i) => (
              <div key={i} className="text-ui-secondary text-[9px] leading-relaxed">
                <span className="text-ui-dim">{i + 1}.</span>{" "}
                <a href={u} target="_blank" rel="noopener noreferrer"
                  className="text-action-dim hover:text-action-hover underline break-all transition-colors">
                  {u}
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
})
