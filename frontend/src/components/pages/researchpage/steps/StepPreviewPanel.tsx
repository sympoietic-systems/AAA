import React, { memo } from "react"
import type { StepPreview } from "../../../../api/research"
import { JsonBlock } from "../shared/JsonBlock"

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
    <div className="space-y-2 text-[10px]">
      <div className="flex items-center justify-between">
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">
          [ {phaseLabel} — preview ]
        </div>
        <button onClick={onReinitialize} disabled={reinitLoading}
          className="text-[#4ade80] hover:text-[#6ee7b0] text-[9px] font-mono disabled:text-[#333] cursor-pointer">
          [{reinitLoading ? "…" : "⟳ reinitialize"}]
        </button>
      </div>
      <div className="flex gap-3 border-b border-[#1a1a1a] pb-1">
        <span className="text-[#94a3b8] text-[9px] uppercase">input</span>
      </div>
      {preview.objective && (
        <div>
          <div className="text-[#555] text-[9px] mb-0.5">objective:</div>
          <div className="text-[#94a3b8] pl-2">{preview.objective}</div>
        </div>
      )}
      {preview.max_depth != null && (
        <div className="flex gap-4 text-[#777] flex-wrap">
          <span>depth: {preview.max_depth}</span>
          <span>budget: ${preview.budget_limit_usd?.toFixed(2)}</span>
          {preview.model && <span>model: {preview.model}</span>}
          {preview.temperature != null && <span>temp: {preview.temperature}</span>}
          {preview.max_tokens && <span>tokens: {preview.max_tokens}</span>}
        </div>
      )}
      {preview.system_prompt && (
        <div>
          <div className="text-[#555] text-[9px] mb-0.5">system prompt:</div>
          <JsonBlock data={preview.system_prompt} variant="prompt" maxHeight="max-h-48" />
        </div>
      )}
      {preview.user_prompt && (
        <div>
          <div className="text-[#555] text-[9px] mb-0.5">user prompt:</div>
          <JsonBlock data={preview.user_prompt} variant="prompt" maxHeight="max-h-32" />
        </div>
      )}
      {preview.pending_queries && preview.pending_queries.length > 0 && (
        <div>
          <div className="text-[#555] text-[9px] mb-0.5">pending queries:</div>
          {preview.pending_queries.map((q, i) => (
            <div key={i} className="text-[#94a3b8] pl-2">· {q}</div>
          ))}
        </div>
      )}
      {preview.note && (
        <div className="text-[#444] italic text-[9px]">{preview.note}</div>
      )}
    </div>
  )
})
