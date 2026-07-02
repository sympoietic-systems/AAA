import { memo } from "react"
import { JsonBlock } from "../../../../UI"
import type { ResultRendererProps } from "./types"

export const EvaluateResult = memo(function EvaluateResult({ selected, inputEntries, responseEntries }: ResultRendererProps) {
  const evalEntry = inputEntries?.find(e => e.event_type === "orchestrator_evaluate")
    ?? responseEntries.find(e => e.event_type === "orchestrator_evaluate")
  const evalData = evalEntry?.event_data as any
  const decision: string = evalData?.decision ?? (selected.result_summary?.startsWith("STOP") ? "stop" : "continue")
  const isStop = decision === "stop"
  const reason: string = evalData?.reason ?? selected.result_summary ?? ""
  const completeness: number = evalData?.completeness ?? evalData?.completeness_score ?? 0
  const hadLlm = responseEntries.some(e => e.event_type === "orchestrator_evaluate_response")

  return (
    <div className="border-t border-ui-border pt-2 space-y-3 font-mono">
      {/* Decision */}
      <div className="flex items-center gap-3">
        <span className={`text-[10px] font-mono font-bold ${isStop ? "text-semantic-red" : "text-semantic-green"}`}>
          {isStop ? "■ STOP" : "▶ CONTINUE"}
        </span>
        <span className={`text-[8px] font-mono ${hadLlm ? "text-semantic-gold" : "text-ui-dim"}`}>
          {hadLlm ? "via LLM" : "hard rule"}
        </span>
      </div>

      {/* Reason */}
      {reason && (
        <div>
          <div className="text-ui-dim text-[8px] uppercase mb-0.5">reason</div>
          <div className="text-ui-secondary text-[9px] leading-relaxed pl-2 border-l border-ui-border">
            {reason.replace(/^(STOP|CONTINUE):\s*/i, "")}
          </div>
        </div>
      )}

      {/* Completeness bar */}
      {completeness > 0 && (
        <div>
          <div className="text-ui-dim text-[8px] uppercase mb-1">completeness at decision</div>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-ui-border overflow-hidden">
              <div
                className={`h-full ${isStop ? "bg-semantic-green" : "bg-semantic-gold"}`}
                style={{ width: `${Math.round(completeness * 100)}%` }}
              />
            </div>
            <span className="text-ui-secondary text-[9px] font-mono">{Math.round(completeness * 100)}%</span>
          </div>
        </div>
      )}

      {/* LLM parsed output (only when LLM was called) */}
      {hadLlm && (() => {
        const llmEntry = responseEntries.find(e => e.event_type === "orchestrator_evaluate_response")
        if (!llmEntry) return null
        const d = llmEntry.event_data as any
        const rawStr = d?.raw_response || d?.raw || ""
        let llmJson: any = null
        try {
          const parsed = typeof rawStr === "string" ? JSON.parse(rawStr) : rawStr
          const inner = parsed?.json_data || parsed?.content
          llmJson = typeof inner === "string" ? JSON.parse(inner) : inner
        } catch {}
        if (!llmJson) return null
        return (
          <div className="space-y-1">
            <div className="text-ui-dim text-[8px] uppercase">llm evaluator output</div>
            <JsonBlock data={llmJson} variant="json" maxHeight="max-h-32" />
          </div>
        )
      })()}
    </div>
  )
})
