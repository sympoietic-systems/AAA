import { memo } from "react"
import type { StepPreview } from "../../../../api/research"
import { JsonBlock } from "../../../UI"
import { DocumentDigestionPreview } from "./preview/DocumentDigestionPreview"
import { ConsolidatingPreview } from "./preview/ConsolidatingPreview"
import { EvaluatingPreview } from "./preview/EvaluatingPreview"
import { SynthesizingPreview } from "./preview/SynthesizingPreview"

interface StepPreviewPanelProps {
  preview: StepPreview
  phaseLabel: string
  onReinitialize: () => void
  reinitLoading: boolean
}

export const StepPreviewPanel = memo(function StepPreviewPanel({
  preview, phaseLabel, onReinitialize, reinitLoading,
}: StepPreviewPanelProps) {
  return (
    <div className="space-y-3 text-[10px]">
      <div className="flex items-center justify-between">
        <div className="text-semantic-header uppercase text-[9px] tracking-wider font-mono">
          [ {phaseLabel} — preview ]
        </div>
        <button onClick={onReinitialize} disabled={reinitLoading}
          className="text-action-dim hover:text-action-hover text-[9px] font-mono disabled:text-[#333] cursor-pointer transition-colors">
          [{reinitLoading ? "…" : "⟳ reinitialize"}]
        </button>
      </div>
      <div className="flex gap-3 border-b border-ui-border pb-1">
        <span className="text-ui-secondary text-[9px] uppercase font-mono">input / upcoming state</span>
      </div>
      {preview.objective && (
        <div>
          <div className="text-ui-dim text-[9px] mb-0.5 uppercase font-mono">objective:</div>
          <div className="text-ui-secondary pl-2 font-mono">{preview.objective}</div>
        </div>
      )}

      {preview.phase === "document_digestion" && <DocumentDigestionPreview preview={preview} />}

      {preview.max_depth != null && (
        <div className="flex gap-4 text-ui-dim flex-wrap font-mono">
          <span>depth: {preview.max_depth}</span>
          <span>budget: ${preview.budget_limit_usd?.toFixed(2)}</span>
          {preview.model && <span>model: {preview.model}</span>}
          {preview.temperature != null && <span>temp: {preview.temperature}</span>}
          {preview.max_tokens && <span>tokens: {preview.max_tokens}</span>}
        </div>
      )}
      {preview.system_prompt && (
        <JsonBlock
          data={preview.system_prompt}
          variant="prompt"
          maxHeight="max-h-[350px]"
          collapsible={true}
          defaultCollapsed={true}
          label="system prompt"
        />
      )}
      {preview.user_prompt && (
        <JsonBlock
          data={preview.user_prompt}
          variant="prompt"
          maxHeight="max-h-[350px]"
          collapsible={true}
          defaultCollapsed={false}
          label="user prompt"
        />
      )}
      {preview.pending_queries && preview.pending_queries.length > 0 && (
        <div>
          <div className="text-ui-dim text-[9px] mb-0.5 uppercase font-mono">pending queries:</div>
          {preview.pending_queries.map((q, i) => (
            <div key={i} className="text-ui-secondary pl-2 font-mono">· {q}</div>
          ))}
        </div>
      )}
      {preview.urls_to_fetch && preview.urls_to_fetch.length > 0 && (
        <div>
          <div className="text-ui-dim text-[9px] mb-1 uppercase font-mono">urls to parse ({preview.urls_to_fetch.length})</div>
          <div className="space-y-0.5 max-h-48 overflow-y-auto">
            {preview.urls_to_fetch.map((u, i) => (
              <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                <span className="text-ui-dim">{i + 1}.</span>{" "}
                <a href={u.url} target="_blank" rel="noopener noreferrer"
                  className="text-action-dim hover:text-action-hover underline break-all font-mono transition-colors">
                  {u.title || u.url || "—"}
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
      {preview.sources_to_digest && preview.sources_to_digest.length > 0 && (
        <div>
          <div className="text-ui-dim text-[9px] mb-1 uppercase font-mono">sources to digest ({preview.sources_to_digest.length})</div>
          <div className="space-y-1.5 max-h-60 overflow-y-auto">
            {preview.sources_to_digest.map((s, i) => (
              <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                <div className="flex gap-1.5 items-center">
                  <span className="text-ui-dim">{i + 1}.</span>
                  <a href={s.url} target="_blank" rel="noopener noreferrer"
                    className="text-action-dim hover:text-action-hover underline break-all font-mono font-semibold transition-colors">
                    {s.title || s.url || "—"}
                  </a>
                </div>
                {s.snippet && (
                  <div className="text-ui-dim text-[8px] pl-4 mt-0.5 leading-normal italic font-mono">
                    {s.snippet}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {preview.phase === "consolidating" && <ConsolidatingPreview preview={preview} />}
      {preview.phase === "evaluating" && <EvaluatingPreview preview={preview} />}
      {preview.phase === "synthesizing" && <SynthesizingPreview preview={preview} />}

      {preview.note && (
        <div className="text-ui-dim italic text-[9px] font-mono">{preview.note}</div>
      )}
    </div>
  )
})
