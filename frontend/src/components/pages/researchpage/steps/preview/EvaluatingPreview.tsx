import { memo } from "react"
import type { StepPreview } from "../../../../../api/research"
import { JsonBlock, KeyValueGrid } from "../../../../UI"

export const EvaluatingPreview = memo(function EvaluatingPreview({ preview }: { preview: StepPreview }) {
  const pathColor = preview.eval_path === "hard_stop"
    ? "text-semantic-red"
    : preview.eval_path === "hard_continue"
    ? "text-semantic-green"
    : "text-semantic-gold"

  return (
    <div className="space-y-3 font-mono">
      {/* Path indicator — hard rule or LLM */}
      {preview.eval_path && (
        <div className="flex items-center gap-2">
          <span className={`text-[9px] font-mono font-bold ${pathColor}`}>
            {preview.eval_path === "hard_stop" ? "■ HARD STOP" :
             preview.eval_path === "hard_continue" ? "▶ HARD CONTINUE" :
             "⚖ LLM BORDERLINE"}
          </span>
          <span className="text-ui-dim text-[9px]">{preview.eval_path_reason}</span>
        </div>
      )}

      {/* Metrics */}
      <div>
        <div className="text-ui-dim text-[9px] uppercase font-mono mb-1">evaluation metrics</div>
        <KeyValueGrid items={[
          { key: "current depth", value: `${preview.current_depth ?? 0} / ${preview.max_depth ?? 0}` },
          { key: "sources analyzed", value: preview.sources_analyzed ?? 0 },
          { key: "stagnation counter", value: preview.stagnation_counter ?? 0 },
        ]} />
      </div>

      {/* Completeness vs threshold */}
      <div>
        <div className="text-ui-dim text-[9px] uppercase font-mono mb-1">completeness score</div>
        <div className="flex items-center gap-2">
          <div className="flex-1 h-2 bg-ui-border overflow-hidden relative">
            <div
              className="h-full bg-semantic-green transition-all"
              style={{ width: `${Math.round((preview.completeness_score ?? 0) * 100)}%` }}
            />
            {preview.satisfaction_threshold != null && (
              <div
                className="absolute top-0 bottom-0 w-px bg-semantic-gold"
                style={{ left: `${Math.round(preview.satisfaction_threshold * 100)}%` }}
                title={`threshold: ${Math.round(preview.satisfaction_threshold * 100)}%`}
              />
            )}
          </div>
          <span className="text-semantic-green text-[9px] font-mono shrink-0">
            {Math.round((preview.completeness_score ?? 0) * 100)}%
            {preview.satisfaction_threshold != null && (
              <span className="text-ui-dim"> / {Math.round(preview.satisfaction_threshold * 100)}%</span>
            )}
          </span>
        </div>
        {preview.eval_path === "llm_borderline" && (
          <div className="text-semantic-gold text-[8px] mt-0.5 font-mono">
            ↑ in borderline zone — LLM evaluator will decide stop vs continue
          </div>
        )}
      </div>

      {/* Consolidation context passed to evaluator */}
      {preview.key_insights && preview.key_insights.length > 0 && (
        <details open>
          <summary className="text-semantic-green text-[9px] cursor-pointer hover:text-semantic-green/80 font-mono transition-colors">
            key insights ({preview.key_insights.length})
          </summary>
          <div className="mt-1 space-y-0.5 max-h-32 overflow-y-auto pr-1">
            {preview.key_insights.map((ins: string, i: number) => (
              <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">✓ {ins}</div>
            ))}
          </div>
        </details>
      )}

      {/* Remaining gaps */}
      {preview.remaining_gaps && preview.remaining_gaps.length > 0 && (
        <details open>
          <summary className="text-semantic-gold text-[9px] cursor-pointer hover:text-semantic-gold/80 font-mono transition-colors">
            remaining gaps ({preview.remaining_gaps.length})
          </summary>
          <div className="mt-1 space-y-0.5 max-h-28 overflow-y-auto pr-1">
            {preview.remaining_gaps.map((g: string, i: number) => (
              <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed font-mono">◇ {g}</div>
            ))}
          </div>
        </details>
      )}

      {/* Proposed next queries */}
      {preview.next_queries && preview.next_queries.length > 0 && (
        <details>
          <summary className="text-ui-secondary text-[9px] cursor-pointer hover:text-ui-primary font-mono transition-colors">
            proposed next queries ({preview.next_queries.length})
          </summary>
          <div className="mt-1 space-y-0.5 pl-2">
            {preview.next_queries.map((q: string, i: number) => (
              <div key={i} className="text-ui-secondary text-[9px] leading-relaxed">· {q}</div>
            ))}
          </div>
        </details>
      )}

      {/* Proposed direct URLs */}
      {preview.next_direct_urls && preview.next_direct_urls.length > 0 && (
        <details>
          <summary className="text-ui-secondary text-[9px] cursor-pointer hover:text-ui-primary font-mono transition-colors">
            proposed direct URLs ({preview.next_direct_urls.length})
          </summary>
          <div className="mt-1 space-y-0.5 pl-2">
            {preview.next_direct_urls.map((u: string, i: number) => (
              <div key={i} className="text-[9px]">
                <a href={u} target="_blank" rel="noopener noreferrer"
                   className="text-action-dim hover:text-action-hover underline break-all transition-colors">{u}</a>
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Show prompts only for LLM borderline mode */}
      {preview.eval_path === "llm_borderline" && preview.system_prompt && (
        <JsonBlock
          data={preview.system_prompt}
          variant="prompt"
          maxHeight="max-h-[300px]"
          collapsible={true}
          defaultCollapsed={true}
          label="evaluator system prompt"
        />
      )}
      {preview.eval_path === "llm_borderline" && preview.user_prompt && (
        <JsonBlock
          data={preview.user_prompt}
          variant="prompt"
          maxHeight="max-h-[350px]"
          collapsible={true}
          defaultCollapsed={false}
          label="evaluator user prompt"
        />
      )}
    </div>
  )
})
