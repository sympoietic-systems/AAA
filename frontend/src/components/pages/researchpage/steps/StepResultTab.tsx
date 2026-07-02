import { memo } from "react"
import type { ResearchStep, ResearchStepResult } from "../../../../api/research"
import type { NotableContentHooks } from "../../../shared/NotableContent"
import type { ParsedResult } from "./results/types"
import { SearchResult } from "./results/SearchResult"
import { ParseResult } from "./results/ParseResult"
import { PlanResult } from "./results/PlanResult"
import { DigestResult } from "./results/DigestResult"
import { DocumentDigestionResult } from "./results/DocumentDigestionResult"
import { ReflectResult } from "./results/ReflectResult"
import { ReflectionResult } from "./results/ReflectionResult"
import { SynthesizeResult } from "./results/SynthesizeResult"
import { EvaluateResult } from "./results/EvaluateResult"
import { LlmMetaLog } from "./results/LlmMetaLog"

interface StepResultTabProps {
  selected: ResearchStep
  selectedResults: ResearchStepResult[]
  parsedResult: ParsedResult
  responseEntries: any[]
  inputEntries?: any[]
  parentInputUrls?: { url: string; title: string }[]
  noteHook: NotableContentHooks
}

const RESULT_RENDERERS: Record<string, typeof SearchResult> = {
  search: SearchResult,
  parallel_parse: ParseResult,
  plan: PlanResult,
  digest: DigestResult,
  document_digestion: DocumentDigestionResult,
  reflect: ReflectResult,
  reflection: ReflectionResult,
  synthesize: SynthesizeResult,
  evaluate: EvaluateResult,
}

export const StepResultTab = memo(function StepResultTab(props: StepResultTabProps) {
  const { selected, selectedResults, responseEntries, inputEntries } = props

  const searchQueries = inputEntries
    ?.filter(e => e.event_type === "orchestrator_search")
    .map(e => ({ resultsCount: (e.event_data as any)?.results_count ?? 0 })) ?? []

  const Renderer = RESULT_RENDERERS[selected.step_type]

  const showNoData =
    selectedResults.length === 0 &&
    !selected.result_summary &&
    responseEntries.length === 0 &&
    selected.step_type !== "evaluate" &&
    !(selected.step_type === "search" && searchQueries.length > 0)

  return (
    <div className="space-y-2 font-mono">
      {selected.result_summary && (
        <div className="text-ui-secondary text-[10px] leading-relaxed">{selected.result_summary}</div>
      )}

      {Renderer && <Renderer {...props} />}

      <LlmMetaLog {...props} />

      {showNoData && <div className="text-ui-dim italic text-[9px]">no result data</div>}
    </div>
  )
})
