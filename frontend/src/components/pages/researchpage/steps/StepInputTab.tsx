import React, { memo } from "react"
import type { StepPreview } from "../../../../api/research"
import { SectionDivider } from "../shared/SectionDivider"
import { JsonBlock } from "../../../UI"
import { LogEntries } from "./LogEntries"

interface StepInputTabProps {
  stepPhase: string
  liveInput: StepPreview | null
  reinitLoading: boolean
  reinitLiveInput: () => void
  inputEntries: any[]
}

export const StepInputTab = memo(function StepInputTab({
  stepPhase, liveInput, reinitLoading, reinitLiveInput, inputEntries,
}: StepInputTabProps) {
  return (
    <div className="space-y-3">
      {stepPhase && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <div className="text-[#555] text-[9px]">live input preview ({stepPhase})</div>
            <button onClick={reinitLiveInput} disabled={reinitLoading}
              className="text-[#4ade80] hover:text-[#6ee7b0] text-[9px] font-mono disabled:text-[#333] cursor-pointer">
              [{reinitLoading ? "…" : "⟳ reinitialize"}]
            </button>
          </div>
          {reinitLoading ? (
            <div className="text-[#555] text-[9px] animate-pulse">regenerating…</div>
          ) : liveInput ? (
            <div className="space-y-2">
              {liveInput.objective && <div><div className="text-[#555] text-[8px]">objective:</div><div className="text-[#94a3b8] text-[9px] pl-2">{liveInput.objective}</div></div>}
              {liveInput.max_depth != null && <div className="flex gap-3 text-[#777] text-[9px] flex-wrap"><span>depth:{liveInput.max_depth}</span><span>budget:${liveInput.budget_limit_usd?.toFixed(2)}</span>{liveInput.model && <span>model:{liveInput.model}</span>}{liveInput.temperature != null && <span>temp:{liveInput.temperature}</span>}</div>}
              {liveInput.system_prompt && <div><div className="text-[#555] text-[8px] mb-0.5">system prompt:</div><JsonBlock data={liveInput.system_prompt} variant="prompt" maxHeight="max-h-32" /></div>}
              {liveInput.user_prompt && <div><div className="text-[#555] text-[8px] mb-0.5">user prompt:</div><JsonBlock data={liveInput.user_prompt} variant="prompt" maxHeight="max-h-24" /></div>}
              {liveInput.pending_queries && liveInput.pending_queries.length > 0 && <div><div className="text-[#555] text-[8px] mb-0.5">queries:</div>{liveInput.pending_queries.map((q,i)=><div key={i} className="text-[#94a3b8] text-[9px] pl-2">· {q}</div>)}</div>}
              {liveInput.note && <div className="text-[#444] italic text-[8px]">{liveInput.note}</div>}
            </div>
          ) : (
            <div className="text-[#444] italic text-[9px]">click reinitialize to load</div>
          )}
        </div>
      )}

      {inputEntries.length > 0 && (
        <div>
          <SectionDivider />
          <div className="text-[#555] text-[9px] mb-1">logged inputs ({inputEntries.length}):</div>
          <LogEntries entries={inputEntries} loading={false} emptyMsg="" />
        </div>
      )}
      {inputEntries.length === 0 && !stepPhase && (
        <div className="text-[#444] italic text-[9px]">no input data for this step</div>
      )}
    </div>
  )
})
